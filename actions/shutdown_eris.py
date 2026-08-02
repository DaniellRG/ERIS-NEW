# -*- coding: utf-8 -*-
"""
shutdown_eris.py — Apaga ERIS de forma segura.
Requiere confirmacion explicita para evitar apagados accidentales.
Acciones: shutdown (apagar), confirm (apagar sin preguntar), status.
"""
from __future__ import annotations

import threading
import time


def _do_shutdown(player):
    try:
        player._stop_requested.set()
        player.set_speaking(False)
        player.ui.write_log("SYS: Apagando ERIS...")
        player.ui.close()
    except Exception:
        pass
    try:
        if player._loop:
            import asyncio
            asyncio.run_coroutine_threadsafe(player._drain_audio_queue(), player._loop)
    except Exception:
        pass
    time.sleep(1.0)
    import os
    os._exit(0)


def shutdown_eris(parameters: dict = None, player=None) -> str:
    if parameters is None:
        parameters = {}
    action = parameters.get("action", "shutdown").lower()

    if action == "status":
        return "ERIS está en línea." if player else "ERIS no está disponible en este contexto."

    if action in ("shutdown", "confirm"):
        if not player:
            return "Error: No hay instancia de ERIS."
        if action == "shutdown" and not parameters.get("confirm"):
            return (
                "¿Apagar ERIS? Respondé con {action: shutdown, confirm: true} "
                "para confirmar. No se recomienda apagar por voz sin confirmacion."
            )
        threading.Thread(target=_do_shutdown, args=(player,), daemon=True).start()
        return "Apagando ERIS. Hasta pronto."

    return "Acciones: shutdown (con confirm), confirm, status."
