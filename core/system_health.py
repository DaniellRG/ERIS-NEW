"""System health dashboard for Eris."""
import json
import psutil
import time
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_MEMORY = _BASE / "memory"

def system_health_tool(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = params.get("action", "status")
    if action == "status":
        cpu = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        disk_c = psutil.disk_usage("C:\\") if Path("C:\\").exists() else None
        disk_d = psutil.disk_usage("D:\\") if Path("D:\\").exists() else None
        net = psutil.net_io_counters()
        boot = psutil.boot_time()
        uptime_hours = round((time.time() - boot) / 3600, 1)
        return json.dumps({
            "cpu_percent": cpu,
            "cpu_count": psutil.cpu_count(),
            "ram_percent": mem.percent,
            "ram_used_gb": round(mem.used / 1024**3, 2),
            "ram_total_gb": round(mem.total / 1024**3, 2),
            "disk_c_free_gb": round(disk_c.free / 1024**3, 2) if disk_c else None,
            "disk_d_free_gb": round(disk_d.free / 1024**3, 2) if disk_d else None,
            "net_sent_mb": round(net.bytes_sent / 1024**2, 1),
            "net_recv_mb": round(net.bytes_recv / 1024**2, 1),
            "uptime_hours": uptime_hours,
            "processes": len(psutil.pids()),
        })
    elif action == "top_processes":
        procs = []
        for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
            try:
                info = p.info
                if info.get("cpu_percent", 0) > 0.5:
                    procs.append({"pid": info["pid"], "name": info["name"], "cpu": round(info["cpu_percent"], 1), "ram": round(info["memory_percent"], 1)})
            except Exception:
                pass
        procs.sort(key=lambda x: x["cpu"], reverse=True)
        return json.dumps({"processes": procs[:15]})
    elif action == "battery":
        try:
            bat = psutil.sensors_battery()
            if bat:
                return json.dumps({"percent": bat.percent, "plugged": bat.power_plugged, "seconds_left": bat.secsleft})
        except Exception:
            pass
        return json.dumps({"percent": -1, "note": "No battery data"})
    elif action == "temperature":
        try:
            temps = psutil.sensors_temperatures()
            result = {}
            for name, entries in temps.items():
                result[name] = [{"label": e.label, "current": e.current, "high": e.high} for e in entries[:5]]
            return json.dumps({"temperatures": result})
        except Exception:
            return json.dumps({"note": "Temperature sensors not available"})
    return json.dumps({"error": "Unknown action"})
