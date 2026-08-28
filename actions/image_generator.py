# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_OUTPUT_DIR = _BASE / "data" / "generated_images"
_HISTORY_FILE = _BASE / "data" / "image_gen_history.json"
_CONFIG_FILE = _BASE / "config" / "api_keys.json"

STYLES = {
    "photorealistic": "photorealistic, high detail, 8k, sharp focus",
    "anime": "anime style, vibrant colors, detailed illustration",
    "digital_art": "digital art, concept art, highly detailed",
    "painting": "oil painting, masterpiece, detailed brushstrokes",
}


def _ensure_dirs():
    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _load_history() -> list:
    if _HISTORY_FILE.exists():
        try:
            return json.loads(_HISTORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def _save_history(history: list):
    _ensure_dirs()
    _HISTORY_FILE.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")


def _load_config() -> dict:
    if _CONFIG_FILE.exists():
        try:
            return json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _style_prompt(prompt: str, style: str) -> str:
    suffix = STYLES.get(style, "")
    if suffix:
        return f"{prompt}, {suffix}"
    return prompt


def _download_image(url: str, save_path: Path) -> str | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ErisAI/1.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
        if len(data) < 1000:
            return None
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_bytes(data)
        return str(save_path)
    except Exception:
        return None


def _pollinations_generate(prompt: str, width: int, height: int, seed: int | None) -> str | None:
    encoded = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded}?width={width}&height={height}"
    if seed is not None:
        url += f"&seed={seed}"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    h = hashlib.md5(prompt.encode()).hexdigest()[:8]
    filename = f"{ts}_{h}.png"
    return _download_image(url, _OUTPUT_DIR / filename)


def _sd_api_generate(prompt: str, width: int, height: int, seed: int | None) -> str | None:
    config = _load_config()
    api_url = config.get("sd_api_url", "")
    if not api_url:
        return None
    payload = {
        "prompt": prompt,
        "width": width,
        "height": height,
        "steps": 30,
        "cfg_scale": 7.0,
    }
    if seed is not None:
        payload["seed"] = seed
    try:
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            api_url, data=body,
            headers={"Content-Type": "application/json", "User-Agent": "ErisAI/1.0"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = resp.read()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        h = hashlib.md5(prompt.encode()).hexdigest()[:8]
        filename = f"{ts}_{h}.png"
        save_path = _OUTPUT_DIR / filename
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_bytes(result)
        return str(save_path)
    except Exception:
        return None


def _action_generate(params: dict) -> str:
    prompt = params.get("prompt", "").strip()
    if not prompt:
        return "Error: se requiere 'prompt'"

    style = params.get("style", "photorealistic").strip().lower()
    width = min(max(int(params.get("width", 512)), 64), 2048)
    height = min(max(int(params.get("height", 512)), 64), 2048)
    seed = None
    if "seed" in params and params["seed"] is not None:
        try:
            seed = int(params["seed"])
        except (TypeError, ValueError):
            seed = None

    full_prompt = _style_prompt(prompt, style)
    _ensure_dirs()

    path = _pollinations_generate(full_prompt, width, height, seed)
    backend = "pollinations"

    if not path:
        path = _sd_api_generate(full_prompt, width, height, seed)
        backend = "sd_api"

    if not path:
        return "Error: no se pudo generar la imagen con ningún backend disponible"

    size_kb = Path(path).stat().st_size / 1024
    entry = {
        "prompt": prompt,
        "full_prompt": full_prompt,
        "style": style,
        "width": width,
        "height": height,
        "seed": seed,
        "backend": backend,
        "path": path,
        "timestamp": datetime.now().isoformat(),
        "size_kb": round(size_kb, 1),
    }
    history = _load_history()
    history.insert(0, entry)
    if len(history) > 200:
        history = history[:200]
    _save_history(history)

    return "Imagen generada ({:.0f} KB): {}\nPrompt: {}\nEstilo: {} | {}x{} | Backend: {}".format(
        size_kb, path, prompt, style, width, height, backend
    )


def _action_from_url(params: dict) -> str:
    url = params.get("url", "").strip()
    if not url:
        return "Error: se requiere 'url'"

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    h = hashlib.md5(url.encode()).hexdigest()[:8]
    ext = ".png"
    lower = url.lower()
    if ".jpg" in lower or ".jpeg" in lower:
        ext = ".jpg"
    elif ".webp" in lower:
        ext = ".webp"
    filename = f"fromurl_{ts}_{h}{ext}"

    path = _download_image(url, _OUTPUT_DIR / filename)
    if not path:
        return "Error: no se pudo descargar la imagen desde la URL"

    size_kb = Path(path).stat().st_size / 1024
    entry = {
        "prompt": f"[descargada de URL] {url}",
        "full_prompt": url,
        "style": "url_download",
        "width": 0,
        "height": 0,
        "seed": None,
        "backend": "url_download",
        "path": path,
        "timestamp": datetime.now().isoformat(),
        "size_kb": round(size_kb, 1),
    }
    history = _load_history()
    history.insert(0, entry)
    if len(history) > 200:
        history = history[:200]
    _save_history(history)

    return "Imagen descargada ({:.0f} KB): {}".format(size_kb, path)


def _action_info(_params: dict) -> str:
    config = _load_config()
    sd_configured = bool(config.get("sd_api_url", ""))

    lines = [
        "Backends de generación de imágenes:",
        "  1. Pollinations.ai — GRATIS, sin API key",
        "     Estado: activo",
        "  2. Stable Diffusion API — {}".format("configurado" if sd_configured else "no configurado"),
    ]
    if not sd_configured:
        lines.append("     Configurar en config/api_keys.json → \"sd_api_url\"")

    lines.append("")
    lines.append("Estilos disponibles: {}".format(", ".join(STYLES.keys())))
    lines.append("Resolución: 64-2048px (default: 512x512)")
    lines.append("Imágenes generadas: {}".format(len(_load_history())))
    return "\n".join(lines)


def _action_history(params: dict) -> str:
    history = _load_history()
    if not history:
        return "Sin historial de generación"

    limit = int(params.get("limit", 10))
    lines = ["Historial de generación ({} total, mostrando {}):".format(len(history), min(limit, len(history)))]

    for i, entry in enumerate(history[:limit]):
        preview = entry.get("prompt", "")[:60]
        ts = entry.get("timestamp", "?")[:16]
        backend = entry.get("backend", "?")
        size = entry.get("size_kb", 0)
        lines.append("  {}. [{}] {} | {} KB | {}".format(i + 1, ts, preview, size, backend))

    return "\n".join(lines)


def image_generator(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = params.get("action", "generate").lower()

    if action == "generate":
        return _action_generate(params)
    elif action == "from_url":
        return _action_from_url(params)
    elif action == "info":
        return _action_info(params)
    elif action == "history":
        return _action_history(params)
    return "Acciones: generate, from_url, info, history"
