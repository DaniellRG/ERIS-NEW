"""
human_mouse.py — Human-like mouse movements for ERIS.
Moves the cursor with natural curves (bezier), variable speed,
overshoot, pauses, and human-like scroll behavior.
"""
from __future__ import annotations

import math
import random
import time
from typing import Callable

try:
    import pyautogui
    _PYAUTOGUI = True
except ImportError:
    _PYAUTOGUI = False

# ── Bezier helpers ───────────────────────────────────────────────────────────

def _bezier_point(t: float, points: list[tuple[float, float]]) -> tuple[float, float]:
    """Evaluate cubic bezier at t (0..1)."""
    n = len(points) - 1
    x, y = 0.0, 0.0
    for i, (px, py) in enumerate(points):
        coeff = math.comb(n, i) * (t ** i) * ((1 - t) ** (n - i))
        x += coeff * px
        y += coeff * py
    return x, y


def _human_bezier_path(x1: float, y1: float, x2: float, y2: float,
                       steps: int = 40) -> list[tuple[float, float]]:
    """Generate a bezier curve path that looks human-made.
    
    Control points create a natural curve with slight overshoot
    and random variation.
    """
    dx = x2 - x1
    dy = y2 - y1
    dist = math.hypot(dx, dy)

    # Control point 1: slightly pulled toward direction with randomness
    cp1 = (
        x1 + dx * 0.25 + random.uniform(-dist * 0.1, dist * 0.1),
        y1 + dy * 0.25 + random.uniform(-dist * 0.1, dist * 0.1),
    )
    # Control point 2: slight overshoot
    overshoot = 1.0 + random.uniform(0.0, 0.08)
    cp2 = (
        x1 + dx * overshoot + random.uniform(-dist * 0.05, dist * 0.05),
        y1 + dy * overshoot + random.uniform(-dist * 0.05, dist * 0.05),
    )

    pts = [(x1, y1), cp1, cp2, (x2, y2)]

    path = []
    for i in range(steps + 1):
        t = i / steps
        px, py = _bezier_point(t, pts)
        path.append((px, py))

    # Add micro-jitter (hand tremor)
    jittered = []
    for px, py in path:
        jx = px + random.uniform(-0.5, 0.5)
        jy = py + random.uniform(-0.5, 0.5)
        jittered.append((jx, jy))
    return jittered


# ── Speed profiles ───────────────────────────────────────────────────────────

_SPEED_PROFILES = {
    "instant": {"base_delay": 0.0003, "jitter": 0.0002, "steps": 5},
    "smooth":  {"base_delay": 0.0008, "jitter": 0.0003, "steps": 80},
    "fast":    {"base_delay": 0.0015, "jitter": 0.0005, "steps": 40},
    "normal":  {"base_delay": 0.0030, "jitter": 0.0010, "steps": 50},
    "slow":    {"base_delay": 0.0060, "jitter": 0.0020, "steps": 60},
    "careful": {"base_delay": 0.0100, "jitter": 0.0040, "steps": 70},
}


# ── Public API ───────────────────────────────────────────────────────────────

def move_to(x: int, y: int, speed: str = "normal") -> str:
    """Move mouse to (x, y) with human-like bezier curve."""
    if not _PYAUTOGUI:
        return "Error: pyautogui no instalado."
    try:
        cx, cy = pyautogui.position()
        profile = _SPEED_PROFILES.get(speed, _SPEED_PROFILES["normal"])
        path = _human_bezier_path(cx, cy, float(x), float(y), steps=profile["steps"])

        for px, py in path:
            pyautogui.moveTo(int(px), int(py), _pause=False)
            delay = profile["base_delay"] + random.uniform(-profile["jitter"], profile["jitter"])
            time.sleep(max(0.0005, delay))

        return f"Mouse movido a ({x}, {y}) como humano."
    except Exception as e:
        return f"Error moviendo mouse: {e}"


def click(x: int | None = None, y: int | None = None,
          button: str = "left", clicks: int = 1) -> str:
    """Click with human-like pre/post pauses."""
    if not _PYAUTOGUI:
        return "Error: pyautogui no instalado."
    try:
        if x is not None and y is not None:
            r = move_to(x, y)
            if r.startswith("Error"):
                return r

        # Pause before click (human reaction)
        time.sleep(random.uniform(0.05, 0.2))

        # Click with micro-movement (human tremor)
        for _ in range(clicks):
            pyautogui.click(button=button)
            if clicks > 1:
                time.sleep(random.uniform(0.05, 0.15))

        # Pause after click
        time.sleep(random.uniform(0.02, 0.1))

        return f"Click {button} {'en (' + str(x) + ',' + str(y) + ')' if x is not None else ''}."
    except Exception as e:
        return f"Error en click: {e}"


def double_click(x: int | None = None, y: int | None = None) -> str:
    return click(x, y, "left", 2)


def right_click(x: int | None = None, y: int | None = None) -> str:
    return click(x, y, "right", 1)


def scroll(direction: str = "down", amount: int = 3) -> str:
    """Scroll with human-like variable intervals."""
    if not _PYAUTOGUI:
        return "Error: pyautogui no instalado."
    try:
        for i in range(amount):
            # Variable scroll amount per tick (human-like)
            tick = random.randint(1, 3)
            if direction == "up":
                pyautogui.scroll(tick)
            elif direction == "down":
                pyautogui.scroll(-tick)
            elif direction == "left":
                pyautogui.hscroll(-tick)
            elif direction == "right":
                pyautogui.hscroll(tick)
            # Pause between scrolls varies (human reading)
            time.sleep(random.uniform(0.1, 0.4))
        return f"Scroll {direction} ({amount} veces)."
    except Exception as e:
        return f"Error en scroll: {e}"


def drag(x1: int, y1: int, x2: int, y2: int, speed: str = "slow") -> str:
    """Drag with human-like bezier path."""
    if not _PYAUTOGUI:
        return "Error: pyautogui no instalado."
    try:
        move_to(x1, y1, "normal")
        time.sleep(random.uniform(0.1, 0.3))

        profile = _SPEED_PROFILES.get(speed, _SPEED_PROFILES["slow"])
        path = _human_bezier_path(float(x1), float(y1), float(x2), float(y2),
                                  steps=profile["steps"])

        pyautogui.mouseDown(button="left")
        for px, py in path:
            pyautogui.moveTo(int(px), int(py))
            delay = profile["base_delay"] + random.uniform(-profile["jitter"], profile["jitter"])
            time.sleep(max(0.002, delay))
        pyautogui.mouseUp(button="left")

        return f"Arrastrado de ({x1},{y1}) a ({x2},{y2})."
    except Exception as e:
        return f"Error en drag: {e}"


def type_text(text: str, speed: str = "normal") -> str:
    """Type text with human-like variable speed."""
    if not _PYAUTOGUI:
        return "Error: pyautogui no instalado."
    try:
        speed_map = {"fast": 0.02, "normal": 0.05, "slow": 0.1, "careful": 0.15}
        base_interval = speed_map.get(speed, 0.05)
        for char in text:
            pyautogui.typewrite(char, interval=0.0)
            # Variable delay per character
            delay = base_interval + random.uniform(-base_interval * 0.3, base_interval * 0.3)
            time.sleep(max(0.01, delay))
            # Occasional longer pause (like human thinking)
            if random.random() < 0.03:
                time.sleep(random.uniform(0.2, 0.5))
        return f"Texto escrito ({len(text)} caracteres)."
    except Exception as e:
        return f"Error escribiendo: {e}"


def get_position() -> str:
    if not _PYAUTOGUI:
        return "Error: pyautogui no instalado."
    try:
        x, y = pyautogui.position()
        return f"Mouse en ({x}, {y})."
    except Exception:
        return "Error obteniendo posición."


# ── Advanced mouse actions ───────────────────────────────────────────────────

import platform as _platform
_WIN = _platform.system() == "Windows"


def middle_click(x: int | None = None, y: int | None = None) -> str:
    """Middle click (opens links in new tab, closes tabs)."""
    if not _PYAUTOGUI:
        return "Error: pyautogui no instalado."
    try:
        if x is not None and y is not None:
            r = move_to(x, y)
            if r.startswith("Error"):
                return r
        time.sleep(random.uniform(0.05, 0.15))
        pyautogui.click(button="middle")
        return "Click medio."
    except Exception as e:
        return f"Error en click medio: {e}"


def triple_click(x: int | None = None, y: int | None = None) -> str:
    """Triple click (select paragraph)."""
    return click(x, y, "left", 3)


def hover(x: int, y: int, duration: float = 0.5) -> str:
    """Hover over an element (move to position and wait)."""
    if not _PYAUTOGUI:
        return "Error: pyautogui no instalado."
    try:
        r = move_to(x, y, "slow")
        if r.startswith("Error"):
            return r
        time.sleep(duration)
        return f"Hover en ({x}, {y}) por {duration}s."
    except Exception as e:
        return f"Error en hover: {e}"


def mouse_down(button: str = "left") -> str:
    """Press and hold mouse button."""
    if not _PYAUTOGUI:
        return "Error: pyautogui no instalado."
    try:
        pyautogui.mouseDown(button=button)
        return f"Botón {button} presionado (manteniendo)."
    except Exception as e:
        return f"Error: {e}"


def mouse_up(button: str = "left") -> str:
    """Release mouse button."""
    if not _PYAUTOGUI:
        return "Error: pyautogui no instalado."
    try:
        pyautogui.mouseUp(button=button)
        return f"Botón {button} liberado."
    except Exception as e:
        return f"Error: {e}"


# ── Window management via mouse ──────────────────────────────────────────────

def window_move(target_x: int = None, target_y: int = None) -> str:
    """Move the active window by dragging its title bar to (target_x, target_y)."""
    if not _PYAUTOGUI:
        return "Error: pyautogui no instalado."
    try:
        cx, cy = pyautogui.position()
        tx = target_x if target_x is not None else cx
        ty = target_y if target_y is not None else cy
        title_bar_y = 10
        pyautogui.moveTo(cx, title_bar_y, duration=0.2)
        time.sleep(0.1)
        pyautogui.mouseDown(button="left")
        time.sleep(0.05)
        path = _human_bezier_path(float(cx), float(title_bar_y), float(tx), float(ty), steps=25)
        for px, py in path:
            pyautogui.moveTo(int(px), int(py))
            time.sleep(0.005)
        pyautogui.mouseUp(button="left")
        return f"Ventana movida a ({tx}, {ty})."
    except Exception as e:
        return f"Error moviendo ventana: {e}"


def window_resize(edge: str = "right", target_x: int = None, target_y: int = None) -> str:
    """Resize active window by dragging an edge or corner.

    edge: right | left | top | bottom | topleft | topright | bottomleft | bottomright
    """
    if not _PYAUTOGUI:
        return "Error: pyautogui no instalado."
    try:
        sw, sh = pyautogui.size()
        cx, cy = pyautogui.position()

        edge_positions = {
            "right": (sw - 5, cy),
            "left": (5, cy),
            "top": (cx, 5),
            "bottom": (cx, sh - 5),
            "topleft": (5, 5),
            "topright": (sw - 5, 5),
            "bottomleft": (5, sh - 5),
            "bottomright": (sw - 5, sh - 5),
        }
        start_pos = edge_positions.get(edge, (sw - 5, cy))

        pyautogui.moveTo(int(start_pos[0]), int(start_pos[1]), duration=0.3)
        time.sleep(0.15)

        tx = target_x if target_x is not None else int(start_pos[0]) + 50
        ty = target_y if target_y is not None else int(start_pos[1]) + 50

        pyautogui.mouseDown(button="left")
        path = _human_bezier_path(float(start_pos[0]), float(start_pos[1]), float(tx), float(ty), steps=20)
        for px, py in path:
            pyautogui.moveTo(int(px), int(py))
            time.sleep(0.005)
        pyautogui.mouseUp(button="left")
        return f"Ventana redimensionada por borde {edge}."
    except Exception as e:
        return f"Error redimensionando: {e}"


def window_minimize() -> str:
    """Minimize the active window by clicking the minimize button."""
    if not _PYAUTOGUI:
        return "Error: pyautogui no instalado."
    try:
        if _WIN:
            title_bar_y = 10
            minimize_x = pyautogui.size()[0] - 200
            pyautogui.moveTo(minimize_x, title_bar_y, duration=0.2)
            time.sleep(0.1)
            pyautogui.click()
            return "Ventana minimizada."
        else:
            pyautogui.hotkey("alt", "space")
            time.sleep(0.2)
            pyautogui.press("n")
            return "Ventana minimizada."
    except Exception as e:
        return f"Error minimizando: {e}"


def window_maximize() -> str:
    """Maximize the active window."""
    if not _PYAUTOGUI:
        return "Error: pyautogui no instalado."
    try:
        if _WIN:
            title_bar_y = 10
            max_x = pyautogui.size()[0] - 100
            pyautogui.moveTo(max_x, title_bar_y, duration=0.2)
            time.sleep(0.05)
            pyautogui.click()
            return "Ventana maximizada."
        else:
            pyautogui.hotkey("alt", "space")
            time.sleep(0.2)
            pyautogui.press("x")
            return "Ventana maximizada."
    except Exception as e:
        return f"Error maximizando: {e}"


def window_close() -> str:
    """Close the active window by clicking the X button."""
    if not _PYAUTOGUI:
        return "Error: pyautogui no instalado."
    try:
        if _WIN:
            sw, _ = pyautogui.size()
            close_x = sw - 10
            pyautogui.moveTo(close_x, 10, duration=0.15)
            time.sleep(0.05)
            pyautogui.click()
            return "Ventana cerrada."
        else:
            pyautogui.hotkey("alt", "f4")
            return "Ventana cerrada."
    except Exception as e:
        return f"Error cerrando ventana: {e}"


def window_restore() -> str:
    """Restore (un-maximize/un-minimize) the active window."""
    if not _PYAUTOGUI:
        return "Error: pyautogui no instalado."
    try:
        if _WIN:
            sw, _ = pyautogui.size()
            mid_x = sw // 2
            pyautogui.moveTo(mid_x, 10, duration=0.2)
            time.sleep(0.05)
            pyautogui.click()
            return "Ventana restaurada."
        else:
            pyautogui.hotkey("alt", "space")
            time.sleep(0.2)
            pyautogui.press("r")
            return "Ventana restaurada."
    except Exception as e:
        return f"Error restaurando: {e}"


def window_snap(side: str = "left") -> str:
    """Snap window to left or right half of screen."""
    if not _PYAUTOGUI:
        return "Error: pyautogui no instalado."
    try:
        title_bar_y = 10
        if side == "left":
            cx, _ = pyautogui.position()
            pyautogui.moveTo(cx, title_bar_y, duration=0.2)
            time.sleep(0.1)
            pyautogui.mouseDown(button="left")
            pyautogui.moveTo(5, title_bar_y, duration=0.3)
            pyautogui.mouseUp(button="left")
        elif side == "right":
            cx, _ = pyautogui.position()
            sw = pyautogui.size()[0]
            pyautogui.moveTo(cx, title_bar_y, duration=0.2)
            time.sleep(0.1)
            pyautogui.mouseDown(button="left")
            pyautogui.moveTo(sw - 5, title_bar_y, duration=0.3)
            pyautogui.mouseUp(button="left")
        return f"Ventana anclada a {side}."
    except Exception as e:
        return f"Error anclando: {e}"


def select_text(start_x: int, start_y: int, end_x: int, end_y: int) -> str:
    """Select text by clicking and dragging from start to end position."""
    if not _PYAUTOGUI:
        return "Error: pyautogui no instalado."
    try:
        pyautogui.moveTo(start_x, start_y, duration=0.2)
        time.sleep(0.1)
        pyautogui.mouseDown(button="left")
        time.sleep(0.05)
        path = _human_bezier_path(float(start_x), float(start_y), float(end_x), float(end_y), steps=30)
        for px, py in path:
            pyautogui.moveTo(int(px), int(py))
            time.sleep(0.008)
        pyautogui.mouseUp(button="left")
        return f"Texto seleccionado de ({start_x},{start_y}) a ({end_x},{end_y})."
    except Exception as e:
        return f"Error seleccionando texto: {e}"


def context_menu_click(x: int | None = None, y: int | None = None, option_text: str = None) -> str:
    """Right-click to open context menu, then optionally click an option by description."""
    if not _PYAUTOGUI:
        return "Error: pyautogui no instalado."
    try:
        r = right_click(x, y)
        if r.startswith("Error"):
            return r
        time.sleep(0.3)
        if option_text:
            try:
                from actions.visual_click import visual_click as _vc
                result = _vc({"element_description": option_text})
                return f"Menú contextual abierto → {result}"
            except Exception:
                return f"Menú contextual abierto en ({x or 'actual'},{y or 'actual'}). Buscando opción..."
        return f"Menú contextual abierto en ({x or 'actual'},{y or 'actual'})."
    except Exception as e:
        return f"Error en menú contextual: {e}"


def scroll_to_element(element_description: str, max_scrolls: int = 10) -> str:
    """Scroll until an element described is visible, then stop."""
    if not _PYAUTOGUI:
        return "Error: pyautogui no instalado."
    try:
        try:
            from actions.visual_click import visual_click as _vc
            for i in range(max_scrolls):
                result = _vc({"element_description": element_description, "dry_run": "true"})
                if result != "not_found" and "encontrado" in result.lower():
                    return f"Elemento '{element_description}' encontrado después de {i} scrolls."
                scroll("down", 3)
                time.sleep(0.5)
            return f"Elemento '{element_description}' no encontrado después de {max_scrolls} scrolls."
        except ImportError:
            return "visual_click no disponible para scroll_to_element."
    except Exception as e:
        return f"Error en scroll_to_element: {e}"


def get_screen_size() -> str:
    """Get screen resolution."""
    if not _PYAUTOGUI:
        return "Error: pyautogui no instalado."
    try:
        w, h = pyautogui.size()
        return f"Pantalla: {w}x{h}."
    except Exception as e:
        return f"Error: {e}"


# ── Tool wrapper ─────────────────────────────────────────────────────────────

def human_mouse(parameters: dict, player=None, **kwargs) -> str:
    """Tool: human-like mouse control with natural movements.
    
    actions: move | click | double_click | right_click | middle_click | triple_click
             hover | scroll | drag | type | position
             window_move | window_resize | window_minimize | window_maximize | window_close
             window_restore | window_snap | select_text | context_menu_click
             mouse_down | mouse_up | scroll_to_element | screen_size
    """
    action = (parameters.get("action") or "").lower().strip()
    x = parameters.get("x")
    y = parameters.get("y")
    x2 = parameters.get("x2")
    y2 = parameters.get("y2")
    button = parameters.get("button", "left")
    direction = parameters.get("direction", "down")
    amount = parameters.get("amount", 3)
    text = parameters.get("text", "")
    speed = parameters.get("speed", "normal")
    edge = parameters.get("edge", "right")
    side = parameters.get("side", "left")
    target_x = parameters.get("target_x")
    target_y = parameters.get("target_y")
    option_text = parameters.get("option_text", "")
    element_desc = parameters.get("element_description", "") or parameters.get("description", "")
    duration = parameters.get("duration", 0.5)

    labels = {
        "move": "🖱 moviendo mouse",
        "click": "🖱 click",
        "double_click": "🖱 doble click",
        "middle_click": "🖱 click medio",
        "triple_click": "🖱 triple click",
        "right_click": "🖱 click derecho",
        "hover": "🖱 hover",
        "scroll": "🖱 scroll",
        "drag": "🖱 arrastrando",
        "type": "⌨️ escribiendo",
        "position": "🖱 posición",
        "window_move": "🖱 mover ventana",
        "window_resize": "🖱 redimensionar ventana",
        "window_minimize": "🖱 minimizar ventana",
        "window_maximize": "🖱 maximizar ventana",
        "window_close": "🖱 cerrar ventana",
        "window_restore": "🖱 restaurar ventana",
        "window_snap": "🖱 anclar ventana",
        "select_text": "🖱 seleccionar texto",
        "context_menu_click": "🖱 menú contextual",
        "mouse_down": "🖱 mouse down",
        "mouse_up": "🖱 mouse up",
        "scroll_to_element": "🖱 scroll hasta elemento",
        "screen_size": "🖱 tamaño de pantalla",
    }
    if player and action in labels:
        player.write_log(labels[action])

    if action == "move":
        return move_to(x, y, speed)
    elif action == "click":
        return click(x, y, button)
    elif action == "double_click":
        return double_click(x, y)
    elif action == "right_click":
        return right_click(x, y)
    elif action == "middle_click":
        return middle_click(x, y)
    elif action == "triple_click":
        return triple_click(x, y)
    elif action == "hover":
        return hover(x, y, duration)
    elif action == "scroll":
        return scroll(direction, amount)
    elif action == "drag" and x is not None and y is not None and x2 is not None and y2 is not None:
        return drag(x, y, x2, y2, speed)
    elif action == "type" and text:
        return type_text(text, speed)
    elif action == "position":
        return get_position()
    elif action == "window_move":
        return window_move(target_x or x, target_y or y)
    elif action == "window_resize":
        return window_resize(edge, target_x, target_y)
    elif action == "window_minimize":
        return window_minimize()
    elif action == "window_maximize":
        return window_maximize()
    elif action == "window_close":
        return window_close()
    elif action == "window_restore":
        return window_restore()
    elif action == "window_snap":
        return window_snap(side)
    elif action == "select_text":
        return select_text(x, y, x2, y2)
    elif action == "context_menu_click":
        return context_menu_click(x, y, option_text if option_text else None)
    elif action == "mouse_down":
        return mouse_down(button)
    elif action == "mouse_up":
        return mouse_up(button)
    elif action == "scroll_to_element":
        return scroll_to_element(element_desc, int(amount or 10))
    elif action == "screen_size":
        return get_screen_size()
    else:
        return (
            "Acciones disponibles:\n"
            "  Básicas: move(x,y), click(x,y), double_click(x,y), right_click(x,y)\n"
            "  Avanzadas: middle_click(x,y), triple_click(x,y), hover(x,y,duration)\n"
            "  Scroll: scroll(direction='up'|'down'|'left'|'right', amount=N)\n"
            "  Arrastrar: drag(x,y, x2,y2)\n"
            "  Texto: type(text), select_text(x,y, x2,y2)\n"
            "  Ventanas: window_move(target_x,target_y), window_resize(edge)\n"
            "    window_minimize, window_maximize, window_close, window_restore\n"
            "    window_snap(side='left'|'right')\n"
            "  Menú: context_menu_click(x,y, option_text='Copiar')\n"
            "  Visión: scroll_to_element(element_description='botón guardar')\n"
            "  mouse_down(button), mouse_up(button), position, screen_size\n"
            "Ej: human_mouse(action='click', x=500, y=400)"
        )
