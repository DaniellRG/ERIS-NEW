import json

from core.logging_setup import API_CONFIG_PATH

LIVE_MODEL          = "models/gemini-2.5-flash-native-audio-preview-12-2025"
CHANNELS            = 1
SEND_SAMPLE_RATE    = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE          = 256      # 16ms chunks — mic input (keep small for low latency)
PLAY_CHUNK_SIZE     = 480      # 20ms chunks — playback (smaller = lower latency)

_cached_api_key: str | None = None


def resolve_device(name_sub: str, kind: str = "input") -> int | None:
    """Find a device index by name substring (e.g. 'HAYLOU'). Returns None if not found."""
    import sounddevice as sd
    for i in range(len(sd.query_devices())):
        d = sd.query_devices(i)
        if name_sub.lower() in d["name"].lower():
            if kind == "input" and d["max_input_channels"] > 0:
                return i
            if kind == "output" and d["max_output_channels"] > 0:
                return i
    return None


def get_api_key() -> str:
    global _cached_api_key
    if _cached_api_key:
        return _cached_api_key
    with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
        _cached_api_key = json.load(f)["gemini_api_key"]
    return _cached_api_key


ERIS_VOICES = {
    "Aoede":  ("Femenina", "Cálida y sofisticada — ideal para asistente IA"),
    "Kore":   ("Femenina", "Suave y precisa"),
    "Leda":   ("Femenina", "Natural y fluida"),
    "Zephyr": ("Femenina", "Dinámica y expresiva"),
    "Charon": ("Masculina", "Profunda y seria — voz original de ERIS"),
    "Puck":   ("Masculina", "Ágil y versátil"),
    "Fenrir": ("Masculina", "Grave y autoritaria"),
    "Orus":   ("Masculina", "Clásica y equilibrada"),
}


def get_eris_voice() -> str:
    try:
        cfg = json.loads(API_CONFIG_PATH.read_text(encoding="utf-8"))
        return cfg.get("eris_voice", cfg.get("jarvis_voice", "Aoede"))
    except Exception:
        return "Aoede"
