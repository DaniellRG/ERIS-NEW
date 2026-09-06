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

def _get_vision_mode() -> str:
    """Modo de vision desde config: 'local_first' (Ollama minicpm-v primero) o 'cloud'."""
    try:
        data = json.loads(API_FILE.read_text(encoding="utf-8"))
        return data.get("vision_mode", "local_first").lower()
    except Exception:
        return "local_first"

def _get_openrouter_model() -> str:
    """Modelo de vision configurable via openrouter_model (fallback gemini-2.5-pro)."""
    try:
        data = json.loads(API_FILE.read_text(encoding="utf-8"))
        model = data.get("openrouter_model", "google/gemini-2.5-pro")
        # Si el modelo configurado no es de vision, usar el de vision potente
        if "instruct" in model or "mini" in model and "gemini" not in model:
            return "google/gemini-2.5-pro"
        return model
    except Exception:
        return "google/gemini-2.5-pro"

def _capture_screen_base64() -> str:
    """
    Captura la pantalla principal, la redimensiona/comprime y la devuelve en base64.
    Wayland/Linux: grim (soporte nativo Hyprland). Windows y fallback: mss.
    """
    import os
    import subprocess
    import shutil
    img = None
    if os.name != "nt":
        grim = shutil.which("grim")
        if grim:
            try:
                r = subprocess.run([grim, "-t", "jpeg", "-q", "70", "-"],
                                   capture_output=True, timeout=15)
                if r.returncode == 0 and r.stdout:
                    img = Image.open(io.BytesIO(r.stdout))
            except Exception:
                img = None
    if img is None:
        with mss() as sct:
            monitor = sct.monitors[0]  # All monitors combined
            screenshot = sct.grab(monitor)
            img = Image.frombytes("RGB", screenshot.size, screenshot.bgra,
                                  "raw", "BGRX")
    # Redimensionar si es muy grande para ahorrar tokens/ancho de banda
    img.thumbnail((1280, 720), Image.Resampling.BILINEAR)
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=65)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")

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

    models_to_try = ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-flash-latest", "gemini-3.1-flash-lite"]
    
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
    """Analiza imagen usando OpenRouter con modelo de vision potente."""
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

    models_to_try = [_get_openrouter_model(), "google/gemini-2.5-pro", "google/gemini-2.5-flash", "qwen/qwen2.5-vl-72b-instruct"]

    for model in models_to_try:
        payload = {
            "model": model,
            "max_tokens": 1500,
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
            with urllib.request.urlopen(req, timeout=60) as response:
                data = json.loads(response.read().decode("utf-8"))
                if "choices" in data and len(data["choices"]) > 0:
                    return data["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            if e.code in (402, 429):
                continue  # sin creditos o rate limit: probar siguiente modelo
        except Exception:
            continue
    return ""

def _analyze_with_local_ocr() -> str:
    """Intenta OCR local rapido via screen_reader (Windows OCR API) para leer texto."""
    try:
        from actions.screen_reader import screen_reader
        result = screen_reader({"action": "read_screen"})
        if result and "sin OCR" not in result.lower() and "no disponible" not in result.lower():
            return result
    except Exception:
        pass
    return ""

def _vision_chain(b64_image: str, query: str) -> tuple:
    """Cadena de análisis según vision_mode.

    local_first (default): Ollama local (minicpm-v) → Gemini → OpenRouter.
    cloud:                 Gemini → OpenRouter → Ollama local.
    Devuelve (resultado, fuente) o (None, None) si todo falla.
    """
    mode = _get_vision_mode()
    if mode == "cloud":
        order = [("Gemini", _analyze_with_gemini),
                 ("OpenRouter", _analyze_with_openrouter),
                 ("Local/Ollama", _analyze_with_ollama)]
    else:
        order = [("Local/Ollama", _analyze_with_ollama),
                 ("Gemini", _analyze_with_gemini),
                 ("OpenRouter", _analyze_with_openrouter)]

    for source, fn in order:
        try:
            result = fn(b64_image, query)
        except Exception:
            continue
        if result and not str(result).startswith("Error"):
            return result, source
    return None, None


def _analyze_image_file(img_path: str, query: str, player=None) -> str:
    """Analiza un archivo de imagen local con la cadena de vision AI."""
    import os
    if not os.path.isfile(img_path):
        return f"Error: archivo no encontrado: {img_path}"
    if not query:
        query = "Describe brevemente que hay en esta imagen."
    try:
        img = Image.open(img_path)
        img.load()
    except Exception as e:
        return f"Error leyendo la imagen: {e}"

    buffer = io.BytesIO()
    try:
        img = img.convert("RGB")
        img.thumbnail((1280, 1280), Image.Resampling.BILINEAR)
        img.save(buffer, format="JPEG", quality=70)
    except Exception as e:
        return f"Error preparando la imagen: {e}"
    b64_image = base64.b64encode(buffer.getvalue()).decode("utf-8")

    if player:
        player.write_log("👁️ Analizando imagen...")
    result, source = _vision_chain(b64_image, query)
    if result:
        return f"[{source}] {result}"
    return "Error: No se pudo analizar la imagen."


def screen_vision(parameters: dict, player=None) -> str:
    """
    Toma una captura de pantalla y la analiza.
    Para lectura de texto (read) → OCR local primero (rápido).
    Para descripción general (describe) → Gemini → OpenRouter → Ollama.
    analyze_image → analiza un archivo de imagen local (path/file).
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

    if parameters.get("file") or parameters.get("path"):
        action = "analyze_image"
        img_path = parameters.get("file") or parameters.get("path")
        return _analyze_image_file(img_path, query, player)

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
        
    # Para "read": OCR local primero (rapido y sin red), luego vision AI
    if action == "read":
        local = _analyze_with_local_ocr()
        if local:
            return f"[OCR local]\n{local}"

    try:
        b64_image = _capture_screen_base64()
    except Exception as e:
        return f"Error al capturar la pantalla: {e}"

    # Cadena según vision_mode (local_first: Ollama primero)
    result, source = _vision_chain(b64_image, query)
    if result:
        if source != "Local/Ollama":
            return f"[{source}] {result}"
        return result

    return "Error: No se pudo analizar la pantalla. Verificá la API key de Gemini/OpenRouter o que Ollama esté corriendo."
