# -*- coding: utf-8 -*-
"""
eris_ui_control.py — Control de la interfaz de ERIS.
Acciones: state (cambiar estado visual), log (escribir en el log de la UI),
         focus (traer la ventana principal al frente), show (mostrar/ocultar orbe).
"""
from __future__ import annotations


def eris_ui_control(parameters: dict = None, player=None) -> str:
    if parameters is None:
        parameters = {}
    action = parameters.get("action", "state").lower()

    if not player or not hasattr(player, "ui"):
        return "Error: no hay interfaz de ERIS en este contexto."

    ui = player.ui

    if action == "state":
        state = (parameters.get("state") or "").strip().upper()
        valid = {"IDLE", "LISTENING", "THINKING", "SPEAKING", "OFFLINE"}
        if state not in valid:
            return f"Error: estado invalido. Usa uno de: {', '.join(sorted(valid))}."
        ui.set_state(state)
        return f"Estado de ERIS cambiado a {state}."

    if action == "log":
        text = (parameters.get("text") or "").strip()
        if not text:
            return "Error: se requiere 'text'."
        ui.write_log(f"CMD: {text}")
        return "Mensaje escrito en el log de ERIS."

    if action == "focus":
        try:
            if hasattr(ui, "showNormal") and hasattr(ui, "raise_") and hasattr(ui, "activateWindow"):
                ui.showNormal()
                ui.raise_()
                ui.activateWindow()
                return "Ventana principal de ERIS traída al frente."
            return "La interfaz no permite foco en este contexto."
        except Exception as e:
            return f"Error: {e}"

    if action == "show":
        try:
            orb = getattr(player, "_orb", None)
            if orb is not None:
                visible = parameters.get("visible", True)
                if hasattr(orb, "show") and hasattr(orb, "hide"):
                    (orb.show if visible else orb.hide)()
                    return f"Orbe {'mostrado' if visible else 'ocultado'}."
            return "No hay orbe disponible."
        except Exception as e:
            return f"Error: {e}"

    return "Acciones: state, log, focus, show (visible)."
