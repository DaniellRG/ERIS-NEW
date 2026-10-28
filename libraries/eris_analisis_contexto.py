"""
eris_analisis_contexto.py — Librería propia creada por Eris.

Analizar y resolver ambigüedad de contexto con OpenCode.
Creada: 2026-10-23 17:43
"""
import json


def analizar_contexto_opencode(**kwargs):
    """Analiza el contexto de OpenCode para entender la tarea truncada."""
def analizar_contexto_opencode(contexto_visual, sesion_opencode):
    if 'modificar un proyecto d' in contexto_visual:
        return 'modificar proyecto de desarrollo'
    return sesion_opencode.get('task', 'desconocido')