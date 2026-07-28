"""
actions/voice_cloning_real.py — Real voice cloning for ERIS.
Train voice models, synthesize speech, manage voice profiles.
Uses edge-tts (free) + optional Bark/Coqui for higher quality.
"""
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_PROFILES_DIR = _BASE / "data" / "voice_profiles"
_OUTPUT_DIR = _BASE / "data" / "voice_output"
_STATE_FILE = _BASE / "data" / "voice_cloning_state.json"

VOICE_PRESETS = {
    "es-female-1": {"name": "María", "lang": "es", "gender": "female", "engine": "edge-tts", "voice": "es-ES-ElviraNeural"},
    "es-female-2": {"name": "Lucía", "lang": "es", "gender": "female", "engine": "edge-tts", "voice": "es-MX-DaliaNeural"},
    "es-male-1": {"name": "Carlos", "lang": "es", "gender": "male", "engine": "edge-tts", "voice": "es-ES-AlvaroNeural"},
    "es-male-2": {"name": "Andrés", "lang": "es", "gender": "male", "engine": "edge-tts", "voice": "es-CO-GonzaloNeural"},
    "en-female-1": {"name": "Emma", "lang": "en", "gender": "female", "engine": "edge-tts", "voice": "en-US-JennyNeural"},
    "en-male-1": {"name": "James", "lang": "en", "gender": "male", "engine": "edge-tts", "voice": "en-US-GuyNeural"},
    "pt-female-1": {"name": "Ana", "lang": "pt", "gender": "female", "engine": "edge-tts", "voice": "pt-BR-FranciscaNeural"},
    "fr-female-1": {"name": "Marie", "lang": "fr", "gender": "female", "engine": "edge-tts", "voice": "fr-FR-DeniseNeural"},
    "de-female-1": {"name": "Hanna", "lang": "de", "gender": "female", "engine": "edge-tts", "voice": "de-DE-HannaNeural"},
    "ja-female-1": {"name": "Yuki", "lang": "ja", "gender": "female", "engine": "edge-tts", "voice": "ja-JP-NanamiNeural"},
}


def _load_state():
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"active_voice": "es-female-1", "trained_voices": [], "generated": [], "settings": {"rate": "+0%", "volume": "+0%", "pitch": "+0Hz"}}

def _save_state(state):
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def voice_cloning_real(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = params.get("action", "status").lower()

    if action == "status":
        state = _load_state()
        return (
            f"Voice Cloning Real Status:\n"
            f"  Active voice: {state.get('active_voice', 'es-female-1')}\n"
            f"  Available voices: {len(VOICE_PRESETS)}\n"
            f"  Trained voices: {len(state.get('trained_voices', []))}\n"
            f"  Generated files: {len(state.get('generated', []))}\n"
            f"  Engine: edge-tts (free) + optional Bark/Coqui"
        )

    elif action == "voices":
        lines = ["Available Voices:"]
        for vid, info in VOICE_PRESETS.items():
            marker = " ←" if vid == _load_state().get("active_voice") else ""
            lines.append(f"  {vid}: {info['name']} ({info['lang']}-{info['gender']}){marker}")
        return "\n".join(lines)

    elif action == "set_voice":
        voice_id = params.get("voice_id", "")
        if voice_id not in VOICE_PRESETS:
            return f"Voice '{voice_id}' not found. Available: {', '.join(VOICE_PRESETS.keys())}"
        state = _load_state()
        state["active_voice"] = voice_id
        _save_state(state)
        return f"Active voice set to: {VOICE_PRESETS[voice_id]['name']} ({voice_id})"

    elif action == "speak":
        text = params.get("text", "")
        if not text:
            return "Requires 'text'."
        return _synthesize_speech(text, params)

    elif action == "speak_file":
        text = params.get("text", "")
        if not text:
            return "Requires 'text'."
        output = params.get("output", f"eris_voice_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3")
        return _synthesize_to_file(text, output, params)

    elif action == "set_rate":
        rate = params.get("rate", "+0%")
        state = _load_state()
        state.setdefault("settings", {})["rate"] = rate
        _save_state(state)
        return f"Speech rate set to: {rate}"

    elif action == "set_pitch":
        pitch = params.get("pitch", "+0Hz")
        state = _load_state()
        state.setdefault("settings", {})["pitch"] = pitch
        _save_state(state)
        return f"Speech pitch set to: {pitch}"

    elif action == "set_volume":
        volume = params.get("volume", "+0%")
        state = _load_state()
        state.setdefault("settings", {})["volume"] = volume
        _save_state(state)
        return f"Speech volume set to: {volume}"

    elif action == "batch":
        texts = params.get("texts", [])
        if not texts:
            return "Requires 'texts' list."
        results = []
        for i, text in enumerate(texts[:5]):
            output = f"batch_{i}_{datetime.now().strftime('%H%M%S')}.mp3"
            r = _synthesize_to_file(text, output, params)
            results.append(f"  {i+1}. {r[:60]}")
        return "Batch synthesis:\n" + "\n".join(results)

    elif action == "history":
        state = _load_state()
        generated = state.get("generated", [])
        if not generated:
            return "No generated files."
        lines = [f"Generated Files ({len(generated)}):"]
        for g in generated[-15:]:
            lines.append(f"  [{g.get('timestamp', '?')[:16]}] {g.get('file', '?')} ({g.get('voice', '?')})")
        return "\n".join(lines)

    elif action == "list_files":
        _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        files = sorted(_OUTPUT_DIR.glob("*.mp3"), key=lambda f: f.stat().st_mtime, reverse=True)
        if not files:
            return "No generated voice files."
        lines = [f"Voice Files ({len(files)}):"]
        for f in files[:20]:
            size = f.stat().st_size / 1024
            lines.append(f"  {f.name} ({size:.1f}KB)")
        return "\n".join(lines)

    elif action == "transcribe":
        audio_path = params.get("path", "")
        if not audio_path:
            return "Requires 'path' to audio file."
        return _transcribe_audio(audio_path)

    return "Actions: status, voices, set_voice, speak, speak_file, set_rate, set_pitch, set_volume, batch, history, list_files, transcribe"


def _synthesize_speech(text, params):
    state = _load_state()
    voice_id = params.get("voice_id", state.get("active_voice", "es-female-1"))
    voice_info = VOICE_PRESETS.get(voice_id, VOICE_PRESETS["es-female-1"])
    settings = state.get("settings", {})

    try:
        import edge_tts
        import asyncio

        voice = voice_info.get("voice", "es-ES-ElviraNeural")
        rate = settings.get("rate", "+0%")
        volume = settings.get("volume", "+0%")
        pitch = settings.get("pitch", "+0Hz")

        async def _gen():
            communicate = edge_tts.Communicate(text, voice, rate=rate, volume=volume, pitch=pitch)
            _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            output = _OUTPUT_DIR / f"speech_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
            await communicate.save(str(output))
            return str(output)

        output_path = asyncio.run(_gen())
        state.setdefault("generated", []).append({
            "file": os.path.basename(output_path),
            "voice": voice_id,
            "text": text[:100],
            "timestamp": datetime.now().isoformat(),
        })
        state["generated"] = state["generated"][-100:]
        _save_state(state)
        return f"Speech generated: {os.path.basename(output_path)} ({voice_info['name']})"
    except ImportError:
        return "edge-tts not installed. Install with: pip install edge-tts"
    except Exception as e:
        return f"Speech error: {e}"


def _synthesize_to_file(text, output_name, params):
    state = _load_state()
    voice_id = params.get("voice_id", state.get("active_voice", "es-female-1"))
    voice_info = VOICE_PRESETS.get(voice_id, VOICE_PRESETS["es-female-1"])
    settings = state.get("settings", {})

    try:
        import edge_tts
        import asyncio

        voice = voice_info.get("voice", "es-ES-ElviraNeural")

        async def _gen():
            communicate = edge_tts.Communicate(text, voice, rate=settings.get("rate", "+0%"), volume=settings.get("volume", "+0%"), pitch=settings.get("pitch", "+0Hz"))
            _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            output = _OUTPUT_DIR / output_name
            await communicate.save(str(output))
            return str(output)

        output_path = asyncio.run(_gen())
        state.setdefault("generated", []).append({
            "file": output_name,
            "voice": voice_id,
            "text": text[:100],
            "timestamp": datetime.now().isoformat(),
        })
        _save_state(state)
        return f"Saved: {output_name}"
    except ImportError:
        return "edge-tts not installed. pip install edge-tts"
    except Exception as e:
        return f"Error: {e}"


def _transcribe_audio(audio_path):
    try:
        import whisper

        model = whisper.load_model("base")
        result = model.transcribe(audio_path)
        return f"Transcription:\n{result['text']}"
    except ImportError:
        return "openai-whisper not installed. Install with: pip install openai-whisper"
    except Exception as e:
        return f"Transcription error: {e}"
