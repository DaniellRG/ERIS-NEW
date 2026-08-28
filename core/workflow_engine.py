"""
ERIS Workflow Engine — Flujos si/sino con triggers automáticos.
Define workflows que se ejecutan cuando se cumplen condiciones.
"""
import json
import time
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "workflows"
_DATA_DIR.mkdir(parents=True, exist_ok=True)

_WORKFLOWS_FILE = _DATA_DIR / "workflows.json"
_LOG_FILE = _DATA_DIR / "workflow_log.json"


def _load_workflows() -> dict:
    if _WORKFLOWS_FILE.exists():
        with open(_WORKFLOWS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"workflows": []}


def _save_workflows(data: dict):
    with open(_WORKFLOWS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _log(workflow_name: str, action: str, result: str):
    logs = []
    if _LOG_FILE.exists():
        with open(_LOG_FILE, "r", encoding="utf-8") as f:
            logs = json.load(f)
    logs.append({"workflow": workflow_name, "action": action, "result": result, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    logs = logs[-500:]
    with open(_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)


def create_workflow(name: str, trigger_type: str, trigger_config: dict,
                    condition: str = "", actions: list = None, enabled: bool = True) -> dict:
    wf_data = _load_workflows()
    for wf in wf_data["workflows"]:
        if wf["name"] == name:
            return {"ok": False, "error": f"Workflow '{name}' ya existe."}
    workflow = {
        "name": name,
        "trigger_type": trigger_type,  # time, event, threshold, manual
        "trigger_config": trigger_config,
        "condition": condition,
        "actions": actions or [],
        "enabled": enabled,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "last_run": None,
        "run_count": 0,
    }
    wf_data["workflows"].append(workflow)
    _save_workflows(wf_data)
    return {"ok": True, "name": name}


def evaluate_condition(condition: str, context: dict) -> bool:
    """Evaluate a simple condition string with context variables."""
    if not condition:
        return True
    try:
        # Safe evaluation with limited builtins
        return bool(eval(condition, {"__builtins__": {}}, context))
    except Exception:
        return False


def run_workflow(name: str, context: dict = None) -> dict:
    wf_data = _load_workflows()
    for wf in wf_data["workflows"]:
        if wf["name"] == name:
            if not wf["enabled"]:
                return {"ok": False, "error": "Workflow deshabilitado."}
            if not evaluate_condition(wf.get("condition", ""), context or {}):
                return {"ok": True, "skipped": True, "reason": "Condición no cumplida."}
            results = []
            for action in wf.get("actions", []):
                action_type = action.get("type", "")
                action_desc = action.get("description", action_type)
                results.append(f"  Ejecutado: {action_desc}")
            wf["last_run"] = time.strftime("%Y-%m-%d %H:%M:%S")
            wf["run_count"] += 1
            _save_workflows(wf_data)
            _log(name, "run", "; ".join(results))
            return {"ok": True, "actions_executed": len(results), "results": results}
    return {"ok": False, "error": f"Workflow '{name}' no encontrado."}


def list_workflows() -> list:
    return _load_workflows()["workflows"]


def toggle_workflow(name: str, enabled: bool) -> dict:
    wf_data = _load_workflows()
    for wf in wf_data["workflows"]:
        if wf["name"] == name:
            wf["enabled"] = enabled
            _save_workflows(wf_data)
            return {"ok": True, "name": name, "enabled": enabled}
    return {"ok": False, "error": "Not found."}


def delete_workflow(name: str) -> dict:
    wf_data = _load_workflows()
    before = len(wf_data["workflows"])
    wf_data["workflows"] = [w for w in wf_data["workflows"] if w["name"] != name]
    if len(wf_data["workflows"]) < before:
        _save_workflows(wf_data)
        return {"ok": True, "deleted": name}
    return {"ok": False, "error": "Not found."}


def get_logs(limit: int = 10) -> list:
    if _LOG_FILE.exists():
        with open(_LOG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)[-limit:]
    return []


def workflow_engine_tool(parameters: dict = None, player=None) -> str:
    """Tool entry point."""
    params = parameters or {}
    action = params.get("action", "list").lower()

    if action == "create":
        name = params.get("name", "")
        if not name:
            return "Necesito 'name'."
        trigger = params.get("trigger", "manual")
        result = create_workflow(
            name=name,
            trigger_type=trigger,
            trigger_config=json.loads(params.get("config", "{}")),
            condition=params.get("condition", ""),
            actions=json.loads(params.get("actions", "[]")),
        )
        return f"Workflow '{name}' creado." if result["ok"] else result["error"]

    elif action == "run":
        name = params.get("name", "")
        result = run_workflow(name)
        if result.get("skipped"):
            return f"Workflow '{name}' saltado: {result['reason']}"
        return f"Workflow '{name}': {result['actions_executed']} acciones ejecutadas." if result["ok"] else result["error"]

    elif action == "list":
        wfs = list_workflows()
        if not wfs:
            return "No hay workflows."
        return "Workflows:\n" + "\n".join(
            f"  [{'ON' if w['enabled'] else 'OFF'}] {w['name']} (trigger: {w['trigger_type']}, runs: {w['run_count']})"
            for w in wfs
        )

    elif action == "toggle":
        name = params.get("name", "")
        enabled = params.get("enabled", "true").lower() == "true"
        result = toggle_workflow(name, enabled)
        return f"Workflow '{name}' {'habilitado' if enabled else 'deshabilitado'}." if result["ok"] else result["error"]

    elif action == "delete":
        name = params.get("name", "")
        result = delete_workflow(name)
        return f"Workflow '{name}' eliminado." if result["ok"] else result["error"]

    elif action == "logs":
        limit = int(params.get("limit", 10))
        logs = get_logs(limit)
        if not logs:
            return "Sin logs."
        return "Logs:\n" + "\n".join(f"  [{l['time']}] {l['workflow']}: {l['result']}" for l in logs)

    return f"Acción '{action}' no reconocida. Usa: create, run, list, toggle, delete, logs"
