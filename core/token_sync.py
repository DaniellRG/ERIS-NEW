# -*- coding: utf-8 -*-
"""
Token Sync — mantiene sincronizada la key del backend de lenguaje de Eris
con el agent_key vivo de Hermes (~/.hermes/auth.json).

PROBLEMA QUE RESUELVE
---------------------
Hermes rota su `agent_key` (providers.nous.agent_key en ~/.hermes/auth.json)
aproximadamente cada hora. Eris guarda su key en config/api_keys.json. Cuando
Hermes rota la key, la copia de Eris queda vieja y el backend responde 401 →
Eris dice "No hay backend de lenguaje disponible" y deja de ejecutar tools.

SOLUCIÓN
--------
Antes de usar la key, si el backend configurado es el Nous Portal
(openrouter_base_url contiene "nousresearch"), se lee el agent_key vivo de
auth.json y se actualiza config/api_keys.json si difiere. Es idempotente y
barato (una lectura de JSON). Si auth.json no existe o no tiene la key, no
toca nada (Eris puede correr con una key propia de OpenRouter sin problema).
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

# Cache para no leer el disco en cada llamada (1 lectura cada N segundos).
_CACHE_TTL = 30.0
_last_check: float = 0.0
_last_result: str = ""


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def _config_path() -> Path:
    return _base_dir() / "config" / "api_keys.json"


def _auth_path() -> Path:
    # El HOME real del usuario, no el workspace de Eris.
    return Path(os.path.expanduser("~")) / ".hermes" / "auth.json"


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _is_nous_backend(cfg: dict) -> bool:
    """True si el backend configurado apunta al Nous Portal."""
    base = (cfg.get("openrouter_base_url") or "").lower()
    if "nousresearch" in base:
        return True
    # Si no hay base_url custom, asumimos OpenRouter real → no tocar.
    return False


def sync_token(force: bool = False) -> str:
    """Sincroniza la key de Eris con el agent_key vivo de Hermes.

    Devuelve uno de: "synced", "ok", "skipped", "no_auth", "error".
    Nunca lanza excepción — es una operación de mantenimiento best-effort.
    """
    global _last_check, _last_result

    now = time.time()
    if not force and (now - _last_check) < _CACHE_TTL:
        return _last_result

    _last_check = now
    try:
        cfg_path = _config_path()
        cfg = _read_json(cfg_path)
        if not cfg:
            _last_result = "skipped"
            return _last_result

        if not _is_nous_backend(cfg):
            _last_result = "skipped"
            return _last_result

        auth = _read_json(_auth_path())
        live_key = (
            auth.get("providers", {})
                .get("nous", {})
                .get("agent_key", "")
        )
        if not live_key:
            _last_result = "no_auth"
            return _last_result

        current = cfg.get("openrouter_api_key", "")
        if current == live_key:
            _last_result = "ok"
            return _last_result

        cfg["openrouter_api_key"] = live_key
        cfg_path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
        print("[TokenSync] 🔄 key de Eris resincronizada con Hermes (agent_key rotó)")
        _last_result = "synced"
        return _last_result
    except Exception as e:
        print(f"[TokenSync] ⚠️ no se pudo sincronizar: {e}")
        _last_result = "error"
        return _last_result


def get_live_key() -> str:
    """Devuelve la key vigente: sincroniza primero si hace falta, luego lee."""
    sync_token()
    return _read_json(_config_path()).get("openrouter_api_key", "")


if __name__ == "__main__":
    print("resultado:", sync_token(force=True))
