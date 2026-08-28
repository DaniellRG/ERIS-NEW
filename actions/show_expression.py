# -*- coding: utf-8 -*-
"""show_expression.py — Expresiones de la cara animada de ERIS.
Tool uniforme en el registry (el dispatcher sigue priorizando su handler
especial, pero así get_tool() la resuelve para auditoría y pruebas)."""


def show_expression(parameters: dict, player=None) -> str:
    expr = (parameters.get("expression") or "").strip().lower()
    text = (parameters.get("text") or "").strip()
    if not expr:
        return "Error: Se requiere 'expression'."
    if player is not None:
        ui = getattr(player, "ui", None)
        if ui is not None and hasattr(ui, "show_expression"):
            try:
                ui.show_expression(expr, text)
            except Exception as e:
                return f"No pude mostrar la expresión: {e}"
    return f"Listo: mostré '{expr}' en mi cara. {text}".strip()
