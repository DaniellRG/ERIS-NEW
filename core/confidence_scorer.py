"""
confidence_scorer.py — Cuantifica confianza en respuestas antes de afirmar.

Analiza múltiples factores para generar un score de confianza:
  - Cantidad de evidencia disponible
  - Contradicciones en la evidencia
  - Complejidad del topic
  - Historial de errores en temas similares
  - Calidad de las fuentes
"""
from __future__ import annotations

import json
import time

try:
    from core.knowledge_verifier import verify_claim
except ImportError:
    verify_claim = None

try:
    from core.error_pattern_db import get_pattern_db
except ImportError:
    get_pattern_db = None


def score_confidence(
    claim: str,
    evidence: list[str] = None,
    topic: str = "",
    context: str = "",
) -> dict:
    """Calcula score de confianza para un claim.

    Args:
        claim: La afirmación a evaluar
        evidence: Evidencia disponible (strings)
        topic: Categoría del tema
        context: Contexto adicional

    Returns:
        dict con: score, factors, recommendation, explanation
    """
    factors = {}

    # Factor 1: Verificación RAG
    if verify_claim:
        verification = verify_claim(claim, context)
        verdict = verification.get("verdict", "unverifiable")
        if verdict == "supported":
            factors["rag_verification"] = {"score": 0.9, "detail": "Evidencia soportada en RAG"}
        elif verdict == "partially_supported":
            factors["rag_verification"] = {"score": 0.6, "detail": "Parcialmente soportado"}
        elif verdict == "contradicted":
            factors["rag_verification"] = {"score": 0.1, "detail": "Contradecido por evidencia"}
        else:
            factors["rag_verification"] = {"score": 0.3, "detail": "Sin evidencia en RAG"}

    # Factor 2: Cantidad de evidencia
    ev_count = len(evidence or [])
    if ev_count >= 5:
        factors["evidence_quantity"] = {"score": 0.9, "detail": "%d fuentes" % ev_count}
    elif ev_count >= 2:
        factors["evidence_quantity"] = {"score": 0.7, "detail": "%d fuentes" % ev_count}
    elif ev_count == 1:
        factors["evidence_quantity"] = {"score": 0.5, "detail": "1 fuente"}
    else:
        factors["evidence_quantity"] = {"score": 0.2, "detail": "Sin evidencia directa"}

    # Factor 3: Complejidad del claim
    words = len(claim.split())
    if words > 50:
        factors["complexity"] = {"score": 0.4, "detail": "Claim muy complejo (%d palabras)" % words}
    elif words > 20:
        factors["complexity"] = {"score": 0.6, "detail": "Claim moderado (%d palabras)" % words}
    else:
        factors["complexity"] = {"score": 0.8, "detail": "Claim simple (%d palabras)" % words}

    # Factor 4: Errores históricos en topic similar
    if topic and get_pattern_db:
        try:
            db = get_pattern_db()
            errors = db.get("errors", []) if isinstance(db, dict) else []
            topic_errors = [e for e in errors if topic.lower() in str(e).lower()]
            if len(topic_errors) > 5:
                factors["historical_errors"] = {"score": 0.3, "detail": "%d errores históricos en '%s'" % (len(topic_errors), topic)}
            elif len(topic_errors) > 0:
                factors["historical_errors"] = {"score": 0.6, "detail": "%d errores históricos en '%s'" % (len(topic_errors), topic)}
            else:
                factors["historical_errors"] = {"score": 0.8, "detail": "Sin errores conocidos en '%s'" % topic}
        except Exception:
            factors["historical_errors"] = {"score": 0.5, "detail": "No disponible"}

    # Factor 5: Especificidad del claim (más específico = más verificable)
    specific_indicators = ["función", "clase", "archivo", "línea", "método", "variable", "imports"]
    specificity = sum(1 for ind in specific_indicators if ind in claim.lower())
    if specificity >= 3:
        factors["specificity"] = {"score": 0.8, "detail": "Claim muy específico"}
    elif specificity >= 1:
        factors["specificity"] = {"score": 0.6, "detail": "Claim moderadamente específico"}
    else:
        factors["specificity"] = {"score": 0.4, "detail": "Claim genérico"}

    # Calcular score final
    if factors:
        weights = {"rag_verification": 0.35, "evidence_quantity": 0.25, "complexity": 0.15,
                    "historical_errors": 0.15, "specificity": 0.10}
        weighted_sum = 0
        total_weight = 0
        for key, factor in factors.items():
            w = weights.get(key, 0.1)
            weighted_sum += factor["score"] * w
            total_weight += w
        final_score = round(weighted_sum / max(0.01, total_weight) * 100)
    else:
        final_score = 50

    # Recomendación
    if final_score >= 80:
        recommendation = "Seguro para afirmar"
    elif final_score >= 60:
        recommendation = "Afirmar con cautela, mencionar incertidumbre"
    elif final_score >= 40:
        recommendation = "Mejor decir 'no estoy seguro' o buscar más evidencia"
    else:
        recommendation = "NO afirmar — confianza muy baja, verificar antes"

    return {
        "claim": claim[:200],
        "confidence_score": final_score,
        "factors": factors,
        "recommendation": recommendation,
        "timestamp": time.time(),
    }


def score_multiple(claims: list[str]) -> list[dict]:
    """Scoring en lote."""
    return [score_confidence(c) for c in claims]


def batch_score_with_evidence(claims: list[dict]) -> list[dict]:
    """Scoring con evidencia pre-cargada.

    claims: [{"claim": "...", "evidence": ["..."], "topic": "..."}]
    """
    results = []
    for c in claims:
        results.append(score_confidence(
            c.get("claim", ""),
            c.get("evidence", []),
            c.get("topic", ""),
            c.get("context", ""),
        ))
    return results


def format_confidence(result: dict) -> str:
    """Formatea resultado de confianza."""
    score = result.get("confidence_score", 0)
    if score >= 80:
        icon = "🟢"
    elif score >= 60:
        icon = "🟡"
    elif score >= 40:
        icon = "🟠"
    else:
        icon = "🔴"

    lines = [
        "%s Confianza: %d/100" % (icon, score),
        "  %s" % result.get("recommendation", ""),
        "",
        "Factores:",
    ]
    for name, factor in result.get("factors", {}).items():
        s = round(factor["score"] * 100)
        lines.append("  - %s: %d%% — %s" % (name, s, factor.get("detail", "")))
    return "\n".join(lines)
