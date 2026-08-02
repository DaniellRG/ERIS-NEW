import json
import threading
from pathlib import Path
from datetime import datetime

_QUEUE_FILE = Path(__file__).resolve().parent.parent / "data" / "task_queue.json"
_LOCK = threading.Lock()


def task_queue(parameters: dict = None, player=None) -> str:
    if parameters is None:
        parameters = {}
    action = parameters.get("action", "list").strip().lower()

    if action == "add":
        task = parameters.get("task", "").strip()
        priority = int(parameters.get("priority", 0))
        if not task:
            return "Error: Debes especificar 'task'."
        with _LOCK:
            queue = _load()
            queue.append({
                "id": len(queue) + 1,
                "task": task,
                "priority": priority,
                "status": "pending",
                "created": datetime.now().isoformat(),
            })
            queue.sort(key=lambda x: (-x["priority"], x["id"]))
            _save(queue)
        return "Tarea agregada: {} (prioridad {})".format(task[:80], priority)

    elif action == "list":
        with _LOCK:
            queue = _load()
        if not queue:
            return "No hay tareas en la cola."
        lines = ["Cola de tareas ({}):".format(len(queue))]
        for t in queue:
            status_icon = "[OK]" if t["status"] == "done" else "[...]" if t["status"] == "running" else "[  ]"
            lines.append("  #{} {} prioridad={} {}".format(t["id"], status_icon, t["priority"], t["task"][:80]))
        return "\n".join(lines)

    elif action == "run_next":
        with _LOCK:
            queue = _load()
            pending = [t for t in queue if t["status"] == "pending"]
            if not pending:
                return "No hay tareas pendientes."
            task = pending[0]
            task["status"] = "running"
            _save(queue)
        result = _execute_task(task, player)
        with _LOCK:
            queue = _load()
            for t in queue:
                if t["id"] == task["id"]:
                    t["status"] = "done"
                    t["result"] = result[:200]
                    t["completed"] = datetime.now().isoformat()
            _save(queue)
        return "Tarea #{} completada:\n{}".format(task["id"], result[:300])

    elif action == "run_all":
        results = []
        while True:
            with _LOCK:
                queue = _load()
                pending = [t for t in queue if t["status"] == "pending"]
                if not pending:
                    break
                task = pending[0]
                task["status"] = "running"
                _save(queue)
            result = _execute_task(task, player)
            with _LOCK:
                queue = _load()
                for t in queue:
                    if t["id"] == task["id"]:
                        t["status"] = "done"
                        t["result"] = result[:200]
                        t["completed"] = datetime.now().isoformat()
                _save(queue)
            results.append("#{}: {}".format(task["id"], result[:100]))
        if not results:
            return "No habia tareas pendientes."
        return "Ejecutadas {} tareas:\n{}".format(len(results), "\n".join(results))

    elif action == "clear":
        with _LOCK:
            _save([])
        return "Cola de tareas vaciada."

    elif action == "remove":
        task_id = int(parameters.get("id", 0))
        with _LOCK:
            queue = _load()
            queue = [t for t in queue if t["id"] != task_id]
            _save(queue)
        return "Tarea #{} eliminada.".format(task_id)

    elif action == "stats":
        with _LOCK:
            queue = _load()
        total = len(queue)
        pending = len([t for t in queue if t["status"] == "pending"])
        running = len([t for t in queue if t["status"] == "running"])
        done = len([t for t in queue if t["status"] == "done"])
        return "Tareas: {} total, {} pendientes, {} en curso, {} completadas.".format(total, pending, running, done)

    return "Acciones: add (agregar), list (listar), run_next (ejecutar siguiente), run_all (ejecutar todas), clear (vaciar), remove (eliminar), stats (estadisticas)."


def _execute_task(task: dict, player) -> str:
    text = task["task"]
    try:
        from actions.auto_agent import auto_agent
        result = auto_agent({"action": "execute", "goal": text}, player)
        return str(result)[:500]
    except Exception as e:
        return "Error: {}".format(str(e)[:80])


def _load() -> list:
    if _QUEUE_FILE.exists():
        try:
            return json.loads(_QUEUE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def _save(queue: list):
    _QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _QUEUE_FILE.write_text(json.dumps(queue, indent=2, ensure_ascii=False), encoding="utf-8")
