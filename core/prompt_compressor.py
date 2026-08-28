"""
prompt_compressor.py — Compresión automática de historial de conversación.

Mantiene ventanas de contexto largas sin gastar todos los tokens:
  - Resume conversaciones viejas en puntos clave
  - Conserva las últimas N interacciones sin comprimir
  - Detecta temas/decisiones importantes para preservar
"""
from __future__ import annotations

import re

try:
    from core.agent_architecture import _chat
except ImportError:
    _chat = None


_SUMMARIZE_SYS = (
    "Resumí esta conversación en 3-5 puntos clave. Enfocarte en:\n"
    "- Decisiones tomadas\n"
    "- Datos importantes mencionados\n"
    "- Tareas pendientes\n"
    "- Errores encontrados y soluciones\n"
    "Sé conciso: máximo 200 palabras."
)


def compress_history(messages: list[dict], keep_recent: int = 6, max_tokens: int = 2000) -> list[dict]:
    """Comprime el historial de conversación resumiendo las partes viejas.

    Args:
        messages: Lista de mensajes [{role, content}, ...]
        keep_recent: Cuántos mensajes recientes conservar sin comprimir.
        max_tokens: Límite aproximado de tokens para el historial comprimido.

    Returns:
        Lista de mensajes comprimidos.
    """
    if len(messages) <= keep_recent:
        return messages

    old_messages = messages[:-keep_recent]
    recent_messages = messages[-keep_recent:]

    # Comprimir mensajes viejos
    old_summary = _summarize_messages(old_messages)

    # Construir historial comprimido
    compressed = []
    if old_summary:
        compressed.append({
            "role": "system",
            "content": f"[Historial previo resumido]\n{old_summary}",
        })
    compressed.extend(recent_messages)

    return compressed


def _summarize_messages(messages: list[dict]) -> str:
    """Resume una lista de mensajes."""
    if not messages:
        return ""

    # Formatear mensajes para el LLM
    conversation = []
    for msg in messages:
        role = msg.get("role", "?")
        content = msg.get("content", "")
        if content and role in ("user", "assistant"):
            conversation.append(f"{role}: {content[:500]}")

    if not conversation:
        return ""

    full_text = "\n".join(conversation)

    if _chat is None:
        # Sin LLM: resumen heurístico
        return _heuristic_summary(messages)

    try:
        resp = _chat([
            {"role": "system", "content": _SUMMARIZE_SYS},
            {"role": "user", "content": full_text[:4000]},
        ], max_tokens=400)
        return resp.get("content", "").strip()
    except Exception:
        return _heuristic_summary(messages)


def _heuristic_summary(messages: list[dict]) -> str:
    """Resumen heurístico sin LLM: extrae puntos clave."""
    points = []
    for msg in messages:
        content = msg.get("content", "")
        if not content:
            continue
        # Detectar decisiones
        if re.search(r"(decidí|decidimos|vamos a|haremos|implementaré)", content, re.IGNORECASE):
            points.append(f"Decisión: {content[:150]}")
        # Detectar errores
        if re.search(r"(error|falló|no funciona|bug)", content, re.IGNORECASE):
            points.append(f"Error: {content[:150]}")
        # Detectar datos importantes
        if re.search(r"(importante|clave|recordá|acordate)", content, re.IGNORECASE):
            points.append(f"Dato clave: {content[:150]}")

    if not points:
        # Fallback: tomar primer y último mensaje
        first = messages[0].get("content", "")[:100] if messages else ""
        last = messages[-1].get("content", "")[:100] if messages else ""
        return f"Inicio: {first}\nFinal: {last}"

    return "\n".join(points[:5])
