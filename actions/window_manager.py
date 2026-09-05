"""Window Manager - control de ventanas multi-monitor."""
import json
import re
import shutil
import subprocess
import sys
import time

_IS_WINDOWS = sys.platform == "win32"
_IS_LINUX = sys.platform.startswith("linux")

# Lazy deps de Windows (evitan romper el import del módulo en Linux).
gw = None
pyautogui = None
_WIN32 = None

_SWP_NOZORDER = 0x0004
_SWP_NOACTIVATE = 0x0010
_SWP_SHOWWINDOW = 0x0040


def _ensure_win32():
    global gw, pyautogui, _WIN32
    if gw is None:
        import pyautogui as _pyautogui
        import ctypes
        import pygetwindow as _gw
        gw = _gw
        pyautogui = _pyautogui
        _WIN32 = ctypes.windll.user32

def _move_resize(hwnd, x, y, w, h):
    """Win32 SetWindowPos — no activate needed, no focus stealing."""
    _WIN32.SetWindowPos(hwnd, 0, x, y, w, h,
                        _SWP_NOZORDER | _SWP_NOACTIVATE | _SWP_SHOWWINDOW)

def _get_hwnd(window):
    """Get window handle from pygetwindow Window."""
    for attr in ('_hWnd', 'hWnd', '_handle', 'handle'):
        v = getattr(window, attr, None)
        if v:
            return v
    return None

def _find_window(name: str):
    """Find a window by partial title match."""
    name_lower = name.lower()
    matches = []
    for w in gw.getAllWindows():
        if w.title.strip() and name_lower in w.title.lower():
            matches.append(w)
    return matches

def _get_monitors():
    """Get monitor positions."""
    try:
        from mss import mss
        with mss() as sct:
            monitors = sct.monitors
            result = []
            for i, m in enumerate(monitors):
                if i == 0: continue  # skip "all monitors" virtual
                result.append({"id": i, "left": m["left"], "top": m["top"], 
                              "width": m["width"], "height": m["height"]})
            return result
    except Exception:
        screen = pyautogui.size()
        return [{"id": 1, "left": 0, "top": 0, "width": screen[0], "height": screen[1]}]

_SAVED_LAYOUT = []

_SYSTEM_WINDOWS = [
    "nvidia", "program manager", "experiencia de entrada", "gestor de tareas",
    "taskbar", "barra de tareas", "menú inicio", "start menu",
    "escritorio remoto", "remote desktop", "windows input experience",
]
_MIN_CELL_W = 620  # minimum comfortable width per window
_MIN_CELL_H = 400  # minimum comfortable height per window

def _is_user_window(w):
    """Filter out system/overlay windows that shouldn't be moved."""
    t = w.title.lower()
    for skip in _SYSTEM_WINDOWS:
        if skip in t:
            return False
    if w.width > 3000 or w.height > 1500:  # full-span overlays
        return False
    return True

def _layout_grid(windows, monitor, cols, rows):
    """Distribute windows in a grid of cols x rows with minimum cell size."""
    m = monitor
    margin = 50
    gap = 15
    usable_w = m["width"] - margin * 2
    usable_h = m["height"] - margin * 2

    cell_w = max(_MIN_CELL_W, (usable_w - gap * (cols - 1)) // cols)
    cell_h = max(_MIN_CELL_H, (usable_h - gap * (rows - 1)) // rows)

    actual_cols = min(cols, (usable_w + gap) // (cell_w + gap))
    actual_rows = min(rows, (usable_h + gap) // (cell_h + gap))

    if actual_cols < 1: actual_cols = 1
    if actual_rows < 1: actual_rows = 1

    results = []
    for i, w in enumerate(windows):
        if i >= actual_cols * actual_rows:
            break
        col = i % actual_cols
        row = i // actual_cols
        x = m["left"] + margin + col * (cell_w + gap)
        y = m["top"] + margin + row * (cell_h + gap)
        results.append((w, x, y, cell_w, cell_h))
    return results

def _auto_layout(windows, monitor):
    """Choose best layout based on window count. Fewer, bigger cells."""
    count = len(windows)
    if count <= 1:
        return _layout_grid(windows, monitor, 1, 1)
    elif count <= 2:
        return _layout_grid(windows, monitor, 2, 1)
    elif count <= 4:
        return _layout_grid(windows, monitor, 2, 2)
    elif count <= 6:
        return _layout_grid(windows, monitor, 3, 2)
    else:
        return _layout_grid(windows, monitor, 3, 3)  # max 9 windows, bigger cells

def _preset_layout(windows, monitor, preset, name=None):
    """Apply a named layout preset to the given windows."""
    m = monitor
    margin = 30
    gap = 10
    w_total = m["width"] - margin * 2
    h_total = m["height"] - margin * 2
    results = []

    if preset == "side_by_side":
        if not windows:
            return results
        hw = (w_total - gap) // 2
        if len(windows) >= 2:
            results.append((windows[0], m["left"] + margin, m["top"] + margin, hw, h_total))
            results.append((windows[1], m["left"] + margin + hw + gap, m["top"] + margin, hw, h_total))
        else:
            results.append((windows[0], m["left"] + margin, m["top"] + margin, w_total, h_total))

    elif preset == "three_columns":
        for i, w in enumerate(windows[:3]):
            cw = (w_total - gap * 2) // 3
            x = m["left"] + margin + i * (cw + gap)
            y = m["top"] + margin
            results.append((w, x, y, cw, h_total))

    elif preset == "quad":
        for i, w in enumerate(windows[:4]):
            col = i % 2
            row = i // 2
            cw = (w_total - gap) // 2
            ch = (h_total - gap) // 2
            x = m["left"] + margin + col * (cw + gap)
            y = m["top"] + margin + row * (ch + gap)
            results.append((w, x, y, cw, ch))

    elif preset == "cascade":
        for i, w in enumerate(windows[:8]):
            offset = margin + i * 35
            sw = w_total - i * 20
            sh = h_total - i * 20
            if sw < 200 or sh < 150:
                break
            x = m["left"] + offset
            y = m["top"] + offset
            results.append((w, x, y, sw, sh))

    elif preset == "focus":
        if not windows:
            return results
        main_h = int(h_total * 0.65)
        side_w = (w_total - gap) // 3
        results.append((windows[0], m["left"] + margin, m["top"] + margin, w_total, main_h))
        for i, w in enumerate(windows[1:4]):
            x = m["left"] + margin + i * (side_w + gap)
            y = m["top"] + margin + main_h + gap
            results.append((w, x, y, side_w, h_total - main_h - gap))

    elif preset == "save":
        global _SAVED_LAYOUT
        _SAVED_LAYOUT = []
        for w in windows:
            try:
                _SAVED_LAYOUT.append({
                    "title": w.title,
                    "left": w.left, "top": w.top,
                    "width": w.width, "height": w.height,
                    "minimized": w.isMinimized
                })
            except Exception:
                pass
        return _SAVED_LAYOUT  # sentinel value — caller handles message

    elif preset == "restore":
        for saved in _SAVED_LAYOUT:
            saved_title_lower = saved["title"].lower()
            match = None
            for w in windows:
                if saved_title_lower in w.title.lower():
                    match = w
                    break
            if match:
                try:
                    hwnd = _get_hwnd(match)
                    if hwnd:
                        if saved["minimized"]:
                            _WIN32.ShowWindow(hwnd, 6)
                        else:
                            if match.isMinimized: match.restore()
                            _move_resize(hwnd, saved["left"], saved["top"],
                                         saved["width"], saved["height"])
                except Exception:
                    pass
        return results  # empty — caller handles message

    return results


# ── Backend Linux (Hyprland/Wayland vía hyprctl; X11 vía xdotool si existe) ──

def _hypr_raw(lua_expr: str, timeout=8):
    """Enviar expression Lua a hyprctl dispatch y devolver (rc, stdout, stderr)."""
    try:
        p = subprocess.run(["hyprctl", "dispatch", lua_expr],
                           capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()
    except Exception as e:
        return -1, "", str(e)


def _hypr_json(*args):
    """Invocar hyprctl <args> con formato JSON y parsear."""
    try:
        p = subprocess.run(["hyprctl", *args], capture_output=True, text=True, timeout=8)
        if p.returncode != 0:
            return None
        return json.loads(p.stdout or "")
    except Exception:
        return None


def _linux_clients():
    data = _hypr_json("clients", "-j")
    if not isinstance(data, list):
        return []
    return [c for c in data if c.get("mapped") and (c.get("title") or "").strip()]


def _linux_list():
    wins = _linux_clients()
    if not wins:
        return "No hay ventanas visibles."
    lines = [f"  [{c['size'][0]}x{c['size'][1]}] {c['title'][:60]}" for c in wins]
    return f"Ventanas ({len(wins)}):\n" + "\n".join(lines[:20])


def _linux_list_monitors():
    data = _hypr_json("monitors", "-j")
    if not isinstance(data, list) or not data:
        return "No se pudo listar monitores (hyprctl)."
    lines = [f"Monitores ({len(data)}):"]
    for m in data:
        lines.append(
            f"  Monitor {m['id']} ({m.get('name')}): "
            f"{m['width']}x{m['height']} en ({m['x']},{m['y']})"
        )
    return "\n".join(lines)


def _linux_find(name):
    n = (name or "").lower()
    return [c for c in _linux_clients() if n in (c.get("title") or "").lower()]


def _linux_focus(name):
    wins = _linux_find(name)
    if not wins:
        return f"No encontre ventana con '{name}'."
    addr = wins[0]["address"]
    rc, out, _ = _hypr_raw(f"hl.dsp.focus({{ window = \"address:{addr}\" }})")
    if out.lower() == "ok" or "focus" in out.lower():
        return f"Ventana '{wins[0]['title'][:40]}' enfocada."
    return f"Error: {out}"


def _linux_close(name):
    wins = _linux_find(name)
    if not wins:
        return f"No encontre ventana con '{name}'."
    addr = wins[0]["address"]
    rc, out, _ = _hypr_raw(f"hl.dsp.window.close({{ window = \"address:{addr}\" }})")
    if out.lower() == "ok":
        return f"Cerrada: {wins[0]['title'][:40]}"
    return f"Error: {out}"


def _linux_minimize(name):
    """Mueve la ventana a un workspace especial oculto (equivalente a minimize en tiling)."""
    wins = _linux_find(name)
    if not wins:
        return f"No encontre ventana con '{name}'."
    addr = wins[0]["address"]
    # window.move to special:hides the window from visible workspaces
    lua = f"hl.dsp.window.move({{ workspace = \"special:hider\", window = \"address:{addr}\" }})"
    rc, out, _ = _hypr_raw(lua)
    if out.lower() == "ok":
        return f"Minimizada (special:hider): {wins[0]['title'][:40]}"
    # fallback: restore then move
    lua2 = f"hl.dsp.focus({{ window = \"address:{addr}\" }})"
    _hypr_raw(lua2)
    rc, out, _ = _hypr_raw(lua)
    return f"Minimizada: {wins[0]['title'][:40]}" if out.lower() == "ok" else f"Error: {out}"


def _linux_maximize(name):
    wins = _linux_find(name)
    if not wins:
        return f"No encontre ventana con '{name}'."
    addr = wins[0]["address"]
    lua = f"hl.dsp.window.fullscreen({{ window = \"address:{addr}\", action = \"set\" }})"
    rc, out, _ = _hypr_raw(lua)
    return f"Maximizada: {wins[0]['title'][:40]}" if out.lower() == "ok" else f"Error: {out}"


def _linux_snap(name, side):
    """Anclar a la mitad de la pantalla (funciona en ventanas flotantes)."""
    wins = _linux_find(name)
    if not wins:
        return f"No encontre ventana con '{name}'."
    data = _hypr_json("monitors", "-j")
    if not isinstance(data, list) or not data:
        return "No se pudo obtener el monitor primario."
    m = data[0]
    mw, mh = m.get("width", 0), m.get("height", 0)
    if not mw or not mh:
        return "Monitor primario con geometria desconocida."
    addr = wins[0]["address"]
    side = side if side in ("left", "right") else "left"
    half_w, target_x = mw // 2, (0 if side == "left" else mw // 2)
    cur_w, cur_h = wins[0]["size"][0], wins[0]["size"][1]
    dx, dy = half_w - cur_w, mh - cur_h
    # resizewindow with deltas (works on tiled windows too)
    move_lua = f"hl.dsp.window.move({{ x = {target_x}, y = 0, window = \"address:{addr}\" }})"
    resize_lua = f"hl.dsp.window.resize({{ x = {dx}, y = {dy}, window = \"address:{addr}\" }})"
    _hypr_raw(move_lua)
    rc, out, _ = _hypr_raw(resize_lua)
    if out.lower() == "ok":
        return f"Ventana anclada a {side}."
    return f"Ventana movida a {side}. Redimension no aplicable (ventana en tiling?): {out}"


def _linux_move_to_monitor(name, monitor_id):
    wins = _linux_find(name)
    if not wins:
        return f"No encontre ventana con '{name}'."
    data = _hypr_json("monitors", "-j")
    if not isinstance(data, list) or not data:
        return "No se pudo listar monitores (hyprctl)."
    if monitor_id < 1 or monitor_id > len(data):
        return f"Monitor {monitor_id} no existe. Monitores: {len(data)}"
    mon = data[monitor_id - 1]
    ws_id = (mon.get("activeWorkspace") or {}).get("id")
    if ws_id is None:
        return f"Monitor {monitor_id} ({mon.get('name')}) sin workspace activo."
    addr = wins[0]["address"]
    lua = f"hl.dsp.window.move({{ workspace = {ws_id}, window = \"address:{addr}\" }})"
    rc, out, _ = _hypr_raw(lua)
    if out.lower() == "ok":
        return f"Ventana '{wins[0]['title'][:30]}' -> Monitor {monitor_id} ({mon.get('name')})"
    return f"Error: {out}"


def _linux_window_manager(action, params):
    name = params.get("name", "")
    if action == "list":
        return _linux_list()
    if action == "list_monitors":
        return _linux_list_monitors()
    if action == "focus":
        if not name:
            return "Dime el nombre de la ventana (name)."
        return _linux_focus(name)
    if action == "close":
        if not name:
            return "Dime el nombre de la ventana (name)."
        return _linux_close(name)
    if action == "minimize":
        if not name:
            return "Dime el nombre de la ventana (name)."
        return _linux_minimize(name)
    if action == "maximize":
        if not name:
            return "Dime el nombre de la ventana (name)."
        return _linux_maximize(name)
    if action == "snap":
        if not name:
            return "Dime el nombre de la ventana (name)."
        return _linux_snap(name, params.get("side", "left"))
    if action == "move_to_monitor":
        if not name:
            return "Dime el nombre de la ventana (name)."
        return _linux_move_to_monitor(name, int(params.get("monitor", 1)))
    if action == "organize":
        return ("Organizar layouts no aplica en Wayland (Hyprland usa tiling). "
                "Disponibles: list, list_monitors, focus, close, minimize, maximize, snap, move_to_monitor.")
    return "Acciones: list, list_monitors, focus, close, minimize, maximize, snap, move_to_monitor."


def window_manager(parameters: dict, player=None) -> str:
    """Control de ventanas multi-monitor."""
    action = parameters.get("action", "list")
    if _IS_LINUX:
        return _linux_window_manager(action, parameters)
    if _IS_WINDOWS:
        _ensure_win32()

    name = parameters.get("name", "")
    monitor_id = int(parameters.get("monitor", 1))
    position = parameters.get("position", "center")  # center, left, right, top, bottom
    width_pct = float(parameters.get("width", 50))  # percentage of screen width
    height_pct = float(parameters.get("height", 70))
    preset = parameters.get("preset", "auto")  # layout preset
    layout = parameters.get("layout", "")  # alias for preset
    
    if action == "list":
        windows = []
        for w in gw.getAllWindows():
            if w.title.strip() and w.width > 100 and w.height > 50:
                windows.append(f"  [{w.width}x{w.height}] {w.title[:60]}")
        if not windows:
            return "No hay ventanas visibles."
        return f"Ventanas ({len(windows)}):\n" + "\n".join(windows[:20])
    
    elif action == "list_monitors":
        monitors = _get_monitors()
        lines = [f"Monitores ({len(monitors)}):"]
        for m in monitors:
            lines.append(f"  Monitor {m['id']}: {m['width']}x{m['height']} en ({m['left']},{m['top']})")
        return "\n".join(lines)
    
    elif action == "focus":
        if not name:
            return "Dime el nombre de la ventana (name)."
        wins = _find_window(name)
        if not wins:
            return f"No encontre ventana con '{name}'."
        w = wins[0]
        try:
            if w.isMinimized: w.restore()
            hwnd = _get_hwnd(w)
            if hwnd:
                _WIN32.ShowWindow(hwnd, 9)  # SW_RESTORE
                _WIN32.SetForegroundWindow(hwnd)
            time.sleep(0.3)
            return f"Ventana '{w.title[:40]}' enfocada."
        except Exception as e:
            return f"Error: {e}"
    
    elif action == "move_to_monitor":
        if not name:
            return "Dime el nombre de la ventana (name)."
        monitors = _get_monitors()
        if monitor_id > len(monitors):
            return f"Monitor {monitor_id} no existe. Monitores: {len(monitors)}"
        
        wins = _find_window(name)
        if not wins:
            return f"No encontre ventana con '{name}'."
        
        w = wins[0]
        m = monitors[monitor_id - 1]
        
        try:
            hwnd = _get_hwnd(w)
            if not hwnd:
                return "No se pudo obtener handle de la ventana."
            if w.isMinimized: w.restore()
            
            # Calculate target position
            target_w = int(m["width"] * width_pct / 100)
            target_h = int(m["height"] * height_pct / 100)
            
            if position == "left":
                target_x = m["left"]
                target_y = m["top"]
            elif position == "right":
                target_x = m["left"] + m["width"] - target_w
                target_y = m["top"]
            elif position == "center":
                target_x = m["left"] + (m["width"] - target_w) // 2
                target_y = m["top"] + (m["height"] - target_h) // 2
            elif position == "top":
                target_x = m["left"] + (m["width"] - target_w) // 2
                target_y = m["top"]
            elif position == "bottom":
                target_x = m["left"] + (m["width"] - target_w) // 2
                target_y = m["top"] + m["height"] - target_h
            else:
                target_x = m["left"] + (m["width"] - target_w) // 2
                target_y = m["top"] + (m["height"] - target_h) // 2
            
            # Move and resize via Win32 (no focus steal)
            _move_resize(hwnd, target_x, target_y, target_w, target_h)
            time.sleep(0.1)
            
            return f"Ventana '{w.title[:30]}' -> Monitor {monitor_id} ({position}, {target_w}x{target_h})"
        except Exception as e:
            return f"Error: {e}"
    
    elif action == "minimize":
        if not name:
            return "Dime el nombre de la ventana (name)."
        wins = _find_window(name)
        if not wins:
            return f"No encontre ventana con '{name}'."
        try:
            hwnd = _get_hwnd(wins[0])
            if hwnd:
                _WIN32.ShowWindow(hwnd, 6)  # SW_MINIMIZE
            return f"Minimizada: {wins[0].title[:40]}"
        except Exception as e:
            return f"Error: {e}"
    
    elif action == "close":
        if not name:
            return "Dime el nombre de la ventana (name)."
        wins = _find_window(name)
        if not wins:
            return f"No encontre ventana con '{name}'."
        try:
            hwnd = _get_hwnd(wins[0])
            if hwnd:
                _WIN32.SendMessageW(hwnd, 0x0010, 0, 0)  # WM_CLOSE
            return f"Cerrada: {wins[0].title[:40]}"
        except Exception as e:
            return f"Error: {e}"
    
    elif action == "maximize":
        if not name:
            return "Dime el nombre de la ventana (name)."
        wins = _find_window(name)
        if not wins:
            return f"No encontre ventana con '{name}'."
        try:
            hwnd = _get_hwnd(wins[0])
            if hwnd:
                _WIN32.ShowWindow(hwnd, 3)  # SW_MAXIMIZE
            return f"Maximizada: {wins[0].title[:40]}"
        except Exception as e:
            return f"Error: {e}"
    
    elif action == "organize":
        monitors = _get_monitors()
        if monitor_id < 1 or monitor_id > len(monitors):
            monitor_id = 1
        m = monitors[monitor_id - 1]

        all_windows = []
        for w in gw.getAllWindows():
            if w.title.strip() and w.width > 100 and w.height > 50 and not w.isMinimized and _is_user_window(w):
                all_windows.append(w)

        if not all_windows:
            return "No hay ventanas abiertas para organizar."

        # Use preset or auto-detect
        p = layout or preset or "auto"
        if p == "auto":
            placements = _auto_layout(all_windows, m)
        else:
            placements = _preset_layout(all_windows, m, p)

        if p == "save":
            msg = f"Layout guardado ({len(_SAVED_LAYOUT)} ventanas)."
            return msg
        if p == "restore":
            if not _SAVED_LAYOUT:
                return "No hay un layout guardado para restaurar."
            _preset_layout(all_windows, m, "restore")
            return f"Layout restaurado ({len(_SAVED_LAYOUT)} ventanas)."

        moved = 0
        for w, x, y, cw, ch in placements:
            try:
                hwnd = _get_hwnd(w)
                if hwnd:
                    if w.isMinimized: w.restore()
                    _move_resize(hwnd, x, y, cw, ch)
                    moved += 1
            except Exception:
                pass

        layout_name = {"side_by_side": "lado a lado", "three_columns": "tres columnas",
                       "quad": "cuadrícula 2x2", "cascade": "cascada", "focus": "foco",
                       "auto": "automático"}.get(p, p)
        return f"Organizadas {moved} ventanas en {layout_name} en monitor {monitor_id}."

    elif action == "snap":
        if not name:
            return "Dime el nombre de la ventana (name)."
        side = parameters.get("side", "left")
        wins = _find_window(name)
        if not wins:
            return f"No encontre ventana con '{name}'."
        
        w = wins[0]
        monitors = _get_monitors()
        m = monitors[0]  # primary monitor
        
        try:
            hwnd = _get_hwnd(w)
            if hwnd:
                if w.isMinimized: w.restore()
                half_w = m["width"] // 2
                if side == "left":
                    _move_resize(hwnd, m["left"], m["top"], half_w, m["height"])
                else:
                    _move_resize(hwnd, m["left"] + half_w, m["top"], half_w, m["height"])
            
            return f"Ventana anclada a {side}."
        except Exception as e:
            return f"Error: {e}"

    return "Acciones: list, list_monitors, focus, move_to_monitor, minimize, close, maximize, snap, organize. Layouts: auto, side_by_side, three_columns, quad, cascade, focus, save, restore."
