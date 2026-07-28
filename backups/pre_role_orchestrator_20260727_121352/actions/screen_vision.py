import json
import base64
import urllib.request
import urllib.error
from pathlib import Path
from mss import mss
from PIL import Image
import io

# Resolve config relative to this script's location
API_FILE = Path(__file__).resolve().parent.parent / "config" / "api_keys.json"

def _get_api_key() -> str:
    try:
        data = json.loads(API_FILE.read_text(encoding="utf-8"))
        return data.get("openrouter_api_key", "")
    except Exception:
        return ""

def _get_gemini_key() -> str:
    try:
        data = json.loads(API_FILE.read_text(encoding="utf-8"))
        return data.get("gemini_api_key", "")
    except Exception:
        return ""

def _get_ollama_cfg() -> dict:
    try:
        data = json.loads(API_FILE.read_text(encoding="utf-8"))
        return {
            "base_url": data.get("ollama_base_url", "http://localhost:11434"),
            "vision_model": data.get("ollama_vision_model", "minicpm-v"),
        }
    except Exception:
        return {"base_url": "http://localhost:11434", "vision_model": "minicpm-v"}

def _capture_screen_base64() -> str:
    """
    Captura la pantalla principal, la redimensiona/comprime y la devuelve en base64.
    """
    with mss() as sct:
        monitor = sct.monitors[0] # All monitors combined
        screenshot = sct.grab(monitor)
        
        # Convertir a imagen de Pillow
        img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
        
        # Redimensionar si es muy grande para ahorrar tokens/ancho de banda
        max_size = (1280, 720)
        img.thumbnail(max_size, Image.Resampling.BILINEAR)
        
        # Guardar en buffer en memoria como JPEG
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=65)
        
        # Codificar a base64
        img_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return img_b64

def _analyze_with_ollama(b64_image: str, query: str) -> str:
    """Analiza imagen usando Ollama local (sin internet)."""
    cfg = _get_ollama_cfg()
    base_url = cfg["base_url"]
    model = cfg["vision_model"]

    # Check if Ollama is available
    try:
        req = urllib.request.Request(f"{base_url}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            if resp.status != 200:
                return ""
    except Exception:
        return ""

    # Check if vision model is available
    try:
        req = urllib.request.Request(f"{base_url}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            tags = json.loads(resp.read().decode("utf-8"))
            available = [m.get("name", "") for m in tags.get("models", [])]
            # Match model name (e.g. "minicpm-v" matches "minicpm-v:latest")
            model_found = any(model in m for m in available)
            if not model_found:
                print(f"[ScreenVision] Ollama vision model '{model}' not found. Available: {available}")
                return ""
    except Exception:
        return ""

    payload = {
        "model": model,
        "prompt": f"Esta es una captura de mi pantalla. {query}",
        "images": [b64_image],
        "stream": False,
        "options": {
            "num_predict": 1500,
            "temperature": 0.3,
        }
    }

    try:
        req = urllib.request.Request(
            f"{base_url}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=120) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data.get("response", "")
    except Exception as e:
        print(f"[ScreenVision] Ollama error: {e}")
        return ""

def _analyze_with_gemini(b64_image: str, query: str) -> str:
    """Analiza imagen usando Gemini directamente (sin OpenRouter)."""
    gemini_key = _get_gemini_key()
    if not gemini_key:
        return ""
    
    models_to_try = ["gemini-flash-latest", "gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-pro-latest"]
    
    for model in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={gemini_key}"
        
        payload = {
            "contents": [{
                "parts": [
                    {"text": f"Esta es una captura de mi pantalla. {query}"},
                    {"inline_data": {"mime_type": "image/jpeg", "data": b64_image}}
                ]
            }],
            "generationConfig": {
                "maxOutputTokens": 1500,
                "temperature": 0.3
            }
        }
        
        try:
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=40) as response:
                data = json.loads(response.read().decode("utf-8"))
                if "candidates" in data and len(data["candidates"]) > 0:
                    parts = data["candidates"][0].get("content", {}).get("parts", [])
                    return "".join(p.get("text", "") for p in parts)
                return ""
        except urllib.error.HTTPError as e:
            if e.code == 429:
                continue  # Rate limited, try next model
            continue
        except Exception:
            continue
    
    return ""

def _analyze_with_openrouter(b64_image: str, query: str) -> str:
    """Analiza imagen usando OpenRouter (fallback)."""
    api_key = _get_api_key()
    if not api_key:
        return ""
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://github.com/eris-beta",
        "X-Title": "ERIS AI Assistant",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "google/gemini-2.5-flash",
        "max_tokens": 800,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"Esta es una captura de mi pantalla. {query}"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"}}
                ]
            }
        ]
    }
    
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=40) as response:
            data = json.loads(response.read().decode("utf-8"))
            if "choices" in data and len(data["choices"]) > 0:
                return data["choices"][0]["message"]["content"]
        return ""
    except Exception:
        return ""

def screen_vision(parameters: dict, player=None) -> str:
    """
    Toma una captura de pantalla y la analiza.
    Para lectura de texto (read) → Gemini primero (mejor OCR, más rápido).
    Para descripción general (describe) → Ollama primero (sin internet).
    """
    query = (
        parameters.get("query")
        or parameters.get("text")
        or parameters.get("question")
        or parameters.get("description")
        or parameters.get("prompt")
    )
    # Handle action-based calls (e.g. from Gemini Live: {"action": "describe", "monitor": 0})
    action = "describe"
    if not query:
        action = parameters.get("action", "describe")
        if action in ("describe", "analyze", "look", "screen"):
            query = "Describe brevemente que ves en esta pantalla."
        elif action == "read":
            query = "Lee y transcribe TODO el texto visible en esta pantalla exactamente como aparece. No omitas nada."
        elif action == "find":
            query = parameters.get("target") or parameters.get("element") or "Que hay en la pantalla?"
        else:
            query = "Describe brevemente que ves en esta pantalla."
    else:
        action = "custom"

    if player:
        player.write_log("👁️ Capturando pantalla...")
        
    try:
        b64_image = _capture_screen_base64()
    except Exception as e:
        return f"Error al capturar la pantalla: {e}"
    
    # Gemini primero para TODAS las acciones (más confiable que Ollama)
    result = _analyze_with_gemini(b64_image, query)
    if result and not result.startswith("Error"):
        return result
    
    # Fallback a Ollama
    result = _analyze_with_ollama(b64_image, query)
    if result:
        return f"[Local/Ollama] {result}"
    
    # OpenRouter deshabilitado (HTTP 402 sin créditos)
    
    return "Error: No se pudo analizar la pantalla. Verificá la API key de Gemini o que Ollama esté corriendo."
