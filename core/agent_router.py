"""
agent_router.py — ERIS Multi-Agent Handoff System.
Routes user intents to specialized agents automatically.
Inspired by OpenAI Agents SDK handoff pattern.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable, Optional

_BASE = Path(__file__).resolve().parent.parent
_REGISTRY_PATH = _BASE / "core" / "agent_registry.json"

# ── Agent definitions ─────────────────────────────────────────────────────────

# Each agent has:
#   name: unique identifier
#   description: what it does (shown to router for classification)
#   keywords: trigger words/phrases for routing
#   tools: list of tool names this agent handles
#   handler: function to call (registered at runtime)

AGENT_DEFINITIONS = {
    # ── 1. CORE — System basics, apps, desktop, settings ──
    "core": {
        "name": "CoreAgent",
        "description": "Operaciones básicas: abrir apps, escritorio, ventanas, volumen, clipboard, sistema, calculator, screenshots",
        "keywords": [
            "abrir", "abre", "abri", "iniciar", "lanzar", "ejecutar app",
            "escritorio", "desktop", "ventana", "window", "minimizar", "maximizar",
            "volumen", "sonido", "audio", "mute", "silenciar",
            "clipboard", "copiar", "pegar", "portapapeles",
            "monitor", "sistema", "cpu", "ram", "disco", "procesos",
            "configuracion", "settings", "config",
            "calculadora", "calc", "notepad", "bloc de notas",
            "captura", "screenshot", "pantalla",
            "control", "pc", "computadora",
        ],
        "penalty_keywords": [
            "spotify", "musica", "codigo", "git", "virus", "email",
            "calendario", "documento", "buscar", "browser",
        ],
        "tools": [
            "open_app", "app_discovery", "desktop_control", "window_manager",
            "system_monitor", "system_volume", "computer_settings", "computer_control",
            "clipboard_manager", "screen_control", "screen_see", "shell_executor",
            "process_manager", "action_history", "windows_settings", "driver_manager",
            "pc_control", "quick_actions", "context_menu", "desktop_notifications",
        ],
    },

    # ── 2. WEB — Search, browse, fetch, research ──
    "web": {
        "name": "WebAgent",
        "description": "Búsqueda web, navegación, scraping, investigación profunda, fetch de páginas",
        "keywords": [
            "buscar", "busca", "buscá", "search", "google", "encontrar",
            "navegador", "browser", "abrir pagina", "web", "sitio",
            "scraping", "scrapear", "extraer", "raspar",
            "investigar", "investiga", "research", "profundo", "deep",
            "url", "enlace", "link", "pagina", "page",
            "resumir pagina", "resumen web", "summarize",
            "fetch", "contenido web",
            "duckduckgo", "ddg", "bing",
        ],
        "penalty_keywords": [
            "spotify", "musica", "codigo", "git", "virus",
            "calendario", "email", "documento", "abrir app",
        ],
        "tools": [
            "web_search", "super_search", "deep_research", "webfetch",
            "web_navigation", "browser_control", "browser_auto", "browser_unified",
            "page_summarizer", "smart_browser", "web_scraper", "multi_search",
            "search_info", "research", "rss_reader", "browser_history",
        ],
    },

    # ── 3. FILE — File operations, editing, AST, organization ──
    "file": {
        "name": "FileAgent",
        "description": "Operaciones con archivos: leer, escribir, editar, organizar, buscar, copiar, mover",
        "keywords": [
            "archivo", "carpeta", "directorio", "folder", "file",
            "leer archivo", "escribir archivo", "editar archivo",
            "copiar archivo", "mover archivo", "renombrar", "eliminar archivo",
            "buscar archivo", "encontrar archivo", "listar archivos",
            "organizar archivos", "organiza",
            "backup", "respaldo", "copia de seguridad",
        ],
        "penalty_keywords": [
            "spotify", "musica", "virus", "email", "calendario",
            "codigo", "git", "navegador", "browser",
        ],
        "tools": [
            "file_api", "file_manager", "file_editor", "file_processor",
            "file_controller", "ast_analyze", "ast_edit",
            "smart_file_organizer", "file_organizer", "file_monitor",
            "file_profiler", "backup_system", "auto_backup",
            "save_everywhere", "clipboard_history",
        ],
    },

    # ── 4. DEV — Code, git, programming, DevOps ──
    "dev": {
        "name": "DevAgent",
        "description": "Programación, código, git, codebase, DevOps, refactoring, testing, creación de scripts/proyectos",
        "keywords": [
            "codigo", "code", "programar", "programa", "script",
            "funcion", "function", "clase", "class", "metodo",
            "git", "commit", "push", "pull", "branch", "repositorio", "repo",
            "python", "javascript", "html", "css", "react", "node",
            "compilar", "compile", "build", "npm", "pip",
            "debug", "error", "bug", "fix", "arreglar codigo",
            "refactor", "refactorizar", "optimizar codigo",
            "test", "testing", "prueba", "unittest",
            "docker", "deploy", "desplegar", "ci/cd",
            "downloader", "scraper", "bot", "proyecto",
            "dependencias", "instalar paquete", "requirements",
            "crear archivo", "creá archivo", "escribir archivo",
            "hacer un programa", "hacé un programa", "make a",
        ],
        "penalty_keywords": [
            "spotify", "virus", "calendario", "email",
            "pantalla", "screenshot", "volumen", "brillo",
            "reproducir", "cancion", "playlist",
        ],
        "tools": [
            "code_helper", "code_generator", "code_analyzer", "code_review",
            "code_engineer", "codebase_explorer", "code_validator",
            "git_control", "git_smart", "git_daily", "github_pr",
            "devops_pipeline", "refactoring_engine", "test_generator",
            "dependency_manager", "vscode_controller", "dev_agent",
            "web_generator", "web_designer", "react_designer",
            "angular_designer", "vue_designer", "next_designer",
            "tool_creator", "code_sandbox", "shell_session",
        ],
    },

    # ── 5. MEDIA — Music, YouTube, images, entertainment ──
    "media": {
        "name": "MediaAgent",
        "description": "Música, YouTube, generación de imágenes, entretenimiento, games",
        "keywords": [
            "musica", "music", "spotify", "cancion", "song", "playlist",
            "youtube", "video", "yt", "descargar video",
            "imagen", "image", "foto", "dibujar", "generar imagen",
            "juego", "game", "gaming", "jugar",
            "tiktok", "reel", "short",
            "radio", "podcast", "audio",
            "pelicula", "movie", "serie", "anime",
        ],
        "penalty_keywords": [
            "calendario", "email", "codigo", "git", "virus",
            "instalar", "archivo", "carpeta", "buscar",
        ],
        "tools": [
            "music_player", "play_direct", "spotify_control",
            "youtube_video", "image_generation", "image_generator",
            "image_analyzer", "video_analyzer", "game_companion",
            "game_agent", "game_launcher", "audio_transcriber",
            "voice_recognition", "tts_set_voice",
        ],
    },

    # ── 6. COMM — Email, calendar, messaging, documents ──
    "comm": {
        "name": "CommAgent",
        "description": "Email, calendario, mensajería, documentos, notificaciones, productividad",
        "keywords": [
            "email", "correo", "gmail", "mail", "enviar mensaje",
            "calendario", "calendar", "evento", "reunion", "meeting",
            "whatsapp", "telegram", "sms", "mensaje",
            "documento", "document", "pdf", "word", "excel", "powerpoint",
            "notificacion", "notification", "alerta",
            "recordatorio", "reminder", "alarma",
            "tarea", "task", "todo", "pendiente",
            "agenda", "schedule", "planificar",
            "hoja de calculo", "spreadsheet", "presentacion",
        ],
        "penalty_keywords": [
            "spotify", "youtube", "virus", "codigo", "git",
            "pantalla", "screenshot", "volumen", "abrir app",
        ],
        "tools": [
            "email_manager", "gmail_control", "send_message", "send_sms",
            "whatsapp", "whatsapp_web", "telegram_bot",
            "google_calendar", "calendar_manager", "reminder", "reminders",
            "document_creator", "document_handler", "document_manager", "document_tool",
            "document_generator", "document_rag",
            "presentation_generator", "spreadsheet_generator",
            "pdf_editor", "pdf_manager", "pdf_generator",
            "office_docs", "notification_center", "notifications",
            "task_manager", "task_scheduler", "goals",
            "scheduler", "alarm_manager", "meeting_transcriber",
            "obsidian_note", "i18n",
        ],
    },

    # ── 7. VISION — Screen analysis, OCR, images, perception ──
    "vision": {
        "name": "VisionAgent",
        "description": "Análisis de pantalla, OCR, visión por computadora, análisis de imágenes",
        "keywords": [
            "ver pantalla", "que se ve", "que hay en pantalla",
            "capturar pantalla", "screenshot para analizar",
            "ocr", "leer texto imagen", "texto en imagen",
            "analizar imagen", "analizar foto", "que hay en la foto",
            "vision", "ver imagen", "mirar imagen",
            "reconocer texto", "detectar", "identificar imagen",
            "cámara", "camera", "webcam", "vigilancia",
        ],
        "penalty_keywords": [
            "spotify", "musica", "virus", "email", "calendario",
            "codigo", "git", "navegador", "abrir app",
        ],
        "tools": [
            "screen_vision", "image_analyzer", "ocr_reader",
            "screen_see", "camera_bus", "vision_guardian",
            "screen_context", "screen_recorder",
        ],
    },

    # ── 8. SECURITY — Scanning, firewall, protection ──
    "security": {
        "name": "SecurityAgent",
        "description": "Seguridad del sistema, escaneo, firewall, protección, criptografía, OSINT",
        "keywords": [
            "seguridad", "security", "escanear", "scan", "virus", "malware",
            "firewall", "proteccion", "protect", "amenaza", "threat",
            "encriptar", "encrypt", "cifrar", "descifrar",
            "contraseña", "password", "credential", "clave",
            "hack", "vulnerabilidad", "vulnerability",
            "osint", "investigar persona", "whois",
            "usb", "dispositivo", "periferico",
            "ransomware", "spyware",
            "instalar programa", "desinstalar programa",
        ],
        "penalty_keywords": [
            "spotify", "youtube", "calendario", "email",
            "pantalla", "screenshot", "volumen", "brillo",
        ],
        "tools": [
            "security_scanner", "security_shield", "eris_guardian",
            "active_firewall", "ransomware_shield", "self_protection",
            "osint_agent", "cybersecurity", "credential_recovery",
            "keylogger_detector", "usb_monitor", "darkweb_monitor",
            "disk_wiper", "file_encryptor", "program_manager",
        ],
    },

    # ── 9. STUDY — Aprendizaje, explicaciones, planes, quizzes ──
    "study": {
        "name": "StudiesAgent",
        "description": "Estudios y aprendizaje: explica conceptos, resume material, arma planes de estudio, genera quizzes y flashcards, guarda notas de estudio",
        "keywords": [
            "explica", "explicame", "explicá", "qué es", "que es", "que son",
            "explicar", "define", "sobre", "acerca de", "contame",
            "estudiar", "estudio", "aprender", "aprendizaje",
            "plan de estudio", "plan de estudios", "cronograma",
            "resume", "resumi", "resumen", "sintetiza",
            "quiz", "flashcard", "repaso", "examen", "evaluame", "autoevaluaci",
            "anota", "anotá", "apunte", "nota de estudio", "material de estudio",
            "tesis", "materia", "facultad", "universidad", "clase", "carrera",
        ],
        "penalty_keywords": [
            "spotify", "youtube", "virus", "email", "calendario",
            "pantalla", "screenshot", "volumen", "abrir app",
        ],
        "tools": [
            "web_search", "super_search", "deep_research", "webfetch",
            "file_api", "file_manager", "save_memory",
            "db_tasks", "task_scheduler", "reminders",
            "document_creator", "document_generator", "pdf_generator",
        ],
    },
}

# ── Registry management ───────────────────────────────────────────────────────

def _load_registry() -> dict:
    """Load agent registry from disk."""
    try:
        if _REGISTRY_PATH.exists():
            return json.loads(_REGISTRY_PATH.read_text("utf-8"))
    except Exception:
        pass
    return {"agents": {}, "handoff_count": 0, "last_handoff": None}

def _save_registry(registry: dict):
    """Save agent registry to disk."""
    try:
        _REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
        _REGISTRY_PATH.write_text(json.dumps(registry, indent=2, ensure_ascii=False), "utf-8")
    except Exception as e:
        print(f"[AgentRouter] Registry save error: {e}")

# ── Router ────────────────────────────────────────────────────────────────────

class AgentRouter:
    """Routes user intents to specialized agents."""

    def __init__(self):
        self._handlers: dict[str, Callable] = {}
        self._registry = _load_registry()
        self._register_builtin_agents()

    def _register_builtin_agents(self):
        """Register all builtin agent definitions."""
        for agent_key, agent_def in AGENT_DEFINITIONS.items():
            self._registry["agents"][agent_key] = {
                "name": agent_def["name"],
                "description": agent_def["description"],
                "keywords": agent_def["keywords"],
                "tools": agent_def["tools"],
                "enabled": True,
            }
        _save_registry(self._registry)

    def register_handler(self, agent_key: str, handler: Callable):
        """Register a handler function for an agent."""
        self._handlers[agent_key] = handler
        print(f"[AgentRouter] Registered handler for {agent_key}")

    def classify_intent(self, text: str) -> Optional[str]:
        """
        Classify user text into an agent key using weighted scoring.
        Improvements over pure keyword matching:
        - Multi-word phrases get bonus weight
        - Exact phrase matches scored higher than substring
        - Penalty keywords reduce false positives
        - Recent handoff context prevents agent bouncing
        - Accent normalization (creá → crear)
        Returns None if no agent matches (handled by main ERIS).
        """
        import unicodedata
        def _norm(s):
            nfkd = unicodedata.normalize('NFKD', s)
            return ''.join(c for c in nfkd if not unicodedata.combining(c))

        text_lower = text.lower()
        text_norm = _norm(text_lower)
        scores: dict[str, float] = {}

        for agent_key, agent_info in self._registry.get("agents", {}).items():
            if not agent_info.get("enabled", True):
                continue

            score = 0.0
            for keyword in agent_info.get("keywords", []):
                kw_lower = keyword.lower()
                kw_norm = _norm(kw_lower)
                matched = False
                # Try normalized match first (handles accents: creá → crear)
                if kw_norm in text_norm:
                    matched = True
                elif kw_lower in text_lower:
                    matched = True

                if matched:
                    # Base weight: longer keywords are more specific
                    base = max(len(kw_lower), len(kw_norm))
                    # Bonus for exact word boundary matches (not substring)
                    if f" {kw_norm} " in f" {text_norm} " or text_norm.startswith(kw_norm) or text_norm.endswith(kw_norm):
                        base *= 1.5
                    # Bonus for multi-word phrases (more specific = more reliable)
                    if " " in kw_lower:
                        base *= 2.0
                    score += base

            # Penalty keywords: if present, reduce this agent's score
            for penalty_kw in agent_info.get("penalty_keywords", []):
                pen_norm = _norm(penalty_kw.lower())
                if pen_norm in text_norm or penalty_kw.lower() in text_lower:
                    score *= 0.3

            if score > 0:
                scores[agent_key] = score

        if not scores:
            return None

        # Sort by score descending
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        best_agent, best_score = ranked[0]

        # Minimum threshold
        if best_score < 3:
            return None

        # Disambiguation: if top two are close (within 20%), prefer the one
        # that was NOT used most recently to prevent agent bouncing
        if len(ranked) >= 2:
            second_agent, second_score = ranked[1]
            if second_score >= best_score * 0.8:
                last_agent = self._registry.get("last_handoff", {})
                if isinstance(last_agent, dict) and last_agent.get("agent") == best_agent:
                    # Top agent was used recently, prefer the runner-up
                    return second_agent

        return best_agent

    def route(self, text: str, agent_key: str, **kwargs) -> Any:
        """Route a request to the appropriate agent handler."""
        if agent_key not in self._handlers:
            return f"[AgentRouter] No handler registered for agent: {agent_key}"

        t0 = time.perf_counter()
        try:
            handler = self._handlers[agent_key]
            result = handler(text, **kwargs)

            elapsed = time.perf_counter() - t0

            # Update registry stats
            self._registry["handoff_count"] = self._registry.get("handoff_count", 0) + 1
            self._registry["last_handoff"] = {
                "agent": agent_key,
                "text": text[:100],
                "elapsed": round(elapsed, 2),
                "timestamp": time.time(),
            }
            _save_registry(self._registry)

            print(f"[AgentRouter] Handoff to {agent_key}: {elapsed:.2f}s")
            return result

        except Exception as e:
            print(f"[AgentRouter] Handoff error for {agent_key}: {e}")
            return f"[AgentRouter] Error delegating a {agent_key}: {e}"

    def get_agent_list(self) -> list[dict]:
        """Get list of available agents."""
        agents = []
        for key, info in self._registry.get("agents", {}).items():
            agents.append({
                "key": key,
                "name": info["name"],
                "description": info["description"],
                "enabled": info.get("enabled", True),
                "handler_registered": key in self._handlers,
            })
        return agents

    def get_stats(self) -> dict:
        """Get router statistics."""
        return {
            "handoff_count": self._registry.get("handoff_count", 0),
            "last_handoff": self._registry.get("last_handoff"),
            "agents_available": len(self._registry.get("agents", {})),
            "handlers_registered": len(self._handlers),
        }

    def toggle_agent(self, agent_key: str, enabled: bool) -> str:
        """Enable or disable an agent."""
        if agent_key not in self._registry.get("agents", {}):
            return f"Agente no encontrado: {agent_key}"

        self._registry["agents"][agent_key]["enabled"] = enabled
        _save_registry(self._registry)
        status = "habilitado" if enabled else "deshabilitado"
        return f"Agente {agent_key} {status}."


# ── Singleton ─────────────────────────────────────────────────────────────────

_router: Optional[AgentRouter] = None

def get_router() -> AgentRouter:
    global _router
    if _router is None:
        _router = AgentRouter()
    return _router
