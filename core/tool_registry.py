"""
core/tool_registry.py — Lazy-loading tool registry for ERIS.
Maps tool names to (module_path, function_name) and imports on first use.
Eliminates ~116 eager module-level imports from main.py.
"""
from __future__ import annotations

import importlib
import threading
from typing import Any, Callable

_cache = {}
_lock = threading.Lock()

# Tool registry: tool_name → (module_path, function_name)
# Module path relative to project root, e.g. "actions.open_app"
_TOOLS = {
    # ── Section 14A: Core System ──
    "open_app":              ("actions.open_app", "open_app"),
    "app_discovery":         ("actions.app_discovery", "app_discovery"),
    "weather_report":        ("actions.weather_report", "weather_action"),
    "computer_settings":     ("actions.computer_settings", "computer_settings"),
    "desktop_control":       ("actions.desktop", "desktop_control"),
    "window_manager":        ("actions.window_manager", "window_manager"),
    "system_monitor":        ("actions.system_monitor", "system_monitor"),
    "auto_repair":           ("core.auto_repair", "auto_repair"),
    "action_history":        ("core.system_logger", "action_history"),
    "system_watcher":        ("core.system_watcher", "system_overview"),
    "file_processor":        ("actions.file_processor", "file_processor"),
    "screen_processor":      ("actions.screen_processor", "screen_process"),

    # ── Section 14B: Productivity ──
    "user_profile":          ("actions.user_profile", "user_profile"),
    "goals":                 ("actions.goals", "goals"),
    "project_manager":       ("actions.project_manager", "project_manager"),
    "knowledge_base":        ("actions.knowledge_base", "knowledge_base"),
    "scheduler":             ("actions.scheduler", "scheduler"),
    "rules_engine":          ("actions.rules_engine", "rules_engine"),
    "document_creator":      ("actions.document_creator", "document_creator"),
    "code_helper":           ("actions.code_helper", "code_helper"),
    "reminder":              ("actions.reminder", "reminder"),
    "notifications":         ("actions.notifications", "notify"),

    # ── Section 14C: Dev ──
    "git_control":           ("actions.git_control", "git_control"),
    "codebase":              ("actions.codebase", "codebase"),
    "shell_executor":        ("actions.shell_executor", "shell_executor"),
    "dev_agent":             ("actions.dev_agent", "dev_agent"),

    # ── Section 14D: Communication ──
    "send_message":          ("actions.send_message", "send_message"),
    "social_media":          ("actions.social_media", "social_media"),
    "telegram_bot":          ("actions.telegram_bot", "telegram_bot"),
    "whatsapp":              ("actions.whatsapp", "whatsapp"),
    "obsidian_control":      ("actions.obsidian_control", "obsidian_control"),
    "unified_communications":("actions.unified_communications", "unified_communications"),

    # ── Section 14E: Integrations ──
    "spotify_control":       ("actions.spotify_control", "spotify_control"),
    "smart_home":            ("actions.smart_home", "smart_home"),
    "google_calendar":       ("actions.google_calendar", "google_calendar"),
    "google_drive":          ("actions.google_drive", "google_drive"),
    "gmail_control":         ("actions.gmail_control", "gmail_control"),
    "google_maps":           ("actions.google_maps", "google_maps"),
    "rgb_control":           ("actions.rgb_control", "rgb_control"),

    # ── Section 14F: Accessibility ──
    "accessibility":         ("actions.accessibility", "accessibility"),
    "accessibility_overlay": ("actions.accessibility_overlay", "accessibility_overlay"),
    "screen_reader":         ("actions.screen_reader", "screen_reader"),
    "mouse_control":         ("actions.mouse_control", "mouse_control"),
    "human_mouse":           ("actions.human_mouse", "human_mouse"),
    "contextual_control":    ("actions.contextual_control", "contextual_control"),
    "proactive_automation":  ("actions.proactive_automation", "proactive_automation"),
    "native_ui":             ("actions.native_ui", "native_ui"),
    "gesture_engine":        ("actions.gesture_engine", "gesture_engine"),

    # ── Section 14G: Search ──
    "web_search":            ("actions.web_search", "web_search"),
    "super_search":          ("actions.super_search", "super_search"),
    "public_apis":           ("actions.public_apis", "public_apis"),
    "scientific_papers":     ("actions.scientific_papers", "scientific_papers"),
    "dataset_search":        ("actions.dataset_search", "dataset_search"),

    # ── Section 14H: Advanced ──
    "rl_lab":                ("actions.rl_lab", "rl_lab"),
    "zep_memory":            ("actions.zep_memory", "zep_memory"),
    "dspy_optimizer":        ("actions.dspy_optimizer", "dspy_optimizer"),
    "auto_programmer":       ("actions.auto_programmer", "auto_programmer"),
    "self_edit":             ("actions.self_edit", "self_edit"),
    "computer_control":      ("actions.computer_control", "computer_control"),
    "visual_click":          ("actions.visual_click", "visual_click"),
    "monitor_manager":       ("actions.monitor_manager", "monitor_manager_tool"),

    # ── Section 14I: Memory & Vision ──
    "security_scanner":      ("actions.security_scanner", "security_scanner"),
    "morning_brief":         ("actions.morning_brief", "morning_brief"),
    "vision_guardian":       ("actions.vision_guardian", "vision_guardian"),
    "screen_vision":         ("actions.screen_vision", "screen_vision"),
    "game_companion":        ("actions.game_companion", "game_companion"),
    "document_rag":          ("actions.document_rag", "document_rag"),
    "image_analyzer":        ("actions.image_analyzer", "analyze_image_file"),

    # ── Section 14J: AI Features ──
    "personality":           ("actions.personality", "personality_engine"),
    "emotional_steering":    ("actions.emotional_steering", "emotional_steering"),
    "emotional_state":       ("core.emotional_state", "emotional_state_tool"),
    "document_rag_stats":    ("actions.document_rag", "document_rag"),
    "image_generation":      ("actions.image_generation", "image_generation"),

    # ── Browser & Files ──
    "browser_control":       ("actions.browser_control", "browser_control"),
    "file_controller":       ("actions.file_controller", "file_controller"),
    "youtube_video":         ("actions.youtube_video", "youtube_video"),
    "program_manager":       ("actions.program_manager", "program_manager"),
    "windows_settings":      ("actions.windows_settings", "windows_settings"),
    "flight_finder":         ("actions.flight_finder", "flight_finder"),
    "tiktok_analyzer":       ("actions.tiktok_analyzer", "tiktok_analyzer"),
    "game_updater":          ("actions.game_updater", "game_updater"),

    # ── MCP ──
    "mcp_tool":              ("actions.mcp_tool", "mcp_tool"),

    # ── Training ──
    "training_pipeline":     ("core.training_pipeline", "training_pipeline_tool"),
    "task_planner":          ("core.task_planner", "task_planner_tool"),
    "curiosity_engine":      ("core.curiosity_engine", "curiosity_engine_tool"),
    "boredom_engine":        ("core.boredom_engine", "boredom_engine_tool"),
    "inner_monologue":       ("core.inner_monologue", "inner_monologue_tool"),
    "computer_use":          ("core.computer_use_agent", "computer_use_tool"),

    # ── AGI ──
    "agi_memory":            ("core.semantic_memory", "get_memory_system"),
    "agi_world_model":       ("core.world_model", "get_world_model"),
    "agi_reasoning":         ("core.reasoning_engine", "get_reasoning_engine"),
    "agi_self_improve":      ("core.self_improvement", "get_self_improvement"),
    "agi_agent":             ("core.agent_architecture", "get_agent_loop"),

    # ── Updater ──
    "eris_update":           ("core.updater", None),  # Special handler in _execute_tool

    # ── Meta ──
    "meta_learning":         ("actions.meta_learning", None),
    "ollama_status":         ("core.model_router", "status"),
    "voice_recognition":     ("core.voice_recognition", "voice_recognition"),
    "tts_set_voice":         ("core.tts_engine", None),

    # ── Skills ──
    "skill_manage":          ("skills.skill_registry", "handle_skill_command"),
    "session_search":        ("core.session_search", "session_search"),
}


def get_tool(tool_name: str) -> Callable | None:
    """Lazy-load a tool function by name. Returns None if not found.
    Checks static registry first, then PluginManager for dynamic plugins."""
    if tool_name in _cache:
        return _cache[tool_name]

    with _lock:
        if tool_name in _cache:
            return _cache[tool_name]

        entry = _TOOLS.get(tool_name)
        if entry is not None:
            module_path, func_name = entry
            if func_name is None:
                _cache[tool_name] = None
                return None  # Special handler, not a simple function call

            try:
                mod = importlib.import_module(module_path)
                func = getattr(mod, func_name, None)
                _cache[tool_name] = func
                return func
            except Exception:
                _cache[tool_name] = None
                return None

        # Check PluginManager for dynamic plugin tools
        try:
            from core.plugin_manager import get_plugin_manager
            pm = get_plugin_manager()
            pfunc = pm.get_tool(tool_name)
            if pfunc is not None:
                _cache[tool_name] = pfunc
                return pfunc
        except Exception:
            pass

        _cache[tool_name] = None
        return None


def get_all_tool_names() -> list[str]:
    """Return list of all registered tool names."""
    return list(_TOOLS.keys())


def register_tool(tool_name: str, func: Callable):
    """Register a tool function dynamically at runtime.
    Used by PluginManager to make plugin tools discoverable."""
    with _lock:
        _cache[tool_name] = func


def preload_tools(names: list[str]):
    """Preload specific tools in background (called at startup for common ones)."""
    for name in names:
        try:
            get_tool(name)
        except Exception:
            pass
