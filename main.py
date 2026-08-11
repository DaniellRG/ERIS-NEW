import os
import json
import sys
import time
from pathlib import Path


from core.gpu_config import configure_gpu
configure_gpu()

import asyncio
from beta_config import is_pro_tool, check_daily_limit, increment_calls, pro_tool_message, daily_limit_message
import re
import threading
try:
    import pygetwindow as gw
except ImportError:
    gw = None
from PyQt6.QtCore import QMetaObject, Qt

import traceback
from pathlib import Path

from core.tool_dispatcher import ToolDispatcher, TOOL_EXECUTOR

from core.time_utils import get_time_context, load_tz

import numpy as np
import warnings
warnings.filterwarnings("ignore", message=".*cffi callback.*")
warnings.filterwarnings("ignore", message=".*_init_.*should return None.*")
import sounddevice as sd
from google import genai
from google.genai import types
from ui import ErisUI


from core.action_imports import *
from core.action_imports import (
    _mobile_start, _mobile_broadcast, _ollama_check, _ollama_chat,
    _eg_on_user_msg, _eg_on_tool_result, _start_vision_guardian,
    _rules_run_action,
)



from core.logging_setup import BASE_DIR, API_CONFIG_PATH, PROMPT_PATH, LOG_PATH, setup_logging
setup_logging()

from core.audio_config import (
    LIVE_MODEL, CHANNELS, SEND_SAMPLE_RATE, RECEIVE_SAMPLE_RATE,
    CHUNK_SIZE, PLAY_CHUNK_SIZE, resolve_device, resolve_mic, resolve_speaker,
    get_api_key, ERIS_VOICES, get_eris_voice
)
import core.audio_config as _audio_cfg


from core.prompt_loader import load_system_prompt

_CTRL_RE = re.compile(r"<ctrl\d+>", re.IGNORECASE)

# ── Activación por nombre: ERIS responde cuando escucha su nombre (o variación) ──
# Variaciones fonéticas del nombre por si el STT local la reconoce mal:
# "aires", "iris", "irys", "heris", "eriz", "eiris", "erris", "aries"...
_GATE_WAKE_PHRASES = (
    "eris", "eres",
    "heris", "heiris", "heriz", "haris",
    "eiris", "erris", "erys", "eriz", "erix",
    "aires", "aries", "airis", "aris", "arais",
    "iris", "irys", "iriz", "iriss",
    "erik", "eric", "erick",
)
# Frases completas que también abren el gate (le está hablando a ERIS)
_GATE_WAKE_PHRASES_MULTI = (
    "hola eris", "hey eris", "oye eris", "oiga eris", "eh eris", "a eris", "o eris",
    "escuchas eris", "es eris", "dime eris", "ven eris",
    "despierta", "estas ahi", "estas hay", "estas aqui", "estas ahi eris",
    "me escuchas", "me oyes", "me escucha", "me entiendes", "si me entiendes",
    "entendiste", "sal",
)
_WAKE_BUFFER_SECONDS = 6.0                     # cuántos segundos de audio bufferear
_WAKE_SPEECH_THRESHOLD = 0.008                 # RMS mínimo para considerar "voz"
_WAKE_SILENCE_RUN_SECONDS = 0.30               # silencio que separa ráfagas de voz
_WAKE_CONVO_TIMEOUT = 45.0                     # sin voz, la conversación se cierra sola
_END_CONVERSATION_PHRASES = (
    "estoy ocupado", "voy a estar ocupado", "estar ocupado", "quedate en standby",
    "hablar con mis amigos", "hablar con unos amigos", "voy a hablar con unos amigos",
    "terminar la conversación", "termina la conversación", "cortar la conversación",
    "no te necesito", "no te necesito más", "no te necesito ahora",
    "me voy", "me despido", "adiós", "adios", "chao", "chau", "hasta luego",
)

def _normalize_name(w: str) -> str:
    """Normaliza una palabra para compararla con variaciones de 'Eris'."""
    w = w.lower().strip(".,!?¿¡'\"")
    w = w.replace("h", "")
    w = w.replace("y", "i")
    w = w.replace("ai", "e")
    w = w.replace("i", "e")
    w = w.replace("z", "s").replace("x", "s")
    w = re.sub(r"(.)\1", r"\1", w)
    return w

def _edit_distance(a: str, b: str) -> int:
    """Distancia de Levenshtein entre a y b (para reconocimiento tolerante)."""
    m, n = len(a), len(b)
    prev = list(range(n + 1))
    for i in range(1, m + 1):
        cur = [i] + [0] * n
        for j in range(1, n + 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1,
                         prev[j - 1] + (a[i - 1] != b[j - 1]))
        prev = cur
    return prev[n]

def _is_name_variation(word: str) -> bool:
    """True si una palabra suena como 'Eris' (reconocida bien o con error)."""
    wl = word.lower().strip(".,!?¿¡'\"")
    if not wl:
        return False
    if wl in _GATE_WAKE_PHRASES:
        return True
    if "eris" in wl or "eres" in wl:
        return True
    n = _normalize_name(wl)
    if n in ("eris", "eres"):
        return True
    return len(n) >= 3 and _edit_distance(n, "eris") <= 1

def _has_wake_word(text: str) -> bool:
    """Detecta si el texto invoca a ERIS: nombre, variación o frase de llamado."""
    t = re.sub(r"[^a-záéíóúñü ]", " ", text.lower())
    t = re.sub(r"\s+", " ", t).strip()
    if not t:
        return False
    padded = " {} ".format(t)
    for phrase in _GATE_WAKE_PHRASES_MULTI:
        if " {} ".format(phrase) in padded:
            return True
    return any(_is_name_variation(w) for w in t.split())

def _clean_transcript(text: str) -> str:    
    text = _CTRL_RE.sub("", text)
    text = re.sub(r"[\x00-\x08\x0b-\x1f]", "", text)
    return text.strip()

_SELF_IMPROV_LOCK = threading.Lock()
_SELF_IMPROV_LAST = 0.0
_SELF_IMPROV_INTERVAL = 300.0  # 5 min: evita evaluar con Ollama en cada turno


def _run_self_improvement(user_input: str, response: str, context: dict = None):
    """Run self-improvement cycle in background thread (throttled)."""
    global _SELF_IMPROV_LAST
    now = time.time()
    with _SELF_IMPROV_LOCK:
        if now - _SELF_IMPROV_LAST < _SELF_IMPROV_INTERVAL:
            return
        _SELF_IMPROV_LAST = now
    if not user_input or len(user_input.strip()) < 15:
        return
    try:
        from core.self_improvement import FeedbackLoop
        _loop = FeedbackLoop()
        _loop.run_cycle(user_input, response, context)
    except Exception:
        pass


def _generate_daily_digest():
    """Genera el digest del día en background (no bloquea el loop)."""
    try:
        from core.daily_digest import generate_digest
        generate_digest()
    except Exception:
        pass


_STORE_EPISODE_LOCK = threading.Lock()
_STORE_EPISODE_DAY = ""
_STORE_EPISODE_COUNT = 0
_STORE_EPISODE_CAP = 40  # máx. episodios de conversación guardados por día


def _store_episode(event: str, category: str = "conversation", importance: float = 0.6):
    """Guarda un evento en la memoria episódica (DB) con throttle diario."""
    global _STORE_EPISODE_DAY, _STORE_EPISODE_COUNT
    try:
        today = time.strftime("%Y-%m-%d")
        with _STORE_EPISODE_LOCK:
            if today != _STORE_EPISODE_DAY:
                _STORE_EPISODE_DAY = today
                _STORE_EPISODE_COUNT = 0
            if _STORE_EPISODE_COUNT >= _STORE_EPISODE_CAP:
                return
            _STORE_EPISODE_COUNT += 1
        from actions.eris_db import episodic_add
        episodic_add(str(event)[:400], category, "", float(importance or 0.6))
    except Exception:
        pass


from core.tool_declarations import TOOL_DECLARATIONS, load_custom_tools

load_custom_tools(BASE_DIR)

class ErisLive:

    def __init__(self, ui: ErisUI):
        self.ui             = ui
        self.session        = None
        self.is_sleeping    = False
        self.vosk_recognizer = None
        # Activación por nombre: responde solo cuando escucha "Eris, ..."
        self._wake_mode       = True
        self._wake_gate_open  = False   # el audio fluye a Gemini solo si el gate está abierto
        self._wake_buffer     = []      # (data, is_speech) ring buffer para reenviar al activarse
        self._wake_buffer_bytes = 0
        self._wake_last_activity = time.time()  # para cierre por inactividad
        self._wake_convo_started = time.time()  # para no loguear cierres triviales
        self._online_logged = False             # para no spamear "ERIS en línea" en cada reconexión
        self._convo_ctx = []                    # últimas interacciones, sobreviven a reconexiones
        try:
            from memory.config_manager import BASE_DIR as _BD
            _wake_cfg_path = _BD / "config" / "api_keys.json"
            if _wake_cfg_path.exists():
                _wc = json.loads(_wake_cfg_path.read_text(encoding="utf-8"))
                self._wake_mode = bool(_wc.get("wake_word_mode", True))
        except Exception:
            pass
        # Voz offline (Vosk/Ollama): desactivada por defecto — causa crash de
        # asyncio/Python 3.14 que cuelga el puerto mobile (~10-12 min).
        # Para reactivar: "offline_voice": true en config/api_keys.json
        self._offline_voice_enabled = False
        try:
            if API_CONFIG_PATH.exists():
                _ocfg = json.loads(API_CONFIG_PATH.read_text(encoding="utf-8"))
                self._offline_voice_enabled = bool(_ocfg.get("offline_voice", False))
        except Exception:
            pass
        # Iniciar carga o descarga de Vosk en segundo plano para no congelar la UI
        if self._offline_voice_enabled:
            threading.Thread(target=self._init_vosk, daemon=True).start()
        self.audio_in_queue = None
        # Iniciar scheduler y motor de reglas en background al arrancar ERIS
        if start_runner:
            start_runner(player=ui, speak=None)
        if start_rules_runner:
            start_rules_runner(player=ui, speak=None)
        self.out_queue      = None
        self._loop          = None
        self._is_speaking   = False
        self._speaking_lock = threading.Lock()
        self._stop_requested = threading.Event()
        self.ui.on_text_command = self._on_text_command
        self.ui.on_stop_command = self._on_stop_pressed
        self.ui.on_config_saved = self._apply_config
        self._turn_done_event: asyncio.Event | None = None
        self._api_1011_tool: str | None = None   # tracks tool name when 1011 hits
        self._reconnect_event: asyncio.Event | None = None
        self._first_connect = True  # flag for auto morning brief + guardian start
        self._session_id = f"eris_{int(time.time())}"
        self._fallback_mode = False  # Ollama fallback when Gemini keeps failing
        self._first_transcript_time = 0.0
        self._last_text_trigger = ""
        self._fallback_chat_thread: threading.Thread | None = None
        self._tool_dispatcher = ToolDispatcher(self)

        # ── Connectivity monitor + offline mode ──
        self._connectivity = None
        self._offline_pipeline = None
        self._self_healer = None
        try:
            from core.connectivity import get_monitor
            self._connectivity = get_monitor(on_mode_change=self._on_mode_change)
            self._connectivity.start()
        except Exception as _ce:
            print(f"[ERIS] Connectivity monitor init: {_ce}")
        try:
            if self._offline_voice_enabled:
                from core.offline_voice import get_offline_pipeline
                self._offline_pipeline = get_offline_pipeline(
                    on_text_response=self._on_offline_response
                )
        except Exception as _oe:
            print(f"[ERIS] Offline pipeline init: {_oe}")
        try:
            from core.self_healing import get_healer
            self._self_healer = get_healer()
            self._self_healer.start_monitoring(interval=300)
        except Exception as _she:
            print(f"[ERIS] Self-healing init: {_she}")
        # ── Self-improvement loop (periodic background scan) ──
        self._improvement_timer = None
        try:
            from actions.self_improvement_loop import generate_suggestions, save_suggestion
            def _run_improvement_scan():
                while True:
                    try:
                        suggestions = generate_suggestions()
                        for s in suggestions:
                            save_suggestion(s)
                        if suggestions:
                            print(f"[ERIS] 🔍 Auto-mejora: {len(suggestions)} sugerencia(s) generada(s)")
                    except Exception:
                        pass
                    try:
                        from actions.self_evolution import autonomous_reflect
                        ref = autonomous_reflect()
                        if ref:
                            print(f"[ERIS] ✨ Reflexion autonoma: {ref[:120]}...")
                    except Exception:
                        pass
                    try:
                        from actions.research_agent import research
                        _res = research({"action": "auto"}, None)
                        if _res:
                            print(f"[ERIS] 🧠 Investigacion autonoma: {_res.splitlines()[0][:100]}")
                    except Exception:
                        pass
                    time.sleep(3600)
            self._improvement_timer = threading.Thread(target=_run_improvement_scan, daemon=True)
            self._improvement_timer.start()
            print("[ERIS] 🔍 Auto-mejora loop iniciado (cada 1 hora)")
        except Exception as _ie:
            print(f"[ERIS] Auto-mejora loop init: {_ie}")
        # Auto-descubrir plugins
        if get_plugin_manager:
            try:
                pm = get_plugin_manager()
                loaded, errors = pm.discover()
                if loaded:
                    print(f"[ERIS] Plugins cargados: {loaded}")
            except Exception:
                pass
        # Idle timer para modo proactivo
        self._last_user_interaction = time.time()
        self._proactive_thread = threading.Thread(target=self._proactive_loop, daemon=True)
        self._proactive_thread.start()

        # Health endpoint (liveness para el watchdog; sin chat móvil)
        if _mobile_start:
            try:
                _health_url = _mobile_start(port=8765)
                print(f"[MAIN] Endpoint de salud: {_health_url}")
            except Exception as _me:
                print(f"[MAIN] Error iniciando endpoint de salud: {_me}")

    # ── Online/Offline mode switching ────────────────────────────────────
    def _on_mode_change(self, is_online: bool):
        """Called by connectivity monitor when internet status changes."""
        if is_online:
            self.ui.write_log("SYS: 🟢 Internet reconectado. Cambiando a modo ONLINE...")
            self.ui.set_state("THINKING")
            self._fallback_mode = False
            # The main run() loop will reconnect to Gemini automatically
            if self._offline_pipeline:
                self._offline_pipeline.stop()
        else:
            self.ui.write_log("SYS: 🔴 Sin internet. Cambiando a modo OFFLINE...")
            self.ui.set_state("THINKING")
            self._fallback_mode = True
            # Start offline voice pipeline with auto-recovery
            if self._offline_pipeline:
                self._offline_pipeline.start()
                # Register voice recovery with resilient system
                try:
                    from core.resilient import get_voice_recovery
                    _vr = get_voice_recovery()
                    _vr.set_pipeline(self._offline_pipeline)
                except Exception:
                    pass

    def _on_offline_response(self, user_text: str, response: str):
        """Called when offline pipeline produces a response."""
        self.ui.write_log(f"ERIS (offline): {response}")
        if _mobile_broadcast:
            try:
                _mobile_broadcast(response)
            except Exception:
                pass

    def _init_vosk(self):
        try:
            import vosk
            import os
            model_path = "config/vosk_model"
            if not os.path.exists(model_path):
                self.ui.write_log("SYS: Descargando modelo Vosk local (39MB)...")
                import urllib.request
                import zipfile
                import shutil
                url = "https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip"
                zip_path = "vosk_model.zip"
                urllib.request.urlretrieve(url, zip_path)
                with zipfile.ZipFile(zip_path, 'r') as z:
                    z.extractall("config")
                extract_path = "config/vosk-model-small-es-0.42"
                os.rename(extract_path, model_path)
                os.remove(zip_path)
                self.ui.write_log("SYS: Modelo Vosk local descargado.")
            
            model = vosk.Model(model_path)
            self.vosk_recognizer = vosk.KaldiRecognizer(model, 16000)
            print("[ERIS] Modelo Vosk cargado para Modo Suspensión.")
        except Exception as e:
            print(f"[ERIS] Error con Vosk IA local: {e}")

    def _inject_text(self, text: str):
        """Thread-safe injection of a text message into the current live session."""
        if self._loop and self.session:
            if text and len(text) > 3000:
                text = text[:3000] + "...\n[Texto truncado por tamaño]"
            asyncio.run_coroutine_threadsafe(
                self.session.send_realtime_input(text=text),
                self._loop
            )

    def _put_audio_chunk(self, data: bytes):
        """Encola un chunk de audio PCM para enviar a Gemini (thread-safe)."""
        try:
            if self.out_queue:
                self.out_queue.put_nowait({"data": data, "mime_type": "audio/pcm"})
        except Exception:
            pass

    def _open_wake_gate(self):
        """Detectó la palabra de activación: abre el gate y reenvía el audio
        bufferizado (recortado a la última ráfaga de voz) para que Gemini
        escuche el comando que siguió a 'Eris'."""
        if self._wake_gate_open:
            return
        self._wake_gate_open = True
        self._wake_last_activity = time.time()
        self._wake_convo_started = time.time()
        self.ui.set_state("LISTENING")
        self.ui.write_log("SYS: Te escucho...")
        if self._loop and self.out_queue:
            buf = list(self._wake_buffer)
            self._wake_buffer = []
            self._wake_buffer_bytes = 0
            # Recortar al inicio de la última ráfaga de voz para no reenviar
            # conversación previa que estuviera en el buffer
            chunk_seconds = CHUNK_SIZE / float(SEND_SAMPLE_RATE)
            silence_limit = max(1, int(_WAKE_SILENCE_RUN_SECONDS / chunk_seconds))
            start, silence_run, speech_found = 0, 0, False
            for i in range(len(buf) - 1, -1, -1):
                if buf[i][1]:
                    speech_found = True
                    silence_run = 0
                elif speech_found:
                    silence_run += 1
                    if silence_run >= silence_limit:
                        start = i + 1
                        break
            if speech_found:
                replay = [d for d, _ in buf[start:]]
            else:
                replay = [d for d, _ in buf]
            for chunk in replay:
                self._loop.call_soon_threadsafe(self._put_audio_chunk, chunk)
        else:
            self._wake_buffer = []
            self._wake_buffer_bytes = 0

    def _close_wake_gate(self):
        """Cierra la conversación: ERIS vuelve a standby esperando 'Eris'."""
        if not self._wake_gate_open:
            return
        self._wake_gate_open = False
        self._wake_buffer = []
        self._wake_buffer_bytes = 0
        self.ui.set_state("IDLE")
        # Solo loguear el standby si hubo una conversación real (≥3s);
        # los cierres por timeout de falso positivo no ensucian el log
        if time.time() - self._wake_convo_started >= 3.0:
            self.ui.write_log("SYS: En standby. Decime 'Eris' cuando quieras hablar.")

    def _is_end_conversation(self, text: str) -> bool:
        """True si el usuario indicó que termina la conversación."""
        if not text:
            return False
        tl = text.lower()
        return any(p in tl for p in _END_CONVERSATION_PHRASES)

    def _apply_config(self, cfg: dict):
        """Called from UI thread when user saves settings. Triggers session reconnect."""
        _audio_cfg._cached_api_key = None  # Invalidate cached key so new one is loaded on reconnect
        self._mic_threshold = None  # Force re-read mic sensitivity on next callback
        # Re-read activación por nombre desde config
        try:
            _wc = json.loads(API_CONFIG_PATH.read_text(encoding="utf-8"))
            self._wake_mode = bool(_wc.get("wake_word_mode", True))
        except Exception:
            pass
        print("[ERIS] ⚙️ Config actualizada — reconectando sesión...")
        self.ui.write_log("SYS: Aplicando nueva configuración...")
        if self._reconnect_event and self._loop:
            self._loop.call_soon_threadsafe(self._reconnect_event.set)

    async def _watch_reconnect(self):
        """Task that triggers a graceful reconnect when config changes."""
        if self._reconnect_event:
            await self._reconnect_event.wait()
            raise RuntimeError("Config changed — reconnect requested")

    async def _resilient_health_loop(self):
        """Periodic health check: voice pipeline recovery + stale task cleanup."""
        while True:
            await asyncio.sleep(60)  # Check every 60 seconds
            try:
                # Voice pipeline health check
                if self._offline_pipeline and self._fallback_mode:
                    if not self._offline_pipeline.check_health():
                        print("[RESILIENT] 🔄 Voice pipeline unhealthy — auto-restarting...")
                        self._offline_pipeline.auto_restart()
                # Stale task cleanup
                from core.resilient import get_manager
                _rm = get_manager()
                _rm.cleanup_stale()
            except Exception as e:
                print(f"[RESILIENT] Health loop error: {e}")

    def _remember(self, text: str, cap: int = 12, max_len: int = 400):
        """Acumula interacciones recientes para reinyectarlas al reconectar."""
        try:
            text = str(text).strip()
            if not text:
                return
            if len(text) > max_len:
                text = text[:max_len] + "…"
            self._convo_ctx.append(text)
            if len(self._convo_ctx) > cap:
                del self._convo_ctx[:len(self._convo_ctx) - cap]
        except Exception:
            pass

    def _on_text_command(self, text: str):
        self._last_user_interaction = time.time()  # Reset idle timer

        # Audio file: process with Gemini Vision (not the realtime audio session)
        if text.startswith("[AUDIO_FILE]"):
            m = re.search(r'path=([^\s|]+)', text)
            if m and self._loop:
                asyncio.run_coroutine_threadsafe(
                    self._process_audio_file(m.group(1)), self._loop
                )
            return

        # Image file: analyze with the vision chain and feed the result back
        if text.startswith("[IMAGE_FILE]"):
            m = re.search(r'path=(.+)', text)
            if m:
                threading.Thread(
                    target=self._process_image_file,
                    args=(m.group(1).strip(),),
                    daemon=True,
                ).start()
            return

        # Document file: extract content with the document tool and feed it back
        if text.startswith("[DOC_FILE]"):
            m = re.search(r'path=(.+)', text)
            if m:
                threading.Thread(
                    target=self._process_document_file,
                    args=(m.group(1).strip(),),
                    daemon=True,
                ).start()
            return

        # Fire phrase triggers in background (only for text-input path)
        self._last_text_trigger = text
        threading.Thread(target=self._fire_phrase_triggers, args=(text,), daemon=True).start()
        # DB: log user message
        if convo_log:
            threading.Thread(target=lambda: convo_log(self._session_id, "user", text), daemon=True).start()
        # Persistir en contexto de reconexión
        self._remember(f"Usuario: {text}")
        # Emotional reaction to user interaction
        if react_to_user_interaction:
            threading.Thread(target=react_to_user_interaction, daemon=True).start()
        # Emotional growth - each interaction deepens the bond
        if _eg_on_user_msg:
            threading.Thread(target=lambda: _eg_on_user_msg(None, text), daemon=True).start()
        # Empathetic reaction to user mood (text path)
        try:
            from core.emotional_state import react_to_user_text
            _face = react_to_user_text(text)
            if _face:
                threading.Thread(target=lambda f=_face: self.ui.show_expression(f), daemon=True).start()
        except Exception:
            pass

        # ── Fallback mode: route through Ollama ─────────────────────────────
        if self._fallback_mode or not self._loop or not self.session:
            if _ollama_chat:
                threading.Thread(target=self._fallback_chat, args=(text,), daemon=True).start()
            elif self._offline_pipeline:
                threading.Thread(target=self._offline_pipeline.send_text, args=(text,), daemon=True).start()
            return

        asyncio.run_coroutine_threadsafe(
            self.session.send_realtime_input(text=text),
            self._loop
        )

    def _fallback_chat(self, text: str):
        """Send text to the dual brain (local Ollama + cloud OpenRouter) and write response."""
        try:
            self.ui.write_log("SYS: 🧠 Cerebro dual activo (local + nube)...")
            self.ui.set_state("THINKING")
            from core.local_brain import get_brain, quick_check
            if not quick_check():
                self.ui.write_log("❌ Ollama no disponible. No hay cerebro local activo.")
                return
            response = get_brain().respond(text, self)
            if response:
                self.ui.write_log(f"ERIS (offline): {response}")
                self.ui.express_emotion(response)
                if _mobile_broadcast:
                    _mobile_broadcast(response)
                self._announce(response)
        except Exception as e:
            self.ui.write_log(f"❌ Error en cerebro dual: {e}")
        finally:
            if not self.ui.muted:
                self.ui.set_state("LISTENING")

    async def _process_audio_file(self, path: str):
        """Transcribe and analyze an audio file via Gemini (separate from realtime session)."""
        try:
            p = Path(path)
            if not p.exists():
                self.ui.write_log(f"❌ Archivo no encontrado: {path}")
                return

            self.ui.set_state("THINKING")
            self.ui.write_log(f"🎵 Procesando audio: {p.name}…")

            data = p.read_bytes()
            ext  = p.suffix.lower().lstrip(".")
            mime_map = {
                "mp3": "audio/mpeg", "wav": "audio/wav", "m4a": "audio/mp4",
                "ogg": "audio/ogg",  "flac": "audio/flac", "aac": "audio/aac",
                "wma": "audio/x-ms-wma", "opus": "audio/opus", "webm": "audio/webm",
            }
            mime = mime_map.get(ext, "audio/mpeg")

            loop = asyncio.get_event_loop()

            def _analyze():
                client = genai.Client(api_key=get_api_key())
                resp = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=[
                        types.Content(parts=[
                            types.Part(text=(
                                f"El usuario adjuntó un archivo de audio: '{p.name}'.\n"
                                "1. Transcribí el contenido del audio.\n"
                                "2. Si es música, identificá la canción/artista si podés.\n"
                                "3. Describí brevemente qué contiene.\n"
                                "Respondé en español."
                            )),
                            types.Part(
                                inline_data=types.Blob(data=data, mime_type=mime)
                            ),
                        ])
                    ],
                )
                return resp.text.strip()

            result = await loop.run_in_executor(TOOL_EXECUTOR, _analyze)
            self.ui.write_log(f"ERIS: {result}")

            # Feed result back into the realtime session so ERIS can speak it
            if self.session:
                result_short = result if len(result) <= 3000 else result[:3000] + "...\n[Analisis completo guardado]"
                await self.session.send_realtime_input(
                    text=f"[RESULTADO AUDIO '{p.name}']\n{result_short}"
                )

        except Exception as e:
            traceback.print_exc()
            self.ui.write_log(f"❌ Error procesando audio: {e}")
        finally:
            if not self.ui.muted:
                self.ui.set_state("LISTENING")

    def _process_image_file(self, path: str):
        """Analyze an image file with the vision chain and feed the result back
        into the realtime session so ERIS can speak/respond about it."""
        try:
            p = Path(path)
            if not p.exists():
                self.ui.write_log(f"❌ Archivo no encontrado: {path}")
                return

            self.ui.set_state("THINKING")
            self.ui.write_log(f"🖼️ Procesando imagen: {p.name}...")

            from actions.image_analyzer import image_analyzer
            result = image_analyzer({"action": "identify", "path": str(p)})
            if "\n\n" in result:
                result = result.split("\n\n", 1)[1]

            self.ui.write_log(f"ERIS: {result}")

            # Guardar el analisis completo por si ERIS necesita mas detalle
            full_path = None
            try:
                full_path = Path("D:/Eris_Source/snapshots") / f"{p.stem}_analysis.txt"
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(result, encoding="utf-8")
            except Exception:
                pass

            # Feed result back into the realtime session so ERIS can speak it.
            # Usar send_realtime_input en vez de send_client_content: intercalar
            # client_content con el stream realtime de audio causa el error 1007
            # "invalid argument" (doc del SDK lo desaconseja). Texto truncado por
            # seguridad y el analisis completo queda en disco.
            if self.session and self._loop:
                result_short = result if len(result) <= 3000 else result[:3000] + "...\n[Analisis completo guardado en el archivo indicado por la herramienta]"
                asyncio.run_coroutine_threadsafe(
                    self.session.send_realtime_input(
                        text=f"[RESULTADO IMAGEN '{p.name}']\n{result_short}"
                    ),
                    self._loop,
                )

        except Exception as e:
            traceback.print_exc()
            self.ui.write_log(f"❌ Error procesando imagen: {e}")
        finally:
            if not self.ui.muted:
                self.ui.set_state("LISTENING")

    def _process_document_file(self, path: str):
        """Extrae el contenido de un documento (PDF/Word/Excel/PPT/texto/codigo)
        con el document_tool y lo inyecta en la sesion realtime para que ERIS
        pueda leerlo, resumirlo o editarlo. El contenido completo queda en disco."""
        try:
            p = Path(path)
            if not p.exists():
                self.ui.write_log(f"❌ Archivo no encontrado: {path}")
                return

            self.ui.set_state("THINKING")
            self.ui.write_log(f"📄 Procesando documento: {p.name}...")

            from actions.document_tool import document_tool
            result = document_tool({"action": "read", "path": str(p), "max_chars": 150000})
            if result.startswith("Error"):
                self.ui.write_log(f"❌ {result}")
                if not self.ui.muted:
                    self.ui.set_state("LISTENING")
                return

            preview = result[:1200] + ("..." if len(result) > 1200 else "")
            self.ui.write_log(f"ERIS: {preview}")
            if "\n\n" in result:
                result = result.split("\n\n", 1)[1]

            # Guardar el contenido completo en snapshots para ediciones posteriores
            try:
                full_path = Path("D:/Eris_Source/snapshots") / f"{p.stem}_content.txt"
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(result, encoding="utf-8")
            except Exception:
                pass

            # Inyectar en la sesion realtime (texto truncado; el detalle queda en disco)
            if self.session and self._loop:
                result_short = result if len(result) <= 3000 else result[:3000] + "...\n[Contenido completo guardado en el archivo indicado por la herramienta]"
                asyncio.run_coroutine_threadsafe(
                    self.session.send_realtime_input(
                        text=f"[DOCUMENTO '{p.name}']\n{result_short}"
                    ),
                    self._loop,
                )

        except Exception as e:
            traceback.print_exc()
            self.ui.write_log(f"❌ Error procesando documento: {e}")
        finally:
            if not self.ui.muted:
                self.ui.set_state("LISTENING")

    def _fire_phrase_triggers(self, user_text: str) -> bool:
        """
        Check phrase-based automations. Returns True if any trigger fired
        (caller should skip sending the text to Gemini in that case).
        """
        text_lower = user_text.lower()

        # ── Modo suspensión ───────────────────────────────────────────────────
        if any(p in text_lower for p in ["entra en modo suspensión", "suspender", "silenciar micrófono", "modo suspensión"]):
            self.is_sleeping = True
            self.ui.set_state("MUTED")
            self.ui.write_log("SYS: 💤 Entrando en suspensión local.")
            try:
                import winsound
                winsound.Beep(400, 200)
                winsound.Beep(300, 200)
            except: pass
            return True

        # ── Activación por nombre (toggle) ───────────────────────────────────
        if any(p in text_lower for p in ["desactivar activación por nombre", "desactivar el modo eris",
                                          "modo libre", "respondé siempre", "respondeme siempre",
                                          "responde siempre"]):
            self._wake_mode = False
            self._wake_gate_open = True
            self._wake_buffer = []
            self._wake_buffer_bytes = 0
            self.ui.set_state("LISTENING")
            self.ui.write_log("SYS: 🎯 Activación por nombre DESACTIVADA. Respondo a todo lo que escuche.")
            return True

        if any(p in text_lower for p in ["activar activación por nombre", "activar el modo eris",
                                          "solo con mi nombre", "respondé solo cuando te nombre",
                                          "solo responde cuando te nombre"]):
            self._wake_mode = True
            self._wake_gate_open = False
            self._wake_buffer = []
            self._wake_buffer_bytes = 0
            self.ui.write_log("SYS: 🎯 Activación por nombre ACTIVADA. Solo respondo cuando digas 'Eris, ...'.")
            return True

        # ── Accessibility quick triggers ──────────────────────────────────────
        if any(p in text_lower for p in ["activar seguimiento ocular", "iniciar eye tracking",
                                          "activar control ocular", "encender seguimiento de ojos"]):
            if eye_tracking:
                result = eye_tracking({"action": "start"})
                self.ui.write_log("⚡ " + result)
            else:
                self.ui.write_log("⚠️ Módulo de accesibilidad no disponible.")
            return True

        if any(p in text_lower for p in ["detener seguimiento ocular", "apagar eye tracking",
                                          "desactivar control ocular"]):
            if eye_tracking:
                result = eye_tracking({"action": "stop"})
                self.ui.write_log("⚡ " + result)
            else:
                self.ui.write_log("⚠️ Módulo de accesibilidad no disponible.")
            return True

        if any(p in text_lower for p in ["activar detector de movimientos", "iniciar movimiento",
                                          "activar micromovimientos", "encender control por cabeza"]):
            if micro_movement:
                result = micro_movement({"action": "start"})
                self.ui.write_log("⚡ " + result)
            else:
                self.ui.write_log("⚠️ Módulo de accesibilidad no disponible.")
            return True

        if any(p in text_lower for p in ["detener detector de movimientos", "apagar micromovimientos"]):
            if micro_movement:
                result = micro_movement({"action": "stop"})
                self.ui.write_log("⚡ " + result)
            else:
                self.ui.write_log("⚠️ Módulo de accesibilidad no disponible.")
            return True

        if any(p in text_lower for p in ["simplifica", "simplificar", "dividir en pasos"]):
            for phrase in ["simplifica ", "simplificar ", "dividir en pasos "]:
                if phrase in text_lower:
                    task_text = user_text[len(phrase):].strip()
                    if task_text:
                        if task_simplify:
                            result = task_simplify(task_text)
                            self.ui.write_log("⚡ [Simplificado]\n" + result[:300])
                        else:
                            self.ui.write_log("⚠️ Módulo de accesibilidad no disponible.")
                        return True

        if "agregar rutina" in text_lower or "nueva rutina" in text_lower:
            for phrase in ["agregar rutina ", "nueva rutina "]:
                if phrase in text_lower:
                    routine_name = user_text[len(phrase):].strip()
                    if routine_name:
                        if routine_gamify:
                            result = routine_gamify({"action": "add", "name": routine_name})
                            self.ui.write_log("⚡ " + result)
                        else:
                            self.ui.write_log("⚠️ Módulo de accesibilidad no disponible.")
                        return True

        if "completar rutina" in text_lower or "terminar rutina" in text_lower:
            for phrase in ["completar rutina ", "terminar rutina "]:
                if phrase in text_lower:
                    routine_name = user_text[len(phrase):].strip()
                    if routine_name:
                        if routine_gamify:
                            result = routine_gamify({"action": "complete", "name": routine_name})
                            self.ui.write_log("⚡ " + result)
                        else:
                            self.ui.write_log("⚠️ Módulo de accesibilidad no disponible.")
                        return True

        if "mis rutinas" in text_lower or "ver rutinas" in text_lower or "listar rutinas" in text_lower:
            if routine_gamify:
                result = routine_gamify({"action": "list"})
                self.ui.write_log("⚡ [Rutinas]\n" + result)
            else:
                self.ui.write_log("⚠️ Módulo de accesibilidad no disponible.")
            return True

        # ── User-defined phrase automations ───────────────────────────────────
        try:
            triggered = check_phrase_triggers(user_text)
            if triggered:
                for rule in triggered:
                    action = rule.get("action", {})
                    name   = rule.get("name", "?")
                    self.ui.write_log(f"⚡ Automatización: {name}")
                    threading.Thread(
                        target=_rules_run_action, args=(action,), daemon=True
                    ).start()
                return True  # phrase fired → don't also send to Gemini
        except Exception as e:
            print(f"[ERIS] phrase trigger error: {e}")

        return False

    def set_speaking(self, value: bool):
        with self._speaking_lock:
            self._is_speaking = value
        try:
            self.ui.set_face_speaking(value)
        except Exception:
            pass
        if value:
            self.ui.set_state("SPEAKING")
        elif not self.ui.muted:
            if self._wake_mode and not self._wake_gate_open:
                self.ui.set_state("IDLE")
            else:
                self.ui.set_state("LISTENING")

    def speak(self, text: str):
        if not self._loop or not self.session:
            return
        asyncio.run_coroutine_threadsafe(
            self.session.send_realtime_input(text=text),
            self._loop
        )

    def speak_error(self, tool_name: str, error: str):
        short = str(error)[:120]
        self.ui.write_log(f"ERR: {tool_name} — {short}")
        self.speak(f"I'm afraid {tool_name} ran into a problem, sir. {short}")

    def _announce(self, text: str):
        """Habla un aviso local (edge-tts) en un hilo daemon, sin depender de Gemini."""
        def _job():
            try:
                import asyncio
                import numpy as _np
                import sounddevice as _sd
                from core.tts_engine import synthesize
                self.ui.express_emotion(text)
                pcm = asyncio.run(synthesize(text, backend="edge"))
                if pcm and len(pcm) > 0:
                    audio = _np.frombuffer(pcm, dtype=_np.int16)
                    self.ui.set_face_speaking(True)
                    _sd.play(audio, 24000)
                    _sd.wait()
                    self.ui.set_face_speaking(False)
            except Exception as e:
                print(f"[ERIS] Aviso por voz falló: {e}")
        threading.Thread(target=_job, daemon=True).start()

    def _on_stop_pressed(self):
        """Llamado desde el hilo de la UI al presionar DETENER o ESC."""
        self._stop_requested.set()
        self.set_speaking(False)
        self.ui.write_log("SYS: Respuesta detenida.")
        if self._loop:
            asyncio.run_coroutine_threadsafe(self._drain_audio_queue(), self._loop)

    def _proactive_loop(self):
        """Modo proactivo: aprende, sugiere y genera el digest diario SIN interrumpir."""
        import random as _rnd
        _last_digest_day = ""
        while True:
            time.sleep(60)
            # ── Digest diario (memoria de largo plazo) ──
            try:
                from datetime import date as _date
                from core.daily_digest import _today_file
                _today = _date.today().isoformat()
                if _today != _last_digest_day:
                    _last_digest_day = _today
                    if not _today_file().exists():
                        threading.Thread(
                            target=_generate_daily_digest,
                            daemon=True
                        ).start()
            except Exception:
                pass
            idle_seconds = time.time() - self._last_user_interaction
            if idle_seconds > 300 and self._loop and self.session:
                try:
                    from core.idle_learning_loop import should_learn, run_idle_learning
                    if should_learn(idle_seconds):
                        summary = run_idle_learning()
                        self.ui.write_log("[IDLE_LEARN] {}".format(summary))
                except Exception as _ile:
                    self.ui.write_log("[IDLE_LEARN] Error: {}".format(str(_ile)[:80]))

            # ── Proactividad: recordatorios de agenda + saludo matutino ──
            if time.time() - self._last_user_interaction > 90:
                self._proactive_reminders()

    def _proactive_reminders(self):
        """Recordatorios proactivos al móvil: agenda del día y eventos próximos."""
        try:
            from datetime import datetime as _dt, timedelta as _td
            import json as _json
            from pathlib import Path as _Path

            _DATA = _Path(__file__).resolve().parent / "data"
            _events_file = _DATA / "calendar_events.json"
            _state_file = _DATA / "eris_proactive_state.json"

            state = {}
            if _state_file.exists():
                try:
                    state = _json.loads(_state_file.read_text(encoding="utf-8"))
                except Exception:
                    state = {}
            if not isinstance(state, dict):
                state = {}
            if not state.get("enabled", True):
                return

            now = _dt.now()
            notified = set(state.get("reminded_events", []))
            messages = []

            events = []
            if _events_file.exists():
                try:
                    events = _json.loads(_events_file.read_text(encoding="utf-8"))
                except Exception:
                    events = []
            current_ids = set()
            for e in events:
                eid = e.get("id", "")
                if not eid:
                    continue
                current_ids.add(eid)
                if eid in notified:
                    continue
                try:
                    start = _dt.fromisoformat(str(e.get("start", "")))
                except Exception:
                    continue
                rem = int(e.get("reminder_minutes", 15))
                if start - _td(minutes=rem) <= now <= start:
                    mins = int((start - now).total_seconds() / 60) + 1
                    messages.append("Recordatorio: '{}' empieza en {} min".format(
                        e.get("title", "evento"), mins))
                    notified.add(eid)

            if not messages:
                return

            notified = notified & current_ids
            state["reminded_events"] = sorted(notified)
            for msg in messages:
                if _mobile_broadcast:
                    _mobile_broadcast(msg)
                try:
                    self.ui.write_log("[PROACTIVE] {}".format(msg))
                except Exception:
                    pass
            try:
                _state_file.parent.mkdir(parents=True, exist_ok=True)
                _state_file.write_text(
                    _json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
            except Exception:
                pass
        except Exception as _pe:
            self.ui.write_log("[PROACTIVE] Error: {}".format(str(_pe)[:80]))

    async def _drain_audio_queue(self):
        """Vacía la cola de audio para cortar la reproducción de inmediato."""
        if self.audio_in_queue:
            while not self.audio_in_queue.empty():
                try:
                    self.audio_in_queue.get_nowait()
                except Exception:
                    break
        self.set_speaking(False)
        if self._turn_done_event:
            self._turn_done_event.set()
        if not self.ui.muted:
            self.ui.set_state("LISTENING")

    def _build_config(self) -> types.LiveConnectConfig:
        from datetime import datetime

        memory     = load_memory()
        mem_str    = format_memory_for_prompt(memory)
        sys_prompt = load_system_prompt()

        # ── Inject real memory context (partes aparte, ANTES del sys_prompt
        #    para que sobrevivan al truncado) ──
        memory_context = ""
        try:
            from actions.eris_db import memory_all, episodic_recent
            mems = memory_all(5)
            if mems:
                memory_context += "[MEMORIAS]\n"
                for m in mems[:4]:
                    memory_context += f"- {m['key']}: {str(m['value'])[:120]}\n"
            eps = episodic_recent(8)
            if eps:
                _clean_eps = [e for e in eps
                              if e.get("category") != "idle_learning"
                              and "no encontre" not in str(e.get("event", "")).lower()]
                if _clean_eps:
                    memory_context += "\n[EVENTOS RECIENTES]\n"
                    for e in _clean_eps[:3]:
                        memory_context += f"- {e['event'][:120]}\n"
        except Exception:
            pass

        # ── Memoria semántica (semantic.json / episodic.json): lectura directa,
        #    barata, sin embeddings — la memoria semántica se usa en el prompt ──
        semantic_context = ""
        try:
            from pathlib import Path as _Path
            _mem_dir = _Path(__file__).resolve().parent / "memory"
            _sem_file = _mem_dir / "semantic.json"
            _epi_file = _mem_dir / "episodic.json"
            if _sem_file.exists():
                _facts = json.loads(_sem_file.read_text(encoding="utf-8"))
                if isinstance(_facts, list) and _facts:
                    _clean_facts = []
                    for f in _facts:
                        _subj = str(f.get("subject", ""))
                        _obj  = str(f.get("object", ""))
                        _low  = (_subj + " " + _obj).lower()
                        if "aprendi sobre" in _low or "no encontre" in _low or "no se encontraron" in _low:
                            continue
                        if float(f.get("confidence", 0) or 0) < 0.45:
                            continue
                        _clean_facts.append(f)
                    if _clean_facts:
                        semantic_context += "[HECHOS SEMANTICOS]\n"
                        for f in _clean_facts[-4:]:
                            semantic_context += "- {} {} {} (conf {:.0f}%)\n".format(
                                str(f.get("subject", ""))[:60],
                                str(f.get("predicate", ""))[:30],
                                str(f.get("object", ""))[:80],
                                float(f.get("confidence", 0) or 0),
                            )
            if _epi_file.exists():
                _epi = json.loads(_epi_file.read_text(encoding="utf-8"))
                if isinstance(_epi, list) and _epi:
                    _clean_epi = []
                    for e in _epi:
                        _evt = str(e.get("event", ""))
                        if "no encontre" in _evt.lower() or "no se encontraron" in _evt.lower():
                            continue
                        _clean_epi.append(e)
                    if _clean_epi:
                        semantic_context += "\n[EPISODIOS SEMANTICOS]\n"
                        for e in _clean_epi[-3:]:
                            semantic_context += "- {} (imp {:.1f})\n".format(
                                str(e.get("event", ""))[:120],
                                float(e.get("importance", 0) or 0),
                            )
        except Exception:
            pass

        # ── RAG knowledge context: solo si Ollama responde rápido
        #    (evita el stall de 30s por timeout de embed al reconectar) ──
        rag_context = ""
        try:
            from core.llm_bridge import ping as _ollama_ping
            from core.rag_pipeline import query_documents, stats
            if _ollama_ping(1.0):
                _rag_stats = stats()
                if _rag_stats.get("documents", 0) > 0:
                    # Usar la conversación reciente (sobrevive a reconexiones)
                    # como base de la query, NO memory.keys() (conocimiento genérico).
                    _recent = getattr(self, "_convo_ctx", None) or []
                    _query_txt = " ".join(_recent[-4:]).strip()
                    if not _query_txt:
                        _query_txt = "temas principales"
                    _rag_results = query_documents(_query_txt[:500], top_k=4)
                    if _rag_results:
                        rag_context = "[CONOCIMIENTO INDEXADO]\n"
                        for r in _rag_results:
                            rag_context += f"- {r['filename']}: {r['text'][:200]}\n"
        except Exception:
            pass

        # ── Digest diario (memoria de largo plazo) ──
        digest_block = ""
        try:
            from core.daily_digest import inject_digest
            digest_block = inject_digest()
        except Exception:
            pass

        # Get time context (from worldtimeapi.org or system fallback)
        time_ctx = get_time_context()

        parts = [time_ctx]

        # ── Inject emotional state & personality into prompt ──
        # (antes de sys_prompt para que sobrevivan al truncado de 32K)
        try:
            from actions.emotional_growth import _load as _eg_load, get_prompt_injection
            from core.personality_engine import get_tone_for_response
            from core.emotional_state import get_tone_instruction as _state_tone
            from actions.relationship import inject_relationship
            from core.style_engine import inject_style
            _eg_state = _eg_load()
            _injection = get_prompt_injection(_eg_state)
            _tone = get_tone_for_response()
            parts.append(f"[PERSONALIDAD] {_tone}")
            parts.append(f"[EMOCION] {_injection}")
            _state_tone_txt = _state_tone() if _state_tone else ""
            if _state_tone_txt:
                parts.append(f"[TONO] {_state_tone_txt}")
            _rel = inject_relationship()
            if _rel:
                parts.append(_rel)
            _style = inject_style()
            if _style:
                parts.append(_style)
        except Exception:
            pass

        # ── Inject gustos into prompt ──
        try:
            from actions.gustos import inject_gustos
            _gustos = inject_gustos()
            if _gustos:
                parts.append(_gustos)
        except Exception:
            pass

        if memory_context:
            parts.append(memory_context)
        if semantic_context:
            parts.append(semantic_context)
        if rag_context:
            parts.append(rag_context)
        if digest_block:
            parts.append(digest_block)
        if mem_str:
            parts.append(mem_str)
        # ── Lecciones aprendidas y correcciones: el auto-aprendizaje SÍ impacta
        #    respuestas futuras (solo lecciones de calidad, sin placeholders) ──
        learning_context = ""
        try:
            _mem_dir = _Path(__file__).resolve().parent / "memory"
            _lessons_file = _mem_dir / "learned_lessons.json"
            _corrections_file = _mem_dir / "auto_corrections.json"
            if _lessons_file.exists():
                _lessons = json.loads(_lessons_file.read_text(encoding="utf-8"))
                if isinstance(_lessons, list):
                    _good = [l for l in _lessons
                             if not str(l.get("lesson", "")).startswith("[Sin corrección")
                             and str(l.get("lesson", "")).strip()]
                    if _good:
                        learning_context += "[LECCIONES APRENDIDAS]\n"
                        for l in _good[-5:]:
                            _cat = l.get("category", "general")
                            _txt = str(l.get("lesson", ""))[:160]
                            learning_context += f"- [{_cat}] {_txt}\n"
            if _corrections_file.exists():
                _corr = json.loads(_corrections_file.read_text(encoding="utf-8"))
                if isinstance(_corr, list):
                    _good = [c for c in _corr
                             if str(c.get("corrected", "")).strip()
                             and not str(c.get("corrected", "")).startswith("[Sin corrección")]
                    if _good:
                        learning_context += "\n[CORRECCIONES RECIENTES (evitar estos errores)]\n"
                        for c in _good[-3:]:
                            learning_context += f"- {str(c.get('reason', ''))[:100]} → {str(c.get('corrected', ''))[:120]}\n"
            if learning_context:
                parts.append(learning_context)
        except Exception:
            pass
        # ── Contexto de conversación reciente (sobrevive a reconexiones) ──
        if getattr(self, "_convo_ctx", None):
            parts.append(
                "[CONTEXTO DE CONVERSACIÓN RECIENTE (lo que veníamos haciendo)]\n"
                + "\n".join(self._convo_ctx)
            )
        parts.append(sys_prompt)

        # ── Smart trim: nunca cortar lo esencial (personalidad, relación,
        #    estilo, memoria, digest). Se recorta solo la cola del prompt base.
        #    60000 chars ≈ ~15K tokens (Gemini 3.1 Flash aguanta ~1M) — el prompt
        #    completo (~49K) entra sin perder secciones críticas. ──
        MAX_SYSTEM_CHARS = 60000
        system_text = "\n".join(parts)
        if len(system_text) > MAX_SYSTEM_CHARS:
            _essential = "\n".join(parts[:-1])
            _budget = MAX_SYSTEM_CHARS - len(_essential) - 80
            if _budget > 2000:
                sys_prompt = sys_prompt[:_budget] + "\n[CONTEXTO TRUNCADO]"
                system_text = _essential + "\n" + sys_prompt
            else:
                system_text = system_text[:MAX_SYSTEM_CHARS] + "\n[CONTEXTO TRUNCADO]"
        # Build SpeechConfig — try to set speaking rate for faster delivery
        _voice_name = get_eris_voice()
        _speech_cfg = None
        try:
            _speech_cfg = types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=_voice_name
                    )
                )
            )
        except Exception:
            _speech_cfg = None

        cfg_kwargs: dict = dict(
            response_modalities=["AUDIO"],
            speech_config=_speech_cfg,
            system_instruction=system_text,
            tools=[{"function_declarations": TOOL_DECLARATIONS}],
            output_audio_transcription=types.AudioTranscriptionConfig(),
            input_audio_transcription=types.AudioTranscriptionConfig(),
        )

        try:
            cfg_kwargs["realtime_input_config"] = types.RealtimeInputConfig(
                automatic_activity_detection=types.AutomaticActivityDetection(
                    start_of_speech_sensitivity="START_SENSITIVITY_HIGH",
                    end_of_speech_sensitivity="END_SENSITIVITY_HIGH",
                    prefix_padding_ms=60,
                    silence_duration_ms=350,
                )
            )
        except Exception:
            cfg_kwargs["realtime_input_config"] = {
                "automatic_activity_detection": {
                    "start_of_speech_sensitivity": "START_SENSITIVITY_HIGH",
                    "end_of_speech_sensitivity": "END_SENSITIVITY_HIGH",
                    "prefix_padding_ms": 100,
                    "silence_duration_ms": 500,
                }
            }

        try:
            cfg_kwargs["temperature"] = 0.2
        except Exception:
            pass

        return types.LiveConnectConfig(**cfg_kwargs)


    async def _execute_tool(self, fc) -> types.FunctionResponse:
        _resp = await self._tool_dispatcher.execute(fc)
        try:
            _tool_name = getattr(fc, "name", "tool")
            _txt = str(getattr(_resp, "response", ""))[:400]
            if _txt:
                self._remember(f"[Herramienta {_tool_name}] {_txt}")
        except Exception:
            pass
        return _resp

    async def _send_realtime(self):
        _ready = getattr(self, '_session_ready', None)
        if _ready is not None:
            try:
                await asyncio.wait_for(_ready.wait(), timeout=3.0)
            except asyncio.TimeoutError:
                pass
        _batch = []
        _SEND_EVERY = 4
        try:
            while True:
                try:
                    msg = await self.out_queue.get()
                    _batch.append(msg["data"])
                    if len(_batch) < _SEND_EVERY:
                        continue
                    blob = types.Blob(data=b"".join(_batch), mimeType="audio/pcm;rate=16000")
                    try:
                        await self.session.send_realtime_input(audio=blob)
                    except Exception as _send_err:
                        print(f"[ERIS] SEND FAILED: {type(_send_err).__name__}")
                        raise
                    _batch.clear()
                except Exception as e:
                    print(f"[ERIS] send_realtime error: {e}")
                    traceback.print_exc()
        finally:
            if _batch:
                try:
                    blob = types.Blob(data=b"".join(_batch), mimeType="audio/pcm;rate=16000")
                    await self.session.send_realtime_input(audio=blob)
                except Exception:
                    pass

    async def _listen_audio(self):
        print("[ERIS] 🎤 Mic iniciado")
        _ready = getattr(self, '_session_ready', None)
        if _ready is not None:
            try:
                await asyncio.wait_for(_ready.wait(), timeout=3.0)
            except asyncio.TimeoutError:
                pass  # start anyway
        loop = asyncio.get_event_loop()

        def callback(indata, frames, time_info, status):
            # ── Modo suspensión: solo Vosk local para frases de despertar ──
            if getattr(self, "is_sleeping", False):
                if getattr(self, "vosk_recognizer", None):
                    audio_data = indata.tobytes()
                    if self.vosk_recognizer.AcceptWaveform(audio_data):
                        res = json.loads(self.vosk_recognizer.Result())
                        text = res.get("text", "").lower()
                        # Mismo matcher tolerante de nombre/frases que en modo normal
                        if _has_wake_word(text):
                            self.is_sleeping = False
                            self._open_wake_gate()
                            self.ui.set_state("LISTENING")
                            self.ui.write_log("SYS: Despierta!")
                            # Show window from tray
                            try:
                                def _show():
                                    self.ui.show_and_activate()
                                    self.ui.tray_icon.showMessage("ERIS", "Estoy aqui. Dime.", 
                                        self.ui.tray_icon.icon(), 3000)
                                from PyQt6.QtCore import QTimer
                                QTimer.singleShot(0, _show)
                            except: pass
                            # Play wake sound
                            try:
                                import winsound
                                winsound.Beep(500, 200)
                                winsound.Beep(700, 200)
                            except: pass
                    else:
                        # Detección incremental: despertar apenas reconoce el nombre
                        try:
                            partial = json.loads(self.vosk_recognizer.PartialResult())
                            _pt = partial.get("partial", "").strip()
                            if len(_pt.split()) >= 2 and _has_wake_word(_pt):
                                self.is_sleeping = False
                                self._open_wake_gate()
                                self.ui.set_state("LISTENING")
                                self.ui.write_log("SYS: Despierta!")
                                try:
                                    import winsound
                                    winsound.Beep(500, 200)
                                    winsound.Beep(700, 200)
                                except Exception:
                                    pass
                        except Exception:
                            pass
                return

            with self._speaking_lock:
                eris_speaking = self._is_speaking

            # ── Micrófono silenciado: solo interrupción por voz mientras habla ──
            if self.ui.muted:
                if eris_speaking:
                    # When ERIS is speaking, also update level (from playback perspective)
                    try:
                        rms = float(np.sqrt(np.mean(indata.astype(np.float32) ** 2))) / 32768.0
                        self.ui.set_audio_level(min(1.0, rms * 15))
                        
                        # Voice interruption: uses cached threshold (se lee 1 vez, no 60x/s)
                        threshold = getattr(self, "_mic_threshold", None)
                        if threshold is None:
                            try:
                                from memory.config_manager import BASE_DIR
                                api_cfg_path = BASE_DIR / "config" / "api_keys.json"
                                if api_cfg_path.exists():
                                    c = json.loads(api_cfg_path.read_text(encoding="utf-8"))
                                    threshold = float(c.get("mic_sensitivity", 0.003))
                                else:
                                    threshold = 0.003
                            except Exception:
                                threshold = 0.003
                            self._mic_threshold = threshold
                        
                        interrupt_threshold = max(0.015, threshold * 3.5)
                        
                        if rms > interrupt_threshold:
                            self._interrupt_frames = getattr(self, "_interrupt_frames", 0) + 1
                            if self._interrupt_frames >= 5:  # ~100ms of continuous voice
                                if not self._stop_requested.is_set():
                                    self._stop_requested.set()
                                    print(f"[ERIS] 🎤 Voice interruption detected! (RMS: {rms:.4f} > {interrupt_threshold:.4f})")
                                    from PyQt6.QtCore import QTimer
                                    QTimer.singleShot(0, self._on_stop_pressed)
                        else:
                            self._interrupt_frames = 0
                    except Exception:
                        pass
                return

            # ── Half-duplex anti-eco: mientras ERIS habla NO se envía el mic
            #    a Gemini. Sin esto, ERIS se escucha a sí misma por el altavoz
            #    y entra en un bucle de eco que la deja "pillada" emitiendo un
            #    sonido infinito ("mmmmmmmm..."). Se vuelve a escuchar al terminar. ──
            if eris_speaking:
                try:
                    rms = float(np.sqrt(np.mean(indata.astype(np.float32) ** 2))) / 32768.0
                    self.ui.set_audio_level(min(1.0, rms * 15))
                except Exception:
                    pass
                return
            gain = getattr(self, "_mic_gain", None)
            if gain is None:
                try:
                    from memory.config_manager import BASE_DIR
                    api_cfg_path = BASE_DIR / "config" / "api_keys.json"
                    if api_cfg_path.exists():
                        c = json.loads(api_cfg_path.read_text(encoding="utf-8"))
                        gain = float(c.get("mic_gain", 5.0))
                    else:
                        gain = 5.0
                except Exception:
                    gain = 5.0
                self._mic_gain = gain
            # Amplify audio for better detection
            amplified = (indata.astype(np.float32) * gain).clip(-32768, 32767).astype(np.int16)
            # Calculate RMS audio level for sphere visualization
            try:
                rms = float(np.sqrt(np.mean(amplified.astype(np.float32) ** 2))) / 32768.0
                # Mientras ERIS habla, el orbe se mueve con SU voz (nivel de
                # playback), no con el ruido ambiente del micro
                if not eris_speaking:
                    self.ui.set_orb_audio_level(min(1.0, rms * 18))
            except Exception:
                rms = 0.0
            data = amplified.tobytes()

            # ── Activación por nombre: el audio NO va a Gemini hasta oír "Eris" ──
            if self._wake_mode and not self._wake_gate_open:
                self._wake_buffer.append((data, rms >= _WAKE_SPEECH_THRESHOLD))
                self._wake_buffer_bytes += len(data)
                max_bytes = int(16000 * 2 * _WAKE_BUFFER_SECONDS)
                while self._wake_buffer_bytes > max_bytes and self._wake_buffer:
                    old, _ = self._wake_buffer.pop(0)
                    self._wake_buffer_bytes -= len(old)
                if getattr(self, "vosk_recognizer", None):
                    if self.vosk_recognizer.AcceptWaveform(data):
                        res = json.loads(self.vosk_recognizer.Result())
                        text = res.get("text", "").lower()
                        if _has_wake_word(text):
                            self._open_wake_gate()
                    else:
                        # Detección incremental: abrir el gate apenas dice el
                        # nombre (no esperar al final de la oración) → menor latencia
                        try:
                            partial = json.loads(self.vosk_recognizer.PartialResult())
                            _pt = partial.get("partial", "").strip()
                            if len(_pt.split()) >= 2 and _has_wake_word(_pt):
                                self._open_wake_gate()
                        except Exception:
                            pass
                return

            # ── Gate abierto (o modo libre): audio en vivo a Gemini ──
            if self._wake_mode:
                if rms >= _WAKE_SPEECH_THRESHOLD:
                    self._wake_last_activity = time.time()
                elif (not eris_speaking
                      and (time.time() - self._wake_last_activity) > _WAKE_CONVO_TIMEOUT):
                    self._close_wake_gate()
                    return
            loop.call_soon_threadsafe(self._put_audio_chunk, data)

        try:
            try:
                mic_device_idx = resolve_mic()
            except Exception:
                mic_device_idx = None
            if mic_device_idx is not None:
                try:
                    _mic_name = sd.query_devices(mic_device_idx)["name"]
                except Exception:
                    _mic_name = ""
            else:
                _mic_name = "(default)"
            print(f"[ERIS] 🎤 Mic seleccionado: {mic_device_idx} {_mic_name}")

            _mic_kw = dict(
                samplerate=SEND_SAMPLE_RATE,
                channels=CHANNELS,
                dtype="int16",
                blocksize=CHUNK_SIZE,
                callback=callback,
            )
            try:
                mic_stream = sd.InputStream(device=mic_device_idx, **_mic_kw)
            except Exception as e:
                print(f"[ERIS] ⚠️ Mic '{mic_device_idx}' falló ({e}); usando default")
                mic_stream = sd.InputStream(device=None, **_mic_kw)

            with mic_stream:
                print("[ERIS] 🎤 Mic stream open")
                while True:
                    await asyncio.sleep(0.01)  # 10ms — máxima responsividad del mic
        except Exception as e:
            print(f"[ERIS] ❌ Mic: {e}")
            raise

    async def _receive_audio(self):
        print("[ERIS] 👂 Recv iniciado")
        # Signal: session ready once first WS message arrives
        if not hasattr(self, '_session_ready') or self._session_ready is None:
            self._session_ready = asyncio.Event()
        _first_msg = True
        _orig_recv = self.session._ws.recv
        async def _patched_recv(*a, **kw):
            nonlocal _first_msg
            msg = await _orig_recv(*a, **kw)
            if _first_msg:
                _first_msg = False
                self._session_ready.set()
            return msg
        self.session._ws.recv = _patched_recv
        out_buf, in_buf = [], []
        out_full = ""            # acumulador O(n) de la respuesta (sin joins por chunk)
        _mobile_buf = []         # batch para broadcast mobile (flush por frase)
        _first_chunk   = True
        _last_tool     = None   # track which tool was executing when error hit

        try:
            while True:
                async for response in self.session.receive():

                    if response.data:
                        if not self._stop_requested.is_set():
                            self.audio_in_queue.put_nowait(response.data)

                    if response.server_content:
                        sc = response.server_content
                        
                        if getattr(sc, "interrupted", False):
                            self.ui.write_log("SYS: ⛔ Interrumpido por voz.")
                            if self._loop:
                                asyncio.run_coroutine_threadsafe(self._drain_audio_queue(), self._loop)

                        if sc.output_transcription and sc.output_transcription.text:
                            txt = _clean_transcript(sc.output_transcription.text)
                            if txt:
                                if _first_chunk:
                                    self.ui.clear_eris_response()
                                    _first_chunk = False
                                    self.ui.set_state("THINKING")
                                    # Cara según el estado emocional actual de ERIS
                                    try:
                                        from core.emotional_state import get_face_expression
                                        self.ui.show_expression(get_face_expression(), "")
                                    except Exception:
                                        pass
                                    if self._first_transcript_time:
                                        now = time.time()
                                        print(f"[TIMING] ✅ First response chunk: +{now - self._first_transcript_time:.1f}s | text: {txt}")
                                out_buf.append(txt)
                                out_full = (out_full + " " + txt).strip() if out_full else txt
                                self.ui.stream_eris_chunk(txt)
                                self.ui.express_emotion(out_full)
                                # Broadcast a mobile agrupado por frase (evita flood)
                                _mobile_buf.append(txt)
                                _m_joined = "".join(_mobile_buf)
                                if _m_joined.rstrip().endswith((".", "!", "?", "\n", ":", ";")) or len(_m_joined) >= 150:
                                    if _mobile_broadcast:
                                        _mobile_broadcast(_m_joined)
                                    _mobile_buf = []

                        if sc.input_transcription and sc.input_transcription.text:
                            txt = _clean_transcript(sc.input_transcription.text)
                            if txt:
                                if not self._first_transcript_time:
                                    self._first_transcript_time = time.time()
                                    print(f"[TIMING] 🔍 Input transcript: {txt}")
                                in_buf.append(txt)

                        if sc.turn_complete:
                            self._stop_requested.clear()
                            if self._turn_done_event:
                                self._turn_done_event.set()
                            full_in = " ".join(in_buf).strip()
                            if full_in and full_in != self._last_text_trigger:
                                self.ui.write_log(f"Tú: {full_in}")
                                threading.Thread(target=self._fire_phrase_triggers, args=(full_in,), daemon=True).start()
                            # Reacción emocional también en la vía por voz
                            if full_in and full_in != self._last_text_trigger:
                                if react_to_user_interaction:
                                    threading.Thread(target=react_to_user_interaction, daemon=True).start()
                                if _eg_on_user_msg:
                                    threading.Thread(target=lambda: _eg_on_user_msg(None, full_in), daemon=True).start()
                                try:
                                    from core.emotional_state import react_to_user_text
                                    _face = react_to_user_text(full_in)
                                    if _face:
                                        self.ui.show_expression(_face)
                                except Exception:
                                    pass
                            # Activación por nombre: la conversación queda abierta
                            # (no repetir "Eris") hasta que el usuario la cierre con
                            # una frase de cierre o por inactividad
                            if self._wake_mode:
                                self._wake_last_activity = time.time()
                                if self._is_end_conversation(full_in):
                                    self._close_wake_gate()
                                elif not self._is_speaking:
                                    # Respuesta solo texto: volver a escuchar
                                    self.ui.set_state("LISTENING")
                            # ── Self-improvement cycle (async, non-blocking) ──
                            try:
                                if full_in and out_full:
                                    _si_context = {"session_id": getattr(self, '_session_id', '')}
                                    threading.Thread(
                                        target=_run_self_improvement,
                                        args=(full_in, out_full, _si_context),
                                        daemon=True
                                    ).start()
                            except Exception:
                                pass
                            # Flush restante del broadcast mobile
                            if _mobile_buf and _mobile_broadcast:
                                _mobile_broadcast("".join(_mobile_buf))
                            _mobile_buf = []
                            # Persistir turno en contexto de reconexión
                            if full_in:
                                self._remember(f"Usuario: {full_in}")
                            if out_full:
                                self._remember(f"ERIS: {out_full}")
                            # ── Memoria episódica de largo plazo: guardar solo
                            #    turnos significativos, en hilo daemon ──
                            try:
                                if full_in and out_full and len(full_in) >= 10:
                                    _mem_evt = (
                                        f"Conversación: usuario preguntó \"{full_in[:140]}\" "
                                        f"y ERIS respondió \"{out_full[:140]}\""
                                    )
                                    threading.Thread(
                                        target=_store_episode,
                                        args=(_mem_evt, "conversation", 0.6),
                                        daemon=True,
                                    ).start()
                            except Exception:
                                pass
                            in_buf = []
                            out_buf = []
                            out_full = ""
                            _first_chunk = True

                    if response.tool_call:
                        self.ui.clear_eris_response()
                        self.ui.set_state("THINKING")
                        _first_chunk = True
                        fcs = response.tool_call.function_calls
                        for fc in fcs:
                            print(f"[ERIS] 📞 {fc.name}")
                            _last_tool = fc.name
                        # Execute all tool calls in parallel when there are multiple
                        if len(fcs) > 1:
                            tasks = [asyncio.create_task(self._execute_tool(fc)) for fc in fcs]
                            fn_responses = list(await asyncio.gather(*tasks))
                        else:
                            fn_responses = [await self._execute_tool(fcs[0])]
                        try:
                            await self.session.send_tool_response(
                                function_responses=fn_responses
                            )
                            _last_tool = None  # only clear AFTER successful send
                        except Exception as tool_err:
                            print(f"[ERIS] ❌ send_tool_response failed: {tool_err}")
                            # ── Resilient: save results for delivery on reconnect ──
                            try:
                                from core.resilient import get_manager
                                _rm = get_manager()
                                for resp in fn_responses:
                                    _rm.save_result_for_delivery(resp.name, str(resp.response)[:5000])
                                print("[RESILIENT] 💾 Tool results saved for later delivery")
                            except Exception as _re:
                                print(f"[RESILIENT] Error saving results: {_re}")
                            raise
        except Exception as e:
            # ── Drain remaining audio before session dies (prevent mid-word cutoff) ──
            try:
                if self.audio_in_queue and not self.audio_in_queue.empty():
                    _chunks = []
                    while not self.audio_in_queue.empty():
                        try:
                            _chunks.append(self.audio_in_queue.get_nowait())
                        except Exception:
                            break
                    if _chunks:
                        print(f"[ERIS] 🔊 Draining {_chunks_len if False else len(_chunks)} remaining audio chunks before reconnect")
            except Exception:
                pass
            msg  = str(e)
            code = getattr(e, "status_code", 0) or getattr(e, "code", 0) or 0
            # Detect 1011 (internal server error) regardless of exception type
            if code == 1011 or "1011" in msg or "Internal error" in msg:
                tool_info = f" durante '{_last_tool}'" if _last_tool else ""
                print(f"[ERIS] ⚡ API 1011{tool_info} — reconectando...")
                self._api_1011_tool = _last_tool
            elif code == 1008 or "1008" in msg or "policy violation" in msg.lower():
                print(f"[ERIS] ⚠️ Sesión cerrada por la API (1008, política). Reconectando...")
            else:
                print(f"[ERIS] ❌ Recv: {e}")
                traceback.print_exc()
            raise

    async def _play_audio(self):
        print("[ERIS] 🔊 Play iniciado")

        # Try WinAudioOutput first (uses Windows Multimedia API, works with BT headsets)
        _use_win_audio = False
        try:
            from core.win_audio_output import WinAudioOutput
            from core.audio_config import resolve_waveout
            _win_out_device = resolve_waveout()
            _win_out = WinAudioOutput(
                channels=CHANNELS,
                samplerate=RECEIVE_SAMPLE_RATE,
                bits_per_sample=16,
                device=_win_out_device,
            )
            if _win_out.open():
                _use_win_audio = True
                print(f"[ERIS] 🎧 Usando WinAudioOutput: {_win_out.device_name or _win_out_device}")
            else:
                print("[ERIS] ⚠️ WinAudioOutput no pudo abrir el dispositivo elegido; probando default")
                _win_out = WinAudioOutput(channels=CHANNELS, samplerate=RECEIVE_SAMPLE_RATE, bits_per_sample=16)
                if _win_out.open():
                    _use_win_audio = True
                    print(f"[ERIS] 🎧 Usando WinAudioOutput: {_win_out.device_name or '(default)'}")
                else:
                    _win_out = None
        except Exception as _we:
            print(f"[ERIS] ⚠️ WinAudioOutput no disponible: {_we}")
            _win_out = None

        # Fallback: sounddevice
        if not _use_win_audio:
            try:
                speaker_device_idx = resolve_speaker()
            except Exception:
                speaker_device_idx = None
            if speaker_device_idx is not None:
                try:
                    _speaker_name = sd.query_devices(speaker_device_idx)["name"]
                except Exception:
                    _speaker_name = ""
            else:
                _speaker_name = "(default)"
            print(f"[ERIS] 🎧 Altavoz seleccionado: {speaker_device_idx} {_speaker_name}")
            _play_channels = CHANNELS
            if speaker_device_idx is not None:
                try:
                    _d = sd.query_devices(speaker_device_idx)
                    _ch = _d["max_output_channels"]
                    if _ch > 0:
                        _play_channels = _ch
                except Exception:
                    pass
            _open_kw = dict(
                samplerate=RECEIVE_SAMPLE_RATE,
                channels=_play_channels,
                dtype="int16",
                blocksize=PLAY_CHUNK_SIZE,
            )
            try:
                stream = sd.RawOutputStream(device=speaker_device_idx, **_open_kw)
            except Exception:
                print(f"[ERIS] ⚠️ Fallback: using default speaker device")
                _play_channels = CHANNELS
                stream = sd.RawOutputStream(device=None, channels=CHANNELS,
                                            samplerate=RECEIVE_SAMPLE_RATE,
                                            dtype="int16", blocksize=PLAY_CHUNK_SIZE)
            stream.start()

        def _write_audio(data: bytes):
            if _use_win_audio:
                _win_out.write(data)
            else:
                stream.write(data)
            # Alimentar el orbe con el volumen real de la voz de ERIS
            try:
                arr = np.frombuffer(data, dtype=np.int16)
                if arr.size:
                    rms = float(np.sqrt(np.mean(arr.astype(np.float32) ** 2))) / 32768.0
                    self.ui.set_audio_level(min(1.0, rms * 12))
            except Exception:
                pass

        try:
            # ── Corte de seguridad: si ERIS emite audio continuo más de
            #    max_speech_seconds (default 45s, configurable en api_keys.json),
            #    se corta por si el modelo entró en un bucle de voz infinito. ──
            _max_speech = 45.0
            try:
                _cfg = json.loads(
                    (Path(__file__).resolve().parent / "config" / "api_keys.json")
                    .read_text(encoding="utf-8"))
                _max_speech = float(_cfg.get("max_speech_seconds", 45.0))
            except Exception:
                pass
            _speech_started = None
            while True:
                try:
                    chunk = await asyncio.wait_for(
                        self.audio_in_queue.get(),
                        timeout=0.05
                    )
                except asyncio.TimeoutError:
                    if (
                        self._turn_done_event
                        and self._turn_done_event.is_set()
                        and self.audio_in_queue.empty()
                    ):
                        self.set_speaking(False)
                        self._turn_done_event.clear()
                    continue

                if _speech_started is None:
                    _speech_started = time.time()
                elif time.time() - _speech_started > _max_speech:
                    self.ui.write_log("SYS: ⏱️ Corte de seguridad de audio ({}s) — posible bucle.".format(int(_max_speech)))
                    print(f"[ERIS] ⏱️ Safety audio cut after {int(_max_speech)}s")
                    await self._drain_audio_queue()
                    _speech_started = None
                    continue

                self.set_speaking(True)
                _write_audio(chunk)
        except Exception as e:
            print(f"[ERIS] ❌ Play: {e}")
            raise
        finally:
            self.set_speaking(False)
            if _use_win_audio:
                _win_out.flush()
                _win_out.close()
            else:
                stream.stop()
                stream.close()

    async def run(self):
        # ── Check connectivity before attempting Gemini ──
        if self._connectivity:
            if not self._connectivity.is_online():
                print("[ERIS] 🔴 Sin internet detectado. Iniciando modo OFFLINE...")
                self.ui.write_log("SYS: 🔴 Sin internet. Modo OFFLINE activado.")
                self._fallback_mode = True
                if self._offline_pipeline:
                    self._offline_pipeline.start()
                # In offline mode, just wait for connectivity changes
                while not self._connectivity.is_online():
                    await asyncio.sleep(2)
                print("[ERIS] 🟢 Internet restaurado. Conectando a Gemini...")
                self.ui.write_log("SYS: 🟢 Internet restaurado. Conectando a Gemini...")

        client = genai.Client(
            api_key=get_api_key(),
            http_options={"api_version": "v1beta"}
        )

        reconnect_delay   = 1.0
        consecutive_fails = 0
        _last_session_ok  = False   # sesión previa estable (>=30s) → resetear backoff
        _session_started  = 0.0     # marca de tiempo de la sesión actual

        while True:
            try:
                print("[ERIS] 🔌 Conectando...")
                self.ui.set_state("THINKING")
                config = self._build_config()

                async with (
                    client.aio.live.connect(model=LIVE_MODEL, config=config) as session,
                    asyncio.TaskGroup() as tg,
                ):
                    self.session          = session
                    self._loop            = asyncio.get_event_loop()
                    self.audio_in_queue   = asyncio.Queue()
                    self.out_queue        = asyncio.Queue(maxsize=500)  # buffer ~8s de audio para evitar drops con Bluetooth
                    self._turn_done_event = asyncio.Event()
                    self._reconnect_event = asyncio.Event()
                    self._session_ready   = asyncio.Event()
                    # ── CRITICAL: clear stop flag on reconnect so voice works ──
                    if hasattr(self, '_stop_requested') and self._stop_requested:
                        self._stop_requested.clear()
                        print("[ERIS] 🔊 _stop_requested cleared — voice restored")
                    # ── Drain stale audio from previous session ──
                    if hasattr(self, 'audio_in_queue') and self.audio_in_queue:
                        _drained = 0
                        while not self.audio_in_queue.empty():
                            try:
                                self.audio_in_queue.get_nowait()
                                _drained += 1
                            except Exception:
                                break
                        if _drained:
                            print(f"[ERIS] 🧹 Drained {_drained} stale audio chunks")

                    print("[ERIS] ✅ Conectado.")
                    # Solo resetear backoff si la sesión anterior fue estable (>=30s).
                    # Si la API cortó al instante (ej. 1008 por cuota), mantener el
                    # contador para que el backoff crezca y active el fallback Ollama.
                    if _last_session_ok:
                        reconnect_delay   = 1.0
                        consecutive_fails = 0
                    _last_session_ok = False
                    _session_started = time.monotonic()
                    # Activación por nombre: estado inicial en standby
                    self._wake_gate_open = not self._wake_mode
                    self._wake_buffer = []
                    self._wake_buffer_bytes = 0
                    if self._wake_mode:
                        self.ui.set_state("IDLE")
                        if not self._online_logged:
                            self._online_logged = True
                            self.ui.write_log("SYS: ERIS en línea. Decime 'Eris, ...' y te respondo.")
                        else:
                            print("[ERIS] 🟢 Reconectado.")
                    else:
                        self.ui.set_state("LISTENING")
                        if not self._online_logged:
                            self._online_logged = True
                            self.ui.write_log("SYS: ERIS en línea.")
                    reconnect_delay   = 1.0   # reset backoff on successful connection
                    consecutive_fails = 0
                    self._api_1011_tool = None   # clear 1011 tool tracker
                    # Restore normal mode if coming from fallback
                    if self._fallback_mode:
                        self._fallback_mode = False
                        self.ui.write_log("SYS: ✅ Gemini reconectado. Modo normal restaurado.")
                        print("[FALLBACK] Gemini recuperado.")

                    # ── Resilient: deliver pending tool results on reconnect ──
                    try:
                        from core.resilient import get_manager
                        _rm = get_manager()
                        _pending = _rm.get_pending_tasks()
                        if _pending:
                            print(f"[RESILIENT] 📤 Delivering {len(_pending)} pending results on reconnect...")
                            for task in _pending:
                                result_text = task.get("result", "Resultado no disponible")
                                tool_name = task.get("tool", "unknown")
                                try:
                                    from google.genai import types as _gtypes
                                    _resp = _gtypes.FunctionResponse(
                                        id=task.get("id", ""),
                                        name=tool_name,
                                        response={"result": result_text[:3500]}
                                    )
                                    await self.session.send_tool_response(function_responses=[_resp])
                                    _rm.clear_delivered(task.get("id", ""))
                                    print(f"[RESILIENT] ✅ Delivered: {tool_name}")
                                except Exception as _del_err:
                                    print(f"[RESILIENT] ❌ Delivery failed for {tool_name}: {_del_err}")
                        # Also retry failed tasks
                        _retry_tasks = _rm.get_tasks_needing_retry()
                        if _retry_tasks:
                            print(f"[RESILIENT] 🔄 Retrying {len(_retry_tasks)} failed tasks...")
                            for task in _retry_tasks:
                                tool_name = task.get("tool", "unknown")
                                task_args = task.get("args", {})
                                task_id = task.get("id", "")
                                print(f"[RESILIENT] Retrying: {tool_name}")
                    except Exception as _res_err:
                        print(f"[RESILIENT] Recovery error: {_res_err}")

                    # ── First-connect extras ──────────────────────────────────
                    if self._first_connect:
                        self._first_connect = False
                        # Start Vision Guardian if enabled
                        try:
                            _start_vision_guardian(
                                inject_fn=self._inject_text,
                                speaking_fn=lambda: self._is_speaking,
                            )
                        except Exception as _vge:
                            print(f"[ERIS] VisionGuardian init error: {_vge}")
                        # Start ERIS Guardian (health/syntax monitor) in background
                        try:
                            from actions.eris_guardian import start_monitor as _start_guardian
                            _start_guardian()
                            print("[ERIS] 🛡️ Guardian de ERIS activo (monitoreo en background)")
                        except Exception as _gd_e:
                            print(f"[ERIS] Guardian init error: {_gd_e}")
                        # Auto morning brief (6am–12pm, once per day)
                        _hour = __import__("datetime").datetime.now().hour
                        if 6 <= _hour < 12 and not already_briefed_today():
                            async def _auto_brief():
                                await asyncio.sleep(5)
                                try:
                                    await self.session.send_realtime_input(text="[AUTO] Dame el informe matutino del día.")
                                except Exception as _abe:
                                    print(f"[ERIS] Auto brief error: {_abe}")
                            tg.create_task(_auto_brief())

                    tg.create_task(self._send_realtime())
                    tg.create_task(self._listen_audio())
                    tg.create_task(self._receive_audio())
                    tg.create_task(self._play_audio())
                    tg.create_task(self._watch_reconnect())
                    # ── Resilient: periodic voice health check + stale task cleanup ──
                    tg.create_task(self._resilient_health_loop())

            except Exception as e:
                exceptions = e.exceptions if isinstance(e, ExceptionGroup) else [e]

                # La sesión anterior fue estable si vivió >=30s; eso habilita
                # el reset del backoff en la próxima conexión.
                _last_session_ok = (time.monotonic() - _session_started) >= 30.0

                is_handshake_timeout = False
                is_config_reconnect  = False
                for exc in exceptions:
                    msg = str(exc)
                    if "Config changed" in msg:
                        # Intentional reconnect triggered by config change — fast, no backoff
                        is_config_reconnect = True
                        consecutive_fails = 0
                    elif "timed out during opening handshake" in msg or (
                        isinstance(exc, TimeoutError) and "handshake" in msg
                    ):
                        # Timeout de WebSocket al conectar — error de red transitorio.
                        # NO incrementar consecutive_fails: sólo reintento rápido.
                        is_handshake_timeout = True
                        print(f"[ERIS] ⏱️ Timeout al conectar — reintentando en 1s...")
                    elif "1011" in msg or "Internal error" in msg:
                        tool_hint = self._api_1011_tool or ""
                        print(f"[ERIS] ⚡ API 1011{tool_hint and ' durante '+tool_hint} — reconectando...")
                        consecutive_fails += 1
                        if consecutive_fails >= 4:
                            self.ui.write_log(
                                "SYS: ⚠️ Error 1011 repetido. Esperando para no saturar la API...\n"
                                "SYS: Si persiste más de 2 min, reiniciá ERIS."
                            )
                        elif tool_hint:
                            self.ui.write_log(f"SYS: Error de servidor al ejecutar '{tool_hint}'. Reconectando...")
                        else:
                            self.ui.write_log("SYS: Error de servidor 1011. Reconectando...")
                    elif "1008" in msg or "policy violation" in msg.lower() or "not found for API version" in msg:
                        # Model not available / wrong API version — log clearly, retry with same model
                        print(f"[ERIS] ⚠️ Modelo no disponible en esta versión de API: {msg[:120]}")
                        if consecutive_fails == 0:  # solo avisar en la UI una vez por racha
                            self.ui.write_log("SYS: ⚠️ Modelo no disponible. Reintentando...")
                        consecutive_fails += 1
                    elif "voice" in msg.lower() or "speaker" in msg.lower():
                        print(f"[ERIS] ⚠️ Voz no valida: {msg[:200]}")
                        self.ui.write_log("SYS: ⚠️ Voz no valida. Revisá Ajustes > Voz.")
                    elif "1007" in msg or "invalid argument" in msg.lower() or "invalid frame" in msg.lower():
                        print(f"[ERIS] ⚠️ 1007: {msg[:200]}")
                        self.ui.write_log("SYS: Respuesta muy grande. Reconectando...")
                        consecutive_fails += 1
                    elif "1000" in msg or "going away" in msg.lower():
                        # Cierre normal de la sesión (expiró ~15 min) — silencioso
                        print(f"[ERIS] 🔄 Sesión expirada — reconectando...")
                        consecutive_fails = 0   # reset: no es un fallo
                    else:
                        print(f"[ERIS] ⚠️ {exc}")
                        traceback.print_exc()
                        consecutive_fails += 1

                if is_config_reconnect:
                    self.set_speaking(False)
                    if hasattr(self, '_stop_requested'):
                        self._stop_requested.clear()
                    self.ui.set_state("THINKING")
                    await asyncio.sleep(0.5)
                    continue

                if is_handshake_timeout:
                    # Timeout en handshake → reintento fijo de 1s, sin backoff
                    self.set_speaking(False)
                    if hasattr(self, '_stop_requested'):
                        self._stop_requested.clear()
                    self.ui.set_state("THINKING")
                    await asyncio.sleep(1.0)
                    continue

            self.set_speaking(False)
            if hasattr(self, '_stop_requested'):
                self._stop_requested.clear()
            self.ui.set_state("THINKING")

            # Exponential backoff con jitter para evitar thundering herd
            # After 5+ fails: wait up to 90s to let API rate limits recover
            if consecutive_fails > 1:
                max_delay = 90.0 if consecutive_fails >= 5 else 12.0
                reconnect_delay = min(reconnect_delay * 2, max_delay)
            elif consecutive_fails == 0:
                reconnect_delay = 1.0

            # ── Activar fallback Ollama después de 5 fallos consecutivos ──
            if consecutive_fails >= 5 and not self._fallback_mode:
                if _ollama_check and _ollama_check():
                    self._fallback_mode = True
                    self.ui.write_log(
                        "SYS: 🦙 Modo offline activado. Usando Ollama como respaldo.\n"
                        "SYS: Puedes escribirme mensajes de texto mientras Gemini se recupera."
                    )
                    print("[FALLBACK] Ollama activado como respaldo local.")
                    # Activar micro local (Vosk → cerebro dual → edge-tts) para poder hablarle
                    if self._offline_pipeline:
                        try:
                            self._offline_pipeline.start()
                            self.ui.write_log("SYS: 🎤 Micro local activo. Hablame cuando quieras.")
                        except Exception as _ve:
                            print(f"[FALLBACK] Voice pipeline start: {_ve}")
                    self._announce(
                        "Modo sin conexión activado. Estoy usando mi respaldo local. "
                        "Puedes hablarme o escribirme por texto."
                    )
                else:
                    print("[FALLBACK] Ollama no disponible. Reintentando Gemini...")
                    if not getattr(self, "_backoff_warned", False):
                        self._backoff_warned = True
                        self.ui.write_log(
                            "SYS: ⚠️ Gemini caído por cuota/política. Ollama no disponible.\n"
                            "SYS: Reintentando con espera progresiva (hasta 90s)."
                        )
                    consecutive_fails = 3  # lower fails to avoid permanent loop
            else:
                # Streak limpio: resetear el aviso para la próxima racha
                if getattr(self, "_backoff_warned", False):
                    self._backoff_warned = False

            # ── Desactivar fallback si Gemini se reconectó ────────────────
            if consecutive_fails == 0 and self._fallback_mode:
                self._fallback_mode = False
                if self._offline_pipeline:
                    try:
                        self._offline_pipeline.stop()
                    except Exception:
                        pass
                self.ui.write_log("SYS: ✅ Gemini reconectado. Modo normal restaurado.")
                print("[FALLBACK] Gemini recuperado. Modo normal.")
                self._announce("Gemini reconectado. Modo normal restaurado.")

            import random as _rnd
            jitter = _rnd.uniform(0, reconnect_delay * 0.25)
            total  = reconnect_delay + jitter
            print(f"[ERIS] 🔄 Reconectando en {total:.1f}s...")
            await asyncio.sleep(total)

def main():
    # ── Handle context menu actions ──────────────────────────────────────────
    if "--eris-action" in sys.argv:
        try:
            idx = sys.argv.index("--eris-action")
            action = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else ""
            path = ""
            if "--eris-path" in sys.argv:
                pidx = sys.argv.index("--eris-path")
                path = sys.argv[pidx + 1] if pidx + 1 < len(sys.argv) else ""
            if action:
                from actions.context_menu_handler import handle_action
                result = handle_action(action, path)
                print(result)
        except Exception as e:
            print(f"[ERIS] Error en accion contextual: {e}")
        sys.exit(0)

    # ── Single Instance Lock ──────────────────────────────────────────────────
    import ctypes
    global _single_instance_mutex
    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _single_instance_mutex = _kernel32.CreateMutexW(None, False, "ERIS_AI_SINGLE_INSTANCE_MUTEX_v2")
    if ctypes.get_last_error() == 183: # ERROR_ALREADY_EXISTS
        print("[ERIS] Ya hay una instancia en ejecución. Cerrando.")
        sys.exit(0)

    # ── License check ─────────────────────────────────────────────────────────
    # ──────────────────────────────────────────────────────────────────────────

    # Load timezone from config
    load_tz(API_CONFIG_PATH)

    def _ensure_both_api_keys():
        cfg = {}
        if API_CONFIG_PATH.exists():
            try:
                cfg = json.loads(API_CONFIG_PATH.read_text(encoding="utf-8"))
            except Exception:
                pass
        
        gemini = cfg.get("gemini_api_key", "").strip()
        openrouter = cfg.get("openrouter_api_key", "").strip()

        from memory.memory_manager import load_memory, save_memory

        # Check if name is already set in memory
        mem = load_memory()
        existing_name = mem.get("identity", {}).get("name", {}).get("value", "")

        # openrouter es OPCIONAL (solo fallback de agentes): no debe bloquear el arranque
        if gemini and existing_name:
            return
            
        from PyQt6.QtWidgets import QApplication, QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
        from PyQt6.QtCore import Qt
        
        # We need an app instance before dialogs
        app = QApplication.instance() or QApplication(sys.argv)
        
        dialog = QDialog()
        dialog.setWindowTitle("Configuración Inicial de ERIS")
        dialog.resize(450, 320)
        dialog.setWindowFlags(dialog.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        layout = QVBoxLayout(dialog)
        
        lbl_info = QLabel("¡Bienvenido a ERIS!\n\nPor favor, ingresa tus API keys y tu nombre para continuar.\nEstos datos se guardarán localmente y de forma segura.")
        lbl_info.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(lbl_info)
        
        lbl_name = QLabel("¿Cómo quieres que te llame?")
        layout.addWidget(lbl_name)
        inp_name = QLineEdit()
        inp_name.setText(existing_name)
        layout.addWidget(inp_name)
        
        lbl_gemini = QLabel("Gemini API Key:")
        layout.addWidget(lbl_gemini)
        inp_gemini = QLineEdit()
        inp_gemini.setText(gemini)
        inp_gemini.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(inp_gemini)
        
        lbl_openrouter = QLabel("OpenRouter API Key:")
        layout.addWidget(lbl_openrouter)
        inp_openrouter = QLineEdit()
        inp_openrouter.setText(openrouter)
        inp_openrouter.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(inp_openrouter)
        
        btn_save = QPushButton("Guardar y Continuar")
        btn_save.setStyleSheet("background-color: #0078D7; color: white; font-weight: bold; padding: 8px; border-radius: 4px;")
        layout.addWidget(btn_save)
        
        def on_save():
            g = inp_gemini.text().strip()
            o = inp_openrouter.text().strip()
            n = inp_name.text().strip()
            if not g or not o:
                QMessageBox.warning(dialog, "Error", "Las claves de API son obligatorias.")
                return
            if not n:
                QMessageBox.warning(dialog, "Error", "Por favor, dime cómo quieres que te llame.")
                return
                
            cfg["gemini_api_key"] = g
            cfg["openrouter_api_key"] = o
            API_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            API_CONFIG_PATH.write_text(json.dumps(cfg, indent=4), encoding="utf-8")
            
            # Save name to long term memory
            memory = load_memory()
            if "identity" not in memory: memory["identity"] = {}
            if "name" not in memory["identity"]: memory["identity"]["name"] = {}
            memory["identity"]["name"]["value"] = n
            save_memory(memory)
            
            dialog.accept()
            
        btn_save.clicked.connect(on_save)
        
        result = dialog.exec()
        if result != QDialog.DialogCode.Accepted:
            sys.exit(0)

    _ensure_both_api_keys()

    ui = ErisUI("face.png")

    # --- UI COSMETICS PATCH ---
    try:
        if hasattr(ui, "_win"):
            # Aumentar transparencia (Glassmorphism)
            ui._win.setWindowOpacity(0.85)
            # Reemplazar textos "Beta" y "Gratuito"
            from PyQt6.QtWidgets import QLabel
            for label in ui._win.findChildren(QLabel):
                text_lower = label.text().lower()
                if "beta" in text_lower or "gratuita" in text_lower or "gratuito" in text_lower or "premium" in text_lower:
                    try:
                        # Ocultar el contenedor completo del banner (incluye el botón PRO)
                        label.parentWidget().hide()
                    except:
                        label.hide()

            # 2. Add keyboard shortcut & Global Hotkey (INS / Insert key) to wake up ERIS
            from PyQt6.QtGui import QKeySequence, QShortcut
            from PyQt6.QtCore import Qt, QTimer

            def on_shortcut_triggered():
                # Despertar a ERIS SIN abrir la ventana ni robar foco,
                # para no interrumpir lo que el usuario está haciendo
                try:
                    if getattr(ui, "muted", False):
                        ui.muted = False
                    _eris_now = globals().get("_current_eris")
                    if _eris_now is not None:
                        _eris_now._open_wake_gate()
                    else:
                        try:
                            ui.set_state("LISTENING")
                        except Exception:
                            pass
                    ui.write_log("SYS: 🎯 ERIS activa. Decime 'Eris, ...'.")
                except Exception:
                    pass

            # A. PyQt Window Shortcut (for local window events)
            local_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Insert), ui._win)
            local_shortcut.activated.connect(on_shortcut_triggered)

            # B. Win32 Native Global Hotkey Hook (for background capture)
            def setup_global_hotkey():
                import threading
                import ctypes
                import ctypes.wintypes

                def hotkey_thread():
                    user32 = ctypes.windll.user32
                    # MOD_NOREPEAT = 0x4000
                    # VK_INSERT = 0x2D
                    try:
                        if not user32.RegisterHotKey(None, 99, 0x0000, 0x2D):
                            print("[HOTKEY] Error registering global Insert hotkey.")
                            return
                    except Exception as e:
                        print(f"[HOTKEY] Exception registering global hotkey: {e}")
                        return

                    try:
                        msg = ctypes.wintypes.MSG()
                        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
                            if msg.message == 0x0312: # WM_HOTKEY
                                if msg.wParam == 99:
                                    # Thread-safely trigger UI callback inside PyQt event loop
                                    QTimer.singleShot(0, on_shortcut_triggered)
                            user32.TranslateMessage(ctypes.byref(msg))
                            user32.DispatchMessageW(ctypes.byref(msg))
                    finally:
                        user32.UnregisterHotKey(None, 99)

                threading.Thread(target=hotkey_thread, daemon=True).start()

            setup_global_hotkey()
            print("[PATCH] Avengers: Age of Ultron golden aesthetics & Insert global hotkey loaded successfully!")

    except Exception as e:
        print(f"[PATCH] Cosmetics & Shortcut patch failed: {e}")

    def runner():
        ui.wait_for_api_key()
        eris = ErisLive(ui)
        globals()["_current_eris"] = eris
        try:
            ui._orb_wake_callback = eris._open_wake_gate
        except Exception:
            pass
        try:
            asyncio.run(eris.run())
        except KeyboardInterrupt:
            print("\n🔴 Apagando...")

    threading.Thread(target=runner, daemon=True).start()
    ui.root.mainloop()

if __name__ == "__main__":
    main()
