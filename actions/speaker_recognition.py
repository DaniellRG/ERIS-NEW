# -*- coding: utf-8 -*-
"""
speaker_recognition.py — ERIS Speaker Recognition & Voice Analysis.
Identifies WHO is speaking, gender, pitch, tone, and voice characteristics.

Uses: sounddevice (mic capture), numpy/scipy (audio analysis), speech_recognition (STT).
Speaker identification via MFCC-like feature extraction + cosine similarity.

Actions:
  enroll       — Record voice sample to identify a speaker
  identify     — Record audio and identify who is speaking
  analyze      — Analyze voice characteristics (pitch, gender, energy, etc.)
  diarize      — Record conversation and identify who spoke when
  profiles     — List enrolled speakers
  delete       — Remove a speaker profile
  record       — Record audio sample (raw)
  compare      — Compare two audio files
  status       — System status
"""
import json
import os
import time
import threading
import tempfile
import wave
from datetime import datetime
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.fftpack import fft
from scipy.signal import lfilter, butter

BASE_DIR = Path(__file__).resolve().parent.parent
PROFILES_DIR = BASE_DIR / "data" / "voice_profiles"
SPEAKER_DB = BASE_DIR / "data" / "speaker_db.json"

# ── Audio constants ──
SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = "int16"
FRAME_DURATION_MS = 30  # 30ms frames
PRE_EMPHASIS = 0.97
N_FFT = 512
N_MFCC = 13
N_MELS = 26


# ═══════════════════════════════════════════════════════════════
# AUDIO CAPTURE
# ═══════════════════════════════════════════════════════════════

def _capture_audio(duration: float = 3.0, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Capture audio from default microphone for `duration` seconds."""
    import sounddevice as sd
    frames = int(duration * sample_rate)
    audio = sd.rec(frames, samplerate=sample_rate, channels=CHANNELS, dtype=DTYPE)
    sd.wait()
    return audio.flatten().astype(np.float64) / 32768.0


def _capture_audio_thread(duration: float = 3.0) -> np.ndarray:
    """Capture audio in a thread (non-blocking for longer recordings)."""
    return _capture_audio(duration)


def _save_wav(audio: np.ndarray, path: str, sample_rate: int = SAMPLE_RATE):
    """Save audio array as WAV file."""
    audio_int16 = (audio * 32767).astype(np.int16)
    with wave.open(path, "w") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio_int16.tobytes())


def _load_wav(path: str) -> tuple:
    """Load WAV file, return (sample_rate, audio_array)."""
    sr, data = wavfile.read(path)
    if data.dtype != np.float64:
        data = data.astype(np.float64) / 32768.0
    return sr, data


# ═══════════════════════════════════════════════════════════════
# FEATURE EXTRACTION — MFCC-like voice fingerprinting
# ═══════════════════════════════════════════════════════════════

def _pre_emphasis(signal: np.ndarray) -> np.ndarray:
    """Apply pre-emphasis filter to boost high frequencies."""
    return np.append(signal[0], signal[1:] - PRE_EMPHASIS * signal[:-1])


def _mel_filterbank(sr: int, n_filters: int, n_fft: int) -> np.ndarray:
    """Create mel filterbank matrix."""
    low_freq_mel = 0
    high_freq_mel = 2595 * np.log10(1 + (sr / 2) / 700)
    mel_points = np.linspace(low_freq_mel, high_freq_mel, n_filters + 2)
    hz_points = 700 * (10 ** (mel_points / 2595) - 1)
    bin_points = np.floor((n_fft + 1) * hz_points / sr).astype(int)

    filters = np.zeros((n_filters, n_fft // 2 + 1))
    for i in range(n_filters):
        for j in range(bin_points[i], bin_points[i + 1]):
            if bin_points[i + 1] != bin_points[i]:
                filters[i, j] = (j - bin_points[i]) / (bin_points[i + 1] - bin_points[i])
        for j in range(bin_points[i + 1], bin_points[i + 2]):
            if bin_points[i + 2] != bin_points[i + 1]:
                filters[i, j] = (bin_points[i + 2] - j) / (bin_points[i + 2] - bin_points[i + 1])
    return filters


def _extract_mfcc(audio: np.ndarray, sr: int = SAMPLE_RATE) -> np.ndarray:
    """Extract MFCC features from audio (voice fingerprint)."""
    # Pre-emphasis
    emphasized = _pre_emphasis(audio)

    # Frame the signal
    frame_len = int(0.025 * sr)  # 25ms frames
    frame_step = int(0.010 * sr)  # 10ms step
    frame_len_samples = frame_len
    frame_step_samples = frame_step

    signal_len = len(emphasized)
    num_frames = int(np.ceil((signal_len - frame_len_samples) / frame_step_samples)) + 1

    # Pad signal
    pad_len = num_frames * frame_step_samples + frame_len_samples
    padded = np.append(emphasized, np.zeros(pad_len - signal_len))

    # Create frames
    indices = np.arange(0, pad_len - frame_len_samples, frame_step_samples).reshape(-1, 1)
    frames = padded[indices + np.arange(frame_len_samples)]

    # Apply Hamming window
    hamming = np.hamming(frame_len_samples)
    frames *= hamming

    # FFT
    mag_frames = np.absolute(fft(frames, N_FFT))
    pow_frames = (1.0 / N_FFT) * (mag_frames[:, :N_FFT // 2 + 1] ** 2)

    # Mel filterbank
    filters = _mel_filterbank(sr, N_MELS, N_FFT)
    filter_banks = np.dot(pow_frames, filters.T)
    filter_banks = np.where(filter_banks == 0, np.finfo(float).eps, filter_banks)
    filter_banks = 20 * np.log10(filter_banks)

    # MFCC via DCT approximation (simplified)
    n_frames = filter_banks.shape[0]
    mfcc = np.zeros((n_frames, N_MFCC))
    for i in range(N_MFCC):
        mfcc[:, i] = np.sum(filter_banks * np.cos(np.pi * i * np.arange(N_MELS) / N_MELS), axis=1)

    return mfcc


def _compute_speaker_embedding(audio: np.ndarray, sr: int = SAMPLE_RATE) -> np.ndarray:
    """Compute a speaker embedding (fingerprint) from audio."""
    mfcc = _extract_mfcc(audio, sr)
    if len(mfcc) == 0:
        return np.zeros(N_MFCC * 3)

    # Statistical features: mean, std, delta-mean, delta-std, delta2-mean, delta2-std
    mean = np.mean(mfcc, axis=0)
    std = np.std(mfcc, axis=0)

    # Delta (first derivative)
    delta = np.diff(mfcc, axis=0)
    delta_mean = np.mean(delta, axis=0) if len(delta) > 0 else np.zeros(N_MFCC)
    delta_std = np.std(delta, axis=0) if len(delta) > 0 else np.zeros(N_MFCC)

    # Delta-delta (second derivative)
    delta2 = np.diff(delta, axis=0) if len(delta) > 1 else np.zeros((1, N_MFCC))
    delta2_mean = np.mean(delta2, axis=0)
    delta2_std = np.std(delta2, axis=0)

    embedding = np.concatenate([mean, std, delta_mean, delta_std, delta2_mean, delta2_std])
    # Normalize
    norm = np.linalg.norm(embedding)
    if norm > 0:
        embedding = embedding / norm
    return embedding


# ═══════════════════════════════════════════════════════════════
# VOICE ANALYSIS
# ═══════════════════════════════════════════════════════════════

def _analyze_pitch(audio: np.ndarray, sr: int = SAMPLE_RATE) -> dict:
    """Analyze pitch (fundamental frequency) of audio."""
    # Autocorrelation method
    audio_np = np.array(audio, dtype=np.float64)
    corr = np.correlate(audio_np, audio_np, mode="full")
    corr = corr[len(corr) // 2:]

    # Find first peak after zero crossing
    d = np.diff(corr)
    starts = np.where(d > 0)[0]
    if len(starts) == 0:
        return {"fundamental_hz": 0, "pitch_category": "unknown"}

    # Find the first strong peak
    min_lag = int(sr / 500)  # Max 500 Hz
    max_lag = int(sr / 50)   # Min 50 Hz

    if max_lag > len(corr):
        max_lag = len(corr) - 1

    search = corr[min_lag:max_lag]
    if len(search) == 0:
        return {"fundamental_hz": 0, "pitch_category": "unknown"}

    peak_idx = np.argmax(search) + min_lag
    f0 = sr / peak_idx if peak_idx > 0 else 0

    # Classify
    if f0 < 85:
        category = "very_low"
    elif f0 < 165:
        category = "low_male"
    elif f0 < 185:
        category = "ambiguous"
    elif f0 < 255:
        category = "female"
    else:
        category = "high_child"

    return {"fundamental_hz": round(f0, 1), "pitch_category": category}


def _analyze_energy(audio: np.ndarray) -> dict:
    """Analyze energy/loudness of audio."""
    rms = np.sqrt(np.mean(audio ** 2))
    peak = np.max(np.abs(audio))
    db_rms = 20 * np.log10(rms + 1e-10)
    db_peak = 20 * np.log10(peak + 1e-10)

    return {
        "rms_energy": round(float(rms), 4),
        "peak_amplitude": round(float(peak), 4),
        "db_rms": round(float(db_rms), 1),
        "db_peak": round(float(db_peak), 1),
    }


def _analyze_spectral(audio: np.ndarray, sr: int = SAMPLE_RATE) -> dict:
    """Analyze spectral characteristics."""
    spectrum = np.abs(fft(audio))
    freqs = np.fft.fftfreq(len(audio), 1 / sr)

    # Only positive frequencies
    pos_mask = freqs > 0
    pos_freqs = freqs[pos_mask]
    pos_spectrum = spectrum[pos_mask]

    # Spectral centroid (brightness)
    centroid = np.sum(pos_freqs * pos_spectrum) / (np.sum(pos_spectrum) + 1e-10)

    # Spectral bandwidth
    bandwidth = np.sqrt(np.sum(((pos_freqs - centroid) ** 2) * pos_spectrum) / (np.sum(pos_spectrum) + 1e-10))

    # Spectral rolloff (85%)
    cumsum = np.cumsum(pos_spectrum)
    rolloff_idx = np.searchsorted(cumsum, 0.85 * cumsum[-1])
    rolloff = pos_freqs[min(rolloff_idx, len(pos_freqs) - 1)]

    # Dominant frequencies (top 3)
    top_idx = np.argsort(pos_spectrum)[-3:][::-1]
    dominant = [round(float(pos_freqs[i]), 1) for i in top_idx]

    return {
        "centroid_hz": round(float(centroid), 1),
        "bandwidth_hz": round(float(bandwidth), 1),
        "rolloff_hz": round(float(rolloff), 1),
        "dominant_freqs": dominant,
    }


def _analyze_gender(audio: np.ndarray, sr: int = SAMPLE_RATE) -> dict:
    """Estimate gender from voice characteristics."""
    pitch = _analyze_pitch(audio, sr)
    spectral = _analyze_spectral(audio, sr)
    energy = _analyze_energy(audio)

    f0 = pitch["fundamental_hz"]
    centroid = spectral["centroid_hz"]

    # Simple heuristic: combine pitch and spectral features
    score_male = 0
    score_female = 0

    if f0 < 165:
        score_male += 2
    elif f0 < 185:
        score_male += 1
        score_female += 1
    elif f0 < 255:
        score_female += 2
    else:
        score_female += 3

    if centroid < 1500:
        score_male += 1
    elif centroid > 2500:
        score_female += 1

    total = score_male + score_female
    confidence = max(score_male, score_female) / total if total > 0 else 0.5

    gender = "male" if score_male > score_female else "female" if score_female > score_male else "ambiguous"

    return {
        "estimated_gender": gender,
        "confidence": round(confidence, 2),
        "male_score": score_male,
        "female_score": score_female,
    }


# ═══════════════════════════════════════════════════════════════
# SPEAKER DATABASE
# ═══════════════════════════════════════════════════════════════

def _load_db() -> dict:
    """Load speaker database."""
    try:
        if SPEAKER_DB.exists():
            return json.loads(SPEAKER_DB.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"speakers": {}}


def _save_db(db: dict):
    """Save speaker database."""
    SPEAKER_DB.parent.mkdir(parents=True, exist_ok=True)
    SPEAKER_DB.write_text(json.dumps(db, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


# ═══════════════════════════════════════════════════════════════
# MAIN FUNCTION
# ═══════════════════════════════════════════════════════════════

def speaker_recognition(parameters: dict, player=None) -> str:
    """
    Speaker Recognition & Voice Analysis for ERIS.
    Actions:
      enroll    — Record voice to identify a speaker (params: name, duration)
      identify  — Record audio and identify who is speaking (params: duration)
      analyze   — Analyze voice characteristics (params: duration OR file)
      diarize   — Record conversation and identify speakers (params: duration)
      profiles  — List enrolled speakers
      delete    — Remove speaker profile (params: name)
      record    — Record raw audio sample (params: duration, save_path)
      compare   — Compare two speakers (params: name1, name2)
      status    — System status
    """
    action = parameters.get("action", "status").lower()
    duration = float(parameters.get("duration", 3.0))
    name = parameters.get("name", "")

    # ── STATUS ──
    if action == "status":
        db = _load_db()
        n_speakers = len(db.get("speakers", {}))
        profiles_exists = PROFILES_DIR.exists()
        return (
            f"Speaker Recognition Status\n"
            f"  Speakers enrolled: {n_speakers}\n"
            f"  Profiles dir: {'exists' if profiles_exists else 'missing'}\n"
            f"  Sample rate: {SAMPLE_RATE} Hz\n"
            f"  MFCC features: {N_MFCC}\n"
            f"  Embedding size: {N_MFCC * 3}"
        )

    # ── PROFILES ──
    if action == "profiles":
        db = _load_db()
        speakers = db.get("speakers", {})
        if not speakers:
            return "No speakers enrolled. Use 'enroll' to add one."
        lines = [f"Enrolled Speakers ({len(speakers)}):\n"]
        for sname, sdata in speakers.items():
            n_samples = len(sdata.get("samples", []))
            gender = sdata.get("gender", "unknown")
            created = sdata.get("created", "?")[:10]
            lines.append(f"  {sname}: gender={gender}, samples={n_samples}, created={created}")
        return "\n".join(lines)

    # ── DELETE ──
    if action == "delete":
        if not name:
            return "Error: 'name' required"
        db = _load_db()
        if name not in db.get("speakers", {}):
            return f"Speaker '{name}' not found."
        del db["speakers"][name]
        _save_db(db)
        # Also delete audio files
        spk_dir = PROFILES_DIR / name
        if spk_dir.exists():
            import shutil
            shutil.rmtree(spk_dir)
        return f"Speaker '{name}' deleted."

    # ── ENROLL ──
    if action == "enroll":
        if not name:
            return "Error: 'name' required (e.g. 'daniel', 'maria')"

        if player:
            player.write_log(f"[speaker_recognition] Grabando voz de '{name}' ({duration}s)...")

        # Capture audio
        audio = _capture_audio(duration)

        # Check if audio is too quiet (silence)
        rms = np.sqrt(np.mean(audio ** 2))
        if rms < 0.01:
            return "Error: Audio too quiet. Make sure the microphone is working and try again."

        # Extract embedding
        embedding = _compute_speaker_embedding(audio)

        # Analyze gender
        gender_info = _analyze_gender(audio)

        # Save to database
        db = _load_db()
        if "speakers" not in db:
            db["speakers"] = {}

        if name not in db["speakers"]:
            db["speakers"][name] = {
                "name": name,
                "created": datetime.now().isoformat(),
                "samples": [],
                "gender": gender_info["estimated_gender"],
            }

        # Save audio sample
        spk_dir = PROFILES_DIR / name
        spk_dir.mkdir(parents=True, exist_ok=True)
        sample_idx = len(db["speakers"][name]["samples"])
        audio_path = str(spk_dir / f"sample_{sample_idx}.wav")
        _save_wav(audio, audio_path)

        # Store embedding
        db["speakers"][name]["samples"].append({
            "embedding": embedding.tolist(),
            "path": audio_path,
            "gender": gender_info["estimated_gender"],
            "gender_confidence": gender_info["confidence"],
            "recorded_at": datetime.now().isoformat(),
        })

        # Update average embedding
        all_embeddings = [s["embedding"] for s in db["speakers"][name]["samples"]]
        db["speakers"][name]["avg_embedding"] = np.mean(all_embeddings, axis=0).tolist()

        _save_db(db)

        if player:
            player.write_log(f"[speaker_recognition] '{name}' enrolled ({gender_info['estimated_gender']})")

        return (
            f"Speaker '{name}' enrolled!\n"
            f"  Gender: {gender_info['estimated_gender']} (confidence: {gender_info['confidence']})\n"
            f"  Samples: {sample_idx + 1}\n"
            f"  Embedding size: {len(embedding)}\n"
            f"  Saved to: {audio_path}"
        )

    # ── IDENTIFY ──
    if action == "identify":
        db = _load_db()
        speakers = db.get("speakers", {})
        if not speakers:
            return "No speakers enrolled. Use 'enroll' first."

        if player:
            player.write_log("[speaker_recognition] Identifying speaker...")

        # Capture audio
        audio = _capture_audio(duration)

        # Check if audio is too quiet
        rms = np.sqrt(np.mean(audio ** 2))
        if rms < 0.01:
            return "Error: Audio too quiet. No voice detected."

        # Extract embedding
        embedding = _compute_speaker_embedding(audio)

        # Analyze voice characteristics
        pitch_info = _analyze_pitch(audio)
        energy_info = _analyze_energy(audio)
        spectral_info = _analyze_spectral(audio)
        gender_info = _analyze_gender(audio)

        # Match against all speakers
        scores = {}
        for sname, sdata in speakers.items():
            avg_emb = np.array(sdata.get("avg_embedding", []))
            if len(avg_emb) == 0:
                continue
            sim = _cosine_similarity(embedding, avg_emb)
            scores[sname] = round(sim, 4)

        # Sort by similarity
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        # Build result
        lines = ["VOICE IDENTIFICATION\n"]

        if sorted_scores:
            best_name, best_score = sorted_scores[0]
            confidence_pct = round(best_score * 100, 1)

            if confidence_pct > 70:
                lines.append(f"  IDENTIFIED: {best_name} (confidence: {confidence_pct}%)")
            elif confidence_pct > 40:
                lines.append(f"  LIKELY: {best_name} (confidence: {confidence_pct}%)")
            else:
                lines.append(f"  UNKNOWN (best match: {best_name} at {confidence_pct}%)")

            lines.append(f"\n  All matches:")
            for sname, score in sorted_scores[:5]:
                pct = round(score * 100, 1)
                lines.append(f"    {sname}: {pct}%")
        else:
            lines.append("  No matches found.")

        lines.append(f"\n  Voice Characteristics:")
        lines.append(f"    Pitch: {pitch_info['fundamental_hz']} Hz ({pitch_info['pitch_category']})")
        lines.append(f"    Gender: {gender_info['estimated_gender']} ({gender_info['confidence']})")
        lines.append(f"    Energy: {energy_info['db_rms']} dB RMS")
        lines.append(f"    Spectral centroid: {spectral_info['centroid_hz']} Hz")

        if player:
            player.write_log(f"[speaker_recognition] Identified: {sorted_scores[0][0] if sorted_scores else 'unknown'}")

        return "\n".join(lines)

    # ── ANALYZE ──
    if action == "analyze":
        # Check if analyzing from file or live
        file_path = parameters.get("file", "")
        if file_path and os.path.exists(file_path):
            sr_audio, audio = _load_wav(file_path)
        else:
            if player:
                player.write_log("[speaker_recognition] Analyzing voice...")
            audio = _capture_audio(duration)
            sr_audio = SAMPLE_RATE

        # Run all analyses
        pitch_info = _analyze_pitch(audio, sr_audio)
        energy_info = _analyze_energy(audio)
        spectral_info = _analyze_spectral(audio, sr_audio)
        gender_info = _analyze_gender(audio, sr_audio)

        # Duration
        dur = len(audio) / sr_audio

        lines = [
            "VOICE ANALYSIS\n",
            f"  Duration: {dur:.2f}s",
            f"  Sample rate: {sr_audio} Hz\n",
            "  PITCH:",
            f"    Fundamental: {pitch_info['fundamental_hz']} Hz",
            f"    Category: {pitch_info['pitch_category']}\n",
            "  GENDER:",
            f"    Estimated: {gender_info['estimated_gender']}",
            f"    Confidence: {gender_info['confidence']}",
            f"    Male score: {gender_info['male_score']}",
            f"    Female score: {gender_info['female_score']}\n",
            "  ENERGY:",
            f"    RMS: {energy_info['rms_energy']}",
            f"    Peak: {energy_info['peak_amplitude']}",
            f"    dB RMS: {energy_info['db_rms']}",
            f"    dB Peak: {energy_info['db_peak']}\n",
            "  SPECTRAL:",
            f"    Centroid: {spectral_info['centroid_hz']} Hz",
            f"    Bandwidth: {spectral_info['bandwidth_hz']} Hz",
            f"    Rolloff: {spectral_info['rolloff_hz']} Hz",
            f"    Dominant freqs: {spectral_info['dominant_freqs']}",
        ]

        return "\n".join(lines)

    # ── DIARIZE ──
    if action == "diarize":
        db = _load_db()
        speakers = db.get("speakers", {})
        if not speakers:
            return "No speakers enrolled. Use 'enroll' first."

        dur = min(duration, 30.0)  # Max 30s for diarization

        if player:
            player.write_log(f"[speaker_recognition] Diarizing {dur}s conversation...")

        # Capture audio
        audio = _capture_audio(dur)

        # Split into 1-second segments
        segment_len = SAMPLE_RATE  # 1 second
        segments = []
        for i in range(0, len(audio) - segment_len, segment_len):
            segment = audio[i:i + segment_len]
            rms = np.sqrt(np.mean(segment ** 2))
            if rms > 0.01:  # Skip silence
                segments.append((i / SAMPLE_RATE, segment))

        if not segments:
            return "No speech detected in the recording."

        # Identify each segment
        results = []
        for start_time, segment in segments:
            emb = _compute_speaker_embedding(segment)
            best_match = "unknown"
            best_score = 0
            for sname, sdata in speakers.items():
                avg_emb = np.array(sdata.get("avg_embedding", []))
                if len(avg_emb) == 0:
                    continue
                sim = _cosine_similarity(emb, avg_emb)
                if sim > best_score:
                    best_score = sim
                    best_match = sname

            if best_score > 0.4:
                results.append({
                    "time": round(start_time, 1),
                    "speaker": best_match,
                    "confidence": round(best_score * 100, 1),
                })
            else:
                results.append({
                    "time": round(start_time, 1),
                    "speaker": "unknown",
                    "confidence": round(best_score * 100, 1),
                })

        # Build diarization output
        lines = [f"DIARIZATION ({dur}s, {len(results)} segments)\n"]

        # Group consecutive same-speaker segments
        grouped = []
        for r in results:
            if grouped and grouped[-1]["speaker"] == r["speaker"]:
                grouped[-1]["end"] = r["time"] + 1.0
                grouped[-1]["segments"] += 1
            else:
                grouped.append({
                    "speaker": r["speaker"],
                    "start": r["time"],
                    "end": r["time"] + 1.0,
                    "confidence": r["confidence"],
                    "segments": 1,
                })

        for g in grouped:
            dur_seg = round(g["end"] - g["start"], 1)
            lines.append(
                f"  [{g['start']:.1f}s - {g['end']:.1f}s] "
                f"{g['speaker']} ({g['confidence']}%, {dur_seg}s)"
            )

        # Speaker summary
        speaker_times = {}
        for g in grouped:
            spk = g["speaker"]
            dur_seg = g["end"] - g["start"]
            speaker_times[spk] = speaker_times.get(spk, 0) + dur_seg

        lines.append(f"\n  Speaker Summary:")
        for spk, total in sorted(speaker_times.items(), key=lambda x: -x[1]):
            lines.append(f"    {spk}: {total:.1f}s ({round(total / dur * 100)}%)")

        return "\n".join(lines)

    # ── RECORD ──
    if action == "record":
        dur = min(duration, 30.0)
        save_path = parameters.get("save_path", "")

        if player:
            player.write_log(f"[speaker_recognition] Recording {dur}s...")

        audio = _capture_audio(dur)

        if not save_path:
            save_path = str(BASE_DIR / "data" / f"recording_{int(time.time())}.wav")

        _save_wav(audio, save_path)
        rms = np.sqrt(np.mean(audio ** 2))

        return (
            f"Recording saved: {save_path}\n"
            f"  Duration: {dur:.1f}s\n"
            f"  Energy: {'OK' if rms > 0.01 else 'SILENCE DETECTED'}"
        )

    # ── COMPARE ──
    if action == "compare":
        name1 = parameters.get("name1", "")
        name2 = parameters.get("name2", "")
        if not name1 or not name2:
            return "Error: 'name1' and 'name2' required"

        db = _load_db()
        speakers = db.get("speakers", {})

        if name1 not in speakers:
            return f"Speaker '{name1}' not found."
        if name2 not in speakers:
            return f"Speaker '{name2}' not found."

        emb1 = np.array(speakers[name1].get("avg_embedding", []))
        emb2 = np.array(speakers[name2].get("avg_embedding", []))

        if len(emb1) == 0 or len(emb2) == 0:
            return "One or both speakers have no embeddings."

        sim = _cosine_similarity(emb1, emb2)
        pct = round(sim * 100, 1)

        similarity = "IDENTICAL" if pct > 90 else "VERY SIMILAR" if pct > 70 else "SIMILAR" if pct > 50 else "DIFFERENT"

        return (
            f"Voice Comparison: {name1} vs {name2}\n"
            f"  Similarity: {pct}%\n"
            f"  Verdict: {similarity}"
        )

    return (
        f"Unknown action: '{action}'.\n"
        "Available: enroll, identify, analyze, diarize, profiles, delete, record, compare, status"
    )
