"""
agentic_rag.py — Agentic RAG para ERIS.

Cuando la pregunta del usuario es compleja, la descompone en sub-queries,
busca en paralelo en ChromaDB, y sintetiza los resultados en una respuesta
unificada. Para preguntas simples, delega al RAG estándar.

Flujo:
  1. Evaluar complejidad de la query
  2. Si es compleja: descomponer en 2-5 sub-queries (vía LLM o heurística)
  3. Buscar cada sub-query en ChromaDB (búsqueda paralela)
  4. Deduplicar y rankear resultados
  5. Sintetizar respuesta con el LLM
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from core.rag_pipeline import query_documents, _get_collection, _get_embedding
except ImportError:
    query_documents = None

try:
    from core.agent_architecture import _chat
except ImportError:
    _chat = None


# ── Evaluación de complejidad ────────────────────────────────────────────────

_SIMPLE_PATTERNS = re.compile(
    r"^(qué|cuál|cuáles|como|cómo|dónde|cuándo|quién|cuánto|existe|hay|tiene|está|"
    r"puedo|hago|sirve|definí|definir|explicá|explicar)\s",
    re.IGNORECASE,
)

_COMPLEX_MARKERS = [
    " y ", " o ", " compará", "comparar", "diferencia", "relacioná", "relacionar",
    "analizá", "analizar", "evaluá", "evaluar", "resumé", "resumir",
    "qué pasó", "por qué", "causa", "consecuencia", "impacto",
    "listá", "enumerate", "todas las", "todos los",
]


def _is_complex(query: str) -> bool:
    """Determina si una query requiere descomposición."""
    q = query.lower().strip()
    if len(q) > 120:
        return True
    if q.count("?") >= 2:
        return True
    for marker in _COMPLEX_MARKERS:
        if marker in q:
            return True
    words = q.split()
    if len(words) > 15:
        return True
    return False


# ── Descomposición de queries ────────────────────────────────────────────────

_DECOMPOSE_SYS = (
    "Sos un descomponedor de queries para búsqueda semántica. Dada una pregunta "
    "compleja del usuario, descomponela en 2-5 sub-queries independientes que "
    "se puedan buscar por separado en una base de conocimiento. Cada sub-query "
    "debe ser concreta y auto-contenida.\n"
    "Respondé SOLO con un JSON válido: [\"sub-query 1\", \"sub-query 2\", ...]\n"
    "No agregues texto fuera del JSON."
)


def _decompose_with_llm(query: str) -> list[str]:
    """Usa el LLM para descomponer una query compleja en sub-queries."""
    if _chat is None:
        return []
    try:
        resp = _chat([
            {"role": "system", "content": _DECOMPOSE_SYS},
            {"role": "user", "content": f"Query: {query}"},
        ], max_tokens=512)
        text = resp.get("content", "")
        m = re.search(r"\[[\s\S]*?\]", text)
        if m:
            data = json.loads(m.group(0))
            if isinstance(data, list) and len(data) >= 2:
                return [str(s).strip() for s in data[:5] if str(s).strip()]
    except Exception:
        pass
    return []


def _decompose_heuristic(query: str) -> list[str]:
    """Descomposición heurística sin LLM: separa por conectores y preguntas."""
    queries = []
    # Separar por "?" y reconstruir
    parts = [p.strip() for p in re.split(r"\?+", query) if p.strip()]
    for part in parts:
        # Limpiar conectores al inicio
        part = re.sub(r"^(y|o|pero|además|también|ahora)\s+", "", part, flags=re.IGNORECASE)
        if len(part) > 10:
            queries.append(part)
    # Si no se pudo separar, devolver la original
    if len(queries) < 2:
        # Intentar por conectores
        parts = re.split(r"\s+(?:y|o|además|también|compará|comparar)\s+", query, flags=re.IGNORECASE)
        if len(parts) >= 2:
            queries = [p.strip() for p in parts if len(p.strip()) > 10]
    return queries[:5] if len(queries) >= 2 else []


def decompose_query(query: str) -> list[str]:
    """Descompone una query en sub-queries. Intenta LLM primero, heurística como fallback."""
    # Intentar con LLM
    result = _decompose_with_llm(query)
    if result:
        return result
    # Fallback heurístico
    result = _decompose_heuristic(query)
    if result:
        return result
    return [query]


# ── Búsqueda paralela ────────────────────────────────────────────────────────

def _search_single(query: str, top_k: int = 5) -> list[dict]:
    """Busca una sub-query en ChromaDB."""
    if query_documents is None:
        return []
    return query_documents(query, top_k=top_k)


def parallel_search(queries: list[str], top_k: int = 5) -> list[dict]:
    """Busca múltiples queries en paralelo y deduplica resultados."""
    all_results = []
    with ThreadPoolExecutor(max_workers=min(len(queries), 5)) as executor:
        futures = {executor.submit(_search_single, q, top_k + 2): q for q in queries}
        for future in as_completed(futures):
            try:
                results = future.result()
                all_results.extend(results)
            except Exception:
                continue

    # Deduplicar por source + chunk
    seen = set()
    unique = []
    for r in all_results:
        key = (r.get("source", ""), r.get("chunk", 0))
        if key not in seen:
            seen.add(key)
            unique.append(r)

    # Rankear por score (menor = mejor en cosine distance)
    unique.sort(key=lambda x: x.get("score", 999))
    return unique[:top_k * 2]


# ── Síntesis ─────────────────────────────────────────────────────────────────

_SYNTHESIZE_SYS = (
    "Sos un sintetizador de información. Dados los resultados de búsqueda de "
    "múltiples fuentes, generá una respuesta coherente y concisa que responda "
    "la pregunta original del usuario. Citá las fuentes cuando sea relevante."
)


def _synthesize(query: str, results: list[dict]) -> str:
    """Sintetiza los resultados de búsqueda en una respuesta unificada."""
    if not results:
        return "No se encontró información relevante en las fuentes indexadas."

    # Formatear resultados para el LLM
    context_parts = []
    for i, r in enumerate(results, 1):
        source = r.get("source", "?")
        text = r.get("text", "")[:500]
        score = r.get("score", 0)
        context_parts.append(f"[{i}] Fuente: {source} (relevancia: {score:.3f})\n{text}")
    context = "\n\n".join(context_parts)

    if _chat is None:
        # Sin LLM: devolver resultados crudos
        lines = [f"Resultados encontrados ({len(results)}):"]
        for r in results:
            lines.append(f"- [{r.get('source', '?')}] {r.get('text', '')[:200]}")
        return "\n".join(lines)

    try:
        resp = _chat([
            {"role": "system", "content": _SYNTHESIZE_SYS},
            {"role": "user", "content": f"Pregunta: {query}\n\nFuentes encontradas:\n{context}"},
        ], max_tokens=1024)
        text = resp.get("content", "").strip()
        if text:
            return text
    except Exception:
        pass

    # Fallback: respuesta cruda
    lines = [f"Resultados encontrados ({len(results)}):"]
    for r in results:
        lines.append(f"- [{r.get('source', '?')}] {r.get('text', '')[:200]}")
    return "\n".join(lines)


# ── API pública ──────────────────────────────────────────────────────────────

def agentic_query(query: str, top_k: int = 5, force_decompose: bool = False) -> dict:
    """Búsqueda agentic: descompone, busca en paralelo, sintetiza.

    Args:
        query: Pregunta del usuario.
        top_k: Número máximo de resultados a devolver.
        force_decompose: Forzar descomposición aunque la query parezca simple.

    Returns:
        dict con keys: query, sub_queries, results, answer, stats
    """
    if not query.strip():
        return {"error": "Query vacía"}

    is_complex = force_decompose or _is_complex(query)
    sub_queries = []

    if is_complex:
        sub_queries = decompose_query(query)
        queries_to_search = sub_queries
    else:
        queries_to_search = [query]

    # Buscar
    results = parallel_search(queries_to_search, top_k=top_k)

    # Sintetizar
    answer = _synthesize(query, results)

    return {
        "query": query,
        "is_complex": is_complex,
        "sub_queries": sub_queries,
        "num_results": len(results),
        "results": results[:top_k],
        "answer": answer,
        "stats": {
            "queries_searched": len(queries_to_search),
            "total_results_before_dedup": len(queries_to_search) * (top_k + 2),
        },
    }
