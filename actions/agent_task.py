# -*- coding: utf-8 -*-
"""
agent_task.py — Delega una tarea a un agente de IA (OpenRouter u Ollama).
Acciones: run (task), status.
"""
from __future__ import annotations


def agent_task(parameters: dict = None, player=None) -> str:
    if parameters is None:
        parameters = {}
    action = parameters.get("action", "run").lower()

    if action == "status":
        try:
            from actions.openrouter_agent import _get_api_key, _get_ollama_cfg
            has_or = bool(_get_api_key())
            has_ol = bool(_get_ollama_cfg())
            return f"Agentes disponibles: OpenRouter {'SI' if has_or else 'NO'}, Ollama {'SI' if has_ol else 'NO'}."
        except Exception:
            return "Estado de agentes no disponible."

    if action == "run":
        task = (parameters.get("task") or parameters.get("text") or "").strip()
        if not task:
            return "Error: se requiere 'task'."
        model = parameters.get("model", "google/gemini-2.5-flash")
        mode = parameters.get("mode", "general")
        prompt = f"[MODO: {mode}]\n{task}"
        try:
            from actions.openrouter_agent import openrouter_agent
            if player:
                player.write_log(f"[agent_task] Delegando a {model}...")
            result = openrouter_agent(prompt, model=model)
            return f"Resultado del agente:\n{str(result)[:1500]}"
        except Exception as e:
            return f"Error delegando tarea: {e}"

    return "Acciones: run (task), status."
