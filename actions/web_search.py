# -*- coding: utf-8 -*-
"""
web_search.py — Búsqueda web real-time con DuckDuckGo.
Acciones:
  search   — Buscar en la web
  news     — Noticias recientes
  images   — Buscar imágenes
"""
from __future__ import annotations

import json
from typing import Any


def web_search(parameters: dict = None, player=None) -> str:
    """Tool: Búsqueda web real-time en DuckDuckGo."""
    params = parameters or {}
    query = str(params.get("query", "")).strip()
    action = str(params.get("action", "search")).lower().strip()
    max_results = min(int(params.get("max_results", 8)), 20)

    if not query:
        return "Necesito un término de búsqueda. Ej: 'noticias IA 2026'"

    try:
        from ddgs import DDGS
    except ImportError:
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            return "ddgs no instalado. pip install ddgs"

    try:
        with DDGS() as ddgs:
            if action == "news":
                results = list(ddgs.news(query, max_results=max_results))
                if not results:
                    return f"No encontré noticias sobre '{query}'"
                lines = [f"**Noticias: {query}**\n"]
                for i, r in enumerate(results, 1):
                    title = r.get("title", "")
                    body = r.get("body", "")[:150]
                    url = r.get("url", "")
                    date = r.get("date", "")[:10]
                    lines.append(f"{i}. **{title}** ({date})")
                    lines.append(f"   {body}")
                    lines.append(f"   {url}\n")
                return "\n".join(lines)

            elif action == "images":
                results = list(ddgs.images(query, max_results=min(max_results, 12)))
                if not results:
                    return f"No encontré imágenes de '{query}'"
                lines = [f"**Imágenes: {query}**\n"]
                for i, r in enumerate(results, 1):
                    title = r.get("title", "")
                    url = r.get("image", "")
                    source = r.get("source", "")
                    lines.append(f"{i}. {title} — {source}")
                    lines.append(f"   {url}")
                return "\n".join(lines)

            else:
                results = list(ddgs.text(query, max_results=max_results))
                if not results:
                    return f"No encontré resultados para '{query}'"
                lines = [f"**Resultados: {query}**\n"]
                for i, r in enumerate(results, 1):
                    title = r.get("title", "")
                    body = r.get("body", "")[:200]
                    url = r.get("href", "")
                    lines.append(f"{i}. **{title}**")
                    lines.append(f"   {body}")
                    lines.append(f"   {url}\n")
                return "\n".join(lines)

    except Exception as e:
        return f"Error en búsqueda: {str(e)[:200]}"
