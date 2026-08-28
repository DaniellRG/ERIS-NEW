"""Workflow builder for Eris."""
import json
from pathlib import Path
from datetime import datetime

_BASE = Path(__file__).resolve().parent.parent
_STATE_FILE = _BASE / "memory" / "workflows.json"

def _load() -> dict:
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"workflows": []}

def _save(data: dict):
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def workflow_builder_tool(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = params.get("action", "status")
    if action == "status":
        data = _load()
        return json.dumps({"workflows": len(data.get("workflows", []))})
    elif action == "create":
        name = params.get("name", "")
        steps = params.get("steps", [])
        if not name:
            return json.dumps({"error": "Name required"})
        data = _load()
        wf = {"name": name, "steps": steps, "created": datetime.now().isoformat(), "active": True, "runs": 0}
        data["workflows"].append(wf)
        _save(data)
        return json.dumps({"status": "created", "workflow": wf})
    elif action == "list":
        data = _load()
        return json.dumps({"workflows": data.get("workflows", [])})
    elif action == "execute":
        name = params.get("name", "")
        data = _load()
        for wf in data.get("workflows", []):
            if wf.get("name") == name:
                results = []
                for i, step in enumerate(wf.get("steps", [])):
                    step_type = step.get("type", "log")
                    step_desc = step.get("description", "step {}".format(i+1))
                    results.append({"step": i+1, "type": step_type, "description": step_desc, "status": "executed"})
                wf["runs"] = wf.get("runs", 0) + 1
                wf["last_run"] = datetime.now().isoformat()
                _save(data)
                return json.dumps({"status": "completed", "results": results, "total_steps": len(results)})
        return json.dumps({"error": "Workflow not found"})
    elif action == "remove":
        name = params.get("name", "")
        data = _load()
        data["workflows"] = [w for w in data.get("workflows", []) if w.get("name") != name]
        _save(data)
        return json.dumps({"status": "removed", "name": name})
    return json.dumps({"error": "Unknown action"})
