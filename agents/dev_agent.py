"""
agents/dev_agent.py — ERIS Development Specialized Agent.
Handles code help, git, codebase analysis, knowledge base, dev tasks.
"""
from __future__ import annotations

import time
from typing import Optional

def handle_dev(text: str, player=None, **kwargs) -> str:
    """Handle development-related requests."""
    from core.tracer import get_tracer
    tracer = get_tracer()
    t0 = time.perf_counter()

    text_lower = text.lower()

    try:
        # Code helper
        if any(kw in text_lower for kw in ["codigo", "code", "funcion", "function", "clase", "class", "programar"]):
            from actions.code_helper import code_helper
            result = code_helper(parameters={"action": "help"}, player=player)

        # Git
        elif any(kw in text_lower for kw in ["git", "commit", "push", "pull", "branch", "repo", "repositorio"]):
            try:
                from actions.git_control import git_control
                if "status" in text_lower or "estado" in text_lower:
                    result = git_control(parameters={"action": "status"}, player=player)
                elif "commit" in text_lower:
                    result = git_control(parameters={"action": "commit"}, player=player)
                elif "push" in text_lower:
                    result = git_control(parameters={"action": "push"}, player=player)
                elif "pull" in text_lower:
                    result = git_control(parameters={"action": "pull"}, player=player)
                else:
                    result = git_control(parameters={"action": "status"}, player=player)
            except Exception:
                result = "El control de Git no est\u00e1 disponible en este momento."

        elif any(kw in text_lower for kw in ["codebase", "analizar codigo", "estructura del proyecto"]):
            try:
                from actions.codebase import codebase
                result = codebase(parameters={"action": "analyze"}, player=player)
            except Exception:
                result = "El an\u00e1lisis de codebase no est\u00e1 disponible en este momento."

        elif any(kw in text_lower for kw in ["tarea de desarrollo", "dev task", "agent task"]):
            try:
                from actions.agent_task import agent_task
                result = agent_task(parameters={"action": "run"}, player=player)
            except Exception:
                result = "El agente de tareas no est\u00e1 disponible en este momento."

        else:
            result = (
                "Puedo ayudarte con desarrollo:\n"
                "- 'Ayuda con codigo' → Asistencia de programacion\n"
                "- 'Git status' → Estado del repositorio\n"
                "- 'Git commit/push/pull' → Operaciones de Git\n"
                "- 'Analiza codebase' → Analisis del proyecto\n"
                "- 'Knowledge base' → Consultar base de conocimiento"
            )

        elapsed = time.perf_counter() - t0
        tracer.trace_handoff("dev_agent", text, result, elapsed)
        return result

    except Exception as e:
        elapsed = time.perf_counter() - t0
        tracer.trace_handoff("dev_agent", text, "", elapsed, success=False, error=str(e))
        return f"Error en DevAgent: {e}"
