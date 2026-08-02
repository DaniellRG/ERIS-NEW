# -*- coding: utf-8 -*-
"""
full_training.py — Entrenamiento completo de ERIS (via training_pipeline).
Acciones: status (puntajes por modulo), lessons (lecciones aprendidas).
"""
from __future__ import annotations


def full_training(parameters: dict = None, player=None) -> str:
    if parameters is None:
        parameters = {}
    action = parameters.get("action", "status").lower()

    try:
        from core import training_pipeline
    except Exception as e:
        return f"Error: pipeline de entrenamiento no disponible ({e})"

    if action == "status":
        try:
            scores = training_pipeline._load_scores()
        except Exception:
            scores = {}
        if not scores:
            return "Aun no hay registros de entrenamiento."
        lines = [f"Puntajes de entrenamiento ({len(scores)} modulos):"]
        for mod, score in sorted(scores.items()):
            lines.append(f"  - {mod}: {score}")
        return "\n".join(lines)

    if action == "lessons":
        try:
            lessons = training_pipeline._load_lessons()
        except Exception:
            lessons = []
        if not lessons:
            return "No hay lecciones aprendidas en el pipeline de entrenamiento."
        lines = [f"Lecciones del pipeline ({len(lessons)}):"]
        for l in lessons[-int(parameters.get("limit", 15)):]:
            lines.append(f"  - {str(l)[:150]}")
        return "\n".join(lines)

    return "Acciones: status, lessons."
