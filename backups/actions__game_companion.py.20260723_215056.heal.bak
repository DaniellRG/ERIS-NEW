"""
Game Companion — ERIS te ayuda a jugar.
Ve la pantalla, busca guias, detecta objetos, da consejos.
"""
import base64, io, json, urllib.request, urllib.error
from pathlib import Path

import sys
BASE_DIR = (Path(sys.executable).parent if getattr(sys, "frozen", False) 
            else Path(__file__).resolve().parent.parent)
API_FILE = BASE_DIR / "config" / "api_keys.json"

def _get_key():
    if API_FILE.exists():
        try: return json.loads(API_FILE.read_text("utf-8")).get("openrouter_api_key", "")
        except: pass
    # Fallback: try relative to cwd
    alt = Path("config/api_keys.json")
    if alt.exists():
        try: return json.loads(alt.read_text("utf-8")).get("openrouter_api_key", "")
        except: pass
    return ""

def _capture() -> str:
    try:
        from mss import mss
        from PIL import Image
        with mss() as sct:
            monitor = sct.monitors[0]  # All monitors
            img = Image.frombytes("RGB", sct.grab(monitor).size, sct.grab(monitor).bgra, "raw", "BGRX")
            w, h = img.size
            if max(w, h) > 1024:
                ratio = 1024 / max(w, h)
                img = img.resize((int(w*ratio), int(h*ratio)), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=70)
            return base64.b64encode(buf.getvalue()).decode()
    except Exception as e:
        return f"ERROR:{e}"

def _ask_vision(prompt: str) -> str:
    b64 = _capture()
    if b64.startswith("ERROR:"):
        return f"No se pudo capturar pantalla: {b64}"
    key = _get_key()
    if not key:
        return "Error: No hay API key de OpenRouter para vision."
    try:
        body = json.dumps({
            "model": "google/gemini-2.5-flash",
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
            ]}],
            "max_tokens": 600
        }).encode()
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions",
            data=body,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Error vision: {e}"

def game_companion(parameters: dict, player=None) -> str:
    """Companero de juegos. Analiza pantalla y ayuda."""
    action = parameters.get("action", "analyze")
    game = parameters.get("game", "")
    question = parameters.get("question", "")
    
    if action == "analyze":
        prompt = "Mira esta pantalla de videojuego. Describe: 1) Que juego es? 2) Que esta pasando? 3) Que deberia hacer el jugador ahora? 4) Hay enemigos, objetos, o peligros visibles? 5) Alguna UI importante (vida, minimapa, misiones)? Responde en espanol de forma util y directa."
        return _ask_vision(prompt)
    
    elif action == "guide":
        if not game:
            return "Dime que juego es para buscar guia."
        prompt = f"Estoy jugando {game}. Busca en internet una guia o consejos utiles para este juego. Dame los mejores tips."
        try:
            import urllib.request as _ur, json as _j
            q = _ur.quote(f"{game} guia consejos tips")
            r = _ur.Request(f"https://www.google.com/search?q={q}", headers={"User-Agent": "Mozilla/5.0"})
            with _ur.urlopen(r, timeout=10) as resp:
                return f"Busca en Google: {game} guia consejos tips"
        except:
            return f"Busca en internet: {game} guia tips trucos"
    
    elif action == "spot":
        target = parameters.get("target", "enemigos")
        prompt = f"Analiza esta pantalla de juego y dime EXACTAMENTE donde estan los {target}. Coordenadas aproximadas, posicion en pantalla (arriba, abajo, izquierda, derecha, centro). Responde en espanol."
        return _ask_vision(prompt)
    
    elif action == "help":
        prompt = "Mira esta pantalla de juego. El jugador esta atascado. Que deberia hacer? Hay alguna pista, objeto, puerta, o camino que no este viendo? Analiza profundo y da consejos especificos. Responde en espanol."
        return _ask_vision(prompt)
    
    elif action == "loot":
        prompt = "Analiza esta pantalla de juego. Enumera TODO el loot, items, objetos, cofres, o cosas interactuables visibles. Donde estan? Vale la pena recogerlos? Responde en espanol."
        return _ask_vision(prompt)
    
    elif action == "danger":
        prompt = "Analiza esta pantalla de juego. Identifica TODOS los peligros: enemigos, trampas, zonas de dano, obstaculos. Que tan peligrosa es la situacion? Que deberia hacer el jugador para sobrevivir? Responde en espanol."
        return _ask_vision(prompt)
    
    elif action == "map":
        prompt = "Mira esta pantalla. Si hay un minimapa o mapa visible, describelo. Si no, describe el entorno: donde esta el jugador, que direcciones puede tomar, hay caminos ocultos? Responde en espanol."
        return _ask_vision(prompt)
    
    else:
        return f"Accion '{action}' no reconocida. Usa: analyze, guide, spot, help, loot, danger, map"
