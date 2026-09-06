"""
agents/agenlix_agent.py — AGENLIX: fragmento especialista en Linux de ERIS.

Agenlix es la subagente/fragmento de ERIS que se encarga de TODO lo relacionado
a Linux: terminal bash persistente, sudo on-demand, paquetes, servicios,
Wayland/hyprland, input físico (ydotool), OCR (tesseract), multimedia (ffmpeg,
wf-recorder), git autónomo, mantenimiento programado, KDE Connect y controles
de sistema. ERIS delega acá la carga Linux para no llevar todo el peso ella.
"""
from __future__ import annotations

import os
import re
import shutil
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent

_GROUPS = {
    "Terminal y paquetes": ["shell_session", "terminal_agent", "apt", "systemctl"],
    "Input físico (Wayland)": ["wayland_input", "ydotool", "grim"],
    "OCR offline": ["ocr_tool", "tesseract"],
    "Multimedia (ffmpeg)": ["media_lab", "ffmpeg", "wf-recorder", "pulse"],
    "Git autónomo": ["git_autonomo", "git"],
    "Mantenimiento": ["maintenance", "systemctl"],
    "Celular (KDE Connect)": ["kde_connect", "kdeconnect-cli"],
    "Controles de sistema": ["system_volume", "window_manager", "pc_control",
                             "desktop_notifications", "screen_control", "screen_see"],
}


def _linux_status() -> str:
    """Estado real de Agenlix: qué hay instalado y qué tools resuelven activas."""
    from core.tool_registry import get_tool
    lines = ["🟢 AGENLIX — Fragmento Linux de ERIS · ESTADO ACTIVO", ""]
    for group, names in _GROUPS.items():
        subs = []
        for n in names:
            bin_path = shutil.which(n) if n not in ("shell_session", "terminal_agent",
                                                    "wayland_input", "ocr_tool",
                                                    "media_lab", "git_autonomo",
                                                    "maintenance", "kde_connect",
                                                    "system_volume", "window_manager",
                                                    "pc_control", "desktop_notifications",
                                                    "screen_control", "screen_see") else ""
            ok = False
            if bin_path:
                ok = True
            elif n == "pulse":
                ok = bool(shutil.which("pactl") or shutil.which("pw-cli"))
            elif n == "systemctl":
                ok = Path("/bin/systemctl").exists() or Path("/usr/bin/systemctl").exists()
            elif n in ("shell_session", "terminal_agent", "wayland_input", "ocr_tool",
                       "media_lab", "git_autonomo", "maintenance", "kde_connect",
                       "system_volume", "window_manager", "pc_control",
                       "desktop_notifications", "screen_control", "screen_see"):
                try:
                    get_tool(n)
                    ok = True
                except Exception:
                    ok = False
            subs.append(f"{' ✅' if ok else ' ❌'} {n}")
        lines.append(f"▸ {group}:")
        for s in subs:
            lines.append(f"   {s}")
    lines.append("")
    lines.append("„Soy el fragmento Linux de Eris. Tengo todo el control Linux:")
    lines.append("   terminal, sudo, paquetes, input, OCR, video, git, "
                 "mantenimiento, celular. Podés delegarme lo pesado.")
    return "\n".join(lines)


def _run_shell(command: str) -> str:
    """Ejecuta un comando en la sesión bash persistente (con sudo askpass)."""
    from core.shell_session import run_shell_tool
    action = "cd" if command.strip().startswith("cd ") else "run"
    try:
        return run_shell_tool({"action": action, "command": command}) or "(ok)"
    except Exception as e:
        return f"Error en terminal: {e}"


def _tool(name: str, params: dict) -> str:
    """Invoca una tool de Eris por nombre y devuelve su resultado."""
    from core.tool_registry import get_tool
    try:
        return str(get_tool(name)(params) or "(ok)")
    except Exception as e:
        return f"Error en {name}: {e}"


def _parse_brackets(text: str):
    """Extrae un objetivo entre comillas o con '=': X, [X], 'X', X.py/X.mp4."""
    m = re.search(r"[\[\"'“”]?([\w.\-/]+)[\]\"'“” ]?(?:\s|$)", text)
    return m.group(1) if m else ""


# ── Delegación por dominio ────────────────────────────────────────────────────


def _handle_terminal(text: str) -> str:
    """Terminal bash persistente: comandos, cd, historial, sudo."""
    t = text.lower()
    if "historial" in t:
        return _run_shell("history")
    if "pwd" in t or "donde estoy" in t:
        return _run_shell("pwd")
    if any(k in t for k in ["permiso", "sudo ", "root", "as root", "elevated", "como administrador"]):
        m = re.search(r"(?:sudo\s+|permiso.*?par[áa].*?)(.+)", text, re.I)
        cmd = m.group(1).strip() if m else ""
        if not cmd:
            cmd = text.replace("sudo", "").replace("con permisos", "").strip()
        # El sudo ya usa SUDO_ASKPASS (diálogo) en la sesión persistente
        return _run_shell(f"sudo {' '.join(cmd.split())[:120]}")
    if re.match(r"^cd\s", text):
        return _run_shell(text.strip()[:120])
    # Extraer comando genérico
    for k, split in (("ejecutá ", "ejecuta "), ("ejecuta", "ejecuta"), ("corré ", "corre "),
                     ("terminal: ", "terminal: "), ("bash: ", "bash: ")):
        idx = text.lower().find(k)
        if idx >= 0:
            cmd = text[idx + len(split):].strip()
            if cmd:
                return _run_shell(cmd[:160])
    # Comando directo si empieza con algo comando-like
    first = text.split()[0] if text.split() else ""
    if re.match(r"^(ls|pwd|whoami|uname|df|du|free|ps|top|htop|grep|cat|echo|mkdir"
                r"|touch|cp|mv|rm|find|locate|which|apt|pacman|dnf|systemctl|git|pip"
                r"|curl|wget|nc|ping|ss|ip|nmcli|rfkill|yaourt|yay)$", first, re.I):
        return _run_shell(text.strip()[:180])
    return ""


def _handle_packages(text: str) -> str:
    """Gestión de paquetes con sudo on-demand."""
    t = text.lower()
    m = re.search(r"(?:instalar|install|instala|eliminar|remover|desinstalar|update|upgrade)"
                  r"[\s\w]*?(?:[a-z0-9.+-]+(?:\s|$))", text, re.I)
    pkg = ""
    if m:
        mm = re.search(r"([a-z0-9_./+-]+(?:-[a-z0-9.+-]+)?)", text)
        pkg = mm.group(1) if mm else ""
    if "update" in t or "actualizar sistema" in t or "actualizá el sistema" in t:
        return _run_shell("sudo apt-get update && sudo apt-get upgrade -y")
    if "instalar paquete" in t or "instala paquete" in t:
        return _run_shell(f"sudo apt-get install -y {pkg}")
    if "eliminar" in t or "desinstalar" in t or "remover" in t:
        return _run_shell(f"sudo apt-get remove -y {pkg}")
    if re.search(r"\b(apt|pacman|dnf)\b", t):
        return _run_shell(text.strip()[:160])
    m2 = re.search(r"(?:instal[áa]|instalar)\s+([a-z0-9_.+-]+)", text, re.I)
    if m2:
        return _run_shell(f"sudo apt-get install -y {m2.group(1)}")
    return f"Gestor de paquetes GNU/Linux. Decime: 'instalá nombre-del-paquete', " \
           f"'actualizá el sistema', 'desinstalá X'. Los permisos se piden al momento (askpass)."


def _handle_input(text: str) -> str:
    """Input físico con ydotool: mouse, clics, teclado, combos."""
    t = text.lower()
    p = {}
    if any(k in t for k in ["clic", "click", "tocá", "toca", "click en"]):
        m = re.search(r"(?:en|sobre|a)\s*[(\[“\"]?(\d+)[,\s]+(\d+)", text)
        if m:
            p = {"action": "click", "x": int(m.group(1)), "y": int(m.group(2))}
        else:
            p = {"action": "click"}
        return _tool("wayland_input", p)
    if "doble clic" in t or "doble click" in t:
        return _tool("wayland_input", {"action": "double_click"})
    if "derecho" in t or "right" in t:
        return _tool("wayland_input", {"action": "right_click"})
    if any(k in t for k in ["mové el mouse", "mueve el mouse", "mouse a", "cursor a"]):
        m = re.search(r"(\d{1,5})[,\s]+(\d{1,5})", text)
        if m:
            return _tool("wayland_input", {"action": "move",
                                           "x": int(m.group(1)), "y": int(m.group(2))})
        return _tool("wayland_input", {"action": "status"})
    if any(k in t for k in ["escribí ", "escribe ", "tipiá", "escribi el texto", "typing"]):
        m = re.search(r"(?:escrib[ií]|escribe|tipi[áa])\s+[\"“‘]?(.+?)[\"”’]?\s*$", text, re.I)
        contenido = m.group(1).strip() if m else text
        return _tool("wayland_input", {"action": "type", "text": contenido[:200]})
    if any(k in t for k in ["combo", "combinación", "combinacion", "tecla ", "atajo", "presioná ctrl"]):
        m = re.search(r"([a-z0-9]+(?:\+[a-z0-9]+)+)", text)
        if m:
            return _tool("wayland_input", {"action": "combo", "combo": m.group(1).lower()})
        m2 = re.search(r"\b(enter|esc|tab|ctrl|super|alt|space)\b", t)
        if m2:
            return _tool("wayland_input", {"action": "key", "key": m2.group(1)})
    return ("Control de input Wayland (ydotool). Ej: 'hacé clic en 500, 300', "
            "'escribí hola mundo', 'mové el mouse a 100 200', 'pulsá ctrl+c', "
            "'presioná la tecla enter'.")


def _handle_ocr(text: str) -> str:
    """OCR offline con tesseract: pantalla, archivo o región."""
    t = text.lower()
    if "pantalla" in t or "screen" in t:
        return _tool("ocr_tool", {"action": "screen"})
    m = re.search(r"([\w./-]+\.(?:png|jpg|jpeg|webp|bmp|pdf))", text)
    if m:
        return _tool("ocr_tool", {"action": "file", "path": m.group(1)})
    if "region" in t or "región" in t:
        return _tool("ocr_tool", {"action": "region"})
    return "OCR offline (tesseract). Decime 'leé el texto de la pantalla' o 'leé la imagen ruta/archivo.png'."


def _handle_media(text: str) -> str:
    """Multimedia: grabar pantalla/audio, convertir, GIFs, info."""
    t = text.lower()
    if "grabar pantalla" in t or "grabá la pantalla" in t or "screen record" in t:
        m = re.search(r"(\d+)\s*(?:s|seg|segundos)", t)
        seconds = int(m.group(1)) if m else 5
        return _tool("media_lab", {"action": "record", "seconds": seconds,
                                   "out": str(BASE / "data" / "grabacion_agelix.mp4")})
    if "grabar audio" in t or "grabá audio" in t:
        m = re.search(r"(\d+)\s*(?:s|seg|segundos)", t)
        seconds = int(m.group(1)) if m else 5
        return _tool("media_lab", {"action": "audio_record", "seconds": seconds})
    if "stop" in t or "detené" in t or "detener" in t or "pará la grabaci" in t:
        return _tool("media_lab", {"action": "stop_record"})
    if "convert" in t or "convertí" in t or "conviert" in t:
        m = re.search(r"([\w./-]+\.\w+)\s+(?:a|to)\s+([\w./-]+\.\w+)", text)
        if m:
            return _tool("media_lab", {"action": "convert",
                                       "input": m.group(1), "output": m.group(2)})
        return "Decime 'convertí archivo.mp4 a .mp3' por ejemplo."
    if "gif" in t:
        m = re.search(r"([\w./-]+\.\w+)", text)
        if m:
            return _tool("media_lab", {"action": "gif", "input": m.group(1)})
    if "info" in t or "duración" in t or "metadatos" in t:
        m = re.search(r"([\w./-]+\.\w+)", text)
        if m:
            return _tool("media_lab", {"action": "info", "path": m.group(1)})
    return ("Laboratorio multimedia: 'grabá la pantalla 8 segundos', 'grabá audio', "
            "'convertí video.mp4 a .mp3', 'hacé un gif de video.mp4', 'pasame la "
            "info de archivo.mp4'.")


def _handle_git(text: str) -> str:
    """Git autónomo: status, commit, subir, diario."""
    t = text.lower()
    if any(k in t for k in ["commiteá", "commitea", "commit", "subi todo", "subí todo",
                            "subí al repo", "sube al repo", "guardar cambios"]):
        return _tool("git_autonomo", {"action": "auto"})
    if any(k in t for k in ["estado git", "status", "ver cambios", "mostrá los cambios", "esta todo commiteado"]):
        return _tool("git_autonomo", {"action": "status"})
    if "diario" in t or "registro" in t or "log" in t:
        return _tool("git_autonomo", {"action": "log"})
    m = re.search(r"message[\s:=]+[\"“‘]?(.+)", text, re.I)
    if m:
        return _tool("git_autonomo", {"action": "commit", "message": m.group(1).strip()})
    return ("Git autónomo de Eris: 'subí todo al repo', 'mostrá el estado de git', "
            "'commiteá con message=arreglé el bug', 'pasame el diario de cambios' "
            "(va a memory/git_diario.md).")


def _handle_maintenance(text: str) -> str:
    """Mantenimiento programado: backup, limpieza, reportes."""
    t = text.lower()
    if "run_all" in t or "ejecutá todo" in t or "hacé mantenimiento" in t or "hacé el mantenimiento" in t:
        return _tool("maintenance", {"action": "run_all"})
    m = re.search(r"(?:clean_logs|backup|health_report|backup_workspace|backup_vault)", text)
    if m:
        return _tool("maintenance", {"action": "run", "name": m.group(1)})
    return _tool("maintenance", {"action": "list"})


def _handle_kde(text: str) -> str:
    """KDE Connect: celular y teléfono."""
    t = text.lower()
    if any(k in t for k in ["listar", "lista", "list", "dispositivos", "estado", "status"]):
        return _tool("kde_connect", {"action": "list"})
    if "pai" in t or "vincular" in t or "emparejar" in t:
        return _tool("kde_connect", {"action": "pair"})
    if "ding" in t or "sonar" in t or "ring" in t:
        return _tool("kde_connect", {"action": "ring"})
    if "sms" in t:
        m = re.search(r"(?:\+?[\d\s]{6,15})", text)
        number = m.group(1).strip() if m else None
        return _tool("kde_connect", {"action": "sms", "number": number})
    if "notificacion" in t or "notificación" in t:
        return _tool("kde_connect", {"action": "notifications"})
    if "enviá" in t or "envia" in t or "mandá" in t or "manda" in t or "clipboard" in t:
        m = re.search(r"(?:envi[áa]|envia|mand[áa]|manda)\s+(.+)$", text, re.I)
        contenido = m.group(1).strip() if m else text
        if "archivo" in t:
            return _tool("kde_connect", {"action": "send_file", "path": contenido})
        return _tool("kde_connect", {"action": "send_text", "text": contenido[:200]})
    return ("KDE Connect + tu celular. Decime 'listá dispositivos', 'vincular celular', "
            "'hacé sonar el teléfono', 'enviá esto al teléfono', 'enviá sms a +54 9 11...', "
            "'mostrame las notificaciones del celular'.")


def _handle_system_controls(text: str) -> str:
    """Controles de sistema Linux: volumen, brillo, ventanas, notificaciones, red."""
    t = text.lower()
    if "volumen" in t:
        if "subi" in t or "aument" in t or "más" in t:
            return _tool("system_volume", {"action": "up"})
        if "baj" in t or "reduc" in t or "menos" in t:
            return _tool("system_volume", {"action": "down"})
        if "mute" in t or "silencia" in t:
            return _tool("system_volume", {"action": "mute"})
        return _tool("system_volume", {"action": "get"})
    if "brillo" in t:
        if "subi" in t or "aument" in t:
            return _tool("screen_control", {"action": "brightness_up"})
        if "baj" in t or "reduc" in t:
            return _tool("screen_control", {"action": "brightness_down"})
        return _tool("screen_control", {"action": "brightness_get"})
    if "notificac" in t:
        m = re.search(r"[“\"](.+?)[”\"']?\s*$(?<!\.)", text)
        mensaje = m.group(1).strip() if m else text
        return _tool("desktop_notifications", {"action": "send",
                                               "title": "Agenlix", "message": mensaje[:150]})
    if any(k in t for k in ["ventana", "window", "hyprland", "hyprctl", "hololens", "workspace"]):
        return _tool("window_manager", {"action": "list"})
    if any(k in t for k in ["wifi", "bluetooth", "monitor apagado", "dpms", "red"]) :
        if "wifi" in t and "apa" in t:
            return _tool("pc_control", {"action": "wifi", "state": "off"})
        return _tool("pc_control", {"action": "status"})
    return ("Controles de sistema Linux: 'subí/bajá el volumen', 'poné mute', "
            "'subí el brillo', 'mandá una notificación con tal mensaje', "
            "'listame las ventanas abiertas', 'qué wifi hay / apagá el wifi'.")


def _handle_screen(text: str) -> str:
    """Visión: describir la pantalla real (grim en Wayland)."""
    if any(k in text.lower() for k in ["leé el texto", "leer el texto"]):
        return _tool("screen_see", {"action": "read_text"})
    return _tool("screen_see", {"action": "see"})


# ── Handler principal ─────────────────────────────────────────────────────────


def handle_linux(text: str, player=None, **kwargs) -> str:
    """Agenlix: fragmento Linux de ERIS. Diplomática en todo dominio Linux."""
    from core.tracer import get_tracer
    tracer = get_tracer()
    t0 = time.perf_counter()
    text = (text or "").strip()

    def _done(result: str) -> str:
        elapsed = time.perf_counter() - t0
        tracer.trace_handoff("agelix_linux", text, result, elapsed)
        return result

    if not text:
        return _done("Agenlix espera una tarea Linux. Probá: 'decime el estado', "
                     "'instalá firefox', 'grabá la pantalla 5 segundos', "
                     "'subí todo a git', 'hacé el mantenimiento'.")

    t = text.lower()
    # Estado/activo/health: reporte de todo lo que Agenlix controla
    if any(k in t for k in ["estado", "activo", "health", "qué herramientas",
                            "que herramientas", "qué podés", "que podes",
                            "qué sabes", "que sabes", "help", "ayuda", "capabilities",
                            "dashboard", "todo activo", "reporte"]):
        return _done(_linux_status())

    if not (os.name == "posix"):
        return _done("Soy Agenlix, el fragmento de ERIS especializado en Linux. "
                     "En este equipo no hay Linux activo (os.name=" + str(os.name) + ").")

    for name, fn in [
        ("git", _handle_git),
        ("kde", _handle_kde),
        ("maintenance", _handle_maintenance),
        ("ocr", _handle_ocr),
        ("media", _handle_media),
        ("input", _handle_input),
        ("paquetes", _handle_packages),
        ("terminal", _handle_terminal),
        ("controles", _handle_system_controls),
        ("pantalla", _handle_screen),
    ]:
        try:
            r = fn(text)
            if r:
                return _done(r)
        except Exception as e:
            return _done(f"Error en dominio {name}: {e}")

    return _done(
        "Agenlix (fragmento Linux de Eris) — dominios: terminal bash + sudo, "
        "paquetes (apt), input físico (ydotool), OCR (tesseract), multimedia "
        "(ffmpeg/wf-recorder), git autónomo, mantenimiento, KDE Connect, "
        "controles (volumen/brillo/ventanas/red). Decime 'agelix + lo que "
        "querés que haga' o 'estado' para ver todo activo."
    )


# ── Tool expuesta a Eris ──────────────────────────────────────────────────────


def agelix(parameters: dict | None = None, player=None) -> str:
    """Tool 'agelix': delega una tarea al fragmento Linux (Agenlix).
    Acciones: status (reporte activo de todo), help, task (task=<texto>)."""
    parameters = parameters or {}
    action = (parameters.get("action") or "task").lower()
    task = (parameters.get("task") or "").strip()

    if action in ("status", "estado", "activo", "health"):
        return _linux_status()
    if action in ("help", "ayuda", "list"):
        return handle_linux("ayuda")
    if action in ("task", "run", "dispatch", "delegar"):
        if not task:
            return "Agenlix necesita 'task': una descripción de la tarea Linux."
        return handle_linux(task, player=player)
    return ("Tool agelix (Agenlix, fragmento Linux de Eris). Acciones: "
            "status, help, task. Ej: {action:'task', task:'instalá htop'}.")