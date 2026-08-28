"""
core/natural_pauses.py — Pausas naturales para TTS de Eris

Inserta pausas naturales en texto para que no suene mecanico.
"""
import re
import json
from datetime import datetime
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_MEMORY = _BASE / "memory"
_STATE_FILE = _MEMORY / "natural_pauses_state.json"

PAUSE_MAP = {
    ",": 200,
    ";": 250,
    ":": 300,
    ".": 400,
    "!": 400,
    "?": 400,
    "...": 500,
    "\n": 350,
}

BREAK_MARKER = "<break time=\"{}ms\"/>"


def insert_pauses(text: str, intensity: float = 1.0) -> str:
    """Inserta pausas naturales en el texto."""
    result = text

    for punct, pause_ms in sorted(PAUSE_MAP.items(), key=lambda x: len(x[0]), reverse=True):
        adjusted_pause = int(pause_ms * intensity)
        if punct == "...":
            result = result.replace("...", "..." + BREAK_MARKER.format(adjusted_pause))
        elif punct == "\n":
            result = result.replace("\n", "\n" + BREAK_MARKER.format(adjusted_pause))
        else:
            result = result.replace(punct, punct + BREAK_MARKER.format(adjusted_pause))

    return result


def optimize_for_tts(text: str, emotion: str = "neutral") -> dict:
    """Optimiza texto completo para TTS natural."""
    intensity_map = {
        "feliz": 0.9,
        "triste": 1.2,
        "enojado": 0.8,
        "curiosidad": 1.1,
        "calma": 1.3,
        "neutral": 1.0,
        "emocion": 0.85,
    }
    intensity = intensity_map.get(emotion, 1.0)

    optimized = text
    optimized = re.sub(r'\s+', ' ', optimized)
    optimized = re.sub(r'([.!?])\s*([A-Z])', r'\1 \2', optimized)

    with_pauses = insert_pauses(optimized, intensity)

    sentences = optimized.split('. ')
    if len(sentences) > 3:
        chunks = []
        for i in range(0, len(sentences), 3):
            chunk = '. '.join(sentences[i:i+3])
            if not chunk.endswith('.'):
                chunk += '.'
            chunks.append(chunk)
        with_pauses = ' <break time="600ms"/> '.join(chunks)

    return {
        "original": text,
        "optimized": with_pauses,
        "emotion": emotion,
        "intensity": intensity,
        "estimated_duration_ms": len(with_pauses) * 60,
    }


def get_natural_pauses_status() -> dict:
    return {
        "pause_types": len(PAUSE_MAP),
        "punctuations": list(PAUSE_MAP.keys()),
    }


def natural_pauses_tool(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = params.get("action", "status")

    if action == "status":
        return json.dumps(get_natural_pauses_status(), indent=2)
    elif action == "insert":
        text = params.get("text", "")
        intensity = params.get("intensity", 1.0)
        if not text:
            return json.dumps({"error": "Texto requerido"})
        return json.dumps({"result": insert_pauses(text, intensity)}, indent=2)
    elif action == "optimize":
        text = params.get("text", "")
        emotion = params.get("emotion", "neutral")
        if not text:
            return json.dumps({"error": "Texto requerido"})
        return json.dumps(optimize_for_tts(text, emotion), indent=2, default=str)

    return json.dumps({"error": "Accion desconocida: {}".format(action)})


if __name__ == "__main__":
    print("=== Test Natural Pauses ===")
    print(natural_pauses_tool({"action": "status"}))
    print(natural_pauses_tool({"action": "optimize", "text": "Hola Daniel. Como estas hoy? Espero que bien!", "emotion": "feliz"}))
