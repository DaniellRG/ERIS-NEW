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
    return _cfg().get("openrouter_api_key", "")


def is_available() -> bool:
    return bool(get_api_key())


def chat(
    prompt: str,
    system: str = "",
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 1024,
) -> str:
    """Send a chat prompt to OpenRouter and return the response text."""
    cfg = _cfg()
    api_key = cfg.get("openrouter_api_key", "")
    if not api_key:
        raise RuntimeError("No OpenRouter API key configured (openrouter_api_key).")
    if model is None:
        model = cfg.get("openrouter_model", DEFAULT_MODEL)

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
        BASE_URL,
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
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", "replace")
        except Exception:
            pass
        raise RuntimeError(f"OpenRouter HTTP {e.code}: {body}") from e
    try:
        return result["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"OpenRouter unexpected response: {result}") from exc
