"""scheduler.py — Programador de tareas (persistido; sobrevive reinicios)."""
import json
import re
import threading
import time
from pathlib import Path

_tasks = {}
_counter = 0

_DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "scheduler_tasks.json"


def _load_store() -> dict:
    try:
        if _DATA_FILE.exists():
            data = json.loads(_DATA_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {}


def _save_store(store: dict) -> None:
    try:
        _DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        _DATA_FILE.write_text(json.dumps(store, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def _fire(task_id, message, player=None):
    try:
        if player is not None and hasattr(player, "write_log"):
            player.write_log(f"[TAREA] {message}")
        else:
            print(f"[TAREA] {message}")
    except Exception:
        pass
    _tasks.pop(task_id, None)
    store = _load_store()
    if task_id in store:
        del store[task_id]
        _save_store(store)


def _rearm(player=None) -> None:
    """Re-arma tareas persistidas tras un reinicio (futuras / vencidas)."""
    store = _load_store()
    now = time.time()
    changed = False
    for tid in list(store):
        if tid in _tasks:
            continue
        entry = store[tid]
        fire_at = float(entry.get("fire_at", 0) or 0)
        msg = str(entry.get("message", "Tarea programada"))
        if fire_at <= now:
            _fire(tid, msg, player)
            del store[tid]
            changed = True
        else:
            t = threading.Timer(fire_at - now, _fire, args=[tid, msg, player])
            t.daemon = True
            t.start()
            _tasks[tid] = (t, msg)
    if changed:
        _save_store(store)


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

    _rearm(player)

    if action in ("add", "schedule"):
        if not task_id:
            _counter += 1
            task_id = f"tarea_{int(time.time())}_{_counter}"
        task_id = str(task_id)
        if task_id in _tasks:  # regenerar si el id colisiona con uno persistido
            _tasks[task_id][0].cancel()
        fire_at = time.time() + max(1, delay)
        t = threading.Timer(max(1, delay), _fire, args=[task_id, message, player])
        t.daemon = True
        t.start()
        _tasks[task_id] = (t, message)
        store = _load_store()
        store[task_id] = {"message": message, "fire_at": fire_at}
        _save_store(store)
        if delay >= 3600:
            return f"Tarea '{task_id}' programada en {delay / 3600:.1f} horas."
        if delay >= 60:
            return f"Tarea '{task_id}' programada en {delay / 60:.1f} minutos."
        return f"Tarea '{task_id}' programada en {delay} segundos."

    if action in ("remove", "delete", "cancel"):
        if task_id in _tasks:
            _tasks[task_id][0].cancel()
            del _tasks[task_id]
        store = _load_store()
        if task_id in store:
            del store[task_id]
            _save_store(store)
        return f"Tarea '{task_id}' cancelada."

    if action == "list":
        if not _tasks and not _load_store():
            return "No hay tareas programadas."
        lines = [f"Tareas programadas ({len(_tasks)}):"]
        for tid, (_, msg) in _tasks.items():
            lines.append(f"  - {tid}: {msg}")
        return "\n".join(lines)

    if action == "clear":
        for t, _ in _tasks.values():
            t.cancel()
        _tasks.clear()
        _save_store({})
        return "Todas las tareas canceladas."

    return "Acciones: add, remove, list, clear"


def start_runner(player=None, speak=None) -> None:
    """Lanza el re-armado de tareas persistidas (compatibilidad)."""
    _rearm(player)