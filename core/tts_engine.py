import asyncio
import json
import os
import struct
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
    return _load_cfg().get("tts_voice", "")


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
        if backend not in ("edge", "gemini", "kokoro", "bark"):
            return f"Backend no soportado: {backend}. Opciones: edge, gemini, kokoro, bark."
        cfg = _load_cfg()
        cfg["tts_backend"] = backend
        _save_cfg(cfg)
        return f"Backend TTS configurado: {backend}"
    return "Acciones: list_voices, set_voice, set_speed, set_backend"


async def synthesize(text: str, backend: str | None = None, voice: str | None = None) -> bytes:
    """Synthesize text to PCM audio (24kHz, mono, int16).
    Returns full WAV bytes ready for playback.
    When backend is 'gemini', returns empty bytes (audio comes from Gemini API).
    """
    if backend is None:
        backend = get_backend()
    if voice is None:
        voice = get_voice()

    if backend == "gemini":
        return b""

    if backend == "edge":
        return await _synthesize_edge(text, voice)

    if backend == "bark":
        return await _synthesize_bark(text, voice)

    if backend == "kokoro":
        return await _synthesize_kokoro(text, voice)

    return b""


async def _synthesize_edge(text: str, voice: str = "") -> bytes:
    """Synthesize with Edge-TTS, return WAV PCM bytes."""
    import edge_tts

    if not voice or voice == "bark" or voice not in _EDGE_VOICES.values():
        voice = _EDGE_VOICES.get("es-ar", "es-AR-ElenaNeural")

    rate = ""
    try:
        speed = float(_load_cfg().get("tts_speed", 1.0))
        if speed and speed != 1.0:
            rate = f"{'+' if speed > 1 else ''}{int(round((speed - 1) * 100))}%"
    except Exception:
        rate = ""

    communicate = edge_tts.Communicate(text, voice, rate=rate)
    audio_chunks: list[bytes] = []
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_chunks.append(chunk["data"])

    if not audio_chunks:
        return b""

    raw = b"".join(audio_chunks)

    # Convert MP3 bytes to PCM via ffmpeg
    import subprocess

    proc = await asyncio.create_subprocess_exec(
        _FFMPEG, "-y", "-i", "pipe:0",
        "-f", "s16le", "-acodec", "pcm_s16le",
        "-ar", "24000", "-ac", "1",
        "pipe:1",
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
    )
    pcm, _ = await proc.communicate(input=raw)
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

    for vname, vlabel in _KOKORO_VOICES.items():
        result.append({"backend": "kokoro", "name": vlabel, "type": "local", "voice": vname})

    for v_file in VOICES_DIR.glob("*.npz"):
        voice_name = v_file.stem
        result.append({"backend": "bark", "name": f"Bark: {voice_name}", "type": "local", "voice": voice_name})

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
