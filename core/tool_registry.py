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
_failed = {}  # tool_name → (module_path, func_name, fail_count)
_lock = threading.Lock()

_MAX_RETRIES = 3

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
    "action_history":        ("actions.flow_recorder", "flow_recorder"),
    "file_processor":        ("actions.file_processor", "file_processor"),

    # ── Section 14B: Productivity ──
    "user_profile":          ("actions.user_profile", "user_profile"),
    "goals":                 ("actions.goals", "goals"),
    "knowledge_base":        ("actions.knowledge_base", "knowledge_base"),
    "scheduler":             ("actions.scheduler", "scheduler"),
    "rules_engine":          ("actions.rules_engine", "rules_engine"),
    "document_creator":      ("actions.document_creator", "document_creator"),
    "document_handler":      ("actions.document_handler", "document_handler"),
    "code_helper":           ("actions.code_helper", "code_helper"),
    "reminder":              ("actions.reminder", "reminder"),
    "notifications":         ("actions.notifications", "notify"),

    # ── Section 14C: Dev ──
    "git_control":           ("actions.git_control", "git_control"),
    "codebase":              ("actions.codebase", "codebase"),
    "dev_agent":             ("actions.dev_agent", "dev_agent"),
    "todowrite":             ("actions.todowrite", "todowrite"),
    "vscode_controller":     ("actions.vscode_controller", "vscode_controller"),
    "web_generator":         ("actions.web_generator", "web_generator"),

    # ── Section 14D: Communication ──
    "send_message":          ("actions.send_message", "send_message"),
    "social_media":          ("actions.social_media", "social_media"),
    "telegram_bot":          ("actions.telegram_bot", "telegram_bot"),
    "whatsapp":              ("actions.whatsapp", "whatsapp"),
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
    "human_mouse":           ("actions.human_mouse", "human_mouse"),
    "contextual_control":    ("actions.contextual_control", "contextual_control"),
    "proactive_automation":  ("actions.proactive_automation", "proactive_automation"),
    "native_ui":             ("actions.native_ui", "native_ui"),

    # ── Section 14G: Search ──
    "web_search":            ("actions.web_search", "web_search"),
    "super_search":          ("actions.super_search", "super_search"),

    # ── Section 14H: Advanced ──
    "auto_programmer":       ("actions.auto_programmer", "auto_programmer"),
    "self_edit":             ("actions.self_edit", "self_edit"),
    "self_awareness":        ("actions.self_awareness", "self_awareness"),
    "computer_control":      ("actions.computer_control", "computer_control"),
    "visual_click":          ("actions.visual_click", "visual_click"),

    # ── Knowledge & RAG ──
    "knowledge_ingestor":     ("actions.knowledge_ingestor", "knowledge_ingestor"),
    "data_connectors":        ("actions.data_connectors", "data_connectors"),

    # ── Section 14I: Memory & Vision ──
    "security_scanner":      ("actions.security_scanner", "security_scanner"),
    "morning_brief":         ("actions.morning_brief", "morning_brief"),
    "vision_guardian":       ("actions.vision_guardian", "vision_guardian"),
    "screen_vision":         ("actions.screen_vision", "screen_vision"),
    "game_companion":        ("actions.game_companion", "game_companion"),
    "document_rag":          ("actions.document_rag", "document_rag"),
    "image_analyzer":        ("actions.image_analyzer", "image_analyzer"),

    # ── Section 14J: AI Features ──
    "personality":           ("actions.personality", "personality_engine"),
    "emotional_state":       ("core.emotional_state", "emotional_state_tool"),
    "self_map":              ("core.self_map", "get_full_map"),
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

    # ── Autonomous Learning ──
    "autonomous_learner":    ("core.autonomous_learner", "autonomous_learner"),

    # ── Training ──
    "training_pipeline":     ("core.training_pipeline", "training_pipeline_tool"),
    "task_planner":          ("core.task_planner", "task_planner_tool"),
    "curiosity_engine":      ("actions.curiosity_engine", "curiosity_tell_fact"),

    # ── AGI ──
    "agi_memory":            ("core.semantic_memory", "get_memory_system"),
    "agi_self_improve":      ("core.self_improvement", "get_self_improvement"),
    "agi_reasoning":         ("core.reasoning_engine", "get_reasoning_engine"),
    "agi_world_model":       ("core.world_model", "get_world_model"),
    "agi_agent":             ("core.agent_architecture", "get_agent_loop"),

    # ── Updater ──
    "eris_update":           ("core.updater", "check_for_update"),

    # ── Meta ──
    "ollama_status":         ("core.model_router", "status"),
    "voice_recognition":     ("core.voice_recognition", "voice_recognition"),
    "tts_set_voice":         ("core.tts_engine", "set_backend"),

    # ── Skills ──
    "skill_manage":          ("skills.skill_registry", "skill_manage"),

    # ── Section 14M: New 16 Features (Jul 2026) ──
    "memory_consolidation":  ("actions.memory_consolidation", "memory_consolidate"),
    "email_manager":         ("actions.email_manager", "email_manager"),
    "calendar_manager":      ("actions.calendar_manager", "calendar_manager"),
    "flow_recorder":         ("actions.flow_recorder", "flow_recorder"),
    "screenshot_history":    ("actions.screenshot_history", "screenshot_history"),
    "clipboard_manager":     ("actions.clipboard_manager", "clipboard_manager"),
    "multi_user":            ("actions.multi_user", "multi_user"),
    "voice_cloning_new":     ("actions.voice_cloning", "voice_cloning"),
    "browser_extension":     ("actions.browser_extension", "browser_extension"),
    "smart_notifications":   ("actions.smart_notifications", "smart_notifications"),
    "usage_analytics":       ("actions.usage_analytics", "usage_analytics"),
    "skill_marketplace":     ("actions.skill_marketplace", "skill_marketplace"),
    "api_server":            ("actions.api_server", "api_server"),
    "federated_learning":    ("actions.federated_learning", "federated_learning"),
    "file_organizer":        ("actions.file_organizer", "file_organizer"),
    "data_encryption":       ("actions.data_encryption", "data_encryption"),

    # ── Section 14N: Batch 13 New Features (Jul 2026) ──
    "auto_backup":           ("actions.auto_backup", "auto_backup"),
    "plugin_marketplace":    ("actions.plugin_marketplace", "plugin_marketplace"),
    "proactive_ia":          ("actions.proactive_ia", "proactive_ia"),
    "voice_enhanced":        ("actions.voice_enhanced", "voice_enhanced"),
    "data_viz":              ("actions.data_viz", "data_viz"),
    "i18n":                  ("actions.i18n", "i18n"),
    "code_review":           ("actions.code_review", "code_review"),
    "code_analyzer":         ("actions.code_analyzer", "code_analyzer"),
    "web_scraper":           ("actions.web_scraper", "web_scraper"),
    "dashboard_web":         ("actions.dashboard_web", "dashboard_web"),
    "docker_deploy":         ("actions.docker_deploy", "docker_deploy"),
    "ci_cd":                 ("actions.ci_cd", "ci_cd"),
    "i18n_ui":               ("actions.i18n_ui", "i18n_ui"),
    "voice_cloning_real":    ("actions.voice_cloning_real", "voice_cloning_real"),

    # ── Batch 3: 11 new features ──
    "sandbox_execution":     ("actions.sandbox_execution", "sandbox_execution"),
    "knowledge_graph":       ("actions.knowledge_graph", "knowledge_graph"),
    "theme_manager":         ("actions.theme_manager", "theme_manager"),
    "plugin_loader":         ("actions.plugin_loader", "plugin_loader"),
    "smart_cache":           ("actions.smart_cache", "smart_cache"),
    "config_export":         ("actions.config_export", "config_export"),
    "desktop_notifications": ("actions.desktop_notifications", "desktop_notifications"),

    # ── Batch 4: Complete Training — All Missing Tools ──
    "translator":            ("actions.translator", "translator"),
    "network_monitor":       ("actions.network_monitor", "network_monitor"),
    "quick_actions":         ("actions.quick_actions", "run"),
    "pdf_editor":            ("actions.pdf_editor", "read_pdf"),
    "context_menu":          ("actions.context_menu", "install"),
    "document_manager":      ("actions.document_manager", "document_manager"),
    "arca_invoice":          ("actions.arca_invoice", "arca_invoice"),
    "openrouter_agent":      ("actions.openrouter_agent", "openrouter_agent"),
    "terminal_agent":        ("actions.terminal_agent", "terminal_agent"),
    "tool_creator":          ("actions.tool_creator", "tool_creator"),
    "smart_file_organizer":  ("actions.smart_file_organizer", "smart_file_organizer"),
    "emo_core":              ("actions.emo_core", "emo_core"),
    "web_jobs":              ("actions.web_jobs", "web_jobs"),
    "web_navigation":        ("actions.web_navigation", "web_navigation"),
    "game_launcher":         ("actions.game_launcher", "game_launcher"),
    "search_background":     ("actions.search_background", "search_background"),
    "backup_system":         ("actions.backup_system", "backup_system"),
    "alarm_manager":         ("actions.alarm_manager", "alarm_manager"),
    "habit_predictor":       ("actions.habit_predictor", "habit_predictor"),
    "file_monitor":          ("actions.file_monitor", "file_monitor"),
    "task_manager":          ("actions.task_manager", "task_manager"),
    "system_reader":         ("actions.system_reader", "system_reader"),
    "webfetch":              ("actions.webfetch", "webfetch"),
    "ask_user":              ("actions.ask_user", "ask_user"),
    "subagent_task":         ("actions.subagent_task", "subagent_task"),
    "self_heal":             ("actions.self_heal", "self_heal"),
    "self_healing_loop":     ("actions.self_healing_loop", "self_healing_loop"),
    "emotional_growth":      ("actions.emotional_growth", "emotional_growth"),
    "english_teacher":       ("actions.english_teacher", "english_teacher"),
    "cybersecurity":         ("actions.cybersecurity", "cybersecurity"),
    "credential_recovery":   ("actions.credential_recovery", "credential_recovery"),
    "osint_agent":           ("actions.osint_agent", "osint_agent"),
    "security_shield":       ("actions.security_shield", "security_shield"),
    "self_protection":       ("actions.self_protection", "self_protection"),
    "video_analyzer":        ("actions.video_analyzer", "video_analyzer"),
    "pc_control":            ("actions.pc_control", "pc_control"),
    "reminders":             ("actions.reminders", "reminders"),
    "calculator":            ("actions.calculator", "calculator"),
    "file_manager":          ("actions.file_manager", "file_manager"),
    "music_player":          ("actions.music_player", "music_player"),
    "fun_mode":              ("actions.fun_mode", "fun_mode"),
    "active_firewall":       ("actions.active_firewall", "active_firewall"),
    "file_encryptor":        ("actions.file_encryptor", "file_encryptor"),
    "task_scheduler":        ("actions.task_scheduler", "task_scheduler"),
    "auto_agent":            ("actions.auto_agent", "auto_agent"),
    "code_generator":        ("actions.code_generator", "code_generator"),
    "role_orchestrator":     ("actions.role_orchestrator", "role_orchestrator"),
    "speaker_recognition":   ("actions.speaker_recognition", "speaker_recognition"),
    "memory_rag":            ("actions.memory_rag", "memory_rag"),
    "context_engine":        ("actions.context_engine", "context_engine"),
    "smart_browser":         ("actions.smart_browser", "smart_browser"),
    "text_summarizer":       ("actions.text_summarizer", "text_summarizer"),
    "ocr_reader":            ("actions.ocr_reader", "ocr_reader"),
    "audio_transcriber":     ("actions.audio_transcriber", "audio_transcriber"),
    "data_analyst":          ("actions.data_analyst", "data_analyst"),
    "pdf_manager":           ("actions.pdf_manager", "pdf_manager"),
    "template_engine":       ("actions.template_engine", "template_engine"),
    "browser_history":       ("actions.browser_history", "browser_history"),
    "process_manager":       ("actions.process_manager", "process_manager"),
    "driver_manager":        ("actions.driver_manager", "driver_manager"),
    "whatsapp_web":          ("actions.whatsapp_web", "whatsapp_web"),
    "notification_center":   ("actions.notification_center", "notification_center"),
    "voice_clone":           ("actions.voice_clone", "voice_clone"),
    "real_time_tts":         ("actions.real_time_tts", "real_time_tts"),
    "keylogger_detector":    ("actions.keylogger_detector", "keylogger_detector"),
    "usb_monitor":           ("actions.usb_monitor", "usb_monitor"),
    "ransomware_shield":     ("actions.ransomware_shield", "ransomware_shield"),
    "darkweb_monitor":       ("actions.darkweb_monitor", "darkweb_monitor"),
    "disk_wiper":            ("actions.disk_wiper", "disk_wiper"),
    "app_installer":         ("actions.app_installer", "app_installer"),
    "screen_recorder":       ("actions.screen_recorder", "start_recording"),
    "save_everywhere":       ("actions.eris_db", "save_everywhere"),
    "screen_see":            ("actions.autonomous_agent", "screen_see"),
    "research":              ("actions.research_agent", "research"),

    # ── Batch 4B: Stub Tools (declared but not yet implemented) ──
    "agent_task":            ("actions.agent_task", "agent_task"),
    "ask_opencode":          ("actions.ask_opencode", "ask_opencode"),
    "conversation_search":   ("actions.conversation_search", "conversation_search"),
    "curiosity_fact":        ("actions.curiosity_fact", "curiosity_fact"),
    "curiosity_fun":         ("actions.curiosity_fun", "curiosity_fun"),
    "curiosity_joke":        ("actions.curiosity_joke", "curiosity_joke"),
    "curiosity_trending":    ("actions.curiosity_trending", "curiosity_trending"),
    "dashboard":             ("actions.dashboard", "dashboard"),
    "db_knowledge":          ("actions.db_knowledge", "db_knowledge"),
    "db_memory":             ("actions.db_memory", "db_memory"),
    "db_tasks":              ("actions.db_tasks", "db_tasks"),
    "episodic_log":          ("actions.episodic_log", "episodic_log"),
    "eris_ui_control":       ("actions.eris_ui_control", "eris_ui_control"),
    "full_training":         ("actions.full_training", "full_training"),
    "learn_from_mistake":    ("actions.learn_from_mistake", "learn_from_mistake"),
    "learn_session":         ("actions.learn_session", "learn_session"),
    "meeting_transcriber":   ("actions.meeting_transcriber", "meeting_transcriber"),
    "obsidian_note":         ("actions.obsidian_note", "obsidian_note"),
    "play_direct":           ("actions.play_direct", "play_direct"),
    "plugin_manage":         ("actions.plugin_manage", "plugin_manage"),
    "predict_analyze":       ("actions.predict_analyze", "predict_analyze"),
    "res_monitor":           ("actions.res_monitor", "res_monitor"),
    "res_protect":           ("actions.res_protect", "res_protect"),
    "sandbox_run":           ("actions.sandbox_run", "sandbox_run"),
    "sandbox_test_tool":     ("actions.sandbox_test_tool", "sandbox_test_tool"),
    "save_memory":           ("actions.save_memory", "save_memory"),
    "search_info":           ("actions.search_info", "search_info"),
    "shutdown_eris":         ("actions.shutdown_eris", "shutdown_eris"),
    "sleep_mode":            ("actions.sleep_mode", "sleep_mode"),
    "sms":                   ("actions.sms", "sms"),
    "superpowers_activate":  ("actions.superpowers_activate", "superpowers_activate"),
    "task_queue":            ("actions.task_queue", "task_queue"),

    # ── Batch 5: Connectivity + Self-Healing ──
    "connectivity":          ("core.connectivity", "connectivity_tool"),
    "self_healing":          ("core.self_healing", "self_healing_tool"),
    # ── Batch 6: Page/Video Summarizer ──
    "page_summarizer":       ("actions.page_summarizer", "page_summarizer"),
}


def get_tool(tool_name: str) -> Callable | None:
    """Lazy-load a tool function by name. Returns None if not found.
    Checks static registry first, then PluginManager for dynamic plugins.
    Retries failed imports up to _MAX_RETRIES times."""
    if tool_name in _cache:
        return _cache[tool_name]

    with _lock:
        if tool_name in _cache:
            return _cache[tool_name]

        # Check if previously failed — allow retry if under limit
        if tool_name in _failed:
            _mod_path, _fn_name, fail_count = _failed[tool_name]
            if fail_count >= _MAX_RETRIES:
                return None
            # Will retry below

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
                _failed.pop(tool_name, None)  # Clear failure tracking on success
                return func
            except Exception:
                prev = _failed.get(tool_name, (module_path, func_name, 0))
                _failed[tool_name] = (module_path, func_name, prev[2] + 1)
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
        _failed.pop(tool_name, None)


def retry_tool(tool_name: str) -> Callable | None:
    """Force retry of a previously failed tool import."""
    with _lock:
        _cache.pop(tool_name, None)
        _failed.pop(tool_name, None)
    return get_tool(tool_name)


def clear_failures():
    """Clear all failure tracking to allow fresh retries."""
    with _lock:
        _failed.clear()
        # Also remove cached None entries so they can be retried
        to_remove = [k for k, v in _cache.items() if v is None]
        for k in to_remove:
            del _cache[k]


def preload_tools(names: list[str]):
    """Preload specific tools in background (called at startup for common ones)."""
    for name in names:
        try:
            get_tool(name)
        except Exception:
            pass
