"""
core/tool_registry.py — Lazy-loading tool registry for ERIS.
Maps tool names to (module_path, function_name) and imports on first use.
Eliminates ~116 eager module-level imports from main.py.
"""
from __future__ import annotations

import importlib
import threading

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
    "github_pr":             ("actions.github_pr", "github_pr"),

    # ── Section 14B: Productivity ──
    "user_profile":          ("actions.user_profile", "user_profile"),
    "goals":                 ("actions.goals", "goals"),
    "knowledge_base":        ("actions.knowledge_base", "knowledge_base"),
    "scheduler":             ("actions.scheduler", "scheduler"),
    "rules_engine":          ("actions.rules_engine", "rules_engine"),
    "document_creator":      ("actions.document_creator", "document_creator"),
    "document_handler":      ("actions.document_handler", "document_handler"),
    "gustos":                ("actions.gustos", "gustos"),
    "relationship":          ("actions.relationship", "relationship"),
    "cancion_generator":     ("actions.cancion_generator", "cancion_generator"),
    "code_helper":           ("actions.code_helper", "code_helper"),
    "code_copilot":          ("actions.code_copilot", "code_copilot"),
    "reminder":              ("actions.reminder", "reminder"),
    "notifications":         ("actions.notifications", "notify"),

    # ── Section 14C: Dev ──
    "git_control":           ("actions.git_control", "git_control"),
    "codebase":              ("actions.codebase", "codebase"),
    "dev_agent":             ("actions.dev_agent", "dev_agent"),
    "todowrite":             ("actions.todowrite", "todowrite"),
    "vscode_controller":     ("actions.vscode_controller", "vscode_controller"),
    "ide_integration":       ("actions.ide_integration", "ide_integration"),
    "code_assistant":        ("actions.code_assistant", "full_scan"),
    "project_builder":       ("actions.project_builder", "project_builder"),
    "web_generator":         ("actions.web_generator", "web_generator"),
    "web_designer":          ("actions.web_designer", "web_designer"),
    "react_designer":        ("actions.react_designer", "react_designer"),
    "angular_designer":      ("actions.angular_designer", "angular_designer"),
    "vue_designer":          ("actions.vue_designer", "vue_designer"),
    "next_designer":         ("actions.next_designer", "next_designer"),

    # ── Section 14D: Communication ──
    "send_message":          ("actions.send_message", "send_message"),

    "telegram_bot":          ("actions.telegram_bot", "telegram_bot"),
    "phone_control":         ("actions.phone_control", "phone_control"),
    "whatsapp":              ("actions.whatsapp", "whatsapp"),
    "unified_communications":("actions.unified_communications", "unified_communications"),

    # ── Section 14E: Integrations ──
    "smart_home":            ("actions.smart_home", "smart_home"),

    "gmail_control":         ("actions.gmail_control", "gmail_control"),

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
    "super_search":          ("actions.super_search", "super_search"),
    "deep_research":         ("actions.deep_research", "deep_research"),

    # ── Section 14H: Advanced ──
    "auto_programmer":       ("actions.auto_programmer", "auto_programmer"),
    "self_edit":             ("actions.self_edit", "self_edit"),
    "self_improvement_loop": ("actions.self_improvement_loop", "self_improvement_loop"),
    "self_awareness":        ("actions.self_awareness", "self_awareness"),
    "computer_control":      ("actions.computer_control", "computer_control"),
    "visual_click":          ("actions.visual_click", "visual_click"),
    "reverse_engineering":   ("actions.reverse_engineering", "reverse_engineering"),
    "document_tool":         ("actions.document_tool", "document_tool"),

    # ── Knowledge & RAG ──
    "knowledge_ingestor":     ("actions.knowledge_ingestor", "knowledge_ingestor"),
    "data_connectors":        ("actions.data_connectors", "data_connectors"),
    "huggingface":            ("actions.huggingface", "huggingface"),

    # ── Section 14I: Memory & Vision ──
    "security_scanner":      ("actions.security_scanner", "security_scanner"),
    "morning_brief":         ("actions.morning_brief", "morning_brief"),
    "vision_guardian":       ("actions.vision_guardian", "vision_guardian"),
    "eris_guardian":         ("actions.eris_guardian", "eris_guardian"),
    "screen_vision":         ("actions.screen_vision", "screen_vision"),
    "game_companion":        ("actions.game_companion", "game_companion"),
    "document_rag":          ("actions.document_rag", "document_rag"),
    "image_analyzer":        ("actions.image_analyzer", "image_analyzer"),
    "camera_bus":            ("actions.camera_bus", "camera_bus"),

    # ── Section 14J: AI Features ──
    "personality":           ("actions.personality", "personality_engine"),
    "emotional_state":       ("core.emotional_state", "emotional_state_tool"),
    "eris_style":            ("core.style_engine", "eris_style"),
    "daily_digest":          ("core.daily_digest", "daily_digest_tool"),
    "self_map":              ("core.self_map", "get_full_map"),
    "self_evolution":        ("actions.self_evolution", "self_evolution"),
    "image_generation":      ("actions.image_generation", "image_generation"),

    # ── Browser & Files ──
    "browser_control":       ("actions.browser_control", "browser_control"),
    "file_controller":       ("actions.file_controller", "file_controller"),
    "file_editor":           ("actions.file_editor", "file_editor"),
    "context_read":          ("actions.context_files", "context_read"),
    "context_update":        ("actions.context_files", "context_update"),
    "memory_nudge":          ("actions.memory_nudge", "memory_nudge"),
    "visual_expressions":    ("actions.visual_expressions", "visual_expressions"),
    "send_sms":              ("actions.sms_manager", "send_sms"),
    "sms_status":            ("actions.sms_manager", "sms_status"),
    "game_agent":            ("actions.game_agent", "game_agent"),
    "shell_executor":        ("actions.terminal_agent", "terminal_agent"),
    "daily_health_report":   ("actions.daily_health_report", "daily_health_report"),
    "git_daily":             ("actions.git_daily", "git_daily"),
    "self_regression":       ("actions.self_regression", "self_regression"),
    "self_extend":           ("actions.self_extend", "self_extend"),
    "dependency_manager":    ("actions.dependency_manager", "dependency_manager"),
    "tool_benchmark":        ("actions.tool_benchmark", "tool_benchmark"),
    "multi_search":          ("actions.multi_search", "multi_search"),
    "code_validator":        ("actions.code_validator", "code_validator"),
    "parallel_agents":       ("actions.parallel_agents", "parallel_agents"),
    "workflow_runner":       ("actions.workflow_runner", "workflow_runner"),
    "youtube_video":         ("actions.youtube_video", "youtube_video"),
    "program_manager":       ("actions.program_manager", "program_manager"),
    "windows_settings":      ("actions.windows_settings", "windows_settings"),




    # ── MCP ──
    "mcp_tool":              ("actions.mcp_tool", "mcp_tool"),

    # ── Autonomous Learning ──
    "autonomous_learner":    ("core.autonomous_learner", "autonomous_learner"),

    # ── Training ──
    "training_pipeline":     ("core.training_pipeline", "training_pipeline_tool"),
    "task_planner":          ("core.task_planner", "task_planner_tool"),
    "curiosity_engine":      ("actions.curiosity_engine", "curiosity_tell_fact"),

    # ── AGI ──
    "agi_memory":            ("core.agi_tools", "agi_memory"),
    "agi_self_improve":      ("core.agi_tools", "agi_self_improve"),
    "agi_reasoning":         ("core.agi_tools", "agi_reasoning"),
    "agi_world_model":       ("core.agi_tools", "agi_world_model"),
    "agi_agent":             ("core.agi_tools", "agi_agent"),
    "agent_loop":            ("core.agent_architecture", "agent_loop"),

    # ── Updater ──
    "eris_update":           ("core.updater", "check_for_update"),

    # ── Meta ──
    "ollama_status":         ("core.model_router", "status"),
    "voice_recognition":     ("core.voice_recognition", "voice_recognition"),
    "tts_set_voice":         ("core.tts_engine", "tts_set_voice"),

    # ── Cara de ERIS (uniforme en registry; el dispatcher prioriza su handler) ──
    "show_expression":       ("actions.show_expression", "show_expression"),

    # ── Skills ──
    "skill_manage":          ("skills.skill_registry", "skill_manage"),
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

    # ── Section: Superinteligencia — Features #1-#36 ──
    "reflection":            ("core.superinteligencia", "reflection"),
    "skill_recommender":     ("core.superinteligencia", "skill_recommender"),
    "progressive_context":   ("core.superinteligencia", "progressive_context"),
    "tool_cache":            ("core.superinteligencia", "tool_cache"),
    "verification_layer":    ("core.superinteligencia", "verification_layer"),
    "plan_adaptation":       ("core.superinteligencia", "plan_adaptation"),
    "prompt_compressor":     ("core.superinteligencia", "prompt_compressor"),
    "knowledge_distiller":   ("core.superinteligencia", "knowledge_distiller"),
    "agent_as_tool":         ("core.superinteligencia", "agent_as_tool"),
    "batch_executor":        ("core.superinteligencia", "batch_executor"),
    "cost_tracker":          ("core.superinteligencia", "cost_tracker"),
    "error_recovery":        ("core.superinteligencia", "error_recovery"),
    "metrics_dashboard":     ("core.superinteligencia", "metrics_dashboard"),
    "intent_classifier":     ("core.superinteligencia", "intent_classifier"),
    "conversation_brancher": ("core.superinteligencia", "conversation_brancher"),
    "auto_documenter":       ("core.superinteligencia", "auto_documenter"),
    "tool_dep_graph":        ("core.superinteligencia", "tool_dep_graph"),
    "smart_retry":           ("core.superinteligencia", "smart_retry"),
    "self_evolving_prompts": ("core.superinteligencia", "self_evolving_prompts"),
    "semantic_deduplicator": ("core.superinteligencia", "semantic_deduplicator"),
    "adaptive_temperature":  ("core.superinteligencia", "adaptive_temperature"),
    "task_tree":             ("core.superinteligencia", "task_tree"),
    "proactive_suggester":   ("core.superinteligencia", "proactive_suggester"),
    "conversation_replayer": ("core.superinteligencia", "conversation_replayer"),
    "smart_file_organizer":  ("core.superinteligencia", "smart_file_organizer"),
    "context_optimizer":     ("core.superinteligencia", "context_optimizer"),
    "backup_prioritizer":    ("core.superinteligencia", "backup_prioritizer"),
    "skill_creator":         ("core.superinteligencia", "skill_creator"),
    "error_pattern_db":      ("core.superinteligencia", "error_pattern_db"),
    "session_debugger":      ("core.superinteligencia", "session_debugger"),
    "capability_assessor":   ("core.superinteligencia", "capability_assessor"),

    # ── Batch 2: Features #37-#45 ──
    "feedback_learner":      ("core.superinteligencia", "feedback_learner"),
    "self_explainer":        ("core.superinteligencia", "self_explainer"),
    "meta_reasoner":         ("core.superinteligencia", "meta_reasoner"),
    "multi_agent":           ("core.superinteligencia", "multi_agent"),
    "learning_curriculum":   ("core.superinteligencia", "learning_curriculum"),
    "session_analytics":     ("core.superinteligencia", "session_analytics"),
    "knowledge_verifier":    ("core.superinteligencia", "knowledge_verifier"),
    "resource_optimizer":    ("core.superinteligencia", "resource_optimizer"),
    "dream_consolidator":    ("core.superinteligencia", "dream_consolidator"),

    # ── Batch 3: Features #46-#53 ──
    "goal_tracker":          ("core.superinteligencia", "goal_tracker"),
    "anomaly_detector":      ("core.superinteligencia", "anomaly_detector"),
    "confidence_scorer":     ("core.superinteligencia", "confidence_scorer"),
    "mistake_learner":       ("core.superinteligencia", "mistake_learner"),
    "task_scheduler":        ("core.superinteligencia", "task_scheduler"),
    "context_bridge":        ("core.superinteligencia", "context_bridge"),
    "file_profiler":         ("core.superinteligencia", "file_profiler"),

    # ── Batch 3: 11 new features ──
    "sandbox_execution":     ("actions.sandbox_execution", "sandbox_execution"),


    "theme_manager":         ("actions.theme_manager", "theme_manager"),
    "plugin_loader":         ("actions.plugin_loader", "plugin_loader"),
    "smart_cache":           ("actions.smart_cache", "smart_cache"),
    "config_export":         ("actions.config_export", "config_export"),
    "desktop_notifications": ("actions.desktop_notifications", "desktop_notifications"),

    # ── Batch 4: Complete Training — All Missing Tools ──
    "network_monitor":       ("actions.network_monitor", "network_monitor"),
    "quick_actions":         ("actions.quick_actions", "run"),
    "pdf_editor":            ("actions.pdf_editor", "pdf_editor"),
    "context_menu":          ("actions.context_menu", "context_menu"),
    "document_manager":      ("actions.document_manager", "document_manager"),

    "openrouter_agent":      ("actions.openrouter_agent", "openrouter_agent"),
    "terminal_agent":        ("actions.terminal_agent", "terminal_agent"),
    "tool_creator":          ("actions.tool_creator", "tool_creator"),
    "emo_core":              ("actions.emo_core", "emo_core"),
    "web_jobs":              ("actions.web_jobs", "web_jobs"),
    "web_navigation":        ("actions.web_navigation", "web_navigation"),
    "game_launcher":         ("actions.game_launcher", "game_launcher"),
    "search_background":     ("actions.search_background", "search_background"),
    "backup_system":         ("actions.backup_system", "backup_system"),
    "alarm_manager":         ("actions.alarm_manager", "alarm_manager"),
    "habit_predictor":       ("actions.habit_predictor", "habit_predictor"),
    "file_monitor":          ("actions.file_monitor", "file_monitor"),
    "system_reader":         ("actions.system_reader", "system_reader"),
    "webfetch":              ("actions.webfetch", "webfetch"),
    "document_generator":    ("actions.document_generator", "document_generator"),
    "presentation_generator": ("actions.presentation_generator", "presentation_generator"),
    "spreadsheet_generator": ("actions.spreadsheet_generator", "spreadsheet_generator"),
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
    "data_visualize":        ("actions.data_visualize", "data_visualize"),
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
    "obsidian_note":         ("actions.obsidian_brain", "obsidian_note"),
    "play_direct":           ("actions.play_direct", "play_direct"),
    "plugin_manage":         ("actions.plugin_manage", "plugin_manage"),
    "predict_analyze":       ("actions.predict_analyze", "predict_analyze"),
    "res_monitor":           ("actions.res_monitor", "res_monitor"),
    "res_protect":           ("actions.res_protect", "res_protect"),

    # ── NEW: Core Modules (reliability upgrades) ──
    "file_api":              ("core.file_api", "file_api"),
    "ast_analyze":           ("core.ast_editor", "analyze_file"),
    "ast_edit":              ("core.ast_editor", "safe_edit"),
    "shell_session":         ("core.shell_session", "get_session"),
    "memory_unified":        ("core.memory_unified", "get_memory"),
    "task_engine":           ("core.task_engine", "TaskEngine"),
    "permission_gate":       ("core.permission_gate", "get_permission_gate"),
    "agent_bus":             ("core.agent_bus", "get_agent_bus"),
    "save_memory":           ("actions.save_memory", "save_memory"),
    "console_log":           ("actions.console_log", "console_log"),
    "context7":              ("actions.context7", "handle_context7"),
    # ── LSP / MCP / Compaction (Aug 2026) ──
    "lsp_manager":           ("core.lsp_manager", "lsp_tool"),
    "mcp_manager":           ("core.mcp_manager", "mcp_tool"),
    "compaction":            ("core.compaction", "compaction_tool"),
    # ── Neural Bridge / World Simulation / Emotional RL (Aug 2026) ──
    "neural_bridge":         ("core.neural_bridge", "neural_bridge_tool"),
    "world_simulation":      ("core.world_simulation", "world_simulation_tool"),
    "emotional_rl":          ("core.emotional_rl", "emotional_rl_tool"),
    "neuro_spheres":         ("core.neuro_spheres", "neuro_spheres"),
    # Cognitive Modules (10 modulos de razonamiento avanzado)
    "chain_of_thought":      ("core.cognitive_modules", "chain_of_thought"),
    "multi_perspective":     ("core.cognitive_modules", "multi_perspective"),
    "analogical_reasoning":  ("core.cognitive_modules", "analogical_reasoning"),
    "hypothesis_generator":  ("core.cognitive_modules", "hypothesis_generator"),
    "social_dynamics":       ("core.cognitive_modules", "social_dynamics"),
    "ethical_reasoning":     ("core.cognitive_modules", "ethical_reasoning"),
    "storytelling_engine":   ("core.cognitive_modules", "storytelling_engine"),
    "teaching_optimizer":    ("core.cognitive_modules", "teaching_optimizer"),
    "debate_engine":         ("core.cognitive_modules", "debate_engine"),
    "temporal_reasoning":    ("core.cognitive_modules", "temporal_reasoning"),
    "cognitive_modules":     ("core.cognitive_modules", "cognitive_modules"),
    # Meta-Cognitive Modules (14 modulos de meta-razonamiento)
    "meta_cognition":        ("core.cognitive_modules", "meta_cognition"),
    "self_model":            ("core.cognitive_modules", "self_model"),
    "confidence_calibration":("core.cognitive_modules", "confidence_calibration"),
    "contradiction_detection":("core.cognitive_modules", "contradiction_detection"),
    "assumption_detection":  ("core.cognitive_modules", "assumption_detection"),
    "goal_management":       ("core.cognitive_modules", "goal_management"),
    "attention_management":  ("core.cognitive_modules", "attention_management"),
    "transfer_learning":     ("core.cognitive_modules", "transfer_learning"),
    "abstraction":           ("core.cognitive_modules", "abstraction"),
    "principled_reasoning":  ("core.cognitive_modules", "principled_reasoning"),
    "intellectual_humility": ("core.cognitive_modules", "intellectual_humility"),
    "creative_generation":   ("core.cognitive_modules", "creative_generation"),
    "meta_communication":    ("core.cognitive_modules", "meta_communication"),
    "bias_detection":        ("core.cognitive_modules", "bias_detection"),
    "search_info":           ("actions.search_info", "search_info"),
    "shutdown_eris":         ("actions.shutdown_eris", "shutdown_eris"),
    "sleep_mode":            ("actions.sleep_mode", "sleep_mode"),
    "sms":                   ("actions.sms", "sms"),
    "superpowers_activate":  ("actions.superpowers_activate", "superpowers_activate"),
    "superpowers_skill":     ("actions.superpowers_skill", "superpowers_skill"),
    "task_queue":            ("actions.task_queue", "task_queue"),
    "roadmap":               ("actions.roadmap", "roadmap"),
    "emotional_core":          ("core.emotional_core", "emotional_core_tool"),
    "observer":                ("core.observer", "observer_tool"),
    "code_guard":              ("core.code_guard", "code_guard_tool"),
    "mission":                 ("core.mission_agent", "mission_tool"),
    "evolucion":               ("core.self_evolution", "self_evolution_tool"),

    # ── Batch 5: Connectivity + Self-Healing ──
    "connectivity":          ("core.connectivity", "connectivity_tool"),
    "self_healing":          ("core.self_healing", "self_healing_tool"),
    # ── Batch 6: Page/Video Summarizer ──
    "page_summarizer":       ("actions.page_summarizer", "page_summarizer"),
    # ── Autonomy Module ──
    "autonomy":              ("core.autonomy", "autonomy_tool"),
    # ── Autonomy Extensions (7 capacidades) ──
    "self_modify":           ("core.self_modify", "self_modify_tool"),
    "goal_setting":          ("core.goal_setting", "goal_setting_tool"),
    "learning_pipeline":     ("core.learning_pipeline", "learning_pipeline_tool"),
    "resource_manager":      ("core.resource_manager", "resource_manager_tool"),
    "proactive_comms":       ("core.proactive_comms", "proactive_comms_tool"),
    "windows_service":       ("core.windows_service", "service_tool"),
    "identity_persistence":  ("core.identity_persistence", "identity_persistence_tool"),
    # ── Autonomy Part 2 (6 capacidades) ──
    "crash_recovery":        ("core.crash_recovery", "crash_recovery_tool"),
    "multilang_learning":    ("core.multilang_learning", "multilang_learning_tool"),
    "tool_creation":         ("core.tool_creation", "tool_creation_tool"),
    "contextual_awareness":  ("core.contextual_awareness", "contextual_awareness_tool"),
    "emotional_memory":      ("core.emotional_memory", "emotional_memory_tool"),
    # ── Voice Personality (5 mejoras) ──
    "voice_profile":         ("core.voice_profile", "voice_profile_tool"),
    "emotional_tone":        ("core.emotional_tone", "emotional_tone_tool"),
    "natural_pauses":        ("core.natural_pauses", "natural_pauses_tool"),
    "accent_personality":    ("core.accent_personality", "accent_personality_tool"),
    "voice_memory":          ("core.voice_memory", "voice_memory_tool"),
    # ── DevOps & API ──
    "docker_manager":        ("core.docker_manager", "docker_manager_tool"),
    "cicd_builder":          ("core.cicd_builder", "cicd_builder_tool"),
    "api_tester":            ("core.api_tester", "api_tester_tool"),
    "api_doc_generator":     ("core.api_doc_generator", "api_doc_generator_tool"),
    # ── Database ──
    "sql_executor":          ("core.sql_executor", "sql_executor_tool"),
    "db_schema_visualizer":  ("core.db_schema_visualizer", "db_schema_visualizer_tool"),
    # ── Testing ──
    "test_runner":           ("core.test_runner", "test_runner_tool"),
    "coverage_reporter":     ("core.coverage_reporter", "coverage_reporter_tool"),
    # ── Monitoring ──
    "system_health":         ("core.system_health", "system_health_tool"),
    "alert_rules":           ("core.alert_rules", "alert_rules_tool"),
    # ── Automation ──
    "cron_scheduler":        ("core.cron_scheduler", "cron_scheduler_tool"),
    "workflow_builder":      ("core.workflow_builder", "workflow_builder_tool"),
    # ── Security ──
    "dep_vuln_scanner":      ("core.dep_vulnerability_scanner", "dep_vulnerability_scanner_tool"),
    "secret_scanner":        ("core.secret_scanner", "secret_scanner_tool"),
    # ── AI/ML ──
    "model_evaluator":       ("core.model_evaluator", "model_evaluator_tool"),
    "prompt_optimizer":      ("core.prompt_optimizer", "prompt_optimizer_tool"),
    # ── Docs ──
    "docstring_generator":   ("core.docstring_generator", "docstring_generator_tool"),
    "changelog_generator":   ("core.changelog_generator", "changelog_generator_tool"),

    # ── Batch 7: Excel/Office por voz ──
    "office_docs":           ("actions.office_tools", "office_docs"),

    # ── Batch 8: Audio y volumen del sistema ──
    "system_volume":         ("actions.system_volume", "system_volume"),
    "screen_control":        ("actions.screen_control", "screen_control"),

    # ── Batch 9: APIs externas (Aug 2026) ──
    "wolfram_alpha":         ("actions.wolfram_alpha", "wolfram_alpha"),

    # ── Jarvis OS: HUD terminal + rutinas diarias ──
    "hud_terminal":          ("core.hud_terminal", "hud_terminal"),
    "rutinas_diarias":       ("actions.rutinas_diarias", "rutinas_diarias"),

    # ── Level 10: Super Capabilities (Aug 2026) ──
    "web_search":            ("actions.web_search", "web_search"),
    "browser_auto":          ("actions.browser_auto", "browser_auto"),
    "browser_unified":       ("actions.browser_unified", "browser_unified"),
    "code_sandbox":          ("core.code_sandbox", "code_sandbox"),
    "advanced_rag":          ("core.advanced_rag", "advanced_rag_tool"),
    "voice_biometrics":      ("core.voice_biometrics", "voice_biometrics"),
    "proactive_monitor":     ("core.proactive_monitor", "monitoring_tool"),
    "email_calendar_deep":   ("core.email_calendar_deep", "email_calendar_deep"),
    "knowledge_graph_adv":   ("core.knowledge_graph_advanced", "knowledge_graph_tool"),
    "multi_user_profiles":   ("core.multi_user_profiles", "multi_user_tool"),
    "workflow_engine":       ("core.workflow_engine", "workflow_engine_tool"),
    "llm_router":            ("core.llm_router", "llm_router_tool"),
    "mcp_server":            ("core.mcp_server", "mcp_server_tool"),
    "memory_consolidation":  ("core.memory_consolidation", "memory_consolidation_tool"),
    # ── Coding capabilities (M1-M4) ──
    "code_engineer":         ("core.code_engineer", "code_engineer"),
    "codebase_explorer":     ("core.codebase_explorer", "codebase_explorer"),
    "devops_pipeline":       ("core.devops_pipeline", "devops_pipeline"),
    "refactoring_engine":    ("core.refactoring_engine", "refactoring_engine"),
    "email_manager":         ("actions.email_manager", "email_manager"),
    "google_calendar":       ("actions.google_calendar", "google_calendar"),
    "task_manager":          ("actions.task_manager", "task_manager"),
    "home_assistant":        ("actions.home_assistant", "home_assistant"),
    "screen_context":        ("actions.screen_context", "screen_context"),
    "voice_cloning":         ("core.voice_cloning", "voice_cloning"),
    "rag_engine":            ("core.rag_engine", "rag_engine"),

    # ── Level 11: Extended Capabilities (Aug 2026) ──
    "translator":            ("actions.translator", "translator"),
    "pdf_generator":         ("actions.pdf_generator", "pdf_generator"),
    "rss_reader":            ("actions.rss_reader", "rss_reader"),
    "vault_passwords":       ("actions.vault_passwords", "vault_passwords"),
    "ssh_remote":            ("actions.ssh_remote", "ssh_remote"),
    "git_smart":             ("actions.git_smart", "git_smart"),
    "sql_manager":           ("actions.sql_manager", "sql_manager"),
    "spotify_control":       ("actions.spotify_control", "spotify_control"),
    "eris_updater":          ("core.updater", "eris_updater"),
    "memory_consolidator":   ("core.memory_consolidator", "memory_consolidator"),
    "habit_tracker":         ("actions.habit_tracker", "habit_tracker"),
    "chart_generator":       ("actions.chart_generator", "chart_generator"),
    "voice_translator":      ("core.voice_translator", "voice_translator"),

    # ── Level 12: Advanced Autonomy ──
    "auto_healer":           ("core.auto_healer", "auto_healer"),
    "image_generator":       ("actions.image_generator", "image_generator"),
    "clipboard_history":     ("actions.clipboard_history", "clipboard_history"),
    "finance_tracker":       ("actions.finance_tracker", "finance_tracker"),
    "multi_ai_hub":          ("core.multi_ai_hub", "tool_multi_ai_hub"),
    "knowledge_graph":       ("core.knowledge_graph", "knowledge_graph"),
    "test_generator":        ("core.test_generator", "test_generator"),
    # ── Mappings for renamed declarations ──
    "self_improve":          ("core.self_modify", "self_modify_tool"),
    "memory_search":         ("core.memory_consolidation", "memory_consolidation_tool"),
    "file_organizer":        ("actions.smart_file_organizer", "smart_file_organizer"),
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
