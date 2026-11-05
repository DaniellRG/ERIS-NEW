"""Speech-to-Text engine for Eris using faster-whisper."""

import asyncio
import os
import time
from pathlib import Path
from core.platform import safe_print

BASE_DIR = Path(__file__).parent.parent
MODELS_DIR = BASE_DIR / "models" / "whisper"

# Model cache
_STT_MODEL = None
_STT_MODEL_LOCK = None
_STT_MODEL_NAME = "tiny"  # tiny, base, small, medium, large-v3


async def transcribe(audio_bytes: bytes, language: str = "es") -> str:
    """Transcribe audio PCM (16kHz, mono, int16) to text.

    Uses faster-whisper with CTranslate2 backend (CPU, int8).
    Returns transcribed text.
    """
    global _STT_MODEL, _STT_MODEL_LOCK

    if _STT_MODEL is None:
        if _STT_MODEL_LOCK is None:
            import asyncio
            _STT_MODEL_LOCK = asyncio.Lock()
        async with _STT_MODEL_LOCK:
            if _STT_MODEL is None:
                try:
                    from faster_whisper import WhisperModel
                    t0 = time.perf_counter()
                    _STT_MODEL = WhisperModel(_STT_MODEL_NAME, device="cpu", compute_type="int8")
                    print(f"[STT] Whisper model '{_STT_MODEL_NAME}' loaded in {time.perf_counter()-t0:.2f}s")
                except Exception as e:
                    safe_print(f"[STT] ⚠️ Whisper init error: {e}")
                    return ""

    if _STT_MODEL is None:
        return ""

    # Save audio to temp file
    import tempfile
    import struct
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
            import wave
            with wave.open(tmp_path, "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(16000)
                w.writeframes(audio_bytes)

        segments, info = _STT_MODEL.transcribe(tmp_path, beam_size=1, language=language)
        text = " ".join(seg.text for seg in segments).strip()
        return text
    except Exception as e:
        safe_print(f"[STT] ⚠️ Transcription error: {e}")
        return ""
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


async def transcribe_file(file_path: str, language: str = "es") -> str:
    """Transcribe an audio file to text."""
    global _STT_MODEL, _STT_MODEL_LOCK

    if _STT_MODEL is None:
        if _STT_MODEL_LOCK is None:
            import asyncio
            _STT_MODEL_LOCK = asyncio.Lock()
        async with _STT_MODEL_LOCK:
            if _STT_MODEL is None:
                try:
                    from faster_whisper import WhisperModel
                    t0 = time.perf_counter()
                    _STT_MODEL = WhisperModel(_STT_MODEL_NAME, device="cpu", compute_type="int8")
                    print(f"[STT] Whisper model '{_STT_MODEL_NAME}' loaded in {time.perf_counter()-t0:.2f}s")
                except Exception as e:
                    safe_print(f"[STT] ⚠️ Whisper init error: {e}")
                    return ""

    if _STT_MODEL is None:
        return ""

    try:
        segments, info = _STT_MODEL.transcribe(file_path, beam_size=1, language=language)
        text = " ".join(seg.text for seg in segments).strip()
        return text
    except Exception as e:
        safe_print(f"[STT] ⚠️ Transcription error: {e}")
        return ""


def set_model(model_name: str):
    """Set the Whisper model size (tiny, base, small, medium, large-v3)."""
    global _STT_MODEL_NAME, _STT_MODEL
    _STT_MODEL_NAME = model_name
    _STT_MODEL = None  # Force reload


async def warmup_stt():
    """Preload the STT model."""
    global _STT_MODEL
    if _STT_MODEL is not None:
        return True
    r = await transcribe(b"\x00" * 32000)  # 1s of silence
    return True
