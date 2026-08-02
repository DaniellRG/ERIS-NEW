# -*- coding: utf-8 -*-
"""
db_knowledge.py — Base de conocimiento de ERIS (SQLite via eris_db).
Acciones: add (agregar dato), search (buscar), topic (por tema), list.
"""
from __future__ import annotations


def db_knowledge(parameters: dict = None, player=None) -> str:
    if parameters is None:
        parameters = {}
    action = parameters.get("action", "search").lower()

    try:
        from actions.eris_db import know_add, know_search, know_by_topic
    except Exception as e:
        return f"Error: base de conocimiento no disponible ({e})"

    if action == "add":
        topic = (parameters.get("topic") or "").strip()
        fact = (parameters.get("fact") or parameters.get("value") or "").strip()
        if not topic or not fact:
            return "Error: se requieren 'topic' y 'fact'."
        confidence = float(parameters.get("confidence", 0.7))
        source = parameters.get("source", "eris")
        know_add(topic, fact, source=source, confidence=confidence)
        return f"Conocimiento guardado: {topic} -> {fact[:100]}"

    if action == "search":
        query = (parameters.get("query") or "").strip()
        if not query:
            return "Error: se requiere 'query'."
        results = know_search(query, limit=int(parameters.get("limit", 10)))
        if not results:
            return f"No encontre conocimiento sobre '{query}'."
        lines = [f"Conocimiento sobre '{query}' ({len(results)}):"]
        for r in results:
            lines.append(f"  - {r.get('topic', '?')}: {str(r.get('fact', ''))[:120]}")
        return "\n".join(lines)

    if action in ("topic", "list"):
        topic = (parameters.get("topic") or "").strip()
        if not topic:
            return "Error: se requiere 'topic'."
        results = know_by_topic(topic, limit=int(parameters.get("limit", 20)))
        if not results:
            return f"No hay conocimiento guardado sobre '{topic}'."
        lines = [f"Conocimiento sobre '{topic}' ({len(results)}):"]
        for r in results:
            lines.append(f"  - {str(r.get('fact', ''))[:150]}")
        return "\n".join(lines)

    return "Acciones: add (topic+fact), search (query), topic (topic), list."
