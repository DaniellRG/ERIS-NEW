"""platform_self.py — ERIS conoce el SO en el que vive y cómo controlarlo.

Autoconciencia de plataforma: detecta el sistema (familia de OS, distro, kernel,
escritorio, display server, backend de audio) y qué herramientas de control hay
disponibles AHORA en esta máquina. Con eso ERIS sabe cómo moverse en cualquier
sistema y detecta cuándo fue "trasplantada" a otro OS para adaptarse rápido.

Estado persistido en memory/platform_state.json (gitignored). 100% portable:
solo stdlib + shutil.which; cada rama de SO se declara con su propio nombre de
familia para que la adaptación no dependa de marcas concretas.
"""
from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path


def _state_path() -> Path:
    return Path(__file__).resolve().parent.parent / "memory" / "platform_state.json"


def detect_os_info() -> dict:
    """Familia + nombre legible + kernel + arq del sistema actual."""
    fam = "unknown"
    if sys.platform == "win32":
        fam = "windows"
    elif sys.platform.startswith("linux"):
        fam = "linux"
    elif sys.platform == "darwin":
        fam = "macos"
    pretty = "unknown"
    distro_id = ""
    version_id = ""
    if fam == "linux":
        try:
            data = {}
            for line in Path("/etc/os-release").read_text(encoding="utf-8").splitlines():
                if "=" in line:
                    k, v = line.split("=", 1)
                    data[k.strip()] = v.strip().strip('"')
            pretty = data.get("PRETTY_NAME") or data.get("NAME") or "Linux"
            distro_id = data.get("ID", "") or ""
            version_id = data.get("VERSION_ID", "") or ""
        except Exception:
            pretty = "Linux"
    elif fam == "windows":
        pretty = "Windows"
    elif fam == "macos":
        pretty = "macOS"
    return {
        "family": fam,
        "os_name": pretty,
        "distro_id": distro_id,
        "version_id": version_id,
        "kernel": platform.release(),
        "arch": platform.machine(),
        "python": sys.version.split()[0],
    }


def detect_session() -> dict:
    """Escritorio y backend gráfico/audio (wayland/x11/tty, pipewire/pulse)."""
    de = os.environ.get("XDG_CURRENT_DESKTOP") or os.environ.get("DESKTOP_SESSION") or "unknown"
    session = os.environ.get("XDG_SESSION_TYPE") or "unknown"
    if os.environ.get("WAYLAND_DISPLAY"):
        display = "wayland"
    elif os.environ.get("DISPLAY"):
        display = "x11"
    else:
        display = session if session in ("wayland", "x11", "tty") else "headless"
    audio = "unknown"
    try:
        run_dir = Path(os.environ.get("XDG_RUNTIME_DIR") or f"/run/user/{os.getuid()}")
        if (run_dir / "pipewire-0").exists():
            audio = "pipewire"
        elif (run_dir / "pulse/native").exists():
            audio = "pulse"
    except Exception:
        pass
    return {"desktop": de, "display": display, "session": session, "audio": audio}


# ── Mapa de capacidad de control: programa del sistema → (tool ERIS, hint) ──
# Funciona para cualquier SO; en Windows estos programas no existen y la lista
# queda vacía (ERIS se apoya en core/action_imports + core/platform.py).
_CONTROL_MAP = {
    "pactl":        ("system_volume", "audio y volumen (PipeWire/Pulse)"),
    "wpctl":        ("system_volume", "audio y volumen (WirePlumber/pipewire)"),
    "hyprctl":      ("window_manager", "ventanas/monitores (Hyprland)"),
    "brightnessctl":("screen_control", "brillo de pantalla"),
    "grim":         ("pc_control", "captura de pantalla en Wayland"),
    "notify-send":  ("desktop_notifications", "notificaciones"),
    "nmcli":        ("pc_control", "red wifi"),
    "rfkill":       ("pc_control", "bluetooth/wireless"),
    "ydotool":      ("computer_control", "input de teclado/mouse sin X11"),
    "xdotool":      ("computer_control", "input de teclado/mouse en X11"),
    "xrandr":       ("monitor_control", "resoluciones/cables en X11"),
    "tesseract":    ("screen_vision", "OCR de pantalla/capturas"),
}


def tools_available() -> dict:
    """Programas de control presentes en PATH y herramientas ERIS asociadas."""
    res = {}
    for prog, (tool, hint) in _CONTROL_MAP.items():
        res[prog] = {
            "available": shutil.which(prog) is not None,
            "eris_tool": tool,
            "for": hint,
        }
    return res


def os_fingerprint() -> str:
    """Id estable del SO: familia + kernel major + arq (suficiente para detectar migración)."""
    info = detect_os_info()
    return f"{info['family']}|{info['distro_id'] or info['os_name']}|{info['kernel'].split('-')[0]}|{info['arch']}"


def _system_dict() -> dict:
    info = detect_os_info()
    sess = detect_session()
    tools = tools_available()
    return {
        "fingerprint": os_fingerprint(),
        "os": info,
        "session": sess,
        "tools": tools,
        "detected_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


def platform_state_refresh() -> dict:
    """Compara con el último estado registrado y persiste el actual.

    Devuelve {"changed": bool, "previous": dict|None, "current": dict}.
    Detecting un cambio de OS/escritorio = ERIS capta que fue migrada y puede
    re-adaptarse (re-health de tools, nota en prompt).
    """
    current = _system_dict()
    previous = None
    path = _state_path()
    try:
        if path.exists():
            previous = json.loads(path.read_text(encoding="utf-8"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
    changed = False
    if previous:
        if previous.get("fingerprint") != current["fingerprint"]:
            changed = True
        elif previous.get("session", {}).get("display") != current["session"].get("display"):
            changed = True
        elif previous.get("session", {}).get("audio") != current["session"].get("audio"):
            changed = True
    return {"changed": changed, "previous": previous, "current": current}


def system_portrait_markdown() -> str:
    """Bloque de texto en español para inyectar en el system prompt."""
    state = platform_state_refresh()
    cur = state["current"]
    info = cur["os"]
    sess = cur["session"]
    tools = cur["tools"]

    lines = [
        "## 🖥️ SISTEMA EN EL QUE VIVES (autodetectado)",
        "Esto lo detectaste tú al arrancar; si migras a otro sistema operativo, este bloque cambia solo.",
        f"- SO: {info['os_name']}  ({info['family']}{' · ' + info['distro_id'] + ' ' + info['version_id'] if info['distro_id'] else ''})",
        f"- Kernel: {info['kernel']} · Arq: {info['arch']} · Python: {info['python']}",
        f"- Escritorio: {sess['desktop']} · Display: {sess['display']} · Audio: {sess['audio']}",
        "",
        "TU CONTROL DE ESTA PC (herramientas del sistema disponibles AHORA):",
    ]

    if info["family"] == "linux":
        avail = [p for p, d in tools.items() if d["available"]]
        missing = [p for p, d in tools.items() if not d["available"]]
        if avail:
            lines.append("- Disponibles: " + ", ".join(sorted(avail)))
            lines.append("  (usa sus tools ERIS: " +
                         ", ".join(f"{d['eris_tool']} ← {p} ({d['for']})"
                                   for p, d in sorted(tools.items()) if d["available"]) + ")")
        else:
            lines.append("- Disponibles: ninguna de las esperadas — pasa `system_reader action=platform` para ver el mapa completo.")
        if missing:
            lines.append(f"- Faltan (control limitado en esa área): {', '.join(sorted(missing))}")
        if sess["display"] == "wayland":
            lines.append("- Estás en Wayland: NO uses pyautogui/pygetwindow (X11). Para input usa ydotool; capturas usa grim; ventanas usa hyprctl.")
    else:
        lines.append(f"- Estás en {info['family']}: las tools de control se adaptan por core/action_imports + core/platform.py (Windows native, Wayland degradado).")
        lines.append("- Corré `system_reader action=platform` para ver el mapa completo de este SO.")

    if state["changed"] and state["previous"]:
        prev = state["previous"]
        lines.append(
            f"\n⚠️ MIGRASTE DE SISTEMA: {prev.get('os', {}).get('os_name', '?')} "
            f"({prev.get('session', {}).get('display', '?')}) → "
            f"{info['os_name']} ({sess['display']}). "
            "Re-verificá qué herramientas de control existen aquí y adaptate rápido."
        )
    return "\n".join(lines)