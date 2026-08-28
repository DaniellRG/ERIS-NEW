"""
knowledge_verifier.py — Verificación de hechos antes de afirmar.

Antes de que ERIS afirme algo como verdad, verifica:
  - ¿Está soportado por documentos indexados en RAG?
  - ¿Es consistente con la memoria semántica?
  - ¿Contradice algo conocido?

Reduce alucinaciones al anclar respuestas en evidencia real.
"""
from __future__ import annotations

import json
import re
import time

try:
    from core.agent_architecture import _chat
except ImportError:
    _chat = None

try:
    from core.rag_pipeline import query_documents
except ImportError:
    query_documents = None

try:
    from core.semantic_memory import get_memory_system
except ImportError:
    get_memory_system = None


def verify_claim(claim: str, context: str = "") -> dict:
    """Verifica un claim/afirmación contra fuentes disponibles.

    Args:
        claim: La afirmación a verificar
        context: Contexto adicional

    Returns:
        dict con: verdict, confidence, evidence, source, warnings
    """
    evidence_parts = []
    warnings = []

    # 1. Buscar en RAG
    rag_evidence = _search_rag(claim)
    if rag_evidence:
        evidence_parts.extend(rag_evidence)

    # 2. Buscar en memoria semántica
    mem_evidence = _search_memory(claim)
    if mem_evidence:
        evidence_parts.extend(mem_evidence)

    # 3. Verificar con LLM si hay evidencia
    if evidence_parts and _chat:
        return _llm_verify(claim, evidence_parts, context)

    # 4. Sin evidencia disponible
    return {
        "claim": claim,
        "verdict": "unverifiable",
        "confidence": 0.0,
        "evidence": evidence_parts,
        "warnings": ["No se encontraron fuentes para verificar este claim"],
        "source": "none",
        "timestamp": time.time(),
    }


def _search_rag(claim: str) -> list[dict]:
    """Busca evidencia en el pipeline RAG."""
    if not query_documents:
        return []
    try:
        results = query_documents(claim, n_results=3)
        evidence = []
        for doc in results:
            content = doc.get("content", "") or doc.get("text", "")
            if content:
                evidence.append({
                    "source": "rag",
                    "content": content[:500],
                    "relevance": doc.get("score", 0),
                })
        return evidence
    except Exception:
        return []


def _search_memory(claim: str) -> list[dict]:
    """Busca evidencia en la memoria semántica."""
    if not get_memory_system:
        return []
    try:
        mem = get_memory_system()
        results = mem.search(claim, limit=3) if hasattr(mem, "search") else []
        evidence = []
        for r in results:
            if hasattr(r, "content"):
                evidence.append({
                    "source": "semantic_memory",
                    "content": str(r.content)[:500],
                    "relevance": getattr(r, "score", 0),
                })
            elif isinstance(r, dict):
                evidence.append({
                    "source": "semantic_memory",
                    "content": str(r.get("content", r.get("text", "")))[:500],
                    "relevance": r.get("score", 0),
                })
        return evidence
    except Exception:
        return []


def _llm_verify(claim: str, evidence: list[dict], context: str) -> dict:
    """Usa el LLM para verificar el claim contra la evidencia."""
    evidence_text = "\n".join(
        "- [%s] %s" % (e.get("source", "?"), e.get("content", "")[:200])
        for e in evidence[:5]
    )

    prompt = (
        "Verificá si este claim está soportado por la evidencia disponible.\n\n"
        "Claim: %s\n\n"
        "Evidencia encontrada:\n%s\n\n"
        "Contexto: %s\n\n"
        "Respondé con JSON:\n"
        '{"verdict": "supported|contradicted|partially_supported|unverifiable", '
        '"confidence": 0-100, "explanation": "por qué", '
        '"warnings": ["advertencias si las hay"]}'
    ) % (claim, evidence_text, context or "(ninguno)")

    try:
        resp = _chat([
            {"role": "system", "content": "Sos un verificador de hechos. Sé estricto: solo marcá como 'supported' si la evidencia lo confirma directamente."},
            {"role": "user", "content": prompt},
        ], max_tokens=400)
        text = resp.get("content", "")
        return _parse_verdict(text, claim, evidence)
    except Exception:
        return {
            "claim": claim,
            "verdict": "unverifiable",
            "confidence": 0,
            "evidence": evidence,
            "warnings": ["Error en verificación LLM"],
            "source": "llm_error",
            "timestamp": time.time(),
        }


def _parse_verdict(text: str, claim: str, evidence: list[dict]) -> dict:
    """Parsea el veredicto del LLM."""
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        try:
            data = json.loads(m.group(0))
            return {
                "claim": claim,
                "verdict": data.get("verdict", "unverifiable"),
                "confidence": min(100, max(0, int(data.get("confidence", 50)))),
                "evidence": evidence,
                "explanation": data.get("explanation", ""),
                "warnings": data.get("warnings", []),
                "source": "llm",
                "timestamp": time.time(),
            }
        except Exception:
            pass

    return {
        "claim": claim,
        "verdict": "unverifiable",
        "confidence": 0,
        "evidence": evidence,
        "explanation": text[:300],
        "warnings": ["No se pudo parsear veredicto"],
        "source": "parse_error",
        "timestamp": time.time(),
    }


def verify_before_stating(statement: str) -> dict:
    """Wrapper para usar antes de afirmar algo.
    Devuelve el veredicto y si es seguro afirmar."""
    result = verify_claim(statement)
    safe = result["verdict"] in ("supported", "partially_supported") and result["confidence"] >= 60
    result["safe_to_state"] = safe
    return result


def batch_verify(claims: list[str]) -> list[dict]:
    """Verifica múltiples claims en lote."""
    return [verify_claim(c) for c in claims]


def format_verdict(verification: dict) -> str:
    """Formatea veredicto para mostrar."""
    icons = {
        "supported": "✓",
        "contradicted": "✗",
        "partially_supported": "~",
        "unverifiable": "?",
    }
    v = verification.get("verdict", "unverifiable")
    icon = icons.get(v, "?")
    lines = [
        "%s Veredicto: %s (confianza: %d%%)" % (icon, v, verification.get("confidence", 0)),
        "  Claim: %s" % verification.get("claim", "")[:100],
    ]
    if verification.get("explanation"):
        lines.append("  Explicación: %s" % verification["explanation"][:200])
    if verification.get("warnings"):
        for w in verification["warnings"]:
            lines.append("  ⚠ %s" % w)
    return "\n".join(lines)
