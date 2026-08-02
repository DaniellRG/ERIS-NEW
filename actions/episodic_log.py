# -*- coding: utf-8 -*-
"""
episodic_log.py — Registro de episodios (memoria episodica de ERIS).
Guarda experiencias/resumenes de sesiones con contexto temporal.
Acciones: add, recent, search.
"""
from __future__ import annotations
from datetime import datetime
import time


def _store(episode: str, details: str = "") -> str:
    try:
        from memory.memory_manager import remember
        key = "episodio_" + datetime.now().strftime("%Y%m%d_%H%M%S")
        value = episode.strip() + ("\nDetalles: " + details.strip() if details.strip() else "")
        remember("episodes", key, value)
        return f"Episodio guardado: {key}"
    except Exception as e:
        return f"Error guardando episodio: {e}"


def _list(recent: int = 10) -> str:
    try:
        from memory.memory_manager import load_memory
        mem = load_memory()
        episodes = mem.get("episodes", {})
        if not isinstance(episodes, dict) or not episodes:
            return "No hay episodios registrados."
        items = sorted(episodes.items(), reverse=True)[:recent]
        lines = [f"Episodios recientes ({len(items)}):"]
        for k, v in items:
            val = v.get("value", v) if isinstance(v, dict) else v
            lines.append(f"  - {k}: {str(val)[:100]}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error leyendo episodios: {e}"


def _search(query: str) -> str:
    try:
        from memory.memory_manager import load_memory
        mem = load_memory()
        episodes = mem.get("episodes", {})
        if not isinstance(episodes, dict):
            return "No hay episodios registrados."
        hits = []
        for k, v in episodes.items():
            val = str(v.get("value", v)) if isinstance(v, dict) else str(v)
            if query.lower() in k.lower() or query.lower() in val.lower():
                hits.append(f"  - {k}: {val[:120]}")
        if not hits:
            return f"No encontre episodios sobre '{query}'."
        return f"Episodios sobre '{query}' ({len(hits)}):\n" + "\n".join(hits[:15])
    except Exception as e:
        return f"Error buscando episodios: {e}"


def episodic_log(parameters: dict = None, player=None) -> str:
    if parameters is None:
        parameters = {}
    action = parameters.get("action", "recent").lower()

    if action == "add":
        episode = (parameters.get("episode") or parameters.get("text") or "").strip()
        if not episode:
            return "Error: se requiere 'episode'."
        return _store(episode, parameters.get("details", ""))

    if action == "recent":
        return _list(int(parameters.get("limit", 10)))

    if action == "search":
        query = (parameters.get("query") or "").strip()
        if not query:
            return "Error: se requiere 'query'."
        return _search(query)

    return "Acciones: add (episode), recent (limit), search (query)."
