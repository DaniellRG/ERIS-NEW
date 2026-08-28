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

_EPISODIC_FILE = _BASE / "memory" / "episodic.json"
_EPISODIC_INDEX_PREFIX = "episodic_chunk"

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
    """Get embedding vector via core.llm_bridge (Ollama nomic-embed-text, 768-dim)."""
    try:
        from core.llm_bridge import get_embedding
        return get_embedding(text[:8192])
    except ImportError:
        pass
    # Ultimate fallback: hash-based
    import numpy as np
    h = hashlib.sha256(text.encode()).digest()
    seed = int.from_bytes(h[:4], "big")
    rng = np.random.RandomState(seed)
    return rng.randn(768).tolist()


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

def index_vault(vault_path: str | Path | None = None, folders: str = "wiki,outputs,raw") -> str:
    """
    Indexa las notas Markdown del vault de Obsidian (obsidian_note) en ChromaDB.
    Cada nota se guarda como un fragmento con fuente 'vault://<ruta-relativa>'.
    folders: lista separada por coma de carpetas a indexar (raw, wiki, outputs,
    y vacio = raiz). Default 'wiki,outputs,raw'. Usá folders='' (vacío) para
    indexar también la raíz (daily notes).
    """
    import datetime as _dt

    vault = Path(vault_path or (_BASE / "vault")).expanduser().resolve()
    if not vault.exists():
        return f"Vault no encontrado: {vault}"

    wanted = [f.strip().strip("/") for f in folders.split(",") if f.strip()]

    def _iter_files():
        if not wanted:
            yield from sorted(vault.rglob("*.md"))
            return
        if "" in wanted:
            yield from sorted(vault.glob("*.md"))
        for folder in wanted:
            if not folder:
                continue
            d = vault / folder
            if d.exists():
                yield from sorted(d.glob("*.md"))

    notes = sorted({p.resolve() for p in _iter_files()})
    if not notes:
        return f"No hay notas .md en el vault ({vault})."

    collection = _get_collection()
    indexed = 0
    for path in notes:
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        # Saltar archivos de convenciones
        if path.stem in ("CLAUDE", "AGENTS", "_INDEX"):
            continue
        if not text.strip():
            continue
        rel = path.relative_to(vault).as_posix()
        source = f"vault://{rel}"
        title = path.stem
        body = text
        # Extraer frontmatter y body
        if body.startswith("---"):
            end = body.find("---", 3)
            if end > 0:
                body = body[end + 3:].lstrip("\n")
        body = body.strip()
        if not body:
            body = f"# {title}"
        chunks = _chunk_text(body)
        if not chunks:
            chunks = [body[:1000]]
        # Remover chunks previos de esta nota
        try:
            collection.delete(where={"source": source})
        except Exception:
            pass
        nid = hashlib.sha256(rel.encode()).hexdigest()[:16]
        ids = [f"vault_{nid}_chunk_{i}" for i in range(len(chunks))]
        metadatas = [{"source": source, "filename": rel, "title": title,
                      "chunk": i, "kind": "vault"} for i in range(len(chunks))]
        embeddings = [_get_embedding(c) for c in chunks]
        collection.add(ids=ids, documents=chunks, metadatas=metadatas, embeddings=embeddings)
        indexed += 1

    return f"Vault indexado: {indexed} notas de {len(notes)} en RAG (fuente vault://)."


def query_vault(query: str, top_k: int = 5) -> list[dict]:
    """
    Busqueda semantica restringida a notas del vault (fuente vault://).
    """
    hits = query_documents(query, top_k=top_k * 3)
    return [h for h in hits if h.get("source", "").startswith("vault://")][:top_k]


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


def index_episodic(max_entries: int = 0) -> str:
    """
    Indexa la memoria episodica (memory/episodic.json) en ChromaDB.
    Cada episodio se guarda como un fragmento con fuente 'episodic://<id>'.
    max_entries > 0 limita a los N episodios mas recientes.
    """
    import datetime as _dt

    if not _EPISODIC_FILE.exists():
        return "No hay archivo de memoria episodica (memory/episodic.json)."

    try:
        entries = json.loads(_EPISODIC_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        return f"Error leyendo memoria episodica: {e}"
    if not isinstance(entries, list) or not entries:
        return "Memoria episodica vacia."

    def _when(e):
        try:
            return e.get("datetime") or e.get("timestamp") or ""
        except Exception:
            return ""
    entries.sort(key=_when, reverse=True)
    if max_entries and len(entries) > max_entries:
        entries = entries[:max_entries]

    collection = _get_collection()
    new_chunks = 0
    existing = set()
    try:
        # ids ya indexados de episodicos (prefix) para evitar duplicar
        res = collection.get(ids=[], include=[])
        all_ids = res.get("ids", []) if res else []
        existing = {i for i in all_ids if i.startswith(_EPISODIC_INDEX_PREFIX + "_")}
    except Exception:
        pass

    batch_ids, batch_docs, batch_meta, batch_emb = [], [], [], []
    for e in entries:
        eid = str(e.get("id", ""))
        event = str(e.get("event", "")).strip()
        if not event:
            continue
        doc_id = f"{_EPISODIC_INDEX_PREFIX}_{eid}"
        if doc_id in existing:
            continue
        context = str(e.get("context", ""))[:100]
        importance = float(e.get("importance", 0.5))
        when = str(e.get("datetime") or "")[:19]
        text = f"[Episodio {when} | contexto: {context}]\n{event}"
        batch_ids.append(doc_id)
        batch_docs.append(text)
        batch_meta.append({"source": f"episodic://{eid}", "filename": "episodic.json",
                           "context": context, "importance": importance,
                           "when": when, "kind": "episodic"})
        batch_emb.append(_get_embedding(event[:2000]))
        new_chunks += 1
        if len(batch_ids) >= 100:
            collection.add(ids=batch_ids, documents=batch_docs,
                           metadatas=batch_meta, embeddings=batch_emb)
            batch_ids, batch_docs, batch_meta, batch_emb = [], [], [], []
    if batch_ids:
        collection.add(ids=batch_ids, documents=batch_docs,
                       metadatas=batch_meta, embeddings=batch_emb)

    total = len(entries)
    return f"Memoria episodica indexada: {new_chunks} nuevos de {total} episodios"


def compact_episodic(older_than_days: int = 30, keep_contexts: bool = True) -> str:
    """
    Compresion de memoria episodica: agrupa episodios antiguos (> N dias) y los
    condensa en resumenes diarios/semanales consolidados que se guardan en
    memory/compacted_episodic.json y se indexan en RAG.
    """
    import datetime as _dt
    from collections import defaultdict

    if not _EPISODIC_FILE.exists():
        return "No hay memoria episodica."
    try:
        entries = json.loads(_EPISODIC_FILE.read_text(encoding="utf-8"))
    except Exception:
        return "Error leyendo memoria episodica."

    cutoff = _dt.datetime.now() - _dt.timedelta(days=older_than_days)
    old, fresh = [], []
    for e in entries:
        try:
            when = _dt.datetime.fromisoformat(str(e.get("datetime", "")))
        except Exception:
            try:
                when = _dt.datetime.fromtimestamp(float(e.get("timestamp", 0)))
            except Exception:
                fresh.append(e)
                continue
        (old if when < cutoff else fresh).append(e)

    if not old:
        return f"No hay episodios mayores a {older_than_days} dias para comprimir."

    # Agrupar por dia
    by_day = defaultdict(list)
    for e in old:
        try:
            day = str(e.get("datetime", ""))[:10]
        except Exception:
            day = "desconocido"
        by_day[day].append(e)

    _COMPACT_DIR = _BASE / "memory"
    compact_file = _COMPACT_DIR / "compacted_episodic.json"
    existing = {}
    if compact_file.exists():
        try:
            existing = json.loads(compact_file.read_text(encoding="utf-8"))
        except Exception:
            existing = {}

    summary_ids = []
    for day in sorted(by_day):
        day_entries = by_day[day]
        texts = [str(e.get("event", "")).strip() for e in day_entries if str(e.get("event", "")).strip()]
        # Consolidar: unir con tope de chars para no explotar
        combined = " ".join(texts)
        combined = combined[:2500]
        if not combined:
            continue
        summary_id = f"compact_{day}"
        existing[summary_id] = {
            "summary": combined,
            "day": day,
            "entries": len(day_entries),
            "compacted_at": _dt.datetime.now().isoformat(),
        }
        summary_ids.append((summary_id, combined, day))

    compact_file.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")

    # Indexar resumenes en RAG
    indexed = 0
    try:
        collection = _get_collection()
        for sid, text, day in summary_ids:
            doc_id = f"episodic_compact_{sid}"
            meta = {"source": f"episodic_compact://{sid}", "filename": "compacted_episodic.json",
                    "when": day, "kind": "episodic_compact"}
            try:
                collection.delete(where={"source": f"episodic_compact://{sid}"})
            except Exception:
                pass
            collection.add(ids=[doc_id], documents=[f"[Resumen episodico {day}]\n{text}"],
                           metadatas=[meta], embeddings=[_get_embedding(text[:2000])])
            indexed += 1
    except Exception:
        pass

    return (f"Memoria episodica comprimida: {len(summary_ids)} resumenes diarios de "
            f"{len(old)} episodios antiguos ({older_than_days}+ dias). "
            f"Indexados en RAG: {indexed}. Guardado en memory/compacted_episodic.json")


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


class RAGPipeline:
    """Object-oriented wrapper around the rag_pipeline module API."""

    def __init__(self, base_path=None):
        self.base_path = str(base_path or _BASE)

    def index(self, path: str | Path) -> str:
        return index_document(path)

    def query(self, query: str, top_k: int = 5) -> list[dict]:
        return query_documents(query, top_k=top_k)

    def list_indexed(self) -> list[dict]:
        return list_indexed()

    def delete(self, path: str | Path) -> str:
        return delete_index(path)

    def clear(self) -> str:
        return clear_all()

    def stats(self) -> dict:
        return stats()


rag = RAGPipeline()
