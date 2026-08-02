# -*- coding: utf-8 -*-
"""
ask_opencode.py — ERIS delega una pregunta de codigo a un agente IA (OpenRouter).
Acciones: ask (question), status.
"""
from __future__ import annotations


def ask_opencode(parameters: dict = None, player=None) -> str:
    if parameters is None:
        parameters = {}
    action = parameters.get("action", "ask").lower()

    if action == "ask":
        question = (parameters.get("question") or parameters.get("text") or "").strip()
        if not question:
            return "Error: se requiere 'question'."
        model = parameters.get("model", "google/gemini-2.5-flash")
        prompt = (
            "Eres un experto en programacion. Responde la siguiente pregunta de codigo "
            "de forma clara y con ejemplos:\n" + question
        )
        try:
            from actions.openrouter_agent import openrouter_agent
            result = openrouter_agent(prompt, model=model)
            return f"Respuesta de codigo:\n{str(result)[:1500]}"
        except Exception as e:
            return f"Error consultando al agente de codigo: {e}"

    if action == "status":
        try:
            from actions.openrouter_agent import _get_api_key
            has = bool(_get_api_key())
            return "Agente de codigo disponible (OpenRouter)." if has else "Agente de codigo sin API key de OpenRouter configurada."
        except Exception:
            return "Estado del agente de codigo no disponible."

    return "Acciones: ask (question), status."
