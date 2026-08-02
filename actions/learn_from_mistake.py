# -*- coding: utf-8 -*-
"""
learn_from_mistake.py — ERIS aprende de errores.
Registra {error, leccion, solucion} en la memoria de lecciones.
Acciones: add, recent.
"""
from __future__ import annotations
from datetime import datetime


def learn_from_mistake(parameters: dict = None, player=None) -> str:
    if parameters is None:
        parameters = {}
    action = parameters.get("action", "add").lower()

    try:
        from memory.memory_manager import remember, load_memory
    except Exception as e:
        return f"Error: memoria no disponible ({e})"

    if action == "add":
        error = (parameters.get("error") or "").strip()
        lesson = (parameters.get("lesson") or parameters.get("text") or "").strip()
        fix = (parameters.get("fix") or parameters.get("solution") or "").strip()
        if not error or not lesson:
            return "Error: se requieren 'error' y 'lesson'."
        key = "leccion_" + datetime.now().strftime("%Y%m%d_%H%M%S")
        value = f"Error: {error}\nLeccion: {lesson}" + (f"\nSolucion: {fix}" if fix else "")
        remember("lessons", key, value)
        return f"Leccion aprendida: {lesson[:120]}"

    if action == "recent":
        mem = load_memory()
        lessons = mem.get("lessons", {})
        if not isinstance(lessons, dict) or not lessons:
            return "Aun no he aprendido lecciones de errores."
        items = sorted(lessons.items(), reverse=True)[:int(parameters.get("limit", 10))]
        lines = [f"Lecciones aprendidas ({len(items)}):"]
        for k, v in items:
            val = v.get("value", v) if isinstance(v, dict) else v
            lines.append(f"  - {str(val)[:120]}")
        return "\n".join(lines)

    return "Acciones: add (error+lesson+fix), recent."
