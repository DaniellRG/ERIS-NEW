"""
ERIS Comprehensive Test Suite v2 - Correct function names
"""
import sys, os, time, json
sys.path.insert(0, r'D:\Eris_Source')

RESULTS = []
def test(name, ok, detail=""):
    status = "PASS" if ok else "FAIL"
    RESULTS.append((name, status, detail))
    print(f"  [{status}] {name}" + (f" ({detail})" if detail else ""))

print("=" * 60)
print("  ERIS COMPREHENSIVE TEST SUITE v2")
print("=" * 60)

# ═══════════════════════════════════════════════════════════
# 1. SYNTAX
# ═══════════════════════════════════════════════════════════
print("\n--- 1. SYNTAX ---")
import py_compile
py_files = []
for root, dirs, files in os.walk(r'D:\Eris_Source'):
    if '__pycache__' in root: continue
    for f in files:
        if f.endswith('.py'):
            py_files.append(os.path.join(root, f))

syntax_ok = syntax_fail = 0
for fp in py_files:
    try:
        py_compile.compile(fp, doraise=True)
        syntax_ok += 1
    except py_compile.PyCompileError as e:
        syntax_fail += 1
        print(f"  ERR: {os.path.relpath(fp, r'D:\\Eris_Source')}")
test(f"Python syntax ({syntax_ok}/{syntax_ok+syntax_fail})", syntax_fail == 0)

# ═══════════════════════════════════════════════════════════
# 2. PERFORMANCE
# ═══════════════════════════════════════════════════════════
print("\n--- 2. PERFORMANCE ---")
start = time.time()
from core.tool_declarations import TOOL_DECLARATIONS
t1 = time.time() - start
schema_json = json.dumps(TOOL_DECLARATIONS, ensure_ascii=False)
tokens_est = len(schema_json) // 4
test("Tool declarations", True, f"{len(TOOL_DECLARATIONS)} tools, {t1:.3f}s")
test("Schema tokens optimized", tokens_est < 30000, f"~{tokens_est:,} tokens")

start = time.time()
from core.action_imports import *
t2 = time.time() - start
test("Action imports", True, f"{t2:.2f}s")

from core.tool_registry import get_tool
tool_names = ["calculator","file_manager","pc_control","web_search","clipboard_manager",
              "process_manager","network_monitor","reminders","browser_history","fun_mode",
              "data_analyst","text_summarizer","template_engine","memory_rag","task_scheduler",
              "context_engine","active_firewall","ransomware_shield","backup_system",
              "notification_center","calendar_manager","image_analyzer","pdf_manager",
              "disk_wiper","driver_manager","smart_browser","file_encryptor","usb_monitor",
              "code_generator","ocr_reader","translator","security_shield","spotify_control",
              "email_manager","whatsapp_web","telegram_bot","voice_clone","real_time_tts",
              "keylogger_detector","darkweb_monitor","music_player","pdf_editor",
              "screen_vision","desktop_control","browser_control","open_app","computer_control",
              "obsidian_note","self_awareness","self_protection","goals","user_profile",
              "knowledge_base","federated_learning","docker_deploy","ci_cd","git_control",
              "self_healing","code_review","document_manager","game_companion","codebase",
              "auto_agent","web_scraper","webfetch","social_media","windows_settings",
              "eris_ui_control","sleep_mode","shutdown_eris","save_memory","agent_task",
              "db_memory","db_knowledge","db_tasks","plugin_manage","openrouter_agent",
              "screen_recorder","meeting_transcriber","sms","dashboard","emotional_state",
              "ask_opencode","system_reader","episodic_log","conversation_search",
              "curiosity_joke","curiosity_fact","curiosity_fun","curiosity_trending",
              "quick_actions","context_menu","data_viz","auto_backup","multi_user",
              "i18n","usage_analytics","app_discovery","app_installer","predict_analyze",
              "rules_engine","morning_brief","contextual_control","super_search",
              "knowledge_ingestor","knowledge_graph","habit_predictor","english_teacher",
              "osint_agent","security_scanner","flow_recorder","tool_creator",
              "plugin_loader","plugin_marketplace","skill_marketplace","full_training",
              "personality","emotional_growth","episodic_log","conversation_search",
              "self_improvement","connectivity","ollama_status","tts_set_voice","eris_update"]
found = sum(1 for n in tool_names if get_tool(n) is not None)
test(f"Tool registry resolution", found > 100, f"{found}/{len(tool_names)} resolved")

# ═══════════════════════════════════════════════════════════
# 3. FUNCTIONAL TESTS (direct function calls)
# ═══════════════════════════════════════════════════════════
print("\n--- 3. FUNCTIONAL MODULE TESTS ---")

def run_test(module_name, func_name, params, check_fn=None, label=None):
    """Generic test runner."""
    try:
        mod = __import__(f"actions.{module_name}", fromlist=[func_name])
        fn = getattr(mod, func_name)
        r = fn(parameters=params, player=None)
        if check_fn:
            ok = check_fn(r)
        else:
            ok = isinstance(r, str) and len(r) > 3
        test(label or module_name, ok, str(r)[:100])
        return r
    except Exception as e:
        test(label or module_name, False, str(e)[:100])
        return None

# 3a. Calculator
run_test("calculator", "calculator", {"action": "calc", "expression": "2+2"},
         lambda r: "4" in r, "calculator: calc 2+2")

# 3b. File Manager
run_test("file_manager", "file_manager", {"action": "list", "path": r"D:\Eris_Source"},
         lambda r: "main.py" in r or "core" in r, "file_manager: list")

# 3c. PC Control
run_test("pc_control", "pc_control", {"action": "status"},
         lambda r: len(r) > 10, "pc_control: status")

# 3d. Clipboard
run_test("clipboard_manager", "clipboard_manager", {"action": "list"},
         label="clipboard: list")

# 3e. Process Manager
run_test("process_manager", "process_manager", {"action": "list", "name": "python"},
         lambda r: "python" in r.lower(), "process_manager: list python")

# 3f. Web Search
run_test("web_search", "web_search", {"action": "search", "query": "python programming"},
         lambda r: len(r) > 10, "web_search: query")

# 3g. Network Monitor
run_test("network_monitor", "network_monitor", {"action": "connections"},
         lambda r: len(r) > 10, "network_monitor: connections")

# 3h. Reminders
run_test("reminders", "reminders", {"action": "list"}, label="reminders: list")

# 3i. Browser History
run_test("browser_history", "browser_history", {"action": "status"},
         label="browser_history: status")

# 3j. Fun Mode
run_test("fun_mode", "fun_mode", {"action": "joke"},
         lambda r: len(r) > 5, "fun_mode: joke")

# 3k. Data Analyst
run_test("data_analyst", "data_analyst", {"action": "status"}, label="data_analyst: status")

# 3l. Text Summarizer
run_test("text_summarizer", "text_summarizer",
         {"action": "summarize_text", "text": "This is test text about python programming. Python is great."},
         lambda r: len(r) > 5, "text_summarizer: summarize")

# 3m. Template Engine
run_test("template_engine", "template_engine",
         {"action": "create", "template": "Hello {{name}}!", "variables": {"name": "ERIS"}},
         lambda r: "ERIS" in r, "template_engine: create")

# 3n. Memory RAG
run_test("memory_rag", "memory_rag", {"action": "status"}, label="memory_rag: status")

# 3o. Task Scheduler
run_test("task_scheduler", "task_scheduler", {"action": "list"}, label="task_scheduler: list")

# 3p. Context Engine
run_test("context_engine", "context_engine", {"action": "status"}, label="context_engine: status")

# 3q. Active Firewall
run_test("active_firewall", "active_firewall", {"action": "status"}, label="active_firewall: status")

# 3r. Ransomware Shield
run_test("ransomware_shield", "ransomware_shield", {"action": "status"}, label="ransomware_shield: status")

# 3s. Backup System
run_test("backup_system", "backup_system", {"action": "status"}, label="backup_system: status")

# 3t. Notification Center
run_test("notification_center", "notification_center", {"action": "list"}, label="notification_center: list")

# 3u. Calendar Manager
run_test("calendar_manager", "calendar_manager", {"action": "list"}, label="calendar_manager: list")

# 3v. Image Analyzer
run_test("image_analyzer", "image_analyzer", {"action": "status"}, label="image_analyzer: status")

# 3w. PDF Manager
run_test("pdf_manager", "pdf_manager", {"action": "status"}, label="pdf_manager: status")

# 3x. Disk Wiper
run_test("disk_wiper", "disk_wiper", {"action": "status"}, label="disk_wiper: status")

# 3y. Driver Manager
run_test("driver_manager", "driver_manager", {"action": "status"}, label="driver_manager: status")

# 3z. Smart Browser
run_test("smart_browser", "smart_browser", {"action": "status"}, label="smart_browser: status")

# 3aa. File Encryptor
run_test("file_encryptor", "file_encryptor", {"action": "status"}, label="file_encryptor: status")

# 3ab. USB Monitor
run_test("usb_monitor", "usb_monitor", {"action": "list"}, label="usb_monitor: list")

# 3ac. Code Generator
run_test("code_generator", "code_generator",
         {"action": "generate", "description": "hello world function"},
         lambda r: len(r) > 10, "code_generator: generate")

# 3ad. OCR Reader
run_test("ocr_reader", "ocr_reader", {"action": "status"}, label="ocr_reader: status")

# 3ae. Translator
run_test("translator", "translator",
         {"action": "translate", "text": "hello world", "target_lang": "es"},
         label="translator: translate")

# 3af. Security Shield
run_test("security_shield", "security_shield", {"action": "status"}, label="security_shield: status")

# 3ag. Spotify
run_test("spotify_control", "spotify_control", {"action": "current"}, label="spotify: current")

# 3ah. Email Manager
run_test("email_manager", "email_manager", {"action": "status"}, label="email_manager: status")

# 3ai. WhatsApp
run_test("whatsapp_web", "whatsapp_web", {"action": "status"}, label="whatsapp: status")

# 3aj. Telegram Bot
run_test("telegram_bot", "telegram_bot", {"action": "status"}, label="telegram: status")

# 3ak. Voice Clone
run_test("voice_clone", "voice_clone", {"action": "status"}, label="voice_clone: status")

# 3al. Real Time TTS
run_test("real_time_tts", "real_time_tts", {"action": "status"}, label="real_time_tts: status")

# 3am. Keylogger Detector
run_test("keylogger_detector", "keylogger_detector", {"action": "status"}, label="keylogger_detector: status")

# 3an. Darkweb Monitor
run_test("darkweb_monitor", "darkweb_monitor", {"action": "status"}, label="darkweb_monitor: status")

# 3ao. Music Player
run_test("music_player", "music_player", {"action": "status"}, label="music_player: status")

# 3ap. Screen Vision (might need Gemini)
run_test("screen_vision", "screen_vision", {"action": "status"}, label="screen_vision: status")

# 3aq. Desktop Control
try:
    from actions.desktop import desktop_control
    r = desktop_control(parameters={"action": "list"}, player=None)
    test("desktop_control: list", isinstance(r, str) and len(r) > 5, str(r)[:100])
except Exception as e:
    test("desktop_control: list", False, str(e)[:100])

# 3ar. Browser Control
run_test("browser_control", "browser_control", {"action": "status"}, label="browser_control: status")

# 3as. Open App
run_test("open_app", "open_app", {"action": "list"}, label="open_app: list")

# 3at. Computer Control
run_test("computer_control", "computer_control", {"action": "status"}, label="computer_control: status")

# 3au. Obsidian
run_test("obsidian_note", "obsidian_note", {"action": "list"}, label="obsidian: list")

# 3av. Self Awareness
run_test("self_awareness", "self_awareness", {"action": "capabilities"}, label="self_awareness: capabilities")

# 3aw. Self Protection
run_test("self_protection", "self_protection", {"action": "status"}, label="self_protection: status")

# 3ax. Goals
run_test("goals", "goals", {"action": "list"}, label="goals: list")

# 3ay. User Profile
run_test("user_profile", "user_profile", {"action": "view"}, label="user_profile: view")

# 3az. Knowledge Base
run_test("knowledge_base", "knowledge_base", {"action": "status"}, label="knowledge_base: status")

# 3ba. Federated Learning
run_test("federated_learning", "federated_learning", {"action": "status"}, label="federated_learning: status")

# 3bb. Auto Agent
run_test("auto_agent", "auto_agent", {"action": "status"}, label="auto_agent: status")

# 3bc. Web Scraper
run_test("web_scraper", "web_scraper", {"action": "status"}, label="web_scraper: status")

# 3bd. Social Media
run_test("social_media", "social_media", {"action": "status"}, label="social_media: status")

# 3be. Windows Settings
run_test("windows_settings", "windows_settings", {"action": "status"}, label="windows_settings: status")

# 3bf. Game Companion
run_test("game_companion", "game_companion", {"action": "status"}, label="game_companion: status")

# 3bg. CI/CD
run_test("ci_cd", "ci_cd", {"action": "status"}, label="ci_cd: status")

# 3bh. Git Control
run_test("git_control", "git_control", {"action": "status"}, label="git_control: status")

# 3bi. Docker Deploy
run_test("docker_deploy", "docker_deploy", {"action": "status"}, label="docker_deploy: status")

# 3bj. Document Manager
run_test("document_manager", "document_manager", {"action": "status"}, label="document_manager: status")

# 3bk. Code Review
run_test("code_review", "code_review", {"action": "status"}, label="code_review: status")

# 3bl. Codebase
run_test("codebase", "codebase", {"action": "status"}, label="codebase: status")

# 3bm. App Discovery
run_test("app_discovery", "app_discovery", {"action": "status"}, label="app_discovery: status")

# 3bn. Predict Analyze
run_test("predict_analyze", "predict_analyze", {"action": "status"}, label="predict_analyze: status")

# 3bo. Morning Brief
run_test("morning_brief", "morning_brief", {"action": "status"}, label="morning_brief: status")

# 3bp. Multi User
run_test("multi_user", "multi_user", {"action": "status"}, label="multi_user: status")

# 3bq. Usage Analytics
run_test("usage_analytics", "usage_analytics", {"action": "status"}, label="usage_analytics: status")

# 3br. I18N
run_test("i18n", "i18n", {"action": "status"}, label="i18n: status")

# 3bs. Auto Backup
run_test("auto_backup", "auto_backup", {"action": "status"}, label="auto_backup: status")

# 3bt. Data Viz
run_test("data_viz", "data_viz", {"action": "status"}, label="data_viz: status")

# ═══════════════════════════════════════════════════════════
# 4. LIVE TESTS (actually do things)
# ═══════════════════════════════════════════════════════════
print("\n--- 4. LIVE INTEGRATION TESTS ---")

# 4a. Open & Close Notepad
print("  [APP OPEN/CLOSE]")
try:
    import subprocess, psutil
    p = subprocess.Popen(["notepad.exe"], creationflags=0x00000008)
    time.sleep(2)
    running = any("notepad" in p.name().lower() for p in psutil.process_iter(['name']))
    test("open notepad", running)
    subprocess.run(["taskkill", "/F", "/IM", "notepad.exe"], capture_output=True)
    time.sleep(1)
    still = any("notepad" in p.name().lower() for p in psutil.process_iter(['name']))
    test("close notepad", not still)
except Exception as e:
    test("app open/close", False, str(e)[:100])

# 4b. Type text
print("  [KEYBOARD]")
try:
    from actions.keyboard import keyboard_tool
    r = keyboard_tool(parameters={"action": "type", "text": "eris test"}, player=None)
    test("keyboard type", True, str(r)[:80])
except Exception as e:
    test("keyboard type", False, str(e)[:100])

# 4c. Screenshot
print("  [SCREENSHOT]")
try:
    from actions.screen_capture import screen_capture_tool
    r = screen_capture_tool(parameters={}, player=None)
    test("screenshot", isinstance(r, str) and len(r) > 5, str(r)[:80])
except Exception as e:
    test("screenshot", False, str(e)[:100])

# 4d. YouTube
print("  [YOUTUBE]")
try:
    from actions.youtube_video import youtube_video
    r = youtube_video(parameters={"action": "search", "query": "python tutorial"}, player=None)
    test("youtube search", isinstance(r, str), str(r)[:80])
except Exception as e:
    test("youtube search", False, str(e)[:100])

# 4e. Voice Control
print("  [VOICE]")
try:
    from actions.voice_enhanced import voice_enhanced
    r = voice_enhanced(parameters={"action": "status"}, player=None)
    test("voice enhanced status", isinstance(r, str), str(r)[:80])
except Exception as e:
    test("voice enhanced status", False, str(e)[:100])

# 4f. Weather
print("  [WEATHER]")
try:
    from actions.weather_report import weather_action
    r = weather_action(parameters={"action": "status"}, player=None)
    test("weather status", isinstance(r, str), str(r)[:80])
except Exception as e:
    test("weather status", False, str(e)[:100])

# 4g. Webfetch
print("  [WEBFETCH]")
try:
    from actions.webfetch import webfetch
    r = webfetch(parameters={"action": "fetch", "url": "https://httpbin.org/get"}, player=None)
    test("webfetch", isinstance(r, str) and len(r) > 10, str(r)[:80])
except Exception as e:
    test("webfetch", False, str(e)[:100])

# 4h. Super Search
print("  [SUPER SEARCH]")
try:
    from actions.super_search import super_search
    r = super_search(parameters={"action": "search", "query": "python"}, player=None)
    test("super_search", isinstance(r, str) and len(r) > 10, str(r)[:80])
except Exception as e:
    test("super_search", False, str(e)[:100])

# 4i. Search Info
print("  [SEARCH INFO]")
try:
    from actions.search_info import search_info
    r = search_info(parameters={"action": "search", "query": "python programming"}, player=None)
    test("search_info", isinstance(r, str) and len(r) > 10, str(r)[:80])
except Exception as e:
    test("search_info", False, str(e)[:100])

# ═══════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════
print("\n" + "=" * 60)
passed = sum(1 for _, s, _ in RESULTS if s == "PASS")
failed = sum(1 for _, s, _ in RESULTS if s == "FAIL")
total = len(RESULTS)
print(f"  RESULTS: {passed}/{total} PASS, {failed} FAIL")
if failed > 0:
    print(f"\n  FAILURES ({failed}):")
    for name, status, detail in RESULTS:
        if status == "FAIL":
            print(f"    - {name}: {detail}")
print("=" * 60)
