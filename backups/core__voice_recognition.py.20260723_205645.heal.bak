"""
voice_recognition.py — ERIS Speaker Verification.
Uses MFCC features + cosine similarity to verify the user's voice.
Lightweight approach: librosa for feature extraction, numpy for comparison.

Workflow:
  1. Enrollment: User speaks 15-30s → extract MFCC → save profile
  2. Verification: User speaks → extract MFCC → compare vs profile
  3. If similarity > threshold → verified, else → rejected
"""
from __future__ import annotations

import io
import json
import os
import time
from pathlib import Path
from typing import Optional

try:
    import numpy as np
    import librosa
    import librosa.feature
    import librosa.util
    _LIBROSA = True
except ImportError:
    _LIBROSA = False

try:
    from sklearn.metrics.pairwise import cosine_similarity
    _SKLEARN = True
except ImportError:
    _SKLEARN = False

_BASE = Path(__file__).resolve().parent.parent
_PROFILE_DIR = _BASE / "data" / "voice_profiles"
_PROFILE_DIR.mkdir(parents=True, exist_ok=True)

# ── Configuration ─────────────────────────────────────────────────────────────

_DEFAULT_THRESHOLD = 0.72
_MIN_AUDIO_SEC = 3.0
_MAX_AUDIO_SEC = 30.0
_N_MFCC = 13
_SR = 16000

# ── Profile management ────────────────────────────────────────────────────────

def _profile_path(user_id: str = "default") -> Path:
    return _PROFILE_DIR / f"{user_id}.json"

def _load_profile(user_id: str = "default") -> Optional[dict]:
    p = _profile_path(user_id)
    if p.exists():
        return json.loads(p.read_text("utf-8"))
    return None

def _save_profile(user_id: str, profile: dict):
    _PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    _profile_path(user_id).write_text(json.dumps(profile, indent=2), "utf-8")

# ── Audio processing ─────────────────────────────────────────────────────────

def _audio_bytes_to_numpy(audio_bytes: bytes) -> np.ndarray:
    """Convert raw PCM audio bytes to numpy array."""
    samples = np.frombuffer(audio_bytes, dtype=np.float32)
    return samples

def _extract_mfcc(audio_bytes: bytes, sr: int = _SR, n_mfcc: int = _N_MFCC) -> Optional[np.ndarray]:
    """
    Extract MFCC features from audio bytes.
    Returns mean MFCC vector (shape: n_mfcc).
    """
    if not _LIBROSA:
        return None

    try:
        samples = _audio_bytes_to_numpy(audio_bytes)

        if len(samples) < sr * 0.5:
            return None

        mfccs = librosa.feature.mfcc(
            y=samples,
            sr=sr,
            n_mfcc=n_mfcc,
            n_fft=512,
            hop_length=256,
        )

        mean_mfcc = np.mean(mfccs, axis=1)
        std_mfcc = np.std(mfccs, axis=1)

        return np.concatenate([mean_mfcc, std_mfcc])

    except Exception as e:
        print(f"[VoiceRec] MFCC extraction error: {e}")
        return None

# ── Enrollment ────────────────────────────────────────────────────────────────

def enroll_voice(audio_bytes: bytes, user_id: str = "default") -> dict:
    """
    Create or update a voice profile from audio samples.
    
    Args:
        audio_bytes: Raw PCM audio bytes (float32, 16kHz)
        user_id: User identifier
    
    Returns:
        dict with status and info
    """
    if not _LIBROSA or not _SKLEARN:
        return {"status": "error", "message": "librosa or scikit-learn not installed"}

    try:
        mfcc = _extract_mfcc(audio_bytes)
        if mfcc is None:
            return {
                "status": "error",
                "message": "Audio too short or invalid. Need at least 0.5 seconds of speech."
            }

        existing = _load_profile(user_id)

        if existing and "mfcc_vectors" in existing:
            existing["mfcc_vectors"].append(mfcc.tolist())
            profile = existing
        else:
            profile = {
                "user_id": user_id,
                "mfcc_vectors": [mfcc.tolist()],
                "created_at": time.time(),
                "updated_at": time.time(),
                "n_samples": 1,
                "threshold": _DEFAULT_THRESHOLD,
            }

        profile["updated_at"] = time.time()
        profile["n_samples"] = len(profile["mfcc_vectors"])

        _save_profile(user_id, profile)

        return {
            "status": "ok",
            "message": f"Voice sample added. Total samples: {profile['n_samples']}",
            "samples": profile["n_samples"],
            "recommendation": "For best results, enroll with 3-5 samples of 5-10 seconds each."
                if profile["n_samples"] < 3 else "Voice profile is ready for verification."
        }

    except Exception as e:
        return {"status": "error", "message": f"Enrollment error: {e}"}

# ── Verification ──────────────────────────────────────────────────────────────

def verify_voice(audio_bytes: bytes, user_id: str = "default") -> dict:
    """
    Verify if the voice matches the enrolled profile.
    
    Args:
        audio_bytes: Raw PCM audio bytes (float32, 16kHz)
        user_id: User identifier
    
    Returns:
        dict with verified (bool), similarity score, and message
    """
    if not _LIBROSA or not _SKLEARN:
        return {"verified": False, "similarity": 0.0, "message": "Voice recognition not available"}

    profile = _load_profile(user_id)
    if not profile or "mfcc_vectors" not in profile:
        return {
            "verified": False,
            "similarity": 0.0,
            "message": "No voice profile enrolled. Say 'Eris, enroll my voice' to set up."
        }

    try:
        mfcc = _extract_mfcc(audio_bytes)
        if mfcc is None:
            return {"verified": False, "similarity": 0.0, "message": "Audio too short"}

        stored_vectors = np.array(profile["mfcc_vectors"])
        query = mfcc.reshape(1, -1)

        similarities = cosine_similarity(query, stored_vectors)[0]
        max_similarity = float(np.max(similarities))
        avg_similarity = float(np.mean(similarities))

        threshold = profile.get("threshold", _DEFAULT_THRESHOLD)
        verified = max_similarity >= threshold

        return {
            "verified": verified,
            "similarity": round(max_similarity, 4),
            "avg_similarity": round(avg_similarity, 4),
            "threshold": threshold,
            "message": "Voice verified" if verified else "Voice not recognized",
        }

    except Exception as e:
        return {"verified": False, "similarity": 0.0, "message": f"Verification error: {e}"}

# ── Profile management ────────────────────────────────────────────────────────

def get_voice_status(user_id: str = "default") -> dict:
    """Get voice profile status."""
    profile = _load_profile(user_id)
    if not profile:
        return {
            "enrolled": False,
            "message": "No voice profile. Say 'Eris, enroll my voice' to set up."
        }

    return {
        "enrolled": True,
        "user_id": profile.get("user_id", user_id),
        "samples": profile.get("n_samples", 0),
        "created": time.strftime("%Y-%m-%d %H:%M", time.localtime(profile.get("created_at", 0))),
        "threshold": profile.get("threshold", _DEFAULT_THRESHOLD),
        "message": f"Voice profile active ({profile.get('n_samples', 0)} samples)",
    }

def reset_voice(user_id: str = "default") -> dict:
    """Delete voice profile."""
    p = _profile_path(user_id)
    if p.exists():
        p.unlink()
        return {"status": "ok", "message": "Voice profile deleted."}
    return {"status": "ok", "message": "No voice profile to delete."}

def set_threshold(threshold: float, user_id: str = "default") -> dict:
    """Set verification threshold (0.5 = lenient, 0.9 = strict)."""
    if not 0.5 <= threshold <= 0.95:
        return {"status": "error", "message": "Threshold must be between 0.5 and 0.95"}

    profile = _load_profile(user_id)
    if not profile:
        return {"status": "error", "message": "No voice profile enrolled"}

    profile["threshold"] = threshold
    _save_profile(user_id, profile)
    return {
        "status": "ok",
        "message": f"Threshold set to {threshold:.2f}",
        "threshold": threshold,
    }

# ── Tool interface ────────────────────────────────────────────────────────────

def voice_recognition(parameters: dict, player=None, **kwargs) -> str:
    """
    Tool declaration for ERIS voice recognition management.
    
    Actions:
        enroll — Start voice enrollment (user speaks for 10-15s)
        verify — Verify current voice against profile
        status — Check voice profile status
        reset — Delete voice profile
        threshold — Set verification threshold
    
    parameters:
        action: enroll | verify | status | reset | threshold
        value: threshold value (for threshold action)
    """
    action = parameters.get("action", "status")
    value = parameters.get("value", None)

    if action == "status":
        info = get_voice_status()
        return info["message"]

    elif action == "enroll":
        return (
            "Para enroll tu voz, necesito que hables durante 10-15 segundos. "
            "Lee este texto en voz alta:\n\n"
            "'Hola Eris, soy tu usuario. Esta es mi voz para que puedas reconocerme. "
            "Quiero que solo respondas cuando yo te hable.'\n\n"
            "Decime 'listo' cuando termines de leer."
        )

    elif action == "verify":
        return "La verificacion de voz se realiza automaticamente cuando hablas. " \
               "Tu voz esta siendo comparada con tu perfil enrollado."

    elif action == "reset":
        return reset_voice()["message"]

    elif action == "threshold":
        if value is not None:
            try:
                t = float(value)
                return set_threshold(t)["message"]
            except (ValueError, TypeError):
                return "Valor invalido. Usa un numero entre 0.5 y 0.95"
        else:
            info = get_voice_status()
            if info.get("enrolled"):
                return f"Threshold actual: {info.get('threshold', _DEFAULT_THRESHOLD):.2f}"
            return "No hay perfil de voz enrollado."

    return f"Accion desconocida: {action}"
