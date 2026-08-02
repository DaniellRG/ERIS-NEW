# -*- coding: utf-8 -*-
"""
curiosity_fun.py — Sugerencia divertida (via curiosity_engine).
Acciones: fun (algo divertido para hacer).
"""
from __future__ import annotations


def curiosity_fun(parameters: dict = None, player=None) -> str:
    if parameters is None:
        parameters = {}
    try:
        from actions.curiosity_engine import curiosity_suggest_fun
        return curiosity_suggest_fun(player=player)
    except Exception as e:
        return f"Error obteniendo sugerencia: {e}"
