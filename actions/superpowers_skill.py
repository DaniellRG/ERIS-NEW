# -*- coding: utf-8 -*-
"""superpowers_skill.py — Cargador dict-style de skills de metodología
Superpowers (SDLC). Envuelve skills.superpowers.superpowers_activate() para
que el dispatcher (parameters=, player=) pueda invocarlo."""


def superpowers_skill(parameters: dict, player=None) -> str:
    name = parameters.get("name", "")
    if not name:
        return "Especifica 'name' (ej: 'test-driven-development', 'brainstorming')."
    try:
        from skills.superpowers import superpowers_activate as _sa
        if _sa is None:
            return "Módulo superpowers no disponible."
        return _sa(name)
    except Exception as e:
        return f"Error cargando skill Superpowers '{name}': {e}"
