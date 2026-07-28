"""
rag_pipeline.py — ERIS RAG (Retrieval-Augmented Generation) pipeline.

Uses ChromaDB for vector storage and Ollama for embeddings.
Supports indexing PDF, DOCX, TXT, MD files and querying them semantically.
"""
from __future__ import annotations

import json
import hashlib
import shutil
from pathlib import Path
from typing import Optional

_BASE = Path(__file__).resolve().parent.parent
_CHROMA_DIR = _BASE / "data" / "chroma_db"
_INDEX_LOG = _BASE / "data" / "rag_index.json"

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}

# Lazy imports — ChromaDB may not be installed
_chromadb = None


def _ensure_chromadb():
    global _chromadb
    if _chromadb is None:
        try:
            import chromadb
            _chromadb = chromadb
        except ImportError:
            raise RuntimeError(
                "ChromaDB no está instalado. Ejecutá: pip install chromadb"
            )


# ── Embeddings ────────────────────────────────────────────────────────────────

def _get_embedding(text: str) -> list[float]:
    """Get embedding vector from Ollama or fallback to hash-based."""
    try:
        import httpx
        cfg_path = _BASE / "config" / "api_keys.json"
        cfg = json.loads(cfg_path.read_text()) if cfg_path.exists() else {}
        base_url = cfg.get("ollama_base_url", "http://localhost:11434")
        model = cfg.get("ollama_embed_model", "nomic-embed-text")
        with httpx.Client(timeout=30) as client:
            resp = client.post(
                f"{base_url}/api/embeddings",
                json={"model": model, "prompt": text[:8192]},
            )
            resp.raise_for_status()
            return resp.json()["embedding"]
    except Exception:
        # Deterministic hash-based fallback
        import numpy as np
        h = hashlib.sha256(text.encode()).digest()
        seed = int.from_bytes(h[:4], "big")  # 32-bit seed
        rng = np.random.RandomState(seed)
        return rng.randn(384).tolist()


# ── Document Parsing ──────────────────────────────────────────────────────────

def _parse_file(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".txt":
        return path.read_text(encoding="utf-8", errors="replace")
    if ext == ".md":
        return path.read_text(encoding="utf-8", errors="replace")
    if ext == ".pdf":
        return _parse_pdf(path)
    if ext == ".docx":
        return _parse_docx(path)
    return ""


def _parse_pdf(path: Path) -> str:
    try:
        import pymupdf
        doc = pymupdf.open(str(path))
        return "\n".join(page.get_text() for page in doc)
    except ImportError:
        try:
            # Fallback to pypdf
            from pypdf import PdfReader
            reader = PdfReader(str(path))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except ImportError:
            return f"[PDF parsing requires pymupdf or pypdf: {path.name}]"
    except Exception as e:
        return f"[Error parsing PDF {path.name}: {e}]"


def _parse_docx(path: Path) -> str:
    try:
        from docx import Document
        doc = Document(str(path))
        return "\n".join(p.text for p in doc.paragraphs)
    except ImportError:
        return f"[DOCX parsing requires python-docx: {path.name}]"
    except Exception as e:
        return f"[Error parsing DOCX {path.name}: {e}]"


def _chunk_text(text: str, max_chars: int = 1000, overlap: int = 200) -> list[str]:
    """Split text into overlapping chunks."""
    if not text.strip():
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        # Try to break at a sentence or paragraph boundary
        if end < len(text):
            # Look for paragraph break
            para = text.rfind("\n\n", start, end)
            if para > start + max_chars // 2:
                end = para + 2
            else:
                # Look for sentence end
                for sep in (". ", "! ", "? ", "\n"):
                    idx = text.rfind(sep, start, end)
                    if idx > start + max_chars // 2:
                        end = idx + len(sep)
                        break
        chunks.append(text[start:end].strip())
        start = end - overlap if end < len(text) else len(text)
    return [c for c in chunks if len(c) > 20]


# ── Index Management ──────────────────────────────────────────────────────────

def _load_index_log() -> dict:
    if _INDEX_LOG.exists():
        try:
            return json.loads(_INDEX_LOG.read_text())
        except Exception:
            return {}
    return {}


def _save_index_log(log: dict):
    _INDEX_LOG.parent.mkdir(parents=True, exist_ok=True)
    _INDEX_LOG.write_text(json.dumps(log, indent=2))


def _get_collection():
    """Get or create ChromaDB collection."""
    _ensure_chromadb()
    _CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = _chromadb.PersistentClient(path=str(_CHROMA_DIR))
    return client.get_or_create_collection(
        name="eris_documents",
        metadata={"hnsw:space": "cosine"},
    )


def _doc_id(path: Path) -> str:
    return f"doc_{hashlib.sha256(str(path.resolve()).encode()).hexdigest()[:16]}"


# ── Public API ────────────────────────────────────────────────────────────────

def index_document(path: str | Path) -> str:
    """
    Index a document (PDF, DOCX, TXT, MD) into ChromaDB.
    Returns a status message.
    """
    path = Path(path).expanduser().resolve()
    if not path.exists():
        return f"Archivo no encontrado: {path}"
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        exts = ", ".join(SUPPORTED_EXTENSIONS)
        return f"Formato no soportado. Usar: {exts}"

    try:
        text = _parse_file(path)
        if not text.strip():
            return f"No se pudo extraer texto de {path.name}"
    except Exception as e:
        return f"Error al leer {path.name}: {e}"

    chunks = _chunk_text(text)
    if not chunks:
        return f"El documento {path.name} no tiene contenido suficiente."

    doc_id = _doc_id(path)
    ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
    metadatas = [
        {"source": str(path), "filename": path.name, "chunk": i, "total_chunks": len(chunks)}
        for i in range(len(chunks))
    ]
    embeddings = [_get_embedding(ch) for ch in chunks]

    collection = _get_collection()

    # Remove old chunks for same doc if re-indexing
    try:
        collection.delete(where={"source": str(path)})
    except Exception:
        pass

    # Add in batches of 100
    batch_size = 100
    for i in range(0, len(chunks), batch_size):
        end = i + batch_size
        collection.add(
            ids=ids[i:end],
            documents=chunks[i:end],
            metadatas=metadatas[i:end],
            embeddings=embeddings[i:end],
        )

    # Update index log
    log = _load_index_log()
    log[str(path)] = {
        "filename": path.name,
        "chunks": len(chunks),
        "size_bytes": path.stat().st_size,
    }
    _save_index_log(log)

    return f"Indexado: {path.name} ({len(chunks)} fragmentos, {path.stat().st_size:,} bytes)"


def query_documents(query: str, top_k: int = 5) -> list[dict]:
    """
    Search indexed documents by semantic similarity.
    Returns list of {text, source, filename, chunk, score}.
    """
    if not query.strip():
        return []
    try:
        collection = _get_collection()
        count = collection.count()
        if count == 0:
            return []
    except Exception:
        return []

    query_emb = _get_embedding(query)
    try:
        results = collection.query(
            query_embeddings=[query_emb],
            n_results=min(top_k, collection.count()),
        )
    except Exception:
        return []

    hits = []
    if results and results.get("ids") and results["ids"][0]:
        for i in range(len(results["ids"][0])):
            hits.append({
                "text": results["documents"][0][i] if results.get("documents") else "",
                "source": results["metadatas"][0][i].get("source", "") if results.get("metadatas") else "",
                "filename": results["metadatas"][0][i].get("filename", "") if results.get("metadatas") else "",
                "chunk": results["metadatas"][0][i].get("chunk", 0) if results.get("metadatas") else 0,
                "score": float(results["distances"][0][i]) if results.get("distances") else 0.0,
            })
    return hits


def list_indexed() -> list[dict]:
    """List all indexed documents with metadata."""
    log = _load_index_log()
    return [
        {"path": p, "filename": info["filename"], "chunks": info["chunks"], "size_bytes": info["size_bytes"]}
        for p, info in log.items()
    ]


def delete_index(path: str | Path) -> str:
    """Remove a document from the index."""
    path = str(Path(path).expanduser().resolve())
    try:
        collection = _get_collection()
        collection.delete(where={"source": path})
    except Exception:
        pass

    log = _load_index_log()
    if path in log:
        del log[path]
        _save_index_log(log)
        return f"Eliminado del índice: {Path(path).name}"
    return f"Ese documento no estaba indexado."


def clear_all() -> str:
    """Delete the entire document index."""
    try:
        _ensure_chromadb()
        _CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        client = _chromadb.PersistentClient(path=str(_CHROMA_DIR))
        try:
            client.delete_collection("eris_documents")
        except Exception:
            pass
    except Exception:
        pass

    if _INDEX_LOG.exists():
        _INDEX_LOG.unlink()
    return "Índice de documentos eliminado por completo."


def stats() -> dict:
    """Get index statistics."""
    log = _load_index_log()
    total_chunks = sum(v["chunks"] for v in log.values())
    try:
        collection = _get_collection()
        chroma_count = collection.count()
    except Exception:
        chroma_count = 0
    return {
        "documents": len(log),
        "chunks": total_chunks,
        "chroma_entries": chroma_count,
    }
