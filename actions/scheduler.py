"""scheduler.py — Programador de tareas en memoria (al estilo alarm_manager)."""
import re
import threading
import time

_tasks = {}
_counter = 0


def _fire(task_id, message, player=None):
    try:
        if player is not None and hasattr(player, "write_log"):
            player.write_log(f"[TAREA] {message}")
        else:
            print(f"[TAREA] {message}")
    except Exception:
        pass
    _tasks.pop(task_id, None)


def _parse_delay(raw):
    if raw is None:
        return 60
    m = re.search(r"(\d+)\s*(hora|horas|hs?|min|mins?|minuto|seg|segs?|segundo)", str(raw).lower())
    if m:
        n = int(m.group(1))
        u = m.group(2)
        if u.startswith("h"):
            return n * 3600
        if u.startswith("min") or u.startswith("minuto"):
            return n * 60
        return n
    try:
        n = float(raw)
        return int(n * 60 if n < 100 else n)
    except Exception:
        return 60


def scheduler(parameters: dict, player=None, speak=None) -> str:
    """Programa tareas: add, remove, list, clear."""
    global _counter
    params = parameters or {}
    action = (params.get("action") or "add").lower()
    task_id = (params.get("task_id") or params.get("id") or params.get("name") or "").strip()
    message = params.get("message") or params.get("task") or "Tarea programada"
    delay = _parse_delay(params.get("delay") or params.get("time") or params.get("when"))

    if action in ("add", "schedule"):
        if not task_id:
            _counter += 1
            task_id = f"tarea_{int(time.time())}_{_counter}"
        t = threading.Timer(max(1, delay), _fire, args=[task_id, message, player])
        t.daemon = True
        t.start()
        _tasks[task_id] = (t, message)
        if delay >= 3600:
            return f"Tarea '{task_id}' programada en {delay / 3600:.1f} horas."
        if delay >= 60:
            return f"Tarea '{task_id}' programada en {delay / 60:.1f} minutos."
        return f"Tarea '{task_id}' programada en {delay} segundos."

    if action in ("remove", "delete", "cancel"):
        if task_id in _tasks:
            _tasks[task_id][0].cancel()
            del _tasks[task_id]
            return f"Tarea '{task_id}' cancelada."
        return f"No existe la tarea '{task_id}'."

    if action == "list":
        if not _tasks:
            return "No hay tareas programadas."
        lines = [f"Tareas programadas ({len(_tasks)}):"]
        for tid, (_, msg) in _tasks.items():
            lines.append(f"  - {tid}: {msg}")
        return "\n".join(lines)

    if action == "clear":
        for t, _ in _tasks.values():
            t.cancel()
        _tasks.clear()
        return "Todas las tareas canceladas."

    return "Acciones: add, remove, list, clear"


def start_runner(player=None, speak=None) -> None:
    """No-op mantenido por compatibilidad."""
    pass
