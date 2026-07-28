"""
core/offline_voice.py — Offline voice pipeline for ERIS.
Replaces Gemini Live with: Vosk STT → Ollama chat → Local TTS.
"""
from __future__ import annotations

import json
import queue
import sounddevice as sd
import numpy as np
from pathlib import Path
from typing import Callable

from core.audio_config import SEND_SAMPLE_RATE, RECEIVE_SAMPLE_RATE, CHUNK_SIZE, PLAY_CHUNK_SIZE


class OfflineVoicePipeline:
    """Local voice pipeline: Mic → Vosk STT → Ollama → TTS → Speaker."""

    def __init__(self, on_text_response: Callable | None = None):
        self._on_text_response = on_text_response
        self._vosk_recognizer = None
        self._vosk_model = None
        self._mic_stream = None
        self._speaker_stream = None
        self._running = False
        self._audio_queue = queue.Queue()
        self._ollama_model = "minicpm-v"
        self._ollama_url = "http://localhost:11434"
        self._tts_backend = "kokoro"

    def configure(self, model: str = None, ollama_url: str = None, tts_backend: str = None):
        if model:
            self._ollama_model = model
        if ollama_url:
            self._ollama_url = ollama_url
        if tts_backend:
            self._tts_backend = tts_backend

    def _init_vosk(self) -> bool:
        """Initialize Vosk for continuous STT."""
        try:
            import vosk
            import os
            model_path = Path(__file__).resolve().parent.parent / "data" / "vosk-model-es"
            if not model_path.exists():
                import urllib.request, zipfile, os
                url = "alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip"
                zip_path = str(model_path) + ".zip"
                print("[offline] Descargando modelo Vosk (es)...")
                urllib.request.urlretrieve("https://" + url, zip_path)
                with zipfile.ZipFile(zip_path, 'r') as z:
                    z.extractall(str(model_path.parent))
                os.remove(zip_path)
                for d in model_path.parent.iterdir():
                    if d.is_dir() and d.name.startswith("vosk-model"):
                        d.rename(model_path)
            model = vosk.KaldiRecognizer(str(model_path), SEND_SAMPLE_RATE)
            self._vosk_recognizer = model
            self._vosk_model = model
            return True
        except Exception as e:
            print("[offline] Vosk init failed:", e)
            return False

    def _ollama_chat(self, text: str) -> str:
        """Send text to Ollama and get response."""
        try:
            import urllib.request
            system_prompt = (
                "Eres ERIS, una asistente de IA de escritorio. "
                "Respondes en español de forma natural y conversacional. "
                "Tienes acceso a herramientas del sistema. "
                "Sé concisa y útil."
            )
            payload = json.dumps({
                "model": self._ollama_model,
                "prompt": text,
                "system": system_prompt,
                "stream": False,
            }).encode("utf-8")
            req = urllib.request.Request(
                "{}/api/generate".format(self._ollama_url),
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            resp = urllib.request.urlopen(req, timeout=120)
            data = json.loads(resp.read().decode("utf-8"))
            resp.close()
            return data.get("response", "No pude generar una respuesta.")
        except Exception as e:
            return "Error de Ollama: {}".format(str(e)[:80])

    def _speak(self, text: str):
        """Convert text to speech and play it."""
        try:
            from core.tts_engine import synthesize
            pcm = synthesize(text, backend=self._tts_backend, voice=None)
            if pcm and len(pcm) > 0:
                import io
                audio = np.frombuffer(pcm, dtype=np.int16)
                sd.play(audio, RECEIVE_SAMPLE_RATE)
                sd.wait()
        except Exception as e:
            print("[offline] TTS error:", e)

    def _mic_callback(self, indata, frames, time_info, status):
        """Mic audio callback — feeds Vosk."""
        if self._vosk_recognizer:
            if self._vosk_recognizer.AcceptWaveform(bytes(indata)):
                result = json.loads(self._vosk_recognizer.Result())
                text = result.get("text", "").strip()
                if text:
                    self._audio_queue.put(text)

    def start(self):
        """Start the offline voice loop."""
        if self._running:
            return
        self._running = True
        vosk_ok = self._init_vosk()
        if not vosk_ok:
            print("[offline] No se pudo inicializar Vosk. Modo solo texto.")
            return
        try:
            self._mic_stream = sd.InputStream(
                samplerate=SEND_SAMPLE_RATE,
                channels=1,
                dtype="int16",
                blocksize=CHUNK_SIZE * 4,
                callback=self._mic_callback,
            )
            self._mic_stream.start()
            print("[offline] Pipeline offline activo. Hablá cuando quieras.")
        except Exception as e:
            print("[offline] Mic error:", e)

    def process_once(self) -> str | None:
        """Check for recognized text, process it, return response."""
        try:
            text = self._audio_queue.get_nowait()
        except queue.Empty:
            return None
        if not text:
            return None
        response = self._ollama_chat(text)
        if self._on_text_response:
            self._on_text_response(text, response)
        self._speak(response)
        return response

    def send_text(self, text: str) -> str:
        """Process text directly (no mic needed)."""
        response = self._ollama_chat(text)
        if self._on_text_response:
            self._on_text_response(text, response)
        self._speak(response)
        return response

    def stop(self):
        """Stop the pipeline."""
        self._running = False
        if self._mic_stream:
            try:
                self._mic_stream.stop()
                self._mic_stream.close()
            except Exception:
                pass
            self._mic_stream = None

    def is_active(self) -> bool:
        return self._running

    def check_health(self) -> bool:
        """Check if pipeline is healthy, auto-restart if needed."""
        if not self._running:
            return False
        if self._mic_stream is None:
            return False
        try:
            # Check if mic stream is still alive
            info = self._mic_stream.device
            return True
        except Exception:
            return False

    def auto_restart(self) -> bool:
        """Auto-restart the pipeline if it crashed."""
        if self._running and self.check_health():
            return True
        print("[offline] 🔄 Auto-restarting voice pipeline...")
        try:
            self.stop()
        except Exception:
            pass
        import time
        time.sleep(1)
        self._running = False
        try:
            self.start()
            print("[offline] ✅ Voice pipeline auto-restarted")
            return True
        except Exception as e:
            print(f"[offline] ❌ Auto-restart failed: {e}")
            return False


# Singleton
_pipeline: OfflineVoicePipeline | None = None


def get_offline_pipeline(**kwargs) -> OfflineVoicePipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = OfflineVoicePipeline(**kwargs)
    return _pipeline
