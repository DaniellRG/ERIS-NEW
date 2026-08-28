"""
core/agi_tools.py — Fábrica AGI funcional de ERIS.

Las herramientas `agi_*` le permiten a ERIS auto-mejorarse:
  - agi_memory:      almacenar/recuperar/consolidar memoria semántica
  - agi_reasoning:   razonamiento paso a paso, verificación, contra-factual
  - agi_world_model: estado del mundo (ERIS + sistema) y observaciones
  - agi_self_improve: escanear problemas, sugerir y marcar mejoras aplicadas
  - agi_agent:       delegar metas a agentes multi-paso (auto_agent)

Cada función recibe (parameters: dict, player=None) según el contrato del
ToolDispatcher y devuelve un str legible.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_MEMORY_DIR = _BASE / "memory"
_DATA_DIR = _BASE / "data"
_WORLD_MODEL_FILE = _MEMORY_DIR / "world_model.json"


def _load_json(path, default=None):
    try:
        if path.exists():
            return json.loads(path.read_text("utf-8"))
    except Exception:
        pass
    return default if default is not None else []


def _save_json(path, data):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), "utf-8")
    except Exception:
        pass


# ── agi_memory ────────────────────────────────────────────────────────────────

def agi_memory(parameters: dict, player=None) -> str:
    """Memoria semántica/episódica: store, recall, consolidate, status."""
    from core.semantic_memory import get_memory_system
    ms = get_memory_system()
    action = parameters.get("action", "status").lower()

    if action == "store":
        text = parameters.get("text", "").strip()
        if not text:
            return "agi_memory store necesita el parámetro 'text'."
        ms.remember(text)
        return f"Memoria almacenada: {text[:150]}"

    if action == "recall":
        query = parameters.get("query", "").strip()
        if not query:
            return "agi_memory recall necesita el parámetro 'query'."
        result = ms.recall(query)
        lines = [f"Recuerdo para: {query}"]
        for channel in ("episodic", "semantic", "working", "graph_neighbors"):
            data = result.get(channel) or []
            if isinstance(data, list) and data:
                for item in data[:3]:
                    if isinstance(item, dict):
                        text = item.get("event") or item.get("fact") or item.get("subject") or str(item)[:100]
                    else:
                        text = str(item)[:100]
                    lines.append(f"  [{channel}] {text[:120]}")
        if len(lines) == 1:
            lines.append("  Sin resultados relevantes.")
        return "\n".join(lines)

    if action == "consolidate":
        ms.consolidate()
        return "Memoria consolidada (working → largo plazo)."

    st = ms.get_status()
    return "Estado de memoria: " + ", ".join(f"{k}={v}" for k, v in st.items())


# ── agi_reasoning ─────────────────────────────────────────────────────────────

def agi_reasoning(parameters: dict, player=None) -> str:
    """Razonamiento: reason, verify, what_if, status."""
    from core.reasoning_engine import get_reasoning_engine
    eng = get_reasoning_engine()
    action = parameters.get("action", "status").lower()

    if action == "reason":
        question = parameters.get("question", "").strip()
        if not question:
            return "agi_reasoning reason necesita el parámetro 'question'."
        context = parameters.get("context") or None
        result = eng.reason(question, context)
        cot = result.get("chain_of_thought") or {}
        steps = cot.get("steps", []) if isinstance(cot, dict) else []
        lines = [f"Razonamiento para: {question}"]
        for step in steps[:8]:
            lines.append(f"  → {step.get('content', '')[:150]}")
        conclusion = cot.get("conclusion") if isinstance(cot, dict) else None
        if conclusion:
            lines.append(f"  Conclusión: {conclusion[:200]}")
        verif = result.get("verification") or {}
        conf = verif.get("confidence") if isinstance(verif, dict) else None
        if conf is not None:
            lines.append(f"  Confianza de verificación: {conf:.0%}")
        return "\n".join(lines)

    if action == "verify":
        claim = parameters.get("claim", "").strip()
        if not claim:
            return "agi_reasoning verify necesita el parámetro 'claim'."
        verif = eng.verify_claim(claim)
        conf = verif.get("confidence", 0.0) if isinstance(verif, dict) else 0.0
        summary = verif.get("summary", "") if isinstance(verif, dict) else ""
        issues = verif.get("issues", []) if isinstance(verif, dict) else []
        lines = [f"Verificación: {claim}", f"  Confianza: {conf:.0%}"]
        if summary:
            lines.append(f"  Resumen: {summary[:200]}")
        if issues:
            lines.append(f"  Observaciones: {str(issues)[:200]}")
        return "\n".join(lines)

    if action == "what_if":
        premise = parameters.get("premise", "").strip()
        question = parameters.get("question", "").strip()
        if not premise or not question:
            return "agi_reasoning what_if necesita 'premise' y 'question'."
        result = eng.what_if(premise, question)
        return json.dumps(result, ensure_ascii=False, default=str)[:800]

    st = eng.get_status()
    return "Estado del motor de razonamiento: " + ", ".join(f"{k}={v}" for k, v in st.items())


# ── agi_world_model ───────────────────────────────────────────────────────────

def _mobile_up() -> bool:
    try:
        import socket
        with socket.create_connection(("127.0.0.1", 8765), timeout=1.0):
            return True
    except Exception:
        return False


def _collect_world_state() -> dict:
    state = {
        "timestamp": time.time(),
        "mobile_port": _mobile_up(),
        "pending_tasks": len(_load_json(_DATA_DIR / "pending_tasks.json", [])),
        "retry_queue": len(_load_json(_DATA_DIR / "retry_queue.json", [])),
        "world_model_history": len(_load_json(_WORLD_MODEL_FILE, [])),
    }
    try:
        from core.semantic_memory import get_memory_system
        state["memory"] = get_memory_system().get_status()
    except Exception:
        pass
    try:
        from core.self_improvement import get_self_improvement
        state["self_improvement"] = get_self_improvement().get_status()
    except Exception:
        pass
    return state


def agi_world_model(parameters: dict, player=None) -> str:
    """Modelo del mundo: status, snapshot, note (observación)."""
    action = parameters.get("action", "status").lower()

    if action == "note":
        observation = parameters.get("observation", "").strip()
        if not observation:
            return "agi_world_model note necesita el parámetro 'observation'."
        history = _load_json(_WORLD_MODEL_FILE, [])
        history.append({
            "type": "observation",
            "observation": observation[:500],
            "timestamp": time.time(),
        })
        history = history[-200:]
        _save_json(_WORLD_MODEL_FILE, history)
        return f"Observación registrada en el modelo del mundo: {observation[:150]}"

    state = _collect_world_state()
    if action == "snapshot":
        history = _load_json(_WORLD_MODEL_FILE, [])
        history.append({
            "type": "snapshot",
            "state": state,
            "timestamp": time.time(),
        })
        history = history[-200:]
        _save_json(_WORLD_MODEL_FILE, history)
        return "Snapshot guardado en memory/world_model.json. " + _format_state(state)

    return "Estado del mundo:\n" + _format_state(state)


def _format_state(state: dict) -> str:
    lines = []
    lines.append(f"  Puerto mobile: {'activo' if state.get('mobile_port') else 'caído'}")
    lines.append(f"  Tareas pendientes: {state.get('pending_tasks', 0)} | Cola reintentos: {state.get('retry_queue', 0)}")
    mem = state.get("memory") or {}
    if mem:
        lines.append("  Memoria: " + ", ".join(f"{k}={v}" for k, v in mem.items()))
    si = state.get("self_improvement") or {}
    if si:
        lines.append("  Auto-mejora: " + ", ".join(f"{k}={v}" for k, v in si.items()))
    return "\n".join(lines)


# ── agi_self_improve ──────────────────────────────────────────────────────────

def agi_self_improve(parameters: dict, player=None) -> str:
    """Auto-mejora: scan, suggestions, applied, apply, learn, report, status."""
    from actions.self_improvement_loop import (
        generate_suggestions, get_stored_suggestions, get_applied,
        save_suggestion, save_applied,
    )
    from core.self_improvement import get_self_improvement
    action = parameters.get("action", "status").lower()

    if action == "scan":
        suggestions = generate_suggestions()
        for s in suggestions:
            save_suggestion(s)
        if not suggestions:
            return "Escaneo completado. No se detectaron problemas."
        lines = ["Sugerencias de mejora:"]
        for s in suggestions:
            lines.append(f"  [{s['severity'].upper()}] {s['title']}")
            lines.append(f"         {s['detail'][:100]}")
        return "\n".join(lines)

    if action == "suggestions":
        suggestions = get_stored_suggestions()
        if not suggestions:
            return "No hay sugerencias guardadas."
        lines = [f"Sugerencias ({len(suggestions)}):"]
        for i, s in enumerate(suggestions[-10:], 1):
            lines.append(f"  {i}. [{s.get('severity', '?').upper()}] {s.get('title', '?')}")
        return "\n".join(lines)

    if action == "applied":
        applied = get_applied()
        if not applied:
            return "No hay mejoras aplicadas aún."
        lines = [f"Mejoras aplicadas ({len(applied)}):"]
        for a in applied[-10:]:
            lines.append(f"  • {a.get('title', '?')} — {a.get('result', '?')[:60]}")
        return "\n".join(lines)

    if action == "apply":
        title = parameters.get("title", "").strip()
        suggestions = get_stored_suggestions()
        match = next((s for s in suggestions if s.get("title", "").strip() == title), None)
        if not match:
            return f"No se encontró la sugerencia '{title}'. Usá 'suggestions' para ver las disponibles."
        save_applied({
            "title": match.get("title", title),
            "detail": match.get("detail", ""),
            "result": "marcada como aplicada",
            "timestamp": time.time(),
        })
        return f"Sugerencia marcada como aplicada: {title}"

    if action == "learn":
        lesson = parameters.get("lesson", "").strip()
        if not lesson:
            return "agi_self_improve learn necesita el parámetro 'lesson'."
        get_self_improvement().learn(lesson)
        return f"Lección aprendida: {lesson[:150]}"

    if action == "report":
        return get_self_improvement().get_improvement_report()

    st = get_self_improvement().get_status()
    return "Estado de auto-mejora: " + ", ".join(f"{k}={v}" for k, v in st.items())


# ── agi_agent ─────────────────────────────────────────────────────────────────

def agi_agent(parameters: dict, player=None) -> str:
    """Delegación de metas a agentes multi-paso."""
    from actions.auto_agent import auto_agent
    parameters = parameters or {}
    fwd = {
        "action": parameters.get("action", "status"),
        "goal": parameters.get("goal", ""),
        "description": parameters.get("description", ""),
        "max_steps": parameters.get("max_steps", 10),
        "plan_id": parameters.get("plan_id", ""),
    }
    return auto_agent(fwd, player)
