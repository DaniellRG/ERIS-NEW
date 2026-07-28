"""
Game Agent - ERIS juega por ti.
Controla personaje, explora, pelea, navega mapas.
"""
import base64, io, json, time, random, urllib.request, urllib.error
from pathlib import Path
import sys as _sys

BASE_DIR = (Path(_sys.executable).parent if getattr(_sys, "frozen", False)
            else Path(__file__).resolve().parent.parent)
API_FILE = BASE_DIR / "config" / "api_keys.json"

def _key():
    if API_FILE.exists():
        try: return json.loads(API_FILE.read_text("utf-8")).get("openrouter_api_key", "")
        except: pass
    alt = Path("config/api_keys.json")
    if alt.exists():
        try: return json.loads(alt.read_text("utf-8")).get("openrouter_api_key", "")
        except: pass
    return ""

def _capture():
    try:
        from mss import mss
        from PIL import Image
        with mss() as sct:
            monitor = sct.monitors[0]  # All monitors
            img = Image.frombytes("RGB", sct.grab(monitor).size, sct.grab(monitor).bgra, "raw", "BGRX")
            w, h = img.size
            if max(w, h) > 900:
                ratio = 900 / max(w, h)
                img = img.resize((int(w*ratio), int(h*ratio)), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=65)
            return base64.b64encode(buf.getvalue()).decode()
    except:
        return ""

def _ask(prompt: str) -> str:
    b64 = _capture()
    if not b64: return "No se pudo capturar pantalla."
    k = _key()
    if not k: return "No hay API key de OpenRouter."
    try:
        body = json.dumps({
            "model": "google/gemini-2.5-flash",
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
            ]}],
            "max_tokens": 400
        }).encode()
        req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions",
            data=body, headers={"Authorization": f"Bearer {k}", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Vision error: {e}"

import pyautogui
import pygetwindow as gw

def _focus_game():
    """Find and focus the game window."""
    game_kw = ["Sons", "Forest", "Steam", "game", "Game", "Valheim", "Minecraft", "Elden", "Dark Souls", "Cyberpunk"]
    for win in gw.getAllWindows():
        t = win.title.strip()
        if t and any(kw.lower() in t.lower() for kw in game_kw):
            try:
                if win.isMinimized: win.restore()
                win.activate()
                time.sleep(0.3)
                return True
            except: pass
    return False

# Game controls
def _move(direction: str, duration: float = 0.5):
    """Move character with WASD."""
    key = {"forward": "w", "back": "s", "left": "a", "right": "d",
           "w": "w", "s": "s", "a": "a", "d": "d"}.get(direction.lower(), direction.lower())
    pyautogui.keyDown(key)
    time.sleep(duration)
    pyautogui.keyUp(key)

def _look(dx: int = 0, dy: int = 0):
    """Move mouse to look around."""
    if dx or dy:
        pyautogui.moveRel(dx, dy, duration=0.2)

def _jump():
    pyautogui.press('space')

def _interact():
    pyautogui.press('e')

def _attack():
    pyautogui.click()

def _inventory():
    pyautogui.press('tab')

def _sprint():
    pyautogui.keyDown('shift')
    time.sleep(0.3)

def _crouch():
    pyautogui.press('ctrl')

def _action_from_text(text: str) -> str:
    """Parse AI response and execute game actions."""
    text_lower = text.lower()
    executed = []
    
    # Movement
    if "avanzar" in text_lower or "adelante" in text_lower or "forward" in text_lower:
        _move("w", 0.4); executed.append("avanzar")
    if "retroceder" in text_lower or "atras" in text_lower or "back" in text_lower:
        _move("s", 0.4); executed.append("retroceder")
    if "izquierda" in text_lower or "left" in text_lower:
        _move("a", 0.3); executed.append("izquierda")
    if "derecha" in text_lower or "right" in text_lower:
        _move("d", 0.3); executed.append("derecha")
    
    # Camera
    if "mirar arriba" in text_lower:
        _look(0, -80); executed.append("mirar arriba")
    if "mirar abajo" in text_lower:
        _look(0, 80); executed.append("mirar abajo")
    if "mirar izquierda" in text_lower or "girar izquierda" in text_lower:
        _look(-150, 0); executed.append("girar izquierda")
    if "mirar derecha" in text_lower or "girar derecha" in text_lower:
        _look(150, 0); executed.append("girar derecha")
    
    # Actions
    if "saltar" in text_lower or "jump" in text_lower:
        _jump(); executed.append("saltar")
    if "interactuar" in text_lower or "abrir" in text_lower or "recoger" in text_lower:
        _interact(); executed.append("interactuar")
    if "atacar" in text_lower or "golpear" in text_lower or "attack" in text_lower:
        _attack(); executed.append("atacar")
    if "inventario" in text_lower or "inventory" in text_lower:
        _inventory(); executed.append("inventario")
    if "correr" in text_lower or "sprint" in text_lower:
        _sprint(); executed.append("correr")
    if "agachar" in text_lower or "crouch" in text_lower:
        _crouch(); executed.append("agachar")
    
    return f"Ejecutado: {', '.join(executed)}" if executed else "Sin acciones ejecutadas."


def game_agent(parameters: dict, player=None) -> str:
    """Agente autonomo de juego. Controla personaje, explora, pelea."""
    action = parameters.get("action", "analyze")
    game = parameters.get("game", "")
    instructions = parameters.get("instructions", "")
    steps = int(parameters.get("steps", 1))
    
    _focus_game()
    
    if action == "analyze":
        return _ask(
            "Eres un asistente de videojuegos. Mira esta pantalla y describe en espanol: "
            "1) Que juego es? 2) Que ve el jugador? 3) Hay enemigos, objetos, peligros? "
            "4) Que deberia hacer el jugador AHORA? 5) Hay UI visible (vida, mapa, misiones)? "
            "Responde de forma directa y practica."
        )
    
    elif action == "play":
        if not instructions:
            return "Dime que quieres que haga (instructions). Ej: 'explora hacia adelante', 'busca enemigos', 'recoge loot'."
        
        for step in range(steps):
            if player: player.write_log(f"Game Agent: paso {step+1}/{steps}")
            analysis = _ask(
                f"Mira esta pantalla de juego. Instruccion del jugador: '{instructions}'. "
                "Responde SOLO con acciones que puedas ejecutar. Una accion por linea. Maximo 3 acciones. "
                "Acciones disponibles: avanzar, retroceder, izquierda, derecha, mirar arriba, mirar abajo, "
                "girar izquierda, girar derecha, saltar, interactuar, atacar, inventario, correr, agachar. "
                "Ejemplo: 'girar derecha, avanzar, atacar'. Responde en espanol."
            )
            result = _action_from_text(analysis)
            if player: player.write_log(f"  {result}")
            time.sleep(0.3)
        
        return f"Jugado {steps} pasos. Instruccion: {instructions}"
    
    elif action == "look_around":
        for angle in range(0, 360, 90):
            _look(200, 0)
            time.sleep(0.4)
        analysis = _ask("Describe lo que ves ahora despues de girar 360 grados. Hay enemigos? Objetos? Caminos?")
        return "Mirada 360. " + analysis
    
    elif action == "explore":
        for s in range(min(steps, 10)):
            _move("w", 0.6)
            time.sleep(0.3)
            if s % 3 == 0:
                _look(-100, 0)
                time.sleep(0.2)
                _look(100, 0)
        return f"Explorado {min(steps, 10)} pasos hacia adelante."
    
    elif action == "fight":
        for s in range(min(steps, 5)):
            _attack()
            time.sleep(0.2)
            _move("w", 0.3)
            _attack()
            time.sleep(0.3)
        return f"Atacado {min(steps, 5)} rondas."
    
    elif action == "find":
        target = parameters.get("target", "objetos")
        return _ask(
            f"Busca en esta pantalla: {target}. Donde estan? Como llegar? "
            "Responde con ubicacion exacta y acciones para alcanzarlos. En espanol."
        )
    
    elif action == "navigate":
        destination = parameters.get("destination", "")
        if not destination:
            return "Dime a donde quieres ir (destination)."
        analysis = _ask(
            f"El jugador quiere ir a: {destination}. Mira la pantalla. "
            "Como puede llegar? Que direccion debe tomar? Hay obstaculos? "
            "Responde con direcciones concretas (norte, sur, este, oeste) y acciones. En espanol."
        )
        _action_from_text(analysis)
        steps_taken = min(steps, 5)
        for s in range(steps_taken):
            _move("w", 0.5)
            time.sleep(0.2)
        return f"Navegando hacia {destination}. {steps_taken} pasos. Analisis: {analysis[:300]}"
    
    elif action == "auto":
        # Autonomous play loop with learning
        for s in range(min(steps, 20)):
            time.sleep(0.5)
            analysis = _ask(
                "Eres un jugador autonomo. Mira esta pantalla y decide que hacer AHORA. "
                "Responde SOLO con acciones (max 3): avanzar, retroceder, izquierda, derecha, "
                "girar izquierda, girar derecha, saltar, interactuar, atacar, inventario, correr, agachar. "
                "NO EXPLIQUES, solo lista de acciones. Ejemplo: 'avanzar, girar derecha, atacar'"
            )
            result = _action_from_text(analysis)
            if player: player.write_log(f"  [{s+1}] {result}")
            time.sleep(0.2)
        
        # Save learning after auto session
        try:
            from actions.eris_db import episodic_add, know_add
            episodic_add(f"Game agent: {steps} pasos autonomos en {game or 'juego'}", "game", str(parameters), 0.7)
            know_add(f"game_{game or 'generico'}", f"Estrategia de juego autonomo: {instructions or 'exploracion y combate'}", "game_learning", 0.5)
        except: pass
        
        return f"Modo autonomo: {min(steps, 20)} decisiones tomadas. Conocimiento guardado."

    elif action == "learn":
        # Analyze game state and save knowledge for future sessions
        analysis = _ask(
            "Analiza esta pantalla de juego. Quiero que aprendas sobre este juego. "
            "Describe: 1) Que genero es? 2) Que mecanicas ves? 3) Que estrategia usarias? "
            "4) Que patrones de UI reconoces (barra de vida, minimapa, inventario)? "
            "5) Consejos para jugar mejor. Responde en espanol, guarda esto para futuras sesiones."
        )
        # Save to knowledge base
        try:
            from actions.eris_db import know_add, save_everywhere
            save_everywhere({
                "topic": f"game_knowledge_{game or 'general'}",
                "content": analysis[:500],
                "category": "game_learning",
                "importance": 0.8
            })
        except: pass
        return f"Aprendizaje guardado para {game or 'este juego'}:\n{analysis[:500]}"
    
    return f"Accion '{action}' no reconocida. Usa: analyze, play, look_around, explore, fight, find, navigate, auto"
