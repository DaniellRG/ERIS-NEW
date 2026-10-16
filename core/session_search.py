"""core/session_search.py — Búsqueda en el historial de sesiones de Eris.

Requerido por `agents/search_agent.py`, que antes hacía
`from core.session_search import session_search` contra un módulo INEXISTENTE:
la rama «sesiones anteriores / historial / recuerdo» caía al `except` y
devolvía error (auditoría 2026-10-15, hallazgo A2).

No inventa una base nueva: reutiliza lo que ya existe.
  - `core/session_summaries.py` → índice de resúmenes (`memory/session_summaries.json`).
  - `core/rag_engine.recall_texto()` → búsqueda semántica en la memoria total
    (memoria + conocimiento + vault + episódica).

API esperada por search_agent:
    session_search(parameters={"mode": "list"|"search", "query": ...}, player=...)
"""
from __future__ import annotations


def _as_dict(parameters) -> dict:
    import json
    if isinstance(parameters, str):
        try:
            return json.loads(parameters)
        except Exception:
            return {}
    return parameters or {}


def session_search(parameters=None, player=None) -> str:
    """Busca en el historial de sesiones anteriores.

    parameters:
      mode  : "list" (índice de sesiones) | "search" (busca `query`)
      query : texto a buscar (modo search)
    """
    params = _as_dict(parameters)
    mode = str(params.get("mode") or params.get("action") or "list").lower().strip()
    query = str(params.get("query") or "").strip()

    # --- Listar el índice de sesiones ---
    if mode in ("list", "lista", "indice", "índice", "historial"):
        try:
            from core.session_summaries import sesiones
            return sesiones({"action": "indice"}, player=player)
        except Exception as e:
            return f"No pude leer el historial de sesiones: {e}"

    # --- Buscar ---
    if not query:
        return "¿Qué querés que busque en las sesiones anteriores?"

    hits: list[str] = []
    ql = query.lower()

    # 1) Resúmenes de sesión (coincidencia textual en slug/tail)
    try:
        from core.session_summaries import _load_index
        for e in _load_index():
            blob = f"{e.get('slug', '')} {e.get('tail', '')}".lower()
            if ql in blob:
                tail = (e.get("tail") or "").strip().replace("\n", " ")[:160]
                hits.append(f"• [{str(e.get('ts', ''))[:16]}] sesion_{e.get('slug', '')}: {tail}")
    except Exception:
        pass

    # 2) Búsqueda semántica en la memoria total
    if not hits:
        try:
            from core.rag_engine import recall_texto
            sem = recall_texto(query, top_k=5)
            if sem and sem.strip():
                hits.append(sem)
        except Exception:
            pass

    if not hits:
        return f"No encontré nada sobre «{query}» en las sesiones anteriores."
    return f"Sesiones relacionadas con «{query}»:\n" + "\n".join(hits[-8:])
