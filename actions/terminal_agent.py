"""
terminal_agent.py — Terminal interactiva persistente para ERIS.
Shell PowerShell/CMD persistente con streaming, cambio de directorio, y memoria de sesión.
"""
import subprocess
import os
import json
import time
import tempfile
import ctypes
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
TERMINAL_STATE = BASE_DIR / "data" / "terminal_state.json"

from core.shell_session import get_session, close_session

# ── SendInput helpers for Win+R simulation ──
user32 = ctypes.windll.user32 if os.name == "nt" else None
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
VK_LWIN = 0x5B
VK_RETURN = 0x0D


def _save_state(state: dict):
    TERMINAL_STATE.parent.mkdir(parents=True, exist_ok=True)
    TERMINAL_STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def _load_state() -> dict:
    if TERMINAL_STATE.exists():
        try:
            return json.loads(TERMINAL_STATE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"history": [], "last_cmd": "", "last_output": ""}


def _press_key(vk):
    """Presiona y suelta una tecla virtual key."""
    if not user32:
        return
    scan = user32.MapVirtualKeyW(vk, 0)
    # Key down
    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [("wVk", ctypes.c_ushort), ("wScan", ctypes.c_ushort),
                     ("dwFlags", ctypes.c_ulong), ("time", ctypes.c_ulong),
                     ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]
    class INPUT(ctypes.Structure):
        _fields_ = [("type", ctypes.c_ulong), ("ki", KEYBDINPUT), ("pad", ctypes.c_ubyte * 8)]
    inp = INPUT(type=INPUT_KEYBOARD)
    inp.ki.wVk = vk
    inp.ki.wScan = scan
    inp.ki.dwFlags = 0
    inp.ki.time = 0
    inp.ki.dwExtraInfo = ctypes.pointer(ctypes.c_ulong(0))
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))
    time.sleep(0.05)
    # Key up
    inp.ki.dwFlags = KEYEVENTF_KEYUP
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))
    time.sleep(0.05)


def _type_unicode(text: str):
    """Escribe texto unicode carácter por carácter."""
    if not user32:
        return
    for ch in text:
        code = ord(ch)
        class KEYBDINPUT(ctypes.Structure):
            _fields_ = [("wVk", ctypes.c_ushort), ("wScan", ctypes.c_ushort),
                         ("dwFlags", ctypes.c_ulong), ("time", ctypes.c_ulong),
                         ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]
        class INPUT(ctypes.Structure):
            _fields_ = [("type", ctypes.c_ulong), ("ki", KEYBDINPUT), ("pad", ctypes.c_ubyte * 8)]
        inp = INPUT(type=INPUT_KEYBOARD)
        inp.ki.wVk = 0
        inp.ki.wScan = code
        inp.ki.dwFlags = KEYEVENTF_UNICODE
        inp.ki.time = 0
        inp.ki.dwExtraInfo = ctypes.pointer(ctypes.c_ulong(0))
        user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))
        time.sleep(0.02)
        inp.ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP
        user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))
        time.sleep(0.01)


def _run_command(cmd: str, shell_type: str = "powershell", timeout: int = 30, elevated: bool = False) -> str:
    """Ejecuta un comando en shell persistente. Mantiene estado entre comandos."""
    session = get_session(shell=shell_type)
    return session.run(cmd, timeout=timeout)


def _open_with_start_process(target: str) -> str:
    """Abre cualquier cosa con Start-Process (apps, carpetas, URLs, archivos)."""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f'Start-Process "{target}" -ErrorAction Stop'],
            capture_output=True, text=True, timeout=15,
            creationflags=0x08000000
        )
        if result.returncode == 0:
            return f"Abierto: {target}"
        return f"Error: {result.stderr.strip()}" if result.stderr else f"Abierto: {target}"
    except Exception as e:
        return f"Error abriendo {target}: {e}"


def terminal_agent(parameters: dict, player=None) -> str:
    """
    Terminal interactiva persistente para ERIS.
    Actions: run, run_cmd, run_ps, elevated, open, win_r, shell_execute,
             stream, session_info, session_reset, list_history, clear, info
    """
    action = parameters.get("action", "run")
    cmd = parameters.get("command", "") or parameters.get("cmd", "")
    target = parameters.get("target", "") or cmd
    shell = parameters.get("shell", "powershell")
    timeout = min(parameters.get("timeout", 30), 120)
    elevated = parameters.get("elevated", False) or parameters.get("admin", False)
    state = _load_state()

    # ── INFO ──
    if action == "info":
        return (
            "Terminal Agent — Control total de Windows.\n\n"
            "TERMINAL:\n"
            "  run_cmd    — Ejecuta en CMD\n"
            "  run_ps     — Ejecuta en PowerShell\n"
            "  run        — Auto-detecta shell\n"
            "  elevated   — Ejecuta como ADMIN (UAC)\n\n"
            "ABRIR COSAS:\n"
            "  open       — Abre app, carpeta, URL o archivo\n"
            "  win_r      — Simula Win+R y ejecuta\n"
            "  shell_execute — Usa ShellExecute (como click derecho > Abrir)\n\n"
            "HISTORIAL:\n"
            "  list_history — Ver comandos ejecutados\n"
            "  clear        — Limpiar historial\n"
            "  info         — Esta ayuda"
        )

    # ── LIST HISTORY ──
    if action == "list_history":
        hist = state.get("history", [])
        if not hist:
            return "Sin historial."
        lines = []
        for h in hist[-20:]:
            admin_tag = " [ADMIN]" if h.get("elevated") else ""
            lines.append(f"  [{h['shell']}{admin_tag}] {h['cmd']}")
            if h.get("output"):
                out_preview = h["output"][:120].replace("\n", " | ")
                lines.append(f"    → {out_preview}")
        return f"Histórico ({len(hist)} comandos):\n" + "\n".join(lines)

    if action == "clear":
        state["history"] = []
        _save_state(state)
        return "Historial limpiado."

    # ── SESSION INFO ──
    if action == "session_info":
        session = get_session(shell=shell)
        return (
            f"Shell: {session.shell}\n"
            f"CWD: {session.cwd}\n"
            f"Viva: {session.is_alive()}\n"
            f"Histórico: {len(state.get('history', []))} comandos"
        )

    # ── SESSION RESET ──
    if action == "session_reset":
        close_session()
        state["history"] = []
        _save_state(state)
        return "Sesión reiniciada."

    # ── STREAM: ejecuta con output en tiempo real ──
    if action == "stream":
        if not cmd:
            return "Falta 'command'."

        def _on_line(line):
            if player:
                player.write_log(f"  {line}")

        if elevated:
            return _run_command(cmd, shell, timeout, elevated=True)
        session = get_session(shell=shell)
        output = session.run_streaming(cmd, timeout=timeout, callback=_on_line)
        state["history"].append({
            "cmd": cmd, "shell": shell, "elevated": False,
            "output": output[:500], "time": time.strftime("%Y-%m-%d %H:%M:%S")
        })
        state["history"] = state["history"][-50:]
        state["last_cmd"] = cmd
        state["last_output"] = output[:1000]
        _save_state(state)
        return output[:3000] if output else "(ejecutado sin output)"

    # ── PREVIEW: abre archivo HTML en el navegador ──
    if action in ("preview", "vista_previa"):
        if not target:
            return "Falta 'command' o 'target' con la ruta del archivo HTML."
        if not target.endswith((".html", ".htm")):
            target = target + ".html" if "." not in target else target
        if not os.path.exists(target):
            return f"No existe: {target}"
        if player:
            player.write_log(f"🌐 Preview: {target}")
        result = _open_with_start_process(target)
        state["history"].append({
            "cmd": f"preview: {target}", "shell": "open", "elevated": False,
            "output": result, "time": time.strftime("%Y-%m-%d %H:%M:%S")
        })
        state["history"] = state["history"][-50:]
        _save_state(state)
        return result

    # ── OPEN: abre app/carpet URL/archivo ──
    if action == "open":
        if not target:
            return "Falta 'command' o 'target'. Ejemplo: 'notepad', 'C:\\Users', 'https://google.com'"
        if player:
            player.write_log(f"📂 Abriendo: {target}")
        result = _open_with_start_process(target)
        state["history"].append({
            "cmd": f"open: {target}", "shell": "open", "elevated": False,
            "output": result, "time": time.strftime("%Y-%m-%d %H:%M:%S")
        })
        state["history"] = state["history"][-50:]
        _save_state(state)
        return result

    # ── WIN+R: simula Win+R, escribe comando, Enter ──
    if action == "win_r":
        if not target:
            return "Falta 'command' o 'target'."
        if player:
            player.write_log(f"⌨️ Win+R: {target}")
        if not user32:
            return "Error: Win+R solo disponible en Windows."
        try:
            # Presionar Win+R
            _press_key(VK_LWIN)
            time.sleep(0.3)
            # Tecla R
            _press_key(0x52)  # VK_R
            time.sleep(0.8)  # Esperar que abra el diálogo

            # Escribir el comando
            _type_unicode(target)
            time.sleep(0.3)

            # Presionar Enter
            _press_key(VK_RETURN)
            time.sleep(1)

            result = f"Win+R ejecutado: {target}"
            state["history"].append({
                "cmd": f"win_r: {target}", "shell": "win_r", "elevated": False,
                "output": result, "time": time.strftime("%Y-%m-%d %H:%M:%S")
            })
            state["history"] = state["history"][-50:]
            _save_state(state)
            return result
        except Exception as e:
            return f"Error Win+R: {e}"

    # ── SHELL_EXECUTE: como click derecho > Abrir con ──
    if action == "shell_execute":
        if not target:
            return "Falta 'command' o 'target'."
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 f'(New-Object -ComObject Shell.Application).ShellExecute("{target}")'],
                capture_output=True, text=True, timeout=15,
                creationflags=0x08000000
            )
            result_text = f"ShellExecute: {target}"
            state["history"].append({
                "cmd": f"shell_execute: {target}", "shell": "powershell", "elevated": False,
                "output": result_text, "time": time.strftime("%Y-%m-%d %H:%M:%S")
            })
            state["history"] = state["history"][-50:]
            _save_state(state)
            return result_text
        except Exception as e:
            return f"Error ShellExecute: {e}"

    # ── ELEVATED alias ──
    if action == "elevated":
        elevated = True

    # ── TERMINAL COMMANDS (persistent shell) ──
    if not cmd:
        return "Falta el parámetro 'command'."

    # Auto-detect shell
    if action == "run_cmd" or cmd.lower().startswith(("dir ", "cd ", "type ", "del ", "copy ", "move ", "mkdir ", "rmdir ", "cls", "echo ", "set ", "where ", "tasklist", "ipconfig", "systeminfo", "net ", "assoc", "ftype")):
        shell = "cmd"
    elif action == "run_ps" or cmd.lower().startswith(("get-", "set-", "write-", "import-", "export-", "new-", "remove-", "select-", "where-object", "foreach", "measure-", "start-", "stop-", "restart-", "invoke-", "install-", "uninstall-")):
        shell = "powershell"

    admin_tag = " [ADMIN]" if elevated else ""
    if player:
        player.write_log(f"💻 {shell.upper()}{admin_tag}: {cmd[:60]}...")

    output = _run_command(cmd, shell, timeout, elevated)

    state["history"].append({
        "cmd": cmd, "shell": shell, "elevated": elevated,
        "output": output[:500], "time": time.strftime("%Y-%m-%d %H:%M:%S")
    })
    state["history"] = state["history"][-50:]
    state["last_cmd"] = cmd
    state["last_output"] = output[:1000]
    _save_state(state)

    return output[:3000] if output else "(comando ejecutado sin output)"
