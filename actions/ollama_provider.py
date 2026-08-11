# -*- coding: utf-8 -*-
"""
Ollama Provider – Chat con modelos locales vía API REST de Ollama.
"""

import json
import urllib.request
import urllib.error
import threading
from pathlib import Path

_local_cfg = {}
_cfg_lock = threading.Lock()


def _get_cfg():
    global _local_cfg
    with _cfg_lock:
        if not _local_cfg:
            try:
                if getattr(sys, "frozen", False):
                    base = Path(sys.executable).parent
                else:
                    base = Path(__file__).resolve().parent.parent
                cfg_path = base / "config" / "api_keys.json"
                _local_cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            except Exception:
                _local_cfg = {}
        return _local_cfg


import sys


def is_available(base_url: str | None = None) -> bool:
    """Check if Ollama is running and reachable."""
    if base_url is None:
        base_url = _get_cfg().get("ollama_base_url", "http://localhost:11434")
    try:
        req = urllib.request.Request(f"{base_url}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status == 200
    except Exception:
        return False


def chat(
    prompt: str,
    system: str = "",
    model: str | None = None,
    base_url: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 1024,
) -> str:
    """Send a prompt to Ollama and return the response text."""
    cfg = _get_cfg()
    if base_url is None:
        base_url = cfg.get("ollama_base_url", "http://localhost:11434")
    if model is None:
        model = cfg.get("ollama_model", "llama3.2")

    payload = {"model": model, "prompt": prompt, "stream": False,
               "temperature": temperature, "num_predict": max_tokens}
    if system:
        payload["system"] = system

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url}/api/generate",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        return result.get("response", "").strip()
