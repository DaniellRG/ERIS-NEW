"""
adaptive_temperature.py — Temperatura dinámica del LLM por tipo de tarea.

En vez de usar 0.3 fijo, ajusta la temperatura según:
  - Código factual: 0.1 (exactitud)
  - Resolución de bugs: 0.0 (determinista)
  - Brainstorming: 0.7 (creatividad)
  - Conversación casual: 0.5 (naturalidad)
  - Datos estructurados: 0.0 (precisión)

Mejora la calidad de respuestas al adaptar la creatividad al contexto.
"""
from __future__ import annotations

import re

# Mapeo de tipo de tarea → temperatura
TEMPERATURE_MAP = {
    # Código y datos (baja temperatura = más preciso)
    "code": 0.1,
    "debug": 0.0,
    "fix": 0.0,
    "refactor": 0.1,
    "test": 0.0,
    "data": 0.0,
    "json": 0.0,
    "config": 0.0,
    "factual": 0.1,

    # Creatividad (alta temperatura = más variado)
    "brainstorm": 0.7,
    "creative": 0.7,
    "story": 0.8,
    "poem": 0.9,
    "idea": 0.7,
    "design": 0.6,

    # Conversación (temperatura media)
    "chat": 0.5,
    "conversation": 0.5,
    "explain": 0.4,
    "summarize": 0.3,

    # Búsqueda y análisis (temperatura baja-media)
    "search": 0.2,
    "analyze": 0.2,
    "compare": 0.3,
    "evaluate": 0.2,

    # Planificación (temperatura media-baja)
    "plan": 0.3,
    "organize": 0.3,
    "schedule": 0.2,
}

# Palabras clave que indican tipo de tarea
KEYWORD_MAP = {
    0.0: ["error", "bug", "crash", "falla", "fix", "arreglar", "test", "verificar"],
    0.1: ["código", "code", "python", "javascript", "función", "clase", "import", "json", "config"],
    0.2: ["buscar", "search", "analizar", "comparar", "evaluar", "verificar", "datos"],
    0.3: ["resumir", "explicar", "plan", "organizar", "estructurar"],
    0.5: ["conversar", "charlar", "hablar", "contar", "preguntar"],
    0.7: ["crear", "diseñar", "idear", "brainstorm", "inventar", "imaginar"],
}


def classify_temperature(query: str) -> float:
    """Determina la temperatura óptima para una query.

    Args:
        query: Texto de la query del usuario

    Returns:
        Temperatura entre 0.0 y 0.9
    """
    q = query.lower().strip()

    # Buscar por tipo explícito
    for temp, keywords in KEYWORD_MAP.items():
        for kw in keywords:
            if kw in q:
                return temp

    # Por longitud: queries cortas = más determinista, largas = más creativas
    if len(q) < 20:
        return 0.2
    if len(q) > 200:
        return 0.5

    # Default
    return 0.3


def get_temperature(query: str, override: float = None) -> dict:
    """Obtiene la temperatura óptima con metadata.

    Args:
        query: Query del usuario
        override: Override manual de temperatura

    Returns:
        dict con: temperature, task_type, reasoning
    """
    if override is not None:
        return {
            "temperature": max(0.0, min(0.9, override)),
            "task_type": "manual_override",
            "reasoning": "Override manual",
        }

    temp = classify_temperature(query)
    q = query.lower()

    # Detectar tipo para explicación
    task_type = "general"
    if any(kw in q for kw in ["error", "bug", "fix"]):
        task_type = "debugging"
    elif any(kw in q for kw in ["code", "código", "python"]):
        task_type = "coding"
    elif any(kw in q for kw in ["buscar", "search"]):
        task_type = "search"
    elif any(kw in q for kw in ["crear", "diseñar", "idear"]):
        task_type = "creative"
    elif any(kw in q for kw in ["resumir", "explicar"]):
        task_type = "explanation"

    return {
        "temperature": temp,
        "task_type": task_type,
        "reasoning": "Auto-detectado: %s → temp=%.1f" % (task_type, temp),
    }
