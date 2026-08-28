"""
core/contextual_awareness.py — Conciencia contextual para Eris

Eris sabe que hora es, que hace Daniel, clima, bateria, etc.
"""
import json
import os
import psutil
import subprocess
from datetime import datetime
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_MEMORY = _BASE / "memory"
_STATE_FILE = _MEMORY / "contextual_awareness_state.json"


def get_time_context() -> dict:
    now = datetime.now()
    hour = now.hour
    if 6 <= hour < 12:
        period = "manana"
    elif 12 <= hour < 18:
        period = "tarde"
    elif 18 <= hour < 22:
        period = "noche"
    else:
        period = "madrugada"
    return {
        "time": now.strftime("%H:%M"),
        "date": now.strftime("%Y-%m-%d"),
        "day": now.strftime("%A"),
        "period": period,
        "hour": hour,
    }


def get_battery() -> dict:
    try:
        battery = psutil.sensors_battery()
        if battery:
            return {
                "percent": battery.percent,
                "plugged": battery.power_plugged,
                "charging": battery.power_plugged,
            }
    except Exception:
        pass
    return {"percent": -1, "plugged": True, "note": "Sin datos de bateria"}


def get_system_resources() -> dict:
    try:
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        disk_c = psutil.disk_usage("C:\\") if os.path.exists("C:\\") else None
        disk_d = psutil.disk_usage("D:\\") if os.path.exists("D:\\") else None

        return {
            "cpu_percent": cpu,
            "ram_percent": mem.percent,
            "ram_used_gb": round(mem.used / 1024**3, 2),
            "ram_total_gb": round(mem.total / 1024**3, 2),
            "disk_c_free_gb": round(disk_c.free / 1024**3, 2) if disk_c else None,
            "disk_d_free_gb": round(disk_d.free / 1024**3, 2) if disk_d else None,
        }
    except Exception as e:
        return {"error": str(e)}


def get_running_processes() -> dict:
    try:
        procs = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                info = proc.info
                if info.get('cpu_percent', 0) > 1 or info.get('memory_percent', 0) > 1:
                    procs.append({
                        "name": info['name'],
                        "cpu": round(info.get('cpu_percent', 0), 1),
                        "ram": round(info.get('memory_percent', 0), 1),
                    })
            except Exception:
                pass
        procs.sort(key=lambda x: x.get('cpu', 0), reverse=True)
        return {"top_processes": procs[:10]}
    except Exception as e:
        return {"error": str(e)}


def get_full_context() -> dict:
    """Retorna el contexto completo de Eris."""
    return {
        "time": get_time_context(),
        "battery": get_battery(),
        "system": get_system_resources(),
        "processes": get_running_processes(),
        "timestamp": datetime.now().isoformat(),
    }


def contextual_awareness_tool(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = params.get("action", "status")

    if action == "status":
        return json.dumps(get_full_context(), indent=2, default=str)
    elif action == "time":
        return json.dumps(get_time_context(), indent=2)
    elif action == "battery":
        return json.dumps(get_battery(), indent=2)
    elif action == "system":
        return json.dumps(get_system_resources(), indent=2, default=str)
    elif action == "processes":
        return json.dumps(get_running_processes(), indent=2, default=str)

    return json.dumps({"error": "Accion desconocida: {}".format(action)})


if __name__ == "__main__":
    print("=== Test Contextual Awareness ===")
    print(contextual_awareness_tool({"action": "status"}))
