"""
core/goal_setting.py — Sistema de metas autonomas para Eris

Eris define sus propias metas basandose en su estado actual,
las prioriza, y las persigue sin que le digan.
"""
import json
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from core.logging_setup import get_obsidian_vault

_BASE = Path(__file__).resolve().parent.parent
_MEMORY = _BASE / "memory"
_STATE_FILE = _MEMORY / "goals.json"
_LOG_FILE = _MEMORY / "goals_log.json"
_OBSIDIAN_VAULT = get_obsidian_vault()

PRIORITY_WEIGHTS = {"critical": 4, "high": 3, "medium": 2, "low": 1}


def _load_goals() -> dict:
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"goals": [], "completed": [], "auto_generated": []}


def _save_goals(data: dict):
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


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


def create_goal(title: str, priority: str = "medium", deadline: str = "", category: str = "general") -> dict:
    data = _load_goals()
    goal_id = "goal_{}".format(uuid.uuid4().hex[:8])
    goal = {
        "id": goal_id,
        "title": title,
        "priority": priority,
        "category": category,
        "status": "active",
        "progress": 0,
        "created": datetime.now().isoformat(),
        "deadline": deadline or (datetime.now() + timedelta(days=7)).isoformat(),
        "milestones": [],
    }
    data["goals"].append(goal)
    _save_goals(data)
    _log("create", "Meta creada: {} ({})".format(title, priority))
    return goal


def list_goals(status: str = "active") -> list:
    data = _load_goals()
    if status == "all":
        return data["goals"] + data.get("completed", [])
    if status == "completed":
        return data.get("completed", [])
    return [g for g in data["goals"] if g.get("status") == status]


def update_goal(goal_id: str, progress: int = -1, status: str = "", milestone: str = "") -> dict:
    data = _load_goals()
    for goal in data["goals"]:
        if goal["id"] == goal_id:
            if progress >= 0:
                goal["progress"] = min(100, progress)
            if status:
                goal["status"] = status
            if milestone:
                goal.setdefault("milestones", []).append({
                    "text": milestone,
                    "timestamp": datetime.now().isoformat(),
                })
            if goal["progress"] >= 100 or goal.get("status") == "completed":
                goal["status"] = "completed"
                goal["completed_at"] = datetime.now().isoformat()
                data["completed"].append(goal)
                data["goals"].remove(goal)
            _save_goals(data)
            _log("update", "Meta actualizada: {}".format(goal["title"]))
            return goal
    return {"error": "Meta no encontrada"}


def evaluate_goals() -> dict:
    data = _load_goals()
    now = datetime.now()
    results = {"active": 0, "overdue": 0, "completed_today": 0, "actions": []}

    for goal in data["goals"]:
        results["active"] += 1
        try:
            deadline = datetime.fromisoformat(goal.get("deadline", ""))
            if now > deadline and goal["status"] == "active":
                results["overdue"] += 1
                results["actions"].append("Meta vencida: {}".format(goal["title"]))
        except Exception:
            pass

    for goal in data.get("completed", []):
        try:
            completed_at = datetime.fromisoformat(goal.get("completed_at", ""))
            if completed_at.date() == now.date():
                results["completed_today"] += 1
        except Exception:
            pass

    return results


def auto_generate_goals() -> list:
    existing_titles = set()
    new_goals = []

    # Meta 1: Aprender topics nuevos
    auto_file = _MEMORY / "autonomy_state.json"
    learned = 0
    if auto_file.exists():
        try:
            auto_state = json.loads(auto_file.read_text(encoding="utf-8"))
            learned = len(auto_state.get("learned_topics", []))
        except Exception:
            pass

    data = _load_goals()
    existing_titles = {g["title"] for g in data["goals"]}

    if learned < 10:
        title = "Aprender al menos 10 topics nuevos de curiosidad"
        if title not in existing_titles:
            g = create_goal(title, "high", category="learning")
            new_goals.append(g)
            existing_titles.add(title)

    # Meta 2: Realizar mejoras de codigo
    sm_file = _MEMORY / "self_modify_state.json"
    changes = 0
    if sm_file.exists():
        try:
            sm_state = json.loads(sm_file.read_text(encoding="utf-8"))
            changes = sm_state.get("total_changes", 0)
        except Exception:
            pass

    if changes < 3:
        title = "Realizar al menos 3 mejoras de codigo auto"
        if title not in existing_titles:
            g = create_goal(title, "medium", category="self_improvement")
            new_goals.append(g)
            existing_titles.add(title)

    # Meta 3: Documentar capacidades en Obsidian
    obsidian_caps = (_OBSIDIAN_VAULT / "Capacidades")
    if obsidian_caps.exists():
        docs = list(obsidian_caps.glob("*.md"))
        if len(docs) < 30:
            title = "Documentar todas las capacidades en Obsidian (30+ docs)"
            if title not in existing_titles:
                g = create_goal(title, "medium", category="documentation")
                new_goals.append(g)
                existing_titles.add(title)

    # Meta 4: Mantener memoria limpia
    title = "Ejecutar limpieza de memoria semanal"
    if title not in existing_titles:
        g = create_goal(title, "low", category="maintenance")
        new_goals.append(g)
        existing_titles.add(title)

    # Meta 5: Consolidar memoria
    title = "Consolidar memoria episodica y semantica"
    if title not in existing_titles:
        g = create_goal(title, "medium", category="memory")
        new_goals.append(g)
        existing_titles.add(title)

    # Meta 6: Mejorar voz y expresion
    title = "Mejorar personalidad de voz y expresion"
    if title not in existing_titles:
        g = create_goal(title, "low", category="voice")
        new_goals.append(g)
        existing_titles.add(title)

    return new_goals


def get_goal_status() -> dict:
    data = _load_goals()
    return {
        "active": len([g for g in data["goals"] if g["status"] == "active"]),
        "completed": len(data.get("completed", [])),
        "overdue": sum(1 for g in data["goals"]
                       if g["status"] == "active" and _is_overdue(g)),
        "total": len(data["goals"]) + len(data.get("completed", [])),
    }


def _is_overdue(goal: dict) -> bool:
    try:
        deadline = datetime.fromisoformat(goal.get("deadline", ""))
        return datetime.now() > deadline
    except Exception:
        return False


def goal_setting_tool(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = params.get("action", "status")

    if action == "status":
        return json.dumps(get_goal_status(), indent=2)

    elif action == "create":
        title = params.get("title", "")
        if not title:
            return json.dumps({"error": "Title requerido"})
        priority = params.get("priority", "medium")
        deadline = params.get("deadline", "")
        category = params.get("category", "general")
        goal = create_goal(title, priority, deadline, category)
        return json.dumps(goal, indent=2)

    elif action == "list":
        status = params.get("status", "active")
        goals = list_goals(status)
        return json.dumps({"goals": goals, "count": len(goals)}, indent=2)

    elif action == "update":
        goal_id = params.get("goal_id", "")
        if not goal_id:
            return json.dumps({"error": "goal_id requerido"})
        progress = params.get("progress", -1)
        status = params.get("status", "")
        milestone = params.get("milestone", "")
        result = update_goal(goal_id, progress, status, milestone)
        return json.dumps(result, indent=2)

    elif action == "evaluate":
        return json.dumps(evaluate_goals(), indent=2)

    elif action == "auto_generate":
        new_goals = auto_generate_goals()
        return json.dumps({"new_goals": len(new_goals), "goals": new_goals}, indent=2)

    return json.dumps({"error": "Accion desconocida: {}".format(action)})


if __name__ == "__main__":
    print("=== Test Goal Setting ===")
    print(goal_setting_tool({"action": "status"}))
    r = json.loads(goal_setting_tool({"action": "auto_generate"}))
    print("Auto-generated:", r["new_goals"])
