"""
Agente autonomo de ERIS — puede ver la pantalla, entender que hay,
posicionarse correctamente, y trabajar de forma independiente.
"""
import time
import base64
import io
import json
from pathlib import Path

import sys as _sys
BASE_DIR = (Path(_sys.executable).parent if getattr(_sys, "frozen", False) 
            else Path(__file__).resolve().parent.parent)
API_FILE = BASE_DIR / "config" / "api_keys.json"

def _get_gemini_key():
    try:
        data = json.loads(API_FILE.read_text("utf-8"))
        return data.get("gemini_api_key", "")
    except:
        return ""

def _get_openrouter_key():
    try:
        data = json.loads(API_FILE.read_text("utf-8"))
        return data.get("openrouter_api_key", "")
    except:
        return ""

def capture_screen_b64() -> str:
    """Captura TODAS las pantallas (multi-monitor)."""
    try:
        from mss import mss
        from PIL import Image
        with mss() as sct:
            monitor = sct.monitors[0]
            raw = sct.grab(monitor)
            img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
            w, h = img.size
            if max(w, h) > 1024:
                ratio = 1024 / max(w, h)
                img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=70)
            return base64.b64encode(buf.getvalue()).decode()
    except Exception as e:
        return f"Error captura: {e}"

def _analyze_with_gemini(b64_image: str, prompt: str) -> str:
    """Analiza imagen usando Gemini directo (sin OpenRouter)."""
    import urllib.request, urllib.error
    gemini_key = _get_gemini_key()
    if not gemini_key:
        return ""
    models = ["gemini-flash-latest", "gemini-2.0-flash", "gemini-2.0-flash-lite"]
    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={gemini_key}"
        payload = {
            "contents": [{"parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": "image/jpeg", "data": b64_image}}
            ]}],
            "generationConfig": {"maxOutputTokens": 1500, "temperature": 0.3}
        }
        try:
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                        headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=40) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if "candidates" in data and data["candidates"]:
                    parts = data["candidates"][0].get("content", {}).get("parts", [])
                    return "".join(p.get("text", "") for p in parts)
        except Exception:
            continue
    return ""

def _analyze_with_openrouter(b64_image: str, prompt: str) -> str:
    """Fallback: OpenRouter (solo si Gemini falla)."""
    import urllib.request, urllib.error
    key = _get_openrouter_key()
    if not key:
        return ""
    body = json.dumps({
        "model": "google/gemini-2.5-flash",
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"}}
        ]}],
        "max_tokens": 800
    }).encode()
    try:
        req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions",
            data=body, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())["choices"][0]["message"]["content"]
    except Exception:
        return ""

def screen_see(parameters: dict = None, player=None) -> str:
    """
    Mira la pantalla y describe que hay en ella usando vision AI.
    Acciones: see, read_text, find_cursor, document_layout, what_changed
    """
    action = (parameters or {}).get("action", "see")
    target = (parameters or {}).get("target", "")
    
    b64 = capture_screen_b64()
    if b64.startswith("Error"):
        return b64

    if action == "see":
        prompt = "Describe EXACTAMENTE lo que ves en esta pantalla. Que aplicaciones estan abiertas? Que ventanas? Que texto hay? Donde estan los elementos?"
    elif action == "read_text":
        prompt = "Lee TODO el texto visible en esta pantalla. Transcribe cada palabra, organizado por secciones."
    elif action == "find_cursor":
        prompt = f"Necesito saber EXACTAMENTE donde hacer clic para: {target}. Dame coordenadas aproximadas."
    elif action == "document_layout":
        prompt = "Analiza el layout de este documento. Titulos, parrafos, estructura."
    elif action == "what_changed":
        prompt = "Describe que ves en la pantalla. Aplicaciones, ventanas, elementos."
    else:
        prompt = "Describe lo que ves en esta pantalla de forma detallada."

    # Gemini primero
    result = _analyze_with_gemini(b64, prompt)
    if result:
        return result
    # OpenRouter fallback
    result = _analyze_with_openrouter(b64, prompt)
    if result:
        return result
    return "Error: No se pudo analizar la pantalla. Verificá las API keys."

def screen_where_to_click(target: str, player=None) -> str:
    """Encuentra donde hacer clic para un objetivo especifico."""
    return screen_see({"action": "find_cursor", "target": target}, player)

def screen_whats_there(player=None) -> str:
    """Describe que hay en la pantalla ahora mismo."""
    return screen_see({"action": "what_changed"}, player)

def screen_read_all_text(player=None) -> str:
    """Lee todo el texto visible en pantalla."""
    return screen_see({"action": "read_text"}, player)

def screen_document_structure(player=None) -> str:
    """Analiza la estructura del documento en pantalla."""
    return screen_see({"action": "document_layout"}, player)
