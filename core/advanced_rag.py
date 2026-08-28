"""
ERIS Advanced RAG — Hybrid search (BM25 + semantic) con cross-encoder re-ranking
y citation tracking. Mejora significativa sobre pure cosine search.

Componentes:
1. BM25 (keyword) search — preciso para nombres, códigos, acrónimos
2. Semantic (ChromaDB) search — mejor para queries conceptuales
3. Hybrid score fusion — combina ambos scores
4. Cross-encoder re-ranking — re-ordena los resultados para máxima precisión
5. Citation tracking — resultados con [1], [2], etc. y fuentes
"""
import json
import re
import hashlib
from pathlib import Path
from typing import Optional
from functools import lru_cache

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Lazy imports (heavy modules)
_bm25_index = None
_bm25_corpus = None
_bm25_metadata = None
_cross_encoder = None
_reranker_name = "cross-encoder/ms-marco-MiniLM-L-6-v2"


def _get_bm25_corpus():
    """Build BM25 corpus from ChromaDB documents."""
    global _bm25_index, _bm25_corpus, _bm25_metadata
    if _bm25_index is not None:
        return _bm25_index, _bm25_corpus, _bm25_metadata
    try:
        import chromadb
        from rank_bm25 import BM25Okapi
        client = chromadb.PersistentClient(path=str(_DATA_DIR / "chroma_db"))
        collection = client.get_collection("eris_documents")
        results = collection.get(include=["documents", "metadatas"])
        if not results["documents"]:
            return None, None, None
        _bm25_corpus = results["documents"]
        _bm25_metadata = results["metadatas"]
        # Tokenize for BM25
        tokenized = [doc.lower().split() for doc in _bm25_corpus]
        _bm25_index = BM25Okapi(tokenized)
        return _bm25_index, _bm25_corpus, _bm25_metadata
    except Exception as e:
        print(f"[AdvancedRAG] BM25 index build failed: {e}")
        return None, None, None


def _get_cross_encoder():
    """Lazy-load cross-encoder model."""
    global _cross_encoder
    if _cross_encoder is not None:
        return _cross_encoder
    try:
        from sentence_transformers import CrossEncoder
        _cross_encoder = CrossEncoder(_reranker_name, max_length=512)
        print(f"[AdvancedRAG] Cross-encoder loaded: {_reranker_name}")
        return _cross_encoder
    except Exception as e:
        print(f"[AdvancedRAG] Cross-encoder load failed: {e}")
        return None


def _bm25_search(query: str, top_k: int = 20) -> list:
    """BM25 keyword search."""
    bm25, corpus, metadata = _get_bm25_corpus()
    if bm25 is None:
        return []
    tokenized_query = query.lower().split()
    scores = bm25.get_scores(tokenized_query)
    top_indices = scores.argsort()[::-1][:top_k]
    results = []
    for idx in top_indices:
        if scores[idx] > 0:
            results.append({
                "text": corpus[idx],
                "metadata": metadata[idx] if metadata else {},
                "bm25_score": float(scores[idx]),
                "rank": len(results) + 1,
            })
    return results


def _semantic_search(query: str, top_k: int = 20) -> list:
    """ChromaDB semantic search using Ollama embeddings (bypasses ChromaDB's own embedder)."""
    try:
        import chromadb
        from core.llm_bridge import get_embedding
        client = chromadb.PersistentClient(path=str(_DATA_DIR / "chroma_db"))
        collection = client.get_collection("eris_documents")
        # Use Ollama embeddings to match the 768-dim collection
        query_embedding = get_embedding(query)
        if not query_embedding or len(query_embedding) < 100:
            # Fallback: Ollama down, skip semantic
            return []
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )
        output = []
        for i in range(len(results["documents"][0])):
            output.append({
                "text": results["documents"][0][i],
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                "semantic_score": 1.0 - results["distances"][0][i],
                "rank": len(output) + 1,
            })
        return output
    except Exception as e:
        print(f"[AdvancedRAG] Semantic search failed: {e}")
        return []


def _hybrid_fuse(bm25_results: list, semantic_results: list, alpha: float = 0.5) -> list:
    """Fuse BM25 and semantic results using Reciprocal Rank Fusion (RRF)."""
    # Combine all unique documents
    doc_map = {}  # text_hash -> {text, metadata, scores}
    
    for r in bm25_results:
        key = hashlib.md5(r["text"][:200].encode()).hexdigest()
        if key not in doc_map:
            doc_map[key] = {"text": r["text"], "metadata": r["metadata"], "bm25_rank": r["rank"], "sem_rank": 999}
        else:
            doc_map[key]["bm25_rank"] = r["rank"]
    
    for r in semantic_results:
        key = hashlib.md5(r["text"][:200].encode()).hexdigest()
        if key not in doc_map:
            doc_map[key] = {"text": r["text"], "metadata": r["metadata"], "bm25_rank": 999, "sem_rank": r["rank"]}
        else:
            doc_map[key]["sem_rank"] = r["rank"]
            doc_map[key]["semantic_score"] = r.get("semantic_score", 0)
    
    # RRF scoring: score = alpha / (k + bm25_rank) + (1-alpha) / (k + sem_rank)
    k = 60  # RRF constant
    for doc in doc_map.values():
        bm25_contrib = alpha / (k + doc["bm25_rank"]) if doc["bm25_rank"] < 999 else 0
        sem_contrib = (1 - alpha) / (k + doc["sem_rank"]) if doc["sem_rank"] < 999 else 0
        doc["hybrid_score"] = bm25_contrib + sem_contrib
    
    # Sort by hybrid score
    sorted_docs = sorted(doc_map.values(), key=lambda x: x["hybrid_score"], reverse=True)
    for i, doc in enumerate(sorted_docs):
        doc["rank"] = i + 1
    return sorted_docs


def _rerank(query: str, results: list, top_k: int = 5) -> list:
    """Re-rank results using cross-encoder."""
    ce = _get_cross_encoder()
    if ce is None or not results:
        return results[:top_k]
    try:
        pairs = [(query, r["text"][:512]) for r in results]
        scores = ce.predict(pairs)
        for i, score in enumerate(scores):
            results[i]["rerank_score"] = float(score)
        results.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
    except Exception as e:
        print(f"[AdvancedRAG] Reranking failed: {e}")
    return results[:top_k]


def advanced_search(query: str, top_k: int = 5, use_reranker: bool = True,
                    alpha: float = 0.5) -> dict:
    """
    Main entry point: hybrid BM25+semantic search with optional cross-encoder re-ranking.
    
    Returns:
        {
            "results": [{text, source, filename, chunk, score, citation_num}],
            "citations": "[1] filename.md:chunk\\n[2] doc.pdf:chunk",
            "method": "hybrid+rerank" | "hybrid" | "semantic" | "bm25" | "none",
            "total_candidates": int,
        }
    """
    # Get candidates from both engines
    bm25_results = _bm25_search(query, top_k=20)
    semantic_results = _semantic_search(query, top_k=20)
    
    if not bm25_results and not semantic_results:
        return {"results": [], "citations": "", "method": "none", "total_candidates": 0}
    
    # Fuse results
    if bm25_results and semantic_results:
        candidates = _hybrid_fuse(bm25_results, semantic_results, alpha=alpha)
        method = "hybrid"
    elif semantic_results:
        candidates = semantic_results
        method = "semantic"
    else:
        candidates = bm25_results
        method = "bm25"
    
    total = len(candidates)
    
    # Re-rank with cross-encoder
    if use_reranker and candidates:
        candidates = _rerank(query, candidates, top_k=top_k)
        method += "+rerank"
    else:
        candidates = candidates[:top_k]
    
    # Format results with citations
    results = []
    citations_lines = []
    for i, doc in enumerate(candidates):
        meta = doc.get("metadata", {})
        citation_num = i + 1
        results.append({
            "text": doc["text"][:800],
            "source": meta.get("source", "unknown"),
            "filename": meta.get("filename", "unknown"),
            "chunk": meta.get("chunk", 0),
            "score": round(doc.get("hybrid_score", doc.get("rerank_score", doc.get("semantic_score", 0))), 4),
            "citation_num": citation_num,
        })
        citations_lines.append(
            f"[{citation_num}] {meta.get('filename', '?')} "
            f"(chunk {meta.get('chunk', '?')}, score {results[-1]['score']})"
        )
    
    return {
        "results": results,
        "citations": "\n".join(citations_lines),
        "method": method,
        "total_candidates": total,
    }


def invalidate_cache():
    """Force rebuild of BM25 index on next search."""
    global _bm25_index, _bm25_corpus, _bm25_metadata
    _bm25_index = None
    _bm25_corpus = None
    _bm25_metadata = None


def advanced_rag_tool(parameters: dict = None, player=None) -> str:
    """Tool entry point for Gemini."""
    params = parameters or {}
    action = params.get("action", "search").lower()
    
    if action == "search":
        query = params.get("query", "")
        if not query:
            return "Error: se necesita 'query'."
        top_k = int(params.get("top_k", 5))
        use_reranker = params.get("rerank", True)
        result = advanced_search(query, top_k=top_k, use_reranker=use_reranker)
        
        if not result["results"]:
            return f"No se encontraron resultados para: {query}"
        
        output = f"Método: {result['method']} | Candidatos: {result['total_candidates']}\n\n"
        for r in result["results"]:
            output += f"[{r['citation_num']}] {r['filename']} (chunk {r['chunk']}, score {r['score']})\n"
            output += f"    {r['text'][:200]}...\n\n"
        output += f"\nFuentes:\n{result['citations']}"
        return output
    
    elif action == "invalidate":
        invalidate_cache()
        return "Cache BM25 invalidado. Se reconstruirá en la próxima búsqueda."
    
    elif action == "stats":
        bm25, corpus, _ = _get_bm25_corpus()
        try:
            import chromadb
            client = chromadb.PersistentClient(path=str(_DATA_DIR / "chroma_db"))
            collection = client.get_collection("eris_documents")
            count = collection.count()
        except Exception:
            count = "unknown"
        has_ce = _cross_encoder is not None
        bm25_count = len(corpus) if corpus else 0
        return (
            f"ChromaDB documents: {count}\n"
            f"BM25 corpus: {bm25_count}\n"
            f"Cross-encoder loaded: {has_ce}\n"
            f"Index cached: {bm25 is not None}"
        )
    
    return f"Acción '{action}' no reconocida. Usa: search, invalidate, stats"
