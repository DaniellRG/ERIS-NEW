"""
user_feedback_learner.py — Aprende de feedback del usuario (👍/👎).

Registra feedback positivo/negativo sobre respuestas, y usa esa
información para mejorar respuestas futuras. Detecta patrones:
  - Qué tipo de respuestas le gustan al usuario
  - Qué estilo prefiere (breve vs detallado, código vs explicación)
  - Qué topics son los más relevantes para él
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from collections import defaultdict

_BASE = Path(__file__).resolve().parent.parent
_FEEDBACK_FILE = _BASE / "data" / "user_feedback.json"

# Peso del feedback positivo vs negativo
POSITIVE_WEIGHT = 1.0
NEGATIVE_WEIGHT = 1.5  # Los negativos pesan más para evitar repetir errores


def _load_feedback() -> dict:
    try:
        if _FEEDBACK_FILE.exists():
            return json.loads(_FEEDBACK_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {
        "entries": [],
        "patterns": {},
        "style_preferences": {
            "brief": 0, "detailed": 0, "code_focused": 0,
            "explanation_focused": 0, "humorous": 0, "formal": 0,
        },
        "topic_scores": {},
        "total_positive": 0,
        "total_negative": 0,
    }


def _save_feedback(data: dict):
    try:
        _FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
        _FEEDBACK_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def record_feedback(
    response_summary: str,
    positive: bool,
    topic: str = "",
    style: str = "",
    context: str = "",
    response_id: str = "",
) -> dict:
    """Registra feedback del usuario.

    Args:
        response_summary: Resumen de la respuesta (primeros 200 chars)
        positive: True si 👍, False si 👎
        topic: Tema de la respuesta (coding, debug, research, etc.)
        style: Estilo detectado (brief, detailed, code_focused, etc.)
        context: Contexto adicional
        response_id: ID de la respuesta para tracking

    Returns:
        dict con: entry_id, total_positive, total_negative, patterns_updated
    """
    data = _load_feedback()

    entry = {
        "id": "fb_%d" % int(time.time() * 1000),
        "timestamp": time.time(),
        "positive": positive,
        "response_summary": response_summary[:200],
        "topic": topic or "general",
        "style": style or "unclassified",
        "context": context[:200],
        "response_id": response_id,
    }
    data["entries"].append(entry)

    # Actualizar contadores
    if positive:
        data["total_positive"] = data.get("total_positive", 0) + 1
    else:
        data["total_negative"] = data.get("total_negative", 0) + 1

    # Actualizar preferencias de estilo
    style_prefs = data.get("style_preferences", {})
    if style:
        weight = POSITIVE_WEIGHT if positive else -NEGATIVE_WEIGHT
        style_prefs[style] = style_prefs.get(style, 0) + weight
        data["style_preferences"] = style_prefs

    # Actualizar scores de topic
    topic_scores = data.get("topic_scores", {})
    t = topic or "general"
    if t not in topic_scores:
        topic_scores[t] = {"positive": 0, "negative": 0, "score": 0}
    if positive:
        topic_scores[t]["positive"] += 1
    else:
        topic_scores[t]["negative"] += 1
    total_t = topic_scores[t]["positive"] + topic_scores[t]["negative"]
    topic_scores[t]["score"] = topic_scores[t]["positive"] / total_t if total_t > 0 else 0.5
    data["topic_scores"] = topic_scores

    # Detectar patrón de estilo preferido
    _update_patterns(data)

    # Mantener solo últimos 500 entries
    if len(data["entries"]) > 500:
        data["entries"] = data["entries"][-500:]

    _save_feedback(data)

    return {
        "entry_id": entry["id"],
        "total_positive": data["total_positive"],
        "total_negative": data["total_negative"],
        "patterns_updated": True,
    }


def _update_patterns(data: dict):
    """Actualiza patrones de preferencia del usuario."""
    entries = data.get("entries", [])
    recent = entries[-50:]  # Últimas 50 interacciones

    patterns = {}
    for e in recent:
        style = e.get("style", "unknown")
        pos = e.get("positive", False)
        if style not in patterns:
            patterns[style] = {"likes": 0, "dislikes": 0}
        if pos:
            patterns[style]["likes"] += 1
        else:
            patterns[style]["dislikes"] += 1

    data["patterns"] = patterns


def get_preferred_style() -> str:
    """Devuelve el estilo preferido del usuario."""
    data = _load_feedback()
    prefs = data.get("style_preferences", {})
    if not prefs:
        return "balanced"
    return max(prefs, key=prefs.get)


def get_preferred_topics() -> list[dict]:
    """Devuelve los topics rankeados por satisfacción."""
    data = _load_feedback()
    topics = data.get("topic_scores", {})
    sorted_topics = sorted(topics.items(), key=lambda x: x[1]["score"], reverse=True)
    return [
        {"topic": t, "score": info["score"],
         "positive": info["positive"], "negative": info["negative"]}
        for t, info in sorted_topics
    ]


def get_feedback_stats() -> dict:
    """Estadísticas de feedback."""
    data = _load_feedback()
    total = data.get("total_positive", 0) + data.get("total_negative", 0)
    return {
        "total_feedback": total,
        "positive": data.get("total_positive", 0),
        "negative": data.get("total_negative", 0),
        "satisfaction_rate": round(data.get("total_positive", 0) / total * 100, 1) if total > 0 else 0,
        "preferred_style": get_preferred_style(),
        "top_topics": get_preferred_topics()[:3],
    }


def should_adjust_style(current_style: str) -> dict | None:
    """Sugiere ajustar el estilo basándose en feedback."""
    preferred = get_preferred_style()
    if current_style != preferred:
        return {
            "current": current_style,
            "suggested": preferred,
            "reason": "El usuario prefiere '%s' sobre '%s' según feedback previo" % (preferred, current_style),
        }
    return None


def format_feedback_report() -> str:
    """Reporte legible de feedback."""
    stats = get_feedback_stats()
    lines = [
        "Reporte de feedback del usuario:",
        "  Total: %d (%d positivos, %d negativos)" % (
            stats["total_feedback"], stats["positive"], stats["negative"]),
        "  Satisfacción: %s%%" % stats["satisfaction_rate"],
        "  Estilo preferido: %s" % stats["preferred_style"],
    ]
    if stats["top_topics"]:
        lines.append("  Topics mejor rankeados:")
        for t in stats["top_topics"]:
            lines.append("    - %s: %.0f%% positivo (%d/%d)" % (
                t["topic"], t["score"] * 100, t["positive"],
                t["positive"] + t["negative"]))
    return "\n".join(lines)
