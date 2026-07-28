"""
desktop.py — Control completo de escritorio + MEMORIA de acciones.
ERIS recuerda que abrio, minimizo y cerro. Puede reportar su estado.
"""
import pygetwindow as gw
import ctypes
import json
import subprocess
import time
import os
from pathlib import Path
from datetime import datetime

_WIN32 = ctypes.windll.user32
HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
SW_MINIMIZE = 6
SW_MAXIMIZE = 3
SW_RESTORE = 9
SW_CLOSE = 0x0010
SW_SHOW = 5
SW_SHOWNORMAL = 1
GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
LWA_ALPHA = 0x02

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_HISTORY_FILE = _DATA_DIR / "desktop_history.json"
_STATE_FILE = _DATA_DIR / "desktop_state.json"


def desktop_control(parameters: dict = None, player=None) -> str:
    """Control completo de escritorio de Windows con memoria."""
    params = parameters or {}
    action = params.get("action", "list_windows").lower()

    if action == "list_windows":
        return _list_windows(params)
    elif action == "list_detailed":
        return _list_detailed(params)
    elif action == "minimize":
        return _minimize_window(params)
    elif action == "maximize":
        return _maximize_window(params)
    elif action == "restore":
        return _restore_window(params)
    elif action == "close":
        return _close_window(params)
    elif action == "focus":
        return _focus_window(params)
    elif action == "get_info":
        return _get_window_info(params)
    elif action == "search":
        return _search_windows(params)
    elif action == "count":
        return _count_windows()
    elif action == "always_on_top":
        return _toggle_always_on_top(params)
    elif action == "set_opacity":
        return _set_opacity(params)
    elif action == "minimize_all":
        return _minimize_all()
    elif action == "restore_all":
        return _restore_all()
    elif action == "cascade":
        return _cascade_windows()
    elif action == "tile_horizontal":
        return _tile_horizontal()
    elif action == "tile_vertical":
        return _tile_vertical()
    elif action == "get_foreground":
        return _get_foreground()
    elif action == "status":
        return _get_status()
    elif action == "open_app":
        return _open_app(params)
    elif action == "close_app":
        return _close_app(params)
    elif action == "list_apps":
        return _list_running_apps()
    elif action == "get_state":
        return _get_state()
    elif action == "get_opened":
        return _get_opened()
    elif action == "get_minimized":
        return _get_minimized()
    elif action == "get_closed":
        return _get_closed()
    elif action == "is_open":
        return _is_open(params)
    elif action == "what_did_i_do":
        return _what_did_i_do(params)
    elif action == "clear_state":
        return _clear_state()
    return (
        "Acciones: list_windows, list_detailed, minimize, maximize, restore, close, "
        "focus, get_info, search, count, always_on_top, set_opacity, minimize_all, "
        "restore_all, cascade, tile_horizontal, tile_vertical, get_foreground, "
        "status, open_app, close_app, list_apps, get_state, get_opened, "
        "get_minimized, get_closed, is_open, what_did_i_do, clear_state"
    )


def _get_hwnd(window):
    for attr in ('_hWnd', 'hWnd', '_handle', 'handle'):
        v = getattr(window, attr, None)
        if v:
            return v
    return None


def _find_windows(name: str):
    name_lower = name.lower()
    return [w for w in gw.getAllWindows()
            if w.title.strip() and name_lower in w.title.lower()]


def _find_single(name: str):
    matches = _find_windows(name)
    if not matches:
        return None, "No encontre ventana con '{}'".format(name)
    return matches[0], None


def _load_state() -> dict:
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"opened": [], "minimized": [], "closed": [], "sessions": []}


def _save_state(state: dict):
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def _track_action(action_type: str, app_name: str, window_title: str = "", details: str = ""):
    state = _load_state()
    entry = {
        "app": app_name,
        "title": window_title[:80],
        "details": details,
        "time": datetime.now().isoformat(),
    }
    if action_type == "opened":
        state["opened"].append(entry)
        state["opened"] = state["opened"][-50:]
    elif action_type == "minimized":
        state["minimized"].append(entry)
        state["minimized"] = state["minimized"][-50:]
    elif action_type == "restored":
        state["minimized"] = [m for m in state["minimized"] if m["app"] != app_name]
    elif action_type == "closed":
        state["closed"].append(entry)
        state["closed"] = state["closed"][-50:]
        state["opened"] = [o for o in state["opened"] if o["app"] != app_name]
    _save_state(state)


def _log_action(action: str, target: str, result: str):
    history = _load_history()
    history.append({
        "action": action,
        "target": target,
        "result": result[:100],
        "timestamp": datetime.now().isoformat(),
    })
    if len(history) > 200:
        history = history[-200:]
    _save_history(history)


def _wait_for_window(app_name: str, before_hwnds: set = None, timeout: float = 5.0):
    """Wait for a NEW window to appear. Uses HWND tracking to avoid false positives."""
    base = app_name.replace(".exe", "").replace(".EXE", "").lower()
    keywords = [base]
    aliases = {
        "notepad": ["bloc de notas", "notepad"],
        "calc": ["calculator", "calculadora", "calculatorapp"],
        "mspaint": ["paint", "dibujo"],
        "explorer": ["explorer", "file explorer", "file explorer window"],
        "cmd": ["command prompt", "símbolo del sistema"],
        "powershell": ["powershell"],
    }
    for key, vals in aliases.items():
        if key in base:
            keywords.extend(vals)
    start = time.time()
    while time.time() - start < timeout:
        for w in gw.getAllWindows():
            if not w.title.strip():
                continue
            hwnd = _get_hwnd(w)
            if before_hwnds and hwnd and hwnd in before_hwnds:
                continue
            title_lower = w.title.lower()
            for kw in keywords:
                if kw in title_lower:
                    return w
        time.sleep(0.3)
    return None


def _list_windows(params: dict) -> str:
    show_hidden = params.get("show_hidden", False)
    windows = []
    for w in gw.getAllWindows():
        if not w.title.strip():
            continue
        if not show_hidden and (w.width < 50 or w.height < 50):
            continue
        state = "MIN" if w.isMinimized else ("MAX" if w.isMaximized else "NOR")
        windows.append({
            "title": w.title[:60],
            "size": "{}x{}".format(w.width, w.height),
            "pos": "({}, {})".format(w.left, w.top),
            "state": state,
        })
    if not windows:
        return "No hay ventanas visibles"
    lines = ["═══ VENTANAS ABIERTAS ({}) ═══".format(len(windows)), ""]
    for i, w in enumerate(windows, 1):
        lines.append("  {:2d}. [{}] {:40s} {} @ {}".format(
            i, w["state"], w["title"], w["size"], w["pos"]))
    return "\n".join(lines)


def _list_detailed(params: dict) -> str:
    windows = []
    for w in gw.getAllWindows():
        if not w.title.strip() or w.width < 50 or w.height < 50:
            continue
        hwnd = _get_hwnd(w)
        pid = w._processId if hasattr(w, '_processId') else "?"
        state = "minimized" if w.isMinimized else ("maximized" if w.isMaximized else "normal")
        windows.append({
            "title": w.title[:80],
            "hwnd": hex(hwnd) if hwnd else "?",
            "pid": pid,
            "size": "{}x{}".format(w.width, w.height),
            "pos": "({}, {})".format(w.left, w.top),
            "state": state,
        })
    if not windows:
        return "No hay ventanas visibles"
    lines = ["═══ VENTANAS DETALLADAS ({}) ═══".format(len(windows)), ""]
    for i, w in enumerate(windows, 1):
        lines.append("  {:2d}. {}".format(i, w["title"]))
        lines.append("      HWND: {} | PID: {} | State: {}".format(w["hwnd"], w["pid"], w["state"]))
        lines.append("      Size: {} | Pos: {}".format(w["size"], w["pos"]))
    return "\n".join(lines)


def _minimize_window(params: dict) -> str:
    name = params.get("name", "")
    if not name:
        return "Error: se requiere 'name'"
    w, err = _find_single(name)
    if err:
        return err
    try:
        hwnd = _get_hwnd(w)
        if hwnd:
            _WIN32.ShowWindow(hwnd, SW_MINIMIZE)
            _track_action("minimized", name, w.title)
            _log_action("minimize", w.title, "OK")
            return "Minimizada: '{}'".format(w.title[:50])
        return "No se pudo obtener HWND para '{}'".format(w.title[:50])
    except Exception as e:
        return "Error minimizando: {}".format(str(e))


def _maximize_window(params: dict) -> str:
    name = params.get("name", "")
    if not name:
        return "Error: se requiere 'name'"
    w, err = _find_single(name)
    if err:
        return err
    try:
        hwnd = _get_hwnd(w)
        if hwnd:
            _WIN32.ShowWindow(hwnd, SW_MAXIMIZE)
            _log_action("maximize", w.title, "OK")
            return "Maximizada: '{}'".format(w.title[:50])
        return "No se pudo obtener HWND"
    except Exception as e:
        return "Error maximizando: {}".format(str(e))


def _restore_window(params: dict) -> str:
    name = params.get("name", "")
    if not name:
        return "Error: se requiere 'name'"
    w, err = _find_single(name)
    if err:
        return err
    try:
        hwnd = _get_hwnd(w)
        if hwnd:
            _WIN32.ShowWindow(hwnd, SW_RESTORE)
            _track_action("restored", name, w.title)
            _log_action("restore", w.title, "OK")
            return "Restaurada: '{}'".format(w.title[:50])
        return "No se pudo obtener HWND"
    except Exception as e:
        return "Error restaurando: {}".format(str(e))


def _close_window(params: dict) -> str:
    name = params.get("name", "")
    if not name:
        return "Error: se requiere 'name'"
    w, err = _find_single(name)
    if err:
        return err
    try:
        hwnd = _get_hwnd(w)
        if hwnd:
            _WIN32.PostMessageW(hwnd, SW_CLOSE, 0, 0)
            _track_action("closed", name, w.title)
            _log_action("close", w.title, "OK")
            return "Cerrada: '{}'".format(w.title[:50])
        w.close()
        _track_action("closed", name, w.title)
        _log_action("close", w.title, "OK (pygetwindow)")
        return "Cerrada: '{}'".format(w.title[:50])
    except Exception as e:
        return "Error cerrando: {}".format(str(e))


def _focus_window(params: dict) -> str:
    name = params.get("name", "")
    if not name:
        return "Error: se requiere 'name'"
    w, err = _find_single(name)
    if err:
        return err
    try:
        if w.isMinimized:
            w.restore()
            _track_action("restored", name, w.title)
        hwnd = _get_hwnd(w)
        if hwnd:
            _WIN32.SetForegroundWindow(hwnd)
        else:
            w.activate()
        _log_action("focus", w.title, "OK")
        return "Enfocada: '{}'".format(w.title[:50])
    except Exception as e:
        return "Error enfocando: {}".format(str(e))


def _get_window_info(params: dict) -> str:
    name = params.get("name", "")
    if not name:
        return "Error: se requiere 'name'"
    w, err = _find_single(name)
    if err:
        return err
    hwnd = _get_hwnd(w)
    pid = w._processId if hasattr(w, '_processId') else "?"
    state = "minimized" if w.isMinimized else ("maximized" if w.isMaximized else "normal")
    lines = [
        "═══ INFO VENTANA ═══",
        "",
        "  Titulo:   {}".format(w.title),
        "  HWND:     {}".format(hex(hwnd) if hwnd else "?"),
        "  PID:      {}".format(pid),
        "  Estado:   {}".format(state),
        "  Posicion: ({}, {})".format(w.left, w.top),
        "  Tamanio:  {}x{}".format(w.width, w.height),
        "  Visible:  {}".format(w.visible),
    ]
    return "\n".join(lines)


def _search_windows(params: dict) -> str:
    query = params.get("query", "").lower()
    if not query:
        return "Error: se requiere 'query'"
    matches = _find_windows(query)
    if not matches:
        return "Sin resultados para '{}'".format(query)
    lines = ["═══ RESULTADOS '{}' ({}) ═══".format(query, len(matches)), ""]
    for w in matches:
        state = "MIN" if w.isMinimized else ("MAX" if w.isMaximized else "NOR")
        lines.append("  [{}] {} ({}x{})".format(state, w.title[:60], w.width, w.height))
    return "\n".join(lines)


def _count_windows() -> str:
    visible = [w for w in gw.getAllWindows() if w.title.strip() and w.width > 50 and w.height > 50]
    minimized = sum(1 for w in visible if w.isMinimized)
    maximized = sum(1 for w in visible if w.isMaximized)
    normal = len(visible) - minimized - maximized
    return "Ventanas: {} total ({} normal, {} minimizadas, {} maximizadas)".format(
        len(visible), normal, minimized, maximized)


def _toggle_always_on_top(params: dict) -> str:
    name = params.get("name", "")
    if not name:
        return "Error: se requiere 'name'"
    w, err = _find_single(name)
    if err:
        return err
    hwnd = _get_hwnd(w)
    if not hwnd:
        return "No se pudo obtener HWND"
    try:
        ex_style = _WIN32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        is_top = bool(ex_style & 0x00000008)
        if is_top:
            _WIN32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0040)
            return "Always-on-top DESACTIVADO para '{}'".format(w.title[:40])
        else:
            _WIN32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0040)
            return "Always-on-top ACTIVADO para '{}'".format(w.title[:40])
    except Exception as e:
        return "Error: {}".format(str(e))


def _set_opacity(params: dict) -> str:
    name = params.get("name", "")
    opacity = int(params.get("opacity", 255))
    if not name:
        return "Error: se requiere 'name'"
    w, err = _find_single(name)
    if err:
        return err
    hwnd = _get_hwnd(w)
    if not hwnd:
        return "No se pudo obtener HWND"
    try:
        _WIN32.SetWindowLongW(hwnd, GWL_EXSTYLE, _WIN32.GetWindowLongW(hwnd, GWL_EXSTYLE) | WS_EX_LAYERED)
        _WIN32.SetLayeredWindowAttributes(hwnd, 0, opacity, LWA_ALPHA)
        pct = int(opacity / 255 * 100)
        return "Opacidad de '{}' = {}%".format(w.title[:40], pct)
    except Exception as e:
        return "Error: {}".format(str(e))


def _minimize_all() -> str:
    count = 0
    for w in gw.getAllWindows():
        if w.title.strip() and w.width > 50 and w.height > 50 and not w.isMinimized:
            try:
                hwnd = _get_hwnd(w)
                if hwnd:
                    _WIN32.ShowWindow(hwnd, SW_MINIMIZE)
                    count += 1
            except Exception:
                pass
    _track_action("minimized", "ALL", "{} ventanas".format(count))
    return "Minimizadas {} ventanas".format(count)


def _restore_all() -> str:
    count = 0
    for w in gw.getAllWindows():
        if w.title.strip() and w.isMinimized:
            try:
                hwnd = _get_hwnd(w)
                if hwnd:
                    _WIN32.ShowWindow(hwnd, SW_RESTORE)
                    count += 1
            except Exception:
                pass
    state = _load_state()
    state["minimized"] = []
    _save_state(state)
    return "Restauradas {} ventanas".format(count)


def _cascade_windows() -> str:
    visible = [w for w in gw.getAllWindows()
               if w.title.strip() and w.width > 100 and w.height > 80 and not w.isMinimized]
    if not visible:
        return "No hay ventanas para cascada"
    offset = 40
    for i, w in enumerate(visible[:10]):
        hwnd = _get_hwnd(w)
        if hwnd:
            _WIN32.SetWindowPos(hwnd, 0, 50 + i * offset, 50 + i * offset,
                                w.width, w.height, 0x0001 | 0x0002 | 0x0040)
    return "Cascada: {} ventanas".format(min(len(visible), 10))


def _tile_horizontal() -> str:
    visible = [w for w in gw.getAllWindows()
               if w.title.strip() and w.width > 100 and w.height > 80 and not w.isMinimized]
    if not visible:
        return "No hay ventanas para tiles"
    import pyautogui
    screen_w, screen_h = pyautogui.size()
    n = min(len(visible), 4)
    h = screen_h // n
    for i, w in enumerate(visible[:n]):
        hwnd = _get_hwnd(w)
        if hwnd:
            _WIN32.SetWindowPos(hwnd, 0, 0, i * h, screen_w, h, 0x0001 | 0x0002 | 0x0040)
    return "Tile horizontal: {} ventanas".format(n)


def _tile_vertical() -> str:
    visible = [w for w in gw.getAllWindows()
               if w.title.strip() and w.width > 100 and w.height > 80 and not w.isMinimized]
    if not visible:
        return "No hay ventanas para tiles"
    import pyautogui
    screen_w, screen_h = pyautogui.size()
    n = min(len(visible), 4)
    w_size = screen_w // n
    for i, win in enumerate(visible[:n]):
        hwnd = _get_hwnd(win)
        if hwnd:
            _WIN32.SetWindowPos(hwnd, 0, i * w_size, 0, w_size, screen_h, 0x0001 | 0x0002 | 0x0040)
    return "Tile vertical: {} ventanas".format(n)


def _get_foreground() -> str:
    hwnd = _WIN32.GetForegroundWindow()
    if not hwnd:
        return "No hay ventana activa"
    length = _WIN32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(length + 1)
    _WIN32.GetWindowTextW(hwnd, buf, length + 1)
    title = buf.value
    return "Ventana activa: '{}'".format(title[:80])


def _get_status() -> str:
    visible = [w for w in gw.getAllWindows() if w.title.strip() and w.width > 50 and w.height > 50]
    minimized = sum(1 for w in visible if w.isMinimized)
    maximized = sum(1 for w in visible if w.isMaximized)
    foreground = _get_foreground()
    state = _load_state()
    opened_count = len(state.get("opened", []))
    minimized_count = len(state.get("minimized", []))
    closed_count = len(state.get("closed", []))
    lines = [
        "═══ DESKTOP STATUS ═══",
        "",
        "  Ventanas:       {} total".format(len(visible)),
        "  Minimizadas:    {}".format(minimized),
        "  Maximizadas:    {}".format(maximized),
        "  Normales:       {}".format(len(visible) - minimized - maximized),
        "  {}".format(foreground),
        "",
        "═══ MI MEMORIA ═══",
        "",
        "  Apps abiertas:  {}".format(opened_count),
        "  Apps minimizadas: {}".format(minimized_count),
        "  Apps cerradas:  {}".format(closed_count),
    ]
    return "\n".join(lines)


def _open_app(params: dict) -> str:
    app = params.get("app", "")
    if not app:
        return "Error: se requiere 'app'"
    before_hwnds = set()
    for w in gw.getAllWindows():
        hwnd = _get_hwnd(w)
        if hwnd:
            before_hwnds.add(hwnd)
    try:
        subprocess.Popen([app], shell=True)
        window = _wait_for_window(app, before_hwnds=before_hwnds, timeout=5.0)
        if window:
            _track_action("opened", app, window.title, "ventana encontrada")
            _log_action("open_app", app, "OK -> '{}'".format(window.title[:40]))
            return "Abierto '{}' -> ventana: '{}'".format(app, window.title[:50])
        else:
            _track_action("opened", app, app, "lanzado")
            _log_action("open_app", app, "OK (sin confirmacion)")
            return "Lanzado '{}'".format(app)
    except Exception as e:
        return "Error abriendo '{}': {}".format(app, str(e))


def _close_app(params: dict) -> str:
    app = params.get("app", "")
    if not app:
        return "Error: se requiere 'app'"
    windows_before = _find_windows(app)
    if not windows_before:
        base = app.replace(".exe", "").replace(".EXE", "")
        aliases = {
            "notepad": "bloc de notas",
            "calc": "calculadora",
            "mspaint": "paint",
            "calculatorapp": "calculadora",
        }
        alias = aliases.get(base.lower(), base)
        windows_before = _find_windows(alias)
    window_titles = [w.title[:50] for w in windows_before]
    variants = [app]
    if not app.lower().endswith(".exe"):
        variants.append(app + ".exe")
    base = app.replace(".exe", "").replace(".EXE", "")
    if base != app:
        variants.append(base)
    variants.append(base + ".exe")
    uwp_map = {
        "calc": ["CalculatorApp.exe"],
        "notepad": ["Notepad.exe"],
        "mspaint": ["mspaint.exe"],
        "snippingtool": ["SnippingTool.exe"],
    }
    for key, exes in uwp_map.items():
        if key in base.lower():
            variants.extend(exes)
    variants = list(dict.fromkeys(variants))
    for variant in variants:
        try:
            result = subprocess.run(
                ["taskkill", "/IM", variant, "/F"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                time.sleep(0.5)
                for t in window_titles:
                    _track_action("closed", app, t, "taskkill exitoso")
                if not window_titles:
                    _track_action("closed", app, app, "taskkill exitoso (sin ventana detectada)")
                _log_action("close_app", app, "OK ({} ventanas)".format(len(window_titles)))
                if window_titles:
                    return "Cerrado '{}' ({} ventana(s): {})".format(
                        app, len(window_titles), ", ".join(window_titles[:3]))
                return "Cerrado '{}'".format(app)
        except Exception:
            pass
    return "No se pudo cerrar '{}' (proceso no encontrado)".format(app)


def _list_running_apps() -> str:
    try:
        result = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=10
        )
        lines_map = {}
        for line in result.stdout.strip().split("\n"):
            parts = line.strip('"').split('","')
            if len(parts) >= 2:
                name = parts[0]
                if name not in lines_map:
                    lines_map[name] = 0
                lines_map[name] += 1
        sorted_apps = sorted(lines_map.items(), key=lambda x: x[1], reverse=True)
        lines = ["═══ APLICACIONES EN EJECUCION ({}) ═══".format(len(sorted_apps)), ""]
        for name, count in sorted_apps[:30]:
            suffix = " (x{})".format(count) if count > 1 else ""
            lines.append("  {}{}".format(name, suffix))
        return "\n".join(lines)
    except Exception as e:
        return "Error: {}".format(str(e))


def _get_state() -> str:
    state = _load_state()
    opened = state.get("opened", [])
    minimized = state.get("minimized", [])
    closed = state.get("closed", [])
    lines = ["═══ ESTADO DE ESCRITORIO ═══", ""]
    lines.append("  Abiertas:     {}".format(len(opened)))
    lines.append("  Minimizadas:  {}".format(len(minimized)))
    lines.append("  Cerradas:     {}".format(len(closed)))
    lines.append("")
    if opened:
        lines.append("─── ABIERTAS RECIENTEMENTE ───")
        for o in opened[-10:]:
            lines.append("  [{}] '{}' ({})".format(
                o.get("time", "?")[:16], o.get("title", "?")[:40], o.get("app", "?")))
    if minimized:
        lines.append("")
        lines.append("─── MINIMIZADAS ───")
        for m in minimized[-10:]:
            lines.append("  [{}] '{}'".format(
                m.get("time", "?")[:16], m.get("title", "?")[:40]))
    if closed:
        lines.append("")
        lines.append("─── CERRADAS RECIENTEMENTE ───")
        for c in closed[-10:]:
            lines.append("  [{}] '{}'".format(
                c.get("time", "?")[:16], c.get("title", "?")[:40]))
    return "\n".join(lines)


def _get_opened() -> str:
    state = _load_state()
    opened = state.get("opened", [])
    if not opened:
        return "No he abierto ninguna app esta sesion"
    lines = ["═══ APPS QUE YO ABRI ({}) ═══".format(len(opened)), ""]
    for o in opened[-15:]:
        lines.append("  [{}] '{}' -> {}".format(
            o.get("time", "?")[:16], o.get("app", "?"), o.get("title", "?")[:40]))
    return "\n".join(lines)


def _get_minimized() -> str:
    state = _load_state()
    minimized = state.get("minimized", [])
    if not minimized:
        return "No he minimizado ninguna ventana"
    lines = ["═══ VENTANAS QUE YO MINIMICE ({}) ═══".format(len(minimized)), ""]
    for m in minimized[-15:]:
        lines.append("  [{}] '{}'".format(
            m.get("time", "?")[:16], m.get("title", "?")[:50]))
    return "\n".join(lines)


def _get_closed() -> str:
    state = _load_state()
    closed = state.get("closed", [])
    if not closed:
        return "No he cerrado ninguna ventana"
    lines = ["═══ VENTANAS QUE YO CERRE ({}) ═══".format(len(closed)), ""]
    for c in closed[-15:]:
        lines.append("  [{}] '{}'".format(
            c.get("time", "?")[:16], c.get("title", "?")[:50]))
    return "\n".join(lines)


def _is_open(params: dict) -> str:
    app = params.get("app", "")
    if not app:
        return "Error: se requiere 'app'"
    matches = _find_windows(app)
    if matches:
        titles = [w.title[:50] for w in matches]
        return "'{}' ESTA ABIERTA ({} ventana(s): {})".format(
            app, len(titles), ", ".join(titles))
    base = app.replace(".exe", "").replace(".EXE", "")
    aliases = {
        "notepad": "bloc de notas",
        "calc": "calculadora",
        "mspaint": "paint",
    }
    alias = aliases.get(base.lower(), base)
    matches = _find_windows(alias)
    if matches:
        titles = [w.title[:50] for w in matches]
        return "'{}' ESTA ABIERTA ({} ventana(s): {})".format(
            app, len(titles), ", ".join(titles))
    try:
        result = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.strip().split("\n"):
            parts = line.strip('"').split('","')
            if parts and base.lower() in parts[0].lower():
                return "'{}' ESTA ABIERTA (proceso: {})".format(app, parts[0])
    except Exception:
        pass
    return "'{}' NO esta abierta".format(app)


def _what_did_i_do(params: dict) -> str:
    period = params.get("period", "all")
    state = _load_state()
    opened = state.get("opened", [])
    minimized = state.get("minimized", [])
    closed = state.get("closed", [])
    if period == "last_hour":
        cutoff = datetime.now().timestamp() - 3600
        opened = [o for o in opened if _parse_time(o.get("time", "")) > cutoff]
        minimized = [m for m in minimized if _parse_time(m.get("time", "")) > cutoff]
        closed = [c for c in closed if _parse_time(c.get("time", "")) > cutoff]
    elif period == "last_5min":
        cutoff = datetime.now().timestamp() - 300
        opened = [o for o in opened if _parse_time(o.get("time", "")) > cutoff]
        minimized = [m for m in minimized if _parse_time(m.get("time", "")) > cutoff]
        closed = [c for c in closed if _parse_time(c.get("time", "")) > cutoff]
    total = len(opened) + len(minimized) + len(closed)
    lines = ["═══ QUE HICE EN EL ESCRITORIO ({}) ═══".format(period), ""]
    if not total:
        lines.append("  No hice nada en el escritorio recientemente.")
        return "\n".join(lines)
    if opened:
        lines.append("  ABRI {} app(s):".format(len(opened)))
        for o in opened[-5:]:
            lines.append("    - '{}' ({})".format(o.get("app", "?"), o.get("title", "?")[:35]))
    if minimized:
        lines.append("")
        lines.append("  MINIMICE {} ventana(s):".format(len(minimized)))
        for m in minimized[-5:]:
            lines.append("    - '{}'".format(m.get("title", "?")[:50]))
    if closed:
        lines.append("")
        lines.append("  CERRE {} ventana(s):".format(len(closed)))
        for c in closed[-5:]:
            lines.append("    - '{}'".format(c.get("title", "?")[:50]))
    return "\n".join(lines)


def _clear_state() -> str:
    _save_state({"opened": [], "minimized": [], "closed": [], "sessions": []})
    return "Memoria de escritorio limpiada"


def _parse_time(ts: str) -> float:
    try:
        return datetime.fromisoformat(ts).timestamp()
    except Exception:
        return 0.0


def _get_history() -> str:
    history = _load_history()
    if not history:
        return "Sin historial de acciones de escritorio"
    lines = ["═══ HISTORIAL DE ESCRITORIO ═══", ""]
    for h in history[-15:]:
        lines.append("  [{}] {} -> '{}' ({})".format(
            h.get("timestamp", "?")[:19],
            h.get("action", "?"),
            h.get("target", "?")[:40],
            h.get("result", "?")[:30]))
    return "\n".join(lines)


def _load_history() -> list:
    if _HISTORY_FILE.exists():
        try:
            return json.loads(_HISTORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def _save_history(history: list):
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    _HISTORY_FILE.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")
