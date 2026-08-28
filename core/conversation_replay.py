"""
conversation_replay.py — Repetición de conversaciones pasadas.

Permite al agente "revivir" una conversación anterior para:
  - Debugging: ver qué hizo y por qué
  - Aprendizaje: recordar cómo resolvió algo
  - Repetir: ejecutar los mismos pasos con datos nuevos
"""
from __future__ import annotations

import json
import time
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_SESSIONS_DIR = _BASE / "data" / "sessions"


def save_session(session_id: str, messages: list[dict], metadata: dict = None):
    """Guarda una sesión de conversación completa."""
    _SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    session = {
        "id": session_id,
        "timestamp": time.time(),
        "messages": messages,
        "metadata": metadata or {},
    }
    path = _SESSIONS_DIR / "%s.json" % session_id
    path.write_text(json.dumps(session, ensure_ascii=False, indent=2), encoding="utf-8")


def list_sessions(limit: int = 10) -> list[dict]:
    """Lista sesiones guardadas."""
    if not _SESSIONS_DIR.exists():
        return []
    sessions = []
    for f in sorted(_SESSIONS_DIR.glob("*.json"), reverse=True)[:limit]:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            sessions.append({
                "id": data.get("id", f.stem),
                "timestamp": data.get("timestamp", 0),
                "messages": len(data.get("messages", [])),
                "metadata": data.get("metadata", {}),
            })
        except Exception:
            continue
    return sessions


def load_session(session_id: str) -> dict | None:
    """Carga una sesión completa."""
    path = _SESSIONS_DIR / "%s.json" % session_id
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def replay_session(session_id: str, step_by_step: bool = False) -> str:
    """Reproduce una sesión paso a paso.

    Args:
        session_id: ID de la sesión
        step_by_step: Si es True, devuelve cada paso por separado

    Returns:
        Reproducción formateada de la conversación
    """
    session = load_session(session_id)
    if not session:
        return "Sesión no encontrada: %s" % session_id

    messages = session.get("messages", [])
    lines = ["Reproducción de sesión: %s" % session_id]
    lines.append("Fecha: %s" % time.strftime("%Y-%m-%d %H:%M", time.localtime(session.get("timestamp", 0))))
    lines.append("Mensajes: %d" % len(messages))
    lines.append("")

    for i, msg in enumerate(messages, 1):
        role = msg.get("role", "?")
        content = msg.get("content", "")
        tool = msg.get("tool_calls", None)
        tool_result = msg.get("tool_result", None)

        icon = {"user": "👤", "assistant": "🤖", "system": "⚙️", "tool": "🔧"}.get(role, "?")
        lines.append("%s Paso %d [%s]: %s" % (icon, i, role, content[:200]))

        if tool:
            for tc in (tool if isinstance(tool, list) else [tool]):
                if isinstance(tc, dict):
                    lines.append("   → Tool: %s(%s)" % (tc.get("name", "?"), str(tc.get("arguments", ""))[:100]))

        if tool_result:
            lines.append("   ← Result: %s" % str(tool_result)[:150])

    return "\n".join(lines)


def extract_tool_sequence(session_id: str) -> list[dict]:
    """Extrae la secuencia de tools de una sesión para análisis."""
    session = load_session(session_id)
    if not session:
        return []

    tools = []
    for msg in session.get("messages", []):
        if msg.get("role") == "assistant" and msg.get("tool_calls"):
            for tc in msg["tool_calls"]:
                if isinstance(tc, dict):
                    tools.append({
                        "name": tc.get("name", ""),
                        "arguments": tc.get("arguments", {}),
                    })
    return tools
