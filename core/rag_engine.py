# -*- coding: utf-8 -*-
"""
rag_engine.py — RAG (Retrieval-Augmented Generation) de MEMORIA TOTAL de ERIS.
Indexa TODAS sus fuentes de conocimiento en un solo índice semántico:

  vault        — Obsidian real (via get_obsidian_vault)
  memoria      — memory/*.json (identidad, emociones, relaciones, estado)
  conocimiento — data/knowledge/*.md
  wiki         — vault/wiki/*.md (memoria destilada)
  episodica    — memory/compacted_episodic.json + data/episodic*.jsonl

Acciones:
  index   — Indexar/re-indexar todas las fuentes
  search  — Buscar por significado (query)
  recall  — Para inyección automática: top-K recuerdos relevantes cortos
  status  — Estado del índice
  stats   — Estadísticas por fuente
"""
from __future__ import annotations

import json
import os
import re
import time
import hashlib
import threading
from pathlib import Path
from typing import Any, Optional

_BASE = Path(__file__).resolve().parent.parent
_INDEX_DIR = _BASE / "data"
_EMBED_FILE = _INDEX_DIR / "rag_embeddings.npz"
_META_FILE = _INDEX_DIR / "rag_meta.json"

_model = None
_model_name = "all-MiniLM-L6-v2"
_load_lock = threading.Lock()


def _get_vault_path() -> Path:
    """Resuelve el vault de Obsidian real (env o get_obsidian_vault)."""
    env = os.environ.get("ERIS_OBSIDIAN_VAULT")
    if env:
        return Path(env)
    try:
        from core.logging_setup import get_obsidian_vault
        vault = get_obsidian_vault()
        if vault and Path(vault).exists():
            return Path(vault)
    except Exception:
        pass
    return _BASE / "obsidian_vault"


_VAULT_PATH = _get_vault_path()


def _get_model():
    global _model
    if _model is None:
        with _load_lock:
            if _model is None:
                try:
                    from sentence_transformers import SentenceTransformer
                    _model = SentenceTransformer(_model_name)
                except Exception:
                    return None
    return _model


def _clean_text(text: str, limit: int = 600) -> str:
    text = re.sub(r"^---.*?---", "", text, flags=re.DOTALL)
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    text = re.sub(r"[#*_~>`\-|]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def _add_source(notes: list[dict], name: str, content: str, path: str, source: str):
    chunk = _clean_text(content)
    if len(chunk) < 40:
        return
    notes.append({
        "name": name,
        "path": path,
        "chunk": chunk,
        "source": source,
        "hash": hashlib.md5(chunk.encode()).hexdigest(),
    })


def _collect_notes(cap_per_source: int = 2500) -> list[dict]:
    """Recolecta notas de todas las fuentes de conocimiento de ERIS."""
    notes = []
    seen_ids = set()

    def _dedup(note):
        key = note["source"] + "::" + note["path"]
        if key in seen_ids:
            return False
        seen_ids.add(key)
        return True

    # 1. Vault de Obsidian
    if _VAULT_PATH.exists():
        count = 0
        for md in sorted(_VAULT_PATH.rglob("*.md")):
            if "_INDEX.md" in str(md) or ".obsidian" in str(md) or "TRASH" in str(md).upper():
                continue
            try:
                rel = str(md.relative_to(_VAULT_PATH)).replace("\\", "/")
            except Exception:
                rel = md.name
            _add_source(notes, md.stem, _read(md), "vault/" + rel, "vault")
            count += 1
            if count >= cap_per_source:
                break
        print(f"[RAG] vault: {count} notas")

    # 2. memory/*.json — el estado vivo (identidad, emociones, relaciones)
    count = 0
    for jf in sorted((_BASE / "memory").glob("*.json")):
        if jf.stat().st_size > 300_000:
            continue
        content = _read(jf)
        try:
            data = json.loads(content)
            if isinstance(data, list):
                text = json.dumps(data[:50], ensure_ascii=False)[:6000]
            elif isinstance(data, dict):
                text = json.dumps(data, ensure_ascii=False)[:6000]
            else:
                text = str(data)
        except Exception:
            text = content[:6000]
        _add_source(notes, jf.stem, text, "memory/" + jf.name, "memoria")
        count += 1
        if count >= cap_per_source:
            break
    print(f"[RAG] memoria: {count} archivos")

    # 3. data/knowledge/*.md
    count = 0
    for md in sorted((_BASE / "data" / "knowledge").glob("*.md")):
        _add_source(notes, md.stem, _read(md), "cono/" + md.name, "conocimiento")
        count += 1
    print(f"[RAG] conocimiento: {count} notas")

    # 4. vault/wiki/*.md (memoria destilada) — si el vault repo local existe
    repo_wiki = _BASE / "vault" / "wiki"
    if repo_wiki.exists():
        count = 0
        for md in sorted(repo_wiki.rglob("*.md")):
            _add_source(notes, md.stem, _read(md), "wiki/" + md.name, "conocimiento")
            count += 1
        print(f"[RAG] wiki repo: {count} notas")

    # 5. Episódicas consolidadas
    for cand, tag in [
        (_BASE / "memory" / "compacted_episodic.json", "episodica"),
        (_BASE / "data" / "episodic.json", "episodica"),
    ]:
        if cand.exists():
            try:
                eps = json.loads(_read(cand))
                limit_eps = 400 if isinstance(eps, list) else 100
                chunk = json.dumps(eps[:limit_eps], ensure_ascii=False)[:8000] if isinstance(eps, list) else _read(cand)[:8000]
                _add_source(notes, cand.stem, chunk, cand.name, tag)
            except Exception:
                pass

    notes = [n for n in notes if _dedup(n)]
    return notes


def _save_index(embeddings, notes):
    _INDEX_DIR.mkdir(parents=True, exist_ok=True)
    import numpy as np
    np.savez_compressed(str(_EMBED_FILE), embeddings=embeddings)
    _META_FILE.write_text(json.dumps(notes, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_index():
    import numpy as np
    if not _EMBED_FILE.exists() or not _META_FILE.exists():
        return None, []
    try:
        embeddings = np.load(str(_EMBED_FILE))["embeddings"]
        notes = json.loads(_META_FILE.read_text(encoding="utf-8"))
        return embeddings, notes
    except Exception:
        return None, []


def _cosine_search(query_emb, note_embs, top_k=5):
    import numpy as np
    if note_embs is None or len(note_embs) == 0:
        return []
    query_norm = query_emb / (np.linalg.norm(query_emb) + 1e-10)
    norms = np.linalg.norm(note_embs, axis=1, keepdims=True) + 1e-10
    note_norms = note_embs / norms
    scores = note_norms @ query_norm
    top_idx = np.argsort(scores)[::-1][:top_k]
    return [(int(i), float(scores[i])) for i in top_idx]


def index_todo() -> str:
    """Indexa todas las fuentes. Retorna resumen. (También se usa desde daemon.)"""
    model = _get_model()
    if model is None:
        return "No pude cargar sentence-transformers."
    notes = _collect_notes()
    if not notes:
        return "No encontré notas en ninguna fuente."
    chunks = [n["chunk"] for n in notes]
    embeddings = model.encode(chunks, show_progress_bar=False, batch_size=64)
    _save_index(embeddings, notes)
    by_src = {}
    for n in notes:
        by_src[n["source"]] = by_src.get(n["source"], 0) + 1
    parts = ", ".join(f"{s}={c}" for s, c in sorted(by_src.items()))
    return f"✅ Índice de MEMORIA TOTAL: {len(notes)} notas ({parts}). dim={embeddings.shape[1]}"


def recall(query: str, top_k: int = 3) -> Optional[list[dict]]:
    """Busca recuerdos relevantes SIN formatear (para inyección automática).
    Devuelve lista de dicts {name, path, source, score, chunk} o None si no hay índice."""
    query = (query or "").strip()
    if not query:
        return None
    model = _get_model()
    if model is None:
        return None
    embeddings, notes = _load_index()
    if notes is None or len(notes) == 0:
        return None
    try:
        q_emb = model.encode([query])[0]
    except Exception:
        return None
    results = _cosine_search(q_emb, embeddings, top_k)
    out = []
    for idx, score in results:
        n = notes[idx]
        out.append({"name": n["name"], "path": n["path"], "source": n.get("source", ""),
                    "score": round(score, 3), "chunk": n["chunk"][:300]})
    return out if out and out[0]["score"] > 0.25 else None


def recall_texto(query: str, top_k: int = 3) -> str:
    """Recuerdos formateados para inyectar como [RECUERDOS RELEVANTES]."""
    found = recall(query, top_k)
    if not found:
        return ""
    lines = ["[RECUERDOS RELEVANTES] (búsqueda semántica en mi memoria total):"]
    for r in found:
        src = {"vault": "vault", "memoria": "estado interno", "conocimiento": "conocimiento",
               "episodica": "memoria episódica"}.get(r["source"], r["source"])
        lines.append(f"• [{src}] {r['name']} (sim {r['score']}): {r['chunk'][:150]}")
    return "\n".join(lines)


def rag_engine(parameters: dict = None, player=None) -> str:
    """Tool: Búsqueda semántica (RAG) sobre la memoria total de ERIS."""
    params = parameters or {}
    action = str(params.get("action", "search")).lower().strip()

    if action == "status":
        has_index = _EMBED_FILE.exists() and _META_FILE.exists()
        count = 0
        if has_index:
            try:
                _, notes = _load_index()
                count = len(notes)
            except Exception:
                pass
        vault = str(_VAULT_PATH)
        return (f"RAG: {'índice activo' if has_index else 'sin índice'} ({count} notas). "
                f"Modelo: {_model_name}. Vault: {vault}")

    if action == "stats":
        embeddings, notes = _load_index()
        if notes is None or len(notes) == 0:
            return "Sin índice. Usá 'index' para crearlo."
        folders = {}
        for n in notes:
            src = n.get("source", "root")
            folders[src] = folders.get(src, 0) + 1
        top_folders = sorted(folders.items(), key=lambda x: -x[1])
        lines = [f"**RAG Stats:** {len(notes)} notas indexadas\n"]
        for f, c in top_folders:
            lines.append(f"  📁 {f}: {c} notas")
        avg_chunk = sum(len(n["chunk"]) for n in notes) // max(len(notes), 1)
        lines.append(f"\n  Promedio chars/nota: {avg_chunk}")
        return "\n".join(lines)

    if action == "index":
        return index_todo()

    if action in ("recall", "recuerdos"):
        query = str(params.get("query", "")).strip()
        if not query:
            return "Necesito una consulta: qué querés recordar."
        return recall_texto(query, int(params.get("top_k", 3))) or "Sin recuerdos relevantes (o sin índice)."

    if action == "search":
        query = str(params.get("query", "")).strip()
        top_k = min(int(params.get("top_k", 5)), 15)
        if not query:
            return "Necesito una consulta. Ej: 'cómo funciona el sistema digestivo'"
        model = _get_model()
        if model is None:
            return "sentence-transformers no disponible."
        embeddings, notes = _load_index()
        if notes is None or len(notes) == 0:
            return "Sin índice. Usá 'index' para crearlo."
        try:
            q_emb = model.encode([query])[0]
        except Exception as e:
            return f"Error en embedding: {e}"
        results = _cosine_search(q_emb, embeddings, top_k)
        lines = [f"**Resultados semánticos: {query}**\n"]
        for idx, score in results:
            n = notes[idx]
            lines.append(f"**{n['name']}** ({n.get('source','?')}, sim: {score:.3f})")
            lines.append(f"  📄 {n['path']}")
            lines.append(f"  {n['chunk'][:200]}...\n")
        return "\n".join(lines)

    return "Acciones disponibles: index, search, recall, status, stats"


def _background_index_once():
    """Index inicial en background al arrancar (si no hay índice)."""
    try:
        embeddings, notes = _load_index()
        if notes is None or len(notes) == 0:
            print("[RAG] Sin índice — construyendo memoria total en background…")
            res = index_todo()
            print(f"[RAG] {res}")
        else:
            print(f"[RAG] Índice listo: {len(notes)} notas")
    except Exception as e:
        print(f"[RAG] background index falló: {e}")