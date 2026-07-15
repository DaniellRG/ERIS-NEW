"""
wake_word.py — ERIS Wake Word Engine.
Usa OpenWakeWord con ONNX runtime para detección local de "Eris".
Fallback: detección por transcripción (Google Speech).

Arquitectura:
  1. OpenWakeWord VAD (voice activity detection) → detecta si hay voz
  2. OpenWakeWord hey_jarvis model → detecta wake word (activación local)
  3. Fallback: Google Speech → verifica "Eris" en el texto transcrito
"""
from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

logger = logging.getLogger("wake_word")

# ── Constants ──────────────────────────────────────────────────────────────────
WAKE_WORD_VARIANTS = ["eris", "hey eris", "hola eris", "oye eris"]

# ── OpenWakeWord wrapper ───────────────────────────────────────────────────────

_oww_model = None


def _patch_oww_paths():
    """Patch OpenWakeWord model paths to use .onnx instead of .tflite on Windows."""
    try:
        import openwakeword
        from openwakeword import MODELS, FEATURE_MODELS

        patched = 0
        for name in list(MODELS.keys()):
            old = MODELS[name]["model_path"]
            if old.endswith(".tflite"):
                new_path = old.replace(".tflite", ".onnx")
                MODELS[name] = {
                    "model_path": new_path,
                    "download_url": MODELS[name].get("download_url", "").replace(".tflite", ".onnx"),
                }
                patched += 1

        for name in list(FEATURE_MODELS.keys()):
            old = FEATURE_MODELS[name]["model_path"]
            if old.endswith(".tflite"):
                new_path = old.replace(".tflite", ".onnx")
                FEATURE_MODELS[name] = {
                    "model_path": new_path,
                    "download_url": FEATURE_MODELS[name].get("download_url", "").replace(".tflite", ".onnx"),
                }
                patched += 1

        if patched:
            logger.info(f"Patched {patched} OpenWakeWord model paths to .onnx")
        return True
    except ImportError:
        logger.debug("openwakeword not installed")
        return False
    except Exception as e:
        logger.warning(f"Error patching OWW paths: {e}")
        return False


def _download_onnx_models():
    """Download ONNX models if not present."""
    try:
        from openwakeword import MODELS, FEATURE_MODELS

        all_items = {}
        all_items.update(MODELS)
        all_items.update(FEATURE_MODELS)

        for _name, info in all_items.items():
            path = Path(info["model_path"])
            if path.exists():
                continue
            url = info.get("download_url", "")
            if not url:
                continue
            logger.info(f"Downloading {path.name}...")
            import urllib.request
            path.parent.mkdir(parents=True, exist_ok=True)
            try:
                urllib.request.urlretrieve(url, path)
                logger.info(f"  OK ({path.stat().st_size} bytes)")
            except Exception as e:
                logger.warning(f"  Failed: {e}")

        return True
    except Exception as e:
        logger.warning(f"Error downloading ONNX models: {e}")
        return False


def oww_available() -> bool:
    """Check if OpenWakeWord can be used."""
    try:
        _patch_oww_paths()
        from openwakeword import Model
        return True
    except ImportError:
        return False
    except Exception:
        return False


def init_oww(model_name: str = "hey_jarvis") -> bool:
    """Initialize the OpenWakeWord model. Returns True on success."""
    global _oww_model

    if _oww_model is not None:
        return True

    if not _patch_oww_paths():
        return False

    _download_onnx_models()

    try:
        from openwakeword import Model
        _oww_model = Model(wakeword_models=[model_name], enable_speex_noise_suppression=False)
        logger.info(f"OpenWakeWord initialized with '{model_name}'")
        return True
    except Exception as e:
        logger.warning(f"Failed to init OpenWakeWord: {e}")
        _oww_model = None
        return False


def predict(audio_bytes: bytes) -> float:
    """Run prediction on audio bytes. Returns confidence score 0.0-1.0."""
    global _oww_model
    if _oww_model is None:
        return 0.0

    try:
        import numpy as np
        samples = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)
        result = _oww_model.predict(samples)
        return max(result.values()) if result else 0.0
    except Exception:
        return 0.0


# ── Transcription-based fallback ───────────────────────────────────────────────

def _load_recognizer():
    """Lazy-load speech recognition."""
    import speech_recognition as sr
    return sr.Recognizer()


def has_wake_word(text: str) -> bool:
    """Check if text contains the wake word 'Eris'."""
    t = text.lower().strip()
    for variant in WAKE_WORD_VARIANTS:
        if variant in t:
            return True
    import re
    if re.search(r'\beris\b', t):
        return True
    return False


# ── Main detector API ─────────────────────────────────────────────────────────

def detect_wake_word(
    audio_bytes: bytes,
    *,
    use_oww: bool = True,
    oww_threshold: float = 0.5,
    enable_transcription: bool = True,
    sample_rate: int = 16000,
) -> tuple[bool, str]:
    """
    Detect wake word in audio.
    Returns (detected, method) where method is 'oww', 'transcription', or ''.
    """
    if use_oww:
        if _oww_model is None:
            init_oww()
        if _oww_model is not None:
            confidence = predict(audio_bytes)
            if confidence >= oww_threshold:
                return True, f"oww({confidence:.2f})"

    if enable_transcription:
        try:
            import speech_recognition as _sr
        except ImportError:
            _sr = None
        if _sr is not None:
            try:
                recognizer = _load_recognizer()
                audio = _sr.AudioData(audio_bytes, sample_rate, 2)
                text = recognizer.recognize_google(audio, language="es-ES")
                if has_wake_word(text):
                    return True, f"transcription({text})"
            except _sr.UnknownValueError:
                pass
            except _sr.RequestError:
                pass
            except Exception:
                pass

    return False, ""
