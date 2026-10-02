"""
Action Imports Registry
-----------------------
Centralized try/except import blocks for all action modules.
Importing this module sets every action name to its real object or None
if the action module is not installed.
"""

from memory.memory_manager import (
    load_memory, update_memory, format_memory_for_prompt,
)

try:
    from actions.file_processor import file_processor
except Exception:
    file_processor = None
try:
    from actions.open_app          import open_app
except Exception:
    open_app = None
try:
    from actions.weather_report    import weather_action
except Exception:
    weather_action = None
try:
    from actions.send_message      import send_message
except Exception:
    send_message = None
try:
    from actions.reminder          import reminder
except Exception:
    reminder = None
try:
    from actions.computer_settings import computer_settings
except Exception:
    computer_settings = None
try:
    from actions.screen_vision import screen_vision
except Exception:
    screen_vision = None
try:
    from actions.youtube_video     import youtube_video
except Exception:
    youtube_video = None
try:
    from actions.desktop           import desktop_control
except Exception:
    desktop_control = None
try:
    from actions.browser_control   import browser_control
except Exception:
    browser_control = None
try:
    from actions.visual_click import visual_click
except Exception:
    visual_click = None
try:
    from actions.file_controller   import file_controller
except Exception:
    file_controller = None
try:
    from actions.code_helper       import code_helper
except Exception:
    code_helper = None
try:
    from actions.dev_agent         import dev_agent
except Exception:
    dev_agent = None
try:
    from actions.web_search        import web_search as web_search_action, web_search
except Exception:
    web_search_action = None; web_search = None
try:
    from actions.paper_search      import paper_search
except Exception:
    paper_search = None
try:
    from actions.repo_discovery    import repo_discovery
except Exception:
    repo_discovery = None
try:
    from actions.computer_control  import computer_control
except Exception:
    computer_control = None
try:
    from actions.google_calendar   import google_calendar
except Exception:
    google_calendar = None
# Nuevos modulos ERIS
try:
    from actions.emo_core import emo_core, emo_tick, emo_task_done, emo_task_failed
except Exception:
    emo_core = emo_tick = emo_task_done = emo_task_failed = None

try:
    from actions.web_jobs import web_jobs, start_server
except Exception:
    web_jobs = start_server = None
try:
    from actions.obsidian_brain import obsidian_note
except Exception:
    obsidian_note = None
try:
    from actions.spotify_control   import spotify_control
except Exception:
    spotify_control = None
try:
    from actions.rgb_control       import rgb_control
except Exception:
    rgb_control = None
try:
    from actions.scheduler         import scheduler, start_runner
except Exception:
    scheduler = None; start_runner = None
try:
    from actions.gmail_control     import gmail_control
except Exception:
    gmail_control = None
try:
    from actions.rules_engine      import rules_engine, start_rules_runner, check_phrase_triggers, _run_action as _rules_run_action
except Exception:
    rules_engine = None; start_rules_runner = None; check_phrase_triggers = None; _rules_run_action = None
try:
    from actions.whatsapp          import whatsapp
except Exception:
    whatsapp = None
try:
    from actions.user_profile      import user_profile, record_action
except Exception:
    user_profile = None; record_action = None
try:
    from actions.goals             import goals
except Exception:
    goals = None
try:
    from actions.git_control       import git_control
except Exception:
    git_control = None
try:
    from actions.codebase          import codebase
except Exception:
    codebase = None
try:
    from actions.vscode_controller import vscode_controller
except Exception:
    vscode_controller = None
try:
    from actions.web_generator import web_generator
except Exception:
    web_generator = None
try:
    from actions.web_designer import web_designer
except Exception:
    web_designer = None
try:
    from actions.react_designer import react_designer
except Exception:
    react_designer = None
try:
    from actions.angular_designer import angular_designer
except Exception:
    angular_designer = None
try:
    from actions.vue_designer import vue_designer
except Exception:
    vue_designer = None
try:
    from actions.next_designer import next_designer
except Exception:
    next_designer = None
try:
    from actions.todowrite         import todowrite
except Exception:
    todowrite = None
try:
    from actions.knowledge_base    import knowledge_base
except Exception:
    knowledge_base = None
try:
    from actions.screen_recorder   import start_recording, stop_recording, recording_status
except Exception:
    start_recording = stop_recording = recording_status = None
try:
    from actions.translator  import translator
except Exception:
    translator = None
try:
    from actions.meeting_transcriber  import meeting_transcriber
except Exception:
    meeting_transcriber = None
try:
    from actions.network_monitor  import network_monitor
except Exception:
    network_monitor = None
try:
    from actions.quick_actions  import add, update, remove, list_actions, execute as qa_execute
except Exception:
    add = update = remove = list_actions = qa_execute = None
try:
    from actions.pdf_editor  import read_pdf, merge_pdfs, split_pdf, pdf_info, fill_form, add_signature
except Exception:
    read_pdf = merge_pdfs = split_pdf = pdf_info = fill_form = add_signature = None
try:
    from actions.context_menu  import install as ctx_install, uninstall as ctx_uninstall, status as ctx_status
except Exception:
    ctx_install = ctx_uninstall = ctx_status = None
try:
    from actions.sms_manager  import send_sms, history as sms_history, sms_status
except Exception:
    send_sms = sms_history = sms_status = None
try:
    from actions.dashboard_server  import start_dashboard, stop_dashboard, dashboard_status
except Exception:
    start_dashboard = stop_dashboard = dashboard_status = None
try:
    from actions.diagnostico import diagnostico
except Exception:
    diagnostico = None
try:
    from actions.windows_settings import windows_settings
except Exception:
    windows_settings = None
try:
    from actions.document_creator  import document_creator
except Exception:
    document_creator = None
try:
    from actions.document_handler  import document_handler
except Exception:
    document_handler = None
try:
    from actions.document_manager  import document_manager
except Exception:
    document_manager = None
try:
    from actions.web_navigation    import web_navigation
except Exception:
    web_navigation = None
try:
    from actions.image_generation  import image_generation
except Exception:
    image_generation = None
try:
    from actions.smart_home        import smart_home
except Exception:
    smart_home = None
try:
    from actions.camera_bus        import camera_bus
except Exception:
    camera_bus = None
# ── Section 14N: System Health & DevOps (integrar subsystem activo) ──
try:
    from core.system_health          import system_health_tool as system_health
except Exception:
    system_health = None
try:
    from actions.daily_health_report import daily_health_report
except Exception:
    daily_health_report = None
try:
    from core.devops_pipeline        import devops_pipeline
except Exception:
    devops_pipeline = None
try:
    from actions.self_evolution      import self_evolution
except Exception:
    self_evolution = None
try:
    from actions.security_scanner   import security_scanner
except Exception:
    security_scanner = None
try:
    from actions.reverse_engineering import reverse_engineering
except Exception:
    reverse_engineering = None
try:
    from actions.document_tool        import document_tool
except Exception:
    document_tool = None
try:
    from actions.huggingface          import huggingface
except Exception:
    huggingface = None
try:
    from actions.system_monitor    import system_monitor
except Exception:
    system_monitor = None
try:
    from actions.audio_diagnostic import audio_diagnostic
except Exception:
    audio_diagnostic = None
try:
    from actions.system_status import system_status
except Exception:
    system_status = None
try:
    from agents.system_monitor_agent import system_monitor_agent
except Exception:
    system_monitor_agent = None
try:
    from agents.deploy_agent import deploy_agent
except Exception:
    deploy_agent = None
try:
    from actions.tiktok_analyzer   import tiktok_analyzer
except Exception:
    tiktok_analyzer = None
try:
    from actions.terminal_agent    import terminal_agent
except Exception:
    terminal_agent = None
try:
    from actions.native_ui         import native_ui
except Exception:
    native_ui = None
try:
    from actions.accessibility          import accessibility
except Exception:
    accessibility = None
# Nombres legacy sin implementación (main.py los usa con `if X:` — dejarlos definidos en None).
eye_tracking = None
micro_movement = None
task_simplify = None
routine_gamify = None
try:
    from actions.screen_reader          import screen_reader
except Exception:
    screen_reader = None
try:
    from actions.accessibility_overlay  import accessibility_overlay
except Exception:
    accessibility_overlay = None
try:
    from actions.morning_brief     import morning_brief, already_briefed_today, mark_briefed
except Exception:
    morning_brief = None; already_briefed_today = None; mark_briefed = None
try:
    from actions.vision_guardian   import vision_guardian, start as _start_vision_guardian
except Exception:
    vision_guardian = None; _start_vision_guardian = None
try:
    from actions.eris_guardian import eris_guardian, start_monitor, stop_monitor, get_guardian_status
except Exception:
    eris_guardian = None; start_monitor = None; stop_monitor = None; get_guardian_status = None
try:
    from actions.openrouter_agent  import openrouter_agent
except Exception:
    openrouter_agent = None
try:
    from actions.eris_db import (
        convo_log, tool_log as db_tool_log, memory_set, memory_get, memory_all, memory_delete,
        know_add, know_search, know_by_topic,
        task_add, task_list, task_update, task_delete,
        profile_set, profile_get, error_log, db_stats, save_everywhere,
        episodic_add, episodic_recent, episodic_search, episodic_count,
        convo_search, convo_recent
    )
except Exception:
    convo_log = None; db_tool_log = None; memory_set = None; memory_get = None; memory_all = None; memory_delete = None
    know_add = None; know_search = None; know_by_topic = None
    task_add = None; task_list = None; task_update = None; task_delete = None
    profile_set = None; profile_get = None; error_log = None; db_stats = None
    save_everywhere = None
    episodic_add = None; episodic_recent = None; episodic_search = None; episodic_count = None
    convo_search = None; convo_recent = None
try:
    from actions.curiosity_engine import (
        curiosity_tell_joke, curiosity_tell_fact, curiosity_suggest_fun,
        curiosity_greeting, curiosity_laugh
    )
except Exception:
    curiosity_tell_joke = None; curiosity_tell_fact = None; curiosity_suggest_fun = None
    curiosity_greeting = None; curiosity_laugh = None
try:
    from actions.curiosity_engine import proactive_suggest, proactive_learn
except Exception:
    proactive_suggest = None; proactive_learn = None
try:
    from actions.auto_programmer import auto_programmer
except Exception:
    auto_programmer = None
try:
    from actions.self_edit import self_edit, self_modify
except Exception:
    self_edit = None
    self_modify = None
try:
    from actions.self_improvement_loop import self_improvement_loop
except Exception:
    self_improvement_loop = None
try:
    from actions.self_awareness import self_awareness
except Exception:
    self_awareness = None
try:
    from core.self_map import get_full_map, get_file_tree, get_recent_changes, get_capabilities, search_my_code
except Exception:
    get_full_map = None; get_file_tree = None; get_recent_changes = None; get_capabilities = None; search_my_code = None
try:
    from skills.skill_registry import skill_manage
except Exception:
    skill_manage = None
try:
    from skills.superpowers import superpowers_list, superpowers_tool_declaration
except Exception:
    superpowers_list = None; superpowers_tool_declaration = None
try:
    from core.plugin_manager import get_plugin_manager
except Exception:
    get_plugin_manager = None
try:
    from actions.app_installer import app_installer
except Exception:
    app_installer = None
try:
    from core.emotional_state import (
        get_emotional_state, adjust_emotion, react_to_success,
        react_to_failure, react_to_user_interaction, get_mood_description,
        get_tone_instruction, emotional_state_tool,
        detect_user_mood, react_to_user_text, get_face_expression,
    )
except Exception:
    get_emotional_state = None; adjust_emotion = None; react_to_success = None
    react_to_failure = None; react_to_user_interaction = None; get_mood_description = None
    get_tone_instruction = None; emotional_state_tool = None
    detect_user_mood = None; react_to_user_text = None; get_face_expression = None
try:
    from agents.opencode_bridge import opencode_task, recall_lessons
except Exception:
    opencode_task = None; recall_lessons = None
try:
    from actions.game_companion import game_companion
except Exception:
    game_companion = None
try:
    from actions.game_launcher import game_launcher
except Exception:
    game_launcher = None
try:
    from actions.search_background import search_background
except Exception:
    search_background = None
try:
    from actions.backup_system import backup_system
except Exception:
    backup_system = None
try:
    from actions.alarm_manager import alarm_manager
except Exception:
    alarm_manager = None
try:
    from actions.habit_predictor import habit_predictor
except Exception:
    habit_predictor = None
try:
    from actions.window_manager import window_manager
except Exception:
    window_manager = None
try:
    from actions.contextual_control import contextual_control
except Exception:
    contextual_control = None
try:
    from actions.proactive_automation import proactive_automation
except Exception:
    proactive_automation = None
try:
    from actions.smart_file_organizer import smart_file_organizer
except Exception:
    smart_file_organizer = None
try:
    from actions.tool_creator import tool_creator
except Exception:
    tool_creator = None
try:
    from actions.unified_communications import unified_communications
except Exception:
    unified_communications = None
try:
    from actions.file_monitor import file_monitor
except Exception:
    file_monitor = None
try:
    from actions.task_manager import task_manager
except Exception:
    task_manager = None
try:
    from actions.system_reader import system_reader
except Exception:
    system_reader = None
try:
    from actions.webfetch import webfetch
except Exception:
    webfetch = None
try:
    from actions.document_generator import document_generator
except Exception:
    document_generator = None
try:
    from actions.presentation_generator import presentation_generator
except Exception:
    presentation_generator = None
try:
    from actions.spreadsheet_generator import spreadsheet_generator
except Exception:
    spreadsheet_generator = None
try:
    from actions.ask_user import ask_user
except Exception:
    ask_user = None
try:
    from actions.subagent_task import subagent_task
except Exception:
    subagent_task = None

try:
    from actions.emotional_growth import emotional_growth, on_user_message as _eg_on_user_msg, on_tool_result as _eg_on_tool_result
except Exception:
    emotional_growth = None; _eg_on_user_msg = None; _eg_on_tool_result = None
try:
    from actions.mobile_server import start as _mobile_start, broadcast as _mobile_broadcast
except Exception:
    _mobile_start = None; _mobile_broadcast = None
try:
    from actions.ollama_provider import is_available as _ollama_check, chat as _ollama_chat
except Exception:
    _ollama_check = None; _ollama_chat = None
try:
    from actions.research_agent import research
except Exception:
    research = None
try:
    from actions.autonomous_agent import screen_see, screen_where_to_click, screen_whats_there
except Exception:
    screen_see = None; screen_where_to_click = None; screen_whats_there = None
try:
    from actions.english_teacher import english_teacher
except Exception:
    english_teacher = None
try:
    from actions.cybersecurity import cybersecurity
except Exception:
    cybersecurity = None
try:
    from actions.credential_recovery import credential_recovery
except Exception:
    credential_recovery = None
try:
    from actions.osint_agent import osint_agent
except Exception:
    osint_agent = None
try:
    from actions.security_shield import security_shield
except Exception:
    security_shield = None
try:
    from actions.self_protection import self_protection
except Exception:
    self_protection = None
try:
    from actions.video_analyzer import video_analyzer
except Exception:
    video_analyzer = None
try:
    from actions.pc_control import pc_control
except Exception:
    pc_control = None
try:
    from actions.reminders import reminders
except Exception:
    reminders = None
try:
    from actions.calculator import calculator
except Exception:
    calculator = None
try:
    from actions.file_manager import file_manager
except Exception:
    file_manager = None
try:
    from actions.music_player import music_player
except Exception:
    music_player = None
try:
    from actions.fun_mode import fun_mode
except Exception:
    fun_mode = None
try:
    from actions.email_manager import email_manager
except Exception:
    email_manager = None
try:
    from actions.calendar_manager import calendar_manager
except Exception:
    calendar_manager = None
try:
    from actions.clipboard_manager import clipboard_manager
except Exception:
    clipboard_manager = None
try:
    from actions.active_firewall import active_firewall
except Exception:
    active_firewall = None
try:
    from actions.file_encryptor import file_encryptor
except Exception:
    file_encryptor = None
try:
    from actions.task_scheduler import task_scheduler
except Exception:
    task_scheduler = None
try:
    from actions.auto_agent import auto_agent
except Exception:
    auto_agent = None
try:
    from actions.code_generator import code_generator
except Exception:
    code_generator = None
try:
    from actions.memory_rag import memory_rag
except Exception:
    memory_rag = None
try:
    from actions.context_engine import context_engine
except Exception:
    context_engine = None
try:
    from actions.smart_browser import smart_browser
except Exception:
    smart_browser = None
try:
    from actions.text_summarizer import text_summarizer
except Exception:
    text_summarizer = None
try:
    from actions.ocr_reader import ocr_reader
except Exception:
    ocr_reader = None
try:
    from actions.image_analyzer import image_analyzer
except Exception:
    image_analyzer = None
try:
    from actions.audio_transcriber import audio_transcriber
except Exception:
    audio_transcriber = None
try:
    from actions.data_analyst import data_analyst
except Exception:
    data_analyst = None
try:
    from actions.pdf_manager import pdf_manager
except Exception:
    pdf_manager = None
try:
    from actions.template_engine import template_engine
except Exception:
    template_engine = None
try:
    from actions.browser_history import browser_history
except Exception:
    browser_history = None
try:
    from actions.process_manager import process_manager
except Exception:
    process_manager = None
try:
    from actions.driver_manager import driver_manager
except Exception:
    driver_manager = None
try:
    from actions.whatsapp_web import whatsapp_web
except Exception:
    whatsapp_web = None
try:
    from actions.telegram_bot import telegram_bot
except Exception:
    telegram_bot = None
try:
    from actions.phone_control import phone_control
except Exception:
    phone_control = None
try:
    from actions.notification_center import notification_center
except Exception:
    notification_center = None
try:
    from actions.voice_clone import voice_clone
except Exception:
    voice_clone = None
try:
    from actions.real_time_tts import real_time_tts
except Exception:
    real_time_tts = None
try:
    from actions.keylogger_detector import keylogger_detector
except Exception:
    keylogger_detector = None
try:
    from actions.usb_monitor import usb_monitor
except Exception:
    usb_monitor = None
try:
    from actions.ransomware_shield import ransomware_shield
except Exception:
    ransomware_shield = None
try:
    from actions.darkweb_monitor import darkweb_monitor
except Exception:
    darkweb_monitor = None
try:
    from actions.disk_wiper import disk_wiper
except Exception:
    disk_wiper = None

# ── Section 14M: New 16 Features (Jul 2026) ──
try:
    from actions.memory_consolidation import memory_consolidate
except Exception:
    memory_consolidation = None
try:
    from actions.flow_recorder import flow_recorder
except Exception:
    flow_recorder = None
try:
    from actions.screenshot_history import screenshot_history
except Exception:
    screenshot_history = None
try:
    from actions.multi_user import multi_user
except Exception:
    multi_user = None
try:
    from actions.voice_cloning import voice_cloning as voice_cloning_new
except Exception:
    voice_cloning_new = None
try:
    from actions.browser_extension import browser_extension
except Exception:
    browser_extension = None
try:
    from actions.smart_notifications import smart_notifications
except Exception:
    smart_notifications = None
try:
    from actions.usage_analytics import usage_analytics
except Exception:
    usage_analytics = None
try:
    from actions.skill_marketplace import skill_marketplace
except Exception:
    skill_marketplace = None
try:
    from actions.api_server import api_server
except Exception:
    api_server = None
try:
    from actions.federated_learning import federated_learning
except Exception:
    federated_learning = None
try:
    from actions.data_encryption import data_encryption
except Exception:
    data_encryption = None
try:
    from actions.auto_backup import auto_backup
except Exception:
    auto_backup = None
try:
    from actions.plugin_marketplace import plugin_marketplace
except Exception:
    plugin_marketplace = None
try:
    from actions.proactive_ia import proactive_ia
except Exception:
    proactive_ia = None
try:
    from actions.voice_enhanced import voice_enhanced
except Exception:
    voice_enhanced = None
try:
    from actions.data_viz import data_viz
except Exception:
    data_viz = None
try:
    from actions.i18n import i18n
except Exception:
    i18n = None
try:
    from actions.code_review import code_review
except Exception:
    code_review = None
try:
    from actions.code_analyzer import code_analyzer
except Exception:
    code_analyzer = None
try:
    from actions.web_scraper import web_scraper
except Exception:
    web_scraper = None
try:
    from actions.dashboard_web import dashboard_web
except Exception:
    dashboard_web = None
try:
    from actions.docker_deploy import docker_deploy
except Exception:
    docker_deploy = None
try:
    from actions.ci_cd import ci_cd
except Exception:
    ci_cd = None
try:
    from actions.i18n_ui import i18n_ui
except Exception:
    i18n_ui = None
try:
    from actions.voice_cloning_real import voice_cloning_real
except Exception:
    voice_cloning_real = None
# ── Batch 3 ──
try:
    from actions.sandbox_execution import sandbox_execution
except Exception:
    sandbox_execution = None
try:
    from actions.knowledge_graph import knowledge_graph
except Exception:
    knowledge_graph = None
try:
    from actions.theme_manager import theme_manager
except Exception:
    theme_manager = None
try:
    from actions.plugin_loader import plugin_loader
except Exception:
    plugin_loader = None
try:
    from actions.smart_cache import smart_cache
except Exception:
    smart_cache = None
try:
    from actions.config_export import config_export
except Exception:
    config_export = None
try:
    from actions.desktop_notifications import desktop_notifications
except Exception:
    desktop_notifications = None
# ── Batch 4: Complete Training ──
try:
    from actions.self_heal import self_heal
except Exception:
    self_heal = None
try:
    from actions.self_healing_loop import self_healing_loop
except Exception:
    self_healing_loop = None
try:
    from actions.role_orchestrator import role_orchestrator
except Exception:
    role_orchestrator = None
try:
    from actions.speaker_recognition import speaker_recognition
except Exception:
    speaker_recognition = None
try:
    from actions.data_visualize import data_visualize
except Exception:
    data_visualize = None
try:
    from actions.workflow_runner import workflow_runner
except Exception:
    workflow_runner = None
try:
    from actions.self_extend import self_extend
except Exception:
    self_extend = None
try:
    from actions.agent_task import agent_task
except Exception:
    agent_task = None
try:
    from actions.ask_opencode import ask_opencode
except Exception:
    ask_opencode = None
try:
    from actions.conversation_search import conversation_search
except Exception:
    conversation_search = None
try:
    from actions.curiosity_fact import curiosity_fact
except Exception:
    curiosity_fact = None
try:
    from actions.curiosity_fun import curiosity_fun
except Exception:
    curiosity_fun = None
try:
    from actions.curiosity_joke import curiosity_joke
except Exception:
    curiosity_joke = None
try:
    from actions.curiosity_trending import curiosity_trending
except Exception:
    curiosity_trending = None
try:
    from actions.dashboard import dashboard
except Exception:
    dashboard = None
try:
    from actions.db_knowledge import db_knowledge
except Exception:
    db_knowledge = None
try:
    from actions.db_memory import db_memory
except Exception:
    db_memory = None
try:
    from actions.db_tasks import db_tasks
except Exception:
    db_tasks = None
try:
    from actions.episodic_log import episodic_log
except Exception:
    episodic_log = None
try:
    from actions.eris_ui_control import eris_ui_control
except Exception:
    eris_ui_control = None
try:
    from actions.full_training import full_training
except Exception:
    full_training = None
try:
    from actions.learn_from_mistake import learn_from_mistake
except Exception:
    learn_from_mistake = None
try:
    from actions.learn_session import learn_session
except Exception:
    learn_session = None
try:
    from actions.play_direct import play_direct
except Exception:
    play_direct = None
try:
    from actions.plugin_manage import plugin_manage
except Exception:
    plugin_manage = None
try:
    from actions.predict_analyze import predict_analyze
except Exception:
    predict_analyze = None
try:
    from actions.res_monitor import res_monitor
except Exception:
    res_monitor = None
try:
    from actions.res_protect import res_protect
except Exception:
    res_protect = None
try:
    from actions.save_memory import save_memory
except Exception:
    save_memory = None
try:
    from actions.search_info import search_info
except Exception:
    search_info = None
try:
    from actions.shutdown_eris import shutdown_eris
except Exception:
    shutdown_eris = None
try:
    from actions.sleep_mode import sleep_mode
except Exception:
    sleep_mode = None
try:
    from actions.sms import sms
except Exception:
    sms = None
try:
    from actions.superpowers_activate import superpowers_activate
except Exception:
    superpowers_activate = None
try:
    from actions.task_queue import task_queue
except Exception:
    task_queue = None
try:
    from actions.roadmap import roadmap
except Exception:
    roadmap = None
try:
    from core.emotional_core import emotional_core_tool as emotional_core
except Exception:
    emotional_core = None
try:
    from core.observer import observer_tool as observer
except Exception:
    observer = None
try:
    from core.code_guard import code_guard_tool as guard
except Exception:
    guard = None
try:
    from core.mission_agent import mission_tool as mission
except Exception:
    mission = None
try:
    from core.self_evolution import self_evolution_tool as evolucion
except Exception:
    evolucion = None
try:
    from core.evolution_campaigns import evolve_campaigns as evolution_campaigns
except Exception:
    evolution_campaigns = None
try:
    from core.learning_engine import learning_engine
except Exception:
    learning_engine = None
try:
    from actions.aprendizaje_videos import aprendizaje_videos
except Exception:
    aprendizaje_videos = None
try:
    from core.auto_defensa import auto_defensa
except Exception:
    auto_defensa = None
# ── Batch 5: Connectivity + Self-Healing ──
try:
    from core.connectivity import connectivity_tool
except Exception:
    connectivity_tool = None
try:
    from core.self_healing import self_healing_tool as self_healing
except Exception:
    self_healing = None
try:
    from core.superinteligencia import error_recovery
except Exception:
    error_recovery = None
try:
    from core.mcp_server import mcp_server_tool as mcp_server
except Exception:
    mcp_server = None
# ── Batch 6: Page/Video Summarizer ──
try:
    from actions.page_summarizer import page_summarizer
except Exception:
    page_summarizer = None


# ── Hermes: Herramientas de Seguridad P0 (wirear) ──
try:
    from core.code_guard import code_guard_tool as code_guard
except Exception:
    code_guard = None
try:
    from core.pentest_lab import pentest_lab
except Exception:
    pentest_lab = None
try:
    from core.permission_gate import get_permission_gate as permission_gate
except Exception:
    permission_gate = None
try:
    from core.permission_gate import permission_policy_tool as permission_policy
except Exception:
    permission_policy = None
try:
    from core.secret_scanner import secret_scanner_tool as secret_scanner
except Exception:
    secret_scanner = None
try:
    from core.dep_vulnerability_scanner import dep_vulnerability_scanner_tool as dep_vuln_scanner
except Exception:
    dep_vuln_scanner = None
try:
    from agents.guardiana_agent import guardiana
except Exception:
    guardiana = None

# ── Hermes: AI/LLM/Memory/Learning — Wireado automático ──
try:
    from core.memory_unified import get_memory as memory_unified
except Exception:
    memory_unified = None
try:
    from core.memory_consolidation import memory_consolidation_tool as memory_consolidation
except Exception:
    memory_consolidation = None
try:
    from core.model_evaluator import model_evaluator_tool as model_evaluator
except Exception:
    model_evaluator = None
try:
    from core.prompt_optimizer import prompt_optimizer_tool as prompt_optimizer
except Exception:
    prompt_optimizer = None
try:
    from core.llm_router import llm_router_tool as llm_router
except Exception:
    llm_router = None
try:
    from core.advanced_rag import advanced_rag_tool as advanced_rag
except Exception:
    advanced_rag = None
try:
    from core.rag_engine import rag_engine as rag_engine
except Exception:
    rag_engine = None
try:
    from core.context_bridge import answer_question as context_bridge
except Exception:
    context_bridge = None
try:
    from core.contextual_awareness import contextual_awareness_tool as contextual_awareness
except Exception:
    contextual_awareness = None
try:
    from core.agent_as_tool import create_sub_agent as agent_as_tool
except Exception:
    agent_as_tool = None
try:
    from core.agent_bus import get_agent_bus as agent_bus
except Exception:
    agent_bus = None
try:
    from core.multi_ai_hub import tool_multi_ai_hub as multi_ai_hub
except Exception:
    multi_ai_hub = None
try:
    from core.self_evolving_prompts import add_rule as self_evolving_prompts
except Exception:
    self_evolving_prompts = None
try:
    from core.self_explainer import explain_decision as self_explainer
except Exception:
    self_explainer = None
try:
    from core.self_map import get_capabilities as self_map
except Exception:
    self_map = None
try:
    from core.task_engine import TaskEngine as task_engine
except Exception:
    task_engine = None
try:
    from core.task_planner import task_planner_tool as task_planner
except Exception:
    task_planner = None
try:
    from core.workflow_builder import workflow_builder_tool as workflow_builder
except Exception:
    workflow_builder = None
try:
    from core.workflow_engine import workflow_engine_tool as workflow_engine
except Exception:
    workflow_engine = None
try:
    from core.world_model import get_world_model as world_model
except Exception:
    world_model = None
try:
    from core.progressive_context import build_progressive_context as progressive_context
except Exception:
    progressive_context = None
try:
    from core.prompt_compressor import compress_history as prompt_compressor
except Exception:
    prompt_compressor = None
try:
    from core.learning_curriculum import complete_exercise as learning_curriculum
except Exception:
    learning_curriculum = None
try:
    from core.emotional_memory import emotional_memory_tool as emotional_memory
except Exception:
    emotional_memory = None
try:
    from core.voice_biometrics import voice_biometrics as voice_biometrics
except Exception:
    voice_biometrics = None
try:
    from core.voice_memory import voice_memory_tool as voice_memory
except Exception:
    voice_memory = None
try:
    from core.voice_profile import voice_profile_tool as voice_profile
except Exception:
    voice_profile = None
try:
    from core.voice_recognition import voice_recognition as voice_recognition
except Exception:
    voice_recognition = None
try:
    from core.voice_translator import voice_translator as voice_translator
except Exception:
    voice_translator = None
try:
    from core.batch_executor import as_completed as batch_executor
except Exception:
    batch_executor = None


# ── Hermes: Herramientas Hermes ──
try:
    from core.hermes_tools import hermes_web_search as hermes_web_search
except Exception:
    hermes_web_search = None
try:
    from core.hermes_tools import hermes_web_scraper as hermes_web_scraper
except Exception:
    hermes_web_scraper = None
try:
    from core.hermes_tools import hermes_page_summarizer as hermes_page_summarizer
except Exception:
    hermes_page_summarizer = None
try:
    from core.hermes_tools import hermes_feed_monitor as hermes_feed_monitor
except Exception:
    hermes_feed_monitor = None
try:
    from core.hermes_tools import hermes_csv_processor as hermes_csv_processor
except Exception:
    hermes_csv_processor = None
try:
    from core.hermes_tools import hermes_data_analyzer as hermes_data_analyzer
except Exception:
    hermes_data_analyzer = None
try:
    from core.hermes_tools import hermes_writer_articles as hermes_writer_articles
except Exception:
    hermes_writer_articles = None
try:
    from core.hermes_tools import hermes_email_writer as hermes_email_writer
except Exception:
    hermes_email_writer = None
try:
    from core.hermes_tools import hermes_test_generator as hermes_test_generator
except Exception:
    hermes_test_generator = None
try:
    from core.hermes_tools import hermes_code_review as hermes_code_review
except Exception:
    hermes_code_review = None
try:
    from core.hermes_tools import hermes_security_audit as hermes_security_audit
except Exception:
    hermes_security_audit = None
try:
    from core.hermes_tools import hermes_github_sync as hermes_github_sync
except Exception:
    hermes_github_sync = None
try:
    from core.hermes_tools import hermes_tools as hermes_tools
except Exception:
    hermes_tools = None

# ── Hermes: Wireado pase 2 — herramientas existentes restantes ──
try:
    from actions.app_discovery import app_discovery as app_discovery
except Exception:
    app_discovery = None
try:
    from actions.github_pr import github_pr as github_pr
except Exception:
    github_pr = None
try:
    from actions.gustos import gustos as gustos
except Exception:
    gustos = None
try:
    from actions.relationship import relationship as relationship
except Exception:
    relationship = None
try:
    from actions.cancion_generator import cancion_generator as cancion_generator
except Exception:
    cancion_generator = None
try:
    from actions.code_copilot import code_copilot as code_copilot
except Exception:
    code_copilot = None
try:
    from actions.ide_integration import ide_integration as ide_integration
except Exception:
    ide_integration = None
try:
    from actions.code_assistant import full_scan as code_assistant
except Exception:
    code_assistant = None
try:
    from actions.human_mouse import human_mouse as human_mouse
except Exception:
    human_mouse = None
try:
    from actions.super_search import super_search as super_search
except Exception:
    super_search = None
try:
    from actions.deep_research import deep_research as deep_research
except Exception:
    deep_research = None
try:
    from core.file_undo import tool_undo as undo
except Exception:
    undo = None
try:
    from actions.knowledge_ingestor import knowledge_ingestor as knowledge_ingestor
except Exception:
    knowledge_ingestor = None
try:
    from actions.data_connectors import data_connectors as data_connectors
except Exception:
    data_connectors = None
try:
    from actions.document_rag import document_rag as document_rag
except Exception:
    document_rag = None
try:
    from actions.personality import personality_engine as personality
except Exception:
    personality = None
try:
    from core.emotional_state import emotional_state_tool as emotional_state
except Exception:
    emotional_state = None
try:
    from core.style_engine import eris_style as eris_style
except Exception:
    eris_style = None
try:
    from core.daily_digest import daily_digest_tool as daily_digest
except Exception:
    daily_digest = None
try:
    from actions.file_editor import file_editor as file_editor
except Exception:
    file_editor = None
try:
    from actions.context_files import context_read as context_read
except Exception:
    context_read = None
try:
    from actions.context_files import context_update as context_update
except Exception:
    context_update = None
try:
    from actions.memory_nudge import memory_nudge as memory_nudge
except Exception:
    memory_nudge = None
try:
    from actions.game_agent import game_agent as game_agent
except Exception:
    game_agent = None
try:
    from actions.terminal_agent import terminal_agent as shell_executor
except Exception:
    shell_executor = None
try:
    from actions.git_daily import git_daily as git_daily
except Exception:
    git_daily = None
try:
    from actions.self_regression import self_regression as self_regression
except Exception:
    self_regression = None
try:
    from actions.dependency_manager import dependency_manager as dependency_manager
except Exception:
    dependency_manager = None
try:
    from actions.tool_benchmark import tool_benchmark as tool_benchmark
except Exception:
    tool_benchmark = None
try:
    from actions.multi_search import multi_search as multi_search
except Exception:
    multi_search = None
try:
    from actions.code_validator import code_validator as code_validator
except Exception:
    code_validator = None
try:
    from actions.parallel_agents import parallel_agents as parallel_agents
except Exception:
    parallel_agents = None
try:
    from actions.program_manager import program_manager as program_manager
except Exception:
    program_manager = None
try:
    from actions.mcp_tool import mcp_tool as mcp_tool
except Exception:
    mcp_tool = None
try:
    from core.autonomous_learner import autonomous_learner as autonomous_learner
except Exception:
    autonomous_learner = None
try:
    from actions.curiosity_engine import curiosity_tell_fact as curiosity_engine
except Exception:
    curiosity_engine = None
try:
    from core.agi_tools import agi_memory as agi_memory
except Exception:
    agi_memory = None
try:
    from core.agi_tools import agi_self_improve as agi_self_improve
except Exception:
    agi_self_improve = None
try:
    from core.agi_tools import agi_reasoning as agi_reasoning
except Exception:
    agi_reasoning = None
try:
    from core.agi_tools import agi_world_model as agi_world_model
except Exception:
    agi_world_model = None
try:
    from core.agi_tools import agi_agent as agi_agent
except Exception:
    agi_agent = None
try:
    from core.agent_architecture import agent_loop as agent_loop
except Exception:
    agent_loop = None
try:
    from core.updater import check_for_update as eris_update
except Exception:
    eris_update = None
try:
    from core.model_router import status as ollama_status
except Exception:
    ollama_status = None
try:
    from core.tts_engine import tts_set_voice as tts_set_voice
except Exception:
    tts_set_voice = None
try:
    from actions.show_expression import show_expression as show_expression
except Exception:
    show_expression = None
try:
    from core.superinteligencia import reflection as reflection
except Exception:
    reflection = None
try:
    from core.superinteligencia import skill_recommender as skill_recommender
except Exception:
    skill_recommender = None
try:
    from core.superinteligencia import tool_cache as tool_cache
except Exception:
    tool_cache = None
try:
    from core.superinteligencia import verification_layer as verification_layer
except Exception:
    verification_layer = None
try:
    from core.superinteligencia import plan_adaptation as plan_adaptation
except Exception:
    plan_adaptation = None
try:
    from core.superinteligencia import knowledge_distiller as knowledge_distiller
except Exception:
    knowledge_distiller = None
try:
    from core.superinteligencia import cost_tracker as cost_tracker
except Exception:
    cost_tracker = None
try:
    from core.superinteligencia import intent_classifier as intent_classifier
except Exception:
    intent_classifier = None
try:
    from core.superinteligencia import conversation_brancher as conversation_brancher
except Exception:
    conversation_brancher = None
try:
    from core.superinteligencia import auto_documenter as auto_documenter
except Exception:
    auto_documenter = None
try:
    from core.superinteligencia import tool_dep_graph as tool_dep_graph
except Exception:
    tool_dep_graph = None
try:
    from core.superinteligencia import smart_retry as smart_retry
except Exception:
    smart_retry = None
try:
    from core.superinteligencia import semantic_deduplicator as semantic_deduplicator
except Exception:
    semantic_deduplicator = None
try:
    from core.superinteligencia import adaptive_temperature as adaptive_temperature
except Exception:
    adaptive_temperature = None
try:
    from core.superinteligencia import task_tree as task_tree
except Exception:
    task_tree = None
try:
    from core.superinteligencia import proactive_suggester as proactive_suggester
except Exception:
    proactive_suggester = None
try:
    from core.superinteligencia import conversation_replayer as conversation_replayer
except Exception:
    conversation_replayer = None
try:
    from core.superinteligencia import context_optimizer as context_optimizer
except Exception:
    context_optimizer = None
try:
    from core.superinteligencia import skill_creator as skill_creator
except Exception:
    skill_creator = None
try:
    from core.superinteligencia import session_debugger as session_debugger
except Exception:
    session_debugger = None
try:
    from core.superinteligencia import capability_assessor as capability_assessor
except Exception:
    capability_assessor = None
try:
    from core.superinteligencia import feedback_learner as feedback_learner
except Exception:
    feedback_learner = None
try:
    from core.superinteligencia import meta_reasoner as meta_reasoner
except Exception:
    meta_reasoner = None
try:
    from core.superinteligencia import multi_agent as multi_agent
except Exception:
    multi_agent = None
try:
    from core.superinteligencia import session_analytics as session_analytics
except Exception:
    session_analytics = None
try:
    from core.superinteligencia import knowledge_verifier as knowledge_verifier
except Exception:
    knowledge_verifier = None
try:
    from core.superinteligencia import dream_consolidator as dream_consolidator
except Exception:
    dream_consolidator = None
try:
    from core.superinteligencia import goal_tracker as goal_tracker
except Exception:
    goal_tracker = None
try:
    from core.superinteligencia import anomaly_detector as anomaly_detector
except Exception:
    anomaly_detector = None
try:
    from core.superinteligencia import confidence_scorer as confidence_scorer
except Exception:
    confidence_scorer = None
try:
    from core.superinteligencia import mistake_learner as mistake_learner
except Exception:
    mistake_learner = None
try:
    from core.superinteligencia import file_profiler as file_profiler
except Exception:
    file_profiler = None
try:
    from actions.pdf_editor import pdf_editor as pdf_editor
except Exception:
    pdf_editor = None
try:
    from actions.context_menu import context_menu as context_menu
except Exception:
    context_menu = None
try:
    from core.ast_editor import analyze_file as ast_analyze
except Exception:
    ast_analyze = None
try:
    from core.ast_editor import safe_edit as ast_edit
except Exception:
    ast_edit = None
try:
    from core.shell_session import run_shell_tool as shell_session
except Exception:
    shell_session = None
try:
    from actions.wayland_input import wayland_input as wayland_input
except Exception:
    wayland_input = None
try:
    from actions.kde_connect import kde_connect as kde_connect
except Exception:
    kde_connect = None
try:
    from actions.ocr_tool import ocr_tool as ocr_tool
except Exception:
    ocr_tool = None
try:
    from actions.git_autonomo import git_autonomo as git_autonomo
except Exception:
    git_autonomo = None
try:
    from agents.agenlix_agent import agelix as agelix
except Exception:
    agelix = None
try:
    from agents.mentora_agent import mentora as mentora
except Exception:
    mentora = None
try:
    from actions.context7 import handle_context7 as context7
except Exception:
    context7 = None
try:
    from core.lsp_manager import lsp_tool as lsp_manager
except Exception:
    lsp_manager = None
try:
    from core.mcp_manager import mcp_tool as mcp_manager
except Exception:
    mcp_manager = None
try:
    from core.compaction import compaction_tool as compaction
except Exception:
    compaction = None
try:
    from core.neural_bridge import neural_bridge_tool as neural_bridge
except Exception:
    neural_bridge = None
try:
    from core.world_simulation import world_simulation_tool as world_simulation
except Exception:
    world_simulation = None
try:
    from core.emotional_rl import emotional_rl_tool as emotional_rl
except Exception:
    emotional_rl = None
try:
    from core.neuro_spheres import neuro_spheres as neuro_spheres
except Exception:
    neuro_spheres = None
try:
    from core.cognitive_modules import chain_of_thought as chain_of_thought
except Exception:
    chain_of_thought = None
try:
    from core.cognitive_modules import multi_perspective as multi_perspective
except Exception:
    multi_perspective = None
try:
    from core.cognitive_modules import analogical_reasoning as analogical_reasoning
except Exception:
    analogical_reasoning = None
try:
    from core.cognitive_modules import hypothesis_generator as hypothesis_generator
except Exception:
    hypothesis_generator = None
try:
    from core.cognitive_modules import social_dynamics as social_dynamics
except Exception:
    social_dynamics = None
try:
    from core.cognitive_modules import ethical_reasoning as ethical_reasoning
except Exception:
    ethical_reasoning = None
try:
    from core.cognitive_modules import storytelling_engine as storytelling_engine
except Exception:
    storytelling_engine = None
try:
    from core.cognitive_modules import teaching_optimizer as teaching_optimizer
except Exception:
    teaching_optimizer = None
try:
    from core.cognitive_modules import debate_engine as debate_engine
except Exception:
    debate_engine = None
try:
    from core.cognitive_modules import temporal_reasoning as temporal_reasoning
except Exception:
    temporal_reasoning = None
try:
    from core.cognitive_modules import cognitive_modules as cognitive_modules
except Exception:
    cognitive_modules = None
try:
    from core.cognitive_modules import meta_cognition as meta_cognition
except Exception:
    meta_cognition = None
try:
    from core.cognitive_modules import self_model as self_model
except Exception:
    self_model = None
try:
    from core.cognitive_modules import confidence_calibration as confidence_calibration
except Exception:
    confidence_calibration = None
try:
    from core.cognitive_modules import contradiction_detection as contradiction_detection
except Exception:
    contradiction_detection = None
try:
    from core.cognitive_modules import assumption_detection as assumption_detection
except Exception:
    assumption_detection = None
try:
    from core.cognitive_modules import goal_management as goal_management
except Exception:
    goal_management = None
try:
    from core.cognitive_modules import attention_management as attention_management
except Exception:
    attention_management = None
try:
    from core.cognitive_modules import transfer_learning as transfer_learning
except Exception:
    transfer_learning = None
try:
    from core.cognitive_modules import abstraction as abstraction
except Exception:
    abstraction = None
try:
    from core.cognitive_modules import principled_reasoning as principled_reasoning
except Exception:
    principled_reasoning = None
try:
    from core.cognitive_modules import intellectual_humility as intellectual_humility
except Exception:
    intellectual_humility = None
try:
    from core.cognitive_modules import creative_generation as creative_generation
except Exception:
    creative_generation = None
try:
    from core.cognitive_modules import meta_communication as meta_communication
except Exception:
    meta_communication = None
try:
    from core.cognitive_modules import bias_detection as bias_detection
except Exception:
    bias_detection = None
try:
    from actions.superpowers_skill import superpowers_skill as superpowers_skill
except Exception:
    superpowers_skill = None
try:
    from core.self_health import self_health_tool as auto_salud
except Exception:
    auto_salud = None
try:
    from core.eris_fabrica import eris_fabrica as fabrica
except Exception:
    fabrica = None
try:
    from core.procedimientos import procedimientos as procedimientos
except Exception:
    procedimientos = None
try:
    from core.auto_fabrica import auto_fabrica as auto_fabrica
except Exception:
    auto_fabrica = None
try:
    from core.mcp_bridge import mcp_bridge as mcp_bridge
except Exception:
    mcp_bridge = None
try:
    from core.proactive_context import pro_contexto as pro_contexto
except Exception:
    pro_contexto = None
try:
    from core.prompt_ab_testing import prompt_ab as prompt_ab
except Exception:
    prompt_ab = None
try:
    from core.edit_journal import edit_journal as edit_journal
except Exception:
    edit_journal = None
try:
    from core.token_saver import token_saver as token_saver
except Exception:
    token_saver = None
try:
    from core.self_improvement import auto_mejora as auto_mejora
except Exception:
    auto_mejora = None
try:
    from core.session_summaries import sesiones as sesiones
except Exception:
    sesiones = None
try:
    from core.ab_automated import ab_automated as ab_automated
except Exception:
    ab_automated = None
try:
    from core.informe_semanal import informe_semanal as informe_semanal
except Exception:
    informe_semanal = None
try:
    from agents.memoria_agent import memoria as memoria
except Exception:
    memoria = None
try:
    from core.escalada import escalada_tool as escalada
except Exception:
    escalada = None
try:
    from core.autonomy import autonomy_tool as autonomy
except Exception:
    autonomy = None
try:
    from core.goal_setting import goal_setting_tool as goal_setting
except Exception:
    goal_setting = None
try:
    from core.identity_persistence import identity_persistence_tool as identity_persistence
except Exception:
    identity_persistence = None
try:
    from core.multilang_learning import multilang_learning_tool as multilang_learning
except Exception:
    multilang_learning = None
try:
    from core.tool_creation import tool_creation_tool as tool_creation
except Exception:
    tool_creation = None
try:
    from core.emotional_tone import emotional_tone_tool as emotional_tone
except Exception:
    emotional_tone = None
try:
    from core.natural_pauses import natural_pauses_tool as natural_pauses
except Exception:
    natural_pauses = None
try:
    from core.accent_personality import accent_personality_tool as accent_personality
except Exception:
    accent_personality = None
try:
    from core.sql_executor import sql_executor_tool as sql_executor
except Exception:
    sql_executor = None
try:
    from core.db_schema_visualizer import db_schema_visualizer_tool as db_schema_visualizer
except Exception:
    db_schema_visualizer = None
try:
    from core.test_runner import test_runner_tool as test_runner
except Exception:
    test_runner = None
try:
    from core.alert_rules import alert_rules_tool as alert_rules
except Exception:
    alert_rules = None
try:
    from core.docstring_generator import docstring_generator_tool as docstring_generator
except Exception:
    docstring_generator = None
try:
    from core.changelog_generator import changelog_generator_tool as changelog_generator
except Exception:
    changelog_generator = None
try:
    from actions.office_tools import office_docs as office_docs
except Exception:
    office_docs = None
try:
    from actions.wolfram_alpha import wolfram_alpha as wolfram_alpha
except Exception:
    wolfram_alpha = None
try:
    from core.hud_terminal import hud_terminal as hud_terminal
except Exception:
    hud_terminal = None
try:
    from actions.rutinas_diarias import rutinas_diarias as rutinas_diarias
except Exception:
    rutinas_diarias = None
try:
    from actions.browser_auto import browser_auto as browser_auto
except Exception:
    browser_auto = None
try:
    from actions.browser_unified import browser_unified as browser_unified
except Exception:
    browser_unified = None
try:
    from core.code_sandbox import code_sandbox as code_sandbox
except Exception:
    code_sandbox = None
try:
    from core.email_calendar_deep import email_calendar_deep as email_calendar_deep
except Exception:
    email_calendar_deep = None
try:
    from core.knowledge_graph_advanced import knowledge_graph_tool as knowledge_graph_adv
except Exception:
    knowledge_graph_adv = None
try:
    from core.multi_user_profiles import multi_user_tool as multi_user_profiles
except Exception:
    multi_user_profiles = None
try:
    from core.code_engineer import code_engineer as code_engineer
except Exception:
    code_engineer = None
try:
    from core.codebase_explorer import codebase_explorer as codebase_explorer
except Exception:
    codebase_explorer = None
try:
    from core.refactoring_engine import refactoring_engine as refactoring_engine
except Exception:
    refactoring_engine = None
try:
    from actions.home_assistant import home_assistant as home_assistant
except Exception:
    home_assistant = None
try:
    from core.memory_curation import curar_memoria as curar_memoria
except Exception:
    curar_memoria = None
try:
    from actions.pdf_generator import pdf_generator as pdf_generator
except Exception:
    pdf_generator = None
try:
    from actions.rss_reader import rss_reader as rss_reader
except Exception:
    rss_reader = None
try:
    from actions.vault_passwords import vault_passwords as vault_passwords
except Exception:
    vault_passwords = None
try:
    from actions.ssh_remote import ssh_remote as ssh_remote
except Exception:
    ssh_remote = None
try:
    from actions.git_smart import git_smart as git_smart
except Exception:
    git_smart = None
try:
    from actions.sql_manager import sql_manager as sql_manager
except Exception:
    sql_manager = None
try:
    from core.updater import eris_updater as eris_updater
except Exception:
    eris_updater = None
try:
    from core.memory_consolidator import memory_consolidator as memory_consolidator
except Exception:
    memory_consolidator = None
try:
    from actions.habit_tracker import habit_tracker as habit_tracker
except Exception:
    habit_tracker = None
try:
    from actions.chart_generator import chart_generator as chart_generator
except Exception:
    chart_generator = None
try:
    from actions.clipboard_history import clipboard_history as clipboard_history
except Exception:
    clipboard_history = None
try:
    from actions.finance_tracker import finance_tracker as finance_tracker
except Exception:
    finance_tracker = None
try:
    from core.test_generator import test_generator as test_generator
except Exception:
    test_generator = None
try:
    from core.self_modify import self_improve as self_improve
except Exception:
    self_improve = None
try:
    from core.cerebro import cerebro_tool as cerebro
except Exception:
    cerebro = None
try:
    from core.expression_engine import expression_tool as expresion_eris
except Exception:
    expresion_eris = None
try:
    from core.vida_interna import vida_interna_tool as vida_interna
except Exception:
    vida_interna = None
try:
    from core.relaciones import relaciones_tool as relaciones
except Exception:
    relaciones = None
try:
    from core.autoimagen import autoimagen_tool as autoimagen
except Exception:
    autoimagen = None
try:
    from core.intereses import intereses_tool as intereses
except Exception:
    intereses = None
try:
    from core.retrospectiva import retrospectiva_tool as retrospectiva
except Exception:
    retrospectiva = None
try:
    from core.ambiente import ambiente_tool as ambiente
except Exception:
    ambiente = None
try:
    from core.suenos import sueno_tool as suenos
except Exception:
    suenos = None
try:
    from core.caprichos import caprichos_tool as caprichos
except Exception:
    caprichos = None
try:
    from core.tiempo_interno import tiempo_interno_tool as tiempo_interno
except Exception:
    tiempo_interno = None
try:
    from core.festejos import festejos_tool as festejos
except Exception:
    festejos = None
try:
    from core.bienestar import bienestar_tool as bienestar
except Exception:
    bienestar = None
try:
    from core.cuadernos import cuadernos_tool as cuadernos
except Exception:
    cuadernos = None
try:
    from core.despedidas import despedidas_tool as despedidas
except Exception:
    despedidas = None
try:
    from core.todo_yo import todo_yo_tool as todo_yo
except Exception:
    todo_yo = None
try:
    from core.opencode_bridge import bridge_tool as opencode_bridge
except Exception:
    opencode_bridge = None
try:
    from core.hermes_bridge import herramienta_eris as hermes_consult
except Exception:
    hermes_consult = None
try:
    from actions.sub_agent_manager import sub_agent_manager as agente_sub
except Exception:
    agente_sub = None


# ── Hermes: Wireado final — herramientas existentes restantes ──
try:
    from actions.flow_recorder import flow_recorder as action_history
except Exception:
    action_history = None
try:
    from core.agi_tools import agi_reasoning as agi_reasoning
except Exception:
    agi_reasoning = None
try:
    from core.api_doc_generator import api_doc_generator_tool as api_doc_generator
except Exception:
    api_doc_generator = None
try:
    from core.api_tester import api_tester_tool as api_tester
except Exception:
    api_tester = None
try:
    from core.auto_healer import auto_healer as auto_healer
except Exception:
    auto_healer = None
try:
    from core.superinteligencia import backup_prioritizer as backup_prioritizer
except Exception:
    backup_prioritizer = None
try:
    from core.cicd_builder import cicd_builder_tool as cicd_builder
except Exception:
    cicd_builder = None
try:
    from core.connectivity import connectivity_tool as connectivity
except Exception:
    connectivity = None
try:
    from actions.console_log import console_log as console_log
except Exception:
    console_log = None
try:
    from core.coverage_reporter import coverage_reporter_tool as coverage_reporter
except Exception:
    coverage_reporter = None
try:
    from core.crash_recovery import crash_recovery_tool as crash_recovery
except Exception:
    crash_recovery = None
try:
    from core.cron_scheduler import cron_scheduler_tool as cron_scheduler
except Exception:
    cron_scheduler = None
try:
    from core.docker_manager import docker_manager_tool as docker_manager
except Exception:
    docker_manager = None
try:
    from core.superinteligencia import error_pattern_db as error_pattern_db
except Exception:
    error_pattern_db = None
try:
    from core.file_api import file_api as file_api
except Exception:
    file_api = None
try:
    from actions.smart_file_organizer import get_file_md5 as file_organizer
except Exception:
    file_organizer = None
try:
    from actions.image_generator import image_generator as image_generator
except Exception:
    image_generator = None
try:
    from core.learning_pipeline import learning_pipeline_tool as learning_pipeline
except Exception:
    learning_pipeline = None
try:
    from core.maintenance_scheduler import maintenance as maintenance
except Exception:
    maintenance = None
try:
    from actions.media_lab import media_lab as media_lab
except Exception:
    media_lab = None
try:
    from core.memory_consolidator import memory_consolidator as memory_consolidator
except Exception:
    memory_consolidator = None
try:
    from core.memory_consolidation import memory_consolidation_tool as memory_search
except Exception:
    memory_search = None
try:
    from core.superinteligencia import metrics_dashboard as metrics_dashboard
except Exception:
    metrics_dashboard = None
try:
    from actions.notifications import notify as notifications
except Exception:
    notifications = None
try:
    from core.proactive_comms import proactive_comms_tool as proactive_comms
except Exception:
    proactive_comms = None
try:
    from core.proactive_monitor import monitoring_tool as proactive_monitor
except Exception:
    proactive_monitor = None
try:
    from actions.project_builder import project_builder as project_builder
except Exception:
    project_builder = None
try:
    from actions.quick_actions import run as quick_actions
except Exception:
    quick_actions = None
try:
    from core.resource_manager import resource_manager_tool as resource_manager
except Exception:
    resource_manager = None
try:
    from core.superinteligencia import resource_optimizer as resource_optimizer
except Exception:
    resource_optimizer = None
try:
    from actions.screen_context import screen_context as screen_context
except Exception:
    screen_context = None
try:
    from actions.screen_recorder import start_recording as screen_recorder
except Exception:
    screen_recorder = None
try:
    from core.self_modify import self_improve as self_improve
except Exception:
    self_improve = None
try:
    from actions.system_volume import system_volume as system_volume
except Exception:
    system_volume = None
try:
    from core.training_pipeline import training_pipeline_tool as training_pipeline
except Exception:
    training_pipeline = None
try:
    from actions.visual_expressions import visual_expressions as visual_expressions
except Exception:
    visual_expressions = None
try:
    from core.voice_cloning import voice_cloning as voice_cloning
except Exception:
    voice_cloning = None
try:
    from actions.weather_report import weather_action as weather_report
except Exception:
    weather_report = None
try:
    from core.windows_service import create_startup_script as windows_service
except Exception:
    windows_service = None