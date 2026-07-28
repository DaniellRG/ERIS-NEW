"""ERIS Full System Test — 26/07/2026"""
import json, os, sys, traceback
from pathlib import Path

PASS = 0
FAIL = 0
WARN = 0
RESULTS = []

def ok(section, msg):
    global PASS
    PASS += 1
    RESULTS.append(("PASS", section, msg))

def fail(section, msg):
    global FAIL
    FAIL += 1
    RESULTS.append(("FAIL", section, msg))

def warn(section, msg):
    global WARN
    WARN += 1
    RESULTS.append(("WARN", section, msg))

print("=" * 70)
print("  TEST COMPLETO DE ERIS — 26/07/2026")
print("=" * 70)

# ── 1. TOOL REGISTRY ──
print("\n[1] TOOL REGISTRY")
try:
    from core.tool_registry import get_tool, get_all_tool_names, _TOOLS
    tools = get_all_tool_names()
    ok("registry", "Total tools: {}".format(len(tools)))
except Exception as e:
    fail("registry", str(e))

# ── 2. TOOL DECLARATIONS ──
print("[2] TOOL DECLARATIONS")
try:
    from core.tool_declarations import TOOL_DECLARATIONS
    ok("declarations", "Total declarations: {}".format(len(TOOL_DECLARATIONS)))
except Exception as e:
    fail("declarations", str(e))

# ── 3. TOOL DISPATCHER ──
print("[3] TOOL DISPATCHER")
try:
    from core.tool_dispatcher import ToolDispatcher
    ok("dispatcher", "ToolDispatcher imported OK")
except Exception as e:
    fail("dispatcher", str(e))

# ── 4. 16 NEW TOOLS LOAD ──
print("[4] 16 NUEVAS TOOLS")
new_tools = [
    "memory_consolidation", "email_manager", "calendar_manager", "flow_recorder",
    "screenshot_history", "clipboard_manager", "multi_user", "voice_cloning_new",
    "browser_extension", "smart_notifications", "usage_analytics", "skill_marketplace",
    "api_server", "federated_learning", "file_organizer", "data_encryption",
]
for t in new_tools:
    try:
        func = get_tool(t)
        if func:
            ok("new_tool", t)
        else:
            fail("new_tool", t + " -> get_tool returned None")
    except Exception as e:
        fail("new_tool", t + " -> " + str(e))

# ── 5. ALL TOOLS LOAD ──
print("[5] ALL TOOLS IN REGISTRY")
loaded = 0
failed_tools = []
for t in tools:
    try:
        func = get_tool(t)
        if func:
            loaded += 1
        else:
            failed_tools.append(t)
    except Exception:
        failed_tools.append(t)
ok("all_tools", "{}/{} loaded".format(loaded, len(tools)))
if failed_tools:
    warn("all_tools", "Tools with no implementation: {}".format(", ".join(failed_tools[:10])))

# ── 6. CORE MODULES ──
print("[6] CORE MODULES")
core_tests = [
    ("core.tool_registry", "get_tool"),
    ("core.tool_declarations", "TOOL_DECLARATIONS"),
    ("core.tool_dispatcher", "ToolDispatcher"),
    ("core.logging_setup", "BASE_DIR"),
    ("core.self_map", "get_full_map"),
    ("core.emotional_state", "emotional_state_tool"),
    ("core.llm_bridge", "get_embedding"),
    ("core.rag_pipeline", "RAGPipeline"),
    ("core.autonomous_learner", "autonomous_learner"),
    ("core.idle_learning_loop", "run_idle_learning"),
    ("core.agent_router", "AgentRouter"),
]
for mod_name, attr in core_tests:
    try:
        mod = __import__(mod_name, fromlist=[attr])
        obj = getattr(mod, attr, None)
        if obj is not None:
            ok("core", mod_name + "." + attr)
        else:
            warn("core", mod_name + "." + attr + " is None")
    except Exception as e:
        fail("core", mod_name + " -> " + str(e))

# ── 7. ACTION MODULES ──
print("[7] ACTION MODULES")
action_tests = [
    "actions.memory_consolidation", "actions.email_manager", "actions.calendar_manager",
    "actions.flow_recorder", "actions.screenshot_history", "actions.clipboard_manager",
    "actions.multi_user", "actions.image_generation", "actions.voice_cloning",
    "actions.browser_extension", "actions.smart_notifications", "actions.usage_analytics",
    "actions.skill_marketplace", "actions.api_server", "actions.federated_learning",
    "actions.file_organizer", "actions.data_encryption",
    "actions.computer_control", "actions.file_controller", "actions.browser_control",
    "actions.system_monitor", "actions.screen_vision", "actions.document_rag",
    "actions.self_awareness", "actions.self_edit", "actions.knowledge_ingestor",
    "actions.data_connectors", "actions.open_app", "actions.weather_report",
    "actions.web_search", "actions.file_processor",
]
for mod_name in action_tests:
    try:
        __import__(mod_name)
        ok("action", mod_name)
    except Exception as e:
        fail("action", mod_name + " -> " + str(e))

# ── 8. FUNCTIONAL TESTS (call tools with status/list) ──
print("[8] FUNCTIONAL TESTS (invoke tools)")
functional_tests = [
    ("memory_consolidation", {"action": "status"}),
    ("email_manager", {"action": "status"}),
    ("calendar_manager", {"action": "status"}),
    ("flow_recorder", {"action": "status"}),
    ("screenshot_history", {"action": "stats"}),
    ("clipboard_manager", {"action": "stats"}),
    ("multi_user", {"action": "stats"}),
    ("image_generation", {"action": "status"}),
    ("voice_cloning_new", {"action": "status"}),
    ("browser_extension", {"action": "status"}),
    ("smart_notifications", {"action": "status"}),
    ("usage_analytics", {"action": "summary"}),
    ("skill_marketplace", {"action": "status"}),
    ("api_server", {"action": "status"}),
    ("federated_learning", {"action": "status"}),
    ("file_organizer", {"action": "scan", "directory": "D:/Eris_Source/actions"}),
    ("data_encryption", {"action": "status"}),
    ("system_monitor", {"action": "status"}),
    ("self_awareness", {"action": "status"}),
]
for tool_name, params in functional_tests:
    try:
        func = get_tool(tool_name)
        if func:
            result = func(parameters=params)
            if result and "error" not in str(result).lower()[:20]:
                ok("functional", tool_name + " -> " + str(result)[:60])
            else:
                warn("functional", tool_name + " -> " + str(result)[:60])
        else:
            fail("functional", tool_name + " -> not found")
    except Exception as e:
        fail("functional", tool_name + " -> " + str(e)[:80])

# ── 9. DATA FILES ──
print("[9] DATA FILES")
data_files = [
    "memory/long_term.json", "memory/episodic.json", "memory/semantic.json",
    "data/self/full_map.json", "core/prompt.txt", "data/autonomous_learn.json",
    "data/idle_learning.json",
]
for f in data_files:
    path = Path("D:/Eris_Source") / f
    if path.exists():
        size = path.stat().st_size
        ok("data", f + " ({:.1f}KB)".format(size / 1024))
    else:
        fail("data", f + " MISSING")

# ── 10. CHROMADB ──
print("[10] CHROMADB")
try:
    import chromadb
    client = chromadb.PersistentClient(path="D:/Eris_Source/data/chroma_db")
    collections = client.list_collections()
    total_docs = sum(c.count() for c in collections)
    ok("chromadb", "{} collections, {} docs".format(len(collections), total_docs))
except Exception as e:
    fail("chromadb", str(e))

# ── 11. OLLAMA ──
print("[11] OLLAMA")
try:
    import requests
    resp = requests.get("http://localhost:11434/api/tags", timeout=3)
    if resp.status_code == 200:
        models = resp.json().get("models", [])
        model_names = [m.get("name", "?") for m in models]
        ok("ollama", "online, {} models: {}".format(len(model_names), ", ".join(model_names[:5])))
    else:
        warn("ollama", "responded with status " + str(resp.status_code))
except Exception:
    warn("ollama", "not running")

# ── 12. SEMANTIC MEMORY ──
print("[12] SEMANTIC MEMORY")
try:
    from core.semantic_memory import get_memory_system
    ms = get_memory_system()
    status = ms.get_status()
    ok("semantic_memory", str(status)[:80])
except Exception as e:
    fail("semantic_memory", str(e))

# ── 13. OBSIDIAN VAULT ──
print("[13] OBSIDIAN VAULT")
obsidian_path = Path("D:/Eris_NEW/BaseDatosObsidian/BaseObsiEris")
if obsidian_path.exists():
    md_files = list(obsidian_path.rglob("*.md"))
    ok("obsidian", "{} markdown files".format(len(md_files)))
else:
    fail("obsidian", "vault not found")

# ── 14. PYTHON ENVIRONMENT ──
print("[14] PYTHON ENVIRONMENT")
ok("python", "version " + sys.version.split()[0])
packages = ["PyQt6", "requests", "chromadb", "google.genai"]
for pkg in packages:
    try:
        __import__(pkg)
        ok("packages", pkg)
    except ImportError:
        warn("packages", pkg + " not installed")

# ── 15. ERIS LOG HEALTH ──
print("[15] ERIS LOG")
log_path = Path("D:/Eris_Source/eris.log")
if log_path.exists():
    content = log_path.read_text(encoding="utf-8", errors="replace")
    lines = content.splitlines()
    errors = [l for l in lines if "ERROR" in l.upper() or "Traceback" in l]
    ok("log", "{} lines, {} errors".format(len(lines), len(errors)))
    if errors:
        for e in errors[-3:]:
            warn("log", e[:80])
else:
    fail("log", "eris.log not found")

# ── 16. TOOL DECLARATION DUPLICATES CHECK ──
print("[16] DUPLICATE CHECK")
try:
    from core.tool_declarations import TOOL_DECLARATIONS
    names = [t["name"] for t in TOOL_DECLARATIONS]
    seen = {}
    dupes = []
    for n in names:
        if n in seen:
            dupes.append(n)
        seen[n] = seen.get(n, 0) + 1
    if dupes:
        warn("dupes", "Duplicados: {}".format(", ".join(dupes)))
    else:
        ok("dupes", "Sin duplicados en declarations")
except Exception as e:
    fail("dupes", str(e))

# ── SUMMARY ──
print("\n" + "=" * 70)
print("  RESUMEN")
print("=" * 70)
print("  PASS: {}".format(PASS))
print("  FAIL: {}".format(FAIL))
print("  WARN: {}".format(WARN))
print("  TOTAL: {}".format(PASS + FAIL + WARN))

if FAIL > 0:
    print("\n  FALLOS:")
    for status, section, msg in RESULTS:
        if status == "FAIL":
            print("    [FAIL] {}: {}".format(section, msg))

if WARN > 0:
    print("\n  ADVERTENCIAS:")
    for status, section, msg in RESULTS:
        if status == "WARN":
            print("    [WARN] {}: {}".format(section, msg))

print("\n" + "=" * 70)
if FAIL == 0:
    print("  TODOS LOS TESTS PASARON!")
else:
    print("  {} TESTS FALLARON".format(FAIL))
print("=" * 70)
