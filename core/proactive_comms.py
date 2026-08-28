"""
core/proactive_comms.py — Comunicacion proactiva de Eris

Eris busca a Daniel cuando algo importante pase.
"""
import json
import time
from datetime import datetime
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_MEMORY = _BASE / "memory"
_STATE_FILE = _MEMORY / "proactive_comms_state.json"
_LOG_FILE = _MEMORY / "proactive_comms_log.json"


def _load_state() -> dict:
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "notifications_sent": 0,
        "last_notification": None,
        "sent_topics": [],
    }


def _save_state(state: dict):
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def _log(action: str, details: str):
    entry = {"timestamp": datetime.now().isoformat(), "action": action, "details": details[:200]}
    logs = []
    if _LOG_FILE.exists():
        try:
            logs = json.loads(_LOG_FILE.read_text(encoding="utf-8"))
        except Exception:
            logs = []
    logs.append(entry)
    if len(logs) > 50:
        logs = logs[-50:]
    _LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    _LOG_FILE.write_text(json.dumps(logs, indent=2, ensure_ascii=False), encoding="utf-8")


def check_important_events() -> list:
    """Verifica si hay eventos importantes que notificar."""
    events = []

    # 1. Metas vencidas
    goals_file = _MEMORY / "goals.json"
    if goals_file.exists():
        try:
            goals = json.loads(goals_file.read_text(encoding="utf-8"))
            for goal in goals.get("goals", []):
                if goal.get("status") == "active":
                    try:
                        deadline = datetime.fromisoformat(goal.get("deadline", ""))
                        if datetime.now() > deadline:
                            events.append({
                                "type": "goal_overdue",
                                "priority": "high",
                                "message": "Meta vencida: {}".format(goal.get("title", "")),
                            })
                    except Exception:
                        pass
        except Exception:
            pass

    # 2. Errores de auto-reparo fallidos
    sm_log = _MEMORY / "self_modify_log.json"
    if sm_log.exists():
        try:
            logs = json.loads(sm_log.read_text(encoding="utf-8"))
            recent_fails = [l for l in logs[-10:] if not l.get("success", True)]
            if len(recent_fails) >= 3:
                events.append({
                    "type": "repair_failures",
                    "priority": "medium",
                    "message": "Multiples fallos de auto-reparo recientes",
                })
        except Exception:
            pass

    # 3. Espacio en disco bajo
    import shutil
    try:
        usage = shutil.disk_usage("C:\\")
        if usage.free < 5 * 1024**3:
            events.append({
                "type": "low_disk",
                "priority": "high",
                "message": "Poco espacio en disco: {:.1f} GB libres".format(usage.free / 1024**3),
            })
    except Exception:
        pass

    # 4. Topics de curiosidad aprendidos hoy
    auto_state = _MEMORY / "autonomy_state.json"
    if auto_state.exists():
        try:
            state = json.loads(auto_state.read_text(encoding="utf-8"))
            learned = state.get("learning_topics_today", 0)
            if learned >= 5:
                events.append({
                    "type": "learning_milestone",
                    "priority": "low",
                    "message": "Ya aprendi {} topics hoy!".format(learned),
                })
        except Exception:
            pass

    return events


def notify_daniel(message: str, priority: str = "medium") -> dict:
    """Registra una notificacion para Daniel."""
    state = _load_state()
    state["notifications_sent"] += 1
    state["last_notification"] = datetime.now().isoformat()
    state.setdefault("sent_topics", []).append({
        "message": message[:200],
        "priority": priority,
        "timestamp": datetime.now().isoformat(),
    })
    if len(state["sent_topics"]) > 50:
        state["sent_topics"] = state["sent_topics"][-50:]
    _save_state(state)
    _log("notify", "Notificacion: {} ({})".format(message[:80], priority))
    return {"status": "notificado", "message": message, "priority": priority}


def broadcast(message: str) -> dict:
    """Envia un mensaje a todos los canales disponibles."""
    _log("broadcast", "Broadcast: {}".format(message[:80]))
    return notify_daniel(message, "broadcast")


def get_comms_status() -> dict:
    state = _load_state()
    return {
        "notifications_sent": state.get("notifications_sent", 0),
        "last_notification": state.get("last_notification"),
        "recent": state.get("sent_topics", [])[-5:],
    }


def proactive_comms_tool(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = params.get("action", "status")

    if action == "status":
        return json.dumps(get_comms_status(), indent=2)
    elif action == "check":
        events = check_important_events()
        return json.dumps({"events": events, "count": len(events)}, indent=2)
    elif action == "notify":
        message = params.get("message", "")
        priority = params.get("priority", "medium")
        if not message:
            return json.dumps({"error": "Mensaje requerido"})
        return json.dumps(notify_daniel(message, priority), indent=2)
    elif action == "broadcast":
        message = params.get("message", "")
        if not message:
            return json.dumps({"error": "Mensaje requerido"})
        return json.dumps(broadcast(message), indent=2)

    return json.dumps({"error": "Accion desconocida: {}".format(action)})


if __name__ == "__main__":
    print("=== Test Proactive Comms ===")
    print(proactive_comms_tool({"action": "status"}))
    r = json.loads(proactive_comms_tool({"action": "check"}))
    print("Events:", r["count"])
