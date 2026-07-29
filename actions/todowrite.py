"""
actions/todowrite.py — Task list tracker for ERIS.
Create, update, and track todo items during a session.
"""
import json
import time
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_TODO_FILE = _DATA_DIR / "todowrite.json"

def todowrite(parameters: dict, player=None) -> str:
    action = (parameters.get("action") or "").lower()
    content = parameters.get("content", [])
    status = parameters.get("status", "")
    item_id = parameters.get("item_id", "")
    priority = parameters.get("priority", "")

    todos = _load()

    if action in ("list", "ver", "status"):
        return _list(todos)

    elif action in ("add", "agregar", "new", "nuevo"):
        if isinstance(content, str):
            content = [content]
        if not content:
            return "Necesito 'content' (texto o lista) para agregar"
        for item in content:
            if isinstance(item, dict):
                todos.append(item)
            else:
                todos.append({
                    "id": _next_id(todos),
                    "content": str(item),
                    "status": status or "pending",
                    "priority": priority or "medium",
                    "created": time.strftime("%Y-%m-%d %H:%M"),
                })
        _save(todos)
        return f"Agregados {len(content)} items a la lista. Total: {len(todos)}"

    elif action in ("update", "actualizar", "in_progress", "completed", "done", "cancelled"):
        if item_id:
            for t in todos:
                if str(t.get("id")) == str(item_id):
                    t["status"] = action if action in ("in_progress", "completed", "done", "cancelled") else (status or "completed")
                    t["updated"] = time.strftime("%Y-%m-%d %H:%M")
                    _save(todos)
                    return f"Item {item_id}: {t['status']}"
            return f"Item {item_id} no encontrado"
        elif action in ("in_progress", "completed", "done", "cancelled"):
            for t in todos:
                if t.get("status") != "completed" and t.get("status") != "cancelled":
                    t["status"] = action if action != "done" else "completed"
                    t["updated"] = time.strftime("%Y-%m-%d %H:%M")
            _save(todos)
            return f"Todos los items pendientes marcados como {action}"
        else:
            return "Especifica 'item_id' para actualizar"

    elif action in ("delete", "remove", "eliminar", "clear", "limpiar"):
        if action == "clear" or action == "limpiar":
            todos.clear()
            _save(todos)
            return "Lista de tareas limpiada"
        if item_id:
            before = len(todos)
            todos = [t for t in todos if str(t.get("id")) != str(item_id)]
            _save(todos)
            return f"Item {item_id} eliminado ({before - len(todos)} items)"
        return "Especifica 'item_id' o 'clear'"

    elif action in ("count", "contar"):
        pend = sum(1 for t in todos if t.get("status") in ("pending", "in_progress"))
        done = sum(1 for t in todos if t.get("status") == "completed")
        return f"Pendientes: {pend} | Completados: {done} | Total: {len(todos)}"

    else:
        actions = [
            "list", "add (content=)", "update (item_id=, status=)",
            "delete (item_id=)", "clear", "in_progress", "completed", "cancelled", "count"
        ]
        return f"Acciones todowrite: {', '.join(actions)}"


def _load() -> list:
    try:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        if _TODO_FILE.exists():
            return json.loads(_TODO_FILE.read_text("utf-8"))
    except Exception:
        pass
    return []


def _save(todos: list):
    try:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        _TODO_FILE.write_text(json.dumps(todos, indent=2, ensure_ascii=False), "utf-8")
    except Exception:
        pass


def _list(todos: list) -> str:
    if not todos:
        return "No hay tareas pendientes."
    lines = [f"Lista de tareas ({len(todos)}):", ""]
    status_icons = {"pending": "⏳", "in_progress": "🔄", "completed": "✅", "cancelled": "❌"}
    priority_icons = {"high": "🔴", "medium": "🟡", "low": "🟢"}
    for t in todos:
        sid = t.get("id", "?")
        s = t.get("status", "pending")
        p = t.get("priority", "medium")
        icon = status_icons.get(s, "⏳")
        picon = priority_icons.get(p, "🟡")
        c = t.get("content", "?")
        lines.append(f"  {icon} [{sid}] {picon} {c} ({s})")
    return "\n".join(lines)


def _next_id(todos: list) -> int:
    return max([t.get("id", 0) for t in todos] or [0]) + 1
