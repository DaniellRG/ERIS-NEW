"""
ERIS Comprehensive Test Suite
Tests: imports, syntax, performance, and functional modules
"""
import sys, os, time, json, traceback
sys.path.insert(0, r'D:\Eris_Source')

RESULTS = []
def test(name, ok, detail=""):
    status = "PASS" if ok else "FAIL"
    RESULTS.append((name, status, detail))
    print(f"  [{status}] {name}" + (f" ({detail})" if detail else ""))

print("=" * 60)
print("  ERIS COMPREHENSIVE TEST SUITE")
print("=" * 60)

# ═══════════════════════════════════════════════════════════
# 1. SYNTAX + IMPORTS
# ═══════════════════════════════════════════════════════════
print("\n--- 1. SYNTAX & IMPORTS ---")
import py_compile

py_files = []
for root, dirs, files in os.walk(r'D:\Eris_Source'):
    for f in files:
        if f.endswith('.py') and '__pycache__' not in root:
            py_files.append(os.path.join(root, f))

syntax_ok = 0
syntax_fail = 0
for fp in py_files:
    try:
        py_compile.compile(fp, doraise=True)
        syntax_ok += 1
    except py_compile.PyCompileError as e:
        syntax_fail += 1
        print(f"  SYNTAX ERROR: {os.path.relpath(fp, r'D:\\Eris_Source')}: {e}")

test(f"Python syntax ({syntax_ok}/{syntax_ok+syntax_fail})", syntax_fail == 0, f"{syntax_fail} errors")

# ═══════════════════════════════════════════════════════════
# 2. PERFORMANCE: TOOL LOADING
# ═══════════════════════════════════════════════════════════
print("\n--- 2. PERFORMANCE: TOOL LOADING ---")

start = time.time()
from core.tool_declarations import TOOL_DECLARATIONS
t_tools = time.time() - start
test("Tool declarations load", True, f"{len(TOOL_DECLARATIONS)} tools in {t_tools:.3f}s")

schema_json = json.dumps(TOOL_DECLARATIONS, ensure_ascii=False)
chars = len(schema_json)
tokens_est = chars // 4
test("Schema size optimized", tokens_est < 30000, f"~{tokens_est:,} tokens (target < 30k)")

start = time.time()
from core.action_imports import *
t_imports = time.time() - start
test("Action imports", True, f"{t_imports:.3f}s")

start = time.time()
from core.tool_registry import get_tool
t_registry = time.time() - start
test("Tool registry load", True, f"{t_registry:.3f}s")

# ═══════════════════════════════════════════════════════════
# 3. FUNCTIONAL TESTS (each module directly)
# ═══════════════════════════════════════════════════════════
print("\n--- 3. FUNCTIONAL MODULE TESTS ---")

# 3a. Calculator
print("  [CALCULATOR]")
try:
    from actions.calculator import calculator_tool
    r = calculator_tool({"action": "calc", "expression": "2+2"})
    test("calculator calc", "4" in r, r[:80])
except Exception as e:
    test("calculator calc", False, str(e)[:80])

# 3b. File Manager
print("  [FILE MANAGER]")
try:
    from actions.file_manager import file_manager_tool
    r = file_manager_tool({"action": "list", "path": r"D:\Eris_Source"})
    test("file_manager list", "main.py" in r, r[:80])
except Exception as e:
    test("file_manager list", False, str(e)[:80])

# 3c. PC Control
print("  [PC CONTROL]")
try:
    from actions.pc_control import pc_control_tool
    r = pc_control_tool({"action": "status"})
    test("pc_control status", "status" in r.lower() or "cpu" in r.lower() or "ram" in r.lower() or "bateria" in r.lower() or "battery" in r.lower() or "disco" in r.lower(), r[:80])
except Exception as e:
    test("pc_control status", False, str(e)[:80])

# 3d. Clipboard
print("  [CLIPBOARD]")
try:
    from actions.clipboard_manager import clipboard_manager_tool
    r = clipboard_manager_tool({"action": "list"})
    test("clipboard list", isinstance(r, str), r[:80])
except Exception as e:
    test("clipboard list", False, str(e)[:80])

# 3e. Process Manager
print("  [PROCESS MANAGER]")
try:
    from actions.process_manager import process_manager_tool
    r = process_manager_tool({"action": "list", "name": "python"})
    test("process_manager list python", "python" in r.lower(), r[:80])
except Exception as e:
    test("process_manager list python", False, str(e)[:80])

# 3f. Web Search
print("  [WEB SEARCH]")
try:
    from actions.web_search import web_search_tool
    r = web_search_tool({"action": "search", "query": "python programming"})
    test("web_search query", "python" in r.lower(), r[:100])
except Exception as e:
    test("web_search query", False, str(e)[:80])

# 3g. Network Monitor
print("  [NETWORK MONITOR]")
try:
    from actions.network_monitor import network_monitor_tool
    r = network_monitor_tool({"action": "connections"})
    test("network_monitor connections", isinstance(r, str) and len(r) > 10, r[:80])
except Exception as e:
    test("network_monitor connections", False, str(e)[:80])

# 3h. Reminders
print("  [REMINDERS]")
try:
    from actions.reminders import reminders_tool
    r = reminders_tool({"action": "list"})
    test("reminders list", isinstance(r, str), r[:80])
except Exception as e:
    test("reminders list", False, str(e)[:80])

# 3i. Browser History
print("  [BROWSER HISTORY]")
try:
    from actions.browser_history import browser_history_tool
    r = browser_history_tool({"action": "status"})
    test("browser_history status", isinstance(r, str), r[:80])
except Exception as e:
    test("browser_history status", False, str(e)[:80])

# 3j. Fun Mode
print("  [FUN MODE]")
try:
    from actions.fun_mode import fun_mode_tool
    r = fun_mode_tool({"action": "joke"})
    test("fun_mode joke", isinstance(r, str) and len(r) > 5, r[:80])
except Exception as e:
    test("fun_mode joke", False, str(e)[:80])

# 3k. Data Analyst
print("  [DATA ANALYST]")
try:
    from actions.data_analyst import data_analyst_tool
    r = data_analyst_tool({"action": "status"})
    test("data_analyst status", isinstance(r, str), r[:80])
except Exception as e:
    test("data_analyst status", False, str(e)[:80])

# 3l. Text Summarizer
print("  [TEXT SUMMARIZER]")
try:
    from actions.text_summarizer import text_summarizer_tool
    r = text_summarizer_tool({"action": "summarize_text", "text": "This is a test text about python programming. Python is a great language for beginners."})
    test("text_summarizer summarize_text", isinstance(r, str) and len(r) > 5, r[:80])
except Exception as e:
    test("text_summarizer summarize_text", False, str(e)[:80])

# 3m. Template Engine
print("  [TEMPLATE ENGINE]")
try:
    from actions.template_engine import template_engine_tool
    r = template_engine_tool({"action": "create", "template": "Hello {{name}}!", "variables": {"name": "Danieris"}})
    test("template_engine create", "Danieris" in r, r[:80])
except Exception as e:
    test("template_engine create", False, str(e)[:80])

# 3n. Knowledge Base
print("  [KNOWLEDGE BASE]")
try:
    from core.semantic_memory import get_memory_system
    mem = get_memory_system()
    test("semantic_memory init", mem is not None)
except Exception as e:
    test("semantic_memory init", False, str(e)[:80])

# 3o. Memory RAG
print("  [MEMORY RAG]")
try:
    from actions.memory_rag import memory_rag_tool
    r = memory_rag_tool({"action": "status"})
    test("memory_rag status", isinstance(r, str), r[:80])
except Exception as e:
    test("memory_rag status", False, str(e)[:80])

# 3p. Task Scheduler
print("  [TASK SCHEDULER]")
try:
    from actions.task_scheduler import task_scheduler_tool
    r = task_scheduler_tool({"action": "list"})
    test("task_scheduler list", isinstance(r, str), r[:80])
except Exception as e:
    test("task_scheduler list", False, str(e)[:80])

# 3q. Context Engine
print("  [CONTEXT ENGINE]")
try:
    from actions.context_engine import context_engine_tool
    r = context_engine_tool({"action": "status"})
    test("context_engine status", isinstance(r, str), r[:80])
except Exception as e:
    test("context_engine status", False, str(e)[:80])

# 3r. Active Firewall
print("  [ACTIVE FIREWALL]")
try:
    from actions.active_firewall import active_firewall_tool
    r = active_firewall_tool({"action": "status"})
    test("active_firewall status", isinstance(r, str), r[:80])
except Exception as e:
    test("active_firewall status", False, str(e)[:80])

# 3s. Ransomware Shield
print("  [RANSOMWARE SHIELD]")
try:
    from actions.ransomware_shield import ransomware_shield_tool
    r = ransomware_shield_tool({"action": "status"})
    test("ransomware_shield status", isinstance(r, str), r[:80])
except Exception as e:
    test("ransomware_shield status", False, str(e)[:80])

# 3t. Backup System
print("  [BACKUP SYSTEM]")
try:
    from actions.backup_system import backup_system_tool
    r = backup_system_tool({"action": "status"})
    test("backup_system status", isinstance(r, str), r[:80])
except Exception as e:
    test("backup_system status", False, str(e)[:80])

# 3u. Notification Center
print("  [NOTIFICATION CENTER]")
try:
    from actions.notification_center import notification_center_tool
    r = notification_center_tool({"action": "list"})
    test("notification_center list", isinstance(r, str), r[:80])
except Exception as e:
    test("notification_center list", False, str(e)[:80])

# 3v. Calendar Manager
print("  [CALENDAR MANAGER]")
try:
    from actions.calendar_manager import calendar_manager_tool
    r = calendar_manager_tool({"action": "list"})
    test("calendar_manager list", isinstance(r, str), r[:80])
except Exception as e:
    test("calendar_manager list", False, str(e)[:80])

# 3w. Image Analyzer (needs Gemini)
print("  [IMAGE ANALYZER]")
try:
    from actions.image_analyzer import image_analyzer_tool
    r = image_analyzer_tool({"action": "status"})
    test("image_analyzer status", isinstance(r, str), r[:80])
except Exception as e:
    test("image_analyzer status", False, str(e)[:80])

# 3x. PDF Manager
print("  [PDF MANAGER]")
try:
    from actions.pdf_manager import pdf_manager_tool
    r = pdf_manager_tool({"action": "status"})
    test("pdf_manager status", isinstance(r, str), r[:80])
except Exception as e:
    test("pdf_manager status", False, str(e)[:80])

# 3y. Disk Wiper
print("  [DISK WIPER]")
try:
    from actions.disk_wiper import disk_wiper_tool
    r = disk_wiper_tool({"action": "status"})
    test("disk_wiper status", isinstance(r, str), r[:80])
except Exception as e:
    test("disk_wiper status", False, str(e)[:80])

# 3z. Driver Manager
print("  [DRIVER MANAGER]")
try:
    from actions.driver_manager import driver_manager_tool
    r = driver_manager_tool({"action": "status"})
    test("driver_manager status", isinstance(r, str), r[:80])
except Exception as e:
    test("driver_manager status", False, str(e)[:80])

# 3aa. Smart Browser
print("  [SMART BROWSER]")
try:
    from actions.smart_browser import smart_browser_tool
    r = smart_browser_tool({"action": "status"})
    test("smart_browser status", isinstance(r, str), r[:80])
except Exception as e:
    test("smart_browser status", False, str(e)[:80])

# 3bb. File Encryptor
print("  [FILE ENCRYPTOR]")
try:
    from actions.file_encryptor import file_encryptor_tool
    r = file_encryptor_tool({"action": "status"})
    test("file_encryptor status", isinstance(r, str), r[:80])
except Exception as e:
    test("file_encryptor status", False, str(e)[:80])

# ═══════════════════════════════════════════════════════════
# 4. DISPATCHER INTEGRATION
# ═══════════════════════════════════════════════════════════
print("\n--- 4. DISPATCHER INTEGRATION ---")
try:
    from core.tool_dispatcher import ToolDispatcher
    test("ToolDispatcher class", True)
except Exception as e:
    test("ToolDispatcher class", False, str(e)[:80])

try:
    from core.tool_registry import get_tool
    # Test registering and retrieving tools
    calc_fn = get_tool("calculator")
    test("get_tool(calculator)", calc_fn is not None)
    fm_fn = get_tool("file_manager")
    test("get_tool(file_manager)", fm_fn is not None)
    pc_fn = get_tool("pc_control")
    test("get_tool(pc_control)", pc_fn is not None)
except Exception as e:
    test("tool_registry", False, str(e)[:80])

# ═══════════════════════════════════════════════════════════
# 5. LIVE FUNCTIONAL TESTS (actually run things)
# ═══════════════════════════════════════════════════════════
print("\n--- 5. LIVE FUNCTIONAL TESTS ---")

# 5a. Calculator real math
print("  [CALC MATH]")
try:
    from actions.calculator import calculator_tool
    tests_math = [
        ("2+2", "4"),
        ("10*5", "50"),
        ("100/4", "25"),
    ]
    for expr, expected in tests_math:
        r = calculator_tool({"action": "calc", "expression": expr})
        test(f"calc({expr})", expected in r, r[:40])
except Exception as e:
    test("calc_math", False, str(e)[:80])

# 5b. Open/close apps
print("  [APP CONTROL]")
try:
    import subprocess
    # Open notepad
    p = subprocess.Popen(["notepad.exe"], creationflags=0x00000008)
    time.sleep(2)
    # Check it's open
    import psutil
    notepad_running = any("notepad" in proc.name().lower() for proc in psutil.process_iter(['name']))
    test("open notepad", notepad_running)
    
    # Close notepad
    subprocess.run(["taskkill", "/F", "/IM", "notepad.exe"], capture_output=True)
    time.sleep(1)
    notepad_still = any("notepad" in proc.name().lower() for proc in psutil.process_iter(['name']))
    test("close notepad", notepad_still == False)
except Exception as e:
    test("app_control", False, str(e)[:80])

# 5c. Desktop windows
print("  [DESKTOP WINDOWS]")
try:
    from actions.desktop_control import desktop_control_tool
    r = desktop_control_tool({"action": "list"})
    test("desktop list windows", isinstance(r, str) and len(r) > 10, r[:80])
except Exception as e:
    test("desktop_control", False, str(e)[:80])

# 5d. Typing
print("  [TYPING TEST]")
try:
    from actions.keyboard import keyboard_tool
    r = keyboard_tool({"action": "type", "text": "eris test message"})
    test("keyboard type", isinstance(r, str) and ("ok" in r.lower() or "typed" in r.lower() or "escrib" in r.lower()), r[:80])
except Exception as e:
    test("keyboard type", False, str(e)[:80])

# 5e. Screen capture
print("  [SCREEN CAPTURE]")
try:
    from actions.screen_capture import screen_capture_tool
    r = screen_capture_tool({})
    test("screen_capture", isinstance(r, str) and len(r) > 5, r[:80])
except Exception as e:
    test("screen_capture", False, str(e)[:80])

# 5f. Browser
print("  [BROWSER]")
try:
    from actions.browser import browser_tool
    r = browser_tool({"action": "go_to", "url": "https://www.google.com"})
    time.sleep(3)
    test("browser go_to google", isinstance(r, str), r[:80])
except Exception as e:
    test("browser go_to", False, str(e)[:80])

# 5g. YouTube
print("  [YOUTUBE]")
try:
    from actions.youtube import youtube_tool
    r = youtube_tool({"action": "search", "query": "python tutorial"})
    test("youtube search", isinstance(r, str), r[:80])
except Exception as e:
    test("youtube search", False, str(e)[:80])

# 5h. Voice status
print("  [VOICE STATUS]")
try:
    from actions.voice_control import voice_control_tool
    r = voice_control_tool({"action": "status"})
    test("voice_control status", isinstance(r, str), r[:80])
except Exception as e:
    test("voice_control status", False, str(e)[:80])

# 5i. Translator
print("  [TRANSLATOR]")
try:
    from actions.translator import translator_tool
    r = translator_tool({"action": "translate", "text": "hello world", "target_lang": "es"})
    test("translator", isinstance(r, str), r[:80])
except Exception as e:
    test("translator", False, str(e)[:80])

# 5j. OCR Reader
print("  [OCR READER]")
try:
    from actions.ocr_reader import ocr_reader_tool
    r = ocr_reader_tool({"action": "status"})
    test("ocr_reader status", isinstance(r, str), r[:80])
except Exception as e:
    test("ocr_reader status", False, str(e)[:80])

# 5k. USB Monitor
print("  [USB MONITOR]")
try:
    from actions.usb_monitor import usb_monitor_tool
    r = usb_monitor_tool({"action": "list"})
    test("usb_monitor list", isinstance(r, str), r[:80])
except Exception as e:
    test("usb_monitor list", False, str(e)[:80])

# 5l. Code Generator
print("  [CODE GENERATOR]")
try:
    from actions.code_generator import code_generator_tool
    r = code_generator_tool({"action": "generate", "description": "hello world function"})
    test("code_generator generate", isinstance(r, str) and len(r) > 10, r[:80])
except Exception as e:
    test("code_generator generate", False, str(e)[:80])

# 5m. Obsidian Vault
print("  [OBSIDIAN VAULT]")
try:
    from actions.obsidian_vault import obsidian_vault_tool
    r = obsidian_vault_tool({"action": "list"})
    test("obsidian_vault list", isinstance(r, str), r[:80])
except Exception as e:
    test("obsidian_vault list", False, str(e)[:80])

# 5n. Spotify status
print("  [SPOTIFY]")
try:
    from actions.spotify_control import spotify_control_tool
    r = spotify_control_tool({"action": "current"})
    test("spotify current", isinstance(r, str), r[:80])
except Exception as e:
    test("spotify current", False, str(e)[:80])

# 5o. Security Shield
print("  [SECURITY SHIELD]")
try:
    from actions.security_shield import security_shield_tool
    r = security_shield_tool({"action": "status"})
    test("security_shield status", isinstance(r, str), r[:80])
except Exception as e:
    test("security_shield status", False, str(e)[:80])

# ═══════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════
print("\n" + "=" * 60)
passed = sum(1 for _, s, _ in RESULTS if s == "PASS")
failed = sum(1 for _, s, _ in RESULTS if s == "FAIL")
total = len(RESULTS)
print(f"  RESULTS: {passed}/{total} PASS, {failed} FAIL")
if failed > 0:
    print(f"\n  FAILURES:")
    for name, status, detail in RESULTS:
        if status == "FAIL":
            print(f"    - {name}: {detail}")
print("=" * 60)
