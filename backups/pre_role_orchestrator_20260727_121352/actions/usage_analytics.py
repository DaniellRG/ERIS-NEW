"""
usage_analytics.py — Estadísticas de uso: qué tools se usan más, cuándo, qué falla.
Registra todas las llamadas a tools y genera reportes.
"""
import json
import time
from pathlib import Path
from datetime import datetime, timedelta

_BASE = Path(__file__).resolve().parent.parent
_ANALYTICS_FILE = _BASE / "data" / "usage_analytics.json"
_MAX_ENTRIES = 10000


def usage_analytics(parameters: dict = None, player=None) -> str:
    """
    Estadísticas de uso.
    Acciones: log, report, top_tools, errors, timeline, summary, export, clear, session, goals
    """
    params = parameters or {}
    action = params.get("action", "summary").lower()

    if action == "log":
        return _log_usage(params)
    elif action == "report":
        return _generate_report(params)
    elif action == "top_tools":
        return _top_tools(params)
    elif action == "errors":
        return _error_report(params)
    elif action == "timeline":
        return _timeline(params)
    elif action == "summary":
        return _get_summary()
    elif action == "export":
        return _export_analytics()
    elif action == "clear":
        return _clear_analytics()
    elif action == "session":
        return _session_stats(params)
    elif action == "goals":
        return _goal_tracking(params)
    elif action == "health":
        return _system_health()
    return "Acciones: log, report, top_tools, errors, timeline, summary, export, clear, session, goals, health"


def _log_usage(params: dict) -> str:
    tool_name = params.get("tool", "")
    success = params.get("success", True)
    duration_ms = params.get("duration_ms", 0)
    error_msg = params.get("error", "")
    context = params.get("context", {})

    entry = {
        "tool": tool_name,
        "success": success,
        "duration_ms": duration_ms,
        "error": error_msg,
        "timestamp": datetime.now().isoformat(),
        "context": context,
        "session_id": params.get("session_id", "default"),
    }

    analytics = _load_analytics()
    analytics["entries"].append(entry)
    analytics["entries"] = analytics["entries"][-_MAX_ENTRIES:]

    analytics["totals"]["calls"] = analytics["totals"].get("calls", 0) + 1
    if success:
        analytics["totals"]["successes"] = analytics["totals"].get("successes", 0) + 1
    else:
        analytics["totals"]["errors"] = analytics["totals"].get("errors", 0) + 1

    analytics["tool_counts"][tool_name] = analytics["tool_counts"].get(tool_name, 0) + 1
    if not success:
        analytics.setdefault("error_counts", {})[tool_name] = analytics.get("error_counts", {}).get(tool_name, 0) + 1

    _save_analytics(analytics)
    return "Usage logged: {} | {}".format(tool_name, "ok" if success else "error")


def _generate_report(params: dict) -> str:
    days = int(params.get("days", 7))
    analytics = _load_analytics()
    entries = analytics["entries"]
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    recent = [e for e in entries if e.get("timestamp", "") > cutoff]

    if not recent:
        return "No hay datos de uso en los últimos {} días".format(days)

    total = len(recent)
    successes = sum(1 for e in recent if e.get("success"))
    errors = total - successes
    avg_duration = sum(e.get("duration_ms", 0) for e in recent) / total if total else 0

    tool_usage = {}
    for e in recent:
        t = e.get("tool", "unknown")
        tool_usage[t] = tool_usage.get(t, 0) + 1

    lines = [
        "Reporte de uso ({} días):".format(days),
        "  Total llamadas: {}".format(total),
        "  Éxitos: {} ({:.1f}%)".format(successes, successes / total * 100),
        "  Errores: {} ({:.1f}%)".format(errors, errors / total * 100),
        "  Duración promedio: {:.0f}ms".format(avg_duration),
        "",
        "Tools más usadas:",
    ]
    for tool, count in sorted(tool_usage.items(), key=lambda x: -x[1])[:10]:
        lines.append("  {} | {} llamadas".format(tool, count))
    return "\n".join(lines)


def _top_tools(params: dict) -> str:
    limit = int(params.get("limit", 10))
    analytics = _load_analytics()
    tool_counts = analytics.get("tool_counts", {})

    if not tool_counts:
        return "No hay datos de uso"

    lines = ["Top {} tools:".format(limit)]
    for tool, count in sorted(tool_counts.items(), key=lambda x: -x[1])[:limit]:
        lines.append("  {} | {} llamadas".format(tool, count))
    return "\n".join(lines)


def _error_report(params: dict) -> str:
    days = int(params.get("days", 7))
    analytics = _load_analytics()
    entries = analytics["entries"]
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    errors = [e for e in entries if not e.get("success") and e.get("timestamp", "") > cutoff]

    if not errors:
        return "No hay errores en los últimos {} días".format(days)

    error_by_tool = {}
    for e in errors:
        tool = e.get("tool", "unknown")
        error_by_tool.setdefault(tool, []).append(e.get("error", "sin detalle"))

    lines = ["Errores ({} días, {} total):".format(days, len(errors))]
    for tool, errs in sorted(error_by_tool.items(), key=lambda x: -len(x[1])):
        lines.append("  {} | {} errores".format(tool, len(errs)))
        for err in errs[:3]:
            lines.append("    - {}".format(err[:80]))
    return "\n".join(lines)


def _timeline(params: dict) -> str:
    hours = int(params.get("hours", 24))
    analytics = _load_analytics()
    entries = analytics["entries"]
    cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
    recent = [e for e in entries if e.get("timestamp", "") > cutoff]

    hourly = {}
    for e in recent:
        try:
            h = datetime.fromisoformat(e["timestamp"]).hour
            hourly[h] = hourly.get(h, 0) + 1
        except Exception:
            pass

    if not hourly:
        return "No hay actividad en las últimas {} horas".format(hours)

    max_count = max(hourly.values())
    lines = ["Timeline ({} horas):".format(hours)]
    for h in range(24):
        count = hourly.get(h, 0)
        bar = "█" * int(count / max_count * 20) if max_count else ""
        lines.append("  {:02d}:00 | {} | {}".format(h, count, bar))
    return "\n".join(lines)


def _get_summary() -> str:
    analytics = _load_analytics()
    totals = analytics.get("totals", {})
    tool_counts = analytics.get("tool_counts", {})
    error_counts = analytics.get("error_counts", {})
    entries = analytics.get("entries", [])

    total_calls = totals.get("calls", 0)
    total_success = totals.get("successes", 0)
    total_errors = totals.get("errors", 0)
    success_rate = (total_success / total_calls * 100) if total_calls else 0

    top_tool = max(tool_counts, key=tool_counts.get) if tool_counts else "ninguna"
    top_error = max(error_counts, key=error_counts.get) if error_counts else "ninguna"

    last_activity = entries[-1].get("timestamp", "?")[:16] if entries else "nunca"

    lines = [
        "Usage Analytics Summary:",
        "  Total llamadas: {}".format(total_calls),
        "  Tasa de éxito: {:.1f}%".format(success_rate),
        "  Errores totales: {}".format(total_errors),
        "  Tools registradas: {}".format(len(tool_counts)),
        "  Tool más usada: {} ({})".format(top_tool, tool_counts.get(top_tool, 0)),
        "  Tool con más errores: {} ({})".format(top_error, error_counts.get(top_error, 0)),
        "  Última actividad: {}".format(last_activity),
    ]
    return "\n".join(lines)


def _export_analytics() -> str:
    analytics = _load_analytics()
    export_path = _BASE / "data" / "analytics_export.json"
    export_path.write_text(json.dumps(analytics, indent=2, ensure_ascii=False), encoding="utf-8")
    return "Analytics exportados a: {}".format(str(export_path))


def _clear_analytics() -> str:
    count = len(_load_analytics().get("entries", []))
    _save_analytics({"entries": [], "totals": {}, "tool_counts": {}, "error_counts": {}})
    return "Analytics limpiados ({} entries removidos)".format(count)


def _session_stats(params: dict) -> str:
    session_id = params.get("session_id", "default")
    analytics = _load_analytics()
    session_entries = [e for e in analytics["entries"] if e.get("session_id") == session_id]

    if not session_entries:
        return "No hay datos para sesión: {}".format(session_id)

    total = len(session_entries)
    successes = sum(1 for e in session_entries if e.get("success"))
    avg_duration = sum(e.get("duration_ms", 0) for e in session_entries) / total

    tools_used = set(e.get("tool", "") for e in session_entries)
    first = session_entries[0].get("timestamp", "?")[:16]
    last = session_entries[-1].get("timestamp", "?")[:16]

    return "Sesión '{}': {} llamadas | {} éxitos | {:.0f}ms promedio | {} tools | {} → {}".format(
        session_id, total, successes, avg_duration, len(tools_used), first, last)


def _goal_tracking(params: dict) -> str:
    goals = params.get("goals", {})
    analytics = _load_analytics()
    stored_goals = analytics.get("goals", {})

    if goals:
        stored_goals.update(goals)
        analytics["goals"] = stored_goals
        _save_analytics(analytics)
        return "Goals actualizados"

    if not stored_goals:
        return "No hay goals definidos"

    lines = ["Goals:"]
    for goal, target in stored_goals.items():
        current = analytics.get("tool_counts", {}).get(goal, 0)
        pct = (current / target * 100) if target else 0
        bar = "█" * int(pct / 5)
        lines.append("  {}: {}/{} ({}%) {}".format(goal, current, target, int(pct), bar))
    return "\n".join(lines)


def _system_health() -> str:
    analytics = _load_analytics()
    entries = analytics.get("entries", [])
    recent_1h = [e for e in entries if e.get("timestamp", "") > (datetime.now() - timedelta(hours=1)).isoformat()]
    recent_24h = [e for e in entries if e.get("timestamp", "") > (datetime.now() - timedelta(hours=24)).isoformat()]

    errors_1h = sum(1 for e in recent_1h if not e.get("success"))
    errors_24h = sum(1 for e in recent_24h if not e.get("success"))

    health = "saludable"
    if errors_1h > 5:
        health = "degradado"
    if errors_1h > 20:
        health = "crítico"

    return "Health: {} | Última hora: {} llamadas ({} errores) | 24h: {} llamadas ({} errores)".format(
        health, len(recent_1h), errors_1h, len(recent_24h), errors_24h)


def _load_analytics():
    if _ANALYTICS_FILE.exists():
        try:
            return json.loads(_ANALYTICS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"entries": [], "totals": {}, "tool_counts": {}, "error_counts": {}}


def _save_analytics(analytics):
    _ANALYTICS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _ANALYTICS_FILE.write_text(json.dumps(analytics, indent=2, ensure_ascii=False), encoding="utf-8")
