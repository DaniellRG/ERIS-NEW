"""
core/windows_service.py — Servicio de Windows para Eris

Permite que Eris corra como servicio del sistema.
"""
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_MEMORY = _BASE / "memory"
_STATE_FILE = _MEMORY / "windows_service_state.json"
_SCRIPT = _BASE / "start_eris_service.bat"


def _load_state() -> dict:
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"installed": False, "running": False, "last_check": None}


def _save_state(state: dict):
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def install_service() -> dict:
    """Instala Eris como servicio de Windows usando NSSM."""
    try:
        nssm_path = _BASE / "tools" / "nssm.exe"
        if not nssm_path.exists():
            return {
                "error": "NSSM no encontrado. Descarga de: https://nssm.cc/download",
                "manual": "Ejecuta: nssm install Eris \"{}\" \"{}\"".format(
                    sys.executable, str(_BASE / "main.py")
                ),
            }

        python_path = sys.executable
        main_path = str(_BASE / "main.py")
        result = subprocess.run(
            [str(nssm_path), "install", "Eris", python_path, main_path],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            subprocess.run(
                [str(nssm_path), "set", "Eris", "AppDirectory", str(_BASE)],
                capture_output=True, timeout=10
            )
            state = _load_state()
            state["installed"] = True
            _save_state(state)
            return {"status": "instalado", "message": "Eris instalado como servicio Windows"}
        return {"error": "Error instalando: {}".format(result.stderr[:200])}
    except Exception as e:
        return {"error": str(e)}


def start_service() -> dict:
    try:
        result = subprocess.run(
            ["net", "start", "Eris"],
            capture_output=True, text=True, timeout=15
        )
        state = _load_state()
        state["running"] = result.returncode == 0
        _save_state(state)
        if result.returncode == 0:
            return {"status": "iniciado"}
        return {"error": result.stderr[:200]}
    except Exception as e:
        return {"error": str(e)}


def stop_service() -> dict:
    try:
        result = subprocess.run(
            ["net", "stop", "Eris"],
            capture_output=True, text=True, timeout=15
        )
        state = _load_state()
        state["running"] = False
        _save_state(state)
        return {"status": "detenido"} if result.returncode == 0 else {"error": result.stderr[:200]}
    except Exception as e:
        return {"error": str(e)}


def get_service_status() -> dict:
    state = _load_state()
    try:
        result = subprocess.run(
            ["sc", "query", "Eris"],
            capture_output=True, text=True, timeout=10
        )
        running = "RUNNING" in result.stdout
        state["running"] = running
        state["last_check"] = datetime.now().isoformat()
        _save_state(state)
    except Exception:
        pass
    return {
        "installed": state.get("installed", False),
        "running": state.get("running", False),
        "last_check": state.get("last_check"),
    }


def create_startup_script() -> dict:
    """Crea un .bat para iniciar Eris manualmente."""
    bat_content = '@echo off\n'
    bat_content += 'title ERIS - Autonomo\n'
    bat_content += 'cd /d "{}"\n'.format(_BASE)
    bat_content += '"{}" main.py\n'.format(sys.executable)
    bat_content += 'pause\n'
    _SCRIPT.write_text(bat_content, encoding="utf-8")
    return {"status": "script_creado", "file": str(_SCRIPT)}


def service_tool(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = params.get("action", "status")

    if action == "status":
        return json.dumps(get_service_status(), indent=2)
    elif action == "install":
        return json.dumps(install_service(), indent=2)
    elif action == "start":
        return json.dumps(start_service(), indent=2)
    elif action == "stop":
        return json.dumps(stop_service(), indent=2)
    elif action == "create_script":
        return json.dumps(create_startup_script(), indent=2)

    return json.dumps({"error": "Accion desconocida: {}".format(action)})


if __name__ == "__main__":
    print("=== Test Windows Service ===")
    print(service_tool({"action": "status"}))
