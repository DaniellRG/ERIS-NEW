import os
import json
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
CONFIG_DIR = os.path.join(BASE_DIR, "config")
PROFILES_FILE = os.path.join(CONFIG_DIR, "voice_profiles.json")
SAMPLES_DIR = os.path.join(BASE_DIR, "data", "voice_samples")

DEFAULT_VOICES = [
    {"name": "en-US-AriaNeural", "language": "en-US", "gender": "Female"},
    {"name": "en-US-GuyNeural", "language": "en-US", "gender": "Male"},
    {"name": "en-US-JennyNeural", "language": "en-US", "gender": "Female"},
    {"name": "en-GB-SoniaNeural", "language": "en-GB", "gender": "Female"},
    {"name": "en-GB-RyanNeural", "language": "en-GB", "gender": "Male"},
    {"name": "en-AU-NatashaNeural", "language": "en-AU", "gender": "Female"},
    {"name": "en-AU-WilliamNeural", "language": "en-AU", "gender": "Male"},
    {"name": "fr-FR-DeniseNeural", "language": "fr-FR", "gender": "Female"},
    {"name": "de-DE-KatjaNeural", "language": "de-DE", "gender": "Female"},
    {"name": "es-ES-ElviraNeural", "language": "es-ES", "gender": "Female"},
    {"name": "ja-JP-NanamiNeural", "language": "ja-JP", "gender": "Female"},
    {"name": "zh-CN-XiaoxiaoNeural", "language": "zh-CN", "gender": "Female"},
    {"name": "pt-BR-FranciscaNeural", "language": "pt-BR", "gender": "Female"},
    {"name": "ko-KR-SunHiNeural", "language": "ko-KR", "gender": "Female"},
]


def _load_profiles():
    if os.path.exists(PROFILES_FILE):
        with open(PROFILES_FILE, "r") as f:
            return json.load(f)
    return {"active_profile": "default", "profiles": {"default": {
        "voice": "en-US-AriaNeural",
        "speed": "+0%",
        "pitch": "+0Hz",
        "volume": "+0%",
        "created": datetime.now().isoformat()
    }}}


def _save_profiles(data):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(PROFILES_FILE, "w") as f:
        json.dump(data, f, indent=2)


def voice_clone(parameters: dict, player=None) -> str:
    action = parameters.get("action", "list").lower()

    if action == "profile":
        return _get_set_profile(parameters)
    elif action == "samples":
        return _manage_samples(parameters)
    elif action == "quality":
        return _check_quality(parameters)
    elif action == "switch":
        return _switch_voice(parameters)
    elif action in ("list", "list_voices"):
        return _list_voices(parameters)
    elif action == "delete":
        profile_name = parameters.get("profile", "")
        if not profile_name:
            return "'profile' parameter required (or use samples with sub_action=delete)."
        profiles = _load_profiles()
        if profile_name not in profiles["profiles"]:
            return f"Profile '{profile_name}' not found."
        del profiles["profiles"][profile_name]
        _save_profiles(profiles)
        return f"Profile '{profile_name}' deleted."
    elif action == "train":
        return ("Entrenamiento de clon de voz no disponible: requiere un modelo tipo Coqui TTS "
                "/ XTTS v2 (pip install TTS) y GPU. Podés gestionar muestras con 'samples'.")
    elif action == "synthesize":
        return ("Síntesis con voz clonada no disponible sin un modelo entrenado. "
                "Usá la tool 'tts' (edge-tts) para síntesis neural de alta calidad.")
    elif action == "compare":
        return ("Comparación de voces no disponible sin modelos entrenados. "
                "Podés listar voces con 'list_voices' y probar cada una con la tool 'tts'.")
    else:
        return f"Unknown action: {action}. Valid: profile, samples, quality, switch, list, delete, train, synthesize, compare"


def _get_set_profile(parameters: dict):
    profiles = _load_profiles()
    profile_name = parameters.get("profile", profiles.get("active_profile", "default"))

    if "set" in parameters:
        voice = parameters.get("voice", "")
        speed = parameters.get("speed", "+0%")
        pitch = parameters.get("pitch", "+0Hz")
        volume = parameters.get("volume", "+0%")

        if profile_name not in profiles["profiles"]:
            profiles["profiles"][profile_name] = {
                "created": datetime.now().isoformat()
            }

        if voice:
            profiles["profiles"][profile_name]["voice"] = voice
        profiles["profiles"][profile_name]["speed"] = speed
        profiles["profiles"][profile_name]["pitch"] = pitch
        profiles["profiles"][profile_name]["volume"] = volume
        profiles["profiles"][profile_name]["updated"] = datetime.now().isoformat()
        _save_profiles(profiles)
        return f"Profile '{profile_name}' updated."

    if profile_name in profiles["profiles"]:
        p = profiles["profiles"][profile_name]
        lines = [f"Profile: {profile_name}"]
        for k, v in p.items():
            lines.append(f"  {k}: {v}")
        return "\n".join(lines)
    return f"Profile '{profile_name}' not found."


def _manage_samples(parameters: dict):
    os.makedirs(SAMPLES_DIR, exist_ok=True)
    sub_action = parameters.get("sub_action", "list")

    if sub_action == "list":
        samples = [f for f in os.listdir(SAMPLES_DIR) if f.endswith(('.wav', '.mp3', '.ogg'))]
        if not samples:
            return "No voice samples found."
        lines = [f"Voice Samples ({len(samples)}):"]
        for s in samples:
            size = os.path.getsize(os.path.join(SAMPLES_DIR, s))
            lines.append(f"  - {s} ({size} bytes)")
        return "\n".join(lines)

    elif sub_action == "add":
        source = parameters.get("source", "")
        if not source or not os.path.exists(source):
            return "Provide valid 'source' file path."
        import shutil
        dest = os.path.join(SAMPLES_DIR, os.path.basename(source))
        shutil.copy2(source, dest)
        return f"Sample added: {os.path.basename(source)}"

    elif sub_action == "delete":
        name = parameters.get("name", "")
        path = os.path.join(SAMPLES_DIR, name)
        if os.path.exists(path):
            os.remove(path)
            return f"Sample deleted: {name}"
        return f"Sample not found: {name}"

    return "Unknown sub_action. Use: list, add, delete"


def _check_quality(parameters: dict):
    voice = parameters.get("voice", "")
    if not voice:
        profiles = _load_profiles()
        active = profiles.get("active_profile", "default")
        voice = profiles.get("profiles", {}).get(active, {}).get("voice", "en-US-AriaNeural")

    lines = [f"Voice Quality Assessment: {voice}"]
    lines.append(f"  Engine: edge-tts (Microsoft Neural TTS)")
    lines.append(f"  Quality: High (neural network-based)")
    lines.append(f"  Latency: Low (~200-500ms)")
    lines.append(f"  Sample Rate: 24kHz")

    speed = parameters.get("speed", "+0%")
    pitch = parameters.get("pitch", "+0Hz")
    lines.append(f"  Speed: {speed}")
    lines.append(f"  Pitch: {pitch}")

    lines.append(f"  Recommendation: edge-tts provides high-quality neural speech.")
    lines.append(f"  For voice cloning, consider using trained models (requires GPU).")
    return "\n".join(lines)


def _switch_voice(parameters: dict):
    voice = parameters.get("voice", "")
    if not voice:
        return "'voice' parameter required."

    profiles = _load_profiles()
    active = profiles.get("active_profile", "default")
    if active not in profiles["profiles"]:
        profiles["profiles"][active] = {"created": datetime.now().isoformat()}

    profiles["profiles"][active]["voice"] = voice
    profiles["profiles"][active]["updated"] = datetime.now().isoformat()
    _save_profiles(profiles)
    return f"Voice switched to: {voice} (profile: {active})"


def _list_voices(parameters: dict):
    language = parameters.get("language", "")
    gender = parameters.get("gender", "")

    voices = DEFAULT_VOICES
    if language:
        voices = [v for v in voices if v["language"].lower().startswith(language.lower())]
    if gender:
        voices = [v for v in voices if v["gender"].lower() == gender.lower()]

    if not voices:
        return "No voices found matching criteria."

    lines = [f"Available Voices ({len(voices)}):"]
    for v in voices:
        lines.append(f"  - {v['name']} | {v['language']} | {v['gender']}")
    lines.append("\nUse 'switch' action to change voice.")
    lines.append("Full list: https://learn.microsoft.com/en-us/azure/cognitive-services/speech-service/language-support")
    return "\n".join(lines)
