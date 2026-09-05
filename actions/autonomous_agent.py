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
    except (json.JSONDecodeError, OSError):
        return ""

def _get_openrouter_key():
    try:
        data = json.loads(API_FILE.read_text("utf-8"))
        return data.get("openrouter_api_key", "")
    except (json.JSONDecodeError, OSError):
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

def capture_region_b64(left: int, top: int, width: int, height: int) -> str:
    """Captura SOLO la región indicada (píxeles de pantalla), recortada contra
    el monitor que la contiene. Resize a máx 1024."""
    try:
        from mss import mss
        from PIL import Image
        if width <= 0 or height <= 0:
            return "Error captura: región inválida"
        with mss() as sct:
            monitors = sct.monitors
            target = monitors[0]  # fallback: todas las pantallas
            cx, cy = left + int(width / 2), top + int(height / 2)
            for mon in monitors[1:]:
                if (mon["left"] <= cx < mon["left"] + mon["width"]
                        and mon["top"] <= cy < mon["top"] + mon["height"]):
                    target = mon
                    break
            clip_l = max(left, target["left"])
            clip_t = max(top, target["top"])
            clip_r = min(left + width, target["left"] + target["width"])
            clip_b = min(top + height, target["top"] + target["height"])
            if clip_r <= clip_l or clip_b <= clip_t:
                return "Error captura: ventana fuera de pantalla"
            region = {"left": clip_l, "top": clip_t,
                      "width": clip_r - clip_l, "height": clip_b - clip_t}
            raw = sct.grab(region)
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

def _screen_prompt(action: str, target: str, hint: str = "") -> str:
    if action == "read_text":
        return ("Lee TODO el texto visible en esta captura de ventana. "
                + (f"Es la ventana «{hint}». " if hint else "")
                + "Transcribí cada palabra/código, organizado por secciones.")
    if action == "find_cursor":
        return f"Necesito saber EXACTAMENTE donde hacer clic para: {target}. Dame coordenadas aproximadas."
    if action == "document_layout":
        return "Analiza el layout de este documento. Titulos, parrafos, estructura."
    if action == "what_changed":
        return "Describe que ves en la pantalla. Aplicaciones, ventanas, elementos."
    return ("Describe EXACTAMENTE lo que se ve en esta captura de ventana del usuario. "
            + (f"Es la ventana «{hint}». " if hint else "")
            + "¿Qué aplicación/archivo/texto/código se ve? ¿Hay errores o algo destacable? Conciso.")

def screen_see_image(image_b64: str, action: str = "see", target: str = "",
                     hint: str = "") -> str:
    """Mismo análisis que screen_see pero sobre una imagen ya capturada."""
    prompt = _screen_prompt(action, target, hint)
    result = _analyze_with_gemini(image_b64, prompt)
    if result:
        return result
    result = _analyze_with_openrouter(image_b64, prompt)
    if result:
        return result
    return "Error: No se pudo analizar la imagen. Verificá las API keys."

def _analyze_with_gemini(b64_image: str, prompt: str) -> str:
    """Analiza imagen usando Gemini directo (sin OpenRouter)."""
    import urllib.request, urllib.error
    gemini_key = _get_gemini_key()
    if not gemini_key:
        return ""
    models = ["gemini-2.5-flash", "gemini-flash-latest", "gemini-2.5-flash-lite"]
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
    action = parameters.get("action", "see")
    target = parameters.get("target", "")
    
    b64 = capture_screen_b64()
    if b64.startswith("Error"):
        return b64
    return screen_see_image(b64, action, target)

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
