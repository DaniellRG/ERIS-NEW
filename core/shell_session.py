"""
core/shell_session.py — Persistent interactive shell for ERIS.

Replaces fire-and-forget subprocess.run() with a live, persistent shell
that maintains state between commands (cwd, env, session).
"""
from __future__ import annotations

import os
import subprocess
import threading
import time
import queue
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
MAX_OUTPUT = 50_000


class ShellSession:
    """Persistent PowerShell session with streaming output."""

    def __init__(self, shell: str = "powershell", cwd: str | None = None):
        self.shell = shell
        self.cwd = cwd or str(BASE_DIR)
        self._proc = None
        self._lock = threading.Lock()
        self._env = os.environ.copy()
        self._started = False

    def _start(self):
        if self._proc and self._proc.poll() is None:
            return
        cmd = (
            ["powershell", "-NoProfile", "-NoLogo", "-Interactive"]
            if self.shell == "powershell"
            else ["cmd"]
        )
        self._proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=self.cwd,
            env=self._env,
            creationflags=0x08000000,
            bufsize=1,
        )
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
        with self._lock:
            try:
                self._start()
                marker = f"___ERIS_END_{os.getpid()}_{int(time.time()*1000)}___"
                # cd handling for PowerShell
                if command.strip().lower().startswith("cd "):
                    path = command.strip()[3:].strip().strip('"').strip("'")
                    if os.path.isdir(path):
                        self.cwd = os.path.abspath(path)
                        self._send_raw(f"cd '{self.cwd}'; echo '{marker}'\n")
                    else:
                        return f"Directorio no encontrado: {path}"
                else:
                    self._send_raw(f"{command}; echo '{marker}'\n")

                output = self._read_until(marker, timeout=timeout)
                # Clean output: remove marker and command echo
                lines = output.split("\n")
                clean = []
                skip_first = True
                for line in lines:
                    if marker in line:
                        break
                    if skip_first and command.strip() in line:
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
        with self._lock:
            try:
                self._start()
                marker = f"___ERIS_STREAM_{os.getpid()}_{int(time.time()*1000)}___"
                self._send_raw(f"{command}; echo '{marker}'\n")

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


def get_session(shell: str = "powershell") -> ShellSession:
    """Get or create the persistent shell session."""
    global _session
    with _lock:
        if _session is None or not _session.is_alive():
            _session = ShellSession(shell=shell)
        return _session


def close_session():
    global _session
    with _lock:
        if _session:
            _session.close()
            _session = None
