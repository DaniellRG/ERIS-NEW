# -*- coding: utf-8 -*-
"""
learn_session.py — Registro de aprendizajes de una sesion.
Guarda temas nuevos que ERIS aprendio durante una conversacion.
Acciones: add (topic+learnings), recent.
"""
from __future__ import annotations
from datetime import datetime


def learn_session(parameters: dict = None, player=None) -> str:
    if parameters is None:
        parameters = {}
    action = parameters.get("action", "add").lower()

    try:
        from memory.memory_manager import remember, load_memory
    except Exception as e:
        return f"Error: memoria no disponible ({e})"

    if action == "add":
        topic = (parameters.get("topic") or "").strip()
        learnings = parameters.get("learnings")
        if isinstance(learnings, str):
            learnings = [x.strip() for x in learnings.split("\n") if x.strip()] or [learnings]
        if not isinstance(learnings, list):
            learnings = []
        if not topic and not learnings:
            return "Error: se requiere 'topic' o 'learnings'."
        if not topic:
            topic = "sesion"
        key = "sesion_" + datetime.now().strftime("%Y%m%d_%H%M%S")
        value = "\n".join(f"- {l}" for l in learnings) if learnings else "(sin detalles)"
        remember("learnings", key, f"Tema: {topic}\n{value}")
        return f"Aprendizaje registrado ({len(learnings)} items): {topic}"

    if action == "recent":
        mem = load_memory()
        items = mem.get("learnings", {})
        if not isinstance(items, dict) or not items:
            return "No hay aprendizajes de sesiones registrados."
        sorted_items = sorted(items.items(), reverse=True)[:int(parameters.get("limit", 10))]
        lines = [f"Aprendizajes de sesiones ({len(sorted_items)}):"]
        for k, v in sorted_items:
            val = v.get("value", v) if isinstance(v, dict) else v
            lines.append(f"  - {str(val)[:150]}")
        return "\n".join(lines)

    return "Acciones: add (topic+learnings), recent."
