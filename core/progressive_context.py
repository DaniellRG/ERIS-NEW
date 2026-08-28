"""
progressive_context.py — Carga gradual de contexto para ERIS.

En vez de cargar todo el contexto de una vez (que gasta tokens), carga
progresivamente: primero lo más relevante, y expande solo si hace falta.

Flujo:
  1. Evaluar la complejidad de la tarea
  2. Cargar contexto mínimo (nivel 1): solo lo esencial
  3. Si la respuesta es insuficiente, expandir a contexto medio (nivel 2)
  4. Si aún falta, cargar contexto completo (nivel 3)

Esto ahorra tokens en tareas simples y da contexto completo en complejas.
"""
from __future__ import annotations

import json
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent


# ── Niveles de contexto ─────────────────────────────────────────────────────

CONTEXT_LEVELS = {
    1: {
        "name": "mínimo",
        "description": "Solo lo esencial: pregunta + última interacción",
        "max_tokens": 500,
    },
    2: {
        "name": "medio",
        "description": "Contexto relevante: historial reciente + skills relevantes",
        "max_tokens": 1500,
    },
    3: {
        "name": "completo",
        "description": "Todo el contexto: historial largo + todos los datos disponibles",
        "max_tokens": 4000,
    },
}


def _estimate_task_complexity(query: str, history: list[dict] = None) -> int:
    """Estima la complejidad de una tarea (1=simple, 3=compleja)."""
    q = query.lower().strip()
    score = 1

    # Por longitud
    if len(q) > 100:
        score += 1
    if len(q) > 300:
        score += 1

    # Por palabras clave de complejidad
    complex_markers = [
        "compará", "comparar", "analizá", "analizar", "evaluá", "evaluar",
        "creá", "crear", "implementá", "implementar", "refactor", "migrá",
        "deploy", "deployear", "configurá", "configurar", "integrá", "integrar",
        "todo", "todos", "toda", "completo", "sistema", "arquitectura",
    ]
    for marker in complex_markers:
        if marker in q:
            score += 1
            break

    # Por historial: si hay muchas interacciones, la tarea probablemente es compleja
    if history and len(history) > 5:
        score += 1

    return min(score, 3)


def build_progressive_context(
    query: str,
    history: list[dict] = None,
    level: int = None,
    system_prompt: str = "",
    skills_context: str = "",
    memory_context: str = "",
) -> dict:
    """Construye contexto progresivo para una tarea.

    Args:
        query: Pregunta/tarea del usuario.
        history: Historial de conversación previo.
        level: Forzar nivel (1-3). Si es None, se estima automáticamente.
        system_prompt: System prompt base.
        skills_context: Contexto de skills cargadas.
        memory_context: Contexto de memoria relevante.

    Returns:
        dict con: level, messages, tokens_estimate, expanded
    """
    if level is None:
        level = _estimate_task_complexity(query, history)

    messages = []

    # System prompt siempre va
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    # Nivel 1: mínimo — solo los últimos mensajes del historial
    if history:
        recent = history[-2:] if level == 1 else history[-5:] if level == 2 else history
        for msg in recent:
            if isinstance(msg, dict):
                messages.append(msg)

    # Nivel 2+: skills relevantes
    if level >= 2 and skills_context:
        messages.append({"role": "system", "content": f"Skills relevantes:\n{skills_context}"})

    # Nivel 3: memoria completa
    if level >= 3 and memory_context:
        messages.append({"role": "system", "content": f"Contexto de memoria:\n{memory_context}"})

    # La pregunta actual siempre va al final
    messages.append({"role": "user", "content": query})

    ctx_info = CONTEXT_LEVELS[level]
    return {
        "level": level,
        "level_name": ctx_info["name"],
        "messages": messages,
        "max_tokens": ctx_info["max_tokens"],
        "tokens_estimate": _estimate_tokens(messages),
        "expanded": level > 1,
    }


def _estimate_tokens(messages: list[dict]) -> int:
    """Estimación rough de tokens (1 token ≈ 4 chars en español)."""
    total_chars = sum(len(str(m.get("content", ""))) for m in messages)
    return total_chars // 4


def maybe_expand_context(
    result: str,
    context: dict,
    query: str,
    history: list[dict] = None,
    **kwargs,
) -> dict | None:
    """Si la respuesta es insuficiente, expande al siguiente nivel de contexto.

    Returns:
        Nuevo contexto expandido o None si no necesita expansión.
    """
    current_level = context.get("level", 1)
    if current_level >= 3:
        return None

    # Detectar respuestas insuficientes
    insufficient_indicators = [
        "no tengo suficiente contexto",
        "necesito más información",
        "no puedo determinar",
        "falta contexto",
        "no hay información",
        "sin resultados",
    ]
    result_lower = result.lower()
    needs_expand = any(ind in result_lower for ind in insufficient_indicators)

    # También expandir si la respuesta es muy corta para una tarea compleja
    if len(result.strip()) < 50 and current_level < 3:
        needs_expand = True

    if not needs_expand:
        return None

    new_level = current_level + 1
    return build_progressive_context(
        query=query,
        history=history,
        level=new_level,
        system_prompt=kwargs.get("system_prompt", ""),
        skills_context=kwargs.get("skills_context", ""),
        memory_context=kwargs.get("memory_context", ""),
    )
