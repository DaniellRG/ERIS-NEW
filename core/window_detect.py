# -*- coding: utf-8 -*-
"""core/window_detect.py — LOS OJOS de Eris (Fase 2.1).

Detecta la ventana en foco y las ventanas abiertas en las dos plataformas que
Eris soporta, con **los dos backends siempre vivos** (no uno u otro según el
build, como pasaba antes):

- **Windows**: `ctypes`/user32 (`GetForegroundWindow`, `EnumWindows`).
- **Linux/Wayland/Hyprland**: `hyprctl` (`-j activewindow`, `-j clients`).
- **X11 (best effort)**: `xdotool` si está instalado.
- **Genérico**: devuelve vacío honestamente. **Nunca lanza.**

Origen: centraliza el patrón que vivía duplicado en `core/observer.py`
(Windows) y `actions/ide_integration.py::_hyprctl_windows` (Hyprland). El
observer (sentidos) y la integración con IDEs lo consumen.

Contrato de retorno:

    get_foreground() -> {"pid": int, "proc": str, "title": str, "class": str}
    list_windows(n)  -> [{"pid": int, "proc": str, "title": str, "class": str}, ...]

`proc` es el nombre de proceso normalizado en minúsculas. En Linux uso la
`class` de Hyprland como análogo (``code``, ``kitty``, ``firefox``…), que es lo
que esperan los clasificadores del observer.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from typing import Optional

_IS_WIN = os.name == "nt"

if _IS_WIN:  # pragma: no cover - solo Windows
    import ctypes
    import ctypes.wintypes  # noqa: F401
    _U32 = ctypes.windll.user32
    _KERNEL32 = ctypes.windll.kernel32
else:
    _U32 = None
    _KERNEL32 = None


def is_windows() -> bool:
    return _IS_WIN


# ── Normalización ──────────────────────────────────────────────────────────
def normalize_proc(proc: str) -> str:
    """Minúsculas y sin sufijos ruidosos (mismo criterio que observer)."""
    p = (proc or "").lower()
    for strip in (".exe", "64", " portable"):
        p = p.replace(strip, "")
    return p.strip()


def _proc_name(pid: int) -> str:
    try:
        import psutil
        return (psutil.Process(int(pid)).name() or "").lower()
    except Exception:
        return ""


# ══════════════════════════════════════════════════════════════════════════
# Backend Windows (ctypes/user32)
# ══════════════════════════════════════════════════════════════════════════
def fg_hwnd() -> int:
    if _U32 is None:
        return 0
    try:
        return int(_U32.GetForegroundWindow())
    except Exception:
        return 0


def window_title(hwnd: int) -> str:
    if _U32 is None:
        return ""
    try:
        n = _U32.GetWindowTextLengthW(hwnd)
        if n <= 0:
            return ""
        buf = ctypes.create_unicode_buffer(n + 1)
        _U32.GetWindowTextW(hwnd, buf, n + 1)
        return buf.value
    except Exception:
        return ""


def pid_of(hwnd: int) -> int:
    if _U32 is None:
        return 0
    pid = ctypes.c_ulong(0)
    try:
        _U32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return int(pid.value)
    except Exception:
        return 0


def window_rect(hwnd: int) -> Optional[dict]:
    if _U32 is None:
        return None

    class _RECT(ctypes.Structure):
        _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                    ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

    r = _RECT()
    try:
        if _U32.GetWindowRect(hwnd, ctypes.byref(r)):
            return {"left": r.left, "top": r.top,
                    "width": r.right - r.left, "height": r.bottom - r.top}
    except Exception:
        pass
    return None


def _list_visible_hwnds(max_n: int = 40) -> list:
    if _U32 is None:
        return []
    out: list = []
    USER32 = _U32

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def _cb(hwnd, lparam):
        if len(out) >= max_n:
            return False
        if not USER32.IsWindowVisible(hwnd):
            return True
        try:
            n = USER32.GetWindowTextLengthW(hwnd)
        except Exception:
            n = 0
        if n <= 0:
            return True
        try:
            buf = ctypes.create_unicode_buffer(n + 1)
            USER32.GetWindowTextW(hwnd, buf, n + 1)
            t = buf.value.strip()
        except Exception:
            t = ""
        if t:
            out.append((int(hwnd), t))
        return True

    try:
        USER32.EnumWindows(_cb, 0)
    except Exception:
        pass
    return out


def _win_get_foreground() -> dict:
    hwnd = fg_hwnd()
    if not hwnd:
        return {"pid": 0, "proc": "", "title": "", "class": ""}
    pid = pid_of(hwnd)
    return {"pid": pid, "proc": _proc_name(pid),
            "title": (window_title(hwnd) or "").strip(), "class": ""}


def _win_list_windows(max_n: int = 25) -> list:
    seen = set()
    result = []
    for hwnd, title in _list_visible_hwnds(max_n=max_n):
        pid = pid_of(hwnd)
        proc = _proc_name(pid) or "?"
        key = (proc, title)
        if key in seen:
            continue
        seen.add(key)
        result.append({"proc": proc, "title": title, "pid": pid, "class": ""})
    return result


# ══════════════════════════════════════════════════════════════════════════
# Backend Linux: Hyprland (hyprctl) con fallback X11 (xdotool)
# ══════════════════════════════════════════════════════════════════════════
def _hypr_json(*args) -> Optional[object]:
    exe = shutil.which("hyprctl")
    if not exe:
        return None
    try:
        r = subprocess.run([exe, "-j", *args], capture_output=True,
                           text=True, timeout=4)
        if r.returncode != 0 or not (r.stdout or "").strip():
            return None
        return json.loads(r.stdout)
    except Exception:
        return None


def _x11_get_foreground() -> dict:
    if not shutil.which("xdotool"):
        return {"pid": 0, "proc": "", "title": "", "class": ""}
    try:
        wid = subprocess.run(["xdotool", "getactivewindow"],
                             capture_output=True, text=True, timeout=3).stdout.strip()
        if not wid:
            return {"pid": 0, "proc": "", "title": "", "class": ""}
        title = subprocess.run(["xdotool", "getwindowname", wid],
                               capture_output=True, text=True, timeout=3).stdout.strip()
        try:
            pid = int(subprocess.run(["xdotool", "getwindowpid", wid],
                                     capture_output=True, text=True, timeout=3).stdout.strip() or 0)
        except Exception:
            pid = 0
        return {"pid": pid, "proc": _proc_name(pid), "title": title, "class": ""}
    except Exception:
        return {"pid": 0, "proc": "", "title": "", "class": ""}


def _linux_get_foreground() -> dict:
    data = _hypr_json("activewindow")
    if isinstance(data, dict) and data:
        cls = (data.get("class") or data.get("initialClass") or "").strip()
        title = (data.get("title") or "").strip()
        try:
            pid = int(data.get("pid") or 0)
        except Exception:
            pid = 0
        return {"pid": pid, "proc": normalize_proc(cls) or _proc_name(pid),
                "title": title, "class": cls}
    return _x11_get_foreground()


def _linux_list_windows(max_n: int = 25) -> list:
    data = _hypr_json("clients")
    if not isinstance(data, list):
        return []
    fg = _hypr_json("activewindow")
    fg_addr = fg.get("address") if isinstance(fg, dict) else None
    # La ventana activa primero (lo que espera ide_integration: titles[0]).
    ordered = sorted(data, key=lambda w: 0 if (isinstance(w, dict)
                                               and w.get("address") == fg_addr) else 1)
    seen = set()
    result = []
    for w in ordered:
        if not isinstance(w, dict):
            continue
        if len(result) >= max_n:
            break
        cls = (w.get("class") or w.get("initialClass") or "").strip()
        title = (w.get("title") or "").strip()
        try:
            pid = int(w.get("pid") or 0)
        except Exception:
            pid = 0
        key = (normalize_proc(cls), title)
        if key in seen:
            continue
        seen.add(key)
        result.append({"proc": normalize_proc(cls) or _proc_name(pid),
                       "title": title, "pid": pid, "class": cls})
    return result


# ══════════════════════════════════════════════════════════════════════════
# API pública
# ══════════════════════════════════════════════════════════════════════════
def get_foreground() -> dict:
    """Ventana en foco: {pid, proc, title, class}. Vacío honesto si no se puede."""
    try:
        return _win_get_foreground() if _IS_WIN else _linux_get_foreground()
    except Exception:
        return {"pid": 0, "proc": "", "title": "", "class": ""}


def list_windows(max_n: int = 25) -> list:
    """Ventanas visibles con título (sin duplicar). Vacía si no se puede."""
    try:
        return _win_list_windows(max_n) if _IS_WIN else _linux_list_windows(max_n)
    except Exception:
        return []


def get_active_class() -> str:
    """Clase/proceso de la ventana en foco (lo que clasifican los sentidos)."""
    fg = get_foreground()
    return fg.get("class") or fg.get("proc") or ""


def backend_name() -> str:
    """Qué backend está resolviendo: windows/hyprctl/x11/none."""
    if _IS_WIN:
        return "windows"
    if shutil.which("hyprctl"):
        return "hyprctl"
    if shutil.which("xdotool"):
        return "x11"
    return "none"
