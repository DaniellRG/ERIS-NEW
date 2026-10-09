# -*- coding: utf-8 -*-
"""
Token Sync — key del backend de lenguaje de Eris.

ERIS ES INDEPENDIENTE
---------------------
La key del backend vive EXCLUSIVAMENTE en config/api_keys.json. Eris no lee ni
sincroniza la key de ningún agente externo.

Histórico: antes esta capa copiaba el `agent_key` vivo de Hermes desde
~/.hermes/auth.json (rotaba ~1h) cada vez que el backend era el Portal Nous.
Ese acople se eliminó para que Eris sea autónoma: si su key falta o vence, lo
resuelve core/key_manager (scoped-key / rotación) o se le pide una nueva al
usuario.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def _config_path() -> Path:
    return _base_dir() / "config" / "api_keys.json"


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def sync_token(force: bool = False) -> str:
    """No-op de compatibilidad: Eris no sincroniza con ninguna key externa.

    Devuelve "ok" si hay una key propia configurada, "no_key" si no.
    Nunca lanza excepción (es una operación de mantenimiento best-effort).
    """
    return "ok" if _read_json(_config_path()).get("openrouter_api_key", "") else "no_key"


def get_live_key() -> str:
    """Devuelve la key propia de Eris desde config/api_keys.json."""
    return _read_json(_config_path()).get("openrouter_api_key", "")
