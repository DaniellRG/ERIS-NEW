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
    CHUNK_SIZE, PLAY_CHUNK_SIZE, resolve_device, get_api_key,
    ERIS_VOICES, get_eris_voice
)
import core.audio_config as _audio_cfg


from core.prompt_loader import load_system_prompt

_CTRL_RE = re.compile(r"<ctrl\d+>", re.IGNORECASE)

# ── Activación por nombre: ERIS solo responde cuando escucha "Eris, ..." ──
_GATE_WAKE_PHRASES = ("eris", "eres")          # palabras que abren el gate
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

def _has_wake_word(text: str) -> bool:
    """Detecta la palabra de activación como palabra completa (no subcadena)."""
    padded = " {} ".format(text.lower())
    return any(" {} ".format(w) in padded for w in _GATE_WAKE_PHRASES)

def _clean_transcript(text: str) -> str:    
    text = _CTRL_RE.sub("", text)
    text = re.sub(r"[\x00-\x08\x0b-\x1f]", "", text)
    return text.strip()

def _run_self_improvement(user_input: str, response: str, context: dict = None):
    """Run self-improvement cycle in background thread."""
    try:
        from core.self_improvement import FeedbackLoop
        _loop = FeedbackLoop()
        _loop.run_cycle(user_input, response, context)
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
        self._online_logged = False             # para no spamear "ERIS en línea" en cada reconexión
        try:
            from memory.config_manager import BASE_DIR as _BD
            _wake_cfg_path = _BD / "config" / "api_keys.json"
            if _wake_cfg_path.exists():
                _wc = json.loads(_wake_cfg_path.read_text(encoding="utf-8"))
                self._wake_mode = bool(_wc.get("wake_word_mode", True))
        except Exception:
            pass
        # Iniciar carga o descarga de Vosk en segundo plano para no congelar la UI
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

        # Mobile companion server (WebSocket + chat web app)
        if _mobile_start:
            try:
                _mobile_url = _mobile_start(port=8765, inject_callback=self._on_text_command)
                print(f"[MAIN] 📱 Compañero mobile: {_mobile_url}")
                print(f"[MAIN] 📱 Abrí esa URL en el navegador de tu celular en la misma red WiFi")
                self.ui.write_log(f"SYS: 📱 Compañero mobile: {_mobile_url}")
            except Exception as _me:
                print(f"[MAIN] Error iniciando servidor mobile: {_me}")

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

        # Fire phrase triggers in background (only for text-input path)
        self._last_text_trigger = text
        threading.Thread(target=self._fire_phrase_triggers, args=(text,), daemon=True).start()
        # DB: log user message
        if convo_log:
            threading.Thread(target=lambda: convo_log(self._session_id, "user", text), daemon=True).start()
        # Emotional reaction to user interaction
        if react_to_user_interaction:
            threading.Thread(target=react_to_user_interaction, daemon=True).start()
        # Emotional growth - each interaction deepens the bond
        if _eg_on_user_msg:
            threading.Thread(target=lambda: _eg_on_user_msg(None, text), daemon=True).start()

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
                await self.session.send_client_content(
                    turns={"parts": [{"text": f"[RESULTADO AUDIO '{p.name}']\n{result}"}]},
                    turn_complete=True
                )

        except Exception as e:
            traceback.print_exc()
            self.ui.write_log(f"❌ Error procesando audio: {e}")
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
            self.session.send_client_content(
                turns={"parts": [{"text": text}]},
                turn_complete=True
            ),
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
                pcm = asyncio.run(synthesize(text, backend="edge"))
                if pcm and len(pcm) > 0:
                    audio = _np.frombuffer(pcm, dtype=_np.int16)
                    _sd.play(audio, 24000)
                    _sd.wait()
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
        """Modo proactivo: aprende y sugiere SIN interrumpir."""
        import random as _rnd
        while True:
            time.sleep(60)
            idle_seconds = time.time() - self._last_user_interaction
            if idle_seconds > 300 and self._loop and self.session:
                try:
                    from core.idle_learning_loop import should_learn, run_idle_learning
                    if should_learn(idle_seconds):
                        summary = run_idle_learning()
                        self.ui.write_log("[IDLE_LEARN] {}".format(summary))
                except Exception as _ile:
                    self.ui.write_log("[IDLE_LEARN] Error: {}".format(str(_ile)[:80]))

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

        # ── Inject real memory context ──
        memory_context = ""
        try:
            from actions.eris_db import memory_all, episodic_recent
            mems = memory_all(5)
            if mems:
                memory_context += "[MEMORIAS]\n"
                for m in mems[:4]:
                    memory_context += f"- {m['key']}: {str(m['value'])[:120]}\n"
            eps = episodic_recent(3)
            if eps:
                memory_context += "\n[EVENTOS RECIENTES]\n"
                for e in eps[:3]:
                    memory_context += f"- {e['event'][:120]}\n"
        except Exception:
            pass
        
        if memory_context:
            sys_prompt = sys_prompt + "\n\n" + memory_context

        # ── Inject RAG knowledge context ──
        try:
            from core.rag_pipeline import query_documents, stats
            _rag_stats = stats()
            if _rag_stats.get("documents", 0) > 0:
                _rag_results = query_documents(f"Conocimiento general sobre {', '.join(memory.keys()) if isinstance(memory, dict) else 'temas principales'}", top_k=4)
                if _rag_results:
                    rag_context = "\n[CONOCIMIENTO INDEXADO]\n"
                    for r in _rag_results:
                        rag_context += f"- {r['filename']}: {r['text'][:200]}\n"
                    sys_prompt += rag_context
        except Exception:
            pass

        # Get time context (from worldtimeapi.org or system fallback)
        time_ctx = get_time_context()

        parts = [time_ctx]
        if mem_str:
            parts.append(mem_str)
        parts.append(sys_prompt)

        # ── Inject emotional state & personality into prompt ──
        try:
            from actions.emotional_growth import _load as _eg_load, get_prompt_injection
            from core.personality_engine import get_tone_for_response
            _eg_state = _eg_load()
            _injection = get_prompt_injection(_eg_state)
            _tone = get_tone_for_response()
            parts.append(f"[PERSONALIDAD] {_tone}")
            parts.append(f"[EMOCION] {_injection}")
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

        system_text = "\n".join(parts)
        MAX_SYSTEM_CHARS = 32000
        if len(system_text) > MAX_SYSTEM_CHARS:
            system_text = system_text[:MAX_SYSTEM_CHARS] + "\n[CONTEXTO TRUNCADO]"

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
        return await self._tool_dispatcher.execute(fc)

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
                        # Multiple wake phrases
                        wake_phrases = ["eris", "despierta", "hola eris", "hey eris", "eres", "oye eris", "sal", "estas ahi", "estas hay"]
                        if any(phrase in text for phrase in wake_phrases):
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

            # Apply mic gain to boost low-level microphones
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
                self.ui.set_audio_level(min(1.0, rms * 18))
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
            mic_device_idx = None
            _dev_name = "HAYLOU"
            try:
                from memory.config_manager import BASE_DIR
                api_cfg_path = BASE_DIR / "config" / "api_keys.json"
                if api_cfg_path.exists():
                    c = json.loads(api_cfg_path.read_text(encoding="utf-8"))
                    d = c.get("mic_device", "")
                    if d != "":
                        mic_device_idx = int(d)
                    _dev_name = c.get("mic_device_name", "HAYLOU")
            except Exception:
                pass
            # Fallback: search by name if numeric index doesn't point to a valid input device
            if mic_device_idx is not None:
                try:
                    _d = sd.query_devices(mic_device_idx)
                    if _d["max_input_channels"] == 0:
                        mic_device_idx = None  # not an input device, fall back
                except Exception:
                    mic_device_idx = None
            if mic_device_idx is None:
                mic_device_idx = resolve_device(_dev_name, "input")

            _mic_kw = dict(
                samplerate=SEND_SAMPLE_RATE,
                channels=CHANNELS,
                dtype="int16",
                blocksize=CHUNK_SIZE,
                callback=callback,
            )
            try:
                mic_stream = sd.InputStream(device=mic_device_idx, **_mic_kw)
            except Exception:
                print(f"[ERIS] ⚠️ Fallback: using default mic device")
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
                                    if self._first_transcript_time:
                                        now = time.time()
                                        print(f"[TIMING] ✅ First response chunk: +{now - self._first_transcript_time:.1f}s | text: {txt}")
                                out_buf.append(txt)
                                self.ui.stream_eris_chunk(txt)
                                # Broadcast to mobile clients
                                if _mobile_broadcast:
                                    _mobile_broadcast(txt)

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
                            # Activación por nombre: la conversación queda abierta
                            # (no repetir "Eris") hasta que el usuario la cierre con
                            # una frase de cierre o por inactividad
                            if self._wake_mode:
                                self._wake_last_activity = time.time()
                                if self._is_end_conversation(full_in):
                                    self._close_wake_gate()
                            # ── Self-improvement cycle (async, non-blocking) ──
                            try:
                                full_out = " ".join(out_buf).strip()
                                if full_in and full_out:
                                    _si_context = {"session_id": getattr(self, '_session_id', '')}
                                    threading.Thread(
                                        target=_run_self_improvement,
                                        args=(full_in, full_out, _si_context),
                                        daemon=True
                                    ).start()
                            except Exception:
                                pass
                            in_buf = []
                            out_buf = []
                            _first_chunk = True

                    if response.tool_call:
                        self.ui.clear_eris_response()
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
            _win_out = WinAudioOutput(channels=CHANNELS, samplerate=RECEIVE_SAMPLE_RATE, bits_per_sample=16)
            if _win_out.open():
                _use_win_audio = True
                print("[ERIS] 🎧 Usando WinAudioOutput (Windows Multimedia API)")
            else:
                _win_out = None
        except Exception as _we:
            print(f"[ERIS] ⚠️ WinAudioOutput no disponible: {_we}")
            _win_out = None

        # Fallback: sounddevice
        if not _use_win_audio:
            speaker_device_idx = None
            _dev_name = "HAYLOU"
            try:
                from memory.config_manager import BASE_DIR
                api_cfg_path = BASE_DIR / "config" / "api_keys.json"
                if api_cfg_path.exists():
                    c = json.loads(api_cfg_path.read_text(encoding="utf-8"))
                    d = c.get("speaker_device", "")
                    if d != "":
                        speaker_device_idx = int(d)
                    _dev_name = c.get("speaker_device_name", "HAYLOU")
            except Exception:
                pass
            if speaker_device_idx is not None:
                try:
                    _d = sd.query_devices(speaker_device_idx)
                    if _d["max_output_channels"] == 0:
                        speaker_device_idx = None
                except Exception:
                    speaker_device_idx = None
            if speaker_device_idx is None:
                speaker_device_idx = resolve_device(_dev_name, "output")
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

        try:
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
                    consecutive_fails = 3  # lower fails to avoid permanent loop

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
    _single_instance_mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "ERIS_AI_SINGLE_INSTANCE_MUTEX_v2")
    if ctypes.windll.kernel32.GetLastError() == 183: # ERROR_ALREADY_EXISTS
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
        
        if gemini and openrouter and existing_name:
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
