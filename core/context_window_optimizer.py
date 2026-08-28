"""
context_window_optimizer.py — Asignación óptima de tokens por tool/LLM.

Calcula cuántos tokens dar a cada herramienta y contexto, maximizando
la información útil sin exceder límites.

Optimización:
  - Priorizar contexto más relevante
  - Reservar tokens para respuesta
  - Ajustar según complejidad de la tarea
"""
from __future__ import annotations

# Límites de tokens por proveedor (approx)
PROVIDER_LIMITS = {
    "openrouter": 128000,
    "ollama": 8192,
    "gemini": 1000000,
    "groq": 8192,
}

# Reserva para respuesta
RESPONSE_RESERVE = 2048

# Reserva para system prompt
SYSTEM_RESERVE = 1500


def calculate_budget(
    provider: str = "openrouter",
    task_complexity: int = 1,
    num_tools: int = 0,
    history_messages: int = 0,
) -> dict:
    """Calcula el presupuesto óptimo de tokens.

    Args:
        provider: Proveedor LLM
        task_complexity: 1=simple, 2=media, 3=compleja
        num_tools: Número de tools disponibles
        history_messages: Número de mensajes en historial

    Returns:
        dict con: total, system, history, tools, response, available_for_context
    """
    total = PROVIDER_LIMITS.get(provider, 8192)

    # Reservas fijas
    system = min(SYSTEM_RESERVE, total // 10)
    response = min(RESPONSE_RESERVE, total // 8)

    # Historial: más complejo = más historial
    history_ratio = {1: 0.15, 2: 0.25, 3: 0.35}.get(task_complexity, 0.2)
    history = int(total * history_ratio)
    # Ajustar por número de mensajes
    if history_messages > 10:
        history = int(history * 0.7)  # Comprimir si hay muchos mensajes

    # Tools: más tools = más tokens para declarations
    tools = min(num_tools * 150, total // 5)  # ~150 tokens por tool declaration

    available = total - system - history - tools - response
    available = max(available, 500)  # Mínimo 500 tokens para contexto

    return {
        "total": total,
        "system": system,
        "history": history,
        "tools": tools,
        "response": response,
        "available_for_context": available,
        "utilization": round((system + history + tools + response) / total * 100, 1),
    }


def allocate_tokens(
    sources: list[dict],
    budget: int,
) -> list[dict]:
    """Asigna tokens óptimamente entre múltiples fuentes de contexto.

    Args:
        sources: [{name, priority (1=alta), base_tokens, content}]
        budget: Total de tokens disponibles

    Returns:
        Lista de fuentes con tokens asignados
    """
    if not sources:
        return []

    # Calcular tokens base totales
    total_base = sum(s.get("base_tokens", 100) for s in sources)

    if total_base <= budget:
        # Cabe todo — asignar base
        for s in sources:
            s["allocated_tokens"] = s.get("base_tokens", 100)
        return sources

    # No cabe todo — priorizar por prioridad
    sorted_sources = sorted(sources, key=lambda x: x.get("priority", 3))

    allocated = 0
    for s in sorted_sources:
        base = s.get("base_tokens", 100)
        priority = s.get("priority", 3)

        # Asignar proporcionalmente, priorizando alta prioridad
        weight = {1: 2.0, 2: 1.5, 3: 1.0, 4: 0.7}.get(priority, 1.0)
        share = (base / total_base) * budget * weight

        # Limitar
        tokens = int(min(share, base * 2, budget - allocated))
        tokens = max(tokens, 50)  # Mínimo 50 tokens

        s["allocated_tokens"] = tokens
        allocated += tokens

        if allocated >= budget:
            break

    # Los que no recibieron tokens
    for s in sources:
        if "allocated_tokens" not in s:
            s["allocated_tokens"] = 0

    return sources


def optimize_messages(messages: list[dict], budget: int) -> list[dict]:
    """Optimiza una lista de mensajes para caber en un presupuesto de tokens.

    Estrategia:
      - System prompt siempre completo
      - Últimos N mensajes completos
      - Mensajes viejos: resumir o truncar
    """
    if not messages:
        return []

    # Estimar tokens totales actuales
    total_chars = sum(len(str(m.get("content", ""))) for m in messages)
    estimated_tokens = total_chars // 4

    if estimated_tokens <= budget:
        return messages

    # Necesitamos comprimir
    optimized = []
    remaining = budget

    # System prompt primero (si existe)
    for msg in messages:
        if msg.get("role") == "system":
            content = msg.get("content", "")
            tokens = len(content) // 4
            if tokens < remaining:
                optimized.append(msg)
                remaining -= tokens
            break

    # Últimos mensajes completos
    recent = messages[-4:] if messages[-1].get("role") != "system" else messages[-5:-1]
    for msg in recent:
        content = msg.get("content", "")
        tokens = len(content) // 4
        if tokens < remaining:
            optimized.append(msg)
            remaining -= tokens

    # Mensajes intermedios: truncar
    middle = [m for m in messages if m not in optimized and m.get("role") != "system"]
    for msg in middle:
        content = msg.get("content", "")
        tokens = len(content) // 4
        if tokens <= remaining:
            optimized.append(msg)
            remaining -= tokens
        elif remaining > 100:
            # Truncar
            max_chars = remaining * 4
            truncated = content[:max_chars] + "... [truncado]"
            optimized.append({**msg, "content": truncated})
            remaining = 0
            break

    return optimized
