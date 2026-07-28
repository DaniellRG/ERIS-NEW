# -*- coding: utf-8 -*-
"""core/llm_bridge.py — Real embedding generation via Ollama.

Provides get_embedding() and get_embeddings_batch() used by:
- core/rag_pipeline.py
- core/semantic_memory.py
- actions/knowledge_base.py
"""
import json
import urllib.request
import urllib.error
import hashlib
import time
from typing import List, Optional

OLLAMA_BASE = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text"
EMBED_DIM = 768
_request_timeout = 30


def _check_ollama() -> bool:
    try:
        urllib.request.urlopen(f"{OLLAMA_BASE}/api/tags", timeout=3)
        return True
    except Exception:
        return False


_ollama_available: Optional[bool] = None


def _is_available() -> bool:
    global _ollama_available
    if _ollama_available is None:
        _ollama_available = _check_ollama()
    return _ollama_available


def get_embedding(text: str) -> List[float]:
    """Get embedding vector for a single text string.

    Uses Ollama nomic-embed-text (768-dim). Falls back to deterministic
    hash-based pseudo-embedding if Ollama is unreachable.
    """
    if _is_available():
        try:
            return _ollama_embed(text)
        except Exception:
            pass
    return _hash_embed(text)


def get_embeddings_batch(texts: List[str], batch_size: int = 32) -> List[List[float]]:
    """Get embeddings for a list of texts. Batches for efficiency."""
    if _is_available():
        try:
            return [_ollama_embed(t) for t in texts]
        except Exception:
            pass
    return [_hash_embed(t) for t in texts]


def _ollama_embed(text: str) -> List[float]:
    body = json.dumps({"model": EMBED_MODEL, "prompt": text}).encode()
    req = urllib.request.Request(
        f"{OLLAMA_BASE}/api/embeddings",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    resp = urllib.request.urlopen(req, timeout=_request_timeout)
    data = json.loads(resp.read())
    vec = data.get("embedding", [])
    if len(vec) != EMBED_DIM:
        raise ValueError(f"Expected {EMBED_DIM}-dim, got {len(vec)}")
    return vec


def _hash_embed(text: str) -> List[float]:
    """Deterministic pseudo-embedding from SHA-256 hash. NOT semantically meaningful."""
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()
    vec = []
    for i in range(0, EMBED_DIM * 2, 2):
        chunk = h[i % len(h): (i % len(h)) + 8]
        val = (int(chunk, 16) / 0xFFFFFFFF) * 2 - 1
        vec.append(val)
    norm = sum(v * v for v in vec) ** 0.5
    if norm > 0:
        vec = [v / norm for v in vec]
    return vec


def embedding_info() -> dict:
    """Return info about the current embedding setup."""
    available = _is_available()
    return {
        "provider": "ollama" if available else "hash_fallback",
        "model": EMBED_MODEL if available else "sha256_pseudo",
        "dimension": EMBED_DIM,
        "ollama_url": OLLAMA_BASE,
        "status": "real embeddings" if available else "DEGRADED: pseudo-embeddings only",
    }
