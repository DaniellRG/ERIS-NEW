"""
core/offline_voice.py — Offline voice pipeline for ERIS.
Replaces Gemini Live with: Vosk STT → Ollama chat → Local TTS.
"""
from __future__ import annotations

import json
import queue
import threading
import sounddevice as sd
import numpy as np
from pathlib import Path
from typing import Callable

from core.audio_config import SEND_SAMPLE_RATE, RECEIVE_SAMPLE_RATE, CHUNK_SIZE, PLAY_CHUNK_SIZE


class OfflineVoicePipeline:
    """Local voice pipeline: Mic → Vosk STT → Cerebro dual → TTS → Speaker.

    Es el modo de voz 100% local de ERIS: no depende de Gemini Live.
    Soporta push-to-talk (mantener la barra espaciadora para hablar).
    """

    def __init__(self, on_text_response: Callable | None = None):
        self._on_text_response = on_text_response
        self._vosk_recognizer = None
        self._vosk_model = None
        self._mic_stream = None
        self._speaker_stream = None
        self._running = False
        self._audio_queue = queue.Queue()
        self._poll_thread = None
        self._ollama_model = "qwen3:8b"
        self._ollama_url = "http://localhost:11434"
        self._tts_backend = "sapi"
        self._ptt_enabled = False
        self._ptt_holding = False
        self._ptt_listener = None
        self._ptt_buffered = b""
        self._ptt_last_size = 0

    def configure(self, model: str = None, ollama_url: str = None, tts_backend: str = None):
        if model:
            self._ollama_model = model
        if ollama_url:
            self._ollama_url = ollama_url
        if tts_backend:
            self._tts_backend = tts_backend

    def set_chat_fn(self, fn):
        """Replace the default Ollama chat with a custom function (e.g. GeminiTextChat)."""
        self._ollama_chat = fn

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
            vmodel = vosk.Model(str(model_path))
            model = vosk.KaldiRecognizer(vmodel, SEND_SAMPLE_RATE)
            self._vosk_recognizer = model
            self._vosk_model = model
            return True
        except Exception as e:
            print("[offline] Vosk init failed:", e)
            return False

    def _ollama_chat(self, text: str) -> str:
        """Enviar texto al cerebro dual (local Ollama + nube OpenRouter)."""
        try:
            from core.local_brain import get_brain, quick_check
            if not quick_check():
                return "El respaldo local no está disponible (Ollama apagado)."
            return get_brain().respond(text)
        except Exception as e:
            return "Error en el cerebro dual: {}".format(str(e)[:80])

    def _speak(self, text: str):
        """Convert text to speech and play it. Uses non-blocking play to avoid gaps."""
        try:
            import asyncio
            from core.tts_engine import synthesize
            backend = self._tts_backend or "sapi"
            if backend in ("windows", "local"):
                backend = "sapi"
            pcm = asyncio.run(synthesize(text, backend=backend, voice=None))
            if pcm and len(pcm) > 0:
                audio = np.frombuffer(pcm, dtype=np.int16)
                sd.play(audio, RECEIVE_SAMPLE_RATE)
                # Don't block — let audio play while next sentence synthesizes
        except Exception as e:
            print("[offline] TTS error:", e)

    def speak(self, text: str):
        """Public wrapper for TTS."""
        self._speak(text)

    def _mic_callback(self, indata, frames, time_info, status):
        """Mic audio callback — feeds Vosk."""
        if self._ptt_enabled and not self._ptt_holding:
            # En PTT, descartar audio mientras no se mantiene ESPACIO
            if self._ptt_buffered:
                self._ptt_buffered = b""
                self._reset_recognizer()
            return
        if self._vosk_recognizer:
            data = bytes(indata)
            if self._ptt_enabled:
                # Acumular audio del segmento PTT y reconocer al soltar
                self._ptt_buffered += data
                self._ptt_last_size = len(self._ptt_buffered)
                return
            if self._vosk_recognizer.AcceptWaveform(data):
                result = json.loads(self._vosk_recognizer.Result())
                text = result.get("text", "").strip()
                if text:
                    self._audio_queue.put(text)

    def _reset_recognizer(self):
        """Reinicia el reconocedor Vosk (para cada turno de PTT)."""
        if self._vosk_recognizer and self._vosk_model:
            try:
                import vosk
                self._vosk_recognizer = vosk.KaldiRecognizer(self._vosk_model, SEND_SAMPLE_RATE)
            except Exception:
                pass

    def start(self):
        """Start the offline voice loop."""
        if self._running:
            return
        vosk_ok = self._init_vosk()
        if not vosk_ok:
            print("[offline] No se pudo inicializar Vosk. Modo solo texto.")
            return
        self._running = True
        try:
            self._mic_stream = sd.InputStream(
                samplerate=SEND_SAMPLE_RATE,
                channels=1,
                dtype="int16",
                blocksize=CHUNK_SIZE * 4,
                callback=self._mic_callback,
            )
            self._mic_stream.start()
            self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
            self._poll_thread.start()
            print("[offline] Pipeline offline activo. Hablá cuando quieras.")
        except Exception as e:
            print("[offline] Mic error:", e)

    def _poll_loop(self):
        """Consume recognized mic text and respond, continuamente."""
        import time
        while self._running:
            try:
                if self._ptt_enabled:
                    self._poll_ptt_once()
                else:
                    self.process_once()
            except Exception:
                pass
            time.sleep(0.2)

    def _poll_ptt_once(self):
        """En PTT: al soltar ESPACIO, reconocer el audio acumulado."""
        if self._ptt_holding:
            return
        if not self._ptt_buffered:
            return
        data = self._ptt_buffered
        self._ptt_buffered = b""
        if not self._vosk_recognizer:
            return
        text = ""
        try:
            if self._vosk_recognizer.AcceptWaveform(data):
                result = json.loads(self._vosk_recognizer.Result())
                text = result.get("text", "").strip()
            if not text:
                partial = json.loads(self._vosk_recognizer.PartialResult())
                text = partial.get("partial", "").strip()
        except Exception:
            pass
        self._reset_recognizer()
        if text:
            self._audio_queue.put(text)

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

    # ── Push-to-talk: mantener ESPACIO para hablar ──────────────────────────
    def enable_ptt(self, enabled: bool = True):
        """Activa/desactiva push-to-talk (mantener barra espaciadora para hablar)."""
        self._ptt_enabled = bool(enabled)
        if not enabled:
            self._stop_ptt_listener()
            return
        if self._ptt_listener:
            return
        try:
            from pynput import keyboard
            self._ptt_holding = False
            self._ptt_buffered = b""
            self._ptt_last_size = 0

            def _on_press(key):
                if key == keyboard.Key.space:
                    self._ptt_holding = True
                elif key == keyboard.KeyCode.from_char(" "):
                    self._ptt_holding = True

            def _on_release(key):
                if key in (keyboard.Key.space, keyboard.KeyCode.from_char(" ")):
                    self._ptt_holding = False

            self._ptt_listener = keyboard.Listener(
                on_press=_on_press, on_release=_on_release
            )
            self._ptt_listener.daemon = True
            self._ptt_listener.start()
            print("[offline] Push-to-talk activo: mantené ESPACIO para hablar.")
        except Exception as e:
            print(f"[offline] PTT no disponible: {e}")
            self._ptt_enabled = False

    def _stop_ptt_listener(self):
        if self._ptt_listener:
            try:
                self._ptt_listener.stop()
            except Exception:
                pass
            self._ptt_listener = None

    def set_tts_backend(self, backend: str):
        """Cambia el motor de voz local (sapi, edge, kokoro)."""
        if backend in ("sapi", "edge", "kokoro", "windows", "local"):
            self._tts_backend = "sapi" if backend in ("windows", "local") else backend

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
        if self._poll_thread:
            self._poll_thread = None

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
        print("[offline] Auto-restarting voice pipeline...")
        try:
            self.stop()
        except Exception:
            pass
        import time
        time.sleep(1)
        self._running = False
        try:
            self.start()
            print("[offline] Voice pipeline auto-restarted")
            return True
        except Exception as e:
            print(f"[offline] Auto-restart failed: {e}")
            return False


# Singleton
_pipeline: OfflineVoicePipeline | None = None


def get_offline_pipeline(**kwargs) -> OfflineVoicePipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = OfflineVoicePipeline(**kwargs)
    return _pipeline
