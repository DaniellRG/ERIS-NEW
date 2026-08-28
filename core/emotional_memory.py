"""
core/emotional_memory.py — Memoria emocional para Eris

Eris recuerda como se sintio en cada interaccion.
"""
import json
from datetime import datetime
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_MEMORY = _BASE / "memory"
_STATE_FILE = _MEMORY / "emotional_memory.json"


def _load_state() -> dict:
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"episodes": [], "patterns": {}}


def _save_state(state: dict):
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def record_emotion(emotion: str, intensity: float, context: str = "", trigger: str = "") -> dict:
    """Registra una emocion en la memoria."""
    state = _load_state()
    episode = {
        "timestamp": datetime.now().isoformat(),
        "emotion": emotion,
        "intensity": min(max(intensity, 0), 1),
        "context": context[:200],
        "trigger": trigger[:100],
    }
    state.setdefault("episodes", []).append(episode)

    if len(state["episodes"]) > 500:
        state["episodes"] = state["episodes"][-500:]

    emotion_counts = {}
    for ep in state["episodes"]:
        e = ep.get("emotion", "")
        emotion_counts[e] = emotion_counts.get(e, 0) + 1
    state["patterns"] = emotion_counts

    _save_state(state)
    return {"status": "registrado", "emotion": emotion, "intensity": intensity}


def analyze_patterns() -> dict:
    """Analiza patrones emocionales."""
    state = _load_state()
    episodes = state.get("episodes", [])
    if not episodes:
        return {"status": "sin_datos"}

    emotion_counts = {}
    intensity_avg = {}
    for ep in episodes:
        e = ep.get("emotion", "")
        emotion_counts[e] = emotion_counts.get(e, 0) + 1
        if e not in intensity_avg:
            intensity_avg[e] = []
        intensity_avg[e].append(ep.get("intensity", 0))

    for e in intensity_avg:
        vals = intensity_avg[e]
        intensity_avg[e] = round(sum(vals) / len(vals), 2)

    sorted_emotions = sorted(emotion_counts.items(), key=lambda x: x[1], reverse=True)

    return {
        "total_episodes": len(episodes),
        "emotion_counts": dict(sorted_emotions),
        "avg_intensity": intensity_avg,
        "most_common": sorted_emotions[0][0] if sorted_emotions else None,
        "least_common": sorted_emotions[-1][0] if sorted_emotions else None,
    }


def predict_emotion(context: str = "") -> dict:
    """Predice la emocion mas probable basada en historial."""
    state = _load_state()
    episodes = state.get("episodes", [])
    if not episodes:
        return {"predicted": "curiosidad", "confidence": 0.5}

    recent = episodes[-20:]
    emotion_counts = {}
    for ep in recent:
        e = ep.get("emotion", "")
        emotion_counts[e] = emotion_counts.get(e, 0) + 1

    if emotion_counts:
        predicted = max(emotion_counts, key=emotion_counts.get)
        confidence = emotion_counts[predicted] / len(recent)
        return {"predicted": predicted, "confidence": round(confidence, 2)}

    return {"predicted": "curiosidad", "confidence": 0.5}


def get_emotional_memory_status() -> dict:
    state = _load_state()
    episodes = state.get("episodes", [])
    return {
        "total_episodes": len(episodes),
        "patterns": state.get("patterns", {}),
        "last_emotion": episodes[-1].get("emotion") if episodes else None,
    }


def emotional_memory_tool(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = params.get("action", "status")

    if action == "status":
        return json.dumps(get_emotional_memory_status(), indent=2)
    elif action == "record":
        emotion = params.get("emotion", "")
        intensity = params.get("intensity", 0.5)
        context = params.get("context", "")
        trigger = params.get("trigger", "")
        if not emotion:
            return json.dumps({"error": "Emocion requerida"})
        return json.dumps(record_emotion(emotion, intensity, context, trigger), indent=2)
    elif action == "analyze":
        return json.dumps(analyze_patterns(), indent=2)
    elif action == "predict":
        return json.dumps(predict_emotion(params.get("context", "")), indent=2)

    return json.dumps({"error": "Accion desconocida: {}".format(action)})


if __name__ == "__main__":
    print("=== Test Emotional Memory ===")
    print(emotional_memory_tool({"action": "status"}))
    print(emotional_memory_tool({"action": "record", "emotion": "curiosidad", "intensity": 0.8}))
    print(emotional_memory_tool({"action": "analyze"}))
