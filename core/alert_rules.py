"""Alert rules for Eris."""
import json
import psutil
from pathlib import Path
from datetime import datetime

_BASE = Path(__file__).resolve().parent.parent
_STATE_FILE = _BASE / "memory" / "alert_rules.json"

def _load() -> dict:
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"rules": [], "triggered": []}

def _save(data: dict):
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def alert_rules_tool(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = params.get("action", "status")
    if action == "status":
        data = _load()
        return json.dumps({"rules": len(data.get("rules", [])), "triggered": len(data.get("triggered", []))})
    elif action == "add":
        name = params.get("name", "")
        metric = params.get("metric", "cpu")
        threshold = params.get("threshold", 90)
        condition = params.get("condition", "above")
        if not name:
            return json.dumps({"error": "Name required"})
        data = _load()
        rule = {"name": name, "metric": metric, "threshold": threshold, "condition": condition, "created": datetime.now().isoformat(), "active": True}
        data["rules"].append(rule)
        _save(data)
        return json.dumps({"status": "added", "rule": rule})
    elif action == "list":
        data = _load()
        return json.dumps({"rules": data.get("rules", [])})
    elif action == "check":
        data = _load()
        alerts = []
        cpu = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory().percent
        for rule in data.get("rules", []):
            if not rule.get("active"):
                continue
            metric = rule.get("metric", "cpu")
            value = cpu if metric == "cpu" else mem if metric == "ram" else 0
            threshold = rule.get("threshold", 90)
            cond = rule.get("condition", "above")
            triggered = (cond == "above" and value > threshold) or (cond == "below" and value < threshold)
            if triggered:
                alert = {"rule": rule["name"], "metric": metric, "value": value, "threshold": threshold, "time": datetime.now().isoformat()}
                alerts.append(alert)
                data.setdefault("triggered", []).append(alert)
                if len(data["triggered"]) > 100:
                    data["triggered"] = data["triggered"][-100:]
        _save(data)
        return json.dumps({"alerts": alerts, "cpu": cpu, "ram": mem})
    elif action == "remove":
        name = params.get("name", "")
        data = _load()
        data["rules"] = [r for r in data.get("rules", []) if r.get("name") != name]
        _save(data)
        return json.dumps({"status": "removed", "name": name})
    return json.dumps({"error": "Unknown action"})
