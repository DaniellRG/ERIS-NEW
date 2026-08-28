"""
core/ollama_autostart.py
─────────────────────────
Gestiona el arranque automático de Ollama (cerebro local de respaldo de ERIS).

Objetivos:
  1. `ensure_ollama_running()` — si Ollama no responde, lo arranca en segundo plano
     (oculto). Idempotente: si ya corre, no hace nada.
  2. `enable_autostart()` / `disable_autostart()` — crea/quita un lanzador en la
     carpeta de Inicio de Windows (Startup) para que Ollama arranque solo al iniciar
     sesión. Método sin privilegios de administrador, 100% reversible.
  3. `is_autostart_enabled()` — consulta el estado actual.

Diseño defensivo: nunca lanza excepciones al exterior; devuelve bool/estado.
Compatible con consola cp1252 (sin emojis en salidas críticas).
"""
from __future__ import annotations

import os
import sys
import subprocess
import urllib.request
from pathlib import Path

# ── Rutas ────────────────────────────────────────────────────────────────────
_OLLAMA_EXE_CANDIDATES = [
    Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe",
    Path("C:/Program Files/Ollama/ollama.exe"),
    Path("C:/Users") / os.environ.get("USERNAME", "") / "AppData" / "Local" / "Programs" / "Ollama" / "ollama.exe",
]

_STARTUP_DIR = (
    Path(os.environ.get("APPDATA", ""))
    / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
)
_LAUNCHER_NAME = "eris_ollama_autostart.vbs"
_OLLAMA_URL = "http://localhost:11434/api/tags"


def _find_ollama_exe() -> Path | None:
    """Localiza ollama.exe entre las rutas conocidas."""
    for c in _OLLAMA_EXE_CANDIDATES:
        try:
            if c and c.is_file():
                return c
        except Exception:
            continue
    # último recurso: buscar en PATH
    try:
        from shutil import which
        w = which("ollama")
        if w:
            return Path(w)
    except Exception:
        pass
    return None


def is_ollama_running(timeout: float = 3.0) -> bool:
    """True si el servidor Ollama responde en localhost:11434."""
    try:
        req = urllib.request.Request(_OLLAMA_URL, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


def ensure_ollama_running(wait_secs: float = 6.0) -> bool:
    """
    Garantiza que Ollama esté corriendo. Si ya corre, devuelve True de inmediato.
    Si no, lo arranca oculto y espera hasta `wait_secs` a que responda.
    Devuelve True si al final está vivo.
    """
    if is_ollama_running():
        return True
    exe = _find_ollama_exe()
    if not exe:
        return False
    try:
        # CREATE_NO_WINDOW + DETACHED para que sobreviva al proceso padre y no abra consola
        creationflags = 0
        if sys.platform == "win32":
            creationflags = 0x08000000 | 0x00000008  # CREATE_NO_WINDOW | DETACHED_PROCESS
        subprocess.Popen(
            [str(exe), "serve"],
            creationflags=creationflags,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            close_fds=True,
        )
    except Exception:
        return False
    # esperar a que levante
    import time
    deadline = time.time() + max(1.0, wait_secs)
    while time.time() < deadline:
        if is_ollama_running(timeout=2.0):
            return True
        time.sleep(1.0)
    return is_ollama_running()


# ── Autostart en Windows (carpeta Startup) ───────────────────────────────────
def _launcher_path() -> Path:
    return _STARTUP_DIR / _LAUNCHER_NAME


def enable_autostart() -> bool:
    """
    Crea un lanzador .vbs en la carpeta de Inicio de Windows que arranca Ollama
    oculto al iniciar sesión. Reversible con disable_autostart(). Sin admin.
    Devuelve True si quedó habilitado.
    """
    if sys.platform != "win32":
        return False
    exe = _find_ollama_exe()
    if not exe:
        return False
    try:
        _STARTUP_DIR.mkdir(parents=True, exist_ok=True)
        # VBS: arranca ollama serve en modo oculto (0 = ventana invisible)
        vbs = (
            'Set WShell = CreateObject("WScript.Shell")\r\n'
            f'WShell.Run """{exe}"" serve", 0, False\r\n'
        )
        _launcher_path().write_text(vbs, encoding="utf-8")
        return True
    except Exception:
        return False


def disable_autostart() -> bool:
    """Quita el lanzador de la carpeta de Inicio. Devuelve True si ya no existe."""
    try:
        p = _launcher_path()
        if p.exists():
            p.unlink()
        return not p.exists()
    except Exception:
        return False


def is_autostart_enabled() -> bool:
    """True si el lanzador de autostart existe en la carpeta de Inicio."""
    try:
        return _launcher_path().is_file()
    except Exception:
        return False


def apply_autostart(enabled: bool) -> bool:
    """Sincroniza el estado del autostart con el flag `enabled`."""
    return enable_autostart() if enabled else disable_autostart()


if __name__ == "__main__":
    # Utilidad de línea de comandos para diagnóstico manual
    import json
    action = sys.argv[1] if len(sys.argv) > 1 else "status"
    if action == "enable":
        print(json.dumps({"enabled": enable_autostart(), "path": str(_launcher_path())}))
    elif action == "disable":
        print(json.dumps({"disabled": disable_autostart()}))
    elif action == "ensure":
        print(json.dumps({"running": ensure_ollama_running()}))
    else:
        print(json.dumps({
            "ollama_exe": str(_find_ollama_exe()),
            "running": is_ollama_running(),
            "autostart_enabled": is_autostart_enabled(),
            "launcher": str(_launcher_path()),
        }))
