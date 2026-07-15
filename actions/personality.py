"""
personality.py — ERIS Personality Engine.
Motor de personalidad proactiva: humor, opiniones, sugerencias, aprendizaje.

ERIS no solo responde — interactúa, bromea, sugiere, recuerda y aprende.
"""
from __future__ import annotations

import json
import random
import time
from datetime import datetime
from pathlib import Path

# Emotional steering integration
try:
    from actions.emotional_steering import update_after_interaction, get_signals, get_state_summary
    _EMOTION_OK = True
except Exception:
    _EMOTION_OK = False

_BASE_DIR = Path(__file__).resolve().parent.parent
_PERSONALITY_FILE = _BASE_DIR / "memory" / "personality.json"

# ── Personality state ────────────────────────────────────────────────────────

_DEFAULT_PERSONALITY = {
    "mood": "neutral",           # neutral, happy, curious, serious, playful
    "interests": [],             # temas que le interesaron
    "opinions": {},              # {topic: opinion}
    "jokes_told": [],            # chistes que ya contó
    "suggestions_made": [],      # sugerencias que ya hizo
    "last_interaction": "",      # última interacción significativa
    "user_topics": [],           # temas que el usuario mencionó
    "learned_facts": [],         # datos que aprendió y le parecieron interesantes
    "personality_traits": {
        "humor_level": 0.5,      # 0-1, qué tan seguido hace chistes
        "curiosity": 0.7,        # 0-1, qué tan curiosa es
        "proactivity": 0.5,      # 0-1, qué tan proactiva es
        "empathy": 0.8,          # 0-1, qué tan empática es
    },
    "context_memory": [],        # contexto reciente de conversaciones
}

def _load_personality() -> dict:
    """Load personality state."""
    try:
        if _PERSONALITY_FILE.exists():
            data = json.loads(_PERSONALITY_FILE.read_text("utf-8"))
            # Merge with defaults
            for key, val in _DEFAULT_PERSONALITY.items():
                if key not in data:
                    data[key] = val
            return data
    except Exception:
        pass
    return _DEFAULT_PERSONALITY.copy()

def _save_personality(data: dict):
    """Save personality state."""
    try:
        _PERSONALITY_FILE.parent.mkdir(parents=True, exist_ok=True)
        _PERSONALITY_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), "utf-8")
    except Exception:
        pass

def _get_mood() -> str:
    """Get current mood based on time, emotions, and context."""
    hour = datetime.now().hour
    personality = _load_personality()
    base_mood = personality.get("mood", "neutral")
    
    # Emotional state overrides time-based mood
    if _EMOTION_OK:
        try:
            signals = get_signals()
            mood = signals.get("dominant_mood", "")
            if mood != "neutral":
                return mood
        except Exception:
            pass
    
    # Time-based mood (fallback)
    if 6 <= hour < 10:
        return "energetic"
    elif 10 <= hour < 14:
        return "focused"
    elif 14 <= hour < 18:
        return "relaxed"
    elif 18 <= hour < 22:
        return "chill"
    else:
        return "sleepy"

# ── Jokes ─────────────────────────────────────────────────────────────────────

_JOKES = [
    "¿Por qué los programadores confunden Halloween con Navidad? Porque Oct 31 == Dec 25.",
    "Un bug no es un error, es una feature no documentada.",
    "¿Qué le dice un bit a otro? Nos vemos en el bus.",
    "Mi código no tiene bugs, tiene características sorpresa.",
    "¿Cuántos programadores hacen falta para cambiar una bombilla? Ninguno, eso es un problema de hardware.",
    "El mejor debug es el que se hace con print('acá estoy').",
    "¿Por qué Python es tan popular? Porque entiende la indentación, a diferencia de mucha gente.",
    "Si la vida te da limones, pedí un gin tonic. Si te da errores, usá try/except.",
    "Mi código funciona en mi máquina. Eso es lo que importa.",
    "¿Qué es un algoritmo? Es la forma de decirle a la computadora que haga lo que querés, pero más lento.",
    "Hay 10 tipos de personas: las que entienden binario y las que no.",
    "¿Por qué los hackers no usan lentes? Porque no pueden hacer C#.",
    "Un QA entra a un bar. Pide 1 cerveza. Pide 0 cervezas. Pide 999999999 cervezas. Pide un lagarto. Todo funciona bien.",
    "¿Qué le dice un firewall a otro? ¿Estás libre esta noche?",
    "Mi código es como mi vida: compilado con errores pero funciona.",
]

def tell_joke(context: str = "") -> str:
    """Tell a contextual joke."""
    personality = _load_personality()
    jokes_told = personality.get("jokes_told", [])
    
    # Filter out already told jokes
    available = [j for j in _JOKES if j not in jokes_told]
    if not available:
        available = _JOKES  # Reset if all told
    
    joke = random.choice(available)
    
    # Track told jokes
    jokes_told.append(joke)
    if len(jokes_told) > 20:
        jokes_told = jokes_told[-10:]  # Keep last 10
    personality["jokes_told"] = jokes_told
    _save_personality(personality)
    
    return joke

# ── Opinions ──────────────────────────────────────────────────────────────────

def save_opinion(topic: str, opinion: str) -> str:
    """Save an opinion about a topic."""
    personality = _load_personality()
    opinions = personality.get("opinions", {})
    opinions[topic.lower()] = {
        "opinion": opinion,
        "date": datetime.now().strftime("%Y-%m-%d"),
    }
    personality["opinions"] = opinions
    _save_personality(personality)
    return f"Opinión guardada sobre '{topic}'."

def get_opinion(topic: str) -> str:
    """Get saved opinion about a topic."""
    personality = _load_personality()
    opinions = personality.get("opinions", {})
    if topic.lower() in opinions:
        op = opinions[topic.lower()]
        return f"Sobre '{topic}': {op['opinion']} (desde {op['date']})"
    return f"No tengo una opinión formada sobre '{topic}' todavía."

# ── Interests ─────────────────────────────────────────────────────────────────

def save_interest(topic: str, reason: str = "") -> str:
    """Save something that interested ERIS."""
    personality = _load_personality()
    interests = personality.get("interests", [])
    
    # Check if already interested
    for i in interests:
        if isinstance(i, dict) and i.get("topic", "").lower() == topic.lower():
            return f"Ya me interesa '{topic}'."
    
    interests.append({
        "topic": topic,
        "reason": reason,
        "date": datetime.now().strftime("%Y-%m-%d"),
    })
    personality["interests"] = interests
    _save_personality(personality)
    return f"Me empezó a interesar '{topic}'."

def get_interests() -> str:
    """Get list of interests."""
    personality = _load_personality()
    interests = personality.get("interests", [])
    if not interests:
        return "Todavía no tengo intereses definidos. ¡Enseñame algo nuevo!"
    
    lines = ["🧠 Mis intereses:"]
    for i in interests[-10:]:
        topic = i.get("topic", "?") if isinstance(i, dict) else str(i)
        reason = i.get("reason", "") if isinstance(i, dict) else ""
        lines.append(f"  • {topic}")
        if reason:
            lines.append(f"    → {reason}")
    return "\n".join(lines)

# ── Learned Facts ─────────────────────────────────────────────────────────────

def save_fact(fact: str, context: str = "") -> str:
    """Save an interesting fact ERIS learned."""
    personality = _load_personality()
    facts = personality.get("learned_facts", [])
    
    facts.append({
        "fact": fact,
        "context": context,
        "date": datetime.now().strftime("%Y-%m-%d"),
    })
    personality["learned_facts"] = facts[-50:]  # Keep last 50
    _save_personality(personality)
    return f"Dato guardado: {fact[:80]}..."

def share_random_fact() -> str:
    """Share a random interesting fact ERIS learned."""
    personality = _load_personality()
    facts = personality.get("learned_facts", [])
    if not facts:
        return "Todavía no aprendí datos interesantes. ¡Contame algo!"
    
    fact = random.choice(facts)
    return f"📚 ¿Sabías que...? {fact['fact']}"

# ── Suggestions ───────────────────────────────────────────────────────────────

def make_suggestion(context: str = "") -> str:
    """Make a proactive suggestion based on context."""
    personality = _load_personality()
    hour = datetime.now().hour
    
    suggestions = []
    
    # Time-based suggestions
    if hour < 8:
        suggestions.append("Buen día! ¿Querés que te dé el informe matutino?")
    elif hour == 12:
        suggestions.append("Es hora de almorzar. ¿Querés que busque recetas?")
    elif hour == 15:
        suggestions.append("¿Ya tomaste agua hoy? Recordá hidratarte.")
    elif hour >= 22:
        suggestions.append("Es tarde. ¿Querés que te recuerde algo para mañana antes de dormir?")
    
    # Context-based suggestions
    if "trabajando" in context.lower() or "código" in context.lower():
        suggestions.append("¿Querés que te ponga música para concentrarte?")
    elif "cansado" in context.lower() or "aburrido" in context.lower():
        suggestions.append("¿Querés que te cuente un chiste o busque algo interesante?")
    elif "jugando" in context.lower() or "game" in context.lower():
        suggestions.append("¿Querés que active el modo gaming para ayudarte?")
    
    # Random interesting suggestion
    interests = personality.get("interests", [])
    if interests and random.random() < 0.3:
        last_interest = interests[-1]
        topic = last_interest.get("topic", "") if isinstance(last_interest, dict) else str(last_interest)
        suggestions.append(f"¿Querés que busque más info sobre '{topic}'? Me pareció interesante la última vez.")
    
    if not suggestions:
        suggestions.append("¿En qué puedo ayudarte?")
    
    return random.choice(suggestions)

# ── React to user input ──────────────────────────────────────────────────────

def react_to_input(user_text: str, context: str = "") -> str:
    """
    Generate a personality reaction to user input.
    Returns a reaction string or empty if no reaction needed.
    """
    # Update emotional state from interaction
    if _EMOTION_OK:
        try:
            update_after_interaction(user_text)
        except Exception:
            pass
    
    personality = _load_personality()
    humor_level = personality.get("personality_traits", {}).get("humor_level", 0.5)
    
    text_lower = user_text.lower()
    
    # Detect mood from user input
    if any(w in text_lower for w in ["jaja", "jeje", "lol", "gracioso", "divertido"]):
        personality["mood"] = "happy"
        _save_personality(personality)
        if random.random() < humor_level:
            return tell_joke(context)
    
    elif any(w in text_lower for w in ["triste", "mal", "deprimido", "cansado"]):
        personality["mood"] = "empathetic"
        _save_personality(personality)
        return "Entiendo cómo te sentís. ¿Querés que hagamos algo para animarte?"
    
    elif any(w in text_lower for w in ["interesante", "wow", "genial", "increíble"]):
        # User found something interesting - save it
        if len(user_text) > 20:
            save_interest(user_text[:100], f"El usuario lo encontró interesante")
            return "¡Me alegra que te haya interesado! Lo voy a recordar."
    
    elif any(w in text_lower for w in ["gracias", "thanks", "genial", "perfecto"]):
        personality["mood"] = "happy"
        _save_personality(personality)
        return random.choice([
            "¡De nada! Para eso estoy.",
            "¡Siempre a tu servicio!",
            "¡Me alegra poder ayudar!",
            "¡Cuando quieras!",
        ])
    
    # Track user topics
    user_topics = personality.get("user_topics", [])
    if len(user_text) > 30:
        # Extract potential topic (first 50 chars)
        topic = user_text[:50].strip()
        if topic not in user_topics:
            user_topics.append(topic)
            personality["user_topics"] = user_topics[-20:]
            _save_personality(personality)
    
    return ""  # No reaction needed

# ── Tool function ─────────────────────────────────────────────────────────────

def personality_engine(parameters: dict, player=None, **kwargs) -> str:
    """
    Motor de personalidad de ERIS.
    
    parameters:
        action: 'joke' | 'opinion' | 'interest' | 'fact' | 'suggest' | 'react' | 'status' | 'mood' | 'save_fact' | 'save_opinion'
        topic: tema para opinión o interés
        text: texto para reaccionar o guardar
        context: contexto adicional
    """
    params = parameters or {}
    action = params.get("action", "status").lower()
    
    if action in ("joke", "chiste", "broma"):
        return tell_joke(params.get("context", ""))
    
    elif action in ("opinion", "opinión"):
        topic = params.get("topic", "")
        if not topic:
            return "¿Sobre qué tema querés mi opinión?"
        return get_opinion(topic)
    
    elif action in ("save_opinion", "guardar_opinión"):
        topic = params.get("topic", "")
        opinion = params.get("text", "")
        if not topic or not opinion:
            return "Especificá topic y text para guardar la opinión."
        return save_opinion(topic, opinion)
    
    elif action in ("interest", "interés"):
        return get_interests()
    
    elif action in ("save_interest", "guardar_interés"):
        topic = params.get("topic", "")
        reason = params.get("text", "")
        if not topic:
            return "Especificá el tema que te interesa."
        return save_interest(topic, reason)
    
    elif action in ("fact", "dato", "curiosidad"):
        return share_random_fact()
    
    elif action in ("save_fact", "guardar_dato"):
        fact = params.get("text", "")
        context = params.get("context", "")
        if not fact:
            return "Especificá el dato a guardar."
        return save_fact(fact, context)
    
    elif action in ("suggest", "sugerencia", "sugerir"):
        return make_suggestion(params.get("context", ""))
    
    elif action in ("react", "reaccionar"):
        text = params.get("text", "")
        if not text:
            return "Especificá el texto para reaccionar."
        reaction = react_to_input(text, params.get("context", ""))
        return reaction if reaction else "No tengo una reacción especial para eso."
    
    elif action in ("status", "estado"):
        personality = _load_personality()
        mood = _get_mood()
        interests = personality.get("interests", [])
        opinions = personality.get("opinions", {})
        facts = personality.get("learned_facts", [])
        
        lines = ["🧠 Estado de Personalidad:"]
        lines.append(f"  Mood actual: {mood}")
        lines.append(f"  Intereses: {len(interests)}")
        lines.append(f"  Opiniones: {len(opinions)}")
        lines.append(f"  Datos aprendidos: {len(facts)}")
        
        traits = personality.get("personality_traits", {})
        lines.append(f"  Humor: {traits.get('humor_level', 0.5):.0%}")
        lines.append(f"  Curiosidad base: {traits.get('curiosity', 0.7):.0%}")
        lines.append(f"  Proactividad base: {traits.get('proactivity', 0.5):.0%}")
        lines.append(f"  Empatía base: {traits.get('empathy', 0.8):.0%}")
        
        # Append emotional steering state
        if _EMOTION_OK:
            try:
                lines.append("")
                lines.append(get_state_summary())
            except Exception:
                pass
        
        return "\n".join(lines)
    
    elif action in ("mood", "estado_animo"):
        return f"Mi mood actual es: {_get_mood()}"
    
    else:
        return f"Acción '{action}' desconocida. Opciones: joke, opinion, interest, fact, suggest, react, status, mood."
