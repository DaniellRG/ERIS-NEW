"""
knowledge_distillation.py — Destilación de conocimiento de conversaciones exitosas.

Extrae patrones de conversaciones exitosas y los convierte en reglas que el
agente aplique siempre. Tipo "lecciones aprendidas" automáticas.

Flujo:
  1. Analizar conversación completada exitosamente
  2. Extraer patrones: qué funcionó, qué no, qué se repite
  3. Convertir en reglas concisas
  4. Guardar en memoria de largo plazo para reutilizar
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_PATTERNS_FILE = _BASE / "memory" / "distilled_patterns.json"

try:
    from core.agent_architecture import _chat
except ImportError:
    _chat = None


_EXTRACT_SYS = (
    "Analizá esta conversación exitosa y extraé patrones reutilizables.\n\n"
    "Para cada patrón, devolvé:\n"
    "- pattern: descripción concisa del patrón (1 línea)\n"
    "- rule: regla que el agente debe seguir siempre\n"
    "- category: categoría (code, debug, communication, workflow, other)\n"
    "- confidence: 0-1 (qué tan seguro estás del patrón)\n\n"
    "Respondé SOLO con un JSON válido: "
    '[{"pattern": "...", "rule": "...", "category": "...", "confidence": 0.8}]'
)


def extract_patterns(conversation: str, goal: str, result: str) -> list[dict]:
    """Extrae patrones de una conversación exitosa.

    Args:
        conversation: Texto de la conversación.
        goal: Objetivo que se cumplió.
        result: Resultado obtenido.

    Returns:
        Lista de patrones extraídos.
    }
    """
    if _chat is None:
        return _extract_patterns_heuristic(conversation, goal, result)

    try:
        resp = _chat([
            {"role": "system", "content": _EXTRACT_SYS},
            {"role": "user", "content": (
                f"Objetivo: {goal}\n"
                f"Resultado: {result[:500]}\n\n"
                f"Conversación:\n{conversation[:6000]}"
            )},
        ], max_tokens=1024)
        text = resp.get("content", "")
    except Exception:
        return _extract_patterns_heuristic(conversation, goal, result)

    m = re.search(r"\[[\s\S]*\]", text)
    if m:
        try:
            patterns = json.loads(m.group(0))
            if isinstance(patterns, list):
                return [p for p in patterns if isinstance(p, dict) and "pattern" in p]
        except Exception:
            pass
    return []


def _extract_patterns_heuristic(conversation: str, goal: str, result: str) -> list[dict]:
    """Extracción heurística sin LLM."""
    patterns = []

    # Patrón: si usó múltiples herramientas, documentar la secuencia
    tool_calls = re.findall(r"→ (\w+)\(", conversation)
    if len(tool_calls) >= 3:
        patterns.append({
            "pattern": f"Secuencia de tools efectiva: {' → '.join(tool_calls[:5])}",
            "rule": f"Para tareas similares, usar la secuencia: {', '.join(tool_calls[:3])}",
            "category": "workflow",
            "confidence": 0.6,
        })

    # Patrón: si hubo errores y se recuperó
    if "error" in conversation.lower() and "completado" in result.lower():
        patterns.append({
            "pattern": "Recuperación exitosa de error durante ejecución",
            "rule": "Cuando un tool falla, intentar alternativa antes de rendirse",
            "category": "debug",
            "confidence": 0.7,
        })

    # Patrón: si el goal menciona un tipo específico de tarea
    goal_lower = goal.lower()
    if any(w in goal_lower for w in ["bug", "error", "falla", "crash"]):
        patterns.append({
            "pattern": "Tarea de debugging exitosa",
            "rule": "Empezar por reproducir el error antes de intentar arreglar",
            "category": "debug",
            "confidence": 0.6,
        })

    return patterns


def save_patterns(patterns: list[dict], source: str = "conversation"):
    """Guarda patrones destilados en memoria de largo plazo."""
    existing = _load_patterns()

    # Evitar duplicados (matching por pattern text)
    existing_texts = {p.get("pattern", "").lower() for p in existing}
    new_patterns = []
    for p in patterns:
        if p.get("pattern", "").lower() not in existing_texts:
            p["source"] = source
            p["created"] = time.time()
            existing.append(p)
            new_patterns.append(p)

    # Guardar
    try:
        _PATTERNS_FILE.parent.mkdir(parents=True, exist_ok=True)
        _PATTERNS_FILE.write_text(
            json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception:
        pass

    return len(new_patterns)


def _load_patterns() -> list[dict]:
    try:
        if _PATTERNS_FILE.exists():
            return json.loads(_PATTERNS_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return []


def get_relevant_patterns(query: str, top_n: int = 3) -> list[dict]:
    """Busca patrones relevantes para una query dada."""
    patterns = _load_patterns()
    if not patterns:
        return []

    query_words = set(query.lower().split())
    scored = []
    for p in patterns:
        pattern_words = set(p.get("pattern", "").lower().split())
        rule_words = set(p.get("rule", "").lower().split())
        all_words = pattern_words | rule_words
        overlap = len(query_words & all_words)
        score = overlap * p.get("confidence", 0.5)
        if score > 0:
            scored.append({"score": score, **p})

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_n]


def format_patterns(patterns: list[dict]) -> str:
    """Formatea patrones para mostrar al agente."""
    if not patterns:
        return ""
    lines = ["Patrones relevantes de conversaciones previas:"]
    for p in patterns:
        lines.append(f"  - [{p.get('category', '?')}] {p.get('rule', '')}")
    return "\n".join(lines)
