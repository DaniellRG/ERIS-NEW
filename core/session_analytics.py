"""
session_analytics.py — Analítica de sesiones de usuario.

Analiza patrones de interacción del usuario:
  - Horas pico de uso
  - Duración promedio de sesiones
  - Topics más frecuentes por día/hora
  - Calidad de conversaciones (longitud, complejidad)
  - Tendencias de uso (más o menos usage)
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from collections import defaultdict
from datetime import datetime

_BASE = Path(__file__).resolve().parent.parent
_ANALYTICS_FILE = _BASE / "data" / "session_analytics.json"


def _load_analytics() -> dict:
    try:
        if _ANALYTICS_FILE.exists():
            return json.loads(_ANALYTICS_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {
        "sessions": [],
        "daily_stats": {},
        "hourly_distribution": defaultdict(int),
        "topic_frequency": defaultdict(int),
        "avg_session_length": 0,
    }


def _save_analytics(data: dict):
    try:
        _ANALYTICS_FILE.parent.mkdir(parents=True, exist_ok=True)
        # Convert defaultdicts a dicts para serialización
        for key in ["hourly_distribution", "topic_frequency"]:
            if isinstance(data.get(key), defaultdict):
                data[key] = dict(data[key])
        _ANALYTICS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def record_session(
    session_id: str = None,
    duration: float = 0,
    message_count: int = 0,
    tools_used: list[str] = None,
    topics: list[str] = None,
    success: bool = True,
):
    """Registra datos de una sesión."""
    data = _load_analytics()
    now = datetime.now()

    entry = {
        "id": session_id or "sess_%d" % int(time.time()),
        "timestamp": time.time(),
        "date": now.strftime("%Y-%m-%d"),
        "hour": now.hour,
        "weekday": now.strftime("%A"),
        "duration": duration,
        "message_count": message_count,
        "tools_used": tools_used or [],
        "topics": topics or [],
        "success": success,
    }
    data["sessions"].append(entry)

    # Actualizar distribución horaria
    hourly = data.get("hourly_distribution", {})
    if not isinstance(hourly, dict):
        hourly = dict(hourly)
    h = str(now.hour)
    hourly[h] = hourly.get(h, 0) + 1
    data["hourly_distribution"] = hourly

    # Actualizar frecuencia de topics
    topic_freq = data.get("topic_frequency", {})
    if not isinstance(topic_freq, dict):
        topic_freq = dict(topic_freq)
    for t in (topics or []):
        topic_freq[t] = topic_freq.get(t, 0) + 1
    data["topic_frequency"] = topic_freq

    # Actualizar stats diarias
    daily = data.get("daily_stats", {})
    date_key = now.strftime("%Y-%m-%d")
    if date_key not in daily:
        daily[date_key] = {"sessions": 0, "total_duration": 0, "total_messages": 0}
    daily[date_key]["sessions"] += 1
    daily[date_key]["total_duration"] += duration
    daily[date_key]["total_messages"] += message_count
    data["daily_stats"] = daily

    # Mantener solo últimas 1000 sesiones
    if len(data["sessions"]) > 1000:
        data["sessions"] = data["sessions"][-1000:]

    _save_analytics(data)


def get_usage_patterns() -> dict:
    """Analiza patrones de uso."""
    data = _load_analytics()
    sessions = data.get("sessions", [])

    if not sessions:
        return {"total_sessions": 0}

    # Horas pico
    hourly = data.get("hourly_distribution", {})
    peak_hours = sorted(hourly.items(), key=lambda x: x[1], reverse=True)[:3]

    # Duración promedio
    durations = [s.get("duration", 0) for s in sessions]
    avg_duration = sum(durations) / len(durations) if durations else 0

    # Messages por sesión
    msgs = [s.get("message_count", 0) for s in sessions]
    avg_messages = sum(msgs) / len(msgs) if msgs else 0

    # Tools más usadas
    all_tools = []
    for s in sessions:
        all_tools.extend(s.get("tools_used", []))
    tool_counts = defaultdict(int)
    for t in all_tools:
        tool_counts[t] += 1
    top_tools = sorted(tool_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    # Topics más frecuentes
    topic_freq = data.get("topic_frequency", {})
    top_topics = sorted(topic_freq.items(), key=lambda x: x[1], reverse=True)[:5]

    # Tendencia (últimos 7 días vs 7 anteriores)
    daily = data.get("daily_stats", {})
    dates = sorted(daily.keys(), reverse=True)
    recent_7 = sum(daily.get(d, {}).get("sessions", 0) for d in dates[:7])
    prev_7 = sum(daily.get(d, {}).get("sessions", 0) for d in dates[7:14])
    trend = "increasing" if recent_7 > prev_7 else ("decreasing" if recent_7 < prev_7 else "stable")

    return {
        "total_sessions": len(sessions),
        "avg_duration_minutes": round(avg_duration / 60, 1),
        "avg_messages_per_session": round(avg_messages, 1),
        "peak_hours": [{"hour": h, "count": c} for h, c in peak_hours],
        "top_tools": [{"tool": t, "count": c} for t, c in top_tools],
        "top_topics": [{"topic": t, "count": c} for t, c in top_topics],
        "trend": trend,
        "recent_sessions_7d": recent_7,
        "prev_sessions_7d": prev_7,
    }


def get_daily_report(days: int = 7) -> list[dict]:
    """Reporte de uso diario de los últimos N días."""
    data = _load_analytics()
    daily = data.get("daily_stats", {})
    dates = sorted(daily.keys(), reverse=True)[:days]

    report = []
    for d in dates:
        info = daily[d]
        report.append({
            "date": d,
            "sessions": info.get("sessions", 0),
            "duration_minutes": round(info.get("total_duration", 0) / 60, 1),
            "messages": info.get("total_messages", 0),
        })
    return report


def format_analytics() -> str:
    """Formatea analíticas para mostrar."""
    patterns = get_usage_patterns()
    lines = [
        "Analíticas de uso:",
        "  Total sesiones: %d" % patterns.get("total_sessions", 0),
        "  Duración promedio: %.1f min" % patterns.get("avg_duration_minutes", 0),
        "  Mensajes/sesión: %.1f" % patterns.get("avg_messages_per_session", 0),
        "  Tendencia: %s" % patterns.get("trend", "N/A"),
    ]
    if patterns.get("peak_hours"):
        hours = ", ".join("%s:00 (%d)" % (h["hour"], h["count"]) for h in patterns["peak_hours"])
        lines.append("  Horas pico: %s" % hours)
    if patterns.get("top_tools"):
        tools = ", ".join("%s (%d)" % (t["tool"], t["count"]) for t in patterns["top_tools"][:3])
        lines.append("  Tools top: %s" % tools)
    return "\n".join(lines)
