"""
core/platform_compat.py
───────────────────────
Una sola forma de pedir "no me abras una ventana de consola".

Problema que resuelve
─────────────────────
`subprocess.CREATE_NO_WINDOW` (0x08000000) y `DETACHED_PROCESS` (0x00000008)
existen SOLO en Windows. El código de Eris los pasaba crudos en decenas de
archivos:

    subprocess.run([...], creationflags=0x08000000)

En Linux eso no es una opción ignorada: `subprocess` valida el parámetro y
levanta `ValueError: creationflags is only supported on Windows platforms`
(según la versión, `TypeError`). El resultado era que herramientas enteras
—`code_analyzer`, `system_monitor`, `terminal_agent`, `vscode_controller`—
quedaban inservibles en Linux, que es la mitad de los sistemas donde el dueño
quiere usar Eris.

Qué NO hace
───────────
No elimina `creationflags`: en Windows sigue siendo necesario para que no
aparezcan consolas negras cada vez que Eris lanza un proceso. Lo que hace es
devolver **0 en Linux** y la bandera real en Windows.

Uso
───
    from core.platform_compat import run_flags
    subprocess.run(cmd, creationflags=run_flags())
    subprocess.Popen(cmd, creationflags=run_flags(detached=True))

`run_flags()` no cuesta nada: en Linux devuelve 0 y `subprocess` lo acepta sin
quejarse.
"""

from __future__ import annotations

import os
import subprocess
import sys

__all__ = [
    "IS_WINDOWS",
    "IS_LINUX",
    "IS_MACOS",
    "CREATE_NO_WINDOW",
    "DETACHED_PROCESS",
    "CREATE_NEW_PROCESS_GROUP",
    "run_flags",
    "detached_flags",
    "home_dir",
    "desktop_dir",
]


# ── Detección de plataforma ──────────────────────────────────────────────────
# `os.name == "nt"` es lo más confiable para el binario; `sys.platform` cubre
# el resto. Se usan los dos para no depender de uno solo.
IS_WINDOWS = os.name == "nt"
IS_LINUX = sys.platform.startswith("linux")
IS_MACOS = sys.platform == "darwin"


# ── Constantes reales de Windows, o 0 fuera de Windows ───────────────────────
# En Windows toman el valor de `subprocess` (que las define); si por lo que sea
# no están, se usan los literales documentados por Microsoft.
CREATE_NO_WINDOW = 0x08000000 if IS_WINDOWS else 0
DETACHED_PROCESS = 0x00000008 if IS_WINDOWS else 0
CREATE_NEW_PROCESS_GROUP = 0x00000200 if IS_WINDOWS else 0


def run_flags(detached: bool = False, new_group: bool = False) -> int:
    """
    `creationflags` portable.

    En Linux/macOS devuelve 0 (`subprocess` lo acepta). En Windows devuelve
    `CREATE_NO_WINDOW`, más `DETACHED_PROCESS` si `detached=True` y
    `CREATE_NEW_PROCESS_GROUP` si `new_group=True`.

    Nota sobre `detached`: en Windows, `CREATE_NO_WINDOW` y `DETACHED_PROCESS`
    son mutuamente excluyentes para apps de consola (documentación de Microsoft).
    El código original los combinaba igual (0x08000010); acá se respeta ese
    comportamiento **a propósito**, para no cambiar semántica, pero queda escrito
    para que se vea.
    """
    if not IS_WINDOWS:
        return 0
    flags = CREATE_NO_WINDOW
    if detached:
        flags |= DETACHED_PROCESS
    if new_group:
        flags |= CREATE_NEW_PROCESS_GROUP
    return flags


def detached_flags() -> int:
    """Atajo para el patrón `CREATE_NO_WINDOW | DETACHED_PROCESS` (0x08000010)."""
    return run_flags(detached=True)


def home_dir():
    """
    Carpeta personal del usuario, portable y sin `KeyError`.

    `agent/task_queue.py` hacía `os.environ["USERPROFILE"]`, que en Linux no
    existe (allí la variable es `HOME`) → `KeyError` al construir la ruta de
    datos. `Path.home()` resuelve ambos.
    """
    from pathlib import Path

    try:
        return Path.home()
    except Exception:
        # Último recurso: variables de entorno de cualquiera de los dos SO.
        raw = (
            os.environ.get("USERPROFILE")
            or os.environ.get("HOME")
            or os.environ.get("HOMEDRIVE", "") + os.environ.get("HOMEPATH", "")
        )
        return Path(raw) if raw else Path.cwd()


def desktop_dir():
    """
    Escritorio del usuario, portable.

    En Linux respeta el estándar XDG (idioma/localización): intenta
    `xdg-user-dir DESKTOP`, y si no, cae a `~/Desktop` o `~/Escritorio`.
    """
    from pathlib import Path

    home = home_dir()

    if IS_WINDOWS:
        cand = home / "Desktop"
        if cand.is_dir():
            return cand
        # Windows localizado (Escritorio)
        alt = home / "Escritorio"
        return alt if alt.is_dir() else cand

    # Linux / macOS: preguntar al estándar XDG.
    try:
        out = subprocess.run(
            ["xdg-user-dir", "DESKTOP"],
            capture_output=True, text=True, timeout=5,
        )
        if out.returncode == 0 and out.stdout.strip():
            cand = Path(out.stdout.strip())
            if cand.is_dir():
                return cand
    except Exception:
        pass

    for name in ("Desktop", "Escritorio", "Escritorio"):
        cand = home / name
        if cand.is_dir():
            return cand
    return home / "Desktop"
