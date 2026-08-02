# -*- coding: utf-8 -*-
"""
meeting_transcriber.py — Transcribe reuniones/conversaciones desde el microfono.
Usa Vosk (local, sin internet) + guarda la transcripcion en data/transcripts/.
Acciones: transcribe (grabar y transcribir), read (leer transcripcion), list.
"""
import json
import time
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
TRANSCRIPTS_DIR = BASE_DIR / "data" / "transcripts"
MODEL_PATH = BASE_DIR / "data" / "vosk-model-es"
SAMPLE_RATE = 16000


def _transcribe(duration: float) -> str:
    import vosk
    import sounddevice as sd
    import numpy as np

    if not MODEL_PATH.exists():
        return "Error: No se encontro el modelo Vosk en data/vosk-model-es."

    model = vosk.Model(str(MODEL_PATH))
    rec = vosk.KaldiRecognizer(model, SAMPLE_RATE)

    frames = int(duration * SAMPLE_RATE)
    audio = sd.rec(frames, samplerate=SAMPLE_RATE, channels=1, dtype="int16").flatten()

    parts = []
    chunk = SAMPLE_RATE * 3
    for i in range(0, len(audio), chunk):
        data = audio[i:i + chunk].tobytes()
        if rec.AcceptWaveform(data):
            res = json.loads(rec.Result())
            if res.get("text"):
                parts.append(res["text"])
        else:
            pass
    final = json.loads(rec.FinalResult())
    if final.get("text"):
        parts.append(final["text"])
    return " ".join(parts).strip()


def meeting_transcriber(parameters: dict = None, player=None) -> str:
    if parameters is None:
        parameters = {}
    action = parameters.get("action", "transcribe").lower()
    duration = min(float(parameters.get("duration", 30.0)), 300.0)

    if action == "transcribe":
        if player:
            player.write_log(f"[meeting_transcriber] Grabando {duration:.0f}s...")
        text = _transcribe(duration)
        if not text:
            return "No se detecto voz durante la grabacion. Verifica el microfono y volve a intentarlo."
        TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
        filename = "reunion_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".txt"
        path = TRANSCRIPTS_DIR / filename
        path.write_text(text, encoding="utf-8")
        words = len(text.split())
        return (
            f"Transcripcion guardada: {path}\n"
            f"  Duracion: {duration:.0f}s | Palabras: {words}\n"
            f"  Texto: {text[:600]}"
        )

    if action == "read":
        name = parameters.get("file", "")
        if not name:
            files = sorted(TRANSCRIPTS_DIR.glob("*.txt"), key=lambda p: p.stat().st_mtime, reverse=True) if TRANSCRIPTS_DIR.exists() else []
            if not files:
                return "No hay transcripciones guardadas."
            path = files[0]
        else:
            path = TRANSCRIPTS_DIR / name if not Path(name).is_absolute() else Path(name)
            if not path.exists():
                return f"Transcripcion no encontrada: {path}"
        text = path.read_text(encoding="utf-8")
        max_chars = int(parameters.get("max_chars", 2000))
        return f"Transcripcion: {path}\n\n{text[:max_chars]}"

    if action == "list":
        if not TRANSCRIPTS_DIR.exists():
            return "No hay transcripciones."
        files = sorted(TRANSCRIPTS_DIR.glob("*.txt"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not files:
            return "No hay transcripciones."
        lines = [f"Transcripciones ({len(files)}):"]
        for f in files:
            words = len(f.read_text(encoding="utf-8", errors="replace").split())
            lines.append(f"  {f.name} ({words} palabras)")
        return "\n".join(lines)

    return "Acciones: transcribe (default), read (file), list."
