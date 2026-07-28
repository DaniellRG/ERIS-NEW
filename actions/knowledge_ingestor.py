# -*- coding: utf-8 -*-
"""actions/knowledge_ingestor.py — Bulk knowledge ingestion for ERIS.

Ingests knowledge from:
- Raw text/Markdown files in data/knowledge/
- URLs (web pages converted to markdown)
- Direct text input
- Batch directory scanning
"""
import os
import sys
import json
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = PROJECT_ROOT / "data" / "knowledge"


def knowledge_ingestor(parameters: dict, player=None) -> str:
    action = parameters.get("action", "").lower().strip()

    if not action:
        return "Error: Se requiere 'action' (ingest_file, ingest_dir, ingest_url, ingest_text, list_knowledge, stats)."

    if action == "ingest_file":
        return _ingest_file(parameters)
    elif action == "ingest_dir":
        return _ingest_dir(parameters)
    elif action == "ingest_url":
        return _ingest_url(parameters)
    elif action == "ingest_text":
        return _ingest_text(parameters)
    elif action == "list_knowledge":
        return _list_knowledge()
    elif action == "stats":
        return _stats()
    else:
        return f"Acción '{action}' no reconocida."


def _ingest_file(params: dict) -> str:
    path = params.get("path", "")
    if not path:
        return "Error: Se requiere 'path'."
    p = Path(path).resolve()
    if not p.exists():
        return f"Error: '{path}' no existe."
    if p.suffix.lower() not in {".md", ".txt", ".json", ".csv"}:
        return f"Formato no soportado: {p.suffix}. Usa .md, .txt, .json, .csv"

    target = KNOWLEDGE_DIR / p.name
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    import shutil
    shutil.copy2(str(p), str(target))

    try:
        from core.rag_pipeline import index_document
        result = index_document(str(target))
        return f"Copiado a knowledge/ y indexado: {result}"
    except Exception as e:
        return f"Copiado a knowledge/ pero error indexando: {e}"


def _ingest_dir(params: dict) -> str:
    path = params.get("path", str(KNOWLEDGE_DIR))
    if not path:
        return "Error: Se requiere 'path'."
    p = Path(path).resolve()
    if not p.exists() or not p.is_dir():
        return f"Error: '{path}' no es un directorio."

    supported = {".md", ".txt"}
    files = [f for f in p.iterdir() if f.suffix.lower() in supported]
    if not files:
        return f"No hay archivos .md/.txt en {path}."

    from core.rag_pipeline import index_document
    results = []
    for f in files:
        t0 = time.time()
        try:
            result = index_document(str(f))
            dt = time.time() - t0
            results.append(f"  OK {f.name}: {result} ({dt:.1f}s)")
        except Exception as e:
            results.append(f"  FAIL {f.name}: {e}")

    return f"Ingestados {len(results)}/{len(files)} archivos:\n" + "\n".join(results)


def _ingest_url(params: dict) -> str:
    url = params.get("url", "")
    if not url:
        return "Error: Se requiere 'url'."

    try:
        import urllib.request
        from pathlib import Path
        req = urllib.request.Request(url, headers={"User-Agent": "ERIS/1.0"})
        resp = urllib.request.urlopen(req, timeout=15)
        html = resp.read().decode("utf-8", errors="replace")

        text = _html_to_text(html)
        label = url.split("/")[-1][:50] or "web_page"
        label = "".join(c if c.isalnum() or c in "-_" else "_" for c in label)
        tmp_path = KNOWLEDGE_DIR / f"{label}.md"
        KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
        tmp_path.write_text(f"# {url}\n\n{text}", encoding="utf-8")

        from core.rag_pipeline import index_document
        result = index_document(str(tmp_path))
        return f"URL ingerida ({len(text)} chars): {result}"
    except Exception as e:
        return f"Error descargando URL: {e}"


def _html_to_text(html: str) -> str:
    import re
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:50000]


def _ingest_text(params: dict) -> str:
    text = params.get("text", "")
    label = params.get("label", "direct_input")
    if not text:
        return "Error: Se requiere 'text'."

    label = "".join(c if c.isalnum() or c in "-_" else "_" for c in label)
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    tmp_path = KNOWLEDGE_DIR / f"{label}.md"
    tmp_path.write_text(text, encoding="utf-8")

    try:
        from core.rag_pipeline import index_document
        result = index_document(str(tmp_path))
        return f"Texto ingerido ({len(text)} chars): {result}"
    except Exception as e:
        return f"Guardado pero error indexando: {e}"


def _list_knowledge() -> str:
    if not KNOWLEDGE_DIR.exists():
        return "Directorio knowledge/ no existe."
    files = [f for f in KNOWLEDGE_DIR.iterdir() if f.is_file() and f.suffix in {".md", ".txt"}]
    if not files:
        return "No hay archivos de conocimiento."
    lines = [f"Archivos de conocimiento ({len(files)}):"]
    for f in sorted(files):
        size = f.stat().st_size
        if size > 1024:
            size_str = f"{size / 1024:.1f}KB"
        else:
            size_str = f"{size}B"
        lines.append(f"  {f.name} | {size_str}")
    return "\n".join(lines)


def _stats() -> str:
    try:
        from core.rag_pipeline import stats as rag_stats
        s = rag_stats()
        return (
            f"RAG: {s.get('documents', 0)} docs | "
            f"{s.get('chunks', 0)} chunks | "
            f"{s.get('chroma_entries', 0)} vectores"
        )
    except Exception as e:
        return f"Error obteniendo stats: {e}"
