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
    from actions.windows_settings  import windows_settings
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
try:
    from actions.self_evolution    import self_evolution
except Exception:
    self_evolution = None
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
    from actions.voice_cloning import voice_cloning
except Exception:
    voice_cloning = None
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
# ── Batch 5: Connectivity + Self-Healing ──
try:
    from core.connectivity import connectivity_tool
except Exception:
    connectivity_tool = None
try:
    from core.self_healing import self_healing_tool
except Exception:
    self_healing_tool = None
# ── Batch 6: Page/Video Summarizer ──
try:
    from actions.page_summarizer import page_summarizer
except Exception:
    page_summarizer = None
