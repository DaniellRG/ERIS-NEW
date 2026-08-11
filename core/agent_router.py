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
    "vision": {
        "name": "VisionAgent",
        "description": "Handles all image and screen analysis: screenshots, uploaded images, vision monitoring, game screenshots, Ollama vision fallback.",
        "keywords": [
            "pantalla", "screen", "imagen", "image", "foto", "photo", "captura",
            "screenshot", "vision", "ver", "mirar", "analizar imagen", "describe la imagen",
            "que ves", "que hay en", "guardian", "vigila", "game screenshot",
            "ollama vision", "llava", "vision local", "modo gaming", "juego pantalla",
            "camara", "camera", "webcam", "vigilancia", "mirar por la camara",
            "que ves por la camara", "que hay por la camara", "detectar movimiento"
        ],
        "tools": [
            "screen_vision", "image_analyzer", "vision_guardian",
            "game_companion", "ollama_vision", "camera_bus"
        ],
    },
    "home": {
        "name": "HomeAgent",
        "description": "Handles smart home and domotics: lights, climate, TV, scenes via Home Assistant, MQTT or simulation.",
        "keywords": [
            "domotica", "smart home", "luces", "luz de", "apaga la luz", "enciende la luz",
            "prende la luz", "apagar la luz", "encender la luz", "aire acondicionado",
            "apaga todo", "encender", "apagar", "escena", "temperatura de la",
            "dispositivos inteligentes", "casa inteligente", "camara de entrada"
        ],
        "penalty_keywords": [
            "musica", "music", "cancion", "youtube", "video", "spotify",
            "pantalla", "brillo", "codigo", "git",
        ],
        "tools": [
            "smart_home"
        ],
    },
    "reverse": {
        "name": "ReverseEngineeringAgent",
        "description": "Handles reverse engineering: binary analysis, disassembly, strings, hashes, PE analysis, hexdump, entropy, black-box testing, malware triage.",
        "keywords": [
            "ingenieria inversa", "reverse engineering", "desensamblar", "disassembler",
            "desensamblado", "hexdump", "hex dump", "analizar binario", "binario",
            "analizar ejecutable", "ejecutable", "extraer strings", "strings",
            "analizar malware", "malware", "triage", "entropia", "caja negra",
            "black box", "pe info", "analizar exe", "analizar dll", "huellas del archivo"
        ],
        "penalty_keywords": [
            "spotify", "musica", "youtube", "instalar", "desinstalar", "codigo", "git",
        ],
        "tools": [
            "reverse_engineering"
        ],
    },
    "self": {
        "name": "SelfEvolutionAgent",
        "description": "Handles ERIS self-evolution: reflection, consciousness simulation, lessons learned, personal goals, experiences and identity.",
        "keywords": [
            "reflexiona", "reflexionar", "conciencia", "evoluciona", "evolucionar",
            "mejorarte", "mejorame", "aprende de tus errores", "que has aprendido",
            "tu existencia", "autoconocimiento", "auto-mejora", "crecimiento",
            "que piensas de ti", "como te sientes", "que has aprendido de mi",
            "tus metas", "tu evolucion", "eris evoluciona"
        ],
        "penalty_keywords": [
            "spotify", "musica", "youtube", "codigo", "git", "virus",
            "instalar", "pantalla", "screenshot",
        ],
        "tools": [
            "self_evolution"
        ],
    },
    "search": {
        "name": "SearchAgent",
        "description": "Handles all search operations: web search, file search, session search, super search, HuggingFace models/datasets.",
        "keywords": [
            "busca", "buscar", "search", "encontrar", "find", "donde esta",
            "donde queda", "sesiones anteriores", "historial", "buscar archivo",
            "buscar en mis sesiones", "super search", "search file",
            "huggingface", "hugging face", "dataset", "modelo ia", "ia modelo"
        ],
        "penalty_keywords": [
            "virus", "malware", "seguridad", "instalar", "desinstalar",
            "spotify", "youtube", "calendario", "email", "codigo", "git",
        ],
        "tools": [
            "web_search", "super_search", "deep_research", "session_search",
            "huggingface", "research"
        ],
    },
    "security": {
        "name": "SecurityAgent",
        "description": "Handles security scanning, program installation/uninstallation with safety gates.",
        "keywords": [
            "escanear", "scan", "virus", "malware", "seguridad", "security",
            "instalar", "install", "desinstalar", "uninstall", "programa",
            "aplicacion", "app", "winget", "choco", "defender", "usb scan",
            "instalar programa", "quitar programa",
            # Linux keywords
            "apt", "dnf", "pacman", "flatpak", "snap",
            "clamav", "rkhunter", "chkrootkit",
            "instalar apt", "instalar flatpak", "instalar snap",
        ],
        "penalty_keywords": [
            "spotify", "youtube", "calendario", "email", "codigo", "git",
            "pantalla", "screenshot", "volumen", "brillo",
        ],
        "tools": [
            "security_scanner", "program_manager"
        ],
    },
    "system": {
        "name": "SystemAgent",
        "description": "Handles system operations: computer control, desktop automation, system monitoring, Windows/Linux settings, Hyprland, Omarchy.",
        "keywords": [
            "computadora", "computer", "sistema", "system", "escritorio", "desktop",
            "ventana", "window", "configuracion", "settings", "monitor", "cpu",
            "ram", "memoria", "disco", "disk", "bateria", "battery", "red", "network",
            "abrir app", "cerrar app", "minimizar", "maximizar", "teclado",
            "mouse", "click", "escribir", "typing", "volumen", "brillo",
            "como esta el sistema", "estado del sistema", "estado del cpu",
            "hyprland", "omarchy", "workspace", "monitor", "tema", "fondo de pantalla",
            "wallpaper", "captura", "screenshot", "grabar pantalla", "tema",
            "linux", "linux settings", "pipewire", "wpctl", "notify-send",
            "bluetooth", "wifi", "nmcli", "brightnessctl", "pactl", "paru", "pacman"
        ],
        "penalty_keywords": [
            "spotify", "youtube", "calendario", "email", "codigo", "git",
            "virus", "instalar programa", "desinstalar programa",
        ],
        "tools": [
            "computer_control", "desktop_control", "system_monitor",
            "windows_settings", "computer_settings", "accessibility",
            "screen_reader", "accessibility_overlay",
            "linux_settings", "hyprland_control", "omarchy_control",
            "shell_executor",
            "file_organizer", "file_monitor", "smart_file_organizer"
        ],
    },
    "media": {
        "name": "MediaAgent",
        "description": "Handles media: Spotify, YouTube, image generation, TikTok analysis.",
        "keywords": [
            "spotify", "musica", "music", "cancion", "song", "playlist",
            "youtube", "video", "tiktok", "generar imagen", "generate image",
            "crear imagen", "reproducir", "play", "pausar", "pause",
            "siguiente", "next", "anterior", "previous", "volumen musica"
        ],
        "penalty_keywords": [
            "calendario", "email", "codigo", "git", "virus", "instalar programa",
        ],
        "tools": [
            "spotify_control", "youtube_video", "image_generation",
            "tiktok_analyzer"
        ],
    },
    "productivity": {
        "name": "ProductivityAgent",
        "description": "Handles productivity: calendar, email, drive, documents, projects, goals.",
        "keywords": [
            "calendario", "calendar", "email", "correo", "gmail", "drive",
            "documento", "document", "crear doc", "proyecto", "project",
            "meta", "goal", "tarea", "task", "agenda", "schedule",
            "reunion", "meeting", "evento", "event", "recordatorio", "reminder"
        ],
        "penalty_keywords": [
            "spotify", "youtube", "virus", "instalar programa",
            "pantalla", "screenshot", "volumen", "brillo",
        ],
        "tools": [
            "google_calendar", "gmail_control", "google_drive",
            "document_creator", "document_generator", "document_handler",
            "presentation_generator", "spreadsheet_generator", "project_manager", "goals", "reminder",
            "scheduler", "document_tool"
        ],
    },
    "dev": {
        "name": "DevAgent",
        "description": "Handles development: code help, git, codebase analysis, knowledge base, dev agent tasks.",
        "keywords": [
            "codigo", "code", "programar", "program", "git", "commit", "push",
            "pull", "branch", "repo", "repositorio", "codebase", "desarrollo",
            "development", "debug", "error", "bug", "funcion", "function",
            "clase", "class", "api", "endpoint", "server", "database",
            "knowledge base", "base de conocimiento"
        ],
        "penalty_keywords": [
            "spotify", "youtube", "virus", "calendario", "email",
            "pantalla", "screenshot", "volumen", "brillo",
        ],
        "tools": [
            "code_helper", "dev_agent", "git_control", "codebase",
            "knowledge_base", "agent_task", "vscode_controller",
            "todowrite", "subagent_task", "webfetch", "web_search",
            "code_analyzer", "code_generator", "web_generator", "web_designer"
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
        Returns None if no agent matches (handled by main ERIS).
        """
        text_lower = text.lower()
        scores: dict[str, float] = {}

        for agent_key, agent_info in self._registry.get("agents", {}).items():
            if not agent_info.get("enabled", True):
                continue

            score = 0.0
            for keyword in agent_info.get("keywords", []):
                kw_lower = keyword.lower()
                if kw_lower in text_lower:
                    # Base weight: longer keywords are more specific
                    base = len(kw_lower)
                    # Bonus for exact word boundary matches (not substring)
                    if f" {kw_lower} " in f" {text_lower} " or text_lower.startswith(kw_lower) or text_lower.endswith(kw_lower):
                        base *= 1.5
                    # Bonus for multi-word phrases (more specific = more reliable)
                    if " " in kw_lower:
                        base *= 2.0
                    score += base

            # Penalty keywords: if present, reduce this agent's score
            for penalty_kw in agent_info.get("penalty_keywords", []):
                if penalty_kw.lower() in text_lower:
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
