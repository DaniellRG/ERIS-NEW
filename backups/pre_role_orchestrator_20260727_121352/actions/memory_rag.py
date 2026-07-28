"""Semantic memory with keyword-based vector search and importance tracking."""

import json
import math
import os
import re
import uuid
from collections import Counter
from datetime import datetime
from typing import Any

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
MEMORY_FILE = os.path.join(DATA_DIR, "memory_rag.json")


def _load_memory() -> dict[str, Any]:
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"memories": {}, "settings": {"max_memories": 5000, "decay_rate": 0.01}}


def _save_memory(data: dict[str, Any]) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)


STOP_WORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "dare", "ought",
    "used", "to", "of", "in", "for", "on", "with", "at", "by", "from",
    "as", "into", "through", "during", "before", "after", "above", "below",
    "between", "out", "off", "over", "under", "again", "further", "then",
    "once", "here", "there", "when", "where", "why", "how", "all", "each",
    "every", "both", "few", "more", "most", "other", "some", "such", "no",
    "nor", "not", "only", "own", "same", "so", "than", "too", "very",
    "just", "because", "but", "and", "or", "if", "while", "that", "this",
    "it", "its", "he", "she", "they", "we", "you", "i", "me", "my",
}


def _tokenize(text: str) -> list[str]:
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    tokens = text.split()
    return [t for t in tokens if t not in STOP_WORDS and len(t) > 1]


def _compute_tf(tokens: list[str]) -> dict[str, float]:
    counts = Counter(tokens)
    total = len(tokens) if tokens else 1
    return {k: v / total for k, v in counts.items()}


def _compute_idf(all_docs_tokens: list[list[str]]) -> dict[str, float]:
    doc_count = len(all_docs_tokens)
    if doc_count == 0:
        return {}
    df: Counter = Counter()
    for tokens in all_docs_tokens:
        unique = set(tokens)
        for t in unique:
            df[t] += 1
    return {t: math.log((doc_count + 1) / (count + 1)) + 1 for t, count in df.items()}


def _tfidf_vector(tokens: list[str], idf: dict[str, float]) -> dict[str, float]:
    tf = _compute_tf(tokens)
    return {term: tf_val * idf.get(term, 1.0) for term, tf_val in tf.items()}


def _cosine_sim(v1: dict[str, float], v2: dict[str, float]) -> float:
    if not v1 or not v2:
        return 0.0
    common = set(v1.keys()) & set(v2.keys())
    if not common:
        return 0.0
    dot = sum(v1[k] * v2[k] for k in common)
    mag1 = math.sqrt(sum(v ** 2 for v in v1.values()))
    mag2 = math.sqrt(sum(v ** 2 for v in v2.values()))
    if mag1 == 0 or mag2 == 0:
        return 0.0
    return dot / (mag1 * mag2)


def _keyword_overlap_score(query_tokens: list[str], doc_tokens: list[str]) -> float:
    if not query_tokens:
        return 0.0
    q_set = set(query_tokens)
    d_set = set(doc_tokens)
    overlap = q_set & d_set
    return len(overlap) / len(q_set) if q_set else 0.0


def memory_rag(parameters: dict, player=None) -> str:
    action = parameters.get("action", "recall").lower()
    data = _load_memory()
    memories = data.get("memories", {})

    if action == "store":
        content = parameters.get("content", "")
        if not content:
            return "Error: 'content' parameter is required."
        tags = parameters.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",")]
        importance = min(1.0, max(0.0, float(parameters.get("importance", 0.5))))
        memory_id = str(uuid.uuid4())[:8]
        tokens = _tokenize(content)
        memories[memory_id] = {
            "id": memory_id,
            "content": content,
            "tags": tags,
            "tokens": tokens,
            "timestamp": datetime.now().isoformat(),
            "importance": importance,
            "access_count": 0,
        }
        max_mem = data.get("settings", {}).get("max_memories", 5000)
        if len(memories) > max_mem:
            sorted_m = sorted(memories.items(), key=lambda x: x[1].get("importance", 0))
            to_remove = len(memories) - max_mem
            for mid, _ in sorted_m[:to_remove]:
                del memories[mid]
        data["memories"] = memories
        _save_memory(data)
        return f"Memory stored (id: {memory_id}) | Tags: {tags} | Importance: {importance} | Tokens: {len(tokens)}"

    elif action == "search":
        query = parameters.get("query", parameters.get("content", ""))
        if not query:
            return "Error: 'query' parameter is required."
        limit = int(parameters.get("limit", 10))
        query_tokens = _tokenize(query)
        if not query_tokens:
            return "No searchable tokens in query."
        all_doc_tokens = [m.get("tokens", _tokenize(m.get("content", ""))) for m in memories.values()]
        idf = _compute_idf(all_doc_tokens)
        query_vec = _tfidf_vector(query_tokens, idf)
        scored = []
        for mid, mem in memories.items():
            doc_tokens = mem.get("tokens", _tokenize(mem.get("content", "")))
            doc_vec = _tfidf_vector(doc_tokens, idf)
            tfidf_score = _cosine_sim(query_vec, doc_vec)
            kw_score = _keyword_overlap_score(query_tokens, doc_tokens)
            combined = tfidf_score * 0.6 + kw_score * 0.4
            importance_boost = mem.get("importance", 0.5) * 0.15
            final_score = combined + importance_boost
            scored.append((final_score, mid, mem))
        scored.sort(key=lambda x: -x[0])
        results = scored[:limit]
        if not results:
            return "No relevant memories found."
        lines = []
        for score, mid, mem in results:
            lines.append(
                f"[{mid}] (score: {score:.3f}, imp: {mem.get('importance', 0):.2f}) "
                f"{mem['content'][:120]} | tags: {mem.get('tags', [])}"
            )
        return f"Search results ({len(results)} matches for '{query}'):\n" + "\n".join(lines)

    elif action == "recall":
        limit = int(parameters.get("limit", 10))
        sort_by = parameters.get("sort", "recent")
        if not memories:
            return "No memories stored."
        mem_list = list(memories.values())
        if sort_by == "recent":
            mem_list.sort(key=lambda m: m.get("timestamp", ""), reverse=True)
        elif sort_by == "important":
            mem_list.sort(key=lambda m: m.get("importance", 0), reverse=True)
        elif sort_by == "accessed":
            mem_list.sort(key=lambda m: m.get("access_count", 0), reverse=True)
        recent = mem_list[:limit]
        lines = []
        for mem in recent:
            lines.append(
                f"[{mem['id']}] {mem['content'][:120]} | "
                f"tags: {mem.get('tags', [])} | imp: {mem.get('importance', 0):.2f} | "
                f"accessed: {mem.get('access_count', 0)}x | {mem.get('timestamp', '')}"
            )
        return f"Recent memories ({len(recent)} of {len(memories)}):\n" + "\n".join(lines)

    elif action == "forget":
        memory_id = parameters.get("memory_id", "")
        query = parameters.get("query", "")
        if memory_id:
            if memory_id in memories:
                content = memories[memory_id]["content"][:80]
                del memories[memory_id]
                data["memories"] = memories
                _save_memory(data)
                return f"Memory '{memory_id}' forgotten: {content}"
            return f"Memory '{memory_id}' not found."
        if query:
            query_tokens = _tokenize(query)
            to_delete = []
            for mid, mem in memories.items():
                doc_tokens = mem.get("tokens", _tokenize(mem.get("content", "")))
                if _keyword_overlap_score(query_tokens, doc_tokens) > 0.3:
                    to_delete.append(mid)
            if not to_delete:
                return "No matching memories to forget."
            for mid in to_delete:
                del memories[mid]
            data["memories"] = memories
            _save_memory(data)
            return f"Forgot {len(to_delete)} memories matching '{query}'."
        return "Provide 'memory_id' or 'query' to forget."

    elif action == "stats":
        if not memories:
            return "No memories stored."
        total = len(memories)
        all_tags: Counter = Counter()
        importances = []
        total_access = 0
        for mem in memories.values():
            for tag in mem.get("tags", []):
                all_tags[tag] += 1
            importances.append(mem.get("importance", 0))
            total_access += mem.get("access_count", 0)
        avg_importance = sum(importances) / len(importances) if importances else 0
        top_tags = all_tags.most_common(10)
        oldest = min(m.get("timestamp", "") for m in memories.values())
        newest = max(m.get("timestamp", "") for m in memories.values())
        total_tokens = sum(len(m.get("tokens", [])) for m in memories.values())
        lines = [
            f"Total memories: {total}",
            f"Total tokens: {total_tokens}",
            f"Avg importance: {avg_importance:.3f}",
            f"Total accesses: {total_access}",
            f"Oldest: {oldest}",
            f"Newest: {newest}",
            f"Top tags: {', '.join(f'{t}({c})' for t, c in top_tags)}" if top_tags else "Top tags: none",
        ]
        return "\n".join(lines)

    else:
        return f"Unknown action: '{action}'. Valid: store, search, recall, forget, stats"
