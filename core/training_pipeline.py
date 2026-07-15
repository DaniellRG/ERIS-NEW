"""
training_pipeline.py — Entrenamiento continuo de ERIS.
Auto-evaluacion, deteccion de fallos, correccion y mejora progresiva.
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_LOG_DIR = _BASE / "memory"
_LOG_FILE = _LOG_DIR / "training_log.json"
_SCORE_FILE = _LOG_DIR / "capability_scores.json"
_PROMPT_FILE = _BASE / "core" / "prompt.txt"
_LESSONS_FILE = _LOG_DIR / "lessons_learned.json"

_CAPABILITIES = {
    "screen_vision": {"score": 0.0, "attempts": 0, "successes": 0, "failures": {}, "last_failure": "", "errors": []},
    "vision_guardian": {"score": 0.0, "attempts": 0, "successes": 0, "failures": {}, "last_failure": "", "errors": []},
    "visual_click": {"score": 0.0, "attempts": 0, "successes": 0, "failures": {}, "last_failure": "", "errors": []},
    "image_analyzer": {"score": 0.0, "attempts": 0, "successes": 0, "failures": {}, "last_failure": "", "errors": []},
    "human_mouse": {"score": 0.0, "attempts": 0, "successes": 0, "failures": {}, "last_failure": "", "errors": []},
    "mouse_control": {"score": 0.0, "attempts": 0, "successes": 0, "failures": {}, "last_failure": "", "errors": []},
    "screen_processor": {"score": 0.0, "attempts": 0, "successes": 0, "failures": {}, "last_failure": "", "errors": []},
    "ollama_vision": {"score": 0.0, "attempts": 0, "successes": 0, "failures": {}, "last_failure": "", "errors": []},
    "emotional_state": {"score": 0.0, "attempts": 0, "successes": 0, "failures": {}, "last_failure": "", "errors": []},
    "inner_monologue": {"score": 0.0, "attempts": 0, "successes": 0, "failures": {}, "last_failure": "", "errors": []},
    "computer_use_agent": {"score": 0.0, "attempts": 0, "successes": 0, "failures": {}, "last_failure": "", "errors": []},
    "task_planner": {"score": 0.0, "attempts": 0, "successes": 0, "failures": {}, "last_failure": "", "errors": []},
}


def _load_scores() -> dict:
    try:
        return json.loads(_SCORE_FILE.read_text("utf-8"))
    except Exception:
        return _CAPABILITIES.copy()


def _save_scores(scores: dict):
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    _SCORE_FILE.write_text(json.dumps(scores, ensure_ascii=False, indent=2), "utf-8")


def _load_log() -> list:
    try:
        return json.loads(_LOG_FILE.read_text("utf-8"))
    except Exception:
        return []


def _save_log(log: list):
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    _LOG_FILE.write_text(json.dumps(log, ensure_ascii=False, indent=2), "utf-8")


def _load_lessons() -> list:
    try:
        return json.loads(_LESSONS_FILE.read_text("utf-8"))
    except Exception:
        return []


def _save_lessons(lessons: list):
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    _LESSONS_FILE.write_text(json.dumps(lessons, ensure_ascii=False, indent=2), "utf-8")


def record_attempt(module: str, success: bool, error: str = "", duration: float = 0.0):
    scores = _load_scores()
    if module not in scores:
        scores[module] = {"score": 0.0, "attempts": 0, "successes": 0, "failures": {}, "last_failure": "", "errors": []}

    scores[module]["attempts"] += 1
    if success:
        scores[module]["successes"] += 1
    else:
        err_type = error.split(":")[0] if error else "unknown"
        scores[module]["failures"][err_type] = scores[module]["failures"].get(err_type, 0) + 1
        scores[module]["last_failure"] = error
        if error:
            scores[module]["errors"].append({"error": error, "time": datetime.now().isoformat()})
            if len(scores[module]["errors"]) > 100:
                scores[module]["errors"] = scores[module]["errors"][-100:]

    attempts = scores[module]["attempts"]
    successes = scores[module]["successes"]
    scores[module]["score"] = successes / attempts if attempts > 0 else 0.0

    _save_scores(scores)

    log_entry = {
        "time": datetime.now().isoformat(),
        "module": module,
        "success": success,
        "error": error,
        "duration": round(duration, 2),
    }
    log = _load_log()
    log.append(log_entry)
    if len(log) > 1000:
        log = log[-1000:]
    _save_log(log)


def get_module_score(module: str) -> float:
    scores = _load_scores()
    return scores.get(module, {}).get("score", 0.0)


def get_best_vision_module() -> str:
    scores = _load_scores()
    vision_modules = ["screen_vision", "vision_guardian", "ollama_vision", "image_analyzer"]
    best = "screen_vision"
    best_score = -1.0
    for m in vision_modules:
        s = scores.get(m, {}).get("score", 0.0)
        if s > best_score and scores.get(m, {}).get("attempts", 0) > 2:
            best = m
            best_score = s
    return best


def get_vision_summary() -> str:
    scores = _load_scores()
    lines = ["[VISION CAPABILITY STATUS]"]
    for mod in ["screen_vision", "vision_guardian", "visual_click", "image_analyzer", "ollama_vision"]:
        data = scores.get(mod, {})
        attempts = data.get("attempts", 0)
        if attempts == 0:
            continue
        score = data.get("score", 0.0)
        last_err = data.get("last_failure", "")
        status = "OK" if score > 0.7 else "WARN" if score > 0.3 else "FAIL"
        lines.append(f"  {mod}: score={score:.0%} attempts={attempts} [{status}]")
        if last_err:
            lines.append(f"    Last error: {last_err[:80]}")
    return "\n".join(lines)


def check_and_fix_vision_prompt() -> str:
    if not _PROMPT_FILE.exists():
        return "No prompt.txt found."
    prompt = _PROMPT_FILE.read_text("utf-8")
    if "OLLAMA" not in prompt and "ollama" not in prompt:
        return "WARNING: Prompt doesn't mention Ollama fallback."
    if "fallback" not in prompt.lower() and "alternativa" not in prompt.lower():
        return "WARNING: Prompt has no fallback instructions."
    return "Prompt looks healthy."


def auto_heal():
    scores = _load_scores()
    fixes = []
    for mod, data in scores.items():
        if data.get("attempts", 0) < 3:
            continue
        score = data.get("score", 0.0)
        failures = data.get("failures", {})
        if score < 0.3:
            common = sorted(failures.items(), key=lambda x: -x[1])
            top_error = common[0][0] if common else "unknown"
            fixes.append(f"Module '{mod}' failing (score={score:.0%}). "
                        f"Most common error: {top_error}.")
    if fixes:
        log = _load_log()
        log.append({
            "time": datetime.now().isoformat(),
            "module": "auto_heal",
            "success": True,
            "error": "; ".join(fixes),
            "duration": 0.0,
        })
        _save_log(log)
    return fixes


def evaluate_tool_usage(tool_name: str, parameters: dict, result: str, duration: float):
    success = not result.startswith("Error") and not result.startswith("ERROR")
    error = result if not success else ""
    record_attempt(tool_name, success, error, duration)
    if not success:
        hints = {
            "Error.*No.*encont": f"'{tool_name}' could not find target. Try more specific description.",
            "quota": f"'{tool_name}' hit API quota. Use Ollama fallback.",
            "429": f"'{tool_name}' rate limited. Ollama fallback activated.",
            "timeout": f"'{tool_name}' timed out. Target may be too complex.",
        }
        for hint_key, hint_msg in hints.items():
            import re
            if re.search(hint_key, error, re.IGNORECASE):
                return hint_msg
    return ""


def learn_from_failure(module: str, error: str, solution: str):
    """Record a lesson learned for future reference."""
    lessons = _load_lessons()
    lesson = {
        "time": datetime.now().isoformat(),
        "module": module,
        "error": error[:200],
        "solution": solution[:500],
    }
    # Avoid duplicates
    for l in lessons:
        if l["module"] == module and l["error"][:100] == lesson["error"][:100]:
            l["time"] = lesson["time"]
            l["count"] = l.get("count", 1) + 1
            _save_lessons(lessons)
            return
    lesson["count"] = 1
    lessons.append(lesson)
    if len(lessons) > 50:
        lessons = lessons[-50:]
    _save_lessons(lessons)


def get_training_status() -> dict:
    """Get full training status for the AI to use."""
    scores = _load_scores()
    lessons = _load_lessons()
    total_attempts = sum(d.get("attempts", 0) for d in scores.values())
    total_successes = sum(d.get("successes", 0) for d in scores.values())
    overall_score = total_successes / total_attempts if total_attempts > 0 else 0.0

    failing = [m for m, d in scores.items()
               if d.get("attempts", 0) >= 3 and d.get("score", 0.0) < 0.5]

    return {
        "overall_score": round(overall_score, 2),
        "total_attempts": total_attempts,
        "total_successes": total_successes,
        "total_failures": total_attempts - total_successes,
        "modules_tracked": len(scores),
        "failing_modules": failing,
        "lessons_learned": len(lessons),
        "recent_lessons": lessons[-5:] if lessons else [],
    }


def _try_module(module: str) -> tuple[bool, str, float]:
    """Try to run a quick test of a module. Returns (success, result, duration)."""
    t0 = time.perf_counter()
    try:
        if module == "screen_vision":
            from actions.screen_vision import screen_vision
            ok = callable(screen_vision)
            return (ok, "Module available" if ok else "Not callable", time.perf_counter() - t0)
        elif module == "ollama_vision":
            from actions.ollama_vision import analyze_image_ollama
            ok = callable(analyze_image_ollama)
            return (ok, "Module available" if ok else "Not callable", time.perf_counter() - t0)
        elif module == "image_analyzer":
            from actions.image_analyzer import image_analyzer
            ok = callable(image_analyzer)
            return (ok, "Module available" if ok else "Not callable", time.perf_counter() - t0)
        elif module == "visual_click":
            return (True, "Visual click requires user context, skipping auto-check", 0.0)
        elif module == "vision_guardian":
            return (True, "Vision guardian runs in background, skipping auto-check", 0.0)
        elif module == "human_mouse":
            return (True, "Human mouse requires user interaction, skipping", 0.0)
        elif module == "mouse_control":
            return (True, "Mouse control requires screen context, skipping", 0.0)
        elif module == "screen_processor":
            from actions.screen_processor import screen_process
            ok = callable(screen_process)
            return (ok, "Module available" if ok else "Not callable", time.perf_counter() - t0)
        elif module == "emotional_state":
            from core.emotional_state import get_emotional_state
            state = get_emotional_state()
            ok = bool(state and "happiness" in state)
            return (ok, f"{len(state)} dims" if ok else "No state", time.perf_counter() - t0)
        elif module == "inner_monologue":
            from core.inner_monologue import generate_inner_monologue
            thought = generate_inner_monologue("health check")
            ok = bool(thought and len(thought) > 10)
            return (ok, thought[:50] if ok else "Empty", time.perf_counter() - t0)
        elif module == "computer_use_agent":
            return (True, "Computer-use agent requires screen, skipping auto-check", 0.0)
        elif module == "task_planner":
            from core.task_planner import _generate_steps, task_planner_tool
            steps = _generate_steps("test goal")
            ok = bool(steps and len(steps) >= 2)
            r = task_planner_tool({"action": "status"})
            return (ok, f"{len(steps)} steps | {r[:30]}" if ok else "No steps", time.perf_counter() - t0)
        return (True, f"No auto-check for {module}", 0.0)
    except Exception as e:
        return (False, str(e), time.perf_counter() - t0)


def run_health_check() -> str:
    """Run a health check on all modules and return a report."""
    scores = _load_scores()
    lines = []
    lines.append("=== TRAINING HEALTH CHECK ===")
    for mod in sorted(_CAPABILITIES.keys()):
        success, result, duration = _try_module(mod)
        record_attempt(mod, success, result if not success else "", duration)
        score = get_module_score(mod)
        status = "OK" if success else "FAIL"
        if not success and scores.get(mod, {}).get("attempts", 0) > 0:
            prev_score = scores.get(mod, {}).get("score", 1.0)
            if prev_score > 0.5:
                status = "DEGRADED"
        lines.append(f"  {mod}: [{status}] score={score:.0%} ({duration:.1f}s)")
        if not success:
            lines.append(f"    Error: {result[:100]}")
    overall = get_training_status()
    lines.append(f"Overall: {overall['overall_score']:.0%} ({overall['total_attempts']} attempts, {overall['total_failures']} failures)")
    fixes = auto_heal()
    if fixes:
        lines.append("Auto-heal applied:")
        for f in fixes:
            lines.append(f"  - {f}")
    return "\n".join(lines)


def evaluate_session(tool_calls: list[dict], duration_seconds: float) -> str:
    """Evaluate a full session's tool usage and return report."""
    lines = ["=== SESSION EVALUATION ==="]
    lines.append(f"Session duration: {duration_seconds:.0f}s")
    module_counts = {}
    for tc in tool_calls:
        mod = tc.get("name", "unknown")
        module_counts[mod] = module_counts.get(mod, 0) + 1
    if module_counts:
        lines.append("Tool usage:")
        for mod, count in sorted(module_counts.items(), key=lambda x: -x[1]):
            lines.append(f"  {mod}: {count}x")
    scores = _load_scores()
    failing = [m for m, d in scores.items()
               if d.get("attempts", 0) >= 3 and d.get("score", 0.0) < 0.5]
    if failing:
        lines.append(f"Failing modules: {', '.join(failing)}")
        for m in failing:
            data = scores.get(m, {})
            errs = data.get("failures", {})
            if errs:
                top = sorted(errs.items(), key=lambda x: -x[1])[0]
                lines.append(f"  {m}: most common error: {top[0]} (x{top[1]})")
    streak = 0
    log = _load_log()
    for entry in reversed(log[-20:]):
        if entry.get("success"):
            streak += 1
        else:
            break
    lines.append(f"Success streak: {streak}")
    return "\n".join(lines)


def training_pipeline_tool(parameters: dict) -> str:
    """Tool interface for ERIS to query training status."""
    action = (parameters.get("action") or "status").lower()
    if action == "status":
        status = get_training_status()
        lines = [f"Training Status: {status['overall_score']:.0%} overall score"]
        lines.append(f"  Attempts: {status['total_attempts']}, Successes: {status['total_successes']}, Failures: {status['total_failures']}")
        lines.append(f"  Modules tracked: {status['modules_tracked']}")
        if status['failing_modules']:
            lines.append(f"  Failing modules: {', '.join(status['failing_modules'])}")
        if status['recent_lessons']:
            lines.append(f"  Recent lessons: {status['lessons_learned']} total")
            for l in status['recent_lessons'][-3:]:
                lines.append(f"    - [{l['module']}] {l['solution'][:80]}...")
        return "\n".join(lines)
    elif action == "vision":
        return get_vision_summary()
    elif action == "prompt_check":
        return check_and_fix_vision_prompt()
    elif action == "heal":
        fixes = auto_heal()
        return "Auto-heal complete." + (f" Issues: {'; '.join(fixes)}" if fixes else " No issues found.")
    elif action == "learn":
        module = parameters.get("module", "")
        error = parameters.get("error", "")
        solution = parameters.get("solution", "")
        if module and solution:
            learn_from_failure(module, error or "success", solution)
            return f"Lesson recorded for '{module}'."
        return "Need: module, solution parameters."
    elif action == "lessons":
        lessons = _load_lessons()
        if not lessons:
            return "No lessons learned yet."
        lines = ["Lessons Learned:"]
        for l in lessons[-10:]:
            lines.append(f"  - [{l['module']}] (x{l.get('count', 1)}) {l['solution'][:100]}...")
        return "\n".join(lines)
    elif action == "check":
        return run_health_check()
    elif action == "session_eval":
        tool_calls = parameters.get("tool_calls", [])
        duration = parameters.get("duration", 0)
        return evaluate_session(tool_calls, duration)
    return f"Unknown action '{action}'. Options: status, vision, prompt_check, heal, learn, lessons, check, session_eval"
