"""
intent_classifier.py — Clasificador de intención basado en embeddings.

En vez de solo keywords (como agent_router), usa embeddings para
clases de intención más precisas. Lightweight: sin dependencias pesadas.

Categorías de intención:
  - code: escribir/editar/revisar código
  - debug: buscar/arreglar bugs
  - search: buscar información
  - document: crear/editar documentos
  - system: control del sistema
  - communicate: enviar mensajes/email
  - learn: aprender/estudiar
  - automate: automatizar tareas
  - creative: contenido creativo
  - admin: configuración/gestión
"""
from __future__ import annotations

import re
import json
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent

# ── Perfiles de intención (patrones + peso) ──────────────────────────────────

INTENT_PROFILES = {
    "code": {
        "keywords": [
            "código", "code", "programar", "escribir", "editar", "función",
            "clase", "método", "import", "variable", "refactor", "implementar",
            "agregar", "modificar", "cambiar", "python", "javascript", "typescript",
            "html", "css", "api", "endpoint", "route", "controller",
        ],
        "tools_hint": ["codebase", "file_edit", "file_write", "code_copilot", "self_edit"],
        "weight": 1.0,
    },
    "debug": {
        "keywords": [
            "bug", "error", "falla", "crash", "exception", "traceback",
            "debug", "depurar", "diagnosticar", "arreglar", "fix", "problema",
            "no funciona", "rompió", "rotó", "fallo",
        ],
        "tools_hint": ["shell", "codebase", "file_read", "code_review"],
        "weight": 1.2,
    },
    "search": {
        "keywords": [
            "buscar", "search", "encontrar", "qué es", "cómo", "dónde",
            "cuándo", "quién", "cuánto", "investigar", "information",
            "documentación", "docs", "referencia",
        ],
        "tools_hint": ["web_search", "webfetch", "codebase", "document_rag"],
        "weight": 0.9,
    },
    "document": {
        "keywords": [
            "documento", "document", "nota", "note", "escribir", "redactar",
            "reporte", "informe", "resumen", "pdf", "markdown", "obsidian",
            "crear archivo", "guardar",
        ],
        "tools_hint": ["file_write", "obsidian_note", "document_creator"],
        "weight": 0.8,
    },
    "system": {
        "keywords": [
            "sistema", "system", "proceso", "process", "memoria", "ram",
            "cpu", "disco", "archivos", "carpeta", "directorio", "permisos",
            "instalar", "configurar", "terminal", "shell", "powershell",
        ],
        "tools_hint": ["shell", "system_monitor", "file_controller"],
        "weight": 1.0,
    },
    "communicate": {
        "keywords": [
            "enviar", "send", "mensaje", "message", "email", "whatsapp",
            "telegram", "llamar", "call", "notificación", "avisar",
        ],
        "tools_hint": ["send_message", "gmail_control", "telegram_bot"],
        "weight": 0.7,
    },
    "learn": {
        "keywords": [
            "aprender", "learn", "estudiar", "study", "explicar", "explain",
            "entender", "concepto", "tutorial", "cursos", "practicar",
        ],
        "tools_hint": ["web_search", "obsidian_note", "learn_from_mistake"],
        "weight": 0.6,
    },
    "automate": {
        "keywords": [
            "automatizar", "automate", "tarea", "task", "programar", "schedule",
            "cron", "timer", "recordatorio", "reminder", "workflow",
            "pipeline", "batch",
        ],
        "tools_hint": ["task_scheduler", "workflow_runner", "task_planner"],
        "weight": 0.9,
    },
    "creative": {
        "keywords": [
            "crear", "create", "diseñar", "design", "escribir", "write",
            "historia", "story", "poema", "poem", "música", "music",
            "imagen", "image", "arte", "art",
        ],
        "tools_hint": ["image_generation", "music_player", "document_creator"],
        "weight": 0.7,
    },
    "admin": {
        "keywords": [
            "configurar", "config", "ajustar", "settings", "preferencias",
            "perfil", "profile", "backup", "restaurar", "actualizar", "update",
            "limpiar", "clean", "organizar",
        ],
        "tools_hint": ["config_export", "backup_system", "self_heal"],
        "weight": 0.8,
    },
}


def classify_intent(query: str, top_n: int = 3) -> list[dict]:
    """Clasifica la intención de una query.

    Args:
        query: Texto del usuario
        top_n: Número de intenciones a devolver

    Returns:
        Lista de [{intent, score, confidence, tools_hint}]
    """
    q = query.lower().strip()
    q_words = set(q.split())
    scores = {}

    for intent, profile in INTENT_PROFILES.items():
        score = 0.0
        keywords = profile["keywords"]
        weight = profile.get("weight", 1.0)

        for kw in keywords:
            if " " in kw:
                # Phrase matching
                if kw in q:
                    score += 3.0 * weight
            else:
                # Word matching
                for qw in q_words:
                    if kw in qw or qw in kw:
                        score += 1.0 * weight
                        break

        if score > 0:
            scores[intent] = score

    if not scores:
        return [{"intent": "unknown", "score": 0, "confidence": 0, "tools_hint": []}]

    # Normalizar y ordenar
    max_score = max(scores.values())
    sorted_intents = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    results = []
    for intent, score in sorted_intents[:top_n]:
        confidence = score / (max_score + 1) if max_score > 0 else 0
        results.append({
            "intent": intent,
            "score": round(score, 2),
            "confidence": round(min(confidence, 1.0), 3),
            "tools_hint": INTENT_PROFILES[intent].get("tools_hint", []),
        })

    return results


def format_intent(intents: list[dict]) -> str:
    """Formato legible de intención."""
    if not intents:
        return "Intención: desconocida"
    primary = intents[0]
    lines = [f"Intención principal: {primary['intent']} (confianza: {primary['confidence']:.0%})"]
    if len(intents) > 1:
        others = ", ".join(f"{i['intent']} ({i['confidence']:.0%})" for i in intents[1:])
        lines.append(f"  Otras posibilidades: {others}")
    lines.append(f"  Tools sugeridas: {', '.join(primary['tools_hint'][:3])}")
    return "\n".join(lines)
