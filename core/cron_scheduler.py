"""Cron scheduler for Eris."""
import json
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_STATE_FILE = _BASE / "memory" / "cron_scheduler.json"

def _load() -> dict:
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"jobs": [], "executions": []}

def _save(data: dict):
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def cron_scheduler_tool(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = params.get("action", "status")
    if action == "status":
        data = _load()
        active = [j for j in data.get("jobs", []) if j.get("active")]
        return json.dumps({"jobs": len(active), "total": len(data.get("jobs", [])), "executions": len(data.get("executions", []))})
    elif action == "add":
        name = params.get("name", "")
        schedule = params.get("schedule", "daily")
        command = params.get("command", "")
        time_str = params.get("time", "09:00")
        if not name or not command:
            return json.dumps({"error": "Name and command required"})
        data = _load()
        job = {"name": name, "schedule": schedule, "command": command, "time": time_str, "active": True, "created": datetime.now().isoformat(), "last_run": None}
        data["jobs"].append(job)
        _save(data)
        return json.dumps({"status": "added", "job": job})
    elif action == "list":
        data = _load()
        return json.dumps({"jobs": data.get("jobs", [])})
    elif action == "remove":
        name = params.get("name", "")
        data = _load()
        data["jobs"] = [j for j in data.get("jobs", []) if j.get("name") != name]
        _save(data)
        return json.dumps({"status": "removed", "name": name})
    elif action == "execute":
        name = params.get("name", "")
        data = _load()
        for j in data.get("jobs", []):
            if j.get("name") == name:
                j["last_run"] = datetime.now().isoformat()
                data.setdefault("executions", []).append({"name": name, "time": datetime.now().isoformat(), "command": j["command"]})
                if len(data["executions"]) > 200:
                    data["executions"] = data["executions"][-200:]
                _save(data)
                return json.dumps({"status": "executed", "command": j["command"]})
        return json.dumps({"error": "Job not found"})
    elif action == "check_due":
        data = _load()
        now = datetime.now()
        due = []
        for j in data.get("jobs", []):
            if not j.get("active"):
                continue
            last = j.get("last_run")
            schedule = j.get("schedule", "daily")
            if not last:
                due.append(j)
                continue
            try:
                last_dt = datetime.fromisoformat(last)
                if schedule == "hourly" and (now - last_dt) > timedelta(hours=1):
                    due.append(j)
                elif schedule == "daily" and (now - last_dt) > timedelta(days=1):
                    due.append(j)
                elif schedule == "weekly" and (now - last_dt) > timedelta(weeks=1):
                    due.append(j)
            except Exception:
                due.append(j)
        return json.dumps({"due": [{"name": j["name"], "command": j["command"]} for j in due], "count": len(due)})
    return json.dumps({"error": "Unknown action"})
