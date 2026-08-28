"""
session_replay_debugger.py — Debugger de sesiones anteriores.

Permite inspeccionar paso a paso qué hizo el agente en sesiones pasadas:
  - Ver qué tools ejecutó
  - Ver qué contexto usó
  - Identificar dónde falló
  - Comparar con la sesión actual

Diferente a conversation_replay.py: esto es para debugging/diagnóstico,
no para repetir la conversación.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from collections import defaultdict

_BASE = Path(__file__).resolve().parent.parent
_SESSIONS_DIR = _BASE / "data" / "sessions"
_DEBUG_LOG_DIR = _BASE / "data" / "debug_logs"


def save_debug_log(
    session_id: str,
    step: int,
    action: str,
    tool_name: str = "",
    tool_args: dict = None,
    tool_result: str = "",
    context_tokens: int = 0,
    timestamp: float = None,
):
    """Guarda un paso de debug log."""
    _DEBUG_LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = _DEBUG_LOG_DIR / (session_id + ".jsonl")

    entry = {
        "step": step,
        "action": action,
        "tool_name": tool_name,
        "tool_args": tool_args or {},
        "tool_result": tool_result[:500] if tool_result else "",
        "context_tokens": context_tokens,
        "timestamp": timestamp or time.time(),
    }

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def load_debug_log(session_id: str) -> list[dict]:
    """Carga el debug log de una sesión."""
    log_file = _DEBUG_LOG_DIR / (session_id + ".jsonl")
    if not log_file.exists():
        return []

    entries = []
    for line in log_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                entries.append(json.loads(line))
            except Exception:
                continue
    return entries


def analyze_session(session_id: str) -> dict:
    """Analiza una sesión completa para debugging.

    Returns:
        dict con: steps, tools_used, errors, bottlenecks, suggestions
    """
    entries = load_debug_log(session_id)
    if not entries:
        return {"error": "No hay logs para esta sesión"}

    steps = len(entries)
    tools_used = defaultdict(int)
    errors = []
    slow_steps = []
    token_usage = []

    for entry in entries:
        tool = entry.get("tool_name", "")
        if tool:
            tools_used[tool] += 1

        # Detectar errores
        result = entry.get("tool_result", "")
        if "error" in result.lower() or "failed" in result.lower() or "exception" in result.lower():
            errors.append({
                "step": entry.get("step", 0),
                "tool": tool,
                "error": result[:200],
            })

        # Detectar pasos lentos (>5s)
        if entry.get("timestamp", 0) > 0 and entry.get("step", 0) > 1:
            prev = entries[entry["step"] - 2] if entry["step"] > 1 else None
            if prev:
                dt = entry.get("timestamp", 0) - prev.get("timestamp", 0)
                if dt > 5:
                    slow_steps.append({
                        "step": entry.get("step", 0),
                        "duration": round(dt, 1),
                        "tool": tool,
                    })

        tokens = entry.get("context_tokens", 0)
        if tokens > 0:
            token_usage.append(tokens)

    # Sugerencias
    suggestions = []
    if errors:
        suggestions.append("Hay %d errores en la sesión — revisar patrones" % len(errors))
    if slow_steps:
        suggestions.append("Hay %d pasos lentos — considerar optimizar tools" % len(slow_steps))
    if len(tools_used) > 10:
        suggestions.append("Se usaron muchas tools diferentes — posible over-engineering")

    max_tokens = max(token_usage) if token_usage else 0
    if max_tokens > 8000:
        suggestions.append("Uso máximo de tokens: %d — considerar comprimir contexto" % max_tokens)

    return {
        "session_id": session_id,
        "total_steps": steps,
        "tools_used": dict(tools_used),
        "errors": errors,
        "slow_steps": slow_steps,
        "max_context_tokens": max_tokens,
        "suggestions": suggestions,
    }


def compare_sessions(session1: str, session2: str) -> dict:
    """Compara dos sesiones para ver diferencias."""
    a = analyze_session(session1)
    b = analyze_session(session2)

    tools_a = set(a.get("tools_used", {}).keys())
    tools_b = set(b.get("tools_used", {}).keys())

    return {
        "session1": session1,
        "session2": session2,
        "steps_diff": a.get("total_steps", 0) - b.get("total_steps", 0),
        "tools_only_in_1": list(tools_a - tools_b),
        "tools_only_in_2": list(tools_b - tools_a),
        "errors_in_1": len(a.get("errors", [])),
        "errors_in_2": len(b.get("errors", [])),
    }


def format_session_report(session_id: str) -> str:
    """Genera un reporte legible de una sesión."""
    analysis = analyze_session(session_id)
    if "error" in analysis:
        return "Error: %s" % analysis["error"]

    lines = [
        "Reporte de sesión: %s" % session_id,
        "Pasos: %d" % analysis["total_steps"],
        "Tools usadas: %s" % ", ".join(analysis.get("tools_used", {}).keys()),
        "Errores: %d" % len(analysis.get("errors", [])),
        "Tokens máximos: %d" % analysis.get("max_context_tokens", 0),
        "",
    ]

    if analysis.get("errors"):
        lines.append("Errores:")
        for err in analysis["errors"][:5]:
            lines.append("  Paso %d [%s]: %s" % (err["step"], err["tool"], err["error"][:100]))
        lines.append("")

    if analysis.get("suggestions"):
        lines.append("Sugerencias:")
        for sug in analysis["suggestions"]:
            lines.append("  - %s" % sug)

    return "\n".join(lines)
