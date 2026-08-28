"""
core/resource_manager.py — Gestion de recursos para Eris

Limpieza de memoria, optimizacion de cache, verificacion de disco.
"""
import json
import os
import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_MEMORY = _BASE / "memory"
_DATA = _BASE / "data"
_STATE_FILE = _MEMORY / "resource_manager_state.json"
_LOG_FILE = _MEMORY / "resource_manager_log.json"

# Dias para considerar archivos viejos
OLD_FILE_DAYS = 30
# Tamano maximo del log (bytes)
MAX_LOG_SIZE = 1_000_000


def _load_state() -> dict:
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"last_cleanup": None, "files_cleaned": 0, "space_freed": 0}


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
    if len(logs) > 50:
        logs = logs[-50:]
    _LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    _LOG_FILE.write_text(json.dumps(logs, indent=2, ensure_ascii=False), encoding="utf-8")


def cleanup_memory() -> dict:
    """Limpia archivos viejos de memoria."""
    results = {"files_cleaned": 0, "space_freed": 0, "details": []}
    cutoff = datetime.now() - timedelta(days=OLD_FILE_DAYS)

    for mem_file in _MEMORY.glob("*.json"):
        if mem_file.name.startswith("_"):
            continue
        try:
            mtime = datetime.fromtimestamp(mem_file.stat().st_mtime)
            if mtime < cutoff:
                size = mem_file.stat().st_size
                mem_file.unlink()
                results["files_cleaned"] += 1
                results["space_freed"] += size
                results["details"].append("Eliminado: {} ({} bytes)".format(mem_file.name, size))
        except Exception:
            pass

    backup_dir = _MEMORY / "self_modify_backups"
    if backup_dir.exists():
        cutoff_backups = datetime.now() - timedelta(days=7)
        for bak in backup_dir.glob("*.py"):
            try:
                mtime = datetime.fromtimestamp(bak.stat().st_mtime)
                if mtime < cutoff_backups:
                    bak.unlink()
                    results["files_cleaned"] += 1
            except Exception:
                pass

    _log("cleanup", "Limpiados {} archivos, {} bytes".format(
        results["files_cleaned"], results["space_freed"]
    ))

    state = _load_state()
    state["last_cleanup"] = datetime.now().isoformat()
    state["files_cleaned"] += results["files_cleaned"]
    state["space_freed"] += results["space_freed"]
    _save_state(state)

    return results


def optimize_cache() -> dict:
    """Optimiza archivos de cache y logs grandes."""
    results = {"files_optimized": 0, "space_freed": 0}

    log_files = [
        _BASE / "eris.log",
        _BASE / "logs" / "eris.log",
    ]
    for log_file in log_files:
        if log_file.exists() and log_file.stat().st_size > MAX_LOG_SIZE:
            content = log_file.read_text(encoding="utf-8", errors="ignore")
            lines = content.split("\n")
            kept = lines[-500:]
            log_file.write_text("\n".join(kept), encoding="utf-8")
            results["files_optimized"] += 1
            results["space_freed"] += len(content) - len("\n".join(kept))

    _log("optimize", "Optimizados {} archivos".format(results["files_optimized"]))
    return results


def disk_check() -> dict:
    """Verifica espacio en disco."""
    results = {"partitions": []}
    for partition in ["C:\\", "D:\\"]:
        try:
            usage = shutil.disk_usage(partition)
            results["partitions"].append({
                "drive": partition,
                "total_gb": round(usage.total / (1024**3), 2),
                "free_gb": round(usage.free / (1024**3), 2),
                "used_percent": round((usage.used / usage.total) * 100, 1),
                "low": usage.free < 5 * 1024**3,
            })
        except Exception:
            pass

    results["memory_files"] = len(list(_MEMORY.glob("*")))
    results["data_files"] = len(list(_DATA.glob("*"))) if _DATA.exists() else 0

    return results


def get_resource_status() -> dict:
    state = _load_state()
    disk = disk_check()
    return {
        "last_cleanup": state.get("last_cleanup"),
        "total_cleaned": state.get("files_cleaned", 0),
        "total_space_freed": state.get("space_freed", 0),
        "disk": disk,
    }


def resource_manager_tool(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = params.get("action", "status")

    if action == "status":
        return json.dumps(get_resource_status(), indent=2)
    elif action == "cleanup":
        return json.dumps(cleanup_memory(), indent=2)
    elif action == "optimize":
        return json.dumps(optimize_cache(), indent=2)
    elif action == "disk_check":
        return json.dumps(disk_check(), indent=2, default=str)

    return json.dumps({"error": "Accion desconocida: {}".format(action)})


if __name__ == "__main__":
    print("=== Test Resource Manager ===")
    print(resource_manager_tool({"action": "status"}))
    print(resource_manager_tool({"action": "disk_check"}))
