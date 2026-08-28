# -*- coding: utf-8 -*-
"""actions/document_rag.py — RAG tool for ERIS.

Expose the RAG pipeline to the LLM agent via a single tool with actions:
  index   — index a document (path) into the vector store
  query   — semantic search over indexed documents
  list    — list all indexed documents
  stats   — show collection stats
  delete  — remove a document from the index
  clear   — wipe entire index
  ingest  — ingest raw text with a label
"""
import os
import sys
import json
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def document_rag(parameters: dict, player=None) -> str:
    action = parameters.get("action", "").lower().strip()

    if not action:
        return "Error: Se requiere 'action' (index, query, list, stats, delete, clear, ingest, index_episodic, compact_episodic, index_vault)."

    try:
        from core.rag_pipeline import (
            index_document,
            query_documents,
            list_indexed,
            delete_index,
            clear_all,
            stats,
            index_episodic,
            compact_episodic,
            index_vault,
        )
    except ImportError as e:
        return f"Error importando RAG pipeline: {e}"

    if action in ("index_episodic", "episodic"):
        max_entries = int(parameters.get("max_entries", 0))
        return index_episodic(max_entries=max_entries)

    if action in ("compact_episodic", "compact"):
        days = int(parameters.get("days", parameters.get("older_than", 30)))
        return compact_episodic(older_than_days=days)

    if action in ("index_vault", "vault"):
        folders = parameters.get("folders", "")
        return index_vault(vault_path=parameters.get("path", ""), folders=folders)

    if action == "index":
        path = parameters.get("path", "")
        if not path:
            return "Error: Se requiere 'path' del documento."
        abs_path = str(Path(path).resolve())
        if not os.path.exists(abs_path):
            return f"Error: '{path}' no existe."
        t0 = time.time()
        result = index_document(abs_path)
        dt = time.time() - t0
        return f"Indexado en {dt:.1f}s: {result}"

    elif action == "query":
        query = parameters.get("query", "")
        if not query:
            return "Error: Se requiere 'query'."
        top_k = int(parameters.get("top_k", 5))
        t0 = time.time()
        results = query_documents(query, top_k=top_k)
        dt = time.time() - t0

        if not results:
            return f"Sin resultados para: '{query}' ({dt:.1f}s)"

        lines = [f"Resultados para '{query}' ({dt:.1f}s):"]
        for i, r in enumerate(results, 1):
            score = r.get("score", 0)
            source = r.get("source", "?")
            filename = r.get("filename", "?")
            text = r.get("text", "")[:300]
            lines.append(f"\n--- #{i} (score: {score:.3f}) ---")
            lines.append(f"Fuente: {source} | Chunk: {r.get('chunk', '?')}")
            lines.append(text)
        return "\n".join(lines)

    elif action == "list":
        docs = list_indexed()
        if not docs:
            return "No hay documentos indexados."
        lines = [f"Documentos indexados ({len(docs)}):"]
        for d in docs:
            chunks = d.get("chunks", 0)
            size = d.get("size_bytes", 0)
            size_str = f"{size / 1024:.1f}KB" if size < 1024 * 1024 else f"{size / (1024**2):.1f}MB"
            lines.append(f"  {d.get('filename', '?')} | {chunks} chunks | {size_str}")
        return "\n".join(lines)

    elif action == "stats":
        s = stats()
        return (
            f"RAG Stats: {s.get('documents', 0)} documentos | "
            f"{s.get('chunks', 0)} chunks | "
            f"{s.get('chroma_entries', 0)} en ChromaDB"
        )

    elif action == "delete":
        path = parameters.get("path", "")
        if not path:
            return "Error: Se requiere 'path'."
        result = delete_index(str(Path(path).resolve()))
        return f"Eliminado: {result}"

    elif action == "clear":
        confirm = parameters.get("confirm", False)
        if not confirm:
            return "Envía 'confirm=true' para borrar TODO el índice RAG."
        result = clear_all()
        return f"Índice limpiado: {result}"

    elif action == "ingest":
        text = parameters.get("text", "")
        label = parameters.get("label", "text_ingest")
        if not text:
            return "Error: Se requiere 'text'."
        tmp_path = os.path.join(str(PROJECT_ROOT), "data", "tmp_ingest", f"{label}.md")
        os.makedirs(os.path.dirname(tmp_path), exist_ok=True)
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(text)
        result = index_document(tmp_path)
        return f"Texto ingerido ({len(text)} chars): {result}"

    elif action == "agentic_query":
        query = parameters.get("query", "")
        if not query:
            return "Error: Se requiere 'query'."
        top_k = int(parameters.get("top_k", 5))
        force = parameters.get("force_decompose", False)
        try:
            from core.agentic_rag import agentic_query
            t0 = time.time()
            result = agentic_query(query, top_k=top_k, force_decompose=force)
            dt = time.time() - t0
            if "error" in result:
                return result["error"]
            lines = [f"Agentic RAG ({dt:.1f}s) — {result['num_results']} resultados:"]
            if result.get("sub_queries"):
                lines.append(f"Sub-queries: {result['sub_queries']}")
            lines.append(f"\n{result['answer']}")
            return "\n".join(lines)
        except ImportError as e:
            return f"Error importando agentic_rag: {e}"

    else:
        return f"Acción '{action}' no reconocida. Usa: index, query, agentic_query, list, stats, delete, clear, ingest, index_episodic, compact_episodic, index_vault."
