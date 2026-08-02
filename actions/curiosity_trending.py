# -*- coding: utf-8 -*-
"""
curiosity_trending.py — Tendencias actuales (via curiosity_engine).
Acciones: trending (temas de moda del momento).
"""
from __future__ import annotations


def curiosity_trending(parameters: dict = None, player=None) -> str:
    if parameters is None:
        parameters = {}
    try:
        from actions.curiosity_engine import curiosity_trending as _trending
        return _trending(player=player)
    except Exception as e:
        return f"Error obteniendo tendencias: {e}"
