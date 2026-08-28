"""
proactive_suggestions.py — Motor de sugerencias proactivas.

Después de completar una tarea, sugiere automáticamente qué hacer después
basándose en:
  - Patrones de usuario (qué suele pedir después de X)
  - Contexto de la tarea completada
  - Hora del día
  - Memoria de conversaciones previas
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from collections import defaultdict

_BASE = Path(__file__).resolve().parent.parent
_PATTERNS_FILE = _BASE / "data" / "suggestion_patterns.json"

# Patrones predefinidos: después de X, sugerir Y
PREDEFINED_PATTERNS = {
    "code": [
        {"suggestion": "Crear tests para el código modificado", "action": "skill: test-driven-development", "priority": 1},
        {"suggestion": "Revisar el diff con code_review", "action": "code_review", "priority": 1},
        {"suggestion": "Hacer commit de los cambios", "action": "git_control(action='status')", "priority": 2},
    ],
    "bug": [
        {"suggestion": "Documentar el bug y su solución", "action": "obsidian_note(action='write')", "priority": 1},
        {"suggestion": "Crear test de regresión", "action": "skill: test-driven-development", "priority": 1},
        {"suggestion": "Verificar que no hay más bugs similares", "action": "codebase", "priority": 2},
    ],
    "deploy": [
        {"suggestion": "Verificar logs después del deploy", "action": "shell", "priority": 1},
        {"suggestion": "Hacer backup de la config actual", "action": "backup_system", "priority": 1},
    ],
    "research": [
        {"suggestion": "Guardar hallazgos en Obsidian", "action": "obsidian_note(action='write')", "priority": 1},
        {"suggestion": "Indexar documentos encontrados en RAG", "action": "document_rag(action='index')", "priority": 2},
    ],
    "document": [
        {"suggestion": "Indexar el documento en RAG", "action": "document_rag(action='index')", "priority": 1},
        {"suggestion": "Crear backup del documento", "action": "backup_system", "priority": 2},
    ],
    "fix": [
        {"suggestion": "Verificar que el fix no rompió nada más", "action": "shell", "priority": 1},
        {"suggestion": "Aprender de este error para el futuro", "action": "learn_from_mistake", "priority": 1},
    ],
}

# Contexto por hora
TIME_SUGGESTIONS = {
    "morning": [
        {"suggestion": "Revisar el resumen del día anterior", "action": "daily_digest", "priority": 3},
        {"suggestion": "Ver tareas pendientes", "action": "goals", "priority": 2},
    ],
    "evening": [
        {"suggestion": "Consolidar aprendizajes del día", "action": "memory_consolidation(action='auto')", "priority": 2},
        {"suggestion": "Backup automático", "action": "backup_system", "priority": 3},
    ],
}


def _get_time_period() -> str:
    from datetime import datetime
    hour = datetime.now().hour
    if 6 <= hour < 12:
        return "morning"
    elif 12 <= hour < 18:
        return "afternoon"
    elif 18 <= hour < 22:
        return "evening"
    return "night"


def _load_user_patterns() -> dict:
    try:
        if _PATTERNS_FILE.exists():
            return json.loads(_PATTERNS_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_user_patterns(patterns: dict):
    try:
        _PATTERNS_FILE.parent.mkdir(parents=True, exist_ok=True)
        _PATTERNS_FILE.write_text(json.dumps(patterns, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def suggest_next_steps(
    completed_task: str,
    task_result: str = "",
    tool_used: str = "",
    context: str = "",
) -> list[dict]:
    """Sugiere próximos pasos después de completar una tarea.

    Args:
        completed_task: Descripción de la tarea completada
        task_result: Resultado de la tarea
        tool_used: Tool que se usó
        context: Contexto adicional

    Returns:
        Lista de [{suggestion, action, priority, source}]
    """
    suggestions = []
    task_lower = completed_task.lower()
    tool_lower = tool_used.lower()

    # 1. Sugerencias predefinidas por tipo de tarea
    for category, preds in PREDEFINED_PATTERNS.items():
        if category in task_lower or category in tool_lower:
            for pred in preds:
                suggestions.append({**pred, "source": "pattern"})

    # 2. Sugerencias por tool específica
    tool_suggestions = {
        "file_write": [{"suggestion": "Verificar el archivo creado", "action": "file_read", "priority": 1}],
        "shell": [{"suggestion": "Verificar que el comando ejecutó correctamente", "action": "shell", "priority": 1}],
        "codebase": [{"suggestion": "Leer los archivos encontrados", "action": "file_read", "priority": 2}],
    }
    for ts, sugs in tool_suggestions.items():
        if ts in tool_lower:
            for sug in sugs:
                suggestions.append({**sug, "source": "tool"})

    # 3. Sugerencias por hora del día
    period = _get_time_period()
    time_sugs = TIME_SUGGESTIONS.get(period, [])
    for sug in time_sugs:
        suggestions.append({**sug, "source": "time"})

    # 4. Sugerencias del usuario (aprendidas)
    user_patterns = _load_user_patterns()
    for pattern, sugs in user_patterns.items():
        if pattern in task_lower:
            for sug in sugs:
                suggestions.append({**sug, "source": "learned"})

    # Deduplicar y ordenar
    seen = set()
    unique = []
    for s in sorted(suggestions, key=lambda x: x.get("priority", 3)):
        key = s.get("suggestion", "")
        if key not in seen:
            seen.add(key)
            unique.append(s)

    return unique[:5]


def record_user_pattern(trigger: str, action: str):
    """Registra un patrón de usuario para sugerencias futuras."""
    patterns = _load_user_patterns()
    if trigger not in patterns:
        patterns[trigger] = []
    patterns[trigger].append({
        "suggestion": action,
        "action": action,
        "priority": 2,
        "source": "learned",
    })
    _save_user_patterns(patterns)


def format_suggestions(suggestions: list[dict]) -> str:
    """Formatea sugerencias para mostrar."""
    if not suggestions:
        return "No hay sugerencias en este momento."
    lines = ["Sugerencias para después:"]
    for i, s in enumerate(suggestions, 1):
        source = s.get("source", "")
        lines.append("  %d. %s (fuente: %s)" % (i, s.get("suggestion", ""), source))
    return "\n".join(lines)
