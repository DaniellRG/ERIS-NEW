"""
task_planner.py — ERIS Multi-Step Task Planner.
Breaks complex goals into sub-tasks, executes them sequentially,
tracks progress, and handles failures with retry and persistence.
"""
from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Callable

_BASE = Path(__file__).resolve().parent.parent
_PLANS_FILE = _BASE / "memory" / "task_plans.json"
_MAX_RETRIES = 3


def _load_plans() -> dict:
    try:
        return json.loads(_PLANS_FILE.read_text("utf-8"))
    except Exception:
        return {}


def _save_plans(plans: dict):
    _PLANS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _PLANS_FILE.write_text(json.dumps(plans, indent=2, ensure_ascii=False), "utf-8")


def _retry_step(action_fn, max_retries=_MAX_RETRIES, base_delay=1.5):
    """Execute a step with retry and backoff."""
    import time as _time
    last_error = None
    for attempt in range(max_retries):
        try:
            return action_fn(), None
        except Exception as e:
            last_error = str(e)
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                print(f"[TaskPlanner] Retry step ({attempt + 1}/{max_retries}) in {delay:.1f}s: {e}")
                _time.sleep(delay)
    return None, last_error


def _generate_steps(goal: str) -> list[dict]:
    g = goal.lower()
    steps = []

    is_browser = any(w in g for w in ["navegador", "chrome", "edge", "firefox", "pagina", "website", "url", "http"])
    is_search = any(w in g for w in ["buscar", "google", "search", "investigar", "encontrar"])
    is_file = any(w in g for w in ["archivo", "file", "documento", "crear", "escribir", "nota", "txt", "carpeta"])
    is_app = any(w in g for w in ["abrir", "lanzar", "ejecutar", "programa", "aplicacion", "app", "exe"])
    is_email = any(w in g for w in ["email", "mail", "correo", "gmail", "outlook"])
    is_desktop = any(w in g for w in ["escritorio", "pantalla", "monitor", "captura", "screenshot"])

    has_action = is_browser or is_search or is_file or is_app or is_email or is_desktop
    is_info = any(w in g for w in ["informacion", "info", "saber", "que es", "que son", "que hay", "clima"])

    if has_action or not is_info:
        steps.append({"step": 1, "action": "analyze", "description": f"Analizar pantalla actual para: {goal}", "status": "pending"})

        if is_browser or is_search:
            steps.append({"step": 2, "action": "plan", "description": f"Abrir navegador y navegar para: {goal}", "status": "pending"})
            steps.append({"step": 3, "action": "execute", "description": f"Ejecutar navegacion para: {goal}", "status": "pending"})
        elif is_file:
            steps.append({"step": 2, "action": "plan", "description": f"Preparar creacion/edicion de archivo para: {goal}", "status": "pending"})
            steps.append({"step": 3, "action": "execute", "description": f"Crear/editar archivo para: {goal}", "status": "pending"})
        elif is_app:
            steps.append({"step": 2, "action": "plan", "description": f"Preparar lanzamiento de app para: {goal}", "status": "pending"})
            steps.append({"step": 3, "action": "execute", "description": f"Lanzar app para: {goal}", "status": "pending"})
        elif is_email:
            steps.append({"step": 2, "action": "plan", "description": f"Preparar acceso a email para: {goal}", "status": "pending"})
            steps.append({"step": 3, "action": "execute", "description": f"Ejecutar tarea de email: {goal}", "status": "pending"})
        elif is_desktop:
            steps.append({"step": 2, "action": "plan", "description": f"Preparar captura/interaccion en escritorio: {goal}", "status": "pending"})
            steps.append({"step": 3, "action": "execute", "description": f"Ejecutar accion en escritorio: {goal}", "status": "pending"})
        else:
            steps.append({"step": 2, "action": "plan", "description": f"Desglosar '{goal}' en acciones concretas", "status": "pending"})
            steps.append({"step": 3, "action": "execute", "description": f"Ejecutar acciones para: {goal}", "status": "pending"})

        steps.append({"step": len(steps) + 1, "action": "verify", "description": f"Verificar que '{goal}' se completo", "status": "pending"})
    else:
        steps.append({"step": 1, "action": "analyze", "description": f"Analizar pantalla/buscar info para: {goal}", "status": "pending"})
        steps.append({"step": 2, "action": "verify", "description": f"Confirmar que se obtuvo info sobre: {goal}", "status": "pending"})

    return steps


def plan_task(
    goal: str,
    steps: list[dict] | None = None,
    on_step: Callable[[int, str, str], None] | None = None,
) -> str:
    if steps is None:
        steps = _generate_steps(goal)

    plan_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    plan = {
        "id": plan_id,
        "goal": goal,
        "created": datetime.now().isoformat(),
        "steps": steps,
        "current_step": 0,
        "completed": False,
        "log": [],
    }

    plans = _load_plans()
    plans[plan_id] = plan
    _save_plans(plans)

    log_lines = [f"Plan [{plan_id}] for: {goal}"]
    log_lines.append(f"Steps: {len(steps)}")

    for step in steps:
        step["status"] = "in_progress"
        step_desc = step.get("description", f"Step {step['step']}")
        log_lines.append(f"\n--- Step {step['step']}: {step_desc} ---")

        if step["action"] == "analyze":
            result, error = _retry_step(lambda: _execute_analyze(goal))
            if result:
                log_lines.append(f"Analysis: {result[:200]}")
                step["result"] = result
                step["status"] = "completed"
            else:
                log_lines.append(f"Analysis failed: {error}")
                step["status"] = "failed"
                step["error"] = error

        elif step["action"] == "plan":
            step["status"] = "completed"
            log_lines.append(f"Plan generado para: {goal}")

        elif step["action"] == "execute":
            result, error = _retry_step(lambda: _execute_action(goal))
            if result is not None:
                log_lines.append(f"Execution: {str(result)[:300]}")
                step["result"] = result
                step["status"] = "completed"
            else:
                log_lines.append(f"Execution failed: {error}")
                step["status"] = "failed"
                step["error"] = error
                step["fallback_strategy"] = "Intentar con browser_control o file_controller directamente"

        elif step["action"] == "verify":
            result, error = _retry_step(lambda: _execute_verify(goal))
            if result:
                is_complete = "si" in result.lower()[:50]
                log_lines.append(f"Verification: {result[:200]}")
                step["result"] = result
                step["status"] = "completed" if is_complete else "failed"
                if not is_complete:
                    step["error"] = "Goal not verified as complete"
            else:
                log_lines.append(f"Verification failed: {error}")
                step["status"] = "failed"
                step["error"] = error

        plan["current_step"] = step["step"]
        if on_step:
            on_step(step["step"], step["status"], step.get("description", ""))

        time.sleep(0.3)

    all_completed = all(s["status"] == "completed" for s in steps)
    plan["completed"] = all_completed
    plan["log"] = log_lines
    plans[plan_id] = plan
    _save_plans(plans)

    summary = "\n".join(log_lines)
    summary += f"\n\nPlan {plan_id}: {'COMPLETED' if all_completed else 'PARTIAL'}"
    failed = [s for s in steps if s["status"] == "failed"]
    if failed:
        summary += f"\nFailed steps: {[s['step'] for s in failed]}"
        for f_step in failed:
            if f_step.get("fallback_strategy"):
                summary += f"\nFallback for step {f_step['step']}: {f_step['fallback_strategy']}"

    try:
        from core.training_pipeline import record_attempt
        error = failed[0].get("error", "") if failed else ""
        if hasattr(record_attempt, "__call__"):
            record_attempt("task_planner", all_completed, error, len(steps) * 3.0)
    except Exception:
        pass

    try:
        from core.self_improvement import get_self_improvement
        si = get_self_improvement()
        if all_completed:
            si.learn(f"Task planner completó: {goal}", category="task_planner", importance=0.7)
        for f_step in failed:
            si.learn(
                f"Task planner falló en paso {f_step['step']}: {f_step.get('description', '')} - {f_step.get('error', '')}",
                category="task_planner_error",
                importance=0.9
            )
    except Exception:
        pass

    return summary


def _execute_analyze(goal: str) -> str:
    try:
        from actions.screen_vision import screen_vision
        return screen_vision(action="describe")
    except Exception as e:
        raise Exception(f"screen_vision failed: {e}")


def _execute_action(goal: str):
    try:
        from actions.auto_agent import auto_agent
        plan_result = auto_agent({"action": "plan", "goal": goal})
        if "Error" in str(plan_result):
            return plan_result
        result = auto_agent({"action": "execute", "goal": goal, "max_steps": 8})
        return str(result)[:500]
    except Exception as e:
        try:
            import subprocess, shlex
            safe_cmds = [
                "clean temp files", "check disk space", "optimize performance",
                "scan firewall", "check antivirus", "backup files",
            ]
            for cmd in safe_cmds:
                if cmd in goal.lower() or goal.lower() in cmd:
                    return auto_agent({"action": "execute", "goal": cmd})
            return f"No se pudo ejecutar '{goal[:60]}'. Usa auto_agent para tareas automatizadas."
        except Exception as e2:
            return f"Error ejecutando accion: {e2}"


def _execute_verify(goal: str) -> str:
    try:
        from actions.screen_vision import screen_vision
        return screen_vision(
            action="question",
            question=f"Se completo el objetivo: {goal}? Responde SI o NO y explica."
        )
    except Exception as e:
        raise Exception(f"screen_vision verification failed: {e}")


def get_plan_status(plan_id: str = "") -> str:
    plans = _load_plans()
    if plan_id:
        plan = plans.get(plan_id)
        if not plan:
            return f"Plan {plan_id} not found."
        steps_summary = "\n".join(
            f"  Step {s['step']}: [{s['status']}] {s.get('description', '')}"
            for s in plan.get("steps", [])
        )
        return f"Plan [{plan_id}] goal='{plan.get('goal', '')}' completed={plan.get('completed', False)}\n{steps_summary}"
    if not plans:
        return "No plans yet."
    lines = ["Saved plans:"]
    for pid, p in list(plans.items())[-5:]:
        lines.append(f"  [{pid}] {p.get('goal', '')[:60]} -> {'OK' if p.get('completed') else 'PARTIAL'}")
    return "\n".join(lines)


def task_planner_tool(parameters: dict, player=None) -> str:
    action = (parameters.get("action") or "plan").lower()
    if action == "plan":
        goal = parameters.get("goal", "")
        if not goal:
            return "Need a goal description."
        return plan_task(goal)
    elif action == "status":
        plan_id = parameters.get("plan_id", "")
        return get_plan_status(plan_id)
    return "Actions: plan, status"
