# -*- coding: utf-8 -*-
"""
core/app.py — Arranque headless de ERIS (sin interfaz gráfica).

Agrupa el pre-arranque que puede hacerse antes de crear la ventana (Qt), de
modo que `main.py` se reduzca a orquestar la UI. No importa PyQt6 ni módulos
de UI; solo stdlib y modulos del nucleo ``core/``.

Se llama desde ``main()`` antes de instanciar ``ErisUI``.
"""
from __future__ import annotations

import json
import sys
import threading
from pathlib import Path

from core.console_log import log_system
from core.goal_setting import goal_setting_tool
from core.identity_persistence import restore_latest
from core.logging_setup import API_CONFIG_PATH
from core.ollama_autostart import apply_autostart, ensure_ollama_running
from core.time_utils import load_tz


def bootstrap() -> None:
    """Ejecuta el arranque headless de ERIS.

    Orden:
      1. Zona horaria (load_tz)
      2. Log de arranque (console_log)
      3. Restaurar identidad (identity_persistence)
      4. Auto-generar metas si vacías (goal_setting)
      5. Arrancar Ollama si está habilitado (ollama_autostart)
    """
    _load_timezone()
    _init_console_log()
    _restore_identity()
    _auto_generate_goals()
    _boot_ollama_if_enabled()


def _load_timezone() -> None:
    try:
        load_tz(API_CONFIG_PATH)
    except Exception:
        pass


def _init_console_log() -> None:
    try:
        log_system("ERIS started", {"version": "2.0", "python": sys.version[:6]})
    except Exception:
        pass


def _restore_identity() -> None:
    try:
        result = restore_latest()
        if result.get("files_restored", 0) > 0:
            print("[ERIS] Identity restaurada: {} archivos".format(result.get("files_restored")))
    except Exception as _ir:
        print("[ERIS] Identity restore skip: {}".format(str(_ir)[:60]))


def _auto_generate_goals() -> None:
    try:
        status = json.loads(goal_setting_tool({"action": "status"}))
        if status.get("active", 0) == 0:
            goal_setting_tool({"action": "auto_generate"})
            print("[ERIS] Metas auto-generadas (estaban vacias)")
    except Exception:
        pass


def _boot_ollama_if_enabled() -> None:
    try:
        _boot_cfg = {}
        if API_CONFIG_PATH.exists():
            try:
                _boot_cfg = json.loads(API_CONFIG_PATH.read_text(encoding="utf-8"))
            except Exception:
                _boot_cfg = {}
        if _boot_cfg.get("ollama_enabled", False):
            try:
                apply_autostart(bool(_boot_cfg.get("ollama_autostart", False)))
            except Exception:
                pass
            threading.Thread(
                target=ensure_ollama_running, kwargs={"wait_secs": 10.0}, daemon=True
            ).start()
    except Exception as _e:
        print(f"[ERIS] ollama boot skip: {_e}")
