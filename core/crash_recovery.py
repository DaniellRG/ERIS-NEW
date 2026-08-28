"""
core/crash_recovery.py — Auto-reinicio si Eris crashea

Monitorea el proceso y lo reinicia si se cae.
"""
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_MEMORY = _BASE / "memory"
_STATE_FILE = _MEMORY / "crash_recovery_state.json"
_LOG_FILE = _MEMORY / "crash_recovery_log.json"

MAX_RESTARTS_PER_HOUR = 5
MONITOR_INTERVAL = 30


def _load_state() -> dict:
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "restarts_today": 0,
        "total_restarts": 0,
        "last_crash": None,
        "crash_history": [],
        "last_reset": datetime.now().isoformat(),
    }


def _save_state(state: dict):
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def _log(action: str, details: str):
    entry = {"timestamp": datetime.now().isoformat(), "action": action, "details": details[:200]}
    logs = []
    if _LOG_FILE.exists():
        try:
            logs = json.loads(_LOG_FILE.read_text(encoding="utf-8"))
        except Exception:
            logs = []
    logs.append(entry)
    if len(logs) > 100:
        logs = logs[-100:]
    _LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    _LOG_FILE.write_text(json.dumps(logs, indent=2, ensure_ascii=False), encoding="utf-8")


def check_eris_running() -> dict:
    """Verifica si Eris esta corriendo (python.exe o pythonw.exe)."""
    try:
        pids = []
        for exe in ("python.exe", "pythonw.exe"):
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq " + exe, "/FO", "CSV"],
                capture_output=True, text=True, timeout=10
            )
            lines = result.stdout.strip().split("\n")
            for l in lines:
                parts = l.split(",")
                if len(parts) >= 2 and exe in l.lower():
                    pid = parts[1].strip('"')
                    if pid.isdigit() and pid not in pids:
                        pids.append(pid)

        return {
            "running": len(pids) > 0,
            "eris_processes": len(pids),
            "pids": pids,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"running": False, "error": str(e)}


def restart_eris() -> dict:
    """Reinicia Eris si se cae."""
    state = _load_state()

    now = datetime.now()
    recent_crashes = [c for c in state.get("crash_history", [])
                      if (now - datetime.fromisoformat(c)).total_seconds() < 3600]
    if len(recent_crashes) >= MAX_RESTARTS_PER_HOUR:
        return {"error": "Demasiados reinicios (max {}/hora)".format(MAX_RESTARTS_PER_HOUR)}

    try:
        main_py = _BASE / "main.py"
        python_exe = sys.executable
        subprocess.Popen(
            [python_exe, str(main_py)],
            cwd=str(_BASE),
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )

        state["restarts_today"] += 1
        state["total_restarts"] += 1
        state["last_crash"] = datetime.now().isoformat()
        state.setdefault("crash_history", []).append(datetime.now().isoformat())
        if len(state["crash_history"]) > 50:
            state["crash_history"] = state["crash_history"][-50:]
        _save_state(state)
        _log("restart", "Eris reiniciada PID: {}".format(os.getpid()))
        return {"status": "reiniciado", "pid": os.getpid()}
    except Exception as e:
        _log("restart_error", str(e))
        return {"error": str(e)}


def get_crash_status() -> dict:
    state = _load_state()
    return {
        "restarts_today": state.get("restarts_today", 0),
        "total_restarts": state.get("total_restarts", 0),
        "last_crash": state.get("last_crash"),
        "max_per_hour": MAX_RESTARTS_PER_HOUR,
    }


def crash_recovery_tool(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = params.get("action", "status")

    if action == "status":
        return json.dumps(get_crash_status(), indent=2)
    elif action == "check":
        return json.dumps(check_eris_running(), indent=2)
    elif action == "restart":
        return json.dumps(restart_eris(), indent=2)

    return json.dumps({"error": "Accion desconocida: {}".format(action)})


if __name__ == "__main__":
    print("=== Test Crash Recovery ===")
    print(crash_recovery_tool({"action": "status"}))
    print(crash_recovery_tool({"action": "check"}))
