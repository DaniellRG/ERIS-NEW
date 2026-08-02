# -*- coding: utf-8 -*-
"""
sleep_mode.py — Duerme/despierta a ERIS.
En modo sueño no responde a la palabra de activacion ni procesa audio.
Acciones: on (dormir), off (despertar), status.
"""
from __future__ import annotations


def sleep_mode(parameters: dict = None, player=None) -> str:
    if parameters is None:
        parameters = {}
    action = parameters.get("action", "status").lower()

    if not player:
        return "Error: No hay instancia de ERIS para controlar el modo sueño."

    if action == "on":
        player._sleeping = True
        try:
            player._wake_gate_open = False
        except Exception:
            pass
        try:
            player.ui.set_state("IDLE")
            player.ui.write_log("SYS: ERIS en modo sueño.")
        except Exception:
            pass
        return "ERIS dormida. Dime 'Eris, despierta' para reactivarla."

    if action == "off":
        player._sleeping = False
        try:
            player._wake_gate_open = True
        except Exception:
            pass
        try:
            player.ui.set_state("THINKING")
            player.ui.write_log("SYS: ERIS despierta.")
        except Exception:
            pass
        return "ERIS despierta y atenta."

    status = "dormida" if getattr(player, "_sleeping", False) else "despierta"
    return f"ERIS está {status}."


# Compatibilidad con el registro (nombre de función esperado)
def sleep_state(player=None):
    return sleep_mode({"action": "status"}, player)
