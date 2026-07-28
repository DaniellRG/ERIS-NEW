"""
actions/voice_enhanced.py — Enhanced voice system for ERIS.
Wake word detection, voice profiles, better TTS control.
"""
import json
import os
from datetime import datetime
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_PROFILES_FILE = _BASE / "data" / "voice_profiles.json"
_STATE_FILE = _BASE / "data" / "voice_state.json"

DEFAULT_PROFILES = {
    "default": {
        "name": "default",
        "voice_id": "default",
        "language": "es",
        "speed": 1.0,
        "pitch": 1.0,
        "volume": 1.0,
        "wake_word": "hey eris",
        "wake_enabled": True,
        "created": datetime.now().isoformat(),
    },
    "spanish_female": {
        "name": "spanish_female",
        "voice_id": "es-female-1",
        "language": "es",
        "speed": 1.1,
        "pitch": 1.2,
        "volume": 1.0,
        "wake_word": "oye eris",
        "wake_enabled": True,
        "created": datetime.now().isoformat(),
    },
    "english_male": {
        "name": "english_male",
        "voice_id": "en-male-1",
        "language": "en",
        "speed": 1.0,
        "pitch": 0.9,
        "volume": 1.0,
        "wake_word": "hey eris",
        "wake_enabled": True,
        "created": datetime.now().isoformat(),
    },
}

def _load_profiles():
    if _PROFILES_FILE.exists():
        try:
            return json.loads(_PROFILES_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return DEFAULT_PROFILES.copy()

def _save_profiles(profiles):
    _PROFILES_FILE.parent.mkdir(parents=True, exist_ok=True)
    _PROFILES_FILE.write_text(json.dumps(profiles, indent=2, ensure_ascii=False), encoding="utf-8")

def _load_state():
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"active_profile": "default", "wake_active": False, "tts_queue": []}

def _save_state(state):
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

def voice_enhanced(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = params.get("action", "status").lower()

    if action == "status":
        state = _load_state()
        profiles = _load_profiles()
        active = state.get("active_profile", "default")
        prof = profiles.get(active, {})
        lines = [
            "Voice Enhanced Status:",
            f"  Active profile: {active}",
            f"  Language: {prof.get('language', '?')}",
            f"  Wake word: '{prof.get('wake_word', '?')}' (enabled: {prof.get('wake_enabled', False)})",
            f"  Speed: {prof.get('speed', 1.0)}x",
            f"  Pitch: {prof.get('pitch', 1.0)}",
            f"  Wake listening: {state.get('wake_active', False)}",
            f"  Available profiles: {len(profiles)}",
        ]
        return "\n".join(lines)

    elif action == "profiles":
        profiles = _load_profiles()
        state = _load_state()
        active = state.get("active_profile", "default")
        lines = [f"Voice Profiles ({len(profiles)}):"]
        for name, prof in profiles.items():
            marker = " ← ACTIVE" if name == active else ""
            lines.append(f"  {name} [{prof.get('language', '?')}] wake='{prof.get('wake_word', '?')}'{marker}")
        return "\n".join(lines)

    elif action == "set_profile":
        name = params.get("name", "")
        profiles = _load_profiles()
        if name not in profiles:
            return f"Profile '{name}' not found. Available: {', '.join(profiles.keys())}"
        state = _load_state()
        state["active_profile"] = name
        _save_state(state)
        return f"Voice profile set to: {name}"

    elif action == "create_profile":
        name = params.get("name", "")
        if not name:
            return "Requires 'name'."
        profiles = _load_profiles()
        if name in profiles:
            return f"Profile '{name}' already exists."
        profiles[name] = {
            "name": name,
            "voice_id": params.get("voice_id", name),
            "language": params.get("language", "es"),
            "speed": float(params.get("speed", 1.0)),
            "pitch": float(params.get("pitch", 1.0)),
            "volume": float(params.get("volume", 1.0)),
            "wake_word": params.get("wake_word", "hey eris"),
            "wake_enabled": params.get("wake_enabled", True),
            "created": datetime.now().isoformat(),
        }
        _save_profiles(profiles)
        return f"Profile '{name}' created."

    elif action == "delete_profile":
        name = params.get("name", "")
        if name == "default":
            return "Cannot delete default profile."
        profiles = _load_profiles()
        if name not in profiles:
            return f"Profile '{name}' not found."
        del profiles[name]
        state = _load_state()
        if state.get("active_profile") == name:
            state["active_profile"] = "default"
            _save_state(state)
        _save_profiles(profiles)
        return f"Profile '{name}' deleted."

    elif action == "set_wake_word":
        word = params.get("word", "")
        if not word:
            return "Requires 'word'."
        state = _load_state()
        profiles = _load_profiles()
        active = state.get("active_profile", "default")
        if active in profiles:
            profiles[active]["wake_word"] = word.lower()
            _save_profiles(profiles)
        return f"Wake word set to: '{word}'"

    elif action == "enable_wake":
        state = _load_state()
        state["wake_active"] = True
        _save_state(state)
        return "Wake word detection ENABLED."

    elif action == "disable_wake":
        state = _load_state()
        state["wake_active"] = False
        _save_state(state)
        return "Wake word detection DISABLED."

    elif action == "set_speed":
        speed = float(params.get("speed", 1.0))
        state = _load_state()
        profiles = _load_profiles()
        active = state.get("active_profile", "default")
        if active in profiles:
            profiles[active]["speed"] = max(0.5, min(3.0, speed))
            _save_profiles(profiles)
        return f"Speed set to: {speed}x"

    elif action == "set_pitch":
        pitch = float(params.get("pitch", 1.0))
        state = _load_state()
        profiles = _load_profiles()
        active = state.get("active_profile", "default")
        if active in profiles:
            profiles[active]["pitch"] = max(0.5, min(2.0, pitch))
            _save_profiles(profiles)
        return f"Pitch set to: {pitch}"

    elif action == "set_language":
        lang = params.get("language", "es")
        state = _load_state()
        profiles = _load_profiles()
        active = state.get("active_profile", "default")
        if active in profiles:
            profiles[active]["language"] = lang
            _save_profiles(profiles)
        return f"Language set to: {lang}"

    elif action == "tts_settings":
        state = _load_state()
        profiles = _load_profiles()
        active = state.get("active_profile", "default")
        prof = profiles.get(active, {})
        return json.dumps(prof, indent=2, ensure_ascii=False)

    elif action == "wake_test":
        state = _load_state()
        profiles = _load_profiles()
        active = state.get("active_profile", "default")
        prof = profiles.get(active, {})
        wake_word = prof.get("wake_word", "hey eris")
        return (
            f"Wake word test:\n"
            f"  Say '{wake_word}' to activate ERIS\n"
            f"  Language: {prof.get('language', 'es')}\n"
            f"  Status: {'LISTENING' if state.get('wake_active') else 'INACTIVE'}"
        )

    return "Actions: status, profiles, set_profile, create_profile, delete_profile, set_wake_word, enable_wake, disable_wake, set_speed, set_pitch, set_language, tts_settings, wake_test"
