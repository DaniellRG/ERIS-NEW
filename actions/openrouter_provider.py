# -*- coding: utf-8 -*-
"""
OpenRouter Provider — Chat con modelos de OpenRouter vía API REST (OpenAI-compatible).
Respaldo con cientos de modelos cuando los demás proveedores fallan.

Key: config/api_keys.json -> openrouter_api_key  (https://openrouter.ai/keys)
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "meta-llama/llama-3.3-70b-instruct"


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def _cfg() -> dict:
    try:
        return json.loads((_base_dir() / "config" / "api_keys.json").read_text(encoding="utf-8"))
    except Exception:
        return {}


def get_api_key() -> str:
    # Auto-sync con el agent_key vivo de Hermes (rota ~1h). Best-effort.
    try:
        from core.token_sync import sync_token
        sync_token()
    except Exception:
        pass
    cfg = _cfg()
    key = cfg.get("openrouter_api_key", "")

    # Auto-gestión de keys: validar la key on-the-fly y rotar si está vencida.
    # Si la key da error, el key_manager intenta scoped-token (xKiro) o pide al
    # usuario una key nueva → esto es lo que Eris "crea" por sí misma: keys
    # efímeras/deleagadas cuando el provider lo permite.
    try:
        from core.key_manager import resolve_key
        resolved = resolve_key(provider="openrouter", purpose="chat")
        if resolved.get("need_user_input"):
            # No hay key válida → Eris debería preguntar al usuario.
            msg = resolved.get("message", "")
            print(f"[ERIS] KeyManager: {msg}", file=sys.stderr)
        elif resolved.get("key"):
            key = resolved["key"]
            # Si la key fue auto-creada (scoped), registrar en config para reuso
            if resolved.get("source") == "auto-created":
                cfg2 = _cfg()
                cfg2.setdefault("scoped_keys", {})[key] = {
                    "provider": "openrouter",
                    "purpose": "chat",
                    "expires_at": 0,  # scoped ya tiene su propio TTL
                    "source": "auto-created",
                }
    except Exception:
        pass  # Nunca romper el chat si el key_manager falla

    return key


def get_base_url() -> str:
    """Base URL configurable: permite apuntar a cualquier endpoint
    OpenAI-compatible (OpenRouter, Nous Portal, etc.). Default: OpenRouter."""
    base = _cfg().get("openrouter_base_url", "") or "https://openrouter.ai/api/v1"
    return base.rstrip("/")


def is_available() -> bool:
    return bool(get_api_key())


def chat(
    prompt: str,
    system: str = "",
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 1024,
) -> str:
    """Send a chat prompt to an OpenAI-compatible endpoint and return the text."""
    cfg = _cfg()
    api_key = get_api_key()  # incluye auto-sync del agent_key de Hermes
    if not api_key:
        raise RuntimeError("No OpenRouter API key configured (openrouter_api_key).")
    if model is None:
        model = cfg.get("openrouter_model", DEFAULT_MODEL)
    url = get_base_url() + "/chat/completions"

    _last_err = None
    for _attempt in range(3):
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "ERIS-Nexus/2.0",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8", "replace")
            except Exception:
                pass
            _last_err = f"HTTP {e.code}: {body}"
            if e.code == 401 and _attempt < 2:
                # Key vencida → rotar via key_manager y reintentar
                try:
                    from core.key_manager import rotate_on_401
                    new = rotate_on_401(provider="openrouter", old_key=api_key)
                    if new and new.get("key"):
                        api_key = new["key"]
                        continue
                except Exception:
                    pass
                raise RuntimeError(f"OpenRouter 401: key vencida y no se pudo rotar.") from e
            if _attempt < 2:
                import time as _t; _t.sleep(2)
                continue
            raise RuntimeError(f"OpenRouter HTTP {e.code}: {body}") from e
    try:
        return result["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"OpenRouter unexpected response: {result}") from exc
