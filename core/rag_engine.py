# -*- coding: utf-8 -*-
"""
rag_engine.py — RAG (Retrieval-Augmented Generation) sobre el vault de Obsidian.
Usa sentence-transformers para embeddings y cosine similarity para búsqueda semántica.
Acciones:
  index   — Indexar/re-indexar el vault
  search  — Buscar por significado (no solo por nombre)
  status  — Estado del índice
  stats   — Estadísticas del índice
"""
from __future__ import annotations

import json
import os
import re
import time
import hashlib
from pathlib import Path
from typing import Any

_BASE = Path(__file__).resolve().parent.parent
_INDEX_DIR = _BASE / "data"
_VAULT_PATH = Path(os.environ.get("ERIS_OBSIDIAN_VAULT",
                                  str(_BASE / "obsidian_vault")))
_EMBED_FILE = _INDEX_DIR / "rag_embeddings.npz"
_META_FILE = _INDEX_DIR / "rag_meta.json"

_model = None
_model_name = "all-MiniLM-L6-v2"


def _get_model():
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer(_model_name)
        except Exception:
            return None
    return _model


def _clean_text(text: str, limit: int = 500) -> str:
    text = re.sub(r"^---.*?---", "", text, flags=re.DOTALL)
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    text = re.sub(r"[#*_~>`\-|]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def _collect_notes() -> list[dict]:
    notes = []
    if not _VAULT_PATH.exists():
        return notes
    for md in _VAULT_PATH.rglob("*.md"):
        if "_INDEX.md" in str(md) or ".obsidian" in str(md):
            continue
        try:
            content = md.read_text(encoding="utf-8", errors="replace")
            name = md.stem
            rel = str(md.relative_to(_VAULT_PATH)).replace("\\", "/")
            chunk = _clean_text(content)
            if len(chunk) < 20:
                continue
            notes.append({"name": name, "path": rel, "chunk": chunk, "hash": hashlib.md5(chunk.encode()).hexdigest()})
        except Exception:
            continue
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
    embeddings = np.load(str(_EMBED_FILE))["embeddings"]
    notes = json.loads(_META_FILE.read_text(encoding="utf-8"))
    return embeddings, notes


def _cosine_search(query_emb, note_embs, top_k=5):
    import numpy as np
    query_norm = query_emb / (np.linalg.norm(query_emb) + 1e-10)
    norms = np.linalg.norm(note_embs, axis=1, keepdims=True) + 1e-10
    note_norms = note_embs / norms
    scores = note_norms @ query_norm
    top_idx = np.argsort(scores)[::-1][:top_k]
    return [(int(i), float(scores[i])) for i in top_idx]


def rag_engine(parameters: dict = None, player=None) -> str:
    """Tool: Búsqueda semántica (RAG) sobre el vault de Obsidian."""
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
        return f"RAG: {'índice activo' if has_index else 'sin índice'} ({count} notas indexadas). Modelo: {_model_name}"

    if action == "stats":
        embeddings, notes = _load_index()
        if notes is None:
            return "Sin índice. Usá 'index' para crearlo."
        folders = {}
        for n in notes:
            parts = n["path"].split("/")
            folder = parts[0] if len(parts) > 1 else "root"
            folders[folder] = folders.get(folder, 0) + 1
        top_folders = sorted(folders.items(), key=lambda x: -x[1])[:8]
        lines = [f"**RAG Stats:** {len(notes)} notas indexadas\n"]
        for f, c in top_folders:
            lines.append(f"  📁 {f}: {c} notas")
        avg_chunk = sum(len(n["chunk"]) for n in notes) // max(len(notes), 1)
        lines.append(f"\n  Promedio chars/nota: {avg_chunk}")
        return "\n".join(lines)

    if action == "index":
        model = _get_model()
        if model is None:
            return "No pude cargar sentence-transformers. Verificá la instalación."
        notes = _collect_notes()
        if not notes:
            return "No encontré notas en el vault."
        chunks = [n["chunk"] for n in notes]
        embeddings = model.encode(chunks, show_progress_bar=False, batch_size=64)
        _save_index(embeddings, notes)
        return f"✅ Índice RAG creado: {len(notes)} notas, dim={embeddings.shape[1]}"

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
            return "Sin índice. Decime 'index' para crearlo."
        q_emb = model.encode([query])[0]
        results = _cosine_search(q_emb, embeddings, top_k)
        lines = [f"**Resultados semánticos: {query}**\n"]
        for idx, score in results:
            n = notes[idx]
            lines.append(f"**{n['name']}** (sim: {score:.3f})")
            lines.append(f"  📄 {n['path']}")
            lines.append(f"  {n['chunk'][:200]}...\n")
        return "\n".join(lines)

    return "Acciones disponibles: index, search, status, stats"
