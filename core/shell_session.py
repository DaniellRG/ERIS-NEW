"""
core/shell_session.py — Persistent interactive shell for ERIS.

Replaces fire-and-forget subprocess.run() with a live, persistent shell
that maintains state between commands (cwd, env, session).
Soporta PowerShell/CMD (Windows) y /bin/bash (Linux) automáticamente.
"""
from __future__ import annotations

import os
import re
import subprocess
import threading
import time
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
MAX_OUTPUT = 50_000
_IS_WIN = os.name == "nt"

# ── Lista blanca de comandos seguros (solo lectura / sin efectos destructivos) ──
_SAFE_COMMANDS = {
    "pwd", "ls", "dir", "cd", "echo", "cat", "type", "whoami", "date", "uptime",
    "uname", "df", "du", "free", "grep", "head", "tail", "wc", "which", "whereis",
    "file", "stat", "tree", "ps", "top", "env", "printenv", "hostname", "id",
    "groups", "locale", "cal", "less", "more", "man", "clear",
    "git status", "git log", "git diff", "git show", "git branch",
    "git remote -v", "git rev-parse",
    "python", "python3", "pip", "npm", "node",
}

# ── Patrones peligrosos que NUNCA se ejecutan ──
_DANGEROUS_PATTERNS = [
    (re.compile(r"\brm\s+(-[rf]+\s+)?/", re.I), "Eliminar archivos/directorios críticos (rm)"),
    (re.compile(r"\bdel\s+(/[sfq]\s+)?[A-Z]:\\", re.I), "Eliminar archivos en Windows (del)"),
    (re.compile(r"\bformat\s+[A-Z]:", re.I), "Formatear disco (format)"),
    (re.compile(r"\brmdir\s+(/s\s+)?[A-Z]:\\", re.I), "Eliminar directorio en Windows (rmdir)"),
    (re.compile(r"\bRemove-Item\s+(-Recurse)?\s+\"", re.I), "Eliminar con PowerShell (Remove-Item)"),
    (re.compile(r"\bgit\s+push\s+--force", re.I), "Git force push"),
    (re.compile(r"\bgit\s+push", re.I), "Git push"),
    (re.compile(r"\bgit\s+reset\s+--hard", re.I), "Git reset hard"),
    (re.compile(r"\bshutdown\b", re.I), "Apagar/reiniciar sistema"),
    (re.compile(r"\bsudo\s+reboot\b", re.I), "Reiniciar con sudo"),
    (re.compile(r"\breboot\b", re.I), "Reiniciar sistema"),
    (re.compile(r"\bhalt\b", re.I), "Detener sistema"),
    (re.compile(r"\bpoweroff\b", re.I), "Apagar sistema"),
    (re.compile(r"\bsystemctl\s+(stop|disable|restart)", re.I), "Detener servicio"),
    (re.compile(r"\bnet\s+user", re.I), "Modificar usuarios"),
    (re.compile(r"\bmkfs\b", re.I), "Formatear sistema de archivos"),
    (re.compile(r"\bdd\s+if=", re.I), "Sobreescribir disco con dd"),
    (re.compile(r">\s*/dev/(sd|nvme|hd|mmcblk)", re.I), "Redirigir a dispositivo de bloque"),
    (re.compile(r"(curl|wget)\b[^\n|]*\|\s*(sudo\s+)?(ba|z|da|k)?sh\b", re.I), "Pipe de descarga a shell"),
    (re.compile(r"\brm\s+(-[rf]+\s+)+(~|/home|\$HOME)(/|\s|$)", re.I), "Borrar home del usuario"),
    (re.compile(r"\brm\b", re.I), "Borrar archivos (rm)"),
    (re.compile(r"\brmdir\b", re.I), "Borrar directorio (rmdir)"),
    (re.compile(r"\bdel\b", re.I), "Borrar archivo (del)"),
    (re.compile(r"\bRemove-Item\b", re.I), "Borrar con PowerShell"),
]

def _is_command_allowed(command: str) -> tuple[bool, str]:
    """Devuelve (permitido, motivo). Si no está permitido, explica por qué."""
    cmd = (command or "").strip()
    if not cmd:
        return False, "Comando vacío"

    first_token = cmd.split()[0].lower() if cmd.split() else ""

    # Comandos explícitamente en lista blanca → permitido
    if first_token in _SAFE_COMMANDS:
        return True, ""

    # Patrones peligrosos → denegado
    for pattern, desc in _DANGEROUS_PATTERNS:
        if pattern.search(cmd):
            return False, f"Comando bloqueado ({desc}): {cmd[:80]}"

    # Cualquier otro comando no en lista blanca → denegado por defecto
    return False, f"Comando no en lista blanca: {cmd[:80]}"



def _default_shell() -> str:
    """bash en Linux/macOS, powershell en Windows."""
    return "powershell" if _IS_WIN else "bash"


def _normalize_shell(shell: str | None) -> str:
    shell = (shell or "auto").strip().lower()
    if shell in ("auto", "", "default", None):
        return _default_shell()
    if shell in ("sh", "zsh", "bash", "bash.exe"):
        return "bash"
    if shell in ("cmd", "cmd.exe", "command"):
        return "cmd"
    if shell in ("ps", "pwsh", "powershell", "powershell.exe"):
        return "powershell"
    return _default_shell()


class ShellSession:
    """Sesión de shell persistente con streaming, cd y estado entre comandos."""

    def __init__(self, shell: str | None = None, cwd: str | None = None):
        self.shell = _normalize_shell(shell)
        self.cwd = cwd or str(BASE_DIR)
        self._proc = None
        self._lock = threading.Lock()
        self._env = os.environ.copy()
        self._started = False
        self._history: list[str] = []

    def _start(self):
        if self._proc and self._proc.poll() is None:
            return
        if self.shell == "bash":
            cmd = ["bash", "--norc", "--noprofile"]
        elif self.shell == "powershell":
            cmd = ["powershell", "-NoProfile", "-NoLogo", "-Interactive"]
        else:
            cmd = ["cmd"]
        kwargs = dict(
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=self.cwd,
            env=self._env,
            bufsize=1,
        )
        if _IS_WIN:
            kwargs["creationflags"] = 0x08000000
        else:
            # sudo on-demand: pedir password al usuario "en el momento" vía askpass
            askpass = BASE_DIR / "tools" / "eris_askpass.py"
            if askpass.exists() and not self._env.get("SUDO_ASKPASS"):
                self._env["SUDO_ASKPASS"] = str(askpass)
        self._proc = subprocess.Popen(cmd, **kwargs)
        self._started = True
        # Send a marker to know when output starts
        self._send_raw(f"echo '___ERIS_SHELL_READY___'\n")
        self._read_until("___ERIS_SHELL_READY___", timeout=5)

    def _send_raw(self, cmd: str):
        if not self._proc or self._proc.poll() is not None:
            self._start()
        self._proc.stdin.write(cmd)
        self._proc.stdin.flush()

    def _read_until(self, marker: str, timeout: float = 30) -> str:
        """Read stdout until marker is found or timeout."""
        output = []
        start = time.time()
        while time.time() - start < timeout:
            line = self._proc.stdout.readline()
            if not line:
                if self._proc.poll() is not None:
                    break
                time.sleep(0.05)
                continue
            output.append(line)
            if marker in line:
                break
        return "".join(output)

    def run(self, command: str, timeout: int = 30) -> str:
        """Execute a command and return output. Maintains session state."""
        cmd = (command or "").strip()
        if not cmd:
            return "(comando vacío)"

        # ── Validación de seguridad: lista blanca ──
        allowed, reason = _is_command_allowed(cmd)
        if not allowed:
            return f"Comando denegado por seguridad: {reason}"

        sep = ";" if self.shell != "cmd" else "&"
        with self._lock:
            try:
                self._start()
                marker = f"___ERIS_END_{os.getpid()}_{int(time.time()*1000)}___"
                # cd puro (sin operadores de shell) → seguimiento local del dir.
                # Si lleva && ; | > < etc., bash lo ejecuta normal (cd + resto).
                rest = cmd[2:].strip() if cmd.lower().startswith("cd ") else ""
                _pure = rest and not any(c in rest for c in "&;|><`$(\"'")
                if rest and _pure and os.path.isdir(rest):
                    self.cwd = os.path.abspath(rest)
                    self._send_raw(f"cd '{self.cwd}'; echo '{marker}'\n")
                elif rest and not _pure and os.path.isdir(rest.strip("'\"")):
                    # cd '/a b' o cd "a b": ruta con espacio, sin operadores
                    self.cwd = os.path.abspath(rest.strip("'\""))
                    self._send_raw(f"cd '{self.cwd}'; echo '{marker}'\n")
                else:
                    if cmd.lower().startswith("cd ") and not rest:
                        return "Falta la ruta para cd."
                    self._send_raw(f"{cmd} {sep} echo '{marker}'\n")
                    self._history.append(cmd)
                    self._history = self._history[-100:]

                output = self._read_until(marker, timeout=timeout)
                # Clean output: remove marker and command echo
                lines = output.split("\n")
                clean = []
                skip_first = (os.name == "nt")
                for line in lines:
                    if marker in line:
                        break
                    if skip_first and command.strip() in line and len(lines) > 1:
                        skip_first = False
                        continue
                    clean.append(line)
                    skip_first = False
                result = "\n".join(clean).strip()
                return result if result else "(ejecutado sin output)"
            except subprocess.TimeoutExpired:
                return f"Timeout: el comando tardó más de {timeout}s"
            except Exception as e:
                return f"Error: {e}"

    def run_streaming(self, command: str, timeout: int = 60, callback=None) -> str:
        """Execute with streaming output. callback(line) called for each line."""
        sep = ";" if self.shell != "cmd" else "&"
        with self._lock:
            try:
                self._start()
                marker = f"___ERIS_STREAM_{os.getpid()}_{int(time.time()*1000)}___"
                self._send_raw(f"{command} {sep} echo '{marker}'\n")

                output = []
                start = time.time()
                while time.time() - start < timeout:
                    line = self._proc.stdout.readline()
                    if not line:
                        if self._proc.poll() is not None:
                            break
                        time.sleep(0.05)
                        continue
                    if marker in line:
                        break
                    output.append(line)
                    if callback:
                        callback(line.rstrip("\n"))
                return "\n".join(output).strip() or "(ejecutado sin output)"
            except Exception as e:
                return f"Error: {e}"

    def get_cwd(self) -> str:
        return self.cwd

    def get_history(self) -> list[str]:
        return list(self._history)

    def set_cwd(self, path: str):
        if os.path.isdir(path):
            self.cwd = os.path.abspath(path)

    def is_alive(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def close(self):
        if self._proc and self._proc.poll() is None:
            try:
                self._proc.stdin.write("exit\n")
                self._proc.stdin.flush()
                self._proc.wait(timeout=5)
            except Exception:
                try:
                    self._proc.kill()
                except Exception:
                    pass
        self._proc = None
        self._started = False


# ── Singleton ──────────────────────────────────────────────────────────────────

_session: ShellSession | None = None
_lock = threading.Lock()


def get_session(shell: str | None = None) -> ShellSession:
    """Get or create the persistent shell session."""
    global _session
    with _lock:
        if shell:
            shell = _normalize_shell(shell)
        if _session is None or not _session.is_alive():
            _session = ShellSession(shell=shell)
        elif shell and _session.shell != shell:
            close_session()
            _session = ShellSession(shell=shell)
        return _session


def close_session():
    global _session
    with _lock:
        if _session:
            _session.close()
            _session = None


def run_shell_tool(parameters: dict | None = None, player=None) -> str:
    """Tool 'shell_session': sesión bash persistente para moverse libre.
    Acciones: run|cd (command), cwd (establecer base), history, clear,
    env, status. El directorio persiste entre llamadas."""
    parameters = parameters or {}
    action = (parameters.get("action") or "run").lower()
    command = (parameters.get("command") or "").strip()
    shell = _normalize_shell(parameters.get("shell"))
    session = get_session(shell=shell)

    if action in ("clear", "limpiar"):
        session._history.clear()
        return "Historial de la sesión limpiado."

    if action in ("history", "historial"):
        hist = session.get_history()
        if not hist:
            return "Sin comandos en la sesión."
        return "Historial de la sesión:\n" + "\n".join("  $ " + h for h in hist[-25:])

    if action in ("env", "entorno"):
        import os as _os
        keys = sorted(_os.environ)
        out = [f"  {k}={_os.environ[k][:120]}" for k in keys
               if k in ("PATH", "HOME", "SHELL", "PWD", "LANG", "TERM", "USER") or k.startswith("ERIS")]
        return "Entorno de la sesión:\n" + "\n".join(out or ["  (vacío)"])

    if action in ("status", "estado"):
        return (f"Sesión: {session.shell}\n"
                f"CWD: {session.cwd}\n"
                f"Proceso vivo: {session.is_alive()}\n"
                f"Histórico: {len(session.get_history())} comandos\n"
                f"Permisos: usuario real ({os.getlogin() if hasattr(os, 'getlogin') else '?'}), sudo si hace falta")

    if action in ("status", "estado"):
        real_cwd = session.run("pwd", timeout=10)
        if real_cwd and not real_cwd.startswith(("Error", "Directorio", "Timeout")):
            session.cwd = real_cwd.strip()
        return (f"Sesión: {session.shell}\n"
                f"CWD: {session.cwd}\n"
                f"Proceso vivo: {session.is_alive()}\n"
                f"Histórico: {len(session.get_history())} comandos\n"
                f"Permisos: usuario real, sudo si hace falta")

    if action in ("cd", "chdir"):
        target = (parameters.get("cwd") or parameters.get("path") or command or "")
        target = target.strip().rstrip("/") or os.path.expanduser("~")
        if not os.path.isdir(target):
            return f"Directorio no encontrado: {target}"
        session.run(f"cd '{os.path.abspath(target)}'")
        return f"Directorio: {session.cwd}"

    if action == "run":
        if command.startswith("cd ") and len(command) > 3 and os.path.isdir(command[3:].strip()):
            return session.run(command)
        return session.run(command if command else "pwd")

    return ("Acciones: run|cd (con 'command' o 'cwd'), history, clear, env, status.\n"
            f"CWD actual: {session.cwd}")
