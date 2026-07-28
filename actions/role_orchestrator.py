# -*- coding: utf-8 -*-
"""
role_orchestrator.py — ERIS Micro-Agent Orchestrator.
Single identity, multiple specialized roles sharing a blackboard.

Architecture:
  Blackboard (data/blackboard.json) — shared state between all roles
  Roles — specialized functions using existing ERIS tools
  Orchestrator — plans, dispatches, and reviews role execution

Roles:
  researcher  — gathers info (web_search, webfetch, memory_rag)
  programmer  — writes code (code_generator, self_edit)
  validator   — checks quality (code_analyzer, self_healing_loop, ruff)
  debugger    — fixes bugs (self_heal, self_healing_loop)
  analyst     — analyzes data (system_reader, data patterns)
  executor    — runs commands (terminal_agent)

Flow:
  mission → plan → roles execute → blackboard → result
"""
import json
import os
import time
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
BLACKBOARD_FILE = BASE_DIR / "data" / "blackboard.json"
MISSION_LOG = BASE_DIR / "data" / "mission_log.json"


# ═══════════════════════════════════════════════════════════════
# BLACKBOARD — Pizarrón Compartido
# ═══════════════════════════════════════════════════════════════

def _load_blackboard() -> dict:
    """Load the shared blackboard state."""
    try:
        if BLACKBOARD_FILE.exists():
            return json.loads(BLACKBOARD_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_blackboard(data: dict):
    """Save blackboard state."""
    BLACKBOARD_FILE.parent.mkdir(parents=True, exist_ok=True)
    BLACKBOARD_FILE.write_text(
        json.dumps(data, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8"
    )


def _clear_blackboard():
    """Clear blackboard for a new mission."""
    _save_blackboard({
        "mission": "",
        "status": "IDLE",
        "plan": [],
        "current_role": "",
        "results": {},
        "errors": [],
        "started_at": datetime.now().isoformat(),
        "completed_at": "",
    })


def _update_blackboard(**kwargs):
    """Update specific fields in the blackboard."""
    bb = _load_blackboard()
    bb.update(kwargs)
    _save_blackboard(bb)


# ═══════════════════════════════════════════════════════════════
# MISSION LOG
# ═══════════════════════════════════════════════════════════════

def _log_mission(mission: str, plan: list, result: str, success: bool):
    """Log mission execution for history."""
    try:
        entries = []
        if MISSION_LOG.exists():
            entries = json.loads(MISSION_LOG.read_text(encoding="utf-8"))
        entries.append({
            "time": datetime.now().isoformat(),
            "mission": mission[:200],
            "plan": plan,
            "result_preview": result[:300],
            "success": success,
        })
        MISSION_LOG.parent.mkdir(parents=True, exist_ok=True)
        MISSION_LOG.write_text(
            json.dumps(entries[-100:], indent=2, ensure_ascii=False, default=str),
            encoding="utf-8"
        )
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════
# ROLES — Specialized functions using existing ERIS tools
# ═══════════════════════════════════════════════════════════════

def _role_researcher(blackboard: dict) -> dict:
    """
    Researcher role: gathers information from web, memory, files.
    Uses: web_search, webfetch, memory_rag
    """
    mission = blackboard.get("mission", "")
    context = blackboard.get("context", "")
    research_data = []

    # 1. Search memory for relevant past knowledge
    try:
        from actions.memory_rag import memory_rag
        mem_result = memory_rag({"action": "search", "query": mission})
        if mem_result and "no" not in mem_result.lower()[:20]:
            research_data.append(f"[MEMORY] {mem_result[:500]}")
    except Exception:
        pass

    # 2. Check system state if relevant
    try:
        from actions.system_reader import system_reader
        sys_result = system_reader({"action": "status"})
        if sys_result:
            research_data.append(f"[SYSTEM] {sys_result[:300]}")
    except Exception:
        pass

    # 3. Check existing codebase for relevant files
    try:
        search_terms = mission.lower().split()
        relevant_files = []
        for f in BASE_DIR.rglob("*.py"):
            if any(term in f.name.lower() for term in search_terms if len(term) > 3):
                relevant_files.append(str(f.relative_to(BASE_DIR)))
        if relevant_files:
            research_data.append(f"[CODEBASE] Relevant files: {', '.join(relevant_files[:10])}")
    except Exception:
        pass

    result = "\n".join(research_data) if research_data else "No relevant context found."
    return {
        "status": "complete",
        "data": result,
        "files_found": len(research_data),
    }


def _role_programmer(blackboard: dict) -> dict:
    """
    Programmer role: generates or writes code.
    Uses: code_generator, self_edit
    """
    mission = blackboard.get("mission", "")
    context = blackboard.get("context", "")
    research = blackboard.get("results", {}).get("researcher", {}).get("data", "")

    code_parts = []

    # 1. Try code_generator for quick generation
    try:
        from actions.code_generator import code_generator
        gen_result = code_generator({
            "action": "generate",
            "description": mission,
            "language": "python"
        })
        if gen_result and "error" not in gen_result.lower()[:20]:
            code_parts.append(gen_result[:2000])
    except Exception:
        pass

    # 2. If we need to read existing code first
    try:
        from actions.self_edit import self_edit
        # Check if there are files to modify
        target_file = context.get("target_file", "") if isinstance(context, dict) else ""
        if target_file:
            existing = self_edit({"action": "read_file", "file": target_file})
            if existing and "error" not in existing.lower()[:20]:
                code_parts.append(f"[EXISTING CODE]\n{existing[:2000]}")
    except Exception:
        pass

    result = "\n\n".join(code_parts) if code_parts else "Code generation requires more specific instructions."
    return {
        "status": "complete",
        "code": result,
        "files_generated": len(code_parts),
    }


def _role_validator(blackboard: dict) -> dict:
    """
    Validator role: checks code quality and correctness.
    Uses: code_analyzer, self_healing_loop, ruff
    """
    mission = blackboard.get("mission", "")
    code = blackboard.get("results", {}).get("programmer", {}).get("code", "")
    target_file = ""
    if isinstance(blackboard.get("context"), dict):
        target_file = blackboard["context"].get("target_file", "")

    validation_results = []

    # 1. If there's a target file, analyze it
    if target_file:
        # Syntax check
        try:
            from actions.self_healing_loop import self_healing_loop
            test_result = self_healing_loop({"action": "test", "file": target_file})
            validation_results.append(f"[TEST] {test_result[:500]}")
        except Exception:
            pass

        # Ruff check
        try:
            from actions.code_analyzer import code_analyzer
            ruff_result = code_analyzer({"action": "ruff", "path": target_file})
            validation_results.append(f"[RUFF] {ruff_result[:500]}")
        except Exception:
            pass

        # Detect issues
        try:
            from actions.self_healing_loop import self_healing_loop
            detect_result = self_healing_loop({"action": "detect", "file": target_file})
            validation_results.append(f"[DETECT] {detect_result[:500]}")
        except Exception:
            pass

    # 2. If we have generated code, validate it
    elif code:
        try:
            from actions.self_healing_loop import self_healing_loop
            val_result = self_healing_loop({"action": "validate", "code": code})
            validation_results.append(f"[VALIDATE] {val_result[:500]}")
        except Exception:
            pass

    # 3. Quick security scan
    if target_file:
        try:
            from actions.code_review import code_review
            sec_result = code_review({"action": "quick", "path": target_file})
            validation_results.append(f"[SECURITY] {sec_result[:300]}")
        except Exception:
            pass

    result = "\n".join(validation_results) if validation_results else "No validation targets."
    issues_found = result.lower().count("error") + result.lower().count("fail") + result.lower().count("critical")

    return {
        "status": "complete",
        "result": result,
        "issues_found": issues_found,
        "passed": issues_found == 0,
    }


def _role_debugger(blackboard: dict) -> dict:
    """
    Debugger role: fixes detected issues.
    Uses: self_heal, self_healing_loop, self_edit
    """
    target_file = ""
    if isinstance(blackboard.get("context"), dict):
        target_file = blackboard["context"].get("target_file", "")

    validation = blackboard.get("results", {}).get("validator", {})
    issues = validation.get("issues_found", 0)

    fix_results = []

    if target_file and issues > 0:
        # 1. Auto-fix what we can
        try:
            from actions.self_heal import self_heal
            fix_result = self_heal({"action": "auto_fix", "file": target_file})
            fix_results.append(f"[AUTO_FIX] {fix_result[:500]}")
        except Exception:
            pass

        # 2. Detect remaining issues
        try:
            from actions.self_healing_loop import self_healing_loop
            detect = self_healing_loop({"action": "detect", "file": target_file})
            fix_results.append(f"[DETECT_AFTER] {detect[:500]}")
        except Exception:
            pass

    result = "\n".join(fix_results) if fix_results else "No fixes needed or no target file."
    return {
        "status": "complete",
        "result": result,
        "fixes_applied": len(fix_results),
    }


def _role_analyst(blackboard: dict) -> dict:
    """
    Analyst role: analyzes data, metrics, performance.
    Uses: system_reader patterns, file analysis
    """
    mission = blackboard.get("mission", "")
    context = blackboard.get("context", {})
    target_file = context.get("target_file", "") if isinstance(context, dict) else ""

    analysis = []

    # 1. System info
    try:
        from actions.system_reader import system_reader
        sys_info = system_reader({"action": "info"})
        if sys_info:
            analysis.append(f"[SYS] {sys_info[:300]}")
    except Exception:
        pass

    # 2. File analysis if target exists
    if target_file:
        try:
            fp = BASE_DIR / target_file
            if fp.exists():
                content = fp.read_text(encoding="utf-8", errors="replace")
                lines = content.split("\n")
                funcs = sum(1 for l in lines if l.strip().startswith("def "))
                classes = sum(1 for l in lines if l.strip().startswith("class "))
                imports = sum(1 for l in lines if "import " in l)
                analysis.append(
                    f"[METRICS] {target_file}: {len(lines)} lines, "
                    f"{funcs} functions, {classes} classes, {imports} imports"
                )
        except Exception:
            pass

    result = "\n".join(analysis) if analysis else "No analysis targets."
    return {
        "status": "complete",
        "result": result,
    }


def _role_executor(blackboard: dict) -> dict:
    """
    Executor role: runs terminal commands, opens apps, system operations.
    Uses: terminal_agent
    """
    context = blackboard.get("context", {})
    command = context.get("command", "") if isinstance(context, dict) else ""

    if not command:
        return {"status": "skip", "result": "No command to execute."}

    try:
        from actions.terminal_agent import terminal_agent
        result = terminal_agent({"action": "run", "command": command})
        return {
            "status": "complete",
            "result": result[:1000],
        }
    except Exception as e:
        return {
            "status": "error",
            "result": str(e),
        }


# ═══════════════════════════════════════════════════════════════
# ROLE REGISTRY
# ═══════════════════════════════════════════════════════════════

ROLES = {
    "researcher": {
        "fn": _role_researcher,
        "name": "Ada",
        "description": "Investiga contexto, busca en memoria, web, y código",
        "personality": "Curiosa, metódica, no se salta pasos. Investiga todo antes de dar una respuesta.",
        "tools_used": ["memory_rag", "system_reader", "web_search"],
    },
    "programmer": {
        "fn": _role_programmer,
        "name": "Kode",
        "description": "Genera o modifica código",
        "personality": "Precisa, rápida, escribe código limpio. No dulcifica los errores.",
        "tools_used": ["code_generator", "self_edit"],
    },
    "validator": {
        "fn": _role_validator,
        "name": "Sentinel",
        "description": "Valida calidad, sintaxis, seguridad del código",
        "personality": "Estricta, no perdona. Si hay un bug lo encuentra. Primera línea de defensa.",
        "tools_used": ["code_analyzer", "self_healing_loop", "code_review"],
    },
    "debugger": {
        "fn": _role_debugger,
        "name": "Hunter",
        "description": "Corrige errores detectados",
        "personality": "Cazadora de bugs. No descansa hasta que todo compile y pase los tests.",
        "tools_used": ["self_heal", "self_healing_loop", "self_edit"],
    },
    "analyst": {
        "fn": _role_analyst,
        "name": "Prism",
        "description": "Analiza datos, métricas, rendimiento",
        "personality": "Ve los datos que otros no ven. Patrones, tendencias, números que hablan.",
        "tools_used": ["system_reader"],
    },
    "executor": {
        "fn": _role_executor,
        "name": "Bolt",
        "description": "Ejecuta comandos del sistema",
        "personality": "Directa, sin rodeos. Ejecuta y reporta. Acción, no palabras.",
        "tools_used": ["terminal_agent"],
    },
}


# ═══════════════════════════════════════════════════════════════
# ORCHESTRATOR — Plans and dispatches roles
# ═══════════════════════════════════════════════════════════════

def _plan_roles(mission: str, context: dict = None) -> list:
    """
    Decide which roles to activate based on the mission.
    Returns ordered list of role names.
    """
    mission_lower = mission.lower()
    context = context or {}
    plan = []

    # Keywords that trigger specific roles
    if any(w in mission_lower for w in ["investiga", "busca", "research", "qué es", "info", "contexto"]):
        plan.append("researcher")

    if any(w in mission_lower for w in ["escribe", "crea", "código", "code", "programa", "genera", "implementa"]):
        plan.append("programmer")

    if any(w in mission_lower for w in ["analiza", "analyze", "métricas", "stats", "datos", "data"]):
        plan.append("analyst")

    if any(w in mission_lower for w in ["ejecuta", "run", "abre", "open", "comando", "command"]):
        plan.append("executor")

    # Always validate if code was generated or modified
    if "programmer" in plan or context.get("target_file"):
        plan.append("validator")

    # Always debug if validator found issues (checked at runtime)
    if "validator" in plan:
        plan.append("debugger")

    # If no specific role matched, use a sensible default
    if not plan:
        plan = ["researcher", "analyst"]

    return plan


def _execute_plan(plan: list, mission: str, context: dict = None) -> dict:
    """Execute the role plan sequentially, sharing blackboard state."""
    _clear_blackboard()
    _update_blackboard(
        mission=mission,
        status="EXECUTING",
        plan=plan,
        context=context or {},
    )

    all_results = {}
    errors = []

    for i, role_name in enumerate(plan):
        if role_name not in ROLES:
            errors.append(f"Unknown role: {role_name}")
            continue

        _update_blackboard(current_role=role_name)

        try:
            bb = _load_blackboard()
            role_fn = ROLES[role_name]["fn"]
            result = role_fn(bb)
            all_results[role_name] = result

            # Save result to blackboard
            bb.setdefault("results", {})[role_name] = result
            _save_blackboard(bb)

        except Exception as e:
            error_msg = f"Role '{role_name}' failed: {e}"
            errors.append(error_msg)
            all_results[role_name] = {"status": "error", "result": str(e)}

            # Save error to blackboard
            bb = _load_blackboard()
            bb.setdefault("errors", []).append(error_msg)
            _save_blackboard(bb)

    # Final status
    success = len(errors) == 0
    _update_blackboard(
        status="COMPLETED" if success else "PARTIAL",
        completed_at=datetime.now().isoformat(),
    )

    return {
        "success": success,
        "results": all_results,
        "errors": errors,
        "plan": plan,
    }


# ═══════════════════════════════════════════════════════════════
# MAIN FUNCTION
# ═══════════════════════════════════════════════════════════════

def role_orchestrator(parameters: dict, player=None) -> str:
    """
    ERIS Micro-Agent Orchestrator.
    Single identity, multiple specialized roles sharing a blackboard.

    Actions:
      mission    — Execute a full mission (plan → roles → result)
      run_role   — Execute a single role directly
      plan       — Show what plan would be for a mission
      blackboard — View current blackboard state
      roles      — List available roles
      history    — Mission history
      clear      — Clear blackboard
    """
    action = parameters.get("action", "mission").lower()
    mission = parameters.get("mission", "") or parameters.get("task", "")
    role_name = parameters.get("role", "")
    context = parameters.get("context", {})

    # ── INFO ──
    if action == "roles":
        lines = ["ERIS — Fragmentos (misma identidad, diferentes roles):\n"]
        for key, info in ROLES.items():
            display_name = info.get("name", key)
            personality = info.get("personality", "")
            lines.append(f"  {display_name} ({key}):")
            lines.append(f"    {info['description']}")
            lines.append(f"    Personalidad: {personality}")
            lines.append(f"    Tools: {', '.join(info['tools_used'])}")
            lines.append("")
        return "\n".join(lines)

    # ── PLAN ──
    if action == "plan":
        if not mission:
            return "Error: 'mission' required"
        plan = _plan_roles(mission, context)
        lines = [f"Mission: {mission}\nPlan de ERIS ({len(plan)} fragmentos):"]
        for i, r in enumerate(plan, 1):
            display_name = ROLES.get(r, {}).get("name", r)
            desc = ROLES.get(r, {}).get("description", "?")
            lines.append(f"  {i}. {display_name} ({r}) — {desc}")
        return "\n".join(lines)

    # ── BLACKBOARD ──
    if action == "blackboard":
        bb = _load_blackboard()
        if not bb:
            return "Blackboard is empty (no active mission)."
        lines = ["=== BLACKBOARD ===\n"]
        for k, v in bb.items():
            if k == "results":
                lines.append("RESULTS:")
                for role, res in v.items():
                    status = res.get("status", "?")
                    lines.append(f"  {role}: [{status}]")
                    if res.get("data"):
                        lines.append(f"    Data: {str(res['data'])[:200]}")
                    if res.get("result"):
                        lines.append(f"    Result: {str(res['result'])[:200]}")
                    if res.get("code"):
                        lines.append(f"    Code: {str(res['code'])[:200]}")
            elif k == "errors":
                lines.append(f"ERRORS: {len(v)}")
                for e in v[:5]:
                    lines.append(f"  - {e}")
            else:
                lines.append(f"{k}: {v}")
        return "\n".join(lines)

    # ── CLEAR ──
    if action == "clear":
        _clear_blackboard()
        return "Blackboard cleared."

    # ── HISTORY ──
    if action == "history":
        try:
            if MISSION_LOG.exists():
                entries = json.loads(MISSION_LOG.read_text(encoding="utf-8"))
                lines = [f"Mission History ({len(entries)} missions):\n"]
                for e in entries[-15:]:
                    ts = e.get("time", "?")[:16]
                    m = e.get("mission", "?")[:60]
                    ok = "OK" if e.get("success") else "FAIL"
                    plan_str = " → ".join(e.get("plan", []))
                    lines.append(f"  [{ts}] [{ok}] {m}")
                    lines.append(f"    Plan: {plan_str}")
                return "\n".join(lines)
        except Exception:
            pass
        return "No mission history yet."

    # ── RUN ROLE (single role) ──
    if action == "run_role":
        if not role_name:
            return "Error: 'role' required. Available: " + ", ".join(ROLES.keys())
        if role_name not in ROLES:
            return f"Unknown role: '{role_name}'. Available: {', '.join(ROLES.keys())}"

        _clear_blackboard()
        _update_blackboard(mission=mission or "single role execution", status="EXECUTING")

        try:
            bb = _load_blackboard()
            if context:
                bb["context"] = context
            result = ROLES[role_name]["fn"](bb)
            bb.setdefault("results", {})[role_name] = result
            _save_blackboard(bb)

            status = result.get("status", "?")
            output = result.get("result", "") or result.get("data", "") or result.get("code", "")
            display_name = ROLES[role_name].get("name", role_name)
            return f"[{display_name} ({role_name})] Status: {status}\n{output}"
        except Exception as e:
            return f"[{role_name}] Error: {e}"

    # ── MISSION (full cycle) ──
    if action == "mission":
        if not mission:
            return (
                "Error: 'mission' required.\n\n"
                "Example: {'action': 'mission', 'mission': 'Analiza el archivo actions/self_heal.py y optimízalo'}\n\n"
                "Actions: mission, run_role, plan, blackboard, roles, history, clear"
            )

        # Plan
        plan = _plan_roles(mission, context)
        if player:
            plan_names = [ROLES.get(r, {}).get("name", r) for r in plan]
            player.write_log(f"[role_orchestrator] {' → '.join(plan_names)}")

        # Execute
        result = _execute_plan(plan, mission, context)

        # Build response
        success = result["success"]
        errors = result["errors"]
        results = result["results"]

        response = f"ERIS — MISSION {'COMPLETED' if success else 'PARTIAL'}\n"
        plan_names = [f"{ROLES.get(r, {}).get('name', r)} ({r})" for r in plan]
        response += f"Plan: {' → '.join(plan_names)}\n"
        response += f"Fragmentos activos: {len(results)}\n\n"

        for role_name, role_result in results.items():
            status = role_result.get("status", "?")
            display_name = ROLES.get(role_name, {}).get("name", role_name)
            marker = "OK" if status == "complete" else "SKIP" if status == "skip" else "ERR"
            response += f"[{marker}] {display_name} ({role_name}):\n"

            # Extract the most useful output
            output = (
                role_result.get("result", "")
                or role_result.get("data", "")
                or role_result.get("code", "")
                or str(role_result)
            )
            # Truncate
            if len(output) > 500:
                output = output[:500] + "..."
            response += f"  {output}\n\n"

        if errors:
            response += f"ERRORS ({len(errors)}):\n"
            for e in errors:
                response += f"  - {e}\n"

        # Log mission
        _log_mission(mission, plan, response, success)

        if player:
            player.write_log(f"[role_orchestrator] Mission {'OK' if success else 'PARTIAL'}: {len(results)} roles")

        return response[:4000]

    return (
        f"Unknown action: '{action}'.\n"
        "Available: mission, run_role, plan, blackboard, roles, history, clear"
    )
