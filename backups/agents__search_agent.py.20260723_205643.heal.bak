"""
agents/search_agent.py — ERIS Search Specialized Agent.
Handles all search operations: web, file, session, super search.
"""
from __future__ import annotations

import time
from typing import Optional

def handle_search(text: str, player=None, **kwargs) -> str:
    """Handle search-related requests."""
    from core.tracer import get_tracer
    tracer = get_tracer()
    t0 = time.perf_counter()

    text_lower = text.lower()

    try:
        # Session search
        if any(kw in text_lower for kw in ["sesiones anteriores", "historial", "buscar en mis sesiones", "sesion anterior", "recuerdo"]):
            from core.session_search import session_search
            # Extract query from text
            query = text_lower.replace("sesiones anteriores", "").replace("historial", "").strip()
            if not query:
                result = session_search(parameters={"mode": "list"}, player=player)
            else:
                result = session_search(parameters={"mode": "search", "query": query}, player=player)

        # Super search (file search)
        elif any(kw in text_lower for kw in ["buscar archivo", "buscar en", "donde esta", "donde queda", "encontrar archivo", "super search"]):
            from actions.super_search import super_search
            query = text_lower.replace("buscar archivo", "").replace("buscar en", "").replace("donde esta", "").replace("donde queda", "").strip()
            if query:
                result = super_search(parameters={"query": query}, player=player)
            else:
                result = "Que archivo o carpeta busco? Decime el nombre o parte del nombre."

        # Web search
        else:
            from actions.web_search import web_search as web_search_action
            query = text_lower
            for prefix in ["busca", "buscar", "search", "encontrar", "find", "que es", "que significa"]:
                if query.startswith(prefix):
                    query = query[len(prefix):].strip()
                    break

            if query:
                result = web_search_action(parameters={"query": query})
            else:
                result = "Que queres buscar en la web?"

        elapsed = time.perf_counter() - t0
        tracer.trace_handoff("search_agent", text, result, elapsed)
        return result

    except Exception as e:
        elapsed = time.perf_counter() - t0
        tracer.trace_handoff("search_agent", text, "", elapsed, success=False, error=str(e))
        return f"Error en SearchAgent: {e}"
