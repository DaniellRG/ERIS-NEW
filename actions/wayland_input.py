"""
actions/wayland_input.py — Input físico REAL en Wayland para ERIS.

Wrapper de ydotool (ydotoold debe estar corriendo como servicio).
Permite mover el mouse, hacer clic (izquierdo/derecho/medio/doble),
arrastrar, scrollear, escribir texto y pulsar teclas/combos en el
escritorio real del usuario, igual que computer_control en Windows.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import time

# Mapa de nombres comunes → códigos evdev (para `ydotool key` y combos)
_KEYCODES = {
    "enter": 28, "return": 28, "esc": 1, "escape": 1, "tab": 15,
    "space": 57, "backspace": 14, "delete": 111, "insert": 110,
    "home": 102, "end": 107, "pageup": 104, "pagedown": 109,
    "left": 105, "right": 106, "up": 103, "down": 108,
    "ctrl": 29, "control": 29, "alt": 56, "leftalt": 56,
    "shift": 42, "super": 125, "meta": 125, "capslock": 58,
    "f1": 59, "f2": 60, "f3": 61, "f4": 62, "f5": 63, "f6": 64,
    "f7": 65, "f8": 66, "f9": 67, "f10": 68, "f11": 87, "f12": 88,
    "a": 30, "b": 48, "c": 46, "d": 32, "e": 18, "f": 33, "g": 34,
    "h": 35, "i": 23, "j": 36, "k": 37, "l": 38, "m": 50, "n": 49,
    "o": 24, "p": 25, "q": 16, "r": 19, "s": 31, "t": 20, "u": 22,
    "v": 47, "w": 17, "x": 45, "y": 21, "z": 44,
    "0": 11, "1": 2, "2": 3, "3": 4, "4": 5, "5": 6, "6": 7,
    "7": 8, "8": 9, "9": 10, "-": 12, "=": 13, "[": 26, "]": 27,
    ";": 39, "'": 40, "`": 41, "\\": 43, ",": 51, ".": 52, "/": 53,
}
_BTN = {"left": "0xC0", "right": "0xC1", "middle": "0xC2"}

_is_win = os.name == "nt"


def _ydo(args, timeout=10):
    bin_ = shutil.which("ydotool")
    if not bin_:
        return "Error: ydotool no está instalado (`sudo pacman -S ydotool`)."
    try:
        r = subprocess.run([bin_, *args], capture_output=True, text=True,
                           timeout=timeout)
        if r.returncode == 0:
            return (r.stdout or "(ok)").strip()
        return f"Error ydotool ({r.returncode}): {r.stderr.strip() or r.stdout.strip()}"
    except FileNotFoundError:
        return "Error: ydotool no está instalado."
    except subprocess.TimeoutExpired:
        return "Error: ydotool tardó demasiado (¿está ydotoold corriendo?)."
    except Exception as e:
        return f"Error: {type(e).__name__}: {e}"


def _resolve_keys(combo: str) -> str:
    """'ctrl+alt+t' → secuencia interna del ydotool key (press+release)."""
    parts = [p.strip().lower() for p in combo.split("+") if p.strip()]
    codes = []
    for p in parts:
        if p in _KEYCODES:
            codes.append(_KEYCODES[p])
        elif re.fullmatch(r"[0-9]{1,3}", p):
            codes.append(int(p))
        else:
            return f"Tecla desconocida: {p}"
    # formato: "29:1 46:1 29:0 46:0" (presionar juntos, soltar en orden inverso)
    seg = " ".join(f"{c}:1" for c in codes) + " " + " ".join(f"{c}:0" for c in reversed(codes))
    return seg


def wayland_input(parameters: dict | None = None, player=None) -> str:
    """Input físico real en Wayland (ydotool).
    Acciones: status, move, click, double_click, scroll, drag, type, key,
    combo, press, release, screenshot."""
    if _is_win:
        return "wayland_input es solo para Wayland/Linux. En Windows usá computer_control."
    parameters = parameters or {}
    action = (parameters.get("action") or "status").lower()

    if action in ("status", "estado"):
        bin_ = shutil.which("ydotool")
        daemon = subprocess.run(["systemctl", "is-active", "ydotool"],
                                capture_output=True, text=True)
        return (f"ydotool: {'instalado' if bin_ else 'NO instalado'}\n"
                f"Daemon ydotoold: {daemon.stdout.strip() or daemon.stderr.strip()}")

    if action in ("move", "mover"):
        x, y = int(parameters.get("x", 0)), int(parameters.get("y", 0))
        if parameters.get("relative"):
            return _ydo(["mousemove", "--", str(x), str(y)])
        return _ydo(["mousemove", "--absolute", "--", str(x), str(y)])

    if action in ("click", "clic"):
        btn = _BTN.get((parameters.get("button") or "left").lower(), "0xC0")
        n = int(parameters.get("count", 1) or 1)
        hold = float(parameters.get("hold_ms", 40)) / 1000
        out = []
        for _ in range(n):
            out.append(_ydo(["click", btn]))
            time.sleep(hold)
        return " | ".join(o for o in out if o not in ("(ok)",))

    if action in ("double_click", "doble_click", "doubleclick"):
        r1 = _ydo(["click", "0xC0"])
        time.sleep(0.02)
        r2 = _ydo(["click", "0xC0"])
        return r1 if r1 != "(ok)" else r2 if r2 != "(ok)" else "(doble clic)"

    if action in ("right_click", "click_derecho"):
        return _ydo(["click", "0xC1"])

    if action in ("middle_click", "click_medio"):
        return _ydo(["click", "0xC2"])

    if action in ("scroll", "scrollear"):
        return ("ydotool 1.0.4 no trae comando scroll en Wayland. "
                "Alternativa: mover el cursor y usar rueda física, o `key` con flechas.")

    if action in ("drag", "arrastrar"):
        x, y = int(parameters.get("x", 0)), int(parameters.get("y", 0))
        btn = _BTN.get((parameters.get("button") or "left").lower(), "0xC0")
        steps = int(parameters.get("steps", 20) or 20)
        r1 = _ydo(["mousedown", btn])
        sx = int(parameters.get("start_x", 0)); sy = int(parameters.get("start_y", 0))
        if sx or sy:
            _ydo(["mousemove", "--absolute", "--", str(sx), str(sy)])
        _ydo(["mousemove", "--absolute", "--", str(x), str(y)], timeout=20)
        r3 = _ydo(["mouseup", btn])
        return r1 if r1 != "(ok)" else r3 if r3 != "(ok)" else "(arrastrado)"

    if action in ("type", "escribir", "teclear"):
        text = parameters.get("text") or parameters.get("command") or ""
        if not text:
            return "Falta 'text'."
        text = text.replace("'", "'\\''")
        return _ydo(["type", text], timeout=20)

    if action in ("key", "tecla"):
        key = parameters.get("key") or parameters.get("target") or ""
        if not key:
            return "Falta 'key'."
        if "+" in key:
            return _ydo(["key", *_resolve_keys(key).split()], timeout=10)
        if key.lower() not in _KEYCODES:
            return f"Tecla desconocida: {key}"
        c = _KEYCODES[key.lower()]
        return _ydo(["key", f"{c}:1", f"{c}:0"])

    if action in ("combo", "hotkey", "atalajo"):
        combo = parameters.get("combo") or parameters.get("key") or parameters.get("target") or ""
        if not combo:
            return "Falta 'combo' (ej: ctrl+alt+t)."
        seq = _resolve_keys(combo)
        if seq.startswith("Tecla desconocida"):
            return seq
        return _ydo(["key", *seq.split()])

    if action in ("press", "presionar"):
        key = parameters.get("key") or parameters.get("target") or ""
        c = _KEYCODES.get(key.lower())
        if c is None:
            return f"Tecla desconocida: {key}"
        return _ydo(["key", f"{c}:1"])

    if action in ("release", "soltar"):
        key = parameters.get("key") or parameters.get("target") or ""
        c = _KEYCODES.get(key.lower())
        if c is None:
            return f"Tecla desconocida: {key}"
        return _ydo(["key", f"{c}:0"])

    if action in ("screenshot", "foto"):
        from actions.screen_vision import _capture_screen_base64
        return _capture_screen_base64()

    return ("Acciones: status, move (x,y), click (button,count), right_click, "
            "double_click, middle_click, scroll (dx,dy), drag (start_x,start_y→x,y), "
            "type (text), key (key), combo (ctrl+alt+t), press, release, screenshot.")