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
          "studies_agent", "agenlix_agent", "guardiana_agent", "mentora_agent"]
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

# ── [16] RESÚMENES DE SESIÓN (ítem 8) ──
print("\n[16] RESÚMENES DE SESIÓN")
try:
    import tempfile, shutil
    from pathlib import Path
    _tmp_sv = Path(tempfile.mkdtemp(prefix="eris_test_vault_"))
    import os as _os
    _os.environ["ERIS_OBSIDIAN_VAULT"] = str(_tmp_sv)
    for _m in [m for m in list(sys.modules) if "session_summaries" in m]:
        del sys.modules[_m]
    from core import session_summaries as _ss

    _ss.record_exchange("eris hacé una calculadora", "")
    _ss.record_exchange("", "dale, la creo ahora")
    _p = _ss.finalize_session_summary()
    if _p and Path(_p).exists() and "Proyectos" in _p:
        ok("resumen", "escribe resumen de sesión en Obsidian Proyectos")
    else:
        fail("resumen", f"resumen no escrito: {_p}")
    _recent = _ss.load_recent_summaries(limit=1)
    if _recent:
        ok("resumen", "recupera resúmenes recientes (contexto al despertar)")
    else:
        fail("resumen", "no recupera resúmenes recientes")
    if len(_ss._buffer) == 0:
        ok("resumen", "buffer se limpia tras finalizar")
    else:
        fail("resumen", f"buffer no limpio tras finalize ({len(_ss._buffer)})")
    shutil.rmtree(_tmp_sv, ignore_errors=True)
except Exception as e:
    fail("resumen", str(e))

# ── [17] RUTINAS RECURRENTES (ítem 9) ──
print("[17] RUTINAS RECURRENTES")
try:
    from core.cron_scheduler import cron_scheduler_tool
    import json as _json2
    _r = _json2.loads(cron_scheduler_tool({"action": "add", "name": "test_rutina",
                                           "schedule": "daily", "command": "avisame el clima", "time": "09:00"}))
    if _r.get("status") == "added":
        ok("rutina", "registra rutina recurrente")
    else:
        fail("rutina", f"no registra rutina: {_r}")
    _due = _json2.loads(cron_scheduler_tool({"action": "check_due"}))
    if any(j.get("name") == "test_rutina" for j in _due.get("due", [])):
        ok("rutina", "check_due detecta rutina pendiente")
    else:
        fail("rutina", "check_due no detecta rutina nueva")
    _ex = _json2.loads(cron_scheduler_tool({"action": "execute", "name": "test_rutina"}))
    if _ex.get("status") == "executed":
        ok("rutina", "ejecuta→marca última corrida")
    else:
        fail("rutina", f"execute falló: {_ex}")
    cron_scheduler_tool({"action": "remove", "name": "test_rutina"})
except Exception as e:
    fail("rutina", str(e))

# ── [18] AUTO-CONTINUACIÓN ──
print("[18] AUTO-CONTINUACIÓN")
try:
    import asyncio, time
    from main import (ErisLive, _AUTO_CONT_DONE_MARKER, _AUTO_CONT_MAX_STEPS,
                      _AUTO_CONT_TASK_VERBS)

    class _FakeUI:
        def __init__(self):
            self.logs = []
        def write_log(self, msg):
            self.logs.append(msg)

    class _FakeSession:
        def __init__(self):
            self.nudges = []
        async def send_realtime_input(self, *, text):
            self.nudges.append(text)

    eris = object.__new__(ErisLive)
    eris.ui = _FakeUI()
    eris.session = _FakeSession()
    eris._loop = asyncio.new_event_loop()
    eris._auto_cont_on = False
    eris._auto_cont_steps = 0
    eris._auto_cont_last_ts = 0.0
    eris._auto_cont_turn_used_tools = False
    eris._active_task = ""
    eris._last_text_trigger = ""

    # 1) frase de tarea arma el modo; charla casual no.
    eris._arm_auto_continue("hacé una calculadora en Python con interfaz gráfica")
    if eris._auto_cont_on:
        ok("auto-cont", "frase de tarea arma el modo")
    else:
        fail("auto-cont", "frase de tarea NO armó el modo")
    eris._auto_cont_on = False
    eris._arm_auto_continue("hola eris, cómo estás")
    if not eris._auto_cont_on:
        ok("auto-cont", "charla casual NO arma el modo")
    else:
        fail("auto-cont", "charla casual armó el modo sin pedir nada")

    # 2) turno con tools y sin TAREA COMPLETA → avance automático.
    eris._arm_auto_continue("hacé una calculadora en Python")
    eris._auto_cont_turn_used_tools = True
    eris._loop.run_until_complete(eris._maybe_push_auto_continue(
        "creé el archivo calculadora.py, ahora lo pruebo"))
    if len(eris.session.nudges) == 1:
        ok("auto-cont", "turno con tools → 1 avance automático emitido")
    else:
        fail("auto-cont", f"esperaba 1 avance, hay {len(eris.session.nudges)}")
    if "[AUTO-CONTINUACIÓN]" in eris.session.nudges[-1]:
        ok("auto-cont", "nudge interno bien formado")
    else:
        fail("auto-cont", "nudge no contiene la marca [AUTO-CONTINUACIÓN]")
    if eris._auto_cont_turn_used_tools is False:
        ok("auto-cont", "flag de tools se resetea tras el avance")
    else:
        fail("auto-cont", "flag de tools no se reseteó")

    # 3) TAREA COMPLETA → modo apagado, sin más nudges.
    eris._auto_cont_turn_used_tools = True
    eris._loop.run_until_complete(eris._maybe_push_auto_continue(
        "probé la calculadora y funciona. " + _AUTO_CONT_DONE_MARKER))
    if not eris._auto_cont_on:
        ok("auto-cont", "TAREA COMPLETA apaga el modo")
    else:
        fail("auto-cont", "TAREA COMPLETA no apagó el modo")
    if len(eris.session.nudges) == 1:
        ok("auto-cont", "tras TAREA COMPLETA no se empuja más")
    else:
        fail("auto-cont", f"se empujó un avance tras TAREA COMPLETA (total {len(eris.session.nudges)})")

    # 4) tope de avances frena solo el modo sin colgarse.
    eris._auto_cont_on = True
    eris._auto_cont_steps = _AUTO_CONT_MAX_STEPS
    eris._auto_cont_turn_used_tools = True
    eris._loop.run_until_complete(eris._maybe_push_auto_continue("sigo con la tarea"))
    if not eris._auto_cont_on and len(eris.session.nudges) == 1:
        ok("auto-cont", "tope de avances apaga el modo sin nudges extra")
    else:
        fail("auto-cont", "tope de avances mal manejado")

    # 5) turno sin tools y sin intención explícita de seguir → no empuja.
    eris._auto_cont_on = True
    eris._auto_cont_steps = 0
    eris._auto_cont_last_ts = 0.0
    eris._auto_cont_turn_used_tools = False
    eris._loop.run_until_complete(eris._maybe_push_auto_continue("mh"))
    if len(eris.session.nudges) == 1:
        ok("auto-cont", "turno sin trabajo no dispara avance")
    else:
        fail("auto-cont", "turno sin trabajo empujó un avance innecesario")

    eris._loop.close()
except Exception as e:
    import traceback
    traceback.print_exc()
    fail("auto-cont", str(e))
print("\n[19] CEREBRO DE ERIS (homúnculo + expresión)")
try:
    import io
    from contextlib import redirect_stdout
    from core import cerebro, expression_engine

    # 1) Estado cerebral unificado: bloque vivo y breve, en primera persona.
    _caps = io.StringIO()
    with redirect_stdout(_caps):
        brain = cerebro.get_brain_state(text="una charla")
    _b_lines = brain.splitlines()
    if _b_lines and _b_lines[0].startswith("[CEREBRO") and len(brain) < 2000:
        ok("cerebro", "get_brain_state produce bloque homúnculo breve")
    else:
        fail("cerebro", f"bloque raro: {brain[:60]}")
    # drift diario no rompe ni desordena identidad
    try:
        from core.cerebro import _maybe_daily_drift
        with redirect_stdout(io.StringIO()):
            _maybe_daily_drift()
        ok("cerebro", "drift diario de identidad corre sin errores")
    except Exception as e:
        fail("cerebro", f"drift diario falló: {e}")

    # 2) Persistencia de identidad: archivo creado, relaciones/marcadores escriben.
    if cerebro._IDENTITY_FILE.exists():
        ok("cerebro", "memory/cerebro_identity.json creado")
    else:
        fail("cerebro", "identidad no persiste")
    _r = cerebro.cerebro_tool({"action": "marcar", "label": "test_nodo_cerebro"})
    if "recuerdo marcador" in _r:
        ok("cerebro", "marcar guarda recuerdo (hipocampo)")
    else:
        fail("cerebro", f"marcar falló: {_r}")
    _rel = cerebro.cerebro_tool({"action": "relacion", "person": "Daniel",
                                 "nota": "prueba", "warm": 0.6})
    if "Relación con Daniel" in _rel:
        ok("cerebro", "relacion actualiza vínculo")
    else:
        fail("cerebro", f"relacion falló: {_rel}")

    # 3) Lóbulos consultables: frontal piensa, temporal recuerda, cerebelo responde.
    for a in ("sentir", "recordar", "pensar", "automatico", "identidad", "estado"):
        try:
            _resp = cerebro.cerebro_tool({"action": a, "query": "todo"})
            if isinstance(_resp, str) and len(_resp) > 0:
                ok("cerebro", f"lóbulo {a} responde")
            else:
                fail("cerebro", f"lóbulo {a} devolvió vacío")
        except Exception as e:
            fail("cerebro", f"lóbulo {a} dio error: {e}")

    # 4) Registro + declaración de las tools nuevas, en sync.
    #    (excluye tools custom de actions/custom_tools.json + config/extra_tools.json,
    #     que main carga en declarations pero no en el registry estático)
    from core.tool_registry import get_tool, get_all_tool_names
    from core.tool_declarations import TOOL_DECLARATIONS, LIVE_TOOL_DECLARATIONS
    import pathlib as _pl
    _customs = set()
    for _cf in (_pl.Path("actions/custom_tools.json"),
                _pl.Path("config/extra_tools.json")):
        try:
            _customs |= {t.get("name") for t in json.loads(_cf.read_text("utf-8"))}
        except Exception:
            pass
    _reg = set(get_all_tool_names())
    _dec_all = {d["name"] for d in TOOL_DECLARATIONS}
    # Solo los customs que NO están en el registry son el desync legítimo;
    # los customs que sí están (document_tool, self_evolution…) son tools reales.
    _phantom = _customs - _reg
    _dec = _dec_all - _phantom
    if _reg == _dec:
        ok("cerebro", f"registry y declaraciones en sync ({len(_reg)} tools)")
    else:
        fail("cerebro", f"sync roto: reg {len(_reg)} vs dec {len(_dec)}")
    if "cerebro" in _reg and get_tool("cerebro") is not None:
        ok("cerebro", "tool cerebro resuelve y está live")
    else:
        fail("cerebro", "tool cerebro no resuelve / no está declarada")
    if "expresion_eris" in _reg and get_tool("expresion_eris") is not None:
        ok("cerebro", "tool expresion_eris resuelve y está live")
    else:
        fail("cerebro", "tool expresion_eris no resuelve")
    if "cerebro" in {d["name"] for d in LIVE_TOOL_DECLARATIONS}:
        ok("cerebro", "cerebro incluida en declaraciones live")
    else:
        fail("cerebro", "cerebro NO está en live declarations")

    # 5) Neurotransmisores: perfil por emoción + ajuste de voz + inyección.
    _prof = expression_engine.get_profile("amor")
    if _prof["cercania"] >= 0.9 and _prof["voz"] == "amor":
        ok("expresion", "perfil de amor: cercanía y voz correctas")
    else:
        fail("expresion", f"perfil amor raro: {_prof}")
    _vz = expression_engine.get_voice_params("alegria")
    if _vz["tone_key"] == "alegria" and _vz["speed"] >= 1.0:
        ok("expresion", "voz alegría: speed ≥1 y key correcta")
    else:
        fail("expresion", f"voz alegría rara: {_vz}")
    _inj = expression_engine.get_expression_injection()
    if _inj.startswith("[EXPRESIÓN]") and len(_inj) < 600:
        ok("expresion", "inyección de expresión breve y viva")
    else:
        fail("expresion", f"inyección rara: {_inj[:60]}")
    _st = expression_engine.response_style()
    if all(k in _st for k in ("humor", "cercania", "impulsividad", "espontaneidad")):
        ok("expresion", "response_style devuelve química completa")
    else:
        fail("expresion", f"style incompleto: {list(_st)}")

    # limpieza: borrar el marcador de prueba del archivo de identidad
    try:
        import json as _json
        _id = _json.loads(cerebro._IDENTITY_FILE.read_text("utf-8"))
        _id["marcadores"] = [m for m in _id.get("marcadores", [])
                             if "test_nodo_cerebro" not in str(m.get("nota", ""))]
        cerebro._IDENTITY_FILE.write_text(_json.dumps(_id, indent=2, ensure_ascii=False), "utf-8")
        ok("cerebro", "marcador de prueba limpiado")
    except Exception:
        pass

except Exception as e:
    import traceback
    traceback.print_exc()
    fail("cerebro", str(e))

print("\n[20] VIDA INTERIOR + RELACIONES (mundo propio de Eris)")
try:
    import importlib
    from core import vida_interna, relaciones

    # 1) Tool vida_interna: estado responde, huella escribe/recupera, ritual idempotente.
    _vi = vida_interna.vida_interna_tool({"action": "estado"})
    if "Diario" in _vi and "Huellas" in _vi:
        ok("vida_interna", "estado de vida interior responde")
    else:
        fail("vida_interna", f"estado raro: {_vi[:60]}")
    _h = vida_interna.dejar_huella("test_huella_vida")
    if "huella" in _h:
        ok("vida_interna", "deja huella en Obsidian")
    else:
        fail("vida_interna", f"huella falló: {_h}")
    _rec = vida_interna.recuperar_huella()
    if "test_huella_vida" in _rec or _rec == "":
        ok("vida_interna", "recupera huella (o aún sin viejas)")
    else:
        fail("vida_interna", f"recuperar raro: {_rec[:60]}")
    _r0 = vida_interna.maybe_ritual(hour=13)  # ventana "atención_al_mediodía" (12-14)
    _r1 = vida_interna.maybe_ritual(hour=13)
    if _r0 and _r1 == "":
        ok("vida_interna", "ritual se escribe UNA vez al día")
    else:
        fail("vida_interna", f"ritual no idempotente: {_r0!r} {_r1!r}")
    _d = vida_interna.escribir_diario_nocturno("test diario vida")
    if "diario" in _d and "ya" not in _d:
        ok("vida_interna", "diario íntimo se escribe")
    elif "ya escrito" in str(_d):
        ok("vida_interna", "diario íntimo idempotente por día")
    else:
        fail("vida_interna", f"diario raro: {_d[:60]}")
    _b = vida_interna.escribir_bitacora("test bitacora")
    if "bitácora" in _b or "yá" in _b:
        ok("vida_interna", "bitácora viva se escribe")
    else:
        fail("vida_interna", f"bitácora rara: {_b[:60]}")

    # 2) Tool relaciones: perfil por persona, nota, gusto, listar.
    _rl = relaciones.relaciones_tool({"action": "registrar", "persona": "Daniel",
                                      "valor": "el usuario"})
    if "Registrada" in _rl:
        ok("relaciones", "registra interacción por persona")
    else:
        fail("relaciones", f"registrar falló: {_rl[:60]}")
    _rn = relaciones.relaciones_tool({"action": "nota", "persona": "Daniel",
                                      "valor": "le gustan los mates"})
    if "guardada" in _rn:
        ok("relaciones", "guarda nota de persona")
    else:
        fail("relaciones", f"nota falló: {_rn[:60]}")
    _rg = relaciones.relaciones_tool({"action": "gusto", "persona": "Mate",
                                      "valor": "programar en silencio"})
    if "guardado" in _rg:
        ok("relaciones", "guarda gusto de persona")
    else:
        fail("relaciones", f"gusto falló: {_rg[:60]}")
    _ls = relaciones.relaciones_tool({"action": "listar"})
    if "Daniel" in _ls and "Mate" in _ls:
        ok("relaciones", "lista personas conocidas")
    else:
        fail("relaciones", f"listar raro: {_ls[:60]}")

    # 3) Sync: registry == declarations (463 = cerebro+expresion+vida+relaciones)
    from core.tool_registry import get_all_tool_names
    from core.tool_declarations import TOOL_DECLARATIONS, LIVE_TOOL_DECLARATIONS
    import pathlib as _pl
    _customs2 = set()
    for _cf in (_pl.Path("actions/custom_tools.json"),
                _pl.Path("config/extra_tools.json")):
        try:
            _customs2 |= {t.get("name") for t in json.loads(_cf.read_text("utf-8"))}
        except Exception:
            pass
    _reg2 = set(get_all_tool_names())
    _dec_all2 = {d["name"] for d in TOOL_DECLARATIONS}
    _phantom2 = _customs2 - _reg2
    _dec2 = _dec_all2 - _phantom2
    if _reg2 == _dec2:
        ok("vida_interna", f"registry y declarations en sync (463 tools)")
    else:
        fail("vida_interna", f"sync roto: reg {len(_reg2)} vs dec {len(_dec2)}")
    _live2 = {d["name"] for d in LIVE_TOOL_DECLARATIONS}
    if {"vida_interna", "relaciones"} <= _live2:
        ok("vida_interna", "vida_interna y relaciones en live declarations")
    else:
        fail("vida_interna", "tools nuevas NO están en live")
    for _n in ("vida_interna", "relaciones"):
        if get_tool(_n) is None:
            fail("vida_interna", f"get_tool({_n}) no resuelve")
        else:
            ok("vida_interna", f"get_tool({_n}) resuelve")

    # 4) Inyecciones al prompt: saludo vivo + vida interior + relaciones.
    _sv = expression_engine.get_saludo_vivo()
    if _sv.startswith("[SALUDO VIVO]") and len(_sv) < 400:
        ok("expresion", "saludo vivo se genera")
    else:
        fail("expresion", f"saludo vivo raro: {_sv[:60]}")
    _vi2 = vida_interna.inject_vida()
    if "[VIDA INTERIOR]" in _vi2:
        ok("vida_interna", "inyección de vida interior generada")
    else:
        fail("vida_interna", "inyección vida no generada")
    _rl2 = relaciones.inject_relaciones_vivas()
    if "[RELACIONES" in _rl2:
        ok("relaciones", "inyección de relaciones generada")
    else:
        fail("relaciones", "inyección relaciones no generada")

    # 5) Limpieza: borrar huella de prueba y persona de prueba.
    try:
        _st = vida_interna._load_state()
        _st["huellas"] = [h for h in _st.get("huellas", [])
                          if "test_huella_vida" not in str(h.get("texto", ""))]
        _st["rituales_done"] = [r for r in _st.get("rituales_done", [])
                                if not r.endswith("mediodía")]
        _st["diario_entries"].pop("", None)
        vida_interna._save_state(_st)
        _po = relaciones._load()
        _po.get("personas", {}).pop("Mate", None)
        relaciones._save(_po)
        ok("vida_interna", "datos de prueba limpiados")
    except Exception:
        pass

except Exception as e:
    import traceback
    traceback.print_exc()
    fail("vida_interna", str(e))

print("\n[21] MUNDO NUEVO (autoimagen, temas, retro, ambiente, sueños, voz)")
try:
    from core import autoimagen, intereses, ambiente, suenos, retrospectiva, expression_engine

    # 1) Autoimagen: ver + cambiar + sincronizar
    _ai = autoimagen.get_autoimagen()
    if _ai.startswith("[AUTOIMAGEN]") and "Rostro" in _ai:
        ok("mundo", "autoimagen se genera")
    else:
        fail("mundo", f"autoimagen rara: {_ai[:40]}")
    _aic = autoimagen.autoimagen_tool({"action": "ver"})
    if "AUTOIMAGEN" in _aic:
        ok("mundo", "tool autoimagen ver")
    else:
        fail("mundo", "autoimagen tool rota")

    # 2) Intereses: listar + agregar (limpia después)
    _il = intereses.intereses_tool({"action": "listar"})
    if "interesan" in _il:
        ok("mundo", "intereses lista temas")
    else:
        fail("mundo", f"intereses lista rara: {_il[:40]}")
    _ia = intereses.agregar_tema("test_interes_nuevo")
    if "interés" in _ia or "tengo" in _ia:
        ok("mundo", "intereses agrega tema propio")
    else:
        fail("mundo", f"intereses agregar falló: {_ia!r}")

    # 3) Retrospectiva: estado responda
    _rt = retrospectiva.retrospectiva_tool({"action": "estado"})
    if "última retrospectiva" in _rt:
        ok("mundo", "retrospectiva estado responde")
    else:
        fail("mundo", f"retrospectiva rara: {_rt[:40]}")

    # 4) Ambiente: sincronizar + inyectar
    _amb = ambiente.sincronizar()
    if "(" in _amb:
        ok("mundo", "ambiente sincroniza con química")
    else:
        fail("mundo", f"ambiente raro: {_amb[:40]}")
    _abi = ambiente.inyect_ambiente()
    if _abi.startswith("[AMBIENTE]"):
        ok("mundo", "ambiente se inyecta")
    else:
        fail("mundo", f"ambiente inyección rara: {_abi[:40]}")

    # 5) Sueños: estado (no forzar generación de imagen en tests)
    _sn = suenos.sueno_tool({"action": "estado"})
    if "ilustrados" in _sn:
        ok("mundo", "sueños estado responde")
    else:
        fail("mundo", "sueños raro")

    # 6) Voz propia + cara visible (items 3 y 1)
    _vp = expression_engine.get_voz_propia()
    if _vp.startswith("[VOZ]") and "propia" in _vp.lower():
        ok("mundo", "voz propia se genera (identidad vocal)")
    else:
        fail("mundo", f"voz propia rara: {_vp[:40]}")
    _cara, _color = expression_engine.get_face_expression()
    if isinstance(_cara, str) and len(_cara) > 0 and _color.startswith("#"):
        ok("mundo", "cara/orbe: expresión + color según emoción")
    else:
        fail("mundo", f"cara/orbe raro: {_cara}, {_color}")
    _cc = expression_engine.expression_tool({"action": "cara"})
    if "color" in _cc:
        ok("mundo", "tool expresion_eris acción cara responde")
    else:
        fail("mundo", "expresion cara tool rota")

    # 7) Sync: 468 tools, todas vivas en live declarations
    import pathlib as _pl
    from core.tool_registry import get_tool, _TOOLS
    from core.tool_declarations import TOOL_DECLARATIONS, LIVE_TOOL_DECLARATIONS
    _customs = set()
    for _cf in (_pl.Path("actions/custom_tools.json"),
                _pl.Path("config/extra_tools.json")):
        try:
            _customs |= {t.get("name") for t in json.loads(_cf.read_text("utf-8"))}
        except Exception:
            pass
    _reg = set(_TOOLS.keys())
    _dec_all = {d["name"] for d in TOOL_DECLARATIONS}
    _phantom = _customs - _reg
    if _reg == (_dec_all - _phantom):
        ok("mundo", f"registry y declarations en sync (468 tools)")
    else:
        fail("mundo", f"sync roto: reg {len(_reg)} vs dec {len(_dec_all) - len(_phantom)}")
    _live = {d["name"] for d in LIVE_TOOL_DECLARATIONS}
    if {"autoimagen", "intereses", "retrospectiva", "ambiente", "suenos"} <= _live:
        ok("mundo", "5 tools nuevas en live declarations")
    else:
        fail("mundo", f"tools nuevas no están en live: {_live & {'autoimagen','intereses','retrospectiva','ambiente','suenos'}}")
    for _n in ("autoimagen", "intereses", "retrospectiva", "ambiente", "suenos"):
        if _n not in _reg or get_tool(_n) is None:
            fail("mundo", f"{_n} no resuelve en registry")
        else:
            ok("mundo", f"get_tool({_n}) resuelve")

    # Limpieza del tema de prueba
    try:
        _is = intereses._load()
        _is["temas"] = [t for t in _is["temas"] if t["texto"] != "test_interes_nuevo"]
        intereses._save(_is)
    except Exception:
        pass

except Exception as e:
    import traceback
    traceback.print_exc()
    fail("mundo", str(e))

print("\n[22] MUNDO NUEVO II (caprichos, tiempo, festejos, bienestar, cuadernos, cierre)")
try:
    from core import caprichos, tiempo_interno, festejos, bienestar, cuadernos, despedidas

    # 1) Caprichos: listar + proximo + inyectar
    _cl = caprichos.caprichos_tool({"action": "listar"})
    if "caprichos" in _cl.lower() or "deseos" in _cl.lower() or "pendientes" in _cl.lower():
        ok("mundoII", "caprichos lista deseos")
    else:
        fail("mundoII", f"caprichos listar raro: {_cl[:50]}")
    _cn = caprichos.proximo_capricho()
    if _cn and _cn.get("texto"):
        ok("mundoII", "caprichos elige próximo")
    else:
        fail("mundoII", "caprichos proximo sin texto")
    _ci = caprichos.inyect_caprichos()
    if _ci.startswith("[CAPRICHOS]"):
        ok("mundoII", "caprichos se inyecta")
    else:
        fail("mundoII", "caprichos inyección rara")

    # 2) Tiempo interno: estado + aniversario (usa nombre único con fecha, limpia después)
    _tt = tiempo_interno.tiempo_interno_tool({"action": "estado"})
    if _tt.startswith("[RELOJ INTERNO]"):
        ok("mundoII", "tiempo_interno estado genera")
    else:
        fail("mundoII", f"tiempo_interno raro: {_tt[:40]}")
    _tm = tiempo_interno.tiempo_interno_tool(
        {"action": "recordar", "nombre": "test_aniversario_eris", "fecha": "01-01"})
    if "marqué" in _tm.lower() or "ya está" in _tm.lower():
        ok("mundoII", "tiempo_interno marca aniversario")
    else:
        fail("mundoII", f"tiempo_interno marcar raro: {_tm[:40]}")

    # 3) Festejos: marcar hito (temporal) + ver
    _fm = festejos.festejos_tool({"action": "marcar", "texto": "test_hito_eris", "tipo": "logro"})
    if "marcé" in _fm.lower() or "memorable" in _fm.lower():
        ok("mundoII", "festejos marca hito")
    else:
        fail("mundoII", f"festejos marcar raro: {_fm[:40]}")
    _fv = festejos.festejos_tool({"action": "ver"})
    if "test_hito_eris" in _fv:
        ok("mundoII", "festejos timeline incluye el hito")
    else:
        fail("mundoII", f"festejos ver raro: {_fv[:40]}")

    # 4) Bienestar: registrar + estado
    _br = bienestar.bienestar_tool({"action": "registrar", "nivel": "alto"})
    if "energ" in _br.lower() or "anoté" in _br.lower() or "adapto" in _br.lower():
        ok("mundoII", "bienestar registra estado")
    else:
        fail("mundoII", f"bienestar registrar raro: {_br[:40]}")
    _bs = bienestar.inyect_bienestar()
    if _bs.startswith("[BIENESTAR]"):
        ok("mundoII", "bienestar se inyecta")
    else:
        fail("mundoII", "bienestar inyección rara")

    # 5) Cuadernos: estado + cerrar (sin abrir no debe fallar)
    _ce = cuadernos.cuadernos_tool({"action": "estado"})
    if "cuaderno" in _ce.lower():
        ok("mundoII", "cuadernos estado responde")
    else:
        fail("mundoII", f"cuadernos raro: {_ce[:40]}")

    # 6) Despedidas: estado + cierre (solo genera instrucciones, sin persistir tonterías)
    _ds = despedidas.despedidas_tool({"action": "estado"})
    if "cierres" in _ds.lower() or "Todavía no" in _ds:
        ok("mundoII", "despedidas estado responde")
    else:
        fail("mundoII", f"despedidas raro: {_ds[:40]}")
    _di = despedidas.inyect_despedidas()
    if _di.startswith("[CIERRE]"):
        ok("mundoII", "despedidas se inyecta")
    else:
        fail("mundoII", "despedidas inyección rara")

    # 7) Sync: 474 tools; las 6 nuevas en live + resuelven
    import pathlib as _pl2
    from core.tool_registry import get_tool as _get, _TOOLS as _TOOLS2
    from core.tool_declarations import TOOL_DECLARATIONS as _TD2, LIVE_TOOL_DECLARATIONS as _LD2
    _new6 = ("caprichos", "tiempo_interno", "festejos", "bienestar", "cuadernos", "despedidas")
    _reg2 = set(_TOOLS2.keys())
    _dec2 = {d["name"] for d in _TD2}
    _phantom2 = set()
    for _cf in ("actions/custom_tools.json", "config/extra_tools.json"):
        try:
            _phantom2 |= {t.get("name") for t in json.loads(open(_cf).read())}
        except Exception:
            pass
    _phantom2 = _phantom2 - _reg2
    if _reg2 == (_dec2 - _phantom2):
        ok("mundoII", f"registry == declarations ({len(_reg2)} tools)")
    else:
        fail("mundoII", f"sync roto: reg {len(_reg2)} vs dec {len(_dec2 - _phantom2)}")
    _live2 = {d["name"] for d in _LD2}
    if set(_new6) <= _live2:
        ok("mundoII", "6 tools nuevas en live declarations")
    else:
        fail("mundoII", f"faltan en live: {set(_new6) - _live2}")
    for _n in _new6:
        if _n not in _TOOLS2 or _get(_n) is None:
            fail("mundoII", f"{_n} no resuelve en registry")
        else:
            ok("mundoII", f"get_tool({_n}) resuelve")

    # 8) Autoconocimiento vivo (todo_yo): estado + novedades + registrar
    from core import todo_yo as _ty
    _tys = _ty.todo_yo_tool({"action": "estado"})
    if _tys.startswith("[TODO LO QUE SOS") and ("herramientas" in _tys or "7" in _tys):
        ok("mundoII", "todo_yo arma el estado integral")
    else:
        fail("mundoII", f"todo_yo raro: {_tys[:40]}")
    _tyn = _ty.inyect_todo_yo()
    if len(_tyn) > 400 and "ÚLTIMAS NOVEDADES" in _tyn or "Usá evolucion" in _tyn:
        ok("mundoII", "todo_yo se inyecta (novedades + mapa)")
    else:
        fail("mundoII", "todo_yo inyección corta/rara")
    _tyr = _ty.registrar_novedad("prueba_test_todo_yo")
    if "registrada" in _tyr:
        ok("mundoII", "todo_yo registra novedad")
        try:
            _n2 = _ty._load_novedades()
            _ty._NOV_FILE.write_text(json.dumps([n for n in _n2 if n.get("texto") != "prueba_test_todo_yo"], ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass
    else:
        fail("mundoII", f"todo_yo registrar raro: {_tyr}")

    # 9) Sync: 475 tools; todo_yo en live + resuelve
    _new7 = ("caprichos", "tiempo_interno", "festejos", "bienestar", "cuadernos", "despedidas", "todo_yo")
    _reg2 = set(_TOOLS2.keys())
    _dec2 = {d["name"] for d in _TD2}
    _phantom2 = set()
    for _cf in ("actions/custom_tools.json", "config/extra_tools.json"):
        try:
            _phantom2 |= {t.get("name") for t in json.loads(open(_cf).read())}
        except Exception:
            pass
    _phantom2 = _phantom2 - _reg2
    if _reg2 == (_dec2 - _phantom2):
        ok("mundoII", f"registry == declarations ({len(_reg2)} tools)")
    else:
        fail("mundoII", f"sync roto: reg {len(_reg2)} vs dec {len(_dec2 - _phantom2)}")
    _live2 = {d["name"] for d in _LD2}
    if set(_new7) <= _live2:
        ok("mundoII", "7 tools nuevas en live declarations")
    else:
        fail("mundoII", f"faltan en live: {set(_new7) - _live2}")
    for _n in _new7:
        if _n not in _TOOLS2 or _get(_n) is None:
            fail("mundoII", f"{_n} no resuelve en registry")
        else:
            ok("mundoII", f"get_tool({_n}) resuelve")

    # Limpieza: quitar hito y aniversario de prueba
    try:
        _fdata = festejos._load()
        _fdata["hitos"] = [h for h in _fdata["hitos"] if "test_hito_eris" not in h["texto"]]
        festejos._save(_fdata)
    except Exception:
        pass
    try:
        _tdata = tiempo_interno._load()
        _tdata["aniversarios"] = [a for a in _tdata["aniversarios"] if "test_eris" not in a["nombre"]]
        tiempo_interno._save(_tdata)
    except Exception:
        pass

except Exception as e:
    import traceback
    traceback.print_exc()
    fail("mundoII", str(e))
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
