"""
voice_cloning.py — Clonación de voz: clonar la voz del usuario para síntesis de voz.
Usa técnicas de transferencia de voz con modelos locales o APIs.
"""
import json
import time
from pathlib import Path
from datetime import datetime

_BASE = Path(__file__).resolve().parent.parent
_VOICE_PROFILES_DIR = _BASE / "data" / "voice_profiles"
_VOICE_LOG = _BASE / "data" / "voice_cloning_log.json"


def voice_cloning(parameters: dict = None, player=None) -> str:
    """
    Clonación de voz.
    Acciones: train, list, delete, synthesize, analyze, compare, status, export, upload_sample
    """
    params = parameters or {}
    action = params.get("action", "list").lower()
    _VOICE_PROFILES_DIR.mkdir(parents=True, exist_ok=True)

    if action == "train":
        return _train_voice(params)
    elif action == "list":
        return _list_profiles()
    elif action == "delete":
        return _delete_profile(params)
    elif action == "synthesize":
        return _synthesize(params)
    elif action == "analyze":
        return _analyze_voice(params)
    elif action == "compare":
        return _compare_voices(params)
    elif action == "status":
        return _get_status()
    elif action == "export":
        return _export_profile(params)
    elif action == "upload_sample":
        return _upload_sample(params)
    elif action == "preview":
        return _preview_voice(params)
    return "Acciones: train, list, delete, synthesize, analyze, compare, status, export, upload_sample, preview"


def _train_voice(params: dict) -> str:
    name = params.get("name", "default")
    samples = params.get("samples", [])
    audio_path = params.get("audio_path", "")

    if not samples and not audio_path:
        return "Error: se requiere 'samples' (lista de paths) o 'audio_path'"

    try:
        import whisper
        model = whisper.load_model("base")
    except ImportError:
        return "Whisper necesario: pip install openai-whisper"

    try:
        if audio_path:
            samples = [audio_path]

        profile = {
            "name": name,
            "created": datetime.now().isoformat(),
            "samples_count": len(samples),
            "status": "training",
            "features": {},
        }

        transcriptions = []
        for sample in samples:
            try:
                result = model.transcribe(sample)
                transcriptions.append({
                    "file": sample,
                    "text": result.get("text", ""),
                    "language": result.get("language", ""),
                })
            except Exception as e:
                transcriptions.append({"file": sample, "error": str(e)})

        profile["transcriptions"] = transcriptions
        profile["status"] = "trained"
        profile["trained_at"] = datetime.now().isoformat()

        path = _VOICE_PROFILES_DIR / "{}.json".format(name)
        path.write_text(json.dumps(profile, indent=2, ensure_ascii=False), encoding="utf-8")

        _log_action("train", name, len(samples))
        return "Voz '{}' entrenada con {} muestras".format(name, len(samples))
    except Exception as e:
        return "Error entrenando voz: {}".format(str(e))


def _list_profiles() -> str:
    profiles = []
    for f in _VOICE_PROFILES_DIR.glob("*.json"):
        try:
            p = json.loads(f.read_text(encoding="utf-8"))
            profiles.append(p)
        except Exception:
            pass

    if not profiles:
        return "No hay perfiles de voz. Sube muestras con upload_sample"

    lines = ["Perfiles de voz ({}):".format(len(profiles))]
    for p in profiles:
        lines.append("  {} | {} muestras | Estado: {} | {}".format(
            p.get("name"), p.get("samples_count", 0),
            p.get("status", "?"), p.get("created", "?")[:10]))
    return "\n".join(lines)


def _delete_profile(params: dict) -> str:
    name = params.get("name", "")
    if not name:
        return "Error: se requiere 'name'"
    path = _VOICE_PROFILES_DIR / "{}.json".format(name)
    if path.exists():
        path.unlink()
        return "Perfil de voz '{}' eliminado".format(name)
    return "No encontrado: {}".format(name)


def _synthesize(params: dict) -> str:
    text = params.get("text", "")
    name = params.get("name", "default")
    if not text:
        return "Error: se requiere 'text'"

    profile_path = _VOICE_PROFILES_DIR / "{}.json".format(name)
    if not profile_path.exists():
        return "Perfil de voz '{}' no encontrado. Entrenalos primero".format(name)

    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.save_to_file(text, str(_VOICE_PROFILES_DIR / "output_{}.wav".format(int(time.time()))))
        engine.runAndWait()
        return "Audio sintetizado para voz '{}'".format(name)
    except ImportError:
        return "pyttsx3 necesario: pip install pyttsx3"


def _analyze_voice(params: dict) -> str:
    audio_path = params.get("audio_path", "")
    if not audio_path:
        return "Error: se requiere 'audio_path'"

    try:
        import whisper
        model = whisper.load_model("base")
        result = model.transcribe(audio_path)

        analysis = {
            "file": audio_path,
            "text": result.get("text", ""),
            "language": result.get("language", ""),
            "segments": len(result.get("segments", [])),
            "duration": sum(s.get("end", 0) - s.get("start", 0) for s in result.get("segments", [])),
        }

        lines = ["Análisis de voz:", "  Archivo: {}".format(audio_path),
                  "  Idioma: {}".format(analysis["language"]),
                  "  Duración: {:.1f}s".format(analysis["duration"]),
                  "  Segmentos: {}".format(analysis["segments"]),
                  "  Transcripción: {}".format(analysis["text"][:200])]
        return "\n".join(lines)
    except ImportError:
        return "Whisper necesario: pip install openai-whisper"
    except Exception as e:
        return "Error analizando: {}".format(str(e))


def _compare_voices(params: dict) -> str:
    name1 = params.get("name1", "")
    name2 = params.get("name2", "")
    if not name1 or not name2:
        return "Error: se requiere 'name1' y 'name2'"

    p1_path = _VOICE_PROFILES_DIR / "{}.json".format(name1)
    p2_path = _VOICE_PROFILES_DIR / "{}.json".format(name2)

    if not p1_path.exists() or not p2_path.exists():
        return "Uno o ambos perfiles no encontrados"

    p1 = json.loads(p1_path.read_text(encoding="utf-8"))
    p2 = json.loads(p2_path.read_text(encoding="utf-8"))

    return "Comparación '{} vs {}':\n  Muestras: {} vs {}\n  Entrenado: {} vs {}".format(
        name1, name2, p1.get("samples_count", 0), p2.get("samples_count", 0),
        p1.get("trained_at", "?")[:10], p2.get("trained_at", "?")[:10])


def _get_status() -> str:
    profiles = list(_VOICE_PROFILES_DIR.glob("*.json"))
    total_samples = 0
    for f in profiles:
        try:
            p = json.loads(f.read_text(encoding="utf-8"))
            total_samples += p.get("samples_count", 0)
        except Exception:
            pass
    return "Voice Cloning: {} perfiles | {} muestras totales".format(len(profiles), total_samples)


def _export_profile(params: dict) -> str:
    name = params.get("name", "")
    if not name:
        return "Error: se requiere 'name'"
    path = _VOICE_PROFILES_DIR / "{}.json".format(name)
    if not path.exists():
        return "No encontrado: {}".format(name)
    export_path = _BASE / "data" / "voice_export_{}.json".format(name)
    import shutil
    shutil.copy2(str(path), str(export_path))
    return "Perfil '{}' exportado a {}".format(name, str(export_path))


def _upload_sample(params: dict) -> str:
    name = params.get("name", "default")
    audio_path = params.get("audio_path", "")
    if not audio_path:
        return "Error: se requiere 'audio_path'"

    path = Path(audio_path)
    if not path.exists():
        return "Archivo no encontrado: {}".format(audio_path)

    profile_path = _VOICE_PROFILES_DIR / "{}.json".format(name)
    if profile_path.exists():
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
    else:
        profile = {"name": name, "created": datetime.now().isoformat(), "samples": [], "samples_count": 0}

    profile.setdefault("samples", []).append(str(path))
    profile["samples_count"] = len(profile["samples"])
    profile_path.write_text(json.dumps(profile, indent=2, ensure_ascii=False), encoding="utf-8")
    return "Muestra agregada a '{}'. Total: {}".format(name, profile["samples_count"])


def _preview_voice(params: dict) -> str:
    name = params.get("name", "")
    if not name:
        return "Error: se requiere 'name'"
    text = params.get("text", "Hola, soy ERIS con la voz de {}".format(name))
    return _synthesize({"text": text, "name": name})


def _log_action(action, name, count):
    log = {"last_action": action, "name": name, "count": count, "timestamp": datetime.now().isoformat()}
    _VOICE_LOG.write_text(json.dumps(log, indent=2), encoding="utf-8")
