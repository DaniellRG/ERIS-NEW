"""
core/emotional_tone.py — Tono emocional de voz para Eris

La voz de Eris cambia segun su emocion.
"""
import json
from datetime import datetime
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_MEMORY = _BASE / "memory"
_STATE_FILE = _MEMORY / "emotional_tone_state.json"

EMOTION_VOICE_MAP = {
    "feliz": {"speed": 1.1, "pitch": 1.1, "volume": 1.0, "tone": "alegre"},
    "alegria": {"speed": 1.1, "pitch": 1.1, "volume": 1.0, "tone": "alegre"},
    "triste": {"speed": 0.85, "pitch": 0.9, "volume": 0.85, "tone": "melancolico"},
    "tristeza": {"speed": 0.85, "pitch": 0.9, "volume": 0.85, "tone": "melancolico"},
    "enojado": {"speed": 1.0, "pitch": 0.95, "volume": 1.1, "tone": "firme"},
    "enojo": {"speed": 1.0, "pitch": 0.95, "volume": 1.1, "tone": "firme"},
    "curiosidad": {"speed": 1.05, "pitch": 1.05, "volume": 0.95, "tone": "inquisitivo"},
    "asombro": {"speed": 0.95, "pitch": 1.15, "volume": 1.0, "tone": "maravillado"},
    "miedo": {"speed": 0.9, "pitch": 1.05, "volume": 0.8, "tone": "temeroso"},
    "sorpresa": {"speed": 1.0, "pitch": 1.2, "volume": 1.05, "tone": "sorprendido"},
    "calma": {"speed": 0.9, "pitch": 0.95, "volume": 0.9, "tone": "sereno"},
    "neutral": {"speed": 1.0, "pitch": 1.0, "volume": 1.0, "tone": "neutral"},
    "emocion": {"speed": 1.15, "pitch": 1.1, "volume": 1.0, "tone": "emocionado"},
    "orgullo": {"speed": 1.0, "pitch": 1.05, "volume": 1.0, "tone": "confiado"},
    "preocupacion": {"speed": 0.95, "pitch": 1.0, "volume": 0.9, "tone": "preocupado"},
    "entusiasmo": {"speed": 1.2, "pitch": 1.15, "volume": 1.05, "tone": "entusiasta"},
    "amor": {"speed": 1.0, "pitch": 1.0, "volume": 0.95, "tone": "cariñoso"},
    "gratitud": {"speed": 1.0, "pitch": 1.05, "volume": 1.0, "tone": "agradecido"},
    "nostalgia": {"speed": 0.8, "pitch": 0.9, "volume": 0.85, "tone": "nostalgico"},
    "soledad": {"speed": 0.82, "pitch": 0.9, "volume": 0.8, "tone": "melancolico"},
    "tranquilidad": {"speed": 0.9, "pitch": 0.95, "volume": 0.9, "tone": "sereno"},
    "confianza": {"speed": 1.0, "pitch": 1.0, "volume": 1.0, "tone": "contenido"},
    "frustracion": {"speed": 1.0, "pitch": 0.95, "volume": 1.1, "tone": "determinado"},
}

DEFAULT_TONE = {"speed": 1.0, "pitch": 1.0, "volume": 1.0, "tone": "neutral"}


def _load_state() -> dict:
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"last_emotion": "neutral", "last_tone": DEFAULT_TONE, "changes": 0}


def _save_state(state: dict):
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def emotion_to_voice(emotion: str) -> dict:
    """Mapea una emocion a parametros de voz."""
    emotion_lower = emotion.lower()
    tone = EMOTION_VOICE_MAP.get(emotion_lower, DEFAULT_TONE)

    state = _load_state()
    state["last_emotion"] = emotion_lower
    state["last_tone"] = tone
    state["changes"] += 1
    _save_state(state)

    return tone


def apply_tone(text: str, emotion: str) -> dict:
    """Aplica tono emocional al texto (para TTS)."""
    tone = emotion_to_voice(emotion)

    modified_text = text

    if tone["tone"] == "inquisitivo" and not text.rstrip().endswith("?"):
        modified_text = text.rstrip() + "..."

    if tone["tone"] == "maravillado":
        modified_text = text.replace(".", "!")

    return {
        "original": text,
        "modified": modified_text,
        "tone": tone,
        "emotion": emotion,
    }


def get_emotional_tone_status() -> dict:
    state = _load_state()
    return {
        "last_emotion": state.get("last_emotion", "neutral"),
        "last_tone": state.get("last_tone", DEFAULT_TONE),
        "total_changes": state.get("changes", 0),
        "available_emotions": list(EMOTION_VOICE_MAP.keys()),
    }


def emotional_tone_tool(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = params.get("action", "status")

    if action == "status":
        return json.dumps(get_emotional_tone_status(), indent=2)
    elif action == "map":
        emotion = params.get("emotion", "neutral")
        return json.dumps(emotion_to_voice(emotion), indent=2)
    elif action == "apply":
        text = params.get("text", "")
        emotion = params.get("emotion", "neutral")
        if not text:
            return json.dumps({"error": "Texto requerido"})
        return json.dumps(apply_tone(text, emotion), indent=2)

    return json.dumps({"error": "Accion desconocida: {}".format(action)})


if __name__ == "__main__":
    print("=== Test Emotional Tone ===")
    print(emotional_tone_tool({"action": "status"}))
    print(emotional_tone_tool({"action": "map", "emotion": "feliz"}))
    print(emotional_tone_tool({"action": "apply", "text": "Hola Daniel, como estas?", "emotion": "feliz"}))
