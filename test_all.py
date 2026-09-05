"""ERIS System Test — 26/08/2026"""
import json, os, sys, py_compile
from pathlib import Path

PASS = 0
FAIL = 0
WARN = 0
RESULTS = []
BASE = Path(__file__).resolve().parent

def ok(section, msg):
    global PASS; PASS += 1; RESULTS.append(("PASS", section, msg))

def fail(section, msg):
    global FAIL; FAIL += 1; RESULTS.append(("FAIL", section, msg))

def warn(section, msg):
    global WARN; WARN += 1; RESULTS.append(("WARN", section, msg))

print("=" * 70)
print("  TEST COMPLETO DE ERIS — 26/08/2026")
print("=" * 70)

# ── 1. TOOL REGISTRY (442 tools) ──
print("\n[1] TOOL REGISTRY")
try:
    from core.tool_registry import get_tool, get_all_tool_names, _TOOLS
    tools = get_all_tool_names()
    if len(tools) >= 440:
        ok("registry", f"{len(tools)} tools loaded")
    else:
        fail("registry", f"Expected 442, got {len(tools)}")
except Exception as e:
    fail("registry", str(e))

# ── 2. TOOL DECLARATIONS (442 declarations) ──
print("[2] TOOL DECLARATIONS")
try:
    from core.tool_declarations import TOOL_DECLARATIONS
    if len(TOOL_DECLARATIONS) >= 440:
        ok("declarations", f"{len(TOOL_DECLARATIONS)} declarations")
    else:
        fail("declarations", f"Expected 442, got {len(TOOL_DECLARATIONS)}")
except Exception as e:
    fail("declarations", str(e))

# ── 3. DECLARATIONS ↔ REGISTRY SYNC ──
print("[3] SYNC CHECK")
try:
    dec_names = {t["name"] for t in TOOL_DECLARATIONS}
    reg_names = set(tools)
    missing_in_reg = dec_names - reg_names
    missing_in_dec = reg_names - dec_names
    if not missing_in_reg and not missing_in_dec:
        ok("sync", f"Perfect: {len(dec_names)} == {len(reg_names)}")
    else:
        if missing_in_reg:
            warn("sync", f"In declarations but not registry: {missing_in_reg}")
        if missing_in_dec:
            warn("sync", f"In registry but not declarations: {missing_in_dec}")
except Exception as e:
    fail("sync", str(e))

# ── 4. NO DUPLICATE DECLARATIONS ──
print("[4] NO DUPLICATES")
try:
    names = [t["name"] for t in TOOL_DECLARATIONS]
    dupes = [n for n in names if names.count(n) > 1]
    if not dupes:
        ok("dupes", "Zero duplicates in declarations")
    else:
        fail("dupes", f"Duplicates: {set(dupes)}")
except Exception as e:
    fail("dupes", str(e))

# ── 5. CORE MODULES IMPORT ──
print("[5] CORE MODULES")
core_modules = [
    "core.tool_registry", "core.tool_declarations", "core.tool_dispatcher",
    "core.logging_setup", "core.self_map", "core.emotional_state",
    "core.llm_bridge", "core.rag_pipeline", "core.autonomous_learner",
    "core.idle_learning_loop", "core.agent_router", "core.neuro_spheres",
    "core.gemini_text_chat", "core.memory_consolidation",
    "core.semantic_memory", "core.prompt_loader",
]
for mod_name in core_modules:
    try:
        __import__(mod_name)
        ok("core", mod_name)
    except Exception as e:
        fail("core", f"{mod_name}: {e}")

# ── 6. AGENT IMPORTS ──
print("[6] AGENTS")
agents = ["dev_agent", "media_agent", "productivity_agent", "search_agent",
          "security_agent", "system_agent", "vision_agent", "opencode_bridge",
          "studies_agent"]
for a in agents:
    try:
        __import__(f"agents.{a}")
        ok("agents", a)
    except Exception as e:
        fail("agents", f"{a}: {e}")

# ── 7. NEUROSPHERES AUTO-LEARN ──
print("[7] NEUROSPHERES")
try:
    from core.neuro_spheres import get_status, add_node, learn_from_sessions
    status = get_status()
    total = status["total_nodes"]
    if total >= 80:
        ok("neuro", f"{total} nodes, {status['total_connections']} connections")
    else:
        warn("neuro", f"Only {total} nodes (expected >= 80)")
    
    # Test add_node
    import time
    test_title = f"TEST_NODE_{int(time.time()*1000)}"
    r = add_node("aprendizaje", "aprendizaje", test_title, "test")
    if r.get("success") or r.get("status") == "updated":
        ok("neuro", "add_node works")
    else:
        fail("neuro", f"add_node failed: {r}")
except Exception as e:
    fail("neuro", str(e))

# ── 8. CLI FILE EXISTS ──
print("[8] CLI")
cli_path = BASE / "eris_cli.py"
if cli_path.exists():
    size = cli_path.stat().st_size
    ok("cli", f"eris_cli.py ({size} bytes)")
else:
    fail("cli", "eris_cli.py not found")

bat_path = Path(r"C:\Users\danie\.eris\bin\eris.bat")
if bat_path.exists():
    ok("cli", "eris.bat exists")
else:
    fail("cli", "eris.bat not found")

# ── 9. ACTION IMPORTS (no duplicates) ──
print("[9] ACTION IMPORTS")
try:
    ai_content = (BASE / "core" / "action_imports.py").read_text("utf-8")
    lines = ai_content.splitlines()
    import_lines = [l for l in lines if "from actions." in l and "import" in l and "(" not in l]
    action_names = []
    for l in import_lines:
        parts = l.split()
        for i, p in enumerate(parts):
            if p == "import" and i + 1 < len(parts):
                action_names.append(parts[i + 1].strip())
    dupes = [n for n in action_names if action_names.count(n) > 1]
    if not dupes:
        ok("imports", f"{len(action_names)} imports, 0 duplicates")
    else:
        fail("imports", f"Duplicate imports: {set(dupes)}")
except Exception as e:
    fail("imports", str(e))

# ── 10. DATA FILES ──
print("[10] DATA FILES")
data_files = [
    "memory/long_term.json", "memory/episodic.json", "memory/semantic.json",
    "memory/neuro_spheres_state.json", "core/prompt.txt",
    "config/api_keys.json",
]
for f in data_files:
    path = BASE / f
    if path.exists():
        size = path.stat().st_size
        ok("data", f"{f} ({size // 1024}KB)")
    else:
        fail("data", f"{f} MISSING")

# ── 11. KNOWLEDGE FILES ──
print("[11] KNOWLEDGE")
kb_dir = BASE / "data" / "knowledge"
if kb_dir.exists():
    md_files = list(kb_dir.glob("*.md"))
    ok("knowledge", f"{len(md_files)} files")
else:
    fail("knowledge", "knowledge dir not found")

# ── 12. PYTHON ENVIRONMENT ──
print("[12] PYTHON")
ok("python", f"version {sys.version.split()[0]}")
packages = ["PyQt6", "requests", "chromadb", "google.genai"]
for pkg in packages:
    try:
        __import__(pkg)
        ok("packages", pkg)
    except ImportError:
        warn("packages", f"{pkg} not installed")

# ── 13. COMPILE CHECK ──
print("[13] COMPILE CHECK")
critical_files = [
    "main.py", "eris_cli.py", "ui.py",
    "core/tool_registry.py", "core/tool_declarations.py",
    "core/action_imports.py", "core/neuro_spheres.py",
    "core/gemini_text_chat.py", "core/tool_dispatcher.py",
]
for f in critical_files:
    try:
        py_compile.compile(str(BASE / f), doraise=True)
        ok("compile", f)
    except py_compile.PyCompileError as e:
        fail("compile", f"{f}: {e}")

# ── 14. BOM CHECK ──
print("[14] BOM CHECK")
bom_count = 0
for root, dirs, files in os.walk(BASE):
    if ".venv" in root or "__pycache__" in root or "backups" in root:
        continue
    for f in files:
        if f.endswith((".py", ".json")):
            fp = os.path.join(root, f)
            try:
                with open(fp, "rb") as fh:
                    if fh.read(3) == b"\xef\xbb\xbf":
                        bom_count += 1
                        warn("bom", f"BOM found: {os.path.relpath(fp, BASE)}")
            except:
                pass
if bom_count == 0:
    ok("bom", "Zero BOM files")

# ── 15. WINDOW CHECK ──
print("[15] GUI WINDOW")
try:
    import ctypes
    user32 = ctypes.windll.user32
    hwnd = user32.FindWindowW(None, "ERIS")
    if hwnd:
        rect = ctypes.wintypes.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        w = rect.right - rect.left
        h = rect.bottom - rect.top
        if w > 100 and h > 100:
            ok("gui", f"Window visible: {w}x{h}")
        else:
            warn("gui", f"Window too small: {w}x{h}")
    else:
        warn("gui", "No ERIS window found (may not be running)")
except Exception as e:
    warn("gui", str(e))

# ── SUMMARY ──
print("\n" + "=" * 70)
print("  RESUMEN")
print("=" * 70)
print(f"  PASS: {PASS}")
print(f"  FAIL: {FAIL}")
print(f"  WARN: {WARN}")
print(f"  TOTAL: {PASS + FAIL + WARN}")

if FAIL > 0:
    print("\n  FALLOS:")
    for status, section, msg in RESULTS:
        if status == "FAIL":
            print(f"    [FAIL] {section}: {msg}")

if WARN > 0:
    print("\n  ADVERTENCIAS:")
    for status, section, msg in RESULTS:
        if status == "WARN":
            print(f"    [WARN] {section}: {msg}")

print("\n" + "=" * 70)
if FAIL == 0:
    print("  TODOS LOS TESTS PASARON!")
else:
    print(f"  {FAIL} TESTS FALLARON")
print("=" * 70)
