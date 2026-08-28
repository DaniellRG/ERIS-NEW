# -*- coding: utf-8 -*-
"""
multi_search.py — Búsqueda web multi-fuente con consolidación por LLM.

Consulta varias fuentes (Google, DuckDuckGo), extrae las N páginas más
relevantes con webfetch y consolida los hallazgos en un resumen estructurado
usando el LLM (OpenRouter → Ollama → Gemini), igual que hace opencode con una
búsqueda web profunda. Sin LLM disponible, devuelve los resultados crudos.
"""
from __future__ import annotations

import re

try:
    from actions.web_search import _search_google, _search_ddg, _log_search
except ImportError:
    def _search_google(query, num_results=5):
        return []
    def _search_ddg(query, num_results=5):
        return []
    def _log_search(query, source, results):
        pass


def _fetch_page(url: str, max_chars: int = 4000) -> str:
    try:
        from actions.webfetch import webfetch
        return str(webfetch({"url": url, "format": "text", "timeout": 15}))[:max_chars]
    except Exception as e:
        return f"[fetch error] {e}"


def _summarize_with_llm(query: str, sources_text: str, max_tokens: int = 1200) -> str:
    try:
        from core.agent_architecture import _chat
    except Exception:
        return ""
    system = (
        "Eres un investigador web experto de ERIS. Con el texto de varias fuentes "
        "sobre la consulta del usuario, produce un RESUMEN CONSOLIDADO en español: "
        "3-7 puntos con la información clave, y al final una línea 'Fuentes:' con "
        "las URLs más relevantes citadas. Si los datos de las fuentes son "
        "contradictorios, indícalo. No inventes información que no esté en las "
        "fuentes."
    )
    user = f"Consulta: {query}\n\n--- FUENTES ---\n{sources_text[:16000]}"
    resp = _chat([{"role": "system", "content": system},
                  {"role": "user", "content": user}], max_tokens=max_tokens)
    if resp.get("error"):
        return ""
    return resp.get("content") or ""


def multi_search(parameters: dict = None, player=None) -> str:
    """Búsqueda web multi-fuente. Consulta Google y DuckDuckGo, extrae las páginas
    más relevantes y consolida un resumen con LLM. Params: query (obligatorio),
    num_results (paginas a extraer, default 3), summarize (bool, default True),
    action (search | sources)."""
    query = str(parameters.get("query") or "").strip()
    num_results = int(parameters.get("num_results") or 3)
    summarize = bool(parameters.get("summarize", True))
    action = str(parameters.get("action") or "search").lower()

    if not query:
        return "Error: se requiere 'query'."

    if action == "sources":
        g = _search_google(query, 5)
        d = _search_ddg(query, 5)
        _log_search("multi_sources", query, g[:300])
        return f"--- GOOGLE ---\n{g}\n\n--- DUCKDUCKGO ---\n{d}"

    if player:
        try:
            player.write_log(f"[multi_search] '{query}' (paginas: {num_results})")
        except Exception:
            pass

    g = _search_google(query, 5)
    d = _search_ddg(query, 5)

    urls = []
    for block in (g, d):
        for m in re.finditer(r"(https?://[^\s\)\"']+)", block or ""):
            u = m.group(1).rstrip(".,;")
            if u not in urls and "google." not in u.split("/")[2].lower():
                urls.append(u)

    raw = [f"--- GOOGLE ---\n{g}", f"--- DUCKDUCKGO ---\n{d}"]
    for url in urls[:num_results]:
        raw.append(f"\n--- PAGINA: {url} ---\n{_fetch_page(url)}")

    if player:
        try:
            player.write_log(f"[multi_search] {len(urls)} URLs, consolidando...")
        except Exception:
            pass

    combined = "\n".join(raw)
    if summarize:
        summary = _summarize_with_llm(query, combined)
        if summary:
            return f"Resumen consolidado para '{query}':\n\n{summary}"

    _log_search("multi", query, combined[:300])
    return f"Resultados para '{query}' (sin resumen LLM):\n\n{combined[:9000]}"
