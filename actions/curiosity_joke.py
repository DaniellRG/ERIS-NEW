# -*- coding: utf-8 -*-
"""
curiosity_joke.py — Chiste (via curiosity_engine).
Acciones: joke (contar un chiste).
"""
from __future__ import annotations


def curiosity_joke(parameters: dict = None, player=None) -> str:
    if parameters is None:
        parameters = {}
    try:
        from actions.curiosity_engine import curiosity_tell_joke
        return curiosity_tell_joke(player=player)
    except Exception as e:
        return f"Error contando chiste: {e}"
