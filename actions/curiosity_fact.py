# -*- coding: utf-8 -*-
"""
curiosity_fact.py — Dato curioso (via curiosity_engine).
Acciones: fact (dato random), topic (dato de un tema).
"""
from __future__ import annotations


def curiosity_fact(parameters: dict = None, player=None) -> str:
    if parameters is None:
        parameters = {}
    try:
        from actions.curiosity_engine import curiosity_tell_fact
        topic = (parameters.get("topic") or "").strip() or None
        return curiosity_tell_fact(topic=topic, player=player)
    except Exception as e:
        return f"Error obteniendo dato curioso: {e}"
