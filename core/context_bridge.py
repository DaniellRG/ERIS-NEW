"""
context_bridge.py — Conecta contexto entre sesiones diferentes.

No solo memoria persistente, sino intención pendiente:
  - ¿Qué estaba haciendo el usuario cuando se fue?
  - ¿Qué quedó a medias?
  - ¿Qué preguntas quedaron sin responder?
  - Transfiere contexto entre sesiones relacionadas
"""
from __future__ import annotations

import json
import time
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_BRIDGE_FILE = _BASE / "data" / "context_bridge.json"


def _load_bridge() -> dict:
    try:
        if _BRIDGE_FILE.exists():
            return json.loads(_BRIDGE_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {
        "active_contexts": [],
        "pending_intentions": [],
        "unfinished_tasks": [],
        "unanswered_questions": [],
        "session_links": [],
    }


def _save_bridge(data: dict):
    try:
        _BRIDGE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _BRIDGE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def save_session_context(
    session_id: str,
    user_intent: str = "",
    tasks_in_progress: list[str] = None,
    open_questions: list[str] = None,
    key_decisions: list[str] = None,
    related_sessions: list[str] = None,
):
    """Guarda el contexto al final de una sesión."""
    data = _load_bridge()

    context = {
        "session_id": session_id,
        "timestamp": time.time(),
        "user_intent": user_intent,
        "tasks_in_progress": tasks_in_progress or [],
        "open_questions": open_questions or [],
        "key_decisions": key_decisions or [],
        "related_sessions": related_sessions or [],
    }

    data["active_contexts"].append(context)

    # Actualizar tareas pendientes
    for task in (tasks_in_progress or []):
        entry = {"task": task, "session": session_id, "created_at": time.time()}
        if entry not in data["unfinished_tasks"]:
            data["unfinished_tasks"].append(entry)

    # Actualizar preguntas sin responder
    for q in (open_questions or []):
        entry = {"question": q, "session": session_id, "created_at": time.time()}
        if entry not in data["unanswered_questions"]:
            data["unanswered_questions"].append(entry)

    # Mantener últimos 50 contextos
    if len(data["active_contexts"]) > 50:
        data["active_contexts"] = data["active_contexts"][-50:]

    # Mantener tareas y preguntas en 100
    data["unfinished_tasks"] = data["unfinished_tasks"][-100:]
    data["unanswered_questions"] = data["unanswered_questions"][-100:]

    _save_bridge(data)


def get_resume_context() -> dict:
    """Obtiene contexto para continuar de donde se dejó."""
    data = _load_bridge()

    # Último contexto activo
    last_context = data["active_contexts"][-1] if data["active_contexts"] else None

    # Tareas pendientes
    pending_tasks = data.get("unfinished_tasks", [])

    # Preguntas sin responder
    open_questions = data.get("unanswered_questions", [])

    return {
        "last_session": last_context,
        "pending_tasks_count": len(pending_tasks),
        "pending_tasks": pending_tasks[-10:],
        "open_questions_count": len(open_questions),
        "open_questions": open_questions[-5:],
    }


def link_sessions(session_a: str, session_b: str, reason: str = ""):
    """Vincula dos sesiones relacionadas."""
    data = _load_bridge()
    link = {
        "session_a": session_a,
        "session_b": session_b,
        "reason": reason,
        "created_at": time.time(),
    }
    data["session_links"].append(link)
    data["session_links"] = data["session_links"][-50:]
    _save_bridge(data)


def get_related_sessions(session_id: str) -> list[dict]:
    """Encuentra sesiones relacionadas."""
    data = _load_bridge()
    related = []

    for link in data.get("session_links", []):
        if link["session_a"] == session_id:
            related.append({"session": link["session_b"], "reason": link["reason"]})
        elif link["session_b"] == session_id:
            related.append({"session": link["session_a"], "reason": link["reason"]})

    # También buscar por similitud de intento
    current_ctx = None
    for ctx in data.get("active_contexts", []):
        if ctx["session_id"] == session_id:
            current_ctx = ctx
            break

    if current_ctx and current_ctx.get("user_intent"):
        intent_words = set(current_ctx["user_intent"].lower().split())
        for ctx in data.get("active_contexts", []):
            if ctx["session_id"] != session_id and ctx.get("user_intent"):
                other_words = set(ctx["user_intent"].lower().split())
                overlap = len(intent_words & other_words)
                if overlap > 2:
                    related.append({
                        "session": ctx["session_id"],
                        "reason": "Intento similar (%d palabras en común)" % overlap,
                    })

    return related


def complete_task(task_text: str) -> bool:
    """Marca una tarea como completada."""
    data = _load_bridge()
    before = len(data["unfinished_tasks"])
    data["unfinished_tasks"] = [
        t for t in data["unfinished_tasks"]
        if t.get("task", "").lower() != task_text.lower()
    ]
    if len(data["unfinished_tasks"]) < before:
        _save_bridge(data)
        return True
    return False


def answer_question(question_text: str) -> bool:
    """Marca una pregunta como respondida."""
    data = _load_bridge()
    before = len(data["unanswered_questions"])
    data["unanswered_questions"] = [
        q for q in data["unanswered_questions"]
        if q.get("question", "").lower() != question_text.lower()
    ]
    if len(data["unanswered_questions"]) < before:
        _save_bridge(data)
        return True
    return False


def get_bridge_summary() -> dict:
    """Resumen del estado del puente de contexto."""
    data = _load_bridge()
    return {
        "active_contexts": len(data.get("active_contexts", [])),
        "pending_tasks": len(data.get("unfinished_tasks", [])),
        "open_questions": len(data.get("unanswered_questions", [])),
        "session_links": len(data.get("session_links", [])),
        "last_context_time": (
            data["active_contexts"][-1]["timestamp"]
            if data.get("active_contexts") else None
        ),
    }


def format_bridge() -> str:
    """Formatea puente de contexto para mostrar."""
    resume = get_resume_context()
    summary = get_bridge_summary()

    lines = ["Puente de contexto:"]
    if summary["last_context_time"]:
        elapsed = time.time() - summary["last_context_time"]
        if elapsed < 3600:
            time_str = "%.0f minutos" % (elapsed / 60)
        elif elapsed < 86400:
            time_str = "%.1f horas" % (elapsed / 3600)
        else:
            time_str = "%.0f días" % (elapsed / 86400)
        lines.append("  Última sesión: hace %s" % time_str)

    if resume.get("pending_tasks"):
        lines.append("\nTareas pendientes:")
        for t in resume["pending_tasks"][-5:]:
            lines.append("  ○ %s" % t.get("task", "")[:60])

    if resume.get("open_questions"):
        lines.append("\nPreguntas abiertas:")
        for q in resume["open_questions"][-5:]:
            lines.append("  ? %s" % q.get("question", "")[:60])

    if not resume.get("pending_tasks") and not resume.get("open_questions"):
        lines.append("  No hay nada pendiente")

    return "\n".join(lines)
