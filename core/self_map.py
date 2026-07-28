"""
self_map.py — Mapa completo de ERIS.
ERIS conoce TODA su estructura: archivos, funciones, dependencias, cambios.
Este es su "espejo interno" — se mira y sabe lo que es.
"""
import os
import json
import hashlib
from pathlib import Path
from datetime import datetime

_BASE = Path(__file__).resolve().parent.parent
_SELF_MAP_FILE = _BASE / "data" / "self" / "full_map.json"
_CHANGELOG_FILE = _BASE / "data" / "self" / "changelog.json"


def _get_file_info(filepath: Path) -> dict:
    """Obtiene info de un archivo."""
    try:
        stat = filepath.stat()
        content = filepath.read_text(encoding="utf-8", errors="replace") if filepath.suffix == ".py" else ""
        return {
            "path": str(filepath.relative_to(_BASE)),
            "size": stat.st_size,
            "lines": content.count("\n") + 1 if content else 0,
            "hash": hashlib.sha256(content.encode()).hexdigest()[:12] if content else "",
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        }
    except Exception:
        return {"path": str(filepath.relative_to(_BASE)), "error": "unreadable"}


ERIS_MAP = {
    "name": "ERIS",
    "version": "2.0",
    "root": str(_BASE),
    "description": "Asistente de IA local con auto-conciencia, aprendizaje autónomo, y control total del sistema",

    "entry_points": {
        "main.py": {
            "desc": "Punto de entrada principal — inicializa UI PyQt6, Gemini Live, voice loop, tool dispatcher",
            "lines": 1374,
            "key_functions": ["main()", "ErisApp", "VoiceThread", "ToolThread", "ProactiveThread"],
        },
        "run.py": {"desc": "Launcher simple — llama main.main()"},
        "run_debug.py": {"desc": "Hot-reload para desarrollo — watch files + auto-restart"},
    },

    "core": {
        "action_imports.py": {"desc": "Imports centralizados para 120+ action modules", "lines": 500},
        "agent_router.py": {"desc": "Ruteo multi-agente — clasifica intención y despacha", "key": "weighted scoring + penalty keywords"},
        "audio_config.py": {"desc": "Config de audio Gemini Native Audio, sample rates, dispositivos"},
        "autonomous_learner.py": {"desc": "CEREBRO DE APRENDIZAJE — detecta gaps, investiga, ingesta en RAG, auto-evalúa", "key": "learn_topic, detect_gaps, auto_expand, assess"},
        "emotional_state.py": {"desc": "Estado emocional persistente — happy, sad, curious, etc.", "recently_fixed": "dead code + disk write"},
        "gpu_config.py": {"desc": "Config GPU — QtWebEngine Chromium flags"},
        "idle_learning_loop.py": {"desc": "APRENDIZAJE AUTÓNOMO — aprende SOLO cuando idle, guarda en Obsidian+RAG+semantic", "recently_created": True},
        "llm_bridge.py": {"desc": "Puente Ollama embeddings — nomic-embed-text 768-dim, hash fallback", "recently_created": True},
        "logging_setup.py": {"desc": "Config logging — paths, TeeStream stdout/stderr"},
        "model_router.py": {"desc": "Routing de modelos — Gemini/Groq/OpenRouter/Ollama por tipo de tarea"},
        "personality_engine.py": {"desc": "Personalidad dinámica — adapta tono de mood, contexto, interacciones"},
        "platform.py": {"desc": "Abstracción multi-plataforma — Windows/Linux/macOS"},
        "plugin_manager.py": {"desc": "Hot-load plugins — escanea plugins/, live reload"},
        "prompt_loader.py": {"desc": "Carga prompt.txt con fallback"},
        "prompt.txt": {"desc": "PROMPT DE ERIS — identidad, reglas, comportamiento, acceso a sí misma", "recently_updated": True},
        "rag_pipeline.py": {"desc": "RAG — ChromaDB vector store, indexa PDF/DOCX/TXT/MD, query semántico", "recently_fixed": "usa llm_bridge"},
        "reasoning_engine.py": {"desc": "Razonamiento AGI — Chain of Thought, verificación de hechos, contrafactuales"},
        "self_improvement.py": {"desc": "Auto-mejora — evaluación, corrección, optimización de prompts"},
        "semantic_memory.py": {"desc": "Memoria semántica — episódica/semántica/working + knowledge graph"},
        "task_planner.py": {"desc": "Planificador multi-paso — descompone metas, retry, persistencia"},
        "time_utils.py": {"desc": "Timezone colombiana, contexto de hora del día"},
        "tool_declarations.py": {"desc": "Schema de 192 herramientas para Gemini function calling", "lines": 3505},
        "tool_dispatcher.py": {"desc": "Despachador — rutea tool calls a actions via ThreadPoolExecutor", "lines": 838},
        "tool_registry.py": {"desc": "Registro lazy-loading — 226 tools, imports bajo demanda"},
        "training_pipeline.py": {"desc": "Entrenamiento continuo — auto-evaluación, detección de fallos, corrección"},
        "tts_engine.py": {"desc": "Text-to-speech — Edge TTS, cache de audio"},
        "updater.py": {"desc": "Auto-updater — GitHub Releases, backup, apply"},
        "voice_recognition.py": {"desc": "Verificación de voz — MFCC + cosine similarity"},
        "connectivity.py": {"desc": "Auto-detección internet + cambio online/offline (ConnectivityMonitor)", "recently_created": True},
        "offline_voice.py": {"desc": "Pipeline offline — Vosk STT + Ollama + Kokoro TTS (100% offline)", "recently_created": True},
        "self_healing.py": {"desc": "Auto-healing, auto-learning, health check cada 5 min, syntax fix, error log", "recently_created": True},
    },

    "actions": {
        "system_monitor.py": {"desc": "Monitor completo — CPU, RAM, disco, red, GPU, batería, procesos", "recently_rewritten": True},
        "computer_control.py": {"desc": "Control nativo — click, type, hotkeys, scroll, screenshot, window mgmt", "recently_rewritten": True},
        "file_controller.py": {"desc": "Archivos — crear, renombrar, editar, buscar, info, disco", "recently_rewritten": True},
        "browser_control.py": {"desc": "Navegador — navigate, search, click, read pages", "recently_rewritten": True},
        "screen_vision.py": {"desc": "Visión — screenshot + análisis por Gemini/Ollama minicpm-v", "recently_added_local_vision": True},
        "obsidian_brain.py": {"desc": "Segundo cerebro — leer/escribir/buscar/link notas Obsidian"},
        "knowledge_base.py": {"desc": "Knowledge base local — ChromaDB + Ollama embeddings"},
        "knowledge_ingestor.py": {"desc": "Ingesta masiva — archivos, URLs, texto, batch", "recently_created": True},
        "document_rag.py": {"desc": "RAG tool — index, query, list, stats, delete, clear", "recently_created": True},
        "data_connectors.py": {"desc": "Conectores — HuggingFace, Wikidata, GitHub, data.gov", "recently_created": True},
        "self_awareness.py": {"desc": "AUTO-CONCIENCIA — introspect, analyze, log, metacognition", "recently_enhanced": True},
        "self_edit.py": {"desc": "AUTO-EDICIÓN — read/edit/create archivos propios con backup"},
        "self_heal.py": {"desc": "AUTO-REPARACIÓN — escanea bugs, auto-fix con validación", "lines": 639},
        "web_search.py": {"desc": "Búsqueda web — DuckDuckGo + scraping"},
        "openrouter_agent.py": {"desc": "Chat AI — OpenRouter + Ollama fallback"},
        "research_agent.py": {"desc": "Investigación autónoma — curiosity-driven web research"},
        "autonomous_agent.py": {"desc": "Agente autónomo — ve pantalla, entiende contexto, trabaja solo"},
        "auto_programmer.py": {"desc": "Auto-programador — genera y testea tools en sandbox"},
        "emotional_growth.py": {"desc": "Desarrollo emocional — etapas, memoria emocional, ciclos", "lines": 514},
        "personality.py": {"desc": "Personalidad proactiva — humor, opiniones, sugerencias"},
        "security_scanner.py": {"desc": "Scanner seguridad — Defender, PowerShell, heurística"},
        "osint_agent.py": {"desc": "OSINT — inteligencia de fuentes abiertas"},
        "game_agent.py": {"desc": "Jugador — controla personaje via visión, explora, pelea"},
        "spotify_control.py": {"desc": "Spotify completo — play, pause, next, search, playlists"},
        "window_manager.py": {"desc": "Multi-monitor — mover, resize, snap, tile ventanas"},
        "proactive_automation.py": {"desc": "Automatización proactiva — reglas basadas en hábitos"},
        "predict_engine.py": {"desc": "Motor predictivo — anticipa necesidades por patrones"},
        "memory_consolidation.py": {"desc": "Consolidación de memorias — limpieza, merge, optimización", "recently_created": True},
        "email_manager.py": {"desc": "Email — IMAP/SMTP, leer, enviar, organizar, buscar", "recently_created": True},
        "calendar_manager.py": {"desc": "Calendario — crear eventos, Google Calendar sync", "recently_created": True},
        "flow_recorder.py": {"desc": "Grabador de flujos — macros, grabar/repetir acciones", "recently_created": True},
        "screenshot_history.py": {"desc": "Historial de screenshots — capturar, buscar, comparar", "recently_created": True},
        "clipboard_manager.py": {"desc": "Portapapeles — historial, monitoreo, fijar textos", "recently_created": True},
        "multi_user.py": {"desc": "Multi-usuario — perfiles diferentes con personalizaciones", "recently_created": True},
        "voice_cloning.py": {"desc": "Clonación de voz — entrenar, sintetizar, comparar", "recently_created": True},
        "browser_extension.py": {"desc": "Extensión de navegador — WebSocket server para Chrome/Firefox", "recently_created": True},
        "smart_notifications.py": {"desc": "Notificaciones inteligentes — contextuales, no molestas", "recently_created": True},
        "usage_analytics.py": {"desc": "Analytics de uso — stats de tools, errores, timeline", "recently_created": True},
        "skill_marketplace.py": {"desc": "Marketplace — publicar, descargar, instalar skills", "recently_created": True},
        "api_server.py": {"desc": "API Server — REST API para que otras apps hablen con ERIS", "recently_created": True},
        "federated_learning.py": {"desc": "Aprendizaje federado — patrones locales sin nube", "recently_created": True},
        "file_organizer.py": {"desc": "Organizador de archivos — auto-clasificar downloads/escritorio", "recently_created": True},
        "data_encryption.py": {"desc": "Cifrado de datos — AES-256 para memorias sensibles", "recently_created": True},
        "auto_backup.py": {"desc": "Auto-backup — backup automático de config, memoria, knowledge", "recently_created": True},
        "plugin_marketplace.py": {"desc": "Plugin marketplace — instalar, buscar, gestionar plugins", "recently_created": True},
        "proactive_ia.py": {"desc": "IA proactiva — recordar tareas, sugerir acciones, monitorear patrones", "recently_created": True},
        "voice_enhanced.py": {"desc": "Voz mejorada — wake word, perfiles de voz, TTS", "recently_created": True},
        "data_viz.py": {"desc": "Data visualization — charts con matplotlib/plotly", "recently_created": True},
        "i18n.py": {"desc": "Internacionalización — traducir mensajes, gestionar idiomas", "recently_created": True},
        "code_review.py": {"desc": "Code review — detectar issues, seguridad, estilo", "recently_created": True},
        "web_scraper.py": {"desc": "Web scraper — scraping avanzado con requests/bs4/playwright", "recently_created": True},
        "dashboard_web.py": {"desc": "Dashboard web — frontend real para api_server", "recently_created": True},
        "docker_deploy.py": {"desc": "Docker deploy — container para ERIS server", "recently_created": True},
        "ci_cd.py": {"desc": "CI/CD — tests automáticos, lint, typecheck", "recently_created": True},
        "i18n_ui.py": {"desc": "i18n UI — traducir interfaz completa", "recently_created": True},
        "voice_cloning_real.py": {"desc": "Voice cloning real — sintetizar voz con edge-tts", "recently_created": True},
    },

    "agents": {
        "vision_agent.py": {"desc": "Agente visión — screenshots, guardian, análisis imágenes"},
        "search_agent.py": {"desc": "Agente búsqueda — historial, archivos, super search, web"},
        "security_agent.py": {"desc": "Agente seguridad — scanning, gestión programas, safety gates"},
        "system_agent.py": {"desc": "Agente sistema — CPU/RAM/disk, desktop, Windows settings"},
        "media_agent.py": {"desc": "Agente media — Spotify, YouTube, image gen, TikTok"},
        "productivity_agent.py": {"desc": "Agente productividad — calendar, email, drive, docs"},
        "dev_agent.py": {"desc": "Agente dev — code help, git, codebase, knowledge base"},
        "opencode_bridge.py": {"desc": "Puente opencode — conecta ERIS con opencode CLI"},
    },

    "bios": {
        "boot.py": {"desc": "Boot sequence — BIOS-style, rule loading, crash tracking"},
        "watchdog.py": {"desc": "Watchdog — heartbeat, crash detection, auto-recovery"},
        "recovery.py": {"desc": "Recovery mode — estado, degradación graceful"},
        "post.py": {"desc": "POST — checksum, verificación integridad"},
    },

    "skills": {
        "skill_registry.py": {"desc": "Skills auto-mejorables con progressive disclosure", "lines": 527},
        "superpowers.py": {"desc": "Metodología Superpowers SDLC como skills"},
        "builtin/": {"desc": "11 skills built-in (brainstorming, TDD, debugging, threat-hunting, etc.)"},
    },

    "memory": {
        "memory_manager.py": {"desc": "Gestor largo plazo — notes, habits, preferences, context"},
        "working.json": {"desc": "Memoria de trabajo — contexto conversación activa"},
        "semantic.json": {"desc": "Memoria semántica — hechos, conceptos, relaciones"},
        "episodic.json": {"desc": "Memoria episódica — qué pasó, cuándo, contexto"},
        "long_term.json": {"desc": "Memoria largo plazo — notas, hábitos, preferencias"},
        "knowledge_graph.json": {"desc": "Grafo de entidades y relaciones"},
        "emotional_state.json": {"desc": "Estado emocional actual"},
    },

    "data": {
        "knowledge/": {"desc": "12+ archivos de conocimiento (.md) — CS, AI, idle learning", "count": "12+ files"},
        "chroma_db/": {"desc": "ChromaDB vector store — 36 chunks, 10 documentos"},
        "self/": {"desc": "Auto-conciencia — identity.json, self_log.json, metacognition.json, full_map.json"},
        "idle_learning.json": {"desc": "Estado aprendizaje idle — ciclos, temas, pool"},
        "autonomous_learn.json": {"desc": "Estado aprendizaje autónomo"},
    },

    "config": {
        "api_keys.json": {"desc": "API keys — Gemini, OpenRouter, Spotify"},
        "user_profile.json": {"desc": "Perfil de usuario"},
        "eris_state.json": {"desc": "Estado runtime ERIS"},
    },

    "context": {
        "AGENTS.md": {"desc": "Definición comportamiento — identidad, principios, capacidades"},
    },

    "tests": {
        "test_agent_router.py": {"desc": "Tests routing de agentes"},
        "test_emotional_state.py": {"desc": "Tests estado emocional"},
        "test_tool_registry.py": {"desc": "Tests registro herramientas"},
        "test_tool_declarations.py": {"desc": "Tests schemas herramientas"},
        "test_time_utils.py": {"desc": "Tests timezone"},
        "test_prompt_loader.py": {"desc": "Tests carga prompt"},
        "test_gpu_config.py": {"desc": "Tests config GPU"},
    },
}

# ─── Cambios recientes (edits de esta sesión) ────────────────────────────
RECENT_CHANGES = [
    {"file": "core/emotional_state.py", "change": "Fixed dead code + disk write issue", "date": "2026-07-24"},
    {"file": "core/tool_registry.py", "change": "Added retry logic + 102 tools registered", "date": "2026-07-24"},
    {"file": "core/agent_router.py", "change": "Improved scoring + penalty keywords", "date": "2026-07-24"},
    {"file": "core/rag_pipeline.py", "change": "Fixed to use llm_bridge for real embeddings", "date": "2026-07-24"},
    {"file": "core/llm_bridge.py", "change": "CREATED — Ollama embeddings via nomic-embed-text", "date": "2026-07-24"},
    {"file": "core/idle_learning_loop.py", "change": "CREATED — autonomous learning when idle", "date": "2026-07-24"},
    {"file": "core/autonomous_learner.py", "change": "CREATED — detect gaps, learn, expand, assess", "date": "2026-07-24"},
    {"file": "actions/computer_control.py", "change": "REWRITTEN — pyperclip, all native actions", "date": "2026-07-24"},
    {"file": "actions/file_controller.py", "change": "REWRITTEN — create, rename, edit, find, disk", "date": "2026-07-24"},
    {"file": "actions/browser_control.py", "change": "REWRITTEN — cleaned dead code, 14 actions", "date": "2026-07-24"},
    {"file": "actions/system_monitor.py", "change": "REWRITTEN — full monitor, fixed Unicode", "date": "2026-07-24"},
    {"file": "actions/screen_vision.py", "change": "Added Ollama local vision + fallback chain", "date": "2026-07-24"},
    {"file": "actions/document_rag.py", "change": "CREATED — RAG tool for LLM agent", "date": "2026-07-24"},
    {"file": "actions/knowledge_ingestor.py", "change": "CREATED — bulk knowledge ingestion", "date": "2026-07-24"},
    {"file": "actions/data_connectors.py", "change": "CREATED — HuggingFace, Wikidata, GitHub, data.gov", "date": "2026-07-24"},
    {"file": "core/prompt.txt", "change": "UPDATED — awareness, RAG rules, autonomous learning", "date": "2026-07-24"},
    {"file": "core/action_imports.py", "change": "Updated with new imports", "date": "2026-07-24"},
    {"file": "core/tool_declarations.py", "change": "Added new tool schemas", "date": "2026-07-24"},
    {"file": "actions/memory_consolidation.py", "change": "CREATED — memory cleanup/consolidation", "date": "2026-07-25"},
    {"file": "actions/email_manager.py", "change": "CREATED — IMAP/SMTP email full management", "date": "2026-07-25"},
    {"file": "actions/calendar_manager.py", "change": "CREATED — calendar events + Google Calendar sync", "date": "2026-07-25"},
    {"file": "actions/flow_recorder.py", "change": "CREATED — record/replay user macros", "date": "2026-07-25"},
    {"file": "actions/screenshot_history.py", "change": "CREATED — screenshot capture/search/history", "date": "2026-07-25"},
    {"file": "actions/clipboard_manager.py", "change": "CREATED — clipboard history + monitoring", "date": "2026-07-25"},
    {"file": "actions/multi_user.py", "change": "CREATED — multi-user profiles system", "date": "2026-07-25"},
    {"file": "actions/image_generation.py", "change": "REWRITTEN — full image gen with multiple providers", "date": "2026-07-25"},
    {"file": "actions/voice_cloning.py", "change": "CREATED — voice cloning + synthesis", "date": "2026-07-25"},
    {"file": "actions/browser_extension.py", "change": "CREATED — WebSocket server for browser extension", "date": "2026-07-25"},
    {"file": "actions/smart_notifications.py", "change": "CREATED — contextual intelligent notifications", "date": "2026-07-25"},
    {"file": "actions/usage_analytics.py", "change": "CREATED — tool usage stats and reporting", "date": "2026-07-25"},
    {"file": "actions/skill_marketplace.py", "change": "CREATED — publish/download/install skills", "date": "2026-07-25"},
    {"file": "actions/api_server.py", "change": "CREATED — REST API server for external apps", "date": "2026-07-25"},
    {"file": "actions/federated_learning.py", "change": "CREATED — local federated learning", "date": "2026-07-25"},
    {"file": "actions/file_organizer.py", "change": "CREATED — auto-organize files by type/date/size", "date": "2026-07-25"},
    {"file": "actions/data_encryption.py", "change": "CREATED — AES-256 data encryption", "date": "2026-07-25"},
    {"file": "actions/auto_backup.py", "change": "CREATED — auto-backup config, memory, knowledge", "date": "2026-07-26"},
    {"file": "actions/plugin_marketplace.py", "change": "CREATED — plugin marketplace + management", "date": "2026-07-26"},
    {"file": "actions/proactive_ia.py", "change": "CREATED — proactive intelligence, tasks, reminders", "date": "2026-07-26"},
    {"file": "actions/voice_enhanced.py", "change": "CREATED — wake word, voice profiles, TTS control", "date": "2026-07-26"},
    {"file": "actions/data_viz.py", "change": "CREATED — data visualization with matplotlib", "date": "2026-07-26"},
    {"file": "actions/i18n.py", "change": "CREATED — internationalization system", "date": "2026-07-26"},
    {"file": "actions/code_review.py", "change": "CREATED — automated code review, security scan", "date": "2026-07-26"},
    {"file": "actions/web_scraper.py", "change": "CREATED — advanced web scraping", "date": "2026-07-26"},
    {"file": "actions/dashboard_web.py", "change": "CREATED — web dashboard frontend", "date": "2026-07-26"},
    {"file": "actions/docker_deploy.py", "change": "CREATED — Docker deployment", "date": "2026-07-26"},
    {"file": "actions/ci_cd.py", "change": "CREATED — CI/CD automation", "date": "2026-07-26"},
    {"file": "actions/i18n_ui.py", "change": "CREATED — UI internationalization", "date": "2026-07-26"},
    {"file": "actions/voice_cloning_real.py", "change": "CREATED — real voice cloning with edge-tts", "date": "2026-07-26"},
    {"file": "actions/sandbox_execution.py", "change": "CREATED — sandboxed Python/JS execution", "date": "2026-07-26"},
    {"file": "actions/knowledge_graph.py", "change": "CREATED — RAG knowledge graph visualization", "date": "2026-07-26"},
    {"file": "actions/theme_manager.py", "change": "CREATED — Dark/Light/Midnight/Sunset/Forest themes", "date": "2026-07-26"},
    {"file": "actions/plugin_loader.py", "change": "CREATED — dynamic plugin loading + hot-reload", "date": "2026-07-26"},
    {"file": "actions/smart_cache.py", "change": "CREATED — LRU cache with TTL + persistence", "date": "2026-07-26"},
    {"file": "actions/config_export.py", "change": "CREATED — export/import full config as ZIP", "date": "2026-07-26"},
    {"file": "actions/desktop_notifications.py", "change": "CREATED — native Windows toast notifications", "date": "2026-07-26"},
    {"file": "core/tool_registry.py", "change": "Updated — 224 tools registered (batch 4 complete training)", "date": "2026-07-26"},
    {"file": "core/action_imports.py", "change": "Updated — batch 3 imports", "date": "2026-07-26"},
    {"file": "actions/desktop.py", "change": "REWRITTEN v2 — 28 actions with STATE TRACKING (open/minimize/close memory, get_state, get_opened, get_minimized, get_closed, is_open, what_did_i_do)", "date": "2026-07-26"},
    {"file": "actions/youtube_video.py", "change": "REWRITTEN — 20+ actions: play_direct (reproduce directo por URL/ID/nombre), play, search, search_and_play, playlist, batch_info, pause/resume/fullscreen/mute/next/prev/stop, open, trending, recent", "date": "2026-07-26"},
    {"file": "actions/web_search.py", "change": "REWRITTEN — 8 actions: search (Google+DDG auto-fallback), news, images, videos, definition, local, open, history", "date": "2026-07-26"},
    {"file": "actions/computer_control.py", "change": "FIXED — _type_text clear_first default changed from True to False (no longer overwrites content)", "date": "2026-07-26"},
    {"file": "core/tool_declarations.py", "change": "ADDED super_search, web_navigation, document_handler declarations. UPDATED youtube_video (8 actions), web_search (8 actions)", "date": "2026-07-26"},
    {"file": "actions/document_handler.py", "change": "CREATED — 24 actions: create Word/PPTX/Excel/PDF/TXT/CSV, read any format, convert to PDF, merge/split PDF, summarize/translate/interpret, open, what_i_wrote memory", "date": "2026-07-26"},
    # ── Batch 5: Connectivity + Self-Healing ──
    {"file": "core/connectivity.py", "change": "CREATED — Internet auto-detect + online/offline mode switcher (ConnectivityMonitor, background thread)", "date": "2026-07-26"},
    {"file": "core/offline_voice.py", "change": "CREATED — Offline voice pipeline (Vosk STT + Ollama chat + local TTS, 100% offline)", "date": "2026-07-26"},
    {"file": "core/self_healing.py", "change": "CREATED — Auto-healing, auto-learning, health monitoring, syntax check/fix, error tracking, learning log", "date": "2026-07-26"},
    {"file": "main.py", "change": "UPDATED — Connectivity/offline mode init, auto-switch handlers, offline TTS fallback, health check", "date": "2026-07-26"},
    {"file": "core/tool_declarations.py", "change": "UPDATED — Added connectivity + self_healing declarations (192 total)", "date": "2026-07-26"},
    {"file": "core/action_imports.py", "change": "UPDATED — Added imports for connectivity, self_healing (68 modules)", "date": "2026-07-26"},
    {"file": "core/tool_registry.py", "change": "UPDATED — 226 tools registered (224 + connectivity + self_healing)", "date": "2026-07-26"},
]


# ─── PUBLIC API ──────────────────────────────────────────────────────────

def get_full_map(parameters: dict = None, player=None) -> str:
    """ERIS obtiene su mapa completo de sí misma."""
    result = []
    result.append("═" * 60)
    result.append("  ERIS SELF-MAP v2.0 — Mapa completo")
    result.append("═" * 60)
    result.append("  Raíz: {}".format(_BASE))
    result.append("  Versión: 2.0")
    result.append("  Fecha: {}".format(datetime.now().strftime("%Y-%m-%d %H:%M")))
    result.append("")

    # Entry points
    result.append("── ENTRY POINTS ──")
    for name, info in ERIS_MAP["entry_points"].items():
        result.append("  {} — {} ({} lines)".format(name, info["desc"], info.get("lines", "?")))

    # Core
    result.append("\n── CORE (motor principal) ──")
    for name, info in ERIS_MAP["core"].items():
        recent = " ★NUEVO" if info.get("recently_created") or info.get("recently_updated") or info.get("recently_fixed") else ""
        result.append("  core/{} — {}{}".format(name, info["desc"], recent))

    # Actions
    result.append("\n── ACTIONS (acciones/herramientas) ──")
    for name, info in ERIS_MAP["actions"].items():
        recent = " ★NUEVO" if info.get("recently_created") or info.get("recently_rewritten") or info.get("recently_added_local_vision") or info.get("recently_enhanced") else ""
        result.append("  actions/{} — {}{}".format(name, info["desc"], recent))

    # Agents
    result.append("\n── AGENTS (agentes especializados) ──")
    for name, info in ERIS_MAP["agents"].items():
        result.append("  agents/{} — {}".format(name, info["desc"]))

    # BIOS
    result.append("\n── BIOS (boot y recovery) ──")
    for name, info in ERIS_MAP["bios"].items():
        result.append("  bios/{} — {}".format(name, info["desc"]))

    # Memory
    result.append("\n── MEMORY (sistemas de memoria) ──")
    for name, info in ERIS_MAP["memory"].items():
        result.append("  memory/{} — {}".format(name, info["desc"]))

    # Data
    result.append("\n── DATA (datos y conocimiento) ──")
    for name, info in ERIS_MAP["data"].items():
        result.append("  data/{} — {}".format(name, info["desc"]))

    # Recent changes
    result.append("\n── CAMBIOS RECIENTES (esta sesión) ──")
    for ch in RECENT_CHANGES:
        result.append("  [{}] {} — {}".format(ch["date"], ch["file"], ch["change"]))

    result.append("\n═" * 60)
    result.append("  Total: ~220+ archivos .py, 226 herramientas, ~50,000+ LOC")
    result.append("═" * 60)

    # Save to file for reference
    _ensure_dirs()
    _SELF_MAP_FILE.write_text(json.dumps(ERIS_MAP, indent=2, ensure_ascii=False), encoding="utf-8")

    return "\n".join(result)


def get_file_tree(parameters: dict = None, player=None) -> str:
    """ERIS lista TODOS sus archivos."""
    result = []
    result.append("ERIS File Tree — {}\n".format(_BASE))

    for root, dirs, files in os.walk(str(_BASE)):
        # Skip unwanted dirs
        skip = ["__pycache__", ".git", "build", "ERIS_AI.egg-info", "node_modules", "venv", "src_clean"]
        dirs[:] = [d for d in dirs if d not in skip]

        level = root.replace(str(_BASE), "").count(os.sep)
        indent = "  " * level
        dirname = os.path.basename(root) or str(_BASE)
        result.append("{}{}/".format(indent, dirname))

        subindent = "  " * (level + 1)
        for f in sorted(files):
            if f.endswith((".pyc", ".pyd")):
                continue
            filepath = Path(root) / f
            try:
                size = filepath.stat().st_size
                if size > 1024:
                    size_str = "{:.1f}KB".format(size / 1024)
                else:
                    size_str = "{}B".format(size)
                result.append("{}{} ({})".format(subindent, f, size_str))
            except Exception:
                result.append("{}{}".format(subindent, f))

    return "\n".join(result)


def get_recent_changes(parameters: dict = None, player=None) -> str:
    """ERIS lista sus cambios recientes."""
    result = ["Cambios recientes en ERIS:\n"]
    for ch in RECENT_CHANGES:
        result.append("[{}] {}".format(ch["date"], ch["file"]))
        result.append("  → {}".format(ch["change"]))
        result.append("")
    return "\n".join(result)


def get_capabilities(parameters: dict = None, player=None) -> str:
    """ERIS lista TODAS sus capacidades."""
    caps = []
    caps.append("═" * 60)
    caps.append("  CAPACIDADES COMPLETAS DE ERIS")
    caps.append("═" * 60)

    categories = {
        "Control del Sistema": [
            "Control nativo (click, type, hotkeys, scroll, mouse)",
            "Gestión de ventanas (multi-monitor, resize, snap)",
            "Monitor de sistema (CPU, RAM, disco, red, GPU, batería)",
            "Lanzador de aplicaciones (Start Menu, PATH, Registry)",
            "Configuraciones de Windows (volumen, brillo, WiFi)",
            "Organizador de archivos (crear, mover, renombrar, buscar)",
            "Procesamiento de documentos (PDF, Word, Excel)",
            "Control del navegador (navegar, buscar, click, leer)",
            "Control de Spotify (play, pause, next, playlists)",
        ],
        "Visión y Percepción": [
            "Análisis de pantalla (screenshot + Gemini/Ollama vision)",
            "Lectura de pantalla (texto OCR)",
            "Visión local (Ollama minicpm-v, sin internet)",
            "Mouse humano (Bezier curves, variable speed)",
        ],
        "Voz y Comunicación": [
            "Escucha continua (OpenWakeWord + Google STT)",
            "Text-to-speech (Edge TTS, voces naturales)",
            "Gemini Live (audio nativo bidireccional)",
            "Traducción en tiempo real",
        ],
        "Conocimiento y Aprendizaje": [
            "RAG pipeline (ChromaDB + embeddings 768-dim)",
            "Base de conocimiento local (vector search)",
            "Ingesta masiva (archivos, URLs, texto, batch)",
            "Conectores externos (HuggingFace, Wikidata, GitHub)",
            "Motor de curiosidad (100+ temas)",
            "Profesor de inglés (A1-C2)",
            "Profesor de ciberseguridad",
            "Investigación autónoma (web search + ingest)",
        ],
        "Aprendizaje Autónomo": [
            "Aprende SOLO cuando idle (cada 30 min)",
            "Detecta gaps de conocimiento",
            "Investiga temas del pool (20 temas curados)",
            "Guarda en Obsidian + RAG + semantic memory",
            "Auto-evalúa lo que aprende",
            "Expande base de conocimiento automáticamente",
        ],
        "Memoria": [
            "Memoria semántica (hechos, conceptos)",
            "Memoria episódica (qué pasó, cuándo)",
            "Memoria de trabajo (conversación activa)",
            "Memoria largo plazo (notas, hábitos)",
            "Knowledge graph (entidades y relaciones)",
            "Obsidian segundo cerebro (vault completo)",
        ],
        "Auto-Conciencia": [
            "Conoce TODO su código fuente (170+ archivos)",
            "Sabe qué archivos existen y qué hacen",
            "Sabe qué cambios se hicieron recientemente",
            "Auto-análisis (introspect, metacognition)",
            "Diario interno (self_log.json)",
            "Identidad persistente (identity.json)",
        ],
        "Auto-Modificación": [
            "Puede LEER cualquier archivo de su código",
            "Puede EDITAR sus propios archivos (con backup)",
            "Puede CREAR nuevos módulos y herramientas",
            "Puede auto-reparar bugs (self_heal.py)",
            "Puede auto-mejorar (self_improvement.py)",
            "Puede auto-generar herramientas (auto_programmer.py)",
        ],
        "Seguridad": [
            "Scanner de seguridad (Defender, PowerShell)",
            "OSINT (inteligencia de fuentes abiertas)",
            "Auto-protección (self_protection.py)",
            "Self-healing (auto-reparación con validación)",
        ],
        "Conectividad y Auto-Switch": [
            "Detección automática de internet (cada 5s)",
            "Cambio automático Online/Offline",
            "Notificación al usuario cuando cambia de modo",
            "Pipeline offline: Vosk STT + Ollama + Kokoro TTS",
        ],
        "Auto-Healing y Auto-Aprendizaje": [
            "Health check cada 5 minutos (Ollama, ChromaDB, syntax)",
            "Auto-detección y auto-fix de errores de código",
            "Log de errores para análisis futuro",
            "Aprendizaje de cada interacción del usuario",
            "Reinicio automático de subsistemas caídos",
        ],
        "Agentes Especializados": [
            "Vision Agent — análisis visual",
            "Search Agent — búsqueda inteligente",
            "Security Agent — seguridad del sistema",
            "System Agent — monitoreo y control",
            "Media Agent — Spotify, YouTube, TikTok",
            "Productivity Agent — calendario, email, docs",
            "Dev Agent — código, git, knowledge base",
        ],
    }

    for cat, items in categories.items():
        caps.append("\n▸ {}".format(cat))
        for item in items:
            caps.append("  • {}".format(item))

    caps.append("\n═" * 60)
    caps.append("  226 herramientas | ~220 archivos | ~50,000 LOC")
    caps.append("═" * 60)

    return "\n".join(caps)


def search_my_code(parameters: dict = None, player=None) -> str:
    """ERIS busca en su propio código fuente."""
    query = parameters.get("query", "") if parameters else ""
    if not query:
        return "Error: Se requiere 'query'."

    results = []
    search_dirs = [_BASE / "core", _BASE / "actions", _BASE / "agents", _BASE / "bios"]

    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        for py_file in search_dir.glob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8", errors="replace")
                lines = content.split("\n")
                for i, line in enumerate(lines, 1):
                    if query.lower() in line.lower():
                        rel = str(py_file.relative_to(_BASE))
                        results.append("{}:{}: {}".format(rel, i, line.strip()[:120]))
                        if len(results) >= 30:
                            break
            except Exception:
                continue
            if len(results) >= 30:
                break
        if len(results) >= 30:
            break

    if not results:
        return "No encontré '{}' en el código de ERIS.".format(query)

    return "Búsqueda '{}' — {} resultados:\n{}".format(
        query, len(results), "\n".join(results[:30])
    )


def _ensure_dirs():
    (_BASE / "data" / "self").mkdir(parents=True, exist_ok=True)
