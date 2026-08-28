# -*- coding: utf-8 -*-
"""
openrouter_agent.py — Delega tareas de texto a un proveedor de IA.

Proveedores (en orden):
  1. OpenRouter (cloud) — si hay openrouter_api_key
  2. Ollama (local)     — si está corriendo
  3. Gemini (ERIS key)  — fallback: usa la gemini_api_key ya configurada

Soporta generación LARGA: si la respuesta se trunca por límite de tokens,
continúa generando por secciones hasta completar el texto y lo guarda en
data/generated/ para no perder contenido.
"""
import json
import time
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
API_FILE = BASE_DIR / "config" / "api_keys.json"
SYSTEM = "Eres un Agente Especialista delegado por ERIS. Responde de forma clara y directa en español."
try:
    from core.model_config import get_model as _get_model
    GEMINI_MODEL = _get_model("agent")
except Exception:
    GEMINI_MODEL = "gemini-flash-latest"

_ollama_cache = {"t": 0.0, "ok": False}


def _read_config() -> dict:
    if not API_FILE.exists():
        return {}
    try:
        return json.loads(API_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _get_api_key() -> str:
    return _read_config().get("openrouter_api_key", "")


def _get_gemini_key() -> str:
    return _read_config().get("gemini_api_key", "")


def _get_ollama_cfg() -> dict:
    data = _read_config()
    return {
        "base_url": data.get("ollama_base_url", "http://localhost:11434"),
        "model": data.get("ollama_model", "qwen3:8b"),
    }


def _ollama_available() -> bool:
    """Caché de 10s para no penalizar cada llamada si Ollama está caído."""
    now = time.time()
    if now - _ollama_cache["t"] < 10:
        return _ollama_cache["ok"]
    cfg = _get_ollama_cfg()
    try:
        req = urllib.request.Request(f"{cfg['base_url']}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            ok = resp.status == 200
    except Exception:
        ok = False
    _ollama_cache.update(t=now, ok=ok)
    return ok


def _chat_with_openrouter(query: str, model: str, max_tokens: int = 8192) -> tuple[str, bool]:
    """OpenRouter cloud. Devuelve (texto, truncado_por_longitud)."""
    api_key = _get_api_key()
    if not api_key:
        return "", False
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://github.com/eris-beta",
        "X-Title": "ERIS AI Assistant",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": query},
        ],
    }
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                     headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if "choices" in data and data["choices"]:
            content = data["choices"][0]["message"].get("content", "")
            fr = (data["choices"][0].get("finish_reason") or "").lower()
            return content, (fr == "length")
    except Exception:
        pass
    return "", False


def _chat_with_ollama(query: str, max_tokens: int = 8192) -> tuple[str, bool]:
    """Ollama local. Devuelve (texto, truncado_por_longitud)."""
    cfg = _get_ollama_cfg()
    if not _ollama_available():
        return "", False
    payload = {
        "model": cfg["model"],
        "prompt": query,
        "system": SYSTEM,
        "stream": False,
        "options": {
            "num_predict": max_tokens,
            "temperature": 0.3,
        },
    }
    try:
        req = urllib.request.Request(
            f"{cfg['base_url']}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        text = data.get("response", "")
        done_reason = data.get("done_reason", "")
        return text, (done_reason == "length")
    except Exception:
        return "", False


def _chat_with_gemini(query: str, max_tokens: int = 8192) -> tuple[str, bool]:
    """Gemini directo con la key de ERIS. Devuelve (texto, truncado_por_longitud)."""
    key = _get_gemini_key()
    if not key:
        return "", False
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={key}"
    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM}]},
        "contents": [{"role": "user", "parts": [{"text": query}]}],
        "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.7},
    }
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                     headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        cand = data["candidates"][0]
        text = "".join(p.get("text", "") for p in cand["content"]["parts"])
        fr = (cand.get("finishReason") or "").upper()
        return text, (fr == "MAX_TOKENS")
    except Exception:
        return "", False


def _chat(query: str, model: str) -> tuple[str, bool]:
    """Prueba proveedores en orden; devuelve la primera respuesta no vacía."""
    if _get_api_key():
        text, truncated = _chat_with_openrouter(query, model)
        if text:
            return text, truncated
    if _ollama_available():
        text, truncated = _chat_with_ollama(query)
        if text:
            return text, truncated
    text, truncated = _chat_with_gemini(query)
    return text, truncated


def _save_text(text: str, tag: str) -> Path:
    out = BASE_DIR / "data" / "generated"
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{tag}_{int(time.time())}.txt"
    path.write_text(text, encoding="utf-8")
    return path


def openrouter_agent(query: str = None, model: str = "google/gemini-2.5-flash",
                     target_chars: int = 30000, max_rounds: int = 12,
                     save_long: bool = True, parameters: dict = None,
                     player=None) -> str:
    if query is None:
        query = parameters.get("query", "")
    if not query:
        return "Error: se requiere 'query'."
    """
    Delega una tarea de texto compleja.

    Genera por secciones: si el proveedor responde hasta su límite de tokens
    (truncado), continúa con "sigue desde donde quedaste" hasta alcanzar
    target_chars o que el proveedor termine naturalmente.

    Si el resultado es largo (>2500 caracteres) y save_long=True, se guarda
    en data/generated/ y se devuelve la ruta + extracto inicial.
    """
    parts: list[str] = []
    q = query
    for _ in range(max_rounds):
        text, truncated = _chat(q, model)
        if not text:
            if not parts:
                return ("No hay ningún proveedor de IA disponible "
                        "(OpenRouter sin API key, Ollama no corriendo, Gemini sin API key).")
            break
        parts.append(text)
        total = sum(len(p) for p in parts)
        if not truncated or total >= target_chars:
            break
        q = (f"Continúa el texto EXACTAMENTE donde terminó, SIN repetir nada anterior. "
             f"Última frase del texto: \"{text[-160:]}\"\n\nContinúa:")

    result = "\n\n".join(parts)
    if save_long and len(result) > 2500:
        path = _save_text(result, "agente")
        words = len(result.split())
        return (f"Texto generado y guardado en: {path} "
                f"({len(result)} caracteres, ~{words} palabras). "
                f"Extracto del inicio:\n{result[:1200]}")
    return result
