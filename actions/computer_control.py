# -*- coding: utf-8 -*-
"""computer_control.py — Full native computer control for ERIS.
Smooth Bezier scrolling, natural mouse movement, tab tracking."""
import os
import time
import math
import random
import subprocess
import json
try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.02
except Exception:
    pyautogui = None  # type: ignore[assignment]  # sin X11 (Wayland) no abre display
import pyperclip
try:
    import pygetwindow as gw
except Exception:
    gw = None  # type: ignore[assignment]  # pygetwindow no soporta Linux

_TABS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "open_tabs.json")
_open_tabs = []


def _load_tabs():
    global _open_tabs
    try:
        if os.path.exists(_TABS_FILE):
            _open_tabs = json.loads(open(_TABS_FILE, "r", encoding="utf-8").read())
    except Exception:
        _open_tabs = []


def _save_tabs():
    try:
        os.makedirs(os.path.dirname(_TABS_FILE), exist_ok=True)
        with open(_TABS_FILE, "w", encoding="utf-8") as f:
            json.dump(_open_tabs[-50:], f, ensure_ascii=False, indent=1)
    except Exception:
        pass


def _track_tab(title, url="", action="open"):
    global _open_tabs
    if not _open_tabs:
        _load_tabs()
    _open_tabs.append({
        "title": title[:80],
        "url": url[:200],
        "action": action,
        "time": __import__("datetime").datetime.now().isoformat(),
    })
    _save_tabs()


def _bezier_scroll(direction, amount, duration=0.6):
    total_clicks = int(amount) * 4
    steps = max(8, total_clicks // 2)
    t_values = [_ease_out_cubic(i / steps) for i in range(steps + 1)]

    for i in range(steps):
        progress = t_values[i + 1] - t_values[i]
        scroll_amount = max(1, int(total_clicks * progress))
        if direction == "up":
            pyautogui.scroll(scroll_amount)
        else:
            pyautogui.scroll(-scroll_amount)
        time.sleep(duration / steps * (1.0 + random.uniform(-0.1, 0.1)))


def _ease_out_cubic(t):
    return 1 - pow(1 - t, 3)


def _ease_in_out_quad(t):
    if t < 0.5:
        return 2 * t * t
    else:
        return 1 - pow(-2 * t + 2, 2) / 2


def _smooth_move(x, y, duration=0.4):
    start_x, start_y = pyautogui.position()
    dx = int(x) - start_x
    dy = int(y) - start_y
    dist = math.sqrt(dx * dx + dy * dy)
    steps = max(10, int(dist / 15))
    cp1x = start_x + dx * 0.3 + random.randint(-20, 20)
    cp1y = start_y + dy * 0.1 + random.randint(-10, 10)
    cp2x = start_x + dx * 0.7 + random.randint(-10, 10)
    cp2y = start_y + dy * 0.9 + random.randint(-5, 5)

    for i in range(steps + 1):
        t = i / steps
        t_ease = _ease_in_out_quad(t)
        inv = 1 - t_ease
        px = inv ** 3 * start_x + 3 * inv ** 2 * t_ease * cp1x + 3 * inv * t_ease ** 2 * cp2x + t_ease ** 3 * int(x)
        py = inv ** 3 * start_y + 3 * inv ** 2 * t_ease * cp1y + 3 * inv * t_ease ** 2 * cp2y + t_ease ** 3 * int(y)
        pyautogui.moveTo(int(px), int(py))
        time.sleep(duration / steps)


def computer_control(parameters: dict, player=None) -> str:
    action = parameters.get("action", "").lower().strip()
    text = parameters.get("text", "")
    key = parameters.get("key", "")
    keys = parameters.get("keys", "")
    x = parameters.get("x", None)
    y = parameters.get("y", None)
    direction = parameters.get("direction", "down").lower()
    amount = int(parameters.get("amount", 3))
    seconds = float(parameters.get("seconds", 1))
    path = parameters.get("path", "")
    title = parameters.get("title", "")
    url = parameters.get("url", "")
    description = parameters.get("description", "")
    field = parameters.get("field", "")
    clear_first = parameters.get("clear_first", True)
    smooth = parameters.get("smooth", True)

    if not action:
        return "Error: No se especifico accion."

    try:
        if action in ("type", "smart_type"):
            return _type_text(text, clear_first)
        elif action == "open_and_type":
            return _open_app_and_type(parameters.get("app", ""), text)
        elif action == "press":
            return _press_key(key)
        elif action == "hotkey":
            return _hotkey(keys)
        elif action == "click":
            if smooth and x is not None and y is not None:
                _smooth_move(x, y, 0.3)
            return _click(x, y)
        elif action == "double_click":
            if smooth and x is not None and y is not None:
                _smooth_move(x, y, 0.3)
            return _double_click(x, y)
        elif action == "right_click":
            if smooth and x is not None and y is not None:
                _smooth_move(x, y, 0.3)
            return _right_click(x, y)
        elif action == "scroll":
            return _scroll(direction, amount, smooth)
        elif action == "scroll_up":
            return _scroll("up", amount, smooth)
        elif action == "scroll_down":
            return _scroll("down", amount, smooth)
        elif action == "scroll_to_top":
            for _ in range(8):
                _bezier_scroll("up", 8, 0.3)
            return "Scroll al inicio (suave)."
        elif action == "scroll_to_bottom":
            for _ in range(8):
                _bezier_scroll("down", 8, 0.3)
            return "Scroll al final (suave)."
        elif action == "scroll_page_up":
            _bezier_scroll("up", 12, 0.4)
            return "Page Up suave."
        elif action == "scroll_page_down":
            _bezier_scroll("down", 12, 0.4)
            return "Page Down suave."
        elif action == "smooth_scroll":
            return _smooth_scroll(amount, duration=float(parameters.get("duration", 1.0)))
        elif action == "drag":
            return _drag(x, y, parameters.get("end_x"), parameters.get("end_y"), seconds)
        elif action == "get_mouse_pos":
            pos = pyautogui.position()
            return "Mouse en ({}, {})".format(pos.x, pos.y)
        elif action == "move":
            if smooth:
                _smooth_move(x, y, seconds)
                return "Mouse movido suavemente a ({}, {}).".format(x, y)
            return _move_mouse(x, y, seconds)
        elif action == "copy":
            pyautogui.hotkey("ctrl", "c")
            return "Copiado."
        elif action == "paste":
            pyautogui.hotkey("ctrl", "v")
            return "Pegado."
        elif action == "screenshot":
            return _screenshot(path)
        elif action == "wait":
            time.sleep(seconds)
            return "Esperado {}s.".format(seconds)
        elif action == "clear_field":
            return _clear_field()
        elif action == "focus_window":
            return _focus_window(title)
        elif action == "open_tab":
            return _open_tab(url, title)
        elif action == "close_tab":
            return _close_tab(title)
        elif action == "close_current_tab":
            return _close_current_tab()
        elif action == "list_tabs":
            return _list_tabs()
        elif action == "track_tab":
            _track_tab(title, url, "manual")
            return "Tab registrada: '{}'".format(title[:50])
        elif action == "get_tab_info":
            return _get_tab_info(title)
        elif action == "switch_tab":
            return _switch_tab(int(parameters.get("tab_index", 1)))
        elif action == "next_tab":
            pyautogui.hotkey("ctrl", "tab")
            return "Siguiente pestana."
        elif action == "prev_tab":
            pyautogui.hotkey("ctrl", "shift", "tab")
            return "Pestana anterior."
        elif action == "new_tab":
            pyautogui.hotkey("ctrl", "t")
            time.sleep(0.3)
            return "Nueva pestana abierta."
        elif action == "select_all":
            pyautogui.hotkey("ctrl", "a")
            return "Todo seleccionado."
        elif action == "undo":
            pyautogui.hotkey("ctrl", "z")
            return "Deshacer ejecutado."
        elif action == "redo":
            pyautogui.hotkey("ctrl", "y")
            return "Rehacer ejecutado."
        elif action == "save":
            pyautogui.hotkey("ctrl", "s")
            return "Guardado (Ctrl+S)."
        elif action == "enter":
            pyautogui.press("enter")
            return "Enter presionado."
        elif action == "tab":
            pyautogui.press("tab")
            return "Tab presionado."
        elif action == "escape":
            pyautogui.press("escape")
            return "Escape presionado."
        elif action == "backspace":
            pyautogui.press("backspace")
            return "Backspace presionado."
        elif action == "delete":
            pyautogui.press("delete")
            return "Delete presionado."
        elif action == "home":
            pyautogui.press("home")
            return "Home presionado."
        elif action == "end":
            pyautogui.press("end")
            return "End presionado."
        elif action == "pageup":
            _bezier_scroll("up", 15, 0.5)
            return "Page Up suave."
        elif action == "pagedown":
            _bezier_scroll("down", 15, 0.5)
            return "Page Down suave."
        elif action == "escape_all":
            pyautogui.hotkey("alt", "f4")
            return "Ventana cerrada (Alt+F4)."
        elif action == "random_data":
            return _random_data(parameters.get("type", "name"))
        elif action == "user_data":
            return _user_data(field)
        elif action == "screen_find":
            return _screen_find(description)
        elif action == "screen_click":
            return _screen_click(description)
        else:
            return "Accion '{}' no reconocida.".format(action)

    except Exception as e:
        return "Error en computer_control: {}".format(str(e)[:100])


def _open_app_and_type(app_name: str, text: str) -> str:
    if not app_name:
        return "Error: Necesito el nombre de la app (ej: 'notepad', 'bloc de notas')."
    if not text:
        return "Error: Necesito el texto a escribir."

    app_map = {
        "notepad": "notepad.exe", "bloc de notas": "notepad.exe", "block de notas": "notepad.exe",
        "bloc": "notepad.exe", "block": "notepad.exe",
        "calc": "calc.exe", "calculadora": "calc.exe",
        "cmd": "cmd.exe", "simbolo del sistema": "cmd.exe", "terminal": "cmd.exe",
        "powershell": "powershell.exe",
        "word": "winword.exe", "wordpad": "write.exe",
        "excel": "excel.exe",
        "paint": "mspaint.exe", "pintura": "mspaint.exe",
        "explorer": "explorer.exe", "explorador": "explorer.exe",
        "chrome": "chrome.exe", "edge": "msedge.exe", "firefox": "firefox.exe",
    }

    exe = app_map.get(app_name.lower().strip(), app_name)
    try:
        subprocess.Popen(exe, shell=False)
    except Exception:
        try:
            os.startfile(exe)
        except Exception as e:
            return f"No pude abrir '{app_name}': {str(e)[:80]}"

    # Wait for window to appear and focus it
    keywords = [exe.replace(".exe", "").lower(), app_name.lower(),
                "bloc de notas", "notepad", "sin título", "calculadora", "paint",
                "word", "excel", "powershell", "símbolo"]

    time.sleep(0.5)
    for attempt in range(15):
        time.sleep(0.3)
        all_wins = gw.getAllWindows()
        target = None
        for w in all_wins:
            if not w.visible or not w.title:
                continue
            for kw in keywords:
                if kw in w.title.lower():
                    target = w
                    break
            if target:
                break
        if target:
            try:
                if target.isMinimized:
                    target.restore()
                target.activate()
                time.sleep(0.5)
                pyperclip.copy(text)
                time.sleep(0.1)
                pyautogui.hotkey("ctrl", "v")
                return "Abierto '{}' y escrito el texto en la ventana.".format(app_name)
            except Exception:
                continue

    # Fallback: just type
    time.sleep(0.5)
    pyperclip.copy(text)
    time.sleep(0.1)
    pyautogui.hotkey("ctrl", "v")
    return "Abierto '{}'. Se intentó escribir.".format(app_name)


def _type_text(text: str, clear_first: bool = False) -> str:
    if not text:
        return "Error: No se proporciono texto."
    if clear_first:
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.05)
    pyperclip.copy(text)
    time.sleep(0.03)
    pyautogui.hotkey("ctrl", "v")
    return "Texto escrito: '{}'.".format(text[:50] + ("..." if len(text) > 50 else ""))


def _press_key(key: str) -> str:
    if not key:
        return "Error: No se proporciono tecla."
    pyautogui.press(key.lower())
    return "Tecla '{}' presionada.".format(key)


def _hotkey(keys: str) -> str:
    if not keys:
        return "Error: No se proporciono combinacion."
    k_list = [k.strip().lower() for k in keys.replace(",", "+").split("+") if k.strip()]
    if not k_list:
        return "Error: Combinacion vacia."
    pyautogui.hotkey(*k_list)
    return "Atajo: {}.".format(keys)


def _click(x=None, y=None) -> str:
    if x is not None and y is not None:
        pyautogui.click(int(x), int(y))
        return "Clic en ({}, {}).".format(x, y)
    pyautogui.click()
    return "Clic izquierdo."


def _double_click(x=None, y=None) -> str:
    if x is not None and y is not None:
        pyautogui.doubleClick(int(x), int(y))
        return "Doble clic en ({}, {}).".format(x, y)
    pyautogui.doubleClick()
    return "Doble clic."


def _right_click(x=None, y=None) -> str:
    if x is not None and y is not None:
        pyautogui.rightClick(int(x), int(y))
        return "Clic derecho en ({}, {}).".format(x, y)
    pyautogui.rightClick()
    return "Clic derecho."


def _scroll(direction: str, amount: int, smooth: bool = True) -> str:
    if smooth:
        _bezier_scroll(direction, amount, 0.5)
        return "Scroll {} ({} unidades, suave).".format(
            "arriba" if direction == "up" else "abajo", amount)
    else:
        clicks = int(amount) * 4
        if direction == "up":
            pyautogui.scroll(clicks)
        else:
            pyautogui.scroll(-clicks)
        return "Scroll {} ({} unidades).".format(
            "arriba" if direction == "up" else "abajo", amount)


def _smooth_scroll(amount: int, duration: float = 1.0) -> str:
    total = int(amount) * 4
    steps = max(15, total // 2)
    for i in range(steps):
        t = i / steps
        speed = math.sin(t * math.pi)
        scroll_amt = max(1, int(total / steps * speed * 1.5))
        pyautogui.scroll(scroll_amt)
        time.sleep(duration / steps)
    return "Scroll fluido completado ({} unidades).".format(amount)


def _move_mouse(x, y, duration: float = 0.5) -> str:
    if x is None or y is None:
        return "Error: Se requieren x, y."
    pyautogui.moveTo(int(x), int(y), duration=duration)
    return "Mouse movido a ({}, {}).".format(x, y)


def _drag(x=None, y=None, end_x=None, end_y=None, duration: float = 0.5) -> str:
    if x is None or y is None or end_x is None or end_y is None:
        return "Error: Se requieren x, y, end_x, end_y."
    _smooth_move(x, y, 0.2)
    pyautogui.mouseDown()
    _smooth_move(end_x, end_y, duration)
    pyautogui.mouseUp()
    return "Arrastrado de ({},{}) a ({},{}).".format(x, y, end_x, end_y)


def _screenshot(save_path: str = "") -> str:
    if not save_path:
        save_path = os.path.join(os.path.expanduser("~"), "Desktop", "screenshot.png")
    img = pyautogui.screenshot()
    img.save(save_path)
    return "Screenshot guardada en: {}".format(save_path)


def _clear_field() -> str:
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.05)
    pyautogui.press("delete")
    return "Campo limpiado."


def _focus_window(title: str) -> str:
    if not title:
        return "Error: Se requiere titulo de ventana."
    try:
        import pygetwindow as gw
        windows = gw.getWindowsWithTitle(title)
        if not windows:
            return "No se encontro ventana con '{}'.".format(title)
        win = windows[0]
        if win.isMinimized:
            win.restore()
        win.activate()
        time.sleep(0.3)
        return "Ventana '{}' enfocada.".format(win.title[:50])
    except Exception as e:
        return "Error enfocando ventana: {}".format(str(e)[:60])


def _open_tab(url: str, title: str = "") -> str:
    if not url:
        return "Error: especifica la URL."
    if not url.startswith("http"):
        url = "https://" + url
    import webbrowser
    webbrowser.open(url)
    tab_title = title or url[:60]
    _track_tab(tab_title, url, "open")
    return "Pestana abierta: {}".format(tab_title[:60])


def _close_tab(title: str = "") -> str:
    if title:
        _track_tab(title, "", "closed")
    pyautogui.hotkey("ctrl", "w")
    time.sleep(0.3)
    return "Pestana cerrada{}.".format(": " + title[:40] if title else "")


def _close_current_tab() -> str:
    pyautogui.hotkey("ctrl", "w")
    time.sleep(0.3)
    return "Pestana actual cerrada."


def _list_tabs() -> str:
    if not _open_tabs:
        _load_tabs()
    if not _open_tabs:
        return "Sin pestanas registradas."
    lines = ["═══ PESTANAS REGISTRADAS ═══", ""]
    recent = {}
    for t in _open_tabs:
        key = t.get("title", "")[:50]
        recent[key] = t
    for i, (key, tab) in enumerate(list(recent.items())[-15:], 1):
        status = "ABIERTA" if tab.get("action") != "closed" else "CERRADA"
        lines.append("  {:2d}. [{}] {} {}".format(
            i, status, tab.get("title", "?")[:45],
            "({})".format(tab.get("url", "")[:30]) if tab.get("url") else ""))
    return "\n".join(lines)


def _get_tab_info(title: str = "") -> str:
    if not _open_tabs:
        _load_tabs()
    if not _open_tabs:
        return "Sin pestanas registradas."
    if title:
        matches = [t for t in _open_tabs if title.lower() in t.get("title", "").lower()]
        if matches:
            tab = matches[-1]
            return "Pestana: {}\nURL: {}\nAccion: {}\nHora: {}".format(
                tab.get("title", "?"), tab.get("url", "?"),
                tab.get("action", "?"), tab.get("time", "?")[:16])
        return "No encontre pestana con '{}'.".format(title[:30])
    last = _open_tabs[-1]
    return "Ultima pestana: {} ({})".format(last.get("title", "?"), last.get("action", "?"))


def _switch_tab(index: int) -> str:
    for _ in range(index - 1):
        pyautogui.hotkey("ctrl", "tab")
        time.sleep(0.15)
    return "Cambiado a pestana #{}.".format(index)


def _screen_find(description: str) -> str:
    if not description:
        return "Error: Se requiere descripcion."
    return "Para encontrar '{}', usa screen_vision o visual_click.".format(description)


def _screen_click(description: str) -> str:
    if not description:
        return "Error: Se requiere descripcion."
    return "Para cliquear '{}', usa visual_click con la descripcion.".format(description)


def _random_data(data_type: str = "name") -> str:
    names = ["Carlos", "Maria", "Juan", "Ana", "Pedro", "Laura", "Diego", "Sofia"]
    emails = ["@gmail.com", "@hotmail.com", "@outlook.com", "@yahoo.com"]
    cities = ["Bogota", "Medellin", "Cali", "Barranquilla", "Bucaramanga"]

    if data_type == "name":
        return random.choice(names)
    elif data_type == "email":
        return random.choice(names).lower() + random.choice(emails)
    elif data_type == "city":
        return random.choice(cities)
    elif data_type == "number":
        return str(random.randint(1000, 99999))
    elif data_type == "phone":
        return "+57 {}{}".format(random.randint(300, 399), random.randint(1000000, 9999999))
    return str(random.randint(1, 1000))


def _user_data(field: str) -> str:
    profile_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "config", "user_profile.json"
    )
    try:
        profile = json.loads(open(profile_path, "r", encoding="utf-8").read())
        field_map = {
            "name": "name", "email": "email", "city": "city",
            "telefono": "phone", "phone": "phone",
        }
        key = field_map.get(field.lower(), field.lower())
        return str(profile.get(key, "Campo '{}' no encontrado en perfil.".format(field)))
    except Exception:
        return "Perfil de usuario no encontrado."
