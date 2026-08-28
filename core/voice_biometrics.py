"""
ERIS Voice Biometrics — Speaker recognition para identificar al usuario por su voz.
Usa resemblyzer (d-vector embeddings) para enrollment y matching.

Flujo:
1. Enrollment: grabar N muestras de voz → generar d-vector promedio → guardar perfil
2. Recognition: grabar audio → generar d-vector → comparar con perfiles → identificar
3. Anti-spoofing básico: verificar que el audio no sea replay (varianza de energía)
"""
import json
import os
import time
import struct
import hashlib
from pathlib import Path
from typing import Optional

_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "voice_profiles"
_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Lazy imports
_encoder = None
_wav_helper = None

MIN_SAMPLES_FOR_ENROLLMENT = 3
SIMILARITY_THRESHOLD = 0.65  # cosine similarity threshold


def _get_encoder():
    """Lazy-load resemblyzer encoder."""
    global _encoder
    if _encoder is not None:
        return _encoder
    try:
        from resemblyzer import VoiceEncoder
        _encoder = VoiceEncoder(device="cpu")
        print("[VoiceBio] Encoder loaded (resemblyzer)")
        return _encoder
    except Exception as e:
        print(f"[VoiceBio] Failed to load encoder: {e}")
        return None


def _audio_bytes_to_embedding(audio_bytes: bytes, sample_rate: int = 16000) -> Optional[list]:
    """Convert raw PCM/WAV audio bytes to d-vector embedding."""
    encoder = _get_encoder()
    if encoder is None:
        return None
    try:
        import numpy as np
        import io, wave

        # Try to parse as WAV first
        try:
            with wave.open(io.BytesIO(audio_bytes), 'rb') as wf:
                frames = wf.readframes(wf.getnframes())
                sr = wf.getframerate()
                channels = wf.getnchannels()
                sampwidth = wf.getsampwidth()
        except Exception:
            # Raw PCM assumption
            frames = audio_bytes
            sr = sample_rate
            channels = 1
            sampwidth = 2

        # Convert to numpy
        if sampwidth == 2:
            audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
        elif sampwidth == 4:
            audio = np.frombuffer(frames, dtype=np.int32).astype(np.float32) / 2147483648.0
        else:
            audio = np.frombuffer(frames, dtype=np.float32)

        # Stereo to mono
        if channels == 2:
            audio = audio.reshape(-1, 2).mean(axis=1)

        # Resample if needed (resemblyzer expects 16kHz)
        if sr != 16000:
            try:
                import librosa
                audio = librosa.resample(audio, orig_sr=sr, target_sr=16000)
            except ImportError:
                # Simple downsampling
                ratio = sr // 16000
                audio = audio[::ratio]

        # Trim silence
        audio = encoder.trim_silence(audio)

        if len(audio) < 16000:  # Less than 1 second
            return None

        # Generate embedding
        embedding = encoder.embed_utterance(audio)
        return embedding.tolist()
    except Exception as e:
        print(f"[VoiceBio] Embedding generation failed: {e}")
        return None


def _cosine_similarity(a: list, b: list) -> float:
    """Compute cosine similarity between two vectors."""
    import numpy as np
    a_np = np.array(a, dtype=np.float32)
    b_np = np.array(b, dtype=np.float32)
    norm_a = np.linalg.norm(a_np)
    norm_b = np.linalg.norm(b_np)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a_np, b_np) / (norm_a * norm_b))


def _anti_spoof_check(audio_bytes: bytes) -> dict:
    """Basic anti-spoofing: check audio variance and energy consistency."""
    try:
        import numpy as np
        import io, wave
        with wave.open(io.BytesIO(audio_bytes), 'rb') as wf:
            frames = wf.readframes(wf.getnframes())
        audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0

        energy = np.abs(audio)
        variance = float(np.var(energy))
        mean_energy = float(np.mean(energy))

        # Suspiciously low variance might indicate synthetic/replay audio
        is_suspicious = variance < 0.001 or mean_energy < 0.005
        return {
            "passed": not is_suspicious,
            "variance": round(variance, 6),
            "mean_energy": round(mean_energy, 6),
            "reason": "audio too uniform/quiet" if is_suspicious else "ok",
        }
    except Exception:
        return {"passed": True, "reason": "check skipped"}


def enroll_speaker(name: str, audio_samples: list, overwrite: bool = False) -> dict:
    """
    Enroll a new speaker with multiple audio samples.
    audio_samples: list of bytes (WAV/PCM audio)
    """
    name = name.strip().lower()
    profile_path = _DATA_DIR / f"{name}.json"

    if profile_path.exists() and not overwrite:
        return {"ok": False, "error": f"Profile '{name}' already exists. Use overwrite=True."}

    if len(audio_samples) < MIN_SAMPLES_FOR_ENROLLMENT:
        return {"ok": False, "error": f"Need at least {MIN_SAMPLES_FOR_ENROLLMENT} samples, got {len(audio_samples)}."}

    embeddings = []
    spoof_results = []
    for i, sample in enumerate(audio_samples):
        # Anti-spoof check
        spoof = _anti_spoof_check(sample)
        spoof_results.append(spoof)
        if not spoof["passed"]:
            return {"ok": False, "error": f"Sample {i+1} failed anti-spoof: {spoof['reason']}"}

        emb = _audio_bytes_to_embedding(sample)
        if emb is None:
            return {"ok": False, "error": f"Sample {i+1}: could not generate embedding."}
        embeddings.append(emb)

    # Average embeddings
    import numpy as np
    avg_embedding = np.mean(embeddings, axis=0).tolist()

    # Save profile
    profile = {
        "name": name,
        "enrolled_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "num_samples": len(audio_samples),
        "embedding": avg_embedding,
        "sample_embeddings": embeddings,  # Keep individual for re-enrollment
    }
    with open(profile_path, "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)

    return {"ok": True, "name": name, "samples": len(audio_samples), "profile_path": str(profile_path)}


def identify_speaker(audio_bytes: bytes) -> dict:
    """Identify a speaker from audio against enrolled profiles."""
    emb = _audio_bytes_to_embedding(audio_bytes)
    if emb is None:
        return {"ok": False, "error": "Could not generate embedding from audio."}

    # Anti-spoof
    spoof = _anti_spoof_check(audio_bytes)

    # Load all profiles
    profiles = []
    for f in _DATA_DIR.glob("*.json"):
        try:
            with open(f, "r", encoding="utf-8") as fp:
                profiles.append(json.load(fp))
        except Exception:
            continue

    if not profiles:
        return {"ok": True, "identified": False, "reason": "no profiles enrolled", "anti_spoof": spoof}

    # Find best match
    best_name = None
    best_score = -1
    scores = {}
    for profile in profiles:
        score = _cosine_similarity(emb, profile["embedding"])
        scores[profile["name"]] = round(score, 4)
        if score > best_score:
            best_score = score
            best_name = profile["name"]

    identified = best_score >= SIMILARITY_THRESHOLD
    return {
        "ok": True,
        "identified": identified,
        "speaker": best_name if identified else None,
        "confidence": round(best_score, 4),
        "threshold": SIMILARITY_THRESHOLD,
        "all_scores": scores,
        "anti_spoof": spoof,
    }


def list_profiles() -> list:
    """List all enrolled voice profiles."""
    profiles = []
    for f in _DATA_DIR.glob("*.json"):
        try:
            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp)
                profiles.append({
                    "name": data["name"],
                    "enrolled_at": data.get("enrolled_at"),
                    "samples": data.get("num_samples", 0),
                })
        except Exception:
            continue
    return profiles


def delete_profile(name: str) -> dict:
    """Delete a voice profile."""
    name = name.strip().lower()
    profile_path = _DATA_DIR / f"{name}.json"
    if profile_path.exists():
        profile_path.unlink()
        return {"ok": True, "deleted": name}
    return {"ok": False, "error": f"Profile '{name}' not found."}


def voice_biometrics(parameters: dict = None, player=None) -> str:
    """Tool entry point for Gemini."""
    params = parameters or {}
    action = params.get("action", "identify").lower()

    if action == "identify":
        return "Para identificar un hablante, necesito un clip de audio grabado del micrófono."
    elif action == "enroll":
        return "Para enrollar un nuevo hablante, necesito el nombre y 3+ clips de audio del micrófono."
    elif action == "profiles":
        profiles = list_profiles()
        if not profiles:
            return "No hay perfiles de voz enrollados."
        return "Perfiles:\n" + "\n".join(f"  - {p['name']} ({p['samples']} samples, {p['enrolled_at']})" for p in profiles)
    elif action == "delete":
        name = params.get("name", "")
        if not name:
            return "Necesito 'name' para borrar el perfil."
        result = delete_profile(name)
        return f"Perfil '{name}' eliminado." if result["ok"] else result["error"]
    else:
        return f"Acción '{action}' no reconocida. Usa: identify, enroll, profiles, delete"
