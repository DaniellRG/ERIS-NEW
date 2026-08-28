import asyncio
import json
import os
import struct
import sys
import time
from pathlib import Path
from core.platform import safe_print

try:
    import imageio_ffmpeg
    _FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    _FFMPEG = "ffmpeg"

BASE_DIR = Path(__file__).parent.parent
VOICES_DIR = BASE_DIR / "voices"
API_CFG_PATH = BASE_DIR / "config" / "api_keys.json"

VOICES_DIR.mkdir(exist_ok=True)

_EDGE_VOICES = {
    "es-ar": "es-AR-ElenaNeural",
    "es-es": "es-ES-AlvaroNeural",
    "es-mx": "es-MX-DaliaNeural",
    "en-us": "en-US-JennyNeural",
    "en-gb": "en-GB-SoniaNeural",
}


def _load_cfg():
    try:
        return json.loads(API_CFG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def get_backend() -> str:
    return _load_cfg().get("tts_backend", "gemini")


def get_voice() -> str:
    cfg = _load_cfg()
    backend = cfg.get("tts_backend", "gemini")
    if backend == "elevenlabs":
        return cfg.get("elevenlabs_voice_id", "")
    return cfg.get("tts_voice", "")


def set_backend(backend: str, voice: str = ""):
    cfg = _load_cfg()
    cfg["tts_backend"] = backend
    if voice:
        cfg["tts_voice"] = voice
    API_CFG_PATH.write_text(json.dumps(cfg, indent=4, ensure_ascii=False), encoding="utf-8")


def _save_cfg(cfg: dict):
    API_CFG_PATH.write_text(json.dumps(cfg, indent=4, ensure_ascii=False), encoding="utf-8")


def tts_set_voice(parameters: dict, player=None) -> str:
    """Tool: configura el motor TTS (selecciona voz, velocidad, backend)."""
    action = (parameters.get("action") or "list_voices").lower().strip()
    if action == "list_voices":
        cfg = _load_cfg()
        voices = ", ".join(sorted(set(_EDGE_VOICES.values())))
        return (f"Backend actual: {cfg.get('tts_backend', 'gemini')} | "
                f"Voz: {cfg.get('tts_voice', '')} | Velocidad: {cfg.get('tts_speed', 1.0)}\n"
                f"Voces edge disponibles: {voices}")
    if action == "set_voice":
        voice = (parameters.get("voice") or "").strip()
        if not voice:
            return "Dime el nombre de la voz a usar."
        cfg = _load_cfg()
        cfg["tts_voice"] = voice
        _save_cfg(cfg)
        return f"Voz configurada: {voice}"
    if action == "set_speed":
        try:
            speed = float(parameters.get("speed", 1.0))
        except (TypeError, ValueError):
            return "Velocidad inválida. Usá un número entre 0.5 y 2.0."
        cfg = _load_cfg()
        cfg["tts_speed"] = max(0.5, min(2.0, speed))
        _save_cfg(cfg)
        return f"Velocidad de voz configurada: {cfg['tts_speed']}"
    if action == "set_backend":
        backend = (parameters.get("backend") or "edge").lower().strip()
        if backend not in ("edge", "gemini", "kokoro", "bark", "sapi", "windows", "local", "elevenlabs", "fish"):
            return f"Backend no soportado: {backend}. Opciones: edge, gemini, kokoro, bark, sapi, elevenlabs, fish."
        cfg = _load_cfg()
        cfg["tts_backend"] = backend
        _save_cfg(cfg)
        return f"Backend TTS configurado: {backend}"
    if action == "elevenlabs_voices":
        cfg = _load_cfg()
        api_key = cfg.get("elevenlabs_api_key", "")
        if not api_key:
            return "elevenlabs_api_key no configurado. Agregalo en config/api_keys.json"
        import urllib.request
        try:
            req = urllib.request.Request(
                "https://api.elevenlabs.io/v1/voices",
                headers={"xi-api-key": api_key},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            voices = data.get("voices", [])
            lines = [f"**ElevenLabs voces disponibles:** {len(voices)}\n"]
            for v in voices[:20]:
                labels = v.get("labels", {})
                accent = labels.get("accent", "")
                age = labels.get("age", "")
                gender = labels.get("gender", "")
                desc = labels.get("description", "")
                use = labels.get("use case", "")
                meta = " | ".join(x for x in [gender, age, accent] if x)
                lines.append(f"  • **{v['name']}** ({v['voice_id'][:12]}...) — {meta}")
                if desc or use:
                    lines.append(f"    {desc} {use}")
            if len(voices) > 20:
                lines.append(f"\n  ... y {len(voices) - 20} más")
            return "\n".join(lines)
        except Exception as e:
            return f"Error listando voces ElevenLabs: {str(e)[:150]}"
    if action == "elevenlabs_set_voice":
        voice_id = (parameters.get("voice_id") or "").strip()
        if not voice_id:
            return "Necesitás 'voice_id'. Usá 'elevenlabs_voices' para ver disponibles."
        cfg = _load_cfg()
        cfg["elevenlabs_voice_id"] = voice_id
        cfg["tts_backend"] = "elevenlabs"
        _save_cfg(cfg)
        return f"✅ ElevenLabs configurado: voice_id={voice_id}, backend=elevenlabs"
    return "Acciones: list_voices, set_voice, set_speed, set_backend, elevenlabs_voices, elevenlabs_set_voice"


async def synthesize(text: str, backend: str | None = None, voice: str | None = None,
                     emotion: str | None = None) -> bytes:
    """Synthesize text to PCM audio (24kHz, mono, int16).
    Returns full WAV bytes ready for playback.
    When backend is 'gemini', returns empty bytes (audio comes from Gemini API).
    `emotion` ajusta prosodia (rate/pitch) en backends locales como edge.
    """
    if backend is None:
        backend = get_backend()
    if voice is None:
        voice = get_voice()

    if backend == "gemini":
        return b""

    if backend == "edge":
        return await _synthesize_edge(text, voice, emotion=emotion)

    if backend in ("sapi", "windows", "local"):
        return await _synthesize_sapi(text)

    if backend == "elevenlabs":
        return await _synthesize_elevenlabs(text, voice)

    if backend == "fish":
        return await synthesize_fish_chunked(text, voice)

    if backend == "bark":
        return await _synthesize_bark(text, voice)

    if backend == "kokoro":
        return await _synthesize_kokoro(text, voice)

    return b""


async def _synthesize_elevenlabs(text: str, voice: str = "") -> bytes:
    """Synthesize with ElevenLabs TTS API, return PCM bytes (24kHz, mono, int16)."""
    import urllib.request
    import urllib.error
    import subprocess

    cfg = _load_cfg()
    api_key = cfg.get("elevenlabs_api_key", "")
    if not api_key:
        safe_print("[TTS] ⚠️ elevenlabs_api_key no configurado en api_keys.json")
        return b""

    voice_id = voice or cfg.get("elevenlabs_voice_id", "21m00Tcm4TlvDq8ikWAM")
    model_id = cfg.get("elevenlabs_model_id", "eleven_multilingual_v2")

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = json.dumps({
        "text": text,
        "model_id": model_id,
        "voice_settings": {
            "stability": cfg.get("elevenlabs_stability", 0.5),
            "similarity_boost": cfg.get("elevenlabs_similarity", 0.75),
            "style": cfg.get("elevenlabs_style", 0.0),
            "use_speaker_boost": True,
        },
    }).encode("utf-8")

    try:
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            mp3_data = resp.read()
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")[:200]
        except Exception:
            pass
        safe_print(f"[TTS] ⚠️ ElevenLabs error {e.code}: {body}")
        return b""
    except Exception as e:
        safe_print(f"[TTS] ⚠️ ElevenLabs error: {e}")
        return b""

    if not mp3_data or len(mp3_data) < 100:
        return b""

    _flags = 0x08000000 if sys.platform == "win32" else 0
    proc = await asyncio.create_subprocess_exec(
        _FFMPEG, "-y", "-i", "pipe:0",
        "-f", "s16le", "-acodec", "pcm_s16le",
        "-ar", "24000", "-ac", "1",
        "pipe:1",
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        creationflags=_flags,
    )
    pcm, _ = await proc.communicate(input=mp3_data)
    return pcm


async def _synthesize_fish(text: str, voice: str = "") -> bytes:
    """Synthesize with Fish Audio TTS API, return PCM bytes (24kHz, mono, int16).
    Optimized for LOW LATENCY: opus format, streaming, reduced sample rate."""
    import urllib.request
    import urllib.error
    import subprocess

    cfg = _load_cfg()
    api_key = cfg.get("fish_api_key", "")
    if not api_key:
        safe_print("[TTS] fish_api_key no configurado en api_keys.json")
        return b""

    voice_id = voice or cfg.get("fish_voice_id", "d942b64244ef4c47b0d4a34d5301c796")
    model = cfg.get("fish_model", "s2.1-pro-free")

    url = "https://api.fish.audio/v1/tts"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "model": model,
    }
    payload = json.dumps({
        "text": text,
        "reference_id": voice_id,
        "format": "opus",
        "sample_rate": 48000,
        "opus_bitrate": 32000,
        "latency": "low",
        "temperature": 0.7,
        "top_p": 0.7,
        "chunk_length": 200,
        "normalize": True,
    }).encode("utf-8")

    try:
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=20) as resp:
            opus_data = resp.read()
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")[:200]
        except Exception:
            pass
        safe_print(f"[TTS] Fish Audio error {e.code}: {body}")
        return b""
    except Exception as e:
        safe_print(f"[TTS] Fish Audio error: {e}")
        return b""

    if not opus_data or len(opus_data) < 100:
        return b""

    _flags = 0x08000000 if sys.platform == "win32" else 0
    proc = await asyncio.create_subprocess_exec(
        _FFMPEG, "-y", "-i", "pipe:0",
        "-f", "s16le", "-acodec", "pcm_s16le",
        "-ar", "24000", "-ac", "1",
        "pipe:1",
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        creationflags=_flags,
    )
    pcm, _ = await proc.communicate(input=opus_data)
    return pcm


def _split_text_chunks(text: str, max_len: int = 480) -> list:
    """Split text into chunks respecting sentence boundaries, each under max_len chars."""
    import re
    chunks = []
    # Split on sentence boundaries
    sentences = re.split(r'(?<=[.!?])\s+', text)
    current = ""
    for sent in sentences:
        if len(current) + len(sent) + 1 <= max_len:
            current = (current + " " + sent).strip()
        else:
            if current:
                chunks.append(current)
            current = sent
    if current:
        chunks.append(current)
    return chunks if chunks else [text[:max_len]]


async def synthesize_fish_chunked(text: str, voice: str = "") -> bytes:
    """Synthesize text with Fish Audio, splitting into chunks if needed (500 char limit).
    Returns concatenated PCM audio (24kHz, mono, int16)."""
    chunks = _split_text_chunks(text, max_len=480)
    all_pcm = b""
    for chunk in chunks:
        pcm = await _synthesize_fish(chunk, voice)
        if pcm:
            all_pcm += pcm
    return all_pcm


async def synthesize_fish_streaming(text: str, voice: str = "", on_chunk=None):
    """Synthesize with Fish Audio using streaming for lower time-to-first-audio."""
    import urllib.request
    import urllib.error
    import subprocess

    cfg = _load_cfg()
    api_key = cfg.get("fish_api_key", "")
    if not api_key:
        return b""

    voice_id = voice or cfg.get("fish_voice_id", "d942b64244ef4c47b0d4a34d5301c796")
    model = cfg.get("fish_model", "s2.1-pro-free")

    url = "https://api.fish.audio/v1/tts"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "model": model,
    }
    payload = json.dumps({
        "text": text,
        "reference_id": voice_id,
        "format": "opus",
        "sample_rate": 48000,
        "opus_bitrate": 32000,
        "latency": "low",
        "temperature": 0.7,
        "top_p": 0.7,
        "chunk_length": 200,
        "normalize": True,
    }).encode("utf-8")

    try:
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        resp = urllib.request.urlopen(req, timeout=20)
        all_opus = b""
        while True:
            chunk = resp.read(4096)
            if not chunk:
                break
            all_opus += chunk
            if on_chunk and len(all_opus) >= 2048:
                on_chunk(all_opus)
                all_opus = b""
        if all_opus:
            # Final decode remaining
            _flags = 0x08000000 if sys.platform == "win32" else 0
            proc = await asyncio.create_subprocess_exec(
                _FFMPEG, "-y", "-i", "pipe:0",
                "-f", "s16le", "-acodec", "pcm_s16le",
                "-ar", "24000", "-ac", "1",
                "pipe:1",
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                creationflags=_flags,
            )
            pcm, _ = await proc.communicate(input=all_opus)
            return pcm
        return b""
    except Exception as e:
        safe_print(f"[TTS] Fish Audio streaming error: {e}")
        return b""


async def _synthesize_edge(text: str, voice: str = "", emotion: str | None = None) -> bytes:
    """Synthesize with Edge-TTS, return WAV PCM bytes."""
    import edge_tts

    if not voice or voice == "bark" or voice not in _EDGE_VOICES.values():
        voice = _EDGE_VOICES.get("es-ar", "es-AR-ElenaNeural")

    rate = "+0%"
    pitch = "+0Hz"
    try:
        cfg = _load_cfg()
        speed = float(cfg.get("tts_speed", 1.0))
        tone = {"speed": 1.0, "pitch": 1.0}
        if emotion:
            try:
                from core.emotional_tone import emotion_to_voice
                tone = emotion_to_voice(emotion) or tone
            except Exception:
                pass
        speed = speed * float(tone.get("speed", 1.0))
        if speed and speed != 1.0:
            rate = f"{'+' if speed > 1 else ''}{int(round((speed - 1) * 100))}%"
        p = float(tone.get("pitch", 1.0))
        if p and p != 1.0:
            pitch = f"{'+' if p > 1 else ''}{int(round((p - 1) * 50))}Hz"
    except Exception:
        rate = "+0%"
        pitch = "+0Hz"

    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    audio_chunks: list[bytes] = []

    # Timeout: si Edge TTS tarda mas de 15 segundos, cortar
    _edge_timeout = 15.0
    _start_time = __import__("time").time()
    async for chunk in communicate.stream():
        if __import__("time").time() - _start_time > _edge_timeout:
            print(f"[TTS] Edge TTS timeout ({_edge_timeout}s) — cortando")
            break
        if chunk["type"] == "audio":
            audio_chunks.append(chunk["data"])

    if not audio_chunks:
        return b""

    raw = b"".join(audio_chunks)

    # Convert MP3 bytes to PCM via ffmpeg
    import subprocess

    _flags = 0x08000000 if sys.platform == "win32" else 0
    proc = await asyncio.create_subprocess_exec(
        _FFMPEG, "-y", "-i", "pipe:0",
        "-f", "s16le", "-acodec", "pcm_s16le",
        "-ar", "24000", "-ac", "1",
        "pipe:1",
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        creationflags=_flags,
    )
    pcm, _ = await asyncio.wait_for(proc.communicate(input=raw), timeout=10.0)
    return pcm


async def _synthesize_sapi(text: str) -> bytes:
    """Synthesize with Windows SAPI (pyttsx3) — 100% offline, no internet needed.

    Genera el audio a un WAV temporal y lo re-codifica a PCM 24kHz mono int16
    para que suene consistente con el resto de backends.
    """
    import pyttsx3

    tmp_wav = str(BASE_DIR / "data" / "_eris_sapi_tmp.wav")
    try:
        engine = pyttsx3.init()
        engine.setProperty("rate", 175)
        try:
            engine.setProperty("volume", 1.0)
        except Exception:
            pass
        engine.save_to_file(text, tmp_wav)
        engine.runAndWait()
    except Exception as e:
        safe_print(f"[TTS] ⚠️ SAPI error: {e}")
        return b""

    import asyncio
    import subprocess

    _flags = 0x08000000 if sys.platform == "win32" else 0
    proc = await asyncio.create_subprocess_exec(
        _FFMPEG, "-y", "-i", tmp_wav,
        "-f", "s16le", "-acodec", "pcm_s16le",
        "-ar", "24000", "-ac", "1",
        "pipe:1",
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        creationflags=_flags,
    )
    pcm, _ = await proc.communicate()
    try:
        import os
        os.remove(tmp_wav)
    except Exception:
        pass
    return pcm


async def _synthesize_bark(text: str, voice: str = "") -> bytes:
    """Synthesize with Bark + optional voice adaptation."""
    import torch
    import numpy as np
    from transformers import BarkModel, AutoProcessor

    device = "cuda" if torch.cuda.is_available() else "cpu"

    model = BarkModel.from_pretrained(
        "suno/bark-small",
        torch_dtype=torch.float16 if device == "cuda" else torch.float32,
    ).to(device)
    processor = AutoProcessor.from_pretrained("suno/bark-small")

    # Load voice prompt if available
    voice_prompt = None
    if voice:
        voice_path = VOICES_DIR / f"{voice}.npz"
        if voice_path.exists():
            try:
                voice_prompt = np.load(str(voice_path))
            except Exception:
                pass

    inputs = processor(
        text=[text],
        voice_preset=voice_prompt,
        return_tensors="pt",
    ).to(device)

    with torch.no_grad():
        audio_array = model.generate(**inputs, do_sample=True)
        audio_array = audio_array.cpu().numpy().squeeze()

    # Normalize to int16
    audio_array = np.clip(audio_array, -1, 1)
    pcm = (audio_array * 32767).astype(np.int16).tobytes()
    return pcm


# ── Kokoro-82M via pykokoro ───────────────────────────────────────────────────
_KOKORO_PIPELINE = None
_KOKORO_PIPELINE_LOCK = None
_KOKORO_VOICES = {
    "ef_dora": "Kokoro español (mujer, Dora)",
    "em_alex": "Kokoro español (hombre, Alex)",
    "em_santa": "Kokoro español (hombre, Santa)",
}


async def _synthesize_kokoro(text: str, voice: str = "") -> bytes:
    global _KOKORO_PIPELINE, _KOKORO_PIPELINE_LOCK

    if not voice or voice not in _KOKORO_VOICES:
        voice = "ef_dora"

    if _KOKORO_PIPELINE is None:
        if _KOKORO_PIPELINE_LOCK is None:
            import asyncio
            _KOKORO_PIPELINE_LOCK = asyncio.Lock()
        async with _KOKORO_PIPELINE_LOCK:
            if _KOKORO_PIPELINE is None:
                try:
                    from pykokoro import KokoroPipeline, PipelineConfig
                    from pykokoro.pipeline_config import TokenizerConfig
                    from espeakng_loader import load_library
                    load_library()
                    t0 = time.perf_counter()
                    tk_cfg = TokenizerConfig(backend="espeak", use_spacy=True)
                    cfg = PipelineConfig(
                        voice=voice,
                        provider="cpu",
                        tokenizer_config=tk_cfg,
                    )
                    _KOKORO_PIPELINE = KokoroPipeline(cfg)
                    print(f"[TTS] Kokoro pipeline cargado en {time.perf_counter()-t0:.2f}s")
                except Exception as e:
                    safe_print(f"[TTS] ⚠️ Kokoro pipeline init error: {e}")
                    return b""

    try:
        result = _KOKORO_PIPELINE.run(text)
        audio = result.audio
        if audio is None or len(audio) == 0:
            return b""
        import numpy as np
        if audio.dtype in (np.float32, np.float64):
            audio = (np.clip(audio, -1, 1) * 32767).astype(np.int16)
        else:
            audio = audio.astype(np.int16)
        return audio.tobytes()
    except Exception as e:
        safe_print(f"[TTS] ⚠️ Kokoro error: {e}")
        return b""


async def warmup_kokoro():
    """Precarga el pipeline Kokoro para evitar delay en primera síntesis."""
    if _KOKORO_PIPELINE is not None:
        return True
    r = await _synthesize_kokoro("Hola.", "ef_dora")
    return len(r) > 0


async def list_voices() -> list[dict]:
    """List available TTS backends and voices."""
    result = []

    result.append({"backend": "gemini", "name": "Gemini (voz por defecto)", "type": "cloud"})

    result.append({"backend": "edge", "name": "Edge-TTS español", "type": "local", "voice": "es-AR-ElenaNeural"})
    result.append({"backend": "edge", "name": "Edge-TTS español España", "type": "local", "voice": "es-ES-AlvaroNeural"})

    result.append({"backend": "sapi", "name": "Windows SAPI (100% offline)", "type": "local", "voice": "Sistema"})

    for vname, vlabel in _KOKORO_VOICES.items():
        result.append({"backend": "kokoro", "name": vlabel, "type": "local", "voice": vname})

    for v_file in VOICES_DIR.glob("*.npz"):
        voice_name = v_file.stem
        result.append({"backend": "bark", "name": f"Bark: {voice_name}", "type": "local", "voice": voice_name})

    # ElevenLabs voces conocidas
    cfg = _load_cfg()
    if cfg.get("elevenlabs_api_key"):
        _EL_PRESETS = {
            "21m00Tcm4TlvDq8ikWAM": "Rachel (mujer, natural) [premium]",
            "ErXwobaYiN019PkySvjV": "Antoni (hombre, profesional) [premium]",
            "VR6AewLTigWG4xSOukaG": "Arnold (hombre, grave) [premium]",
            "pNInz6obpgDQGcFmaJgB": "Adam (hombre, narrador) [premium]",
            "f9DFWr0Y8aHd6VNMEdTt": "Amaia (mujer, español) [gratuita]",
        }
        for vid, vname in _EL_PRESETS.items():
            result.append({"backend": "elevenlabs", "name": f"ElevenLabs: {vname}", "type": "cloud", "voice": vid})
        custom_id = cfg.get("elevenlabs_voice_id", "")
        if custom_id and custom_id not in _EL_PRESETS:
            result.append({"backend": "elevenlabs", "name": f"ElevenLabs: Custom ({custom_id[:8]}...)", "type": "cloud", "voice": custom_id})

    return result


def extract_voice_embedding(audio_path: str, voice_name: str) -> str:
    """Extract speaker embedding from audio for Bark voice cloning.
    
    Args:
        audio_path: Path to reference audio file (WAV/MP3)
        voice_name: Name to save the voice as (e.g., 'gaby')
    
    Returns:
        Path to saved embedding file
    """
    import torch
    import numpy as np
    import soundfile as sf
    from transformers import AutoProcessor, BarkModel

    device = "cuda" if torch.cuda.is_available() else "cpu"

    # Load audio
    audio, sr = sf.read(audio_path)
    if sr != 16000:
        from scipy import signal
        target_len = int(len(audio) * 16000 / sr)
        audio = signal.resample(audio, target_len)

    # Load Bark model for encoding
    processor = AutoProcessor.from_pretrained("suno/bark-small")
    model = BarkModel.from_pretrained("suno/bark-small").to(device)

    # Encode audio
    inputs = processor(
        audio=audio, sampling_rate=16000,
        return_tensors="pt",
    ).to(device)

    with torch.no_grad():
        embedding = model.audio_encoder(**inputs).last_hidden_state.mean(dim=1).cpu().numpy()

    # Save
    out_path = VOICES_DIR / f"{voice_name}.npz"
    np.savez_compressed(str(out_path), embedding=embedding)
    return str(out_path)


# ── Streaming ElevenLabs + Dynamic Emotion ─────────────────────────────────────

_EMOTION_PROFILES = {
    "happy":     {"stability": 0.2, "style": 0.75, "similarity_boost": 0.9},
    "smiling":   {"stability": 0.2, "style": 0.65, "similarity_boost": 0.88},
    "excited":   {"stability": 0.15, "style": 0.85, "similarity_boost": 0.92},
    "thinking":  {"stability": 0.4, "style": 0.25, "similarity_boost": 0.8},
    "neutral":   {"stability": 0.25, "style": 0.55, "similarity_boost": 0.88},
    "sad":       {"stability": 0.5, "style": 0.5, "similarity_boost": 0.85},
    "worried":   {"stability": 0.45, "style": 0.4, "similarity_boost": 0.85},
    "angry":     {"stability": 0.15, "style": 0.7, "similarity_boost": 0.88},
    "serious":   {"stability": 0.4, "style": 0.2, "similarity_boost": 0.82},
    "mysterious": {"stability": 0.35, "style": 0.5, "similarity_boost": 0.88},
    "playful":   {"stability": 0.15, "style": 0.8, "similarity_boost": 0.9},
    "calm":      {"stability": 0.45, "style": 0.2, "similarity_boost": 0.85},
    "surprised": {"stability": 0.12, "style": 0.8, "similarity_boost": 0.92},
    "disgusted": {"stability": 0.3, "style": 0.55, "similarity_boost": 0.85},
    "fearful":   {"stability": 0.2, "style": 0.6, "similarity_boost": 0.85},
    "warm":      {"stability": 0.25, "style": 0.6, "similarity_boost": 0.9},
    "loving":    {"stability": 0.2, "style": 0.7, "similarity_boost": 0.92},
    "sassy":     {"stability": 0.18, "style": 0.75, "similarity_boost": 0.88},
    "gentle":    {"stability": 0.35, "style": 0.4, "similarity_boost": 0.9},
}

def _get_emotion_profile(emotion: str = "neutral") -> dict:
    """Return voice_settings for an emotional state."""
    return _EMOTION_PROFILES.get(emotion.lower().strip(), _EMOTION_PROFILES["neutral"])


async def synthesize_elevenlabs_streaming(
    text_chunk: str,
    voice: str = "",
    emotion: str = "neutral",
    play_audio=None,
):
    """Synthesize with ElevenLabs streaming API: sends full text, receives audio
    progressively, decodes all at once for gap-free continuous speech."""
    import subprocess

    cfg = _load_cfg()
    api_key = cfg.get("elevenlabs_api_key", "")
    if not api_key or not text_chunk.strip():
        return b""

    voice_id = voice or cfg.get("elevenlabs_voice_id", "0ASlVJI7QecvFHVE5VQk")
    model_id = cfg.get("elevenlabs_model_id", "eleven_multilingual_v2")
    profile = _get_emotion_profile(emotion)

    import urllib.request
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
    }
    payload = json.dumps({
        "text": text_chunk,
        "model_id": model_id,
        "voice_settings": {
            "stability": profile["stability"],
            "similarity_boost": profile["similarity_boost"],
            "style": profile["style"],
            "use_speaker_boost": True,
        },
    }).encode("utf-8")

    try:
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        resp = urllib.request.urlopen(req, timeout=60)
    except Exception as e:
        safe_print(f"[TTS] ⚠️ ElevenLabs stream error: {e}")
        return b""

    # Read ALL MP3 data from the streaming response (fast, no decoding gaps)
    mp3_data = resp.read()

    if not mp3_data or len(mp3_data) < 100:
        return b""

    # Decode entire MP3 at once — no pauses between sentences
    _flags = 0x08000000 if sys.platform == "win32" else 0
    proc = await asyncio.create_subprocess_exec(
        _FFMPEG, "-y", "-i", "pipe:0",
        "-f", "s16le", "-acodec", "pcm_s16le",
        "-ar", "24000", "-ac", "1",
        "pipe:1",
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        creationflags=_flags,
    )
    pcm, _ = await proc.communicate(input=mp3_data)

    if pcm and play_audio:
        try:
            play_audio(pcm)
        except Exception:
            pass

    return pcm if pcm else b""
