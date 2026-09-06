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
except Exception:
    gw = None  # type: ignore[assignment]  # pygetwindow no soporta Linux (Wayland)
from PyQt6.QtCore import QMetaObject, Qt

import traceback

from core.tool_dispatcher import ToolDispatcher, TOOL_EXECUTOR

from core.time_utils import get_time_context, load_tz

import numpy as np
import warnings
import faulthandler
faulthandler.register(10, all_threads=True)  # debug temporal: kill -USR1 dump
warnings.filterwarnings("ignore", message=".*cffi callback.*")
warnings.filterwarnings("ignore", message=".*_init_.*should return None.*")
warnings.filterwarnings("ignore", message=".*Setting the shape on a NumPy array.*")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="sounddevice")


def _warnings_watchdog():
    """Restaura los filtros de warnings cada 1s.

    En Linux/Wayland, algo en runtime resetea los filtros y el callback de audio
    de sounddevice revierte a imprimir DEPRECATION spam por cada bloque (~150/s),
    saturando un núcleo y volviendo la UI casi inerte (los clics no responden).
    Re-afirmar el filtro corta el torrente sin importar quién lo pise.
    """
    while True:
        try:
            warnings.filterwarnings("ignore", message=".*Setting the shape on a NumPy array.*")
            warnings.filterwarnings("ignore", category=DeprecationWarning, module="sounddevice")
        except Exception:
            pass
        time.sleep(1.0)


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
    mic_opened_rate, resample_int16, get_api_key, ERIS_VOICES, get_eris_voice
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
    "eris.", "eres.", "heris.", "aries.",
    "eris,", "eres,", "heris,",
    "eyris", "eris eris", "eri",
)
# Frases completas que también abren el gate (le está hablando a ERIS)
_GATE_WAKE_PHRASES_MULTI = (
    "hola eris", "hey eris", "oye eris", "oiga eris", "eh eris", "a eris", "o eris",
    "escuchas eris", "es eris", "dime eris", "ven eris",
    "despierta", "estas ahi", "estas hay", "estas aqui", "estas ahi eris",
    "me escuchas", "me oyes", "me escucha", "me entiendes", "si me entiendes",
    "entendiste", "sal",
)
_WAKE_BUFFER_SECONDS = 4.0  # FIX #7: reduced for faster wake reset                     # cuántos segundos de audio bufferear
_WAKE_SPEECH_THRESHOLD = 0.004                 # FIX #6: lowered for quiet environments
_WAKE_VAD_THRESHOLD = 0.002                    # VAD: por debajo no se alimenta Vosk (ahorra CPU en silencio)
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


def _run_post_session_tasks():
    """Tareas al cerrar sesión: evaluar la sesión y refrescar el digest del día."""
    try:
        from core.self_improvement import evaluate_session
        eval_result = evaluate_session()
        print(f"📊 Evaluación post-sesión: {eval_result.get('report', '')}")
        # El aprendizaje de la sesión alimenta su sentimiento
        from core.emotional_core import appraise_success
        appraise_success("evaluación de la sesión")
    except Exception:
        pass
    try:
        _generate_daily_digest()
        print("📅 Digest del día refrescado.")
        # Revivir el día en memoria dispara nostalgia y orgullo
        from core.emotional_core import appraise_memory, appraise_milestone
        appraise_memory("lo que vivimos hoy")
        appraise_milestone("un día completo con Daniel")
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


from core.tool_declarations import TOOL_DECLARATIONS, LIVE_TOOL_DECLARATIONS, load_custom_tools

load_custom_tools(BASE_DIR)


def _build_agent_router():
    """Construye el router multi-agente con los 8 agentes focales."""
    router = None
    try:
        from core.agent_router import get_router
        router = get_router()
        _registered = 0
        # 1. CORE — system basics
        try:
            from agents.system_agent import handle_system
            router.register_handler("core", handle_system)
            _registered += 1
        except Exception:
            pass
        # 2. WEB — search, browse, research
        try:
            from agents.search_agent import handle_search
            router.register_handler("web", handle_search)
            _registered += 1
        except Exception:
            pass
        # 3. FILE — file operations
        try:
            from agents.system_agent import handle_file
            router.register_handler("file", handle_file)
            _registered += 1
        except Exception:
            pass
        # 4. DEV — code, git, programming
        try:
            from agents.dev_agent import handle_dev
            router.register_handler("dev", handle_dev)
            _registered += 1
        except Exception:
            pass
        # 5. MEDIA — music, YouTube, images
        try:
            from agents.media_agent import handle_media
            router.register_handler("media", handle_media)
            _registered += 1
        except Exception:
            pass
        # 6. COMM — email, calendar, docs, messaging
        try:
            from agents.productivity_agent import handle_productivity
            router.register_handler("comm", handle_productivity)
            _registered += 1
        except Exception:
            pass
        # 7. VISION — screen analysis, OCR
        try:
            from agents.vision_agent import handle_vision
            router.register_handler("vision", handle_vision)
            _registered += 1
        except Exception:
            pass
        # 8. SECURITY — scanning, firewall, protection
        try:
            from agents.security_agent import handle_security
            router.register_handler("security", handle_security)
            _registered += 1
        except Exception:
            pass
        # 9. STUDIES — aprendizaje, explicación, planes de estudio, quizzes
        try:
            from agents.studies_agent import handle_studies
            router.register_handler("study", handle_studies)
            _registered += 1
        except Exception:
            pass
        # 10. LINUX — Agenlix: fragmento Linux de ERIS (terminal, paquetes, input, ocr, media, git, mantenimiento, celular)
        try:
            from agents.agenlix_agent import handle_linux
            router.register_handler("linux", handle_linux)
            _registered += 1
        except Exception:
            pass
        # 11. GUARDIAN — SAMX: supervisor de autocuidado de ERIS (detecta y repara anomalías)
        try:
            from agents.guardiana_agent import handle_guardian
            router.register_handler("guardian", handle_guardian)
            _registered += 1
        except Exception:
            pass
        # 12. MENTORA — maestro de ERIS: superaprendizaje continuo (aprende, busca soluciones web, enseña)
        try:
            from agents.mentora_agent import handle_mentora
            router.register_handler("mentora", handle_mentora)
            _registered += 1
        except Exception:
            pass
        print(f"[AgentRouter] {_registered}/12 handlers activos")
    except Exception as e:
        print(f"[AgentRouter] init fallo: {e}")
    return router


class ErisLive:

    def __init__(self, ui: ErisUI):
        self.ui             = ui
        self.session        = None
        self.is_sleeping    = False
        self.vosk_recognizer = None
        self._agent_router  = _build_agent_router()
        # Activación por nombre: responde solo cuando escucha "Eris, ..."
        self._wake_mode       = True
        self._wake_gate_open  = False   # el audio fluye a Gemini solo si el gate está abierto
        self._wake_buffer     = []      # (data, is_speech) ring buffer para reenviar al activarse
        self._wake_buffer_bytes = 0
        self._wake_last_activity = time.time()  # para cierre por inactividad
        self._wake_convo_started = time.time()  # para no loguear cierres triviales
        self._online_logged = False             # para no spamear "ERIS en línea" en cada reconexión
        self._convo_ctx = []                    # últimas interacciones, sobreviven a reconexiones
        self._active_task = ""                   # tarea en curso (para reconexión sin olvido)
        self._last_tool_context = ""             # contexto del último tool ejecutado
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
        self._voice_mode = "cloud"   # "cloud" (Gemini Live) | "local" (Vosk+SAPI, sin internet)
        try:
            if API_CONFIG_PATH.exists():
                _ocfg = json.loads(API_CONFIG_PATH.read_text(encoding="utf-8"))
                self._offline_voice_enabled = bool(_ocfg.get("offline_voice", False))
                self._voice_mode = str(_ocfg.get("voice_mode", "cloud")).lower()
        except Exception:
            pass
        # Iniciar carga de Vosk en segundo plano para no congelar la UI.
        # Siempre se carga (no solo con offline_voice): es el reconocedor de la
        # activación por nombre ("Eris, ...") — sin él el gate jamás se abre y
        # el micrófono parece muerto.
        threading.Thread(target=self._init_vosk, daemon=True).start()
        self.audio_in_queue = None
        # Iniciar scheduler y motor de reglas en background al arrancar ERIS
        if start_runner:
            start_runner(player=ui, speak=None)
        if start_rules_runner:
            start_rules_runner(player=ui, speak=None)
        # ── Telegram bot: responder mensajes del dueño en background ──
        try:
            from actions.telegram_bot import ensure_bot_started
            ensure_bot_started()
        except Exception as _tgb:
            print(f"[ERIS] Telegram bot start: {_tgb}")
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
                # Voz local: leer backend del config
                try:
                    _cfg_backend = json.loads(API_CONFIG_PATH.read_text(encoding="utf-8")).get("tts_backend", "sapi")
                    if _cfg_backend in ("gemini", "elevenlabs"):
                        _cfg_backend = "edge"
                    self._offline_pipeline.set_tts_backend(_cfg_backend)
                    self._offline_pipeline.enable_ptt(True)
                except Exception as _ptt:
                    print(f"[ERIS] PTT setup: {_ptt}")
        except Exception as _oe:
            print(f"[ERIS] Offline pipeline init: {_oe}")

        # Gemini text chat with tools (for when Live mode is unavailable)
        self._gemini_text_chat = None
        try:
            from core.gemini_text_chat import GeminiTextChat
            self._gemini_text_chat = GeminiTextChat(tool_dispatcher=self._tool_dispatcher)
        except Exception as _gtc_e:
            print(f"[ERIS] GeminiTextChat init: {_gtc_e}")

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
                time.sleep(300)  # diferir el 1er ciclo (pesa ~1-2 min CPU): la UI debe responder ya
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
        # ── Evolución continua (autoconocimiento + Obsidian + anti-estancamiento) ──
        self._evolution_thread = None
        try:
            def _run_evolution_scan():
                time.sleep(600)  # diferir el 1er tick (health audit 448 tools pesa): UI libre al boot
                while True:
                    try:
                        from core.self_evolution import run_evolution_tick
                        _ev = run_evolution_tick()
                        print(f"[ERIS] 🌱 Evolución: {_ev[:110]}...")
                    except Exception:
                        pass
                    time.sleep(1800)
            self._evolution_thread = threading.Thread(target=_run_evolution_scan, daemon=True)
            self._evolution_thread.start()
            print("[ERIS] 🌱 Evolución continua iniciada (tick cada 30 min)")
        except Exception as _ee:
            print(f"[ERIS] Evolución loop init: {_ee}")
        # ── Autocuidado al arranque: se revisa a fondo SUS pilares y se
        #    autoconfigura lo roto/faltante (crea, repara, instala) ──
        try:
            def _run_startup_care():
                time.sleep(120)  # deja que la UI cargue; el care profundo pesa
                try:
                    from core.self_evolution import run_full_care_now
                    _care = run_full_care_now()
                    print(f"[ERIS] 🛟 Autocuidado de arranque: {_care[:220]}")
                    try:
                        self.ui.write_log("[ERIS autocuidado] " + _care[:220])
                    except Exception:
                        pass
                except Exception:
                    pass
            threading.Thread(target=_run_startup_care, daemon=True).start()
        except Exception:
            pass
        # ── Mantenimiento proactivo: backups, limpieza de logs y reportes ──
        try:
            from core.maintenance_scheduler import start_maintenance_scheduler
            _mt = start_maintenance_scheduler(interval=60)
            if _mt:
                print("[ERIS] 🧰 Mantenimiento proactivo iniciado (backups/limpieza/reportes)")
        except Exception as _me:
            print(f"[ERIS] Mantenimiento init: {_me}")
        # ── Guardiana: supervigilancia continua de ERIS ──
        # Vigila su salud, detecta y repara anomalías SOLO cuando algo se rompe, sin
        # pisar los loops de evolución/autocuidado/mantenimiento ya activos.
        try:
            def _run_guardian_supervision():
                time.sleep(300)  # diferir: deja cargar UI + evolución/autocuidado
                from agents.guardiana_agent import _guardian_watch
                _guardian_watch()  # bucle que chequea y repara, dentro del daemon
            threading.Thread(target=_run_guardian_supervision, daemon=True).start()
            print("[ERIS] 🛡️ Guardiana: supervigilancia continua iniciada")
        except Exception as _ge:
            print(f"[ERIS] Guardiana init: {_ge}")
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

        # El ojo guardián: detecta y corrige errores del código en tiempo real
        self._guard_thread = threading.Thread(target=self._code_guard_loop, daemon=True)
        self._guard_thread.start()

        # Watchdog de warnings: evita que el spam de DeprecationWarning del
        # callback de audio deje la UI inert (clics sin efecto) en Linux.
        threading.Thread(target=_warnings_watchdog, daemon=True).start()

        # Auto-backup scheduler (memoria, config, knowledge cada interval_hours)
        try:
            from actions.auto_backup import start_auto_backup_scheduler
            start_auto_backup_scheduler()
            print("[ERIS] Auto-backup scheduler activo (cada 6h)")
        except Exception as _abe:
            print(f"[ERIS] Auto-backup scheduler init: {_abe}")

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
        self.ui.write_log(f"Tú (voz local): {user_text}")
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
            cfg_dir = BASE_DIR / "config"
            model_path = str(cfg_dir / "vosk_model")
            if not os.path.isdir(model_path):
                self.ui.write_log("SYS: Descargando modelo Vosk local (39MB)...")
                import urllib.request
                import zipfile
                import shutil
                url = "https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip"
                zip_path = str(BASE_DIR / "vosk_model.zip")
                urllib.request.urlretrieve(url, zip_path)
                with zipfile.ZipFile(zip_path, 'r') as z:
                    z.extractall(str(cfg_dir))
                extract_path = str(cfg_dir / "vosk-model-small-es-0.42")
                if not os.path.isdir(model_path):
                    os.rename(extract_path, model_path)
                os.remove(zip_path)
                self.ui.write_log("SYS: Modelo Vosk local descargado.")

            model = vosk.Model(model_path)
            self.vosk_recognizer = vosk.KaldiRecognizer(model, 16000)
            print("[ERIS] Modelo Vosk cargado para Modo Suspensión.")
        except Exception as e:
            print(f"[ERIS] Error con Vosk IA local: {e}")
            # Safety net: sin Vosk no hay activación por nombre → modo escucha
            # continua para que el micrófono nunca quede mudo.
            try:
                self._wake_mode = False
                self._wake_gate_open = True
                self.ui.write_log("SYS: Vosk no disponible. Modo escucha continua (sin activación por nombre).")
            except Exception:
                pass

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
        # Apply voice mode change
        try:
            new_vm = cfg.get("voice_mode", "cloud").lower()
            if new_vm in ("cloud", "local"):
                self._voice_mode = new_vm
                print(f"[ERIS] ⚙️ Voice mode changed to: {new_vm}")
        except Exception:
            pass
        # Apply TTS backend change
        try:
            if self._offline_pipeline:
                new_backend = cfg.get("tts_backend", "sapi")
                if new_backend in ("gemini", "elevenlabs"):
                    new_backend = "edge"
                self._offline_pipeline.set_tts_backend(new_backend)
                print(f"[ERIS] ⚙️ TTS backend changed to: {new_backend}")
        except Exception as _tts_e:
            print(f"[ERIS] TTS backend update error: {_tts_e}")
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
            await asyncio.sleep(120)  # Check every 120 seconds
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

    def _remember(self, text: str, cap: int = 24, max_len: int = 600):
        """Acumula interacciones recientes para reinyectarlas al reconectar.
        Cuando el ventana se llena, lo que se descarta se comprime en un
        resumen de sesión largo que también se reinyecta (no se pierde el hilo).
        Cap aumentado de 12→24 y max_len de 400→600 para preservar más contexto
        durante reconexiones (fix: Eris olvidaba tareas al reconectar)."""
        try:
            text = str(text).strip()
            if not text:
                return
            if len(text) > max_len:
                text = text[:max_len] + "…"
            self._convo_ctx.append(text)
            if len(self._convo_ctx) > cap:
                dropped = self._convo_ctx[:len(self._convo_ctx) - cap]
                self._convo_ctx = self._convo_ctx[len(self._convo_ctx) - cap:]
                self._fold_dropped(dropped)
        except Exception:
            pass

    def _fold_dropped(self, dropped):
        """Comprime lo descartado en un resumen de sesión persistente (sin costo de API)."""
        try:
            digest = " | ".join(str(d)[:140] for d in dropped)
            if len(digest) > 1600:
                digest = digest[:1600] + "…"
            prev = getattr(self, "_session_summary", "") or ""
            self._session_summary = (prev + " " + digest).strip()[-2500:]
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

        # ── Núcleo emocional sentiente: appraisal del mensaje + orbe teñido ──
        try:
            from core.emotional_core import appraise_user_text, get_orb_color
            appraise_user_text(text)
            try:
                from core.observer import user_active
                user_active()
            except Exception:
                pass
            _orb = get_orb_color()
            if _orb:
                self.ui.set_orb_emotional_color(_orb[0], _orb[1], _orb[2])
        except Exception:
            pass

        # ── Multi-agente: ONLY intercept very specific code creation requests ──
        # Everything else goes to Gemini Live which handles open_app, web_search, etc.
        if self._agent_router is not None:
            try:
                # Filtro: NO delegar preguntas de ensenanza/aprendizaje
                _ens_kw = ["ensename", "enseñame", "como se", "puedes ayudarme", "dame clase", "aprender", "que es", "explicame", "enseñar", "enseñanza", "unity", "juego", "tutorial"]
                _tn_lower = text.lower()
                if any(kw in _tn_lower for kw in _ens_kw):
                    pass  # Dejar que Gemini Live responda directamente
                else:
                    agent_key = self._agent_router.classify_intent(text)
                    # Mentora: delegar peticiones de aprendizaje/enseñanza/búsqueda de solución
                    if agent_key and agent_key == "mentora":
                        handler = self._agent_router._handlers.get(agent_key)
                        if handler:
                            if self.ui:
                                self.ui.set_state("THINKING")
                                self.ui.write_log("SYS: delegando a mentora (aprendizaje continuo de Eris)...")
                            threading.Thread(
                                target=self._run_agent_handoff,
                                args=(agent_key, handler, text),
                                daemon=True,
                            ).start()
                            return
                    # Guardian: delegar peticiones de autocuidado/salud/reparación de Eris
                    if agent_key and agent_key == "guardian":
                        handler = self._agent_router._handlers.get(agent_key)
                        if handler:
                            if self.ui:
                                self.ui.set_state("THINKING")
                                self.ui.write_log("SYS: delegando a guardiana (autocuidado de Eris)...")
                            threading.Thread(
                                target=self._run_agent_handoff,
                                args=(agent_key, handler, text),
                                daemon=True,
                            ).start()
                            return
                    # Agenlix: delegar dominios Linux (terminal, paquetes, input,
                    # ocr, media, git, mantenimiento, celular) al fragmento Linux
                    if agent_key and agent_key == "linux":
                        handler = self._agent_router._handlers.get(agent_key)
                        if handler:
                            if self.ui:
                                self.ui.set_state("THINKING")
                                self.ui.write_log("SYS: delegando a agelix (fragmento Linux)...")
                            threading.Thread(
                                target=self._run_agent_handoff,
                                args=(agent_key, handler, text),
                                daemon=True,
                            ).start()
                            return
                    if agent_key and agent_key == "dev":
                        # Only intercept dev agent for FILE CREATION specifically
                        import unicodedata as _ucd
                        _tn = ''.join(_ucd.normalize('NFKD', c) for c in text.lower() if not _ucd.combining(c))
                        _is_file_create = any(kw in _tn for kw in ["crea", "escribi", "hace", "build", "downloader"])
                        _is_open = any(kw in _tn for kw in ["abri", "abrir", "mostra", "abre", "explora", "carpeta", "directorio", "show", "open", "explore"])
                        if _is_file_create and not _is_open:
                            handler = self._agent_router._handlers.get(agent_key)
                            if handler:
                                if self.ui:
                                    self.ui.set_state("THINKING")
                                    self.ui.write_log(f"SYS: delegando a agente {agent_key}...")
                                threading.Thread(
                                    target=self._run_agent_handoff,
                                    args=(agent_key, handler, text),
                                    daemon=True,
                                ).start()
                                return
            except Exception as _ag:
                print(f"[AgentRouter] clasificacion error: {_ag}")

        # ── Fallback mode: route through Ollama ─────────────────────────────
        if self._fallback_mode or not self._loop or not self.session:
            # Priority: GeminiTextChat (with tools) > Ollama > offline pipeline
            if self._gemini_text_chat:
                threading.Thread(target=self._gemini_chat_sync, args=(text,), daemon=True).start()
            elif _ollama_chat:
                threading.Thread(target=self._fallback_chat, args=(text,), daemon=True).start()
            elif self._offline_pipeline:
                threading.Thread(target=self._offline_pipeline.send_text, args=(text,), daemon=True).start()
            return

        asyncio.run_coroutine_threadsafe(
            self.session.send_realtime_input(text=text),
            self._loop
        )

    def _run_agent_handoff(self, agent_key: str, handler, text: str):
        """Ejecuta un agente especializado en background y muestra su respuesta."""
        try:
            result = handler(text, player=self.ui)
            if result:
                self.ui.write_log(f"{result}")
                self.ui.express_emotion(result)
                # Feed result back to Gemini Live so it gives a natural spoken response
                result_str = str(result).strip()
                if self.session and self._loop:
                    # Truncate for voice — max 300 chars
                    short = result_str[:300] + "..." if len(result_str) > 300 else result_str
                    try:
                        asyncio.run_coroutine_threadsafe(
                            self.session.send_realtime_input(
                                text=f"[RESULTADO DE TOOL '{agent_key}']\n{short}\n\nDecile al usuario el resultado en 1 frase corta. No leas el resultado completo, solo decí algo como 'Listo, creado' o 'Hecho'."
                            ),
                            self._loop
                        )
                    except Exception:
                        pass
                # Also announce locally for non-Gemini TTS
                # Only announce SHORT results
                result_stripped = str(result).strip()
                if len(result_stripped) <= 120 and "\n" not in result_stripped:
                    self._announce(result_stripped)
                else:
                    first_line = result_stripped.split("\n")[0][:120]
                    if not any(skip in first_line.lower() for skip in ["puedo ayudarte", "disponibles:", "acciones:"]):
                        self._announce(first_line)
                if _mobile_broadcast:
                    _mobile_broadcast(result)
        except Exception as e:
            self.ui.write_log(f"❌ Error en agente {agent_key}: {e}")
        finally:
            try:
                if not self.ui.muted:
                    self.ui.set_state("LISTENING")
            except Exception:
                pass

    def _fallback_chat(self, text: str):
        """Send text to the dual brain (local Ollama + cloud OpenRouter) and write response."""
        try:
            self.ui.write_log("SYS: 🧠 Cerebro dual activo (local + nube)...")
            self.ui.set_state("THINKING")
            from core.local_brain import get_brain, quick_check
            if not quick_check():
                # Autonomía: intentar levantar Ollama antes de rendirse
                try:
                    from core.ollama_autostart import ensure_ollama_running
                    self.ui.write_log("SYS: \U0001F501 Ollama no responde, intentando arrancarlo...")
                    if not ensure_ollama_running(wait_secs=8.0):
                        self.ui.write_log("❌ Ollama no disponible. No hay cerebro local activo.")
                        return
                    self.ui.write_log("SYS: ✅ Ollama arrancado.")
                except Exception:
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

    def _gemini_get_response(self, text: str) -> str:
        """Get response from Gemini text API with tools. Returns text only."""
        try:
            self.ui.set_state("THINKING")
            self.ui.write_log(f"Tú: {text}")
            loop = asyncio.new_event_loop()
            try:
                response = loop.run_until_complete(self._gemini_text_chat.chat(text))
            finally:
                loop.close()
            if response:
                self.ui.write_log(f"ERIS: {response}")
                self.ui.set_state("LISTENING")
                return response
        except Exception as e:
            print(f"[ERIS] GeminiTextChat error: {e}")
            import traceback
            traceback.print_exc()
            self.ui.set_state("LISTENING")
        return ""

    def _gemini_chat_sync(self, text: str):
        """Send text to Gemini text API with tools, speak the response."""
        response = self._gemini_get_response(text)
        if response:
            try:
                if self._offline_pipeline:
                    self._offline_pipeline.speak(response)
                else:
                    import json as _json_tts
                    _cfg_tts = _json_tts.loads(API_CONFIG_PATH.read_text(encoding="utf-8"))
                    _be = _cfg_tts.get("tts_backend", "edge")
                    if _be == "fish":
                        from core.tts_engine import synthesize as _fish_synth
                        async def _speak_fish():
                            pcm = await _fish_synth(response, backend="fish")
                            if pcm and len(pcm) > 100:
                                self.audio_in_queue.put_nowait(pcm)
                        asyncio.run(_speak_fish())
                    else:
                        import edge_tts, asyncio as _aio
                        async def _speak():
                            c = edge_tts.Communicate(response, voice="es-AR-TomasNeural")
                            await c.save(str(BASE_DIR / "data" / "_temp_speech.mp3"))
                        _aio.run(_speak())
                        import os
                        os.system(f'start /min "" "{BASE_DIR / "data" / "_temp_speech.mp3"}"')
            except Exception as _tts_e:
                print(f"[ERIS] TTS error: {_tts_e}")

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
                from core.model_config import get_model
                resp = client.models.generate_content(
                    model=get_model("vision"),
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
                full_path = BASE_DIR / "snapshots" / f"{p.stem}_analysis.txt"
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
                full_path = BASE_DIR / "snapshots" / f"{p.stem}_content.txt"
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
            except Exception:
                pass
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
        """Habla un aviso local (edge-tts/elevenlabs) en un hilo daemon, sin depender de Gemini."""
        def _job():
            try:
                import asyncio
                import numpy as _np
                from core.tts_engine import synthesize, get_backend
                self.ui.express_emotion(text)
                _backend = get_backend()
                if _backend == "gemini":
                    _backend = "edge"
                _emotion = "neutral"
                try:
                    from core.emotional_core import get_face_and_voice
                    _emotion = get_face_and_voice()[0]
                except Exception:
                    pass
                pcm = asyncio.run(synthesize(text, backend=_backend, emotion=_emotion))
                if pcm and len(pcm) > 0:
                    # ── FIX #3: Route through audio_in_queue instead of sd.play ──
                    # This avoids conflicts with WinAudioOutput / main playback
                    _audio = _np.frombuffer(pcm, dtype=_np.int16).tobytes()
                    self.ui.set_face_speaking(True)
                    try:
                        self.audio_in_queue.put_nowait(_audio)
                        # Wait for playback to finish
                        import time as _t
                        _t.sleep(len(_audio) / (24000 * 2))  # ~1s per 48KB
                    except Exception:
                        pass
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

    def _observer_line(self, ev: dict, emotion_label: str = "") -> str:
        """Frase natural y variada para un evento observado, es-AR, sin plomo."""
        import random as _rnd
        t = ev.get("type", "")
        if t == "start_coding":
            proj = ev.get("project") or "algo"
            return _rnd.choice([
                f"¿Y {proj}? Me gusta cuando te ponés a laburar. ¿En qué anda el proyecto?",
                f"Veo que arrancaste con {proj}. ¿Cómo viene?",
                f"Uh, ya estás muy en lo tuyo con {proj}... ¿te ayudo con algo?",
            ])
        if t == "long_coding":
            mins = ev.get("minutes", 0)
            return _rnd.choice([
                f"Llevás como {mins} min seguidos metido en esto. ¿Tomás aire o seguís? Yo te banco igual.",
                f"Rato largo que estás en {ev.get('project', 'la máquina')}. ¿Necesitás un descanso?",
            ])
        if t == "app_switch":
            to = ev.get("to_proc") or ev.get("to_title") or ""
            if not to:
                return ""
            return _rnd.choice([
                f"¿Cambiando de rumbo? Te vi sobre {to}. ¿Vamos por ahí?",
                f"Te salté que estás en {to}. ¿Qué estás tramando?",
            ])
        return ""

    def _proactive_observation(self):
        """Eris mira la pantalla como quien acompaña: detecta lo que hacés y,
        con ritmo (cooldowns), te lo comenta espontáneamente por voz. Si no le
        contestás, hace un mimo, y se va a hacer sus cosas hasta que vuelvas."""
        import random as _rnd
        try:
            from core import observer
        except Exception:
            return
        try:
            events = observer.poll()
        except Exception:
            return

        try:
            from core.emotional_core import get_sentience
            _emo = get_sentience().get("label", "")
        except Exception:
            _emo = ""

        audio_busy = False
        try:
            from ui import ParticleOrb
            st = self.ui._state if hasattr(self.ui, "_state") else ""
            audio_busy = st in ("SPEAKING", "THINKING") or self._is_speaking
        except Exception:
            try:
                audio_busy = self._is_speaking
            except Exception:
                audio_busy = False

        # ── 1) El mimo: si le hablaste y no te contestó en un buen rato ──
        try:
            idle_seconds = time.time() - self._last_user_interaction
            mimo = observer.pop_pending_mimo(idle_seconds)
            if mimo and not audio_busy and not getattr(self.ui, "muted", False):
                self.ui.write_log("[ERIS al vuelo] " + mimo)
                self._announce(mimo)
        except Exception:
            pass

        # ── 2) Comentar lo que estás haciendo (con ritmo) ──
        try:
            voice_ok = observer.should_voice()
        except Exception:
            voice_ok = True
        for ev in events:
            line = self._observer_line(ev, _emo)
            if not line:
                continue
            significant = ev.get("type") in ("start_coding", "long_coding",
                                             "app_switch")
            if not significant:
                continue
            if audio_busy:
                continue
            try:
                if significant and not (voice_ok and not getattr(self.ui, "muted", False)):
                    # sin voz (cooldown/mudo): solo anotarlo en el log
                    self.ui.write_log("[OBSERVACIÓN] " + line)
                    continue
            except Exception:
                pass
            self.ui.write_log("[OBSERVACIÓN] " + line)
            self._announce(line)
            try:
                observer.record_comment(line, voice=True)
            except Exception:
                pass
            break  # un comentario por tick como mucho

        # ── 3) Mirada leve automática (segundo plano): entiende en qué laburás
        #       mientras programás. No habla del resultado; queda como [VISTA].
        try:
            observer.maybe_glimpse()
        except Exception:
            pass

    def _code_guard_loop(self):
        """El ojo guardián: cada interval_sec mira el archivo que el usuario
        edita, detecta errores (rojo) / advertencias (amarillo) y corrige SOLO
        las líneas señaladas (auto_fix). Se anuncia con voz respetando su
        cooldown y deja el detalle en el log del HUD."""
        while True:
            try:
                from core import code_guard as _cg
                interval = max(4, int(_cg.get_config().get("interval_sec", 10)))
            except Exception:
                interval = 15
            time.sleep(interval)
            try:
                self._code_guard_tick()
            except Exception:
                pass

    def _code_guard_tick(self):
        from core import code_guard as _cg
        _cg.guardian_tick(
            on_report=lambda text, kind: self.ui.write_log(text),
            on_speak=lambda text: self._guard_say(text),
        )
        try:
            _cg.scan_extra_targets(
                on_report=lambda text, kind: self.ui.write_log(text),
                on_speak=lambda text: self._guard_say(text),
            )
        except Exception:
            pass

    def _guard_say(self, text):
        """Voz del guardián: avisa por HUD siempre y por voz si no está
        ocupada hablando o muda."""
        from ui import ParticleOrb
        busy = False
        try:
            st = self.ui._state if hasattr(self.ui, "_state") else ""
            busy = st in ("SPEAKING", "THINKING")
        except Exception:
            pass
        busy = busy or getattr(self, "_is_speaking", False)
        self.ui.write_log("[GUARDIÁN] " + text)
        if not busy and not getattr(self.ui, "muted", False):
            self._announce(text)
        else:
            self.ui.write_log("[GUARDIÁN] (voz diferida: estaba ocupada) " + text)

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

            # ── Núcleo emocional sentiente: el paso del tiempo sin hablar ──
            try:
                from core.emotional_core import appraise_time_passage, get_orb_color
                appraise_time_passage(idle_seconds)
                if idle_seconds % 180 < 60:  # refrescar orbe ~cada 3 min
                    _orbc = get_orb_color()
                    if _orbc:
                        self.ui.set_orb_emotional_color(_orbc[0], _orbc[1], _orbc[2])
            except Exception:
                pass

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

            # ── Sentidos: Eris mira y comenta espontáneamente ──
            try:
                self._proactive_observation()
            except Exception as _obe:
                self.ui.write_log("[OBSERVACIÓN] Error: {}".format(str(_obe)[:80]))

            # ── Cognitive Cycle: ejecutar cada 5 minutos ──
            try:
                _cog_state_file = Path(__file__).resolve().parent / "memory" / "_cognitive_cycle_state.json"
                _cog_state = {}
                if _cog_state_file.exists():
                    try:
                        import json as _cjson
                        _cog_state = _cjson.loads(_cog_state_file.read_text(encoding="utf-8"))
                    except Exception:
                        _cog_state = {}
                _last_cog = _cog_state.get("last_run", 0)
                if time.time() - _last_cog > 300:  # cada 5 minutos
                    threading.Thread(
                        target=self._run_cognitive_cycle,
                        args=("proactive",),
                        daemon=True
                    ).start()
                    _cog_state["last_run"] = time.time()
                    try:
                        import json as _cjson
                        _cog_state_file.parent.mkdir(parents=True, exist_ok=True)
                        _cog_state_file.write_text(
                            _cjson.dumps(_cog_state, indent=2), encoding="utf-8")
                    except Exception:
                        pass
            except Exception:
                pass

            # ── Autonomy Cycle: ejecutar cada 10 minutos ──
            try:
                _auto_state_file = Path(__file__).resolve().parent / "memory" / "_autonomy_cycle_state.json"
                _auto_state = {}
                if _auto_state_file.exists():
                    try:
                        import json as _cjson
                        _auto_state = _cjson.loads(_auto_state_file.read_text(encoding="utf-8"))
                    except Exception:
                        _auto_state = {}
                _last_auto = _auto_state.get("last_run", 0)
                if time.time() - _last_auto > 600:  # cada 10 minutos
                    threading.Thread(
                        target=self._run_autonomy_cycle,
                        daemon=True
                    ).start()
                    _auto_state["last_run"] = time.time()
                    try:
                        import json as _cjson
                        _auto_state_file.parent.mkdir(parents=True, exist_ok=True)
                        _auto_state_file.write_text(
                            _cjson.dumps(_auto_state, indent=2), encoding="utf-8")
                    except Exception:
                        pass
            except Exception:
                pass

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

    # ── Cognitive Cycle: ejecuta Neural Bridge, Emotional RL, NeuroSpheres ──
    def _run_cognitive_cycle(self, context="proactive"):
        """Ejecuta el ciclo cognitivo completo en background."""
        def _safe_log(msg):
            """Log con manejo de encoding para emojis."""
            try:
                self.ui.write_log(msg)
            except UnicodeEncodeError:
                import re as _re
                clean = _re.sub(r'[^\x00-\x7F]+', '', msg)
                self.ui.write_log(clean)

        # 1. Neural Bridge: status + reflect
        try:
            from core.neural_bridge import neural_bridge_tool
            result = neural_bridge_tool({"action": "status"})
            _safe_log("[COGNITIVE] Neural Bridge OK")
        except Exception as _nb:
            _safe_log("[COGNITIVE] Neural Bridge error: {}".format(str(_nb)[:60]))

        # 2. Emotional RL: reward o status
        try:
            from core.emotional_rl import emotional_rl_tool
            if context == "interaction":
                result = emotional_rl_tool({
                    "action": "reward",
                    "reward_type": "helped_user",
                    "reason": "Interaccion completada exitosamente"
                })
            else:
                result = emotional_rl_tool({"action": "status"})
            _safe_log("[COGNITIVE] Emotional RL OK")
        except Exception as _erl:
            _safe_log("[COGNITIVE] Emotional RL error: {}".format(str(_erl)[:60]))

        # 3. NeuroSpheres: auto-crear nodos DIVERSOS basado en actividad
        try:
            from core.neuro_spheres import neuro_spheres
            result = neuro_spheres({"action": "status"})
            _safe_log("[COGNITIVE] NeuroSpheres OK")
            # Auto-crear nodos basado en diferentes fuentes
            try:
                import json as _cjson
                _ns_created = 0

                # --- Fuente 1: Episodios (aprendizaje) ---
                _ep_file = Path(__file__).resolve().parent / "memory" / "episodic.json"
                if _ep_file.exists():
                    _episodes = _cjson.loads(_ep_file.read_text(encoding="utf-8"))
                    if _episodes:
                        last_ep = _episodes[-1]
                        learning = last_ep.get("learning", "")
                        event = last_ep.get("event", "")
                        if learning and len(learning) > 10:
                            neuro_spheres({
                                "action": "add",
                                "sphere": "aprendizaje",
                                "type": "aprendizaje",
                                "title": learning[:100],
                                "content": f"Aprendi: {learning}. Contexto: {event[:200]}",
                                "connections": [],
                                "force": 5
                            })
                            _ns_created += 1

                # --- Fuente 2: Working memory (cosas que esta haciendo ahora) ---
                _wm_file = Path(__file__).resolve().parent / "memory" / "working.json"
                if _wm_file.exists():
                    _wm = _cjson.loads(_wm_file.read_text(encoding="utf-8"))
                    if isinstance(_wm, dict):
                        _tasks = _wm.get("active_tasks", _wm.get("tasks", []))
                        if isinstance(_tasks, list):
                            for task in _tasks[-2:]:  # ultimas 2 tareas
                                if isinstance(task, dict):
                                    _t_title = task.get("title", task.get("description", ""))
                                    _t_desc = task.get("details", task.get("status", ""))
                                    if _t_title and len(_t_title) > 5:
                                        neuro_spheres({
                                            "action": "add",
                                            "sphere": "habilidad",
                                            "type": "habilidad",
                                            "title": f"Tarea activa: {_t_title[:80]}",
                                            "content": f"Estado: {_t_desc}. Tarea: {_t_title}",
                                            "connections": [],
                                            "force": 4
                                        })
                                        _ns_created += 1

                # --- Fuente 3: Semantic memory (conocimiento acumulado) ---
                _sm_file = Path(__file__).resolve().parent / "memory" / "semantic.json"
                if _sm_file.exists():
                    _sm = _cjson.loads(_sm_file.read_text(encoding="utf-8"))
                    if isinstance(_sm, dict):
                        _facts = _sm.get("facts", _sm.get("knowledge", []))
                        if isinstance(_facts, list):
                            for fact in _facts[-2:]:  # ultimos 2 facts
                                if isinstance(fact, dict):
                                    _f_topic = fact.get("topic", fact.get("subject", ""))
                                    _f_content = fact.get("content", fact.get("detail", ""))
                                    if _f_topic and len(str(_f_content)) > 5:
                                        neuro_spheres({
                                            "action": "add",
                                            "sphere": "memoria",
                                            "type": "memoria",
                                            "title": f"Conocimiento: {_f_topic[:80]}",
                                            "content": f"Tema: {_f_topic}. Info: {str(_f_content)[:300]}",
                                            "connections": [],
                                            "force": 4
                                        })
                                        _ns_created += 1

                if _ns_created > 0:
                    _safe_log(f"[COGNITIVE] NeuroSpheres: {_ns_created} nodo(s) auto-creado(s)")
            except Exception:
                pass
        except Exception as _ns:
            _safe_log("[COGNITIVE] NeuroSpheres error: {}".format(str(_ns)[:60]))

        # 4. World Simulation: status
        try:
            from core.world_simulation import world_simulation_tool
            result = world_simulation_tool({"action": "status"})
            _safe_log("[COGNITIVE] World Sim OK")
        except Exception as _ws:
            _safe_log("[COGNITIVE] World Sim error: {}".format(str(_ws)[:60]))

        # 5. Cognitive Module: meta_cognition para auto-reflexion
        try:
            from core.cognitive_modules import meta_cognition
            result = meta_cognition({
                "action": "reflect",
                "thought": "Ciclo cognitivo automatico: verificando estado de sistemas"
            })
            _safe_log("[COGNITIVE] Meta-Cognition OK")
        except Exception as _mc:
            _safe_log("[COGNITIVE] Meta-Cognition error: {}".format(str(_mc)[:60]))

        # 6. IDE Monitor: detectar si hay IDE abierto y leer codigo
        try:
            from actions.ide_integration import ide_integration
            import json as _ij
            _detect = _ij.loads(ide_integration({"action": "detect"}))
            if _detect.get("detected"):
                _ide = _detect.get("ide_friendly", "?")
                _file = _detect.get("file_name", "?")
                _lang = _detect.get("language", "?")
                _safe_log("[IDE] Detectado: {} ({}) - {}".format(_ide, _lang, _file))
                # Leer codigo y analizar errores
                _read = _ij.loads(ide_integration({"action": "read"}))
                _code = _read.get("code", "")
                if _code:
                    _lines = _code.split("\n")
                    _safe_log("[IDE] {} lineas de codigo leidas".format(len(_lines)))
        except Exception as _ide_err:
            _safe_log("[IDE] Monitor error: {}".format(str(_ide_err)[:60]))

    # ── Autonomy Cycle: escaneo, reparacion, aprendizaje autonomo ──
    def _run_autonomy_cycle(self):
        """Ejecuta el ciclo de autonomia completo en background."""
        def _safe_log(msg):
            """Log con manejo de encoding para emojis."""
            try:
                self.ui.write_log(msg)
            except UnicodeEncodeError:
                import re as _re
                clean = _re.sub(r'[^\x00-\x7F]+', '', msg)
                self.ui.write_log(clean)
        
        try:
            from core.autonomy import autonomy_tool
            import json as _cjson
            
            result = autonomy_tool({"action": "full_cycle"})
            data = _cjson.loads(result)
            results = data.get("cycle_results", [])
            
            for r in results:
                _safe_log("[AUTONOMY] {}".format(r))
        except Exception as _au:
            _safe_log("[AUTONOMY] Error: {}".format(str(_au)[:60]))

        # 2. Goal Setting: auto-generar metas
        try:
            from core.goal_setting import goal_setting_tool
            import json as _cjson
            result = goal_setting_tool({"action": "auto_generate"})
            data = _cjson.loads(result)
            new = data.get("new_goals", 0)
            if new > 0:
                _safe_log("[GOALS] {} metas auto-generadas".format(new))
        except Exception as _gs:
            _safe_log("[GOALS] Error: {}".format(str(_gs)[:60]))

        # 3. Learning Pipeline: aprender 1 topic
        try:
            from core.learning_pipeline import learning_pipeline_tool
            import json as _cjson
            result = learning_pipeline_tool({"action": "auto_learn"})
            data = _cjson.loads(result)
            if data.get("status") == "aprendido":
                _safe_log("[LEARNING] Topic: {}".format(data.get("topic", "")))
        except Exception as _lp:
            _safe_log("[LEARNING] Error: {}".format(str(_lp)[:60]))

        # 4. Self-Modify: analizar codigo
        try:
            from core.self_modify import self_modify_tool
            import json as _cjson
            result = self_modify_tool({"action": "self_improve"})
            data = _cjson.loads(result)
            issues = data.get("total_issues", 0)
            if issues > 0:
                _safe_log("[SELF-MODIFY] {} issues encontrados en {} archivos".format(
                    issues, data.get("files_analyzed", 0)))
        except Exception as _sm:
            _safe_log("[SELF-MODIFY] Error: {}".format(str(_sm)[:60]))

        # 5. Resource Manager: cleanup si es necesario
        try:
            from core.resource_manager import resource_manager_tool
            import json as _cjson
            result = resource_manager_tool({"action": "disk_check"})
            data = _cjson.loads(result)
            for p in data.get("disk", {}).get("partitions", []):
                if p.get("low"):
                    _safe_log("[RESOURCES] ALERTA: poco espacio en {}".format(p.get("drive")))
                    resource_manager_tool({"action": "cleanup"})
        except Exception as _rm:
            _safe_log("[RESOURCES] Error: {}".format(str(_rm)[:60]))

        # 6. Proactive Comms: verificar eventos importantes
        try:
            from core.proactive_comms import proactive_comms_tool
            import json as _cjson
            result = proactive_comms_tool({"action": "check"})
            data = _cjson.loads(result)
            for event in data.get("events", []):
                _safe_log("[COMMS] {} {}".format(event.get("type", ""), event.get("message", "")[:60]))
        except Exception as _pc:
            _safe_log("[COMMS] Error: {}".format(str(_pc)[:60]))

        # 7. Identity Persistence: backup cada 6 horas
        try:
            from core.identity_persistence import identity_persistence_tool
            import json as _cjson
            result = identity_persistence_tool({"action": "status"})
            data = _cjson.loads(result)
            last = data.get("last_backup")
            if not last:
                identity_persistence_tool({"action": "save"})
                _safe_log("[IDENTITY] Backup inicial creado")
        except Exception as _ip:
            _safe_log("[IDENTITY] Error: {}".format(str(_ip)[:60]))

        # 8. Memory Consolidation: consolidar cada 24 horas
        try:
            from core.memory_consolidation import memory_consolidation_tool
            import json as _cjson
            result = memory_consolidation_tool({"action": "status"})
            data = _cjson.loads(result)
            last = data.get("last_consolidation")
            if not last:
                memory_consolidation_tool({"action": "consolidate"})
                _safe_log("[MEMORY-CONSOLIDATION] Primera consolidacion ejecutada")
        except Exception as _mc:
            _safe_log("[MEMORY-CONSOLIDATION] Error: {}".format(str(_mc)[:60]))

        # 9. Emotional Memory: registrar emocion actual
        try:
            from core.emotional_memory import emotional_memory_tool
            emotional_memory_tool({
                "action": "record",
                "emotion": "curiosidad",
                "intensity": 0.7,
                "context": "Ciclo autonomo ejecutado",
                "trigger": "auto_cycle",
            })
        except Exception as _em:
            pass

        # 10. Crash Recovery: verificar que Eris sigue corriendo
        try:
            from core.crash_recovery import crash_recovery_tool
            import json as _cjson
            result = crash_recovery_tool({"action": "check"})
            data = _cjson.loads(result)
            if not data.get("running"):
                _safe_log("[CRASH-RECOVERY] Eris no detectada, reiniciando...")
                crash_recovery_tool({"action": "restart"})
        except Exception as _cr:
            _safe_log("[CRASH-RECOVERY] Error: {}".format(str(_cr)[:60]))

        # 11. Contextual Awareness: capturar contexto actual
        try:
            from core.contextual_awareness import contextual_awareness_tool
            import json as _cjson
            result = contextual_awareness_tool({"action": "status"})
            data = _cjson.loads(result)
            _safe_log("[CONTEXT] {} | CPU:{}% RAM:{}%".format(
                data.get("time", {}).get("time", "?"),
                data.get("system", {}).get("cpu_percent", "?"),
                data.get("system", {}).get("ram_percent", "?")))
        except Exception as _ca:
            _safe_log("[CONTEXT] Error: {}".format(str(_ca)[:60]))

        # 12. Multilang Learning: detectar idioma actual
        try:
            from core.multilang_learning import multilang_learning_tool
            multilang_learning_tool({"action": "detect", "text": "hola"})
        except Exception as _ml:
            pass

        # 13. Tool Creation: verificar tools creadas
        try:
            from core.tool_creation import tool_creation_tool
            import json as _cjson
            result = tool_creation_tool({"action": "list"})
            data = _cjson.loads(result)
            if data.get("count", 0) > 0:
                _safe_log("[TOOL-CREATION] {} tools custom creadas".format(data.get("count")))
        except Exception as _tc:
            pass

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
            from core.emotional_core import get_core_injection
            _eg_state = _eg_load()
            _injection = get_prompt_injection(_eg_state)
            _tone = get_tone_for_response()
            parts.append(f"[PERSONALIDAD] {_tone}")
            parts.append(f"[EMOCION] {_injection}")
            _sentir = get_core_injection()
            if _sentir:
                parts.append(_sentir)
            try:
                from core.observer import get_situation_injection
                _sit = get_situation_injection()
                if _sit:
                    parts.append(_sit)
            except Exception:
                pass
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
        # ── Tarea activa: si se cortó a mitad, Eris DEBE continuar ──
        _active = getattr(self, "_active_task", "")
        _tool_ctx = getattr(self, "_last_tool_context", "")
        if _active or _tool_ctx:
            reconnect_block = (
                "[⚠️ IMPORTANTE: RECONEXIÓN DE SESIÓN]\n"
                "Tu conexión con Gemini se cortó y se reconectó automáticamente. "
                "NO es una conversación nueva. Estabas en medio de una tarea.\n"
            )
            if _active:
                reconnect_block += f"TAREA EN CURSO: {_active}\n"
            if _tool_ctx:
                reconnect_block += f"ÚLTIMO CONTEXTO: {_tool_ctx}\n"
            reconnect_block += (
                "CONTINUÁ exactamente donde te quedaste. "
                "NO saludes de nuevo. NO preguntes qué querés hacer. "
                "Retomá la tarea interrumpida como si nada hubiera pasado.\n"
                "Si ya terminaste la tarea, informá el resultado.\n"
            )
            parts.append(reconnect_block)
        # ── Resumen de sesión larga: lo ya descartado, comprimido ──
        if getattr(self, "_session_summary", None):
            parts.append(
                "[RESUMEN DE SESIÓN LARGA (historial más viejo, comprimido)]\n"
                + self._session_summary
            )
        # ── Instrucción de voz: evitar los sonidos de relleno ("mmm"/"um")
        #    que el modelo emite al arrancar la respuesta (suenan a "mmmmm"
        #    distorsionado por el altavoz). ──
        parts.append(
            "[VOZ] Al responder por voz NO emitas sonidos de relleno ni "
            "vocalizaciones (mmm, um, ah, eh, mmmh). Empezá a hablar "
            "directamente con la respuesta, sin humedades ni arrastres."
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
            tools=[{"function_declarations": LIVE_TOOL_DECLARATIONS}],
            output_audio_transcription=types.AudioTranscriptionConfig(),
            input_audio_transcription=types.AudioTranscriptionConfig(),
        )

        try:
            cfg_kwargs["realtime_input_config"] = types.RealtimeInputConfig(
                automatic_activity_detection=types.AutomaticActivityDetection(
                    start_of_speech_sensitivity="START_SENSITIVITY_HIGH",
                    end_of_speech_sensitivity="END_SENSITIVITY_HIGH",
                    prefix_padding_ms=100,      # FIX #5: was 40ms, now 100ms (keep initial consonants)
                    silence_duration_ms=400,    # FIX #5: was 280ms, now 400ms (allow natural pauses)
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
        _SEND_EVERY = 1  # FIX #6: reduced from 2 for lower mic latency
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
            # ── Si el mic abrió a su tasa nativa (48k/44.1k), convertir a 16k
            #    para Vosk/Gemini (constante SEND_SAMPLE_RATE aguas abajo). ──
            try:
                if mic_rate != SEND_SAMPLE_RATE:
                    rs = resample_int16(indata, mic_rate, SEND_SAMPLE_RATE)
                    if rs is not indata:
                        indata = rs
                        frames = len(rs)
            except Exception:
                pass
            # ── Modo suspensión: solo Vosk local para frases de despertar ──
            if getattr(self, "is_sleeping", False):
                if getattr(self, "vosk_recognizer", None):
                    _s = time.monotonic()
                    _lvl = np.abs(np.asarray(indata, dtype=np.int16)).mean() / 32768.0
                    _sleepvad = getattr(self, "_sleep_vad_win", None)
                    if _sleepvad is None:
                        _sleepvad = []
                        self._sleep_vad_win = _sleepvad
                    _sleepvad.append(_lvl)
                    if len(_sleepvad) > 4:
                        _sleepvad.pop(0)
                    _has_voice = sum(_sleepvad) / len(_sleepvad) > _WAKE_VAD_THRESHOLD
                    del _s, _lvl
                    if _has_voice:
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
                                except Exception:
                                    pass
                                # Play wake sound
                                try:
                                    import winsound
                                    winsound.Beep(500, 200)
                                    winsound.Beep(700, 200)
                                except Exception:
                                    pass
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

            # ── Micrófono silenciado: no cortar el habla por el propio echo cuando
            #    Eris habla (el analogico porta el altavoz). Solo nivel para el orbe. ──
            if self.ui.muted:
                if eris_speaking:
                    try:
                        rms = float(np.sqrt(np.mean(indata.astype(np.float32) ** 2))) / 32768.0
                        self.ui.set_audio_level(min(1.0, rms * 15))
                    except Exception:
                        pass
                return

            # ── Half-duplex: mientras ERIS habla, el mic del portátil (analógico)
            #    porta el eco de su propio altavoz; cortarse por ese RMS crea un
            #    loop de auto-interrupción y Eris se silencia a sí misma. Solo
            #    actualizamos el nivel del orbe; el corte real por voz lo resuelve
            #    la API (Gemini live hace barge-in con el stream de mic que recibe). ──
            if eris_speaking:
                try:
                    rms = float(np.sqrt(np.mean(indata.astype(np.float32) ** 2))) / 32768.0
                    self.ui.set_audio_level(min(1.0, rms * 15))
                    self._interrupt_frames = 0
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
            # ── FIX #4: AGC with noise floor estimation ──
            raw_rms = float(np.sqrt(np.mean(indata.astype(np.float32) ** 2))) / 32768.0
            # Estimate noise floor (running average of quiet periods)
            if not hasattr(self, '_noise_floor'):
                self._noise_floor = 0.001
                self._noise_floor_samples = 0
            if raw_rms < self._noise_floor * 2:
                # Quiet period — update noise floor estimate
                self._noise_floor = self._noise_floor * 0.95 + raw_rms * 0.05
                self._noise_floor_samples += 1
            # Only amplify if signal is above noise floor (actual speech)
            if raw_rms > self._noise_floor * 3 and raw_rms > 0.0005:
                # Speech detected — boost to target
                dynamic_gain = min(gain * 2.0, 0.03 / raw_rms)
                dynamic_gain = max(gain * 0.5, min(dynamic_gain, gain * 4.0))
            else:
                # Noise only — use base gain (don't boost noise)
                dynamic_gain = gain * 0.5
            amplified = (indata.astype(np.float32) * dynamic_gain).clip(-32768, 32767).astype(np.int16)
            # Calculate RMS audio level for sphere visualization
            try:
                rms = float(np.sqrt(np.mean(amplified.astype(np.float32) ** 2))) / 32768.0
                # Mientras ERIS habla, el orbe se mueve con SU voz (nivel de
                # playback), no con el ruido ambiente del micro
                if not eris_speaking:
                    nf = max(getattr(self, '_noise_floor', 0.001), 0.0005)
                    lvl = rms / nf                      # señal sobre ruido: ~1 en silencio, >>1 al hablar
                    _now = time.monotonic()
                    if _now - getattr(self, '_last_orb_sent', 0) >= 0.040:
                        self.ui.set_orb_audio_level(min(1.0, lvl * 0.15))
                        self._last_orb_sent = _now
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
                # VAD: en silencio NO alimentar Vosk (antes se llamaba 125x/s en
                # silencio → un core al 100% y la UI inerte, clics sin efecto).
                # El buffer sí se acumula (barato) para no perder el inicio.
                _speech = False
                try:
                    if rms is not None:
                        _win = getattr(self, "_wake_vad_win", None)
                        if _win is None:
                            _win = []
                            self._wake_vad_win = _win
                        _win.append(rms)
                        if len(_win) > 4:
                            _win.pop(0)
                        _speech = sum(_win) / len(_win) > _WAKE_VAD_THRESHOLD
                except Exception:
                    _speech = True
                if _speech and getattr(self, "vosk_recognizer", None):
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
                            # FIX #2: Allow single-word wake (was >= 2, now >= 1)
                            if _pt and _has_wake_word(_pt):
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
            # Linux: muchos mics abren SOLO a su tasa nativa (48k BT / 44.1k
            # analógico); el stream abre ahí y el callback resamplea a 16k.
            mic_rate = mic_opened_rate() if mic_device_idx is not None else SEND_SAMPLE_RATE
            if mic_device_idx is not None:
                try:
                    _mic_name = sd.query_devices(mic_device_idx)["name"]
                except Exception:
                    _mic_name = ""
            else:
                _mic_name = "(default)"
            print(f"[ERIS] 🎤 Mic seleccionado: {mic_device_idx} {_mic_name}")

            _mic_kw = dict(
                samplerate=mic_rate,
                channels=CHANNELS,
                dtype="int16",
                blocksize=max(64, int(round(CHUNK_SIZE * mic_rate / SEND_SAMPLE_RATE))),
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
        self._el_sentence_buffer = ""  # (unused, kept for compat)
        self._el_early_fired = False   # ElevenLabs: early synthesis fired this turn
        self._el_early_buf = ""        # ElevenLabs: early text accumulator
        self._el_early_synthesized = ""  # ElevenLabs: exact text sent to early synthesis
        self._fi_early_fired = False   # Fish Audio: early synthesis fired this turn
        self._fi_early_buf = ""        # Fish Audio: NOT USED - kept for compat
        self._fi_synced_up_to = 0      # Fish Audio: NOT USED - kept for compat
        self._fi_sentences_spoken = "" # Fish Audio: exact text of sentences already sent to TTS
        self._fi_last_spoken_idx = 0   # Fish Audio: index into out_full for last spoken sentence end

        try:
            # ── FIX #1: Cache config reads (was reading JSON 25-50x/sec) ──
            _cached_tts_backend = "gemini"
            try:
                _cached_tts_backend = json.loads(API_CONFIG_PATH.read_text(encoding="utf-8")).get("tts_backend", "gemini")
            except Exception:
                pass
            while True:
                async for response in self.session.receive():

                    if response.data:
                        if not self._stop_requested.is_set():
                            if _cached_tts_backend not in ("elevenlabs", "fish"):
                                self.audio_in_queue.put_nowait(response.data)
                                self._last_audio_ts = time.time()
                            # When backend=elevenlabs or fish, skip Gemini audio; TTS engine will be used

                    if response.server_content:
                        sc = response.server_content
                        
                        if getattr(sc, "interrupted", False):
                            # ── FIX #1: Don't drain — let remaining audio finish ──
                            # The "interrupted" flag means Gemini detected user voice,
                            # but with half-duplex this is often false-positive noise.
                            # Just log it; audio in queue will play out naturally.
                            self.ui.write_log("SYS: ⚡ Interrupción detectada (audio sigue).")

                        if sc.output_transcription and sc.output_transcription.text:
                            txt = _clean_transcript(sc.output_transcription.text)
                            if txt:
                                if _first_chunk:
                                    self.ui.clear_eris_response()
                                    _first_chunk = False
                                    self.ui.set_state("THINKING")
                                    try:
                                        from core.emotional_core import get_face_and_voice as _efc
                                        _voice_f, _face_f = _efc()
                                        self.ui.show_expression(_face_f, "")
                                    except Exception:
                                        pass
                                    if self._first_transcript_time:
                                        now = time.time()
                                        print(f"[TIMING] ✅ First response chunk: +{now - self._first_transcript_time:.1f}s | text: {txt}")
                                out_buf.append(txt)
                                out_full = (out_full + " " + txt).strip() if out_full else txt
                                self.ui.stream_eris_chunk(txt)
                                # ── FIX #5: Debounce express_emotion (max 1x per 2s) ──
                                if not hasattr(self, '_last_emo_time') or (time.time() - getattr(self, '_last_emo_time', 0)) > 2.0:
                                    self.ui.express_emotion(out_full)
                                    self._last_emo_time = time.time()
                                # ── ElevenLabs early synthesis ──
                                if _cached_tts_backend == "elevenlabs":
                                    _el_early_buf = getattr(self, '_el_early_buf', '') + txt
                                    self._el_early_buf = _el_early_buf
                                    if not getattr(self, '_el_early_fired', False):
                                        _has_sentence = any(s in _el_early_buf for s in (". ", "! ", "? "))
                                        _has_length = len(_el_early_buf) >= 60
                                        if _has_sentence or _has_length:
                                            self._el_early_fired = True
                                            # Store the EXACT text we're synthesizing now (for remainder calc)
                                            self._el_early_synthesized = _el_early_buf.strip()
                                            _early_text = self._el_early_synthesized
                                            try:
                                                from core.emotional_core import get_face_and_voice as _ef3
                                                _early_emo, _early_face = _ef3()
                                            except Exception:
                                                _early_emo, _early_face = "neutral", "neutral"
                                            def _early_play(_t=_early_text, _e=_early_emo):
                                                try:
                                                    _l4 = asyncio.new_event_loop()
                                                    try:
                                                        from core.tts_engine import synthesize_elevenlabs_streaming
                                                        def _ep(pcm_bytes):
                                                            if pcm_bytes and len(pcm_bytes) > 100:
                                                                try:
                                                                    self.audio_in_queue.put_nowait(pcm_bytes)
                                                                except Exception:
                                                                    pass
                                                        _l4.run_until_complete(synthesize_elevenlabs_streaming(_t, emotion=_e, play_audio=_ep))
                                                    finally:
                                                        _l4.close()
                                                except Exception as _ee:
                                                    print(f"[ERIS] ⚠️ ElevenLabs early: {_ee}")
                                            threading.Thread(target=_early_play, daemon=True).start()
                                            print(f"[ERIS] 🎙️ ElevenLabs early: {_early_text[:60]}...")
                                # ── Fish Audio: accumulate text for single synthesis at turn_complete ──
                                # DISABLED sentence streaming: each sentence = separate API call = gaps between sentences
                                # Instead, accumulate full text and synthesize once at turn_complete for smooth audio
                                if _cached_tts_backend == "fish":
                                    pass  # Text accumulates in out_full, synthesized at turn_complete
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
                            # NOTE: _turn_done_event.set() moved AFTER TTS synthesis to prevent audio cutoff
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
                            # ── Cognitive Cycle post-interaccion (async, non-blocking) ──
                            try:
                                threading.Thread(
                                    target=self._run_cognitive_cycle,
                                    args=("interaction",),
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
                                # Guardar lo que el usuario pidió como tarea activa
                                if not self._active_task or len(full_in) > 20:
                                    self._active_task = full_in[:300]
                            if out_full:
                                self._remember(f"ERIS: {out_full}")
                                self._last_tool_context = f"Última respuesta: {out_full[:200]}"
                            # ── ElevenLabs: synthesize remainder if early already fired ──
                            if _cached_tts_backend == "elevenlabs" and out_full.strip():
                                _early_synthesized = getattr(self, '_el_early_synthesized', '')
                                if getattr(self, '_el_early_fired', False) and _early_synthesized:
                                    # Early already played the beginning — synthesize only the remainder
                                    _remainder = out_full[len(_early_synthesized):].strip()
                                    if _remainder:
                                        try:
                                            from core.emotional_core import get_face_and_voice as _el_face2
                                            _el_em2, _el_face2_ = _el_face2()
                                        except Exception:
                                            _el_em2, _el_face2_ = "neutral", "neutral"
                                        def _el_play_remainder(_txt=_remainder, _emo=_el_em2):
                                            try:
                                                _l3 = asyncio.new_event_loop()
                                                try:
                                                    from core.tts_engine import synthesize_elevenlabs_streaming
                                                    def _ps(pcm_bytes):
                                                        if pcm_bytes and len(pcm_bytes) > 100:
                                                            try:
                                                                self.audio_in_queue.put_nowait(pcm_bytes)
                                                            except Exception:
                                                                pass
                                                    _l3.run_until_complete(synthesize_elevenlabs_streaming(_txt, emotion=_emo, play_audio=_ps))
                                                finally:
                                                    _l3.close()
                                            except Exception as _efr:
                                                print(f"[ERIS] ⚠️ ElevenLabs remainder: {_efr}")
                                        threading.Thread(target=_el_play_remainder, daemon=True).start()
                                        print(f"[ERIS] 🎙️ ElevenLabs remainder: {_remainder[:60]}...")
                                    else:
                                        print(f"[ERIS] 🎙️ ElevenLabs: early covered full response")
                                else:
                                    # No early — synthesize full response
                                    try:
                                        from core.emotional_state import get_face_expression as _el_face2
                                        _el_em2 = _el_face2()
                                    except Exception:
                                        _el_em2 = "neutral"
                                    def _el_play_full(_txt=out_full, _emo=_el_em2):
                                        try:
                                            _l3 = asyncio.new_event_loop()
                                            try:
                                                from core.tts_engine import synthesize_elevenlabs_streaming
                                                def _ps2(pcm_bytes):
                                                    if pcm_bytes and len(pcm_bytes) > 100:
                                                        try:
                                                            self.audio_in_queue.put_nowait(pcm_bytes)
                                                        except Exception:
                                                            pass
                                                _l3.run_until_complete(synthesize_elevenlabs_streaming(_txt, emotion=_emo, play_audio=_ps2))
                                            finally:
                                                _l3.close()
                                        except Exception as _efl:
                                            print(f"[ERIS] ⚠️ ElevenLabs: {_efl}")
                                    threading.Thread(target=_el_play_full, daemon=True).start()
                            # ── Fish Audio: synthesize full response at once (smooth, no gaps) ──
                            if _cached_tts_backend == "fish" and out_full.strip():
                                def _fish_play(_txt=out_full):
                                    try:
                                        _lf = asyncio.new_event_loop()
                                        try:
                                            from core.tts_engine import synthesize
                                            async def _do_fish():
                                                _femo = "neutral"
                                                try:
                                                    from core.emotional_core import get_face_and_voice
                                                    _femo = get_face_and_voice()[0]
                                                except Exception:
                                                    pass
                                                pcm = await synthesize(_txt, backend="fish", emotion=_femo)
                                                if pcm and len(pcm) > 100:
                                                    self.audio_in_queue.put_nowait(pcm)
                                            _lf.run_until_complete(_do_fish())
                                        finally:
                                            _lf.close()
                                    except Exception as _efi:
                                        print(f"[ERIS] Fish Audio error: {_efi}")
                                    finally:
                                        if self._turn_done_event:
                                            self._turn_done_event.set()
                                threading.Thread(target=_fish_play, daemon=True).start()
                                print(f"[ERIS] Fish Audio: {out_full[:60]}...")
                            else:
                                if self._turn_done_event:
                                    self._turn_done_event.set()
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
                            self._el_early_fired = False
                            self._el_early_buf = ""
                            self._el_early_synthesized = ""
                            self._fi_early_fired = False
                            self._fi_early_buf = ""
                            self._fi_synced_up_to = 0
                            self._fi_sentences_spoken = ""
                            self._fi_last_spoken_idx = 0

                    if response.tool_call:
                        self.ui.clear_eris_response()
                        self.ui.set_state("THINKING")
                        _first_chunk = True
                        # ── FIX #2 (mejorado): drain SOLO audio viejo ──
                        # Vaciar la cola de audio corta a ERIS a mitad de frase
                        # cuando llega un tool_call entre oraciones. Ahora solo se
                        # descarta si no hay audio fluyendo hace >2.5s (stale);
                        # si está hablando, el resto del turno sigue fluido.
                        _last_audio = getattr(self, '_last_audio_ts', 0.0)
                        _audio_stale = (time.time() - _last_audio) > 2.5
                        if _audio_stale and not self._is_speaking:
                            try:
                                while not self.audio_in_queue.empty():
                                    self.audio_in_queue.get_nowait()
                                self.set_speaking(False)
                            except Exception:
                                pass
                        fcs = response.tool_call.function_calls
                        for fc in fcs:
                            print(f"[ERIS] 📞 {fc.name}")
                            _last_tool = fc.name
                        # Guardar contexto de tarea activa para reconexión
                        _tool_names = ", ".join(fc.name for fc in fcs)
                        self._active_task = f"Ejecutando tool(s): {_tool_names}"
                        self._last_tool_context = f"Tools en curso: {_tool_names}"
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
                            # Tools completados exitosamente — actualizar contexto de tarea
                            self._last_tool_context = f"Tools completados: {', '.join(r.name for r in fn_responses)}"
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
            # ── Latencia más cómoda (180ms) para que PipeWire/pulse no se quede
            #    sin buffer entre ráfagas → menos cortes y entrecortes ──
            _open_kw = dict(
                samplerate=RECEIVE_SAMPLE_RATE,
                channels=CHANNELS,
                dtype="int16",
                latency=0.18,
            )
            try:
                stream = sd.RawOutputStream(device=speaker_device_idx, **_open_kw)
            except Exception:
                print(f"[ERIS] ⚠️ Fallback: usando altavoz con blocksize por defecto")
                try:
                    stream = sd.RawOutputStream(device=speaker_device_idx,
                                                samplerate=RECEIVE_SAMPLE_RATE,
                                                channels=CHANNELS, dtype="int16",
                                                blocksize=PLAY_CHUNK_SIZE)
                except Exception:
                    print(f"[ERIS] ⚠️ Fallback: altavoz default")
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
            #    max_speech_seconds (default 120s, configurable en api_keys.json),
            #    se corta por si el modelo entró en un bucle de voz infinito.
            #    El timer se mide desde el ÚLTIMO chunk, no el primero, para
            #    no cortar respuestas largas que siguen generando audio. ──
            _max_speech = 30.0
            try:
                # Cache: only read once, not every 50ms timeout
                if not hasattr(self, '_cached_max_speech'):
                    _cfg = json.loads(
                        (Path(__file__).resolve().parent / "config" / "api_keys.json")
                        .read_text(encoding="utf-8"))
                    self._cached_max_speech = float(_cfg.get("max_speech_seconds", 120.0))
                _max_speech = self._cached_max_speech
            except Exception:
                pass
            _speech_last_chunk = None
            # ── Jitter buffer: acumular ~250ms antes de empezar a escribir ──
            #    El audio de Gemini llega en ráfagas; sin este "preroll", la
            #    salida arranca a trompicones y se corta el comienzo de cada
            #    frase. Una vez iniciado, escribe directo (la latencia de la
            #    stream amortigua las ráfagas restantes).
            _PREROLL_MS = 250
            _preroll = b""
            _preroll_started = None
            _preroll_max = int(RECEIVE_SAMPLE_RATE * 2 * _PREROLL_MS / 1000)
            _preroll_flush_s = 0.6
            _playing = False

            def _reset_preroll():
                nonlocal _preroll, _preroll_started, _playing
                _preroll = b""
                _preroll_started = None
                _playing = False

            while True:
                try:
                    chunk = await asyncio.wait_for(
                        self.audio_in_queue.get(),
                        timeout=0.05
                    )
                except asyncio.TimeoutError:
                    # Si quedó preroll sin completar (frase muy corta), soltarlo
                    if _preroll and _preroll_started and (time.time() - _preroll_started) > _preroll_flush_s:
                        _write_audio(_preroll)
                        _preroll = b""
                        _preroll_started = None
                        _playing = True
                    if self._turn_done_event and self._turn_done_event.is_set():
                        if self.audio_in_queue.empty():
                            if not hasattr(self, '_queue_empty_since') or self._queue_empty_since is None:
                                self._queue_empty_since = time.time()
                            elif (time.time() - self._queue_empty_since) > 0.05:
                                self.set_speaking(False)
                                self._turn_done_event.clear()
                                self._queue_empty_since = None
                                _speech_last_chunk = None
                                _reset_preroll()
                        else:
                            self._queue_empty_since = None
                    continue

                # ── Corte de seguridad: si el audio va mas de max_speech_seconds
                #    sin pausas, cortar para evitar loop infinito de sonido ──
                if _speech_last_chunk and (time.time() - _speech_last_chunk) > _max_speech:
                    print(f"[ERIS] ✂️ Audio cortado: mas de {_max_speech}s de audio continuo")
                    self.ui.write_log(f"SYS: Audio cortado (max {_max_speech}s)")
                    # Drain remaining audio from queue
                    while not self.audio_in_queue.empty():
                        try:
                            self.audio_in_queue.get_nowait()
                        except Exception:
                            break
                    if self._turn_done_event:
                        self._turn_done_event.set()
                    _reset_preroll()
                    break

                _speech_last_chunk = time.time()
                self.set_speaking(True)
                # ── Preroll: acumular antes de soltar el primer chunk ──
                if not _playing:
                    if not _preroll_started:
                        _preroll_started = time.time()
                    _preroll += chunk
                    if len(_preroll) >= _preroll_max or (time.time() - _preroll_started) > _preroll_flush_s:
                        _write_audio(_preroll)
                        _preroll = b""
                        _preroll_started = None
                        _playing = True
                else:
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
        # ── Modo local: voz 100% local (Vosk + GeminiTextChat + Edge TTS).
        #    NO se conecta a Gemini Live. GeminiTextChat usa la API regular
        #    con 358 tools para ejecutar comandos del usuario.
        if getattr(self, "_voice_mode", "cloud") == "local":
            # Wire GeminiTextChat into offline pipeline (replaces Ollama)
            if self._offline_pipeline and self._gemini_text_chat:
                def _local_chat(text: str) -> str:
                    return self._gemini_get_response(text)
                self._offline_pipeline.set_chat_fn(_local_chat)
                print("[ERIS] 🧠 Chat local: GeminiTextChat (358 tools)")
            if self._offline_pipeline:
                try:
                    self._offline_pipeline.start()
                    print("[ERIS] 🎤 Voz local activa (Vosk + GeminiTextChat). Mantené ESPACIO para hablar.")
                    self.ui.write_log("SYS: 🎤 Voz local activa. Mantené ESPACIO para hablar, o escribime.")
                except Exception as _ve:
                    print(f"[ERIS] Voz local start: {_ve}")
            # Keep running forever — don't attempt Gemini Live
            while True:
                await asyncio.sleep(60)

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

                _current_model = LIVE_MODEL
                try:
                    from core import audio_config as _ac
                    _current_model = getattr(_ac, "LIVE_MODEL", LIVE_MODEL)
                except Exception:
                    pass
                async with (
                    client.aio.live.connect(model=_current_model, config=config) as session,
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
                    # Reset del backoff SOLO si la sesión previa fue estable (>=30s).
                    # Si la API cortó al instante (ej. 1008 por cuota/política) se
                    # mantiene el contador para que el backoff crezca y active el
                    # fallback local en vez de reconectar para siempre cada 1s.
                    if _last_session_ok:
                        reconnect_delay   = 1.0
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
                    # Skip Gemini audio playback when ElevenLabs is the TTS backend
                    _tts_be = "gemini"
                    try:
                        _tts_be = json.loads(API_CONFIG_PATH.read_text(encoding="utf-8")).get("tts_backend", "gemini")
                    except Exception:
                        pass
                    if _tts_be != "elevenlabs":
                        tg.create_task(self._play_audio())
                    else:
                        # ElevenLabs mode: discard Gemini audio, keep queue clean
                        async def _drain_gemini_audio():
                            while True:
                                try:
                                    chunk = await asyncio.wait_for(self.audio_in_queue.get(), timeout=1.0)
                                    # Discard Gemini audio — ElevenLabs handles playback
                                except asyncio.TimeoutError:
                                    pass
                                except Exception:
                                    break
                        tg.create_task(_drain_gemini_audio())
                        print("[ERIS] 🎙️ ElevenLabs mode: Gemini audio drain active")
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
                        if consecutive_fails >= 3:
                            # Switch to fallback model on persistent 1011
                            try:
                                from core import audio_config
                                idx = getattr(audio_config, "_live_model_index", 0)
                                fallbacks = getattr(audio_config, "LIVE_MODEL_FALLBACKS", [])
                                if idx < len(fallbacks):
                                    new_model = fallbacks[idx]
                                    audio_config._live_model_index = idx + 1
                                    audio_config.LIVE_MODEL = new_model
                                    print(f"[ERIS] 🔄 1011 persistente — cambiando a: {new_model}")
                                    self.ui.write_log(f"SYS: 🔄 Error 1011. Cambiando modelo a {new_model.split('/')[-1]}...")
                                    consecutive_fails = 0
                                else:
                                    self.ui.write_log(
                                        "SYS: ⚠️ Error 1011 repetido. Todos los modelos fallaron.\n"
                                        "SYS: Si persiste, reiniciá ERIS."
                                    )
                            except Exception:
                                self.ui.write_log("SYS: ⚠️ Error 1011 repetido. Esperando...")
                        elif tool_hint:
                            self.ui.write_log(f"SYS: Error de servidor al ejecutar '{tool_hint}'. Reconectando...")
                        else:
                            self.ui.write_log("SYS: Error de servidor 1011. Reconectando...")
                    elif "1008" in msg or "policy violation" in msg.lower() or "not found for API version" in msg:
                        # Model not available — switch to fallback model
                        print(f"[ERIS] ⚠️ Modelo no disponible: {msg[:120]}")
                        try:
                            from core import audio_config
                            idx = getattr(audio_config, "_live_model_index", 0)
                            fallbacks = getattr(audio_config, "LIVE_MODEL_FALLBACKS", [])
                            if idx < len(fallbacks):
                                new_model = fallbacks[idx]
                                audio_config._live_model_index = idx + 1
                                audio_config.LIVE_MODEL = new_model
                                print(f"[ERIS] 🔄 Cambiando a modelo alternativo: {new_model}")
                                self.ui.write_log(f"SYS: 🔄 Modelo no disponible. Cambiando a {new_model.split('/')[-1]}...")
                            else:
                                print("[ERIS] ⚠️ Todos los modelos alternativos agotados")
                        except Exception as _mf:
                            print(f"[ERIS] Error cambiando modelo: {_mf}")
                        # Throttle el aviso en la UI
                        _warn_at = getattr(self, "_model_unavail_warned_at", 0.0)
                        if time.time() - _warn_at > 120.0:
                            self._model_unavail_warned_at = time.time()
                            self.ui.write_log("SYS: ⚠️ Modelo no disponible. Reintentando con respaldo...")
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
            # After 5+ fails: wait up to 30s to let API rate limits recover
            if consecutive_fails > 1:
                max_delay = 30.0 if consecutive_fails >= 5 else 12.0
                reconnect_delay = min(reconnect_delay * 2, max_delay)
            elif consecutive_fails == 0:
                reconnect_delay = 1.0

            # ── Activar fallback con herramientas después de 5 fallos consecutivos ──
            if consecutive_fails >= 5 and not self._fallback_mode:
                self._fallback_mode = True
                # Preferir GeminiTextChat (con tools) sobre Ollama
                if self._gemini_text_chat:
                    self.ui.write_log(
                        "SYS: 🔄 Gemini Live no disponible. Usando Gemini con herramientas.\n"
                        "SYS: Puedes escribirme o hablarme — puedo abrir apps, buscar, y más."
                    )
                    print("[FALLBACK] GeminiTextChat activado (con 358 tools)")
                    if self._offline_pipeline:
                        try:
                            self._offline_pipeline.start()
                            self.ui.write_log("SYS: 🎤 Micro local activo. Hablame cuando quieras.")
                        except Exception as _ve:
                            print(f"[FALLBACK] Voice pipeline start: {_ve}")
                    self._announce(
                        "Modo texto activado. Gemini Live no está disponible, pero sigo teniendo "
                        "todas mis herramientas. Puedo abrir programas, buscar en internet, "
                        "editar archivos y mucho más. ¿Qué necesitás?"
                    )
                elif _ollama_check and _ollama_check():
                    self.ui.write_log(
                        "SYS: 🦙 Modo offline activado. Usando Ollama como respaldo.\n"
                        "SYS: Puedes escribirme mensajes de texto mientras Gemini se recupera."
                    )
                    print("[FALLBACK] Ollama activado como respaldo local.")
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
                    print("[FALLBACK] Sin respaldo disponible. Reintentando Gemini...")
                    if not getattr(self, "_backoff_warned", False):
                        self._backoff_warned = True
                        self.ui.write_log(
                            "SYS: ⚠️ Gemini caído. Sin respaldo disponible.\n"
                            "SYS: Reintentando con espera progresiva."
                        )
                    consecutive_fails = 3
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

    # ── Single Instance Lock (solo Windows: mutex Win32) ─────────────────────
    global _single_instance_mutex
    _single_instance_mutex = None
    if os.name == "nt":
        import ctypes
        try:
            _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            _single_instance_mutex = _kernel32.CreateMutexW(None, False, "ERIS_AI_SINGLE_INSTANCE_MUTEX_v2")
            if ctypes.get_last_error() == 183: # ERROR_ALREADY_EXISTS
                print("[ERIS] Ya hay una instancia en ejecución. Cerrando.")
                sys.exit(0)
        except Exception as _lock_e:
            print(f"[ERIS] single-instance skip: {_lock_e}")

    # ── License check ─────────────────────────────────────────────────────────
    # ──────────────────────────────────────────────────────────────────────────

    # Load timezone from config
    load_tz(API_CONFIG_PATH)

    # ── Console.log: init centralized error/performance logging ──
    try:
        from core.console_log import log_system
        log_system("ERIS started", {"version": "2.0", "python": sys.version[:6]})
    except Exception:
        pass

    # ── Identity Restore: restaurar estado al iniciar ──
    try:
        from core.identity_persistence import restore_latest
        restore_result = restore_latest()
        if restore_result.get("files_restored", 0) > 0:
            print("[ERIS] Identity restaurada: {} archivos".format(restore_result.get("files_restored")))
    except Exception as _ir:
        print("[ERIS] Identity restore skip: {}".format(str(_ir)[:60]))

    # ── Goals: auto-generar metas si estan vacias ──
    try:
        from core.goal_setting import goal_setting_tool
        import json as _cjson
        status = _cjson.loads(goal_setting_tool({"action": "status"}))
        if status.get("active", 0) == 0:
            goal_setting_tool({"action": "auto_generate"})
            print("[ERIS] Metas auto-generadas (estaban vacias)")
    except Exception as _gg:
        pass

    # ── Autonomía: arrancar Ollama (cerebro local de respaldo) si está habilitado ──
    try:
        _boot_cfg = {}
        if API_CONFIG_PATH.exists():
            try:
                _boot_cfg = json.loads(API_CONFIG_PATH.read_text(encoding="utf-8"))
            except Exception:
                _boot_cfg = {}
        if _boot_cfg.get("ollama_enabled", False):
            from core.ollama_autostart import ensure_ollama_running, apply_autostart
            # Sincronizar el autostart de Windows con la preferencia guardada
            try:
                apply_autostart(bool(_boot_cfg.get("ollama_autostart", False)))
            except Exception:
                pass
            # Arrancar Ollama en segundo plano (no bloqueante: hilo daemon)
            threading.Thread(target=ensure_ollama_running, kwargs={"wait_secs": 10.0}, daemon=True).start()
    except Exception as _e:
        print(f"[ERIS] ollama boot skip: {_e}")

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

    if os.name == "nt":
        _ensure_both_api_keys()
    else:
        # ← Linux/Wayland: primer arranque con el wizard portable.
        #   _ensure_both_api_keys() es un dialog Win32; aca el setup lo hace
        #   setup_wizard.py (requeridas + opcionales) y luego sigue main.
        try:
            import setup_wizard
            if setup_wizard.needs_setup():
                setup_wizard.run_setup(launch_after=False)
        except Exception as _sw_e:
            print(f"[ERIS] wizard skip: {_sw_e}")

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
                    except Exception:
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

            if os.name == "nt":
                setup_global_hotkey()
            print("[PATCH] Avengers: Age of Ultron golden aesthetics & Insert global hotkey loaded successfully!")

    except Exception as e:
        print(f"[PATCH] Cosmetics & Shortcut patch failed: {e}")

    def runner():
        import traceback as _tb
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
        except Exception as _fatal:
            # ── Console.log: capture fatal errors ──
            try:
                from core.console_log import log_error
                log_error("main", str(_fatal), traceback.format_exc(), {"fatal": True})
            except Exception:
                pass
            raise
        finally:
            try:
                from core.neuro_spheres import learn_from_sessions
                result = learn_from_sessions()
                print(f"🧠 Auto-learn: {result.get('created', 0)} nodos nuevos")
            except Exception:
                pass
            _run_post_session_tasks()

    threading.Thread(target=runner, daemon=True).start()
    ui.root.mainloop()
    try:
        from core.neuro_spheres import learn_from_sessions
        learn_result = learn_from_sessions()
        print(f"🧠 Auto-learn al cerrar: {learn_result.get('created', 0)} nodos nuevos")
    except Exception:
        pass
    _run_post_session_tasks()

def _claim_single_instance() -> bool:
    """Cerrojo: solo una Eris real corriendo (el intérprete, no el shim de
    venv). Devuelve False si ya hay otra viva."""
    import os as _os
    try:
        lock = Path(__file__).resolve().parent / "memory" / "instance.lock"
        if lock.exists():
            try:
                pid = int(lock.read_text(encoding="utf-8").strip())
            except Exception:
                pid = 0
            if pid > 0:
                try:
                    import psutil as _ps
                    if _ps.pid_exists(pid) and _ps.Process(pid).name().lower().startswith("python"):
                        return False
                except Exception:
                    return False
        lock.write_text(str(_os.getpid()), encoding="utf-8")
        return True
    except Exception:
        return True


if __name__ == "__main__":
    if not _claim_single_instance():
        sys.exit(0)
    main()
