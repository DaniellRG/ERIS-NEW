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
            "ollama vision", "llava", "vision local", "modo gaming", "juego pantalla"
        ],
        "tools": [
            "screen_vision", "image_analyzer", "vision_guardian",
            "game_companion", "ollama_vision"
        ],
    },
    "search": {
        "name": "SearchAgent",
        "description": "Handles all search operations: web search, file search, session search, super search.",
        "keywords": [
            "busca", "buscar", "search", "encontrar", "find", "donde esta",
            "donde queda", "sesiones anteriores", "historial", "buscar archivo",
            "buscar en mis sesiones", "super search", "search file"
        ],
        "tools": [
            "web_search", "super_search", "session_search"
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
        "tools": [
            "computer_control", "desktop_control", "system_monitor",
            "windows_settings", "computer_settings", "accessibility",
            "screen_reader", "accessibility_overlay",
            "linux_settings", "hyprland_control", "omarchy_control",
            "shell_executor"
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
        "tools": [
            "google_calendar", "gmail_control", "google_drive",
            "document_creator", "project_manager", "goals", "reminder",
            "scheduler"
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
        "tools": [
            "code_helper", "dev_agent", "git_control", "codebase",
            "knowledge_base", "agent_task"
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
        Classify user text into an agent key using keyword matching.
        Returns None if no agent matches (handled by main ERIS).
        """
        text_lower = text.lower()
        best_match = None
        best_score = 0

        for agent_key, agent_info in self._registry.get("agents", {}).items():
            if not agent_info.get("enabled", True):
                continue

            score = 0
            for keyword in agent_info.get("keywords", []):
                if keyword.lower() in text_lower:
                    # Longer keywords get higher priority
                    score += len(keyword)

            if score > best_score:
                best_score = score
                best_match = agent_key

        # Minimum threshold to avoid false positives
        if best_score >= 3:
            return best_match
        return None

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
