# -*- coding: utf-8 -*-
"""
gui/styles.py — Sistema de temas de ERIS (6 temas, gold por defecto).

Extraído de ui.py durante el refactor T4 (partir ui.py en gui/).
Módulo puro: sin dependencia de Qt widgets, solo stdlib + core.logging_setup.

Uso:
    from gui.styles import THEMES, THEME_LIST, C, _base_dir, _user_cfg_dir
    C.set_theme("cyan")
    print(C.PRI, C.TEXT)
"""
from __future__ import annotations

import json
import os
import platform as _plat
import sys
from pathlib import Path

_IS_WIN = _plat.system() == "Windows"


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).parent
        internal = base / "_internal"
        if internal.exists():
            return internal
        return base
    return Path(__file__).resolve().parent.parent  # raíz del repo (gui/ está dentro)


def _user_cfg_dir() -> Path:
    """User-writable config directory (%APPDATA%/ERIS)."""
    p = Path(os.environ.get("APPDATA", Path.home())) / "ERIS"
    p.mkdir(parents=True, exist_ok=True)
    return p


# ── Theme System (6 temas, gold default) ──────────────────────────────────────

THEMES = {
    "gold": {
        "BG": "#0f0a02", "BG2": "#1a1308", "BG3": "#2a1f0a",
        "SURFACE": "#1f180d", "SURFACE2": "#2f2612",
        "PRI": "#f59e0b", "PRI_LIGHT": "#fbbf24", "PRI_DIM": "#b8830a",
        "TEXT": "#fde68a", "TEXT_DIM": "#a08858", "TEXT_BRIGHT": "#fffbeb",
        "BORDER": "rgba(245,158,11,0.45)",
        "GLOW": "rgba(245,158,11,0.25)", "GLOW2": "rgba(251,191,36,0.15)",
        "SUCCESS": "#10b981", "ERROR": "#ef4444", "WARNING": "#f59e0b",
    },
    "cyan": {
        "BG": "#0a0a1a", "BG2": "#12122a", "BG3": "#1a1a3a",
        "SURFACE": "#1e1e3e", "SURFACE2": "#2a2a5e",
        "PRI": "#00f0ff", "PRI_LIGHT": "#66f0ff", "PRI_DIM": "#0090aa",
        "TEXT": "#c8c8d4", "TEXT_DIM": "#6a6a8a", "TEXT_BRIGHT": "#f0f0ff",
        "BORDER": "rgba(0,240,255,0.4)",
        "GLOW": "rgba(0,240,255,0.25)", "GLOW2": "rgba(102,240,255,0.15)",
        "SUCCESS": "#00ff88", "ERROR": "#ff3355", "WARNING": "#ffcc00",
    },
    "green": {
        "BG": "#0a0f0a", "BG2": "#0f1a0f", "BG3": "#1a2a1a",
        "SURFACE": "#122012", "SURFACE2": "#1a301a",
        "PRI": "#00ff88", "PRI_LIGHT": "#66ffaa", "PRI_DIM": "#00aa55",
        "TEXT": "#c8e8d4", "TEXT_DIM": "#6a8a7a", "TEXT_BRIGHT": "#f0fff5",
        "BORDER": "rgba(0,255,136,0.4)",
        "GLOW": "rgba(0,255,136,0.25)", "GLOW2": "rgba(102,255,170,0.15)",
        "SUCCESS": "#00ff88", "ERROR": "#ff3355", "WARNING": "#ffcc00",
    },
    "red": {
        "BG": "#0f0a0a", "BG2": "#1a0f0f", "BG3": "#2a1a1a",
        "SURFACE": "#201212", "SURFACE2": "#301a1a",
        "PRI": "#ff3355", "PRI_LIGHT": "#ff6688", "PRI_DIM": "#aa2244",
        "TEXT": "#e4c8c8", "TEXT_DIM": "#8a6a6a", "TEXT_BRIGHT": "#fff0f0",
        "BORDER": "rgba(255,51,85,0.4)",
        "GLOW": "rgba(255,51,85,0.25)", "GLOW2": "rgba(255,102,136,0.15)",
        "SUCCESS": "#00ff88", "ERROR": "#ff3355", "WARNING": "#ffcc00",
    },
    "purple": {
        "BG": "#0a0a12", "BG2": "#12121a", "BG3": "#1a1a2a",
        "SURFACE": "#1e1e2e", "SURFACE2": "#2a2a3e",
        "PRI": "#7b2d8e", "PRI_LIGHT": "#aa55cc", "PRI_DIM": "#5a1e6a",
        "TEXT": "#c8c8d4", "TEXT_DIM": "#6a6a7a", "TEXT_BRIGHT": "#f0f0ff",
        "BORDER": "rgba(123,45,142,0.45)",
        "GLOW": "rgba(123,45,142,0.25)", "GLOW2": "rgba(170,85,204,0.15)",
        "SUCCESS": "#00ff88", "ERROR": "#ff3355", "WARNING": "#ffcc00",
    },
    "white": {
        "BG": "#0a0a0a", "BG2": "#141414", "BG3": "#1e1e1e",
        "SURFACE": "#181818", "SURFACE2": "#282828",
        "PRI": "#cccccc", "PRI_LIGHT": "#eeeeee", "PRI_DIM": "#888888",
        "TEXT": "#cccccc", "TEXT_DIM": "#8a8a8a", "TEXT_BRIGHT": "#ffffff",
        "BORDER": "rgba(200,200,200,0.3)",
        "GLOW": "rgba(200,200,200,0.2)", "GLOW2": "rgba(255,255,255,0.1)",
        "SUCCESS": "#00ff88", "ERROR": "#ff3355", "WARNING": "#ffcc00",
    },
}

THEME_LIST = list(THEMES.keys())


class C:
    """Theme-aware color constants. Use C.COLOR_NAME anywhere in UI code."""
    _current = "gold"

    @classmethod
    def set_theme(cls, name: str):
        if name in THEMES:
            cls._current = name
            for k, v in THEMES[name].items():
                setattr(cls, k, v)

    @classmethod
    def get_theme(cls) -> str:
        return cls._current


def _load_saved_theme():
    try:
        from core.logging_setup import API_CONFIG_PATH
        if API_CONFIG_PATH.exists():
            cfg = json.loads(API_CONFIG_PATH.read_text("utf-8"))
        else:
            cfg = json.loads((_base_dir() / "config" / "api_keys.json").read_text("utf-8"))
        theme = cfg.get("eris_theme", "gold")
        if theme in THEMES:
            C.set_theme(theme)
    except Exception:
        pass


C.set_theme("gold")
