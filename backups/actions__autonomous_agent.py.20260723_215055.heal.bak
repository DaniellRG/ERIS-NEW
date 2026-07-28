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

def _get_key():
    if not API_FILE.exists():
        # Fallback: try relative to cwd
        alt = Path("config/api_keys.json")
        if alt.exists():
            try: return json.loads(alt.read_text("utf-8")).get("openrouter_api_key", "")
            except: pass
        return ""
    try:
        return json.loads(API_FILE.read_text("utf-8")).get("openrouter_api_key", "")
    except:
        return ""

def capture_screen_b64() -> str:
    """Captura TODAS las pantallas (multi-monitor)."""
    try:
        from mss import mss
        from PIL import Image
        with mss() as sct:
            # monitor 0 = all monitors combined
            monitor = sct.monitors[0]
            img = Image.frombytes("RGB", sct.grab(monitor).size, sct.grab(monitor).bgra, "raw", "BGRX")
            w, h = img.size
            if max(w, h) > 1024:
                ratio = 1024 / max(w, h)
                img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=70)
            return base64.b64encode(buf.getvalue()).decode()
    except Exception as e:
        return f"Error captura: {e}"

def screen_see(parameters: dict = None, player=None) -> str:
    """
    Mira la pantalla y describe que hay en ella usando vision AI.
    Acciones: see (describir pantalla), read_text (leer texto visible),
    find_position (encontrar donde colocar cursor), document_layout (analizar layout)
    """
    action = (parameters or {}).get("action", "see")
    target = (parameters or {}).get("target", "")
    
    b64 = capture_screen_b64()
    if b64.startswith("Error"):
        return b64
    
    key = _get_key()
    if not key:
        return "Error: No hay API key de OpenRouter para vision."

    if action == "see":
        prompt = "Describe EXACTAMENTE lo que ves en esta pantalla. Que aplicaciones estan abiertas? Que ventanas? Que texto hay? Donde estan los elementos? Se especifico."
    elif action == "read_text":
        prompt = "Lee TODO el texto visible en esta pantalla. Transcribe cada palabra que veas, organizado por secciones. Incluye titulos, parrafos, botones, menus."
    elif action == "find_cursor":
        prompt = f"Necesito saber EXACTAMENTE donde hacer clic para: {target}. Dame las coordenadas aproximadas y describe la posicion relativa en la pantalla."
    elif action == "document_layout":
        prompt = "Analiza el layout de este documento. Donde estan los titulos? Los parrafos? Hay espacio para escribir? Donde insertarias texto nuevo? Que estructura tiene?"
    elif action == "what_changed":
        prompt = "Describe que ves en la pantalla. Que aplicaciones, ventanas, o elementos hay? Que esta pasando?"
    else:
        prompt = "Describe lo que ves en esta pantalla de forma detallada."

    try:
        import urllib.request, urllib.error
        body = json.dumps({
            "model": "google/gemini-2.5-flash",
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
                ]
            }],
            "max_tokens": 800
        }).encode()
        
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions",
            data=body,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Error vision: {e}"

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
