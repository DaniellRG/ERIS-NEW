# -*- coding: utf-8 -*-
"""
task_manager.py — Gestor de tareas tipo Kanban con dependencias y deadlines.
Acciones:
  add     — Agregar tarea
  list    — Listar tareas (filtro opcional: pending/in_progress/done/blocked/all)
  update  — Actualizar tarea
  move    — Mover tarea a otro estado
  delete  — Eliminar tarea
  search  — Buscar tareas
  overdue — Tareas vencidas
  stats   — Estadísticas
  dependencies — Listar dependencias de una tarea
Storage: data/tasks.json
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_TASKS_FILE = Path(r"D:\Eris_Source\data\tasks.json")

VALID_STATES = ["pending", "in_progress", "done", "blocked", "review"]
VALID_PRIORITIES = ["low", "medium", "high", "urgent"]


def _load() -> list[dict]:
    if _TASKS_FILE.exists():
        try:
            return json.loads(_TASKS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def _save(tasks: list[dict]):
    _TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _TASKS_FILE.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")


def _find(tasks: list[dict], task_id: str) -> dict | None:
    for t in tasks:
        if t.get("id") == task_id or t.get("id", "").startswith(task_id):
            return t
    return None


def _next_id(tasks):
    nums = []
    for t in tasks:
        try:
            nums.append(int(t.get("id", "t-0").split("-")[1]))
        except (ValueError, IndexError):
            pass
    return f"t-{max(nums, default=0) + 1}"


def _format_task(t):
    state_emoji = {"pending": "⏳", "in_progress": "🔄", "done": "✅", "blocked": "🚫", "review": "👀"}
    prio_emoji = {"urgent": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
    e = state_emoji.get(t.get("state", "pending"), "⏳")
    p = prio_emoji.get(t.get("priority", "medium"), "🟡")
    line = f"{e} **{t['id']}** {p} {t.get('title', 'Sin título')}"
    if t.get("deadline"):
        line += f" ⏰ {t['deadline'][:10]}"
    if t.get("deps"):
        line += f" → depende de: {', '.join(t['deps'])}"
    return line


def task_manager(parameters: dict = None, player=None) -> str:
    """Tool: Gestor de tareas Kanban con dependencias y deadlines."""
    params = parameters or {}
    action = str(params.get("action", "list")).lower().strip()
    tasks = _load()

    if action == "add":
        title = str(params.get("title", "")).strip()
        if not title:
            return "Necesitás un título."
        priority = str(params.get("priority", "medium")).lower().strip()
        if priority not in VALID_PRIORITIES:
            priority = "medium"
        desc = str(params.get("description", "")).strip()
        deadline = str(params.get("deadline", "")).strip()
        deps = params.get("deps", [])
        if isinstance(deps, str):
            deps = [d.strip() for d in deps.split(",") if d.strip()]
        tags = params.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]
        tid = _next_id(tasks)
        task = {
            "id": tid, "title": title, "description": desc,
            "state": "pending", "priority": priority,
            "deadline": deadline, "deps": deps, "tags": tags,
            "created": datetime.now(timezone.utc).isoformat(),
            "updated": datetime.now(timezone.utc).isoformat(),
        }
        tasks.append(task)
        _save(tasks)
        return f"✅ Tarea creada: {_format_task(task)}"

    if action == "list":
        state_filter = str(params.get("state", "all")).lower().strip()
        if state_filter == "all":
            filtered = tasks
        else:
            filtered = [t for t in tasks if t.get("state") == state_filter]
        if not filtered:
            return f"Sin tareas{f' en estado {state_filter}' if state_filter != 'all' else ''}."
        lines = [f"**Tareas ({len(filtered)}):**\n"]
        for t in sorted(filtered, key=lambda x: {"urgent": 0, "high": 1, "medium": 2, "low": 3}.get(x.get("priority", "medium"), 2)):
            lines.append(_format_task(t))
        return "\n".join(lines)

    if action == "move":
        tid = str(params.get("task_id", "")).strip()
        new_state = str(params.get("state", "")).lower().strip()
        if not tid or new_state not in VALID_STATES:
            return f"task_id y state válido ({'/'.join(VALID_STATES)})."
        task = _find(tasks, tid)
        if not task:
            return f"Tarea {tid} no encontrada."
        if new_state == "done":
            blocked = [t for t in tasks if tid in t.get("deps", []) and t.get("state") != "done"]
            for b in blocked:
                b["deps"] = [d for d in b["deps"] if d != tid]
        task["state"] = new_state
        task["updated"] = datetime.now(timezone.utc).isoformat()
        _save(tasks)
        return f"✅ {_format_task(task)}"

    if action == "update":
        tid = str(params.get("task_id", "")).strip()
        task = _find(tasks, tid)
        if not task:
            return f"Tarea {tid} no encontrada."
        for key in ("title", "description", "priority", "deadline", "tags"):
            if key in params and params[key] is not None:
                task[key] = params[key]
        task["updated"] = datetime.now(timezone.utc).isoformat()
        _save(tasks)
        return f"✅ Actualizada: {_format_task(task)}"

    if action == "delete":
        tid = str(params.get("task_id", "")).strip()
        task = _find(tasks, tid)
        if not task:
            return f"Tarea {tid} no encontrada."
        tasks = [t for t in tasks if t.get("id") != task["id"]]
        _save(tasks)
        return f"🗑️ Eliminada: {task.get('title', tid)}"

    if action == "overdue":
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        overdue = [t for t in tasks if t.get("deadline") and t["deadline"][:10] < now_str and t.get("state") != "done"]
        if not overdue:
            return "✅ Sin tareas vencidas."
        lines = [f"**🔴 {len(overdue)} tareas vencidas:**\n"]
        for t in overdue:
            lines.append(_format_task(t))
        return "\n".join(lines)

    if action == "search":
        query = str(params.get("query", "")).lower().strip()
        if not query:
            return "Necesitás un término."
        found = [t for t in tasks if query in t.get("title", "").lower() or query in t.get("description", "").lower() or any(query in tag.lower() for tag in t.get("tags", []))]
        if not found:
            return f"Sin resultados para '{query}'"
        lines = [f"**Resultados ({len(found)}):**\n"]
        for t in found:
            lines.append(_format_task(t))
        return "\n".join(lines)

    if action == "stats":
        states = {}
        for t in tasks:
            s = t.get("state", "pending")
            states[s] = states.get(s, 0) + 1
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        overdue = sum(1 for t in tasks if t.get("deadline") and t["deadline"][:10] < now_str and t.get("state") != "done")
        lines = [f"**Stats:** {len(tasks)} total\n"]
        for s in VALID_STATES:
            if s in states:
                lines.append(f"  {s}: {states[s]}")
        if overdue:
            lines.append(f"  🔴 vencidas: {overdue}")
        return "\n".join(lines)

    return "Acciones: add, list, move, update, delete, overdue, search, stats"
