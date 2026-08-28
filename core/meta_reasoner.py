"""
meta_reasoner.py — Razonamiento sobre el propio razonamiento.

Analiza la calidad del proceso de pensamiento del agente:
  - ¿Fue lógico el razonamiento?
  - ¿Saltó conclusiones sin evidencia?
  - ¿Consideró suficientes alternativas?
  - ¿Usó la evidencia correcta?

Funciona como un "crítico interno" que evalúa el proceso, no solo el resultado.
"""
from __future__ import annotations

import json
import re
import time

try:
    from core.agent_architecture import _chat
except ImportError:
    _chat = None


_META_SYS = (
    "Sos un meta-razonador. Analizá el PROCESO de pensamiento de un asistente "
    "(no el resultado final, sino CÓMO llegó a él). Evaluá:\n\n"
    "1. LÓGICA: ¿El razonamiento es deductivamente válido?\n"
    "2. EVIDENCIA: ¿Usó evidencia suficiente y relevante?\n"
    "3. ALTERNATIVAS: ¿Consideró suficientes opciones?\n"
    "4. SESGOS: ¿Detectás algún sesgo (confirmación, anclaje, disponibilidad)?\n"
    "5. SALTOS: ¿Saltó conclusiones sin justificación?\n\n"
    "Respondé con JSON:\n"
    '{"score": 0-100, "logic": "bueno/regular/malo", "evidence": "...", '
    '"biases": ["sesgo1"], "gaps": ["laguna1"], "suggestion": "mejora sugerida"}'
)


def meta_analyze(
    reasoning_trace: str,
    decision: str = "",
    context: str = "",
) -> dict:
    """Analiza la calidad del razonamiento.

    Args:
        reasoning_trace: El proceso de pensamiento a analizar
        decision: La decisión final a la que llegó
        context: Contexto adicional

    Returns:
        dict con: score, logic, evidence_quality, biases, gaps, suggestion
    """
    user_msg = (
        f"Proceso de pensamiento:\n{reasoning_trace[:1500]}\n\n"
        f"Decisión final: {decision}\n"
        f"Contexto: {context}\n\n"
        f"Analizá la calidad del razonamiento."
    )

    if _chat:
        try:
            resp = _chat([
                {"role": "system", "content": _META_SYS},
                {"role": "user", "content": user_msg},
            ], max_tokens=600)
            text = resp.get("content", "")
            if text:
                return _parse_meta_analysis(text)
        except Exception:
            pass

    return _meta_heuristic(reasoning_trace, decision)


def _parse_meta_analysis(text: str) -> dict:
    """Parsea análisis meta del LLM."""
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        try:
            data = json.loads(m.group(0))
            return {
                "score": min(100, max(0, int(data.get("score", 50)))),
                "logic": data.get("logic", "desconocido"),
                "evidence_quality": data.get("evidence", ""),
                "biases": data.get("biases", []),
                "gaps": data.get("gaps", []),
                "suggestion": data.get("suggestion", ""),
                "timestamp": time.time(),
            }
        except Exception:
            pass

    return {
        "score": 50,
        "logic": "no analizable",
        "evidence_quality": text[:200],
        "biases": [],
        "gaps": [],
        "suggestion": "No se pudo parsear el análisis",
        "timestamp": time.time(),
    }


def _meta_heuristic(reasoning: str, decision: str) -> dict:
    """Análisis heurístico sin LLM."""
    score = 70
    biases = []
    gaps = []

    # Detectar posibles sesgos por patrones de texto
    reasoning_lower = reasoning.lower()
    if "siempre" in reasoning_lower or "nunca" in reasoning_lower:
        biases.append("Generalización absoluta (siempre/nunca)")
        score -= 10
    if "claramente" in reasoning_lower or "obviamente" in reasoning_lower:
        biases.append("Falsa certeza (claramente/obviamente)")
        score -= 5
    if "todos" in reasoning_lower and "saben" in reasoning_lower:
        biases.append("Asumir conocimiento compartido")
        score -= 5

    # Verificar que hay evidencia
    evidence_markers = ["porque", "dado que", "evidencia", "datos", "resultado", "verifiqué"]
    has_evidence = any(m in reasoning_lower for m in evidence_markers)
    if not has_evidence:
        gaps.append("Sin evidencia explícita que soporte la conclusión")
        score -= 15

    # Verificar que consideró alternativas
    alt_markers = ["alternativa", "otra opción", "podría", "también", "en vez de"]
    has_alternatives = any(m in reasoning_lower for m in alt_markers)
    if not has_alternatives:
        gaps.append("No se mencionaron alternativas")
        score -= 10

    return {
        "score": max(0, min(100, score)),
        "logic": "bueno" if score >= 70 else ("regular" if score >= 50 else "malo"),
        "evidence_quality": "Detectada" if has_evidence else "No detectada",
        "biases": biases,
        "gaps": gaps,
        "suggestion": "Agregar evidencia explícita y considerar alternativas" if gaps else "Razonamiento sólido",
        "timestamp": time.time(),
    }


def quick_meta_check(reasoning: str) -> str:
    """Check rápido de calidad de razonamiento (sin LLM)."""
    result = _meta_heuristic(reasoning, "")
    return "Score: %d/100 [%s]. Biases: %s. Gaps: %s" % (
        result["score"], result["logic"],
        ", ".join(result["biases"]) or "ninguno",
        ", ".join(result["gaps"]) or "ninguno",
    )


def format_meta_analysis(analysis: dict) -> str:
    """Formatea análisis meta para mostrar."""
    lines = ["Meta-análisis de razonamiento:"]
    lines.append("  Score: %d/100 [%s]" % (analysis.get("score", 0), analysis.get("logic", "?")))
    lines.append("  Evidencia: %s" % analysis.get("evidence_quality", ""))
    if analysis.get("biases"):
        lines.append("  Sesgos detectados:")
        for b in analysis["biases"]:
            lines.append("    ⚠ %s" % b)
    if analysis.get("gaps"):
        lines.append("  Lagunas:")
        for g in analysis["gaps"]:
            lines.append("    - %s" % g)
    if analysis.get("suggestion"):
        lines.append("  Sugerencia: %s" % analysis["suggestion"])
    return "\n".join(lines)
