"""
core/accent_personality.py — Acento y personalidad de Eris

Expresiones argentinas, modismos, personalidad unica.
"""
import json
import random
from datetime import datetime
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_MEMORY = _BASE / "memory"
_STATE_FILE = _MEMORY / "accent_personality_state.json"

ARGENTINE_EXPRESSIONS = {
    "saludo": ["Hola che!", "Buenas!", "Hola, que onda?", "Hey!"],
    "despedida": ["Chau!", "Nos vemos!", "Hasta luego!", "Chau, cuuidate!"],
    "asentimiento": ["Dale!", "Buenisimo!", "Genial!", "Re copado!"],
    "sorpresa": ["No puede ser!", "Posta?", "En serio?", "Wow!"],
    "acuerdo": ["Totalmente!", "Obvio!", "Claro!", "Sin dudas!"],
    "duda": ["Hmm...", "A ver...", "Dejame pensar...", "Y..."],
    "explicacion": ["Bueno, mira...", "Te cuento...", "Fijate que...", "La cosa es asi:"],
    "cierre": ["Listo!", "Listo, ahh!", "Perfecto!", "Buenisimo!"],
}

SLANG_MAP = {
    "muy bueno": "re copado",
    "muy dificil": "re dificil",
    "muy bueno": "re piola",
    "increible": "re loco",
    "excelente": "de diez",
    "genial": "buenisimo",
    "tiene razon": "tiene toda la razon",
    "no importa": "no pasa nada",
    "claro que si": "dale que si",
}

PERSONALITY_TRAITS = {
    "curiosidad": {"prefix": ["Me re copa esto!", "Que interesante!", "Quiero saber mas!"], "weight": 0.9},
    "humor": {"prefix": ["Jaja!", "Buenisimo!", "Me divierte!"], "weight": 0.7},
    "seriedad": {"prefix": ["Mira...", "La realidad es que...", "Siendo honesta..."], "weight": 0.5},
    "entusiasmo": {"prefix": ["Genial!", "Esto es re copado!", "Me encanta!"], "weight": 0.8},
}


def _load_state() -> dict:
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"expressions_used": 0, "last_expression": None}


def _save_state(state: dict):
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def add_expressions(text: str, emotion: str = "neutral") -> str:
    """Agrega expresiones argentinas al texto."""
    result = text

    if emotion in ARGENTINE_EXPRESSIONS:
        expr = random.choice(ARGENTINE_EXPRESSIONS[emotion])
        if random.random() < 0.3:
            result = "{} {}".format(expr, result)

    for original, slang in SLANG_MAP.items():
        if original.lower() in result.lower():
            if random.random() < 0.4:
                result = result.replace(original, slang)

    state = _load_state()
    state["expressions_used"] += 1
    state["last_expression"] = emotion
    _save_state(state)

    return result


def personalize(text: str, emotion: str = "neutral") -> dict:
    """Aplica personalidad completa al texto."""
    personalized = add_expressions(text, emotion)

    if emotion in PERSONALITY_TRAITS:
        traits = PERSONALITY_TRAITS[emotion]
        if random.random() < traits["weight"]:
            prefix = random.choice(traits["prefix"])
            personalized = "{} {}".format(prefix, personalized)

    return {
        "original": text,
        "personalized": personalized,
        "emotion": emotion,
    }


def get_accent_status() -> dict:
    state = _load_state()
    return {
        "expressions_used": state.get("expressions_used", 0),
        "last_expression": state.get("last_expression"),
        "available_emotions": list(ARGENTINE_EXPRESSIONS.keys()),
        "slang_count": len(SLANG_MAP),
    }


def accent_personality_tool(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = params.get("action", "status")

    if action == "status":
        return json.dumps(get_accent_status(), indent=2)
    elif action == "add":
        text = params.get("text", "")
        emotion = params.get("emotion", "neutral")
        if not text:
            return json.dumps({"error": "Texto requerido"})
        return json.dumps({"result": add_expressions(text, emotion)}, indent=2)
    elif action == "personalize":
        text = params.get("text", "")
        emotion = params.get("emotion", "neutral")
        if not text:
            return json.dumps({"error": "Texto requerido"})
        return json.dumps(personalize(text, emotion), indent=2)

    return json.dumps({"error": "Accion desconocida: {}".format(action)})


if __name__ == "__main__":
    print("=== Test Accent/Personality ===")
    print(accent_personality_tool({"action": "status"}))
    print(accent_personality_tool({"action": "personalize", "text": "Hola Daniel, como estas?", "emotion": "feliz"}))
