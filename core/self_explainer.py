"""
self_explainer.py — Explica decisiones y razonamiento del agente.

Cuando ERIS toma una decisión compleja, puede generar una explicación
clara de POR QUÉ eligió esa acción. Mejora la confianza del usuario
y facilita debugging de comportamiento inesperado.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent

try:
    from core.agent_architecture import _chat
except ImportError:
    _chat = None


_EXPLAIN_SYS = (
    "Sos un explicador de decisiones de IA. Dada una decisión tomada por "
    "un asistente, generá una explicación clara y concisa en español.\n\n"
    "La explicación debe incluir:\n"
    "1. QUÉ se decidió (1 frase)\n"
    "2. POR QUÉ esa opción y no otra (razones principales)\n"
    "3. QUÉ alternativas se descartaron y por qué\n"
    "4. RIESGOS o limitaciones de la decisión\n\n"
    "Sé directo, sin rodeos. Máximo 4 oraciones."
)


def explain_decision(
    decision: str,
    alternatives: list[str] = None,
    context: str = "",
    reasoning_trace: str = "",
) -> dict:
    """Genera una explicación de una decisión tomada.

    Args:
        decision: La decisión que se tomó
        alternatives: Alternativas consideradas
        context: Contexto de la decisión
        reasoning_trace: Trace del razonamiento (si existe)

    Returns:
        dict con: explanation, confidence, key_factors, risks
    """
    alt_text = ""
    if alternatives:
        alt_text = "Alternativas consideradas: " + "; ".join(alternatives[:5])

    user_msg = (
        f"Decisión tomada: {decision}\n\n"
        f"{alt_text}\n\n"
        f"Contexto: {context}\n\n"
        f"Trace de razonamiento: {reasoning_trace}\n\n"
        f"Explicá esta decisión."
    )

    if _chat:
        try:
            resp = _chat([
                {"role": "system", "content": _EXPLAIN_SYS},
                {"role": "user", "content": user_msg},
            ], max_tokens=500)
            text = resp.get("content", "")
            if text:
                return _parse_explanation(text, decision)
        except Exception:
            pass

    return _explain_heuristic(decision, alternatives, context)


def _parse_explanation(text: str, decision: str) -> dict:
    """Parsea la explicación del LLM."""
    lines = text.strip().split("\n")
    explanation = text.strip()

    # Detectar factores clave (líneas que empiezan con número o guión)
    key_factors = []
    risks = []
    in_risks = False
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if "riesgo" in line.lower() or "limitación" in line.lower():
            in_risks = True
            continue
        if in_risks and (line.startswith("-") or line.startswith("*") or line[0].isdigit()):
            risks.append(line.lstrip("-* 0123456789."))
        elif line.startswith("-") or line.startswith("*") or (line[0].isdigit() and "." in line[:3]):
            clean = line.lstrip("-* 0123456789.)").strip()
            if clean:
                key_factors.append(clean)

    return {
        "explanation": explanation,
        "decision": decision,
        "confidence": 0.8 if len(key_factors) >= 2 else 0.6,
        "key_factors": key_factors[:5],
        "risks": risks[:3],
        "timestamp": time.time(),
    }


def _explain_heuristic(decision: str, alternatives: list[str] = None, context: str = "") -> dict:
    """Explicación heurística sin LLM."""
    parts = ["Decisión: %s" % decision]
    if alternatives:
        parts.append("Se descartaron %d alternativas: %s" % (
            len(alternatives), ", ".join(alternatives[:3])))
    if context:
        parts.append("Contexto: %s" % context[:200])

    return {
        "explanation": ". ".join(parts),
        "decision": decision,
        "confidence": 0.5,
        "key_factors": ["Decisión basada en análisis heurístico"],
        "risks": ["Sin LLM disponible para explicación detallada"],
        "timestamp": time.time(),
    }


def explain_tool_choice(tool_name: str, task: str, available_tools: list[str] = None) -> dict:
    """Explica por qué se eligió una tool específica para una tarea."""
    alternatives = [t for t in (available_tools or []) if t != tool_name]

    decision = "Usar '%s' para: %s" % (tool_name, task[:100])
    context = "Tools disponibles: %s" % ", ".join((available_tools or [])[:10])

    return explain_decision(decision, alternatives[:5], context)


def explain_error(error: str, action_taken: str = "", context: str = "") -> dict:
    """Explica qué pasó cuando hubo un error."""
    decision = "Manejo de error: %s" % (action_taken or "reportar al usuario")
    context = "Error: %s. %s" % (error[:200], context[:200])

    return explain_decision(decision, ["reintentar", "ignorar", "abortar"], context)


def format_explanation(explanation: dict) -> str:
    """Formatea explicación para mostrar."""
    lines = ["Explicación de decisión:"]
    lines.append("  Decisión: %s" % explanation.get("decision", ""))
    lines.append("  Explicación: %s" % explanation.get("explanation", "")[:300])
    if explanation.get("key_factors"):
        lines.append("  Factores clave:")
        for f in explanation["key_factors"]:
            lines.append("    - %s" % f)
    if explanation.get("risks"):
        lines.append("  Riesgos:")
        for r in explanation["risks"]:
            lines.append("    ⚠ %s" % r)
    lines.append("  Confianza: %.0f%%" % (explanation.get("confidence", 0) * 100))
    return "\n".join(lines)
