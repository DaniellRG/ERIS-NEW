"""
core/voice_memory.py — Memoria de voz para Eris

Eris recuerda como hablo y mantiene consistencia.
"""
import json
from datetime import datetime
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_MEMORY = _BASE / "memory"
_STATE_FILE = _MEMORY / "voice_memory.json"


def _load_state() -> dict:
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "last_voice": "Aoede",
        "last_profile": "eris_default",
        "last_emotion": "neutral",
        "consistency_score": 1.0,
        "history": [],
    }


def _save_state(state: dict):
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def remember_voice(voice_name: str, profile: str, emotion: str) -> dict:
    """Recuerda la ultima configuracion de voz."""
    state = _load_state()

    if state.get("last_voice") == voice_name and state.get("last_profile") == profile:
        state["consistency_score"] = min(1.0, state.get("consistency_score", 1.0) + 0.05)
    else:
        state["consistency_score"] = max(0.5, state.get("consistency_score", 1.0) - 0.1)

    state["last_voice"] = voice_name
    state["last_profile"] = profile
    state["last_emotion"] = emotion

    state.setdefault("history", []).append({
        "voice": voice_name,
        "profile": profile,
        "emotion": emotion,
        "timestamp": datetime.now().isoformat(),
    })
    if len(state["history"]) > 100:
        state["history"] = state["history"][-100:]

    _save_state(state)
    return {
        "status": "recordado",
        "voice": voice_name,
        "profile": profile,
        "consistency": state["consistency_score"],
    }


def maintain_consistency() -> dict:
    """Retorna la configuracion recomendada para mantener consistencia."""
    state = _load_state()
    return {
        "recommended_voice": state.get("last_voice", "Aoede"),
        "recommended_profile": state.get("last_profile", "eris_default"),
        "consistency_score": state.get("consistency_score", 1.0),
        "should_change": state.get("consistency_score", 1.0) < 0.7,
    }


def get_voice_memory_status() -> dict:
    state = _load_state()
    return {
        "last_voice": state.get("last_voice"),
        "last_profile": state.get("last_profile"),
        "last_emotion": state.get("last_emotion"),
        "consistency_score": state.get("consistency_score", 1.0),
        "total_uses": len(state.get("history", [])),
    }


def voice_memory_tool(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = params.get("action", "status")

    if action == "status":
        return json.dumps(get_voice_memory_status(), indent=2)
    elif action == "remember":
        voice = params.get("voice", "Aoede")
        profile = params.get("profile", "eris_default")
        emotion = params.get("emotion", "neutral")
        return json.dumps(remember_voice(voice, profile, emotion), indent=2)
    elif action == "consistent":
        return json.dumps(maintain_consistency(), indent=2)

    return json.dumps({"error": "Accion desconocida: {}".format(action)})


if __name__ == "__main__":
    print("=== Test Voice Memory ===")
    print(voice_memory_tool({"action": "status"}))
    print(voice_memory_tool({"action": "remember", "voice": "Aoede", "profile": "eris_emocionada", "emotion": "feliz"}))
    print(voice_memory_tool({"action": "consistent"}))
