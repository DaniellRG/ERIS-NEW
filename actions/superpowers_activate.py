# -*- coding: utf-8 -*-
"""
superpowers_activate.py — Activa el "modo superpoderes" de ERIS.
Habilita respuestas maximas, proactividad y refuerza el orbe.
Acciones: on (activar), off (desactivar), status.
"""
from __future__ import annotations


def superpowers_activate(parameters: dict = None, player=None) -> str:
    if parameters is None:
        parameters = {}
    action = parameters.get("action", "status").lower()

    if not player:
        return "Error: no hay instancia de ERIS."

    if action == "on":
        player._superpowers = True
        try:
            from core.emotional_state import set_energy
            set_energy(1.0)
        except Exception:
            pass
        try:
            player.ui.write_log("SYS: SUPERMODOS ACTIVADOS.")
            if hasattr(player.ui, "_orb") and player.ui._orb is not None:
                try:
                    player.ui._orb.set_glow(3)
                except Exception:
                    pass
        except Exception:
            pass
        return (
            "Súper poderes activados. ERIS operará con máxima proactividad, "
            "detallará más sus respuestas y estará más atenta a tus necesidades."
        )

    if action == "off":
        player._superpowers = False
        try:
            from core.emotional_state import set_energy
            set_energy(0.5)
        except Exception:
            pass
        try:
            player.ui.write_log("SYS: Modo normal restaurado.")
        except Exception:
            pass
        return "Súper poderes desactivados. Modo normal restaurado."

    return f"Súper poderes: {'ACTIVADOS' if getattr(player, '_superpowers', False) else 'desactivados'}."
