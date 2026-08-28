"""
goal_tracker.py — Persistencia y seguimiento de objetivos a largo plazo.

Permite al agente definir, rastrear y reportar progreso sobre objetivos:
  - Crear objetivos con sub-tareas y milestones
  - Actualizar progreso (porcentaje, estado, notas)
  - Detectar objetivos estancados
  - Siguientes pasos recomendados
"""
from __future__ import annotations

import json
import time
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_GOALS_FILE = _BASE / "data" / "goals.json"

VALID_STATES = ("pending", "active", "blocked", "completed", "abandoned")
VALID_PRIORITIES = ("low", "medium", "high", "critical")


def _load_goals() -> dict:
    try:
        if _GOALS_FILE.exists():
            return json.loads(_GOALS_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"goals": [], "completed_count": 0}


def _save_goals(data: dict):
    try:
        _GOALS_FILE.parent.mkdir(parents=True, exist_ok=True)
        _GOALS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def create_goal(
    title: str,
    description: str = "",
    priority: str = "medium",
    subtasks: list[str] = None,
    milestones: list[str] = None,
) -> dict:
    """Crea un nuevo objetivo."""
    data = _load_goals()
    goal_id = "goal_%d_%d" % (int(time.time()), len(data["goals"]))

    goal = {
        "id": goal_id,
        "title": title,
        "description": description,
        "priority": priority if priority in VALID_PRIORITIES else "medium",
        "state": "active",
        "progress": 0,
        "subtasks": [
            {"id": "st_%d" % i, "text": s, "done": False}
            for i, s in enumerate(subtasks or [])
        ],
        "milestones": [
            {"id": "ms_%d" % i, "text": m, "reached": False}
            for i, m in enumerate(milestones or [])
        ],
        "notes": [],
        "created_at": time.time(),
        "updated_at": time.time(),
        "completed_at": None,
    }
    data["goals"].append(goal)
    _save_goals(data)
    return goal


def update_goal(
    goal_id: str,
    state: str = None,
    progress: int = None,
    note: str = "",
) -> dict:
    """Actualiza un objetivo existente."""
    data = _load_goals()
    for goal in data["goals"]:
        if goal["id"] == goal_id:
            if state and state in VALID_STATES:
                goal["state"] = state
                if state == "completed":
                    goal["progress"] = 100
                    goal["completed_at"] = time.time()
                    data["completed_count"] = data.get("completed_count", 0) + 1
            if progress is not None:
                goal["progress"] = max(0, min(100, progress))
            if note:
                goal["notes"].append({"text": note, "timestamp": time.time()})
                goal["notes"] = goal["notes"][-20:]
            goal["updated_at"] = time.time()
            _save_goals(data)
            return goal
    return {"error": "Goal not found"}


def complete_subtask(goal_id: str, subtask_index: int) -> dict:
    """Marca una sub-tarea como completada."""
    data = _load_goals()
    for goal in data["goals"]:
        if goal["id"] == goal_id:
            if 0 <= subtask_index < len(goal["subtasks"]):
                goal["subtasks"][subtask_index]["done"] = True
                # Recalcular progreso
                total = len(goal["subtasks"])
                done = sum(1 for s in goal["subtasks"] if s["done"])
                goal["progress"] = round(done / total * 100) if total > 0 else 0
                goal["updated_at"] = time.time()
                _save_goals(data)
                return goal
    return {"error": "Goal or subtask not found"}


def reach_milestone(goal_id: str, milestone_index: int) -> dict:
    """Marca un milestone como alcanzado."""
    data = _load_goals()
    for goal in data["goals"]:
        if goal["id"] == goal_id:
            if 0 <= milestone_index < len(goal["milestones"]):
                goal["milestones"][milestone_index]["reached"] = True
                goal["updated_at"] = time.time()
                _save_goals(data)
                return goal
    return {"error": "Goal or milestone not found"}


def get_active_goals() -> list[dict]:
    """Obtiene todos los objetivos activos."""
    data = _load_goals()
    return [g for g in data["goals"] if g["state"] in ("active", "blocked")]


def get_stalled_goals(days: int = 3) -> list[dict]:
    """Objetivos que no se actualizaron en N días."""
    data = _load_goals()
    cutoff = time.time() - (days * 86400)
    stalled = []
    for g in data["goals"]:
        if g["state"] in ("active", "blocked") and g["updated_at"] < cutoff:
            stalled.append(g)
    return stalled


def get_next_step(goal_id: str) -> dict | None:
    """Siguiente sub-tarea recomendada para un objetivo."""
    data = _load_goals()
    for g in data["goals"]:
        if g["id"] == goal_id:
            for i, st in enumerate(g["subtasks"]):
                if not st["done"]:
                    return {"goal_id": goal_id, "subtask_index": i, "text": st["text"]}
            return None
    return None


def delete_goal(goal_id: str) -> bool:
    """Elimina un objetivo."""
    data = _load_goals()
    before = len(data["goals"])
    data["goals"] = [g for g in data["goals"] if g["id"] != goal_id]
    if len(data["goals"]) < before:
        _save_goals(data)
        return True
    return False


def get_summary() -> dict:
    """Resumen de todos los objetivos."""
    data = _load_goals()
    goals = data["goals"]
    return {
        "total": len(goals),
        "active": sum(1 for g in goals if g["state"] == "active"),
        "blocked": sum(1 for g in goals if g["state"] == "blocked"),
        "completed": sum(1 for g in goals if g["state"] == "completed"),
        "abandoned": sum(1 for g in goals if g["state"] == "abandoned"),
        "stalled": len(get_stalled_goals()),
        "avg_progress": round(
            sum(g["progress"] for g in goals if g["state"] in ("active", "blocked"))
            / max(1, sum(1 for g in goals if g["state"] in ("active", "blocked"))),
            1,
        ),
    }


def format_goals() -> str:
    """Formatea objetivos para mostrar."""
    summary = get_summary()
    lines = [
        "Objetivos: %d total (%d activos, %d bloqueados, %d completados, %d abandonados)" % (
            summary["total"], summary["active"], summary["blocked"],
            summary["completed"], summary["abandoned"]),
        "Progreso promedio: %.0f%%" % summary["avg_progress"],
    ]
    if summary["stalled"] > 0:
        lines.append("⚠ %d objetivo(s) estancado(s)" % summary["stalled"])

    for g in get_active_goals():
        bar = "#" * int(g["progress"] / 10) + "-" * (10 - int(g["progress"] / 10))
        icon = "🔒" if g["state"] == "blocked" else "▶"
        lines.append("\n%s [%s] %s (%d%%)" % (icon, g["priority"][:1], g["title"], g["progress"]))
        lines.append("  [%s] %s" % (bar, g["state"]))
        # Sub-tareas pendientes
        pending = [s for s in g["subtasks"] if not s["done"]]
        if pending:
            lines.append("  Pendiente: %s" % pending[0]["text"][:60])
        # Milestones
        ms_done = sum(1 for m in g["milestones"] if m["reached"])
        ms_total = len(g["milestones"])
        if ms_total > 0:
            lines.append("  Milestones: %d/%d" % (ms_done, ms_total))

    return "\n".join(lines)
