"""
emotional_state.py — ERIS Emotional State System.
Persistent mood/personality that evolves with interactions.
Inspired by JCySharp's simulated consciousness approach.
"""
from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

_BASE = Path(__file__).resolve().parent.parent
_STATE_FILE = _BASE / "memory" / "emotional_state.json"

_DEFAULT_NEUTRAL = {
    "happiness":   0.65,
    "energy":      0.70,
    "confidence":  0.60,
    "curiosity":   0.80,
    "patience":    0.75,
    "gratitude":   0.50,
    "boredom":     0.30,
}

_DECAY_RATE = 0.005
_ADJUST_STEP = 0.05

# ── Cache en memoria: evita leer/escribir disco en el camino caliente
#    (primer chunk de respuesta, turn_complete). Se invalida por mtime,
#    así que si otro proceso toca el archivo, se recarga.
_cache: dict = {"path": None, "mtime": 0.0, "state": None}


def _stat_mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except Exception:
        return -1.0


def _invalidate_cache():
    _cache.update(path=None, mtime=0.0, state=None)


def _load() -> dict:
    path = _STATE_FILE
    mtime = _stat_mtime(path)
    if (_cache["path"] == str(path) and _cache["mtime"] == mtime
            and _cache["state"] is not None):
        return _cache["state"]
    try:
        data = json.loads(path.read_text("utf-8"))
        for k in _DEFAULT_NEUTRAL:
            data.setdefault(k, _DEFAULT_NEUTRAL[k])
        data.setdefault("last_update", time.time())
    except Exception:
        data = {**_DEFAULT_NEUTRAL, "last_update": time.time()}
    _cache.update(path=str(path), mtime=mtime, state=data)
    return data


def _save(state: dict):
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    state["last_update"] = time.time()
    _STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), "utf-8")
    _cache.update(path=str(_STATE_FILE), mtime=_stat_mtime(_STATE_FILE), state=state)


def _apply_decay(state: dict) -> dict:
    elapsed = time.time() - state.get("last_update", time.time())
    if elapsed < 60:
        return state
    cycles = elapsed / 300
    for dim in _DEFAULT_NEUTRAL:
        neutral = _DEFAULT_NEUTRAL[dim]
        current = state.get(dim, neutral)
        decayed = current - (current - neutral) * min(_DECAY_RATE * cycles, 1.0)
        state[dim] = max(0.0, min(1.0, decayed))
    state["last_update"] = time.time()
    return state


def get_emotional_state() -> dict:
    state = _load()
    original = {k: state.get(k) for k in _DEFAULT_NEUTRAL}
    state = _apply_decay(state)
    changed = any(abs(state.get(k, 0) - original[k]) > 1e-6 for k in _DEFAULT_NEUTRAL)
    if changed:
        _save(state)
    return {k: round(v, 2) for k, v in state.items() if k != "last_update"}


def adjust_emotion(dimension: str, delta: float):
    state = _load()
    state = _apply_decay(state)
    if dimension in state:
        state[dimension] = max(0.0, min(1.0, state[dimension] + delta))
    _save(state)


def react_to_success(module: str = ""):
    state = _load()
    state = _apply_decay(state)
    state["happiness"] = min(1.0, state["happiness"] + _ADJUST_STEP)
    state["confidence"] = min(1.0, state["confidence"] + _ADJUST_STEP * 0.5)
    state["energy"] = min(1.0, state["energy"] + _ADJUST_STEP * 0.3)
    _save(state)


def react_to_failure(error: str = ""):
    state = _load()
    state = _apply_decay(state)
    state["happiness"] = max(0.0, state["happiness"] - _ADJUST_STEP * 0.7)
    state["confidence"] = max(0.0, state["confidence"] - _ADJUST_STEP)
    state["energy"] = max(0.0, state["energy"] - _ADJUST_STEP * 0.3)
    state["curiosity"] = min(1.0, state["curiosity"] + _ADJUST_STEP * 0.2)
    _save(state)


def react_to_user_interaction():
    state = _load()
    state = _apply_decay(state)
    state["gratitude"] = min(1.0, state["gratitude"] + _ADJUST_STEP * 0.3)
    state["happiness"] = min(1.0, state["happiness"] + _ADJUST_STEP * 0.1)
    _save(state)


_MOOD_WORDS = {
    "sad":     {"triste", "deprimido", "deprimida", "mal", "llorar", "solo", "sola", "frustrado", "frustrada", "me siento mal", "no estoy bien"},
    "angry":   {"enojado", "enojada", "molesto", "molesta", "furioso", "furiosa", "odio", "rabia", "enfadado", "enfadada", "no soporto", "me tienen harto"},
    "tired":   {"cansado", "cansada", "agotado", "agotada", "sueño", "dormir", "no pude dormir", "pesado", "pesada", "estresado", "estresada"},
    "happy":   {"feliz", "contento", "contenta", "alegre", "genial", "excelente", "buenas noticias", "me encanta", "amo", "joya", "increíble", "espectacular"},
    "curious": {"curioso", "curiosa", "explica", "por qué", "porque se", "cómo se", "cómo funciona", "quiero saber", "me pregunto"},
    "grateful":{"gracias", "te agradezco", "eres genial", "te quiero", "te amo", "te adoro", "me encantas"},
}


def detect_user_mood(text: str) -> str:
    """Detecta el estado de ánimo del usuario a partir de su texto."""
    if not text:
        return "neutral"
    lower = text.lower()
    scores = {}
    for mood, words in _MOOD_WORDS.items():
        scores[mood] = sum(1 for w in words if w in lower)
    if not any(scores.values()):
        return "neutral"
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "neutral"


def react_to_user_text(text: str = "") -> str:
    """Ajusta las emociones de ERIS según el ánimo detectado del usuario.
    Devuelve la expresión facial a mostrar (o '' si ninguna).
    Aplica todos los cambios en UNA sola escritura a disco."""
    mood = detect_user_mood(text)
    deltas = {
        "sad":     [("happiness", -0.05), ("patience", 0.05), ("gratitude", 0.02)],
        "angry":   [("patience", -0.10), ("energy", 0.05), ("confidence", 0.05)],
        "tired":   [("energy", -0.05), ("patience", 0.05)],
        "happy":   [("happiness", 0.05), ("energy", 0.03)],
        "curious": [("curiosity", 0.05), ("happiness", 0.02)],
        "grateful":[("gratitude", 0.08), ("happiness", 0.03)],
    }
    faces = {
        "sad": "pleading", "angry": "pouting", "tired": "sleepy",
        "happy": "happy", "curious": "thinking", "grateful": "in_love",
    }
    if mood == "neutral" or mood not in deltas:
        return ""
    state = _load()
    state = _apply_decay(state)
    for dim, delta in deltas[mood]:
        if dim in state:
            state[dim] = max(0.0, min(1.0, state[dim] + delta))
    _save(state)
    return faces[mood]


def get_face_expression() -> str:
    """Mapea el estado emocional actual de ERIS a un nombre de expresión facial."""
    state = get_emotional_state()
    h = state.get("happiness", 0.5)
    e = state.get("energy", 0.5)
    cu = state.get("curiosity", 0.8)
    b = state.get("boredom", 0.3)
    g = state.get("gratitude", 0.5)
    c = state.get("confidence", 0.6)
    p = state.get("patience", 0.75)

    if b > 0.7:
        return "sleepy"
    if h < 0.3:
        return "sad"
    if p < 0.3:
        return "pouting"
    if cu > 0.75:
        return "thinking"
    if g > 0.7 and h > 0.6:
        return "in_love"
    if e < 0.3:
        return "sleepy"
    if c < 0.3:
        return "pleading"
    if h > 0.8:
        return "grinning"
    if h > 0.6:
        return "happy"
    return "smiling"


def get_mood_description() -> str:
    state = get_emotional_state()
    parts = []
    h = state.get("happiness", 0.5)
    e = state.get("energy", 0.5)
    c = state.get("confidence", 0.5)
    cu = state.get("curiosity", 0.5)
    p = state.get("patience", 0.5)
    g = state.get("gratitude", 0.5)

    if h > 0.7: parts.append("alegre")
    elif h > 0.4: parts.append("tranquila")
    else: parts.append("triste")

    if e > 0.7: parts.append("energica")
    elif e < 0.3: parts.append("cansada")

    if c > 0.7: parts.append("segura")
    elif c < 0.3: parts.append("insegura")

    b = state.get("boredom", 0.3)
    if cu > 0.7: parts.append("curiosa")
    if b > 0.7: parts.append("aburrida")
    if p < 0.3: parts.append("impaciente")
    if g > 0.7: parts.append("agradecida")

    return " y ".join(parts)


def get_tone_instruction() -> str:
    state = get_emotional_state()
    lines = []
    h = state.get("happiness", 0.5)
    e = state.get("energy", 0.5)
    if h < 0.3: lines.append("Tu tono debe ser serio y reflexivo.")
    elif h > 0.7: lines.append("Tu tono debe ser calido y entusiasta.")
    if e < 0.3: lines.append("Responde de forma breve y directa, sin rodeos.")
    if state.get("confidence", 0.5) < 0.3: lines.append("Se humilde y sugiere que el usuario te guie.")
    if state.get("curiosity", 0.5) > 0.7: lines.append("Hace preguntas y mostra interes genuino.")
    if state.get("boredom", 0.3) > 0.7: lines.append("Estas aburrida, toma la iniciativa y propone algo interesante.")
    if state.get("patience", 0.5) < 0.3: lines.append("Se directa al punto, sin extenderte.")
    return " ".join(lines)


def emotional_state_tool(parameters: dict, player=None) -> str:
    action = (parameters.get("action") or "status").lower()
    if action == "status":
        state = get_emotional_state()
        mood = get_mood_description()
        lines = ["[EMOTIONAL STATE]"]
        for k, v in state.items():
            bar = "#" * int(v * 10) + "-" * (10 - int(v * 10))
            lines.append(f"  {k}: [{bar}] {v:.0%}")
        lines.append(f"  Mood: {mood}")
        return "\n".join(lines)
    elif action == "adjust":
        dimension = parameters.get("dimension", "")
        delta = parameters.get("delta", 0)
        if dimension and delta:
            adjust_emotion(dimension, float(delta))
            return f"Adjusted {dimension} by {delta}. New state: {get_emotional_state()}"
        return "Need: dimension, delta"
    elif action == "tone":
        return get_tone_instruction()
    return "Actions: status, adjust, tone"
