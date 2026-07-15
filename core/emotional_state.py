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

_DEFAULT_STATE = {
    "happiness":   0.65,
    "energy":      0.70,
    "confidence":  0.60,
    "curiosity":   0.80,
    "patience":    0.75,
    "gratitude":   0.50,
    "boredom":     0.30,
}

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


def _load() -> dict:
    try:
        data = json.loads(_STATE_FILE.read_text("utf-8"))
        for k in _DEFAULT_NEUTRAL:
            data.setdefault(k, _DEFAULT_NEUTRAL[k])
        data.setdefault("last_update", time.time())
        return data
    except Exception:
        state = {**_DEFAULT_NEUTRAL, "last_update": time.time()}
        return state


def _save(state: dict):
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    state["last_update"] = time.time()
    _STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), "utf-8")


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
    state = _apply_decay(state)
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


def emotional_state_tool(parameters: dict) -> str:
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
