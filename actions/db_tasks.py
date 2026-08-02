# -*- coding: utf-8 -*-
"""
db_tasks.py — Gestion de tareas de ERIS (SQLite via eris_db).
Acciones: add, list, update (marcar done/pendiente), delete.
"""
from __future__ import annotations


def db_tasks(parameters: dict = None, player=None) -> str:
    if parameters is None:
        parameters = {}
    action = parameters.get("action", "list").lower()

    try:
        from actions.eris_db import task_add, task_list, task_update, task_delete
    except Exception as e:
        return f"Error: base de tareas no disponible ({e})"

    if action == "add":
        title = (parameters.get("title") or parameters.get("task") or "").strip()
        if not title:
            return "Error: se requiere 'title'."
        priority = parameters.get("priority", "medium")
        due = parameters.get("due_date")
        task_add(title, description=parameters.get("description", ""), priority=priority, due_date=due)
        return f"Tarea agregada: '{title}' (prioridad {priority})"

    if action == "list":
        status = parameters.get("status") or None
        tasks = task_list(status=status, limit=int(parameters.get("limit", 20)))
        if not tasks:
            return "No hay tareas" + (f" con estado '{status}'" if status else "") + "."
        lines = [f"Tareas ({len(tasks)}):"]
        for t in tasks:
            lines.append(f"  #{t.get('id')} [{t.get('status')}] {t.get('title')} (prioridad {t.get('priority')})")
        return "\n".join(lines)

    if action in ("update", "done"):
        try:
            task_id = int(parameters.get("task_id") or parameters.get("id"))
        except (TypeError, ValueError):
            return "Error: se requiere 'task_id' numerico."
        status = parameters.get("status", "done" if action == "done" else None)
        priority = parameters.get("priority")
        task_update(task_id, status=status, priority=priority)
        return f"Tarea #{task_id} actualizada."

    if action == "delete":
        try:
            task_id = int(parameters.get("task_id") or parameters.get("id"))
        except (TypeError, ValueError):
            return "Error: se requiere 'task_id' numerico."
        task_delete(task_id)
        return f"Tarea #{task_id} eliminada."

    return "Acciones: add (title), list (status), update (task_id), delete (task_id)."
