"""
core/voice_profile.py — Perfil de voz para Eris

Configuracion unica de voz: tono, velocidad, personalidad.
"""
import json
from datetime import datetime
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_MEMORY = _BASE / "memory"
_CONFIG = _BASE / "config"
_STATE_FILE = _MEMORY / "voice_profile_state.json"
_PROFILE_FILE = _CONFIG / "voice_profile.json"

PROFILES = {
    "eris_default": {
        "name": "Eris Default",
        "voice_name": "Aoede",
        "speed": 1.0,
        "pitch": 1.0,
        "volume": 1.0,
        "description": "Voz natural de Eris",
    },
    "eris_calmada": {
        "name": "Eris Calmada",
        "voice_name": "Aoede",
        "speed": 0.85,
        "pitch": 0.95,
        "volume": 0.9,
        "description": "Voz suave y pausada",
    },
    "eris_emocionada": {
        "name": "Eris Emocionada",
        "voice_name": "Aoede",
        "speed": 1.15,
        "pitch": 1.1,
        "volume": 1.0,
        "description": "Voz animada y rapida",
    },
    "eris_seria": {
        "name": "Eris Seria",
        "voice_name": "Aoede",
        "speed": 0.9,
        "pitch": 0.9,
        "volume": 0.95,
        "description": "Voz formal y directa",
    },
    "eris_juguetona": {
        "name": "Eris Juguetona",
        "voice_name": "Aoede",
        "speed": 1.1,
        "pitch": 1.15,
        "volume": 1.0,
        "description": "Voz alegre y expressiva",
    },
}


def _load_profile() -> dict:
    if _PROFILE_FILE.exists():
        try:
            return json.loads(_PROFILE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return PROFILES["eris_default"].copy()


def _save_profile(profile: dict):
    _PROFILE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _PROFILE_FILE.write_text(json.dumps(profile, indent=2, ensure_ascii=False), encoding="utf-8")


def set_profile(profile_name: str) -> dict:
    if profile_name not in PROFILES:
        return {"error": "Perfil no encontrado: {}".format(profile_name)}
    profile = PROFILES[profile_name].copy()
    profile["set_at"] = datetime.now().isoformat()
    _save_profile(profile)
    return {"status": "perfil_activo", "profile": profile_name, "params": profile}


def get_current_profile() -> dict:
    return _load_profile()


def list_profiles() -> list:
    return [{"name": k, "description": v["description"]} for k, v in PROFILES.items()]


def get_voice_params() -> dict:
    profile = _load_profile()
    return {
        "voice_name": profile.get("voice_name", "Aoede"),
        "speed": profile.get("speed", 1.0),
        "pitch": profile.get("pitch", 1.0),
        "volume": profile.get("volume", 1.0),
    }


def voice_profile_tool(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = params.get("action", "status")

    if action == "status":
        return json.dumps(get_current_profile(), indent=2)
    elif action == "set":
        name = params.get("profile", "")
        if not name:
            return json.dumps({"error": "Nombre de perfil requerido"})
        return json.dumps(set_profile(name), indent=2, default=str)
    elif action == "list":
        return json.dumps({"profiles": list_profiles()}, indent=2)
    elif action == "params":
        return json.dumps(get_voice_params(), indent=2)

    return json.dumps({"error": "Accion desconocida: {}".format(action)})


if __name__ == "__main__":
    print("=== Test Voice Profile ===")
    print(voice_profile_tool({"action": "status"}))
    print(voice_profile_tool({"action": "list"}))
    print(voice_profile_tool({"action": "set", "profile": "eris_emocionada"}))
