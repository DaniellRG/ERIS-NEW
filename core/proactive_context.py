"""
proactive_context.py — Carga proactiva de contexto.

En vez de esperar a que el usuario pida algo y luego buscar contexto,
predice qué información se necesitará y la pre-carga.

Señales de predicción:
  - Patrones de conversación previa
  - Hora del día (mañana = tareas, noche = entretenimiento)
  - Palabras clave que sugieren qué viene
  - Archivos frecuentemente accedidos juntos
  - Skills que se suelen usar en conjunto
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from collections import defaultdict

_BASE = Path(__file__).resolve().parent.parent
_PATTERNS_FILE = _BASE / "data" / "proactive_patterns.json"

# Patrones de co-ocurrencia: si el usuario hace X, probablemente hará Y
CO_OCCURRENCE = {
    "code": ["codebase", "file_read", "file_edit", "shell"],
    "bug": ["codebase", "shell", "file_read", "code_review"],
    "deploy": ["shell", "github_pr", "github_push"],
    "test": ["shell", "codebase", "file_read"],
    "document": ["file_write", "obsidian_note", "document_creator"],
    "search": ["web_search", "webfetch", "codebase"],
    "memory": ["obsidian_note", "episodic_add", "learn_from_mistake"],
    "audio": ["tts_engine", "voice_clone", "music_player"],
    "image": ["image_generation", "image_analyzer", "screen_vision"],
    "email": ["gmail_control", "email_manager", "send_message"],
    "calendar": ["google_calendar", "calendar_manager", "reminder"],
}

# Contexto por hora del día
TIME_CONTEXT = {
    "morning": ["daily_digest", "morning_brief", "goals", "task_scheduler"],
    "afternoon": ["codebase", "shell", "github_pr"],
    "evening": ["obsidian_note", "music_player", "curiosity_engine"],
    "night": ["self_improvement", "autonomous_learner", "idle_learning"],
}


def _get_time_period() -> str:
    """Determina el período del día."""
    from datetime import datetime
    hour = datetime.now().hour
    if 6 <= hour < 12:
        return "morning"
    elif 12 <= hour < 18:
        return "afternoon"
    elif 18 <= hour < 22:
        return "evening"
    return "night"


def predict_next_tools(current_tools: list[str], query: str = "") -> list[str]:
    """Predice qué tools se necesitarán pronto basándose en patrones.

    Args:
        current_tools: Tools que se están usando ahora
        query: Query actual del usuario

    Returns:
        Lista de tools predichas, ordenadas por probabilidad
    """
    predictions = defaultdict(float)

    # 1. Co-ocurrencia con tools actuales
    for tool in current_tools:
        for key, related in CO_OCCURRENCE.items():
            if key in tool.lower():
                for r in related:
                    if r not in current_tools:
                        predictions[r] += 1.0

    # 2. Basado en query
    query_lower = query.lower()
    for key, related in CO_OCCURRENCE.items():
        if key in query_lower:
            for r in related:
                if r not in current_tools:
                    predictions[r] += 1.5

    # 3. Basado en hora del día
    period = _get_time_period()
    time_tools = TIME_CONTEXT.get(period, [])
    for t in time_tools:
        if t not in current_tools:
            predictions[t] += 0.5

    # Ordenar por score
    sorted_pred = sorted(predictions.items(), key=lambda x: x[1], reverse=True)
    return [tool for tool, score in sorted_pred if score > 0.5][:5]


def preload_context(query: str, current_tools: list[str] = None) -> dict:
    """Pre-carga contexto relevante antes de que se pida.

    Returns:
        dict con: predicted_tools, skills_to_load, memory_hints, files_to_watch
    """
    current_tools = current_tools or []
    predicted = predict_next_tools(current_tools, query)

    # Skills que podrían ser relevantes
    skills_to_load = []
    query_lower = query.lower()
    skill_keywords = {
        "test": "test-driven-development",
        "bug": "depuracion-playbook",
        "review": "review",
        "plan": "plan-eng-review",
        "security": "cso",
        "qa": "qa",
        "code": "workflow-codigo",
    }
    for kw, skill in skill_keywords.items():
        if kw in query_lower:
            skills_to_load.append(skill)

    # Archivos que podrían ser relevantes (por patrones conocidos)
    files_to_watch = []
    if any(t in predicted for t in ["codebase", "file_read"]):
        files_to_watch.append("core/agent_architecture.py")

    return {
        "predicted_tools": predicted,
        "skills_to_load": skills_to_load,
        "memory_hints": [],
        "files_to_watch": files_to_watch,
    }


def record_tool_sequence(tools: list[str]):
    """Registra una secuencia de tools para mejorar predicciones futuras."""
    patterns = _load_patterns()
    if len(tools) >= 2:
        key = "|".join(tools[:3])
        patterns[key] = patterns.get(key, 0) + 1
        # Mantener solo top 500
        if len(patterns) > 500:
            sorted_p = sorted(patterns.items(), key=lambda x: x[1], reverse=True)
            patterns = dict(sorted_p[:500])
        _save_patterns(patterns)


def _load_patterns() -> dict:
    try:
        if _PATTERNS_FILE.exists():
            return json.loads(_PATTERNS_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_patterns(data: dict):
    try:
        _PATTERNS_FILE.parent.mkdir(parents=True, exist_ok=True)
        _PATTERNS_FILE.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass
