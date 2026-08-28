"""
scheduler.py — Programación de tareas y recordatorios.

Permite crear tareas programadas:
  - "Recordame hacer X en Y minutos"
  - "Hacé X cada Y horas"
  - "Ejecutá X cuando pase Y condición"
  - Lista de tareas pendientes y su estado
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from datetime import datetime

_BASE = Path(__file__).resolve().parent.parent
_SCHEDULE_FILE = _BASE / "data" / "schedule.json"

TASK_TYPES = ("once", "interval", "daily", "weekly", "on_condition")
TASK_STATES = ("pending", "active", "completed", "expired", "cancelled")


def _load_schedule() -> dict:
    try:
        if _SCHEDULE_FILE.exists():
            return json.loads(_SCHEDULE_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"tasks": [], "history": []}


def _save_schedule(data: dict):
    try:
        _SCHEDULE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _SCHEDULE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def create_task(
    description: str,
    task_type: str = "once",
    execute_at: float = None,
    interval_seconds: int = 0,
    action_tool: str = "",
    action_params: dict = None,
    recurring: bool = False,
    max_runs: int = 1,
) -> dict:
    """Crea una tarea programada.

    Args:
        description: Descripción de la tarea
        task_type: once, interval, daily, weekly, on_condition
        execute_at: Timestamp para ejecutar (para 'once')
        interval_seconds: Intervalo (para 'interval')
        action_tool: Tool a ejecutar
        action_params: Parámetros para la tool
        recurring: Si se repite después de ejecutarse
        max_runs: Máximo de ejecuciones
    """
    data = _load_schedule()
    task_id = "task_%d_%d" % (int(time.time()), len(data["tasks"]))

    now = time.time()
    task = {
        "id": task_id,
        "description": description,
        "task_type": task_type if task_type in TASK_TYPES else "once",
        "state": "active",
        "execute_at": execute_at,
        "interval_seconds": interval_seconds,
        "last_run": None,
        "run_count": 0,
        "max_runs": max_runs,
        "recurring": recurring,
        "action_tool": action_tool,
        "action_params": action_params or {},
        "created_at": now,
        "updated_at": now,
    }
    data["tasks"].append(task)
    _save_schedule(data)
    return task


def create_reminder(description: str, minutes: int = 60) -> dict:
    """Convenience: crear un recordatorio rápido."""
    execute_at = time.time() + (minutes * 60)
    return create_task(
        description="RECORDATORIO: %s" % description,
        task_type="once",
        execute_at=execute_at,
    )


def create_recurring(description: str, interval_seconds: int, max_runs: int = 10) -> dict:
    """Crea tarea recurrente."""
    return create_task(
        description=description,
        task_type="interval",
        interval_seconds=interval_seconds,
        recurring=True,
        max_runs=max_runs,
    )


def get_due_tasks() -> list[dict]:
    """Obtiene tareas que deben ejecutarse ahora."""
    data = _load_schedule()
    now = time.time()
    due = []

    for task in data["tasks"]:
        if task["state"] != "active":
            continue
        if task["task_type"] == "once" and task.get("execute_at"):
            if now >= task["execute_at"]:
                due.append(task)
        elif task["task_type"] == "interval" and task.get("interval_seconds"):
            last = task.get("last_run") or task.get("created_at", 0)
            if now >= last + task["interval_seconds"]:
                if task.get("run_count", 0) < task.get("max_runs", 1):
                    due.append(task)
    return due


def mark_executed(task_id: str) -> bool:
    """Marca una tarea como ejecutada."""
    data = _load_schedule()
    for task in data["tasks"]:
        if task["id"] == task_id:
            task["last_run"] = time.time()
            task["run_count"] = task.get("run_count", 0) + 1

            if not task.get("recurring") or task["run_count"] >= task.get("max_runs", 1):
                task["state"] = "completed"
            elif task["task_type"] == "once":
                task["state"] = "completed"

            task["updated_at"] = time.time()

            # Agregar al historial
            data["history"].append({
                "task_id": task_id,
                "description": task.get("description", ""),
                "executed_at": time.time(),
                "run_count": task["run_count"],
            })
            data["history"] = data["history"][-100:]

            _save_schedule(data)
            return True
    return False


def cancel_task(task_id: str) -> bool:
    """Cancela una tarea."""
    data = _load_schedule()
    for task in data["tasks"]:
        if task["id"] == task_id:
            task["state"] = "cancelled"
            task["updated_at"] = time.time()
            _save_schedule(data)
            return True
    return False


def delete_task(task_id: str) -> bool:
    """Elimina una tarea."""
    data = _load_schedule()
    before = len(data["tasks"])
    data["tasks"] = [t for t in data["tasks"] if t["id"] != task_id]
    if len(data["tasks"]) < before:
        _save_schedule(data)
        return True
    return False


def get_active_tasks() -> list[dict]:
    """Obtiene tareas activas."""
    data = _load_schedule()
    return [t for t in data["tasks"] if t["state"] == "active"]


def get_pending_reminders() -> list[dict]:
    """Recordatorios pendientes (once, no ejecutados)."""
    data = _load_schedule()
    now = time.time()
    return [
        t for t in data["tasks"]
        if t["state"] == "active" and t["task_type"] == "once"
        and t.get("execute_at") and t["execute_at"] > now
    ]


def get_history(limit: int = 20) -> list[dict]:
    """Historial de ejecuciones."""
    data = _load_schedule()
    return data.get("history", [])[-limit:]


def format_schedule() -> str:
    """Formatea agenda para mostrar."""
    active = get_active_tasks()
    reminders = get_pending_reminders()
    due = get_due_tasks()

    lines = [
        "Agenda: %d tareas activas, %d recordatorios pendientes, %d para ejecutar ahora" % (
            len(active), len(reminders), len(due)),
    ]

    if reminders:
        lines.append("\nRecordatorios próximos:")
        for r in sorted(reminders, key=lambda x: x.get("execute_at", 0)):
            remaining = (r.get("execute_at", 0) - time.time()) / 60
            if remaining > 60:
                time_str = "%.1f horas" % (remaining / 60)
            else:
                time_str = "%.0f minutos" % remaining
            lines.append("  ⏰ %s (en %s)" % (r.get("description", "")[:60], time_str))

    if due:
        lines.append("\nPara ejecutar ahora:")
        for d in due:
            lines.append("  ▶ %s" % d.get("description", "")[:60])

    recurring = [t for t in active if t["task_type"] == "interval"]
    if recurring:
        lines.append("\nRecurrentes:")
        for r in recurring:
            interval = r.get("interval_seconds", 0)
            if interval >= 3600:
                ival = "%.1fh" % (interval / 3600)
            else:
                ival = "%dm" % (interval / 60)
            lines.append("  🔄 %s (cada %s, %d/%d ejecutadas)" % (
                r.get("description", "")[:50], ival,
                r.get("run_count", 0), r.get("max_runs", 1)))

    return "\n".join(lines)
