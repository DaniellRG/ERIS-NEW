"""self_improvement_loop.py — ERIS auto-mejora autónoma.
Lee logs, detecta errores, sugiere y aplica mejoras via self_modify."""
import os
import re
import json
import time
import threading
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
MEMORY_DIR = BASE_DIR / "memory"

DATA_DIR.mkdir(exist_ok=True)
MEMORY_DIR.mkdir(exist_ok=True)

_SUGGESTIONS_FILE = MEMORY_DIR / "improvement_suggestions.json"
_APPLIED_FILE = MEMORY_DIR / "applied_improvements.json"
_ERROR_CACHE_FILE = MEMORY_DIR / "error_cache.json"

_LOCK = threading.Lock()


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


def _read_log_file(filename):
    path = BASE_DIR / filename
    if not path.exists():
        return ""
    try:
        return path.read_text("utf-8", errors="replace")
    except Exception:
        return ""


def _get_eris_log_lines(max_lines=200):
    log = _read_log_file("eris.log")
    lines = log.split("\n")
    return [l for l in lines if l.strip()][-max_lines:]


def _scan_errors():
    log_lines = _get_eris_log_lines(300)
    patterns = {
        "import_error": re.compile(r"ImportError|ModuleNotFoundError|No module named", re.IGNORECASE),
        "attribute_error": re.compile(r"AttributeError.*object has no attribute", re.IGNORECASE),
        "key_error": re.compile(r"KeyError", re.IGNORECASE),
        "type_error": re.compile(r"TypeError", re.IGNORECASE),
        "index_error": re.compile(r"IndexError", re.IGNORECASE),
        "value_error": re.compile(r"ValueError", re.IGNORECASE),
        "file_not_found": re.compile(r"FileNotFoundError|No such file", re.IGNORECASE),
        "timeout": re.compile(r"Timeout|timed out", re.IGNORECASE),
        "connection": re.compile(r"ConnectionError|Connection refused|Connection reset", re.IGNORECASE),
        "permission": re.compile(r"PermissionError|Access denied", re.IGNORECASE),
        "syntax": re.compile(r"SyntaxError", re.IGNORECASE),
        "runtime": re.compile(r"RuntimeError", re.IGNORECASE),
        "zero_division": re.compile(r"ZeroDivisionError", re.IGNORECASE),
        "os_error": re.compile(r"OSError", re.IGNORECASE),
    }
    found = []
    for i, line in enumerate(log_lines):
        for error_type, pattern in patterns.items():
            if pattern.search(line):
                context = "\n".join(l[:160] for l in log_lines[max(0, i - 6):i])[-400:]
                found.append({
                    "type": error_type,
                    "line": line[:200],
                    "context": context,
                    "timestamp": time.time(),
                })
                break
    return found


def _count_errors_by_type(errors):
    counts = {}
    for err in errors:
        counts[err["type"]] = counts.get(err["type"], 0) + 1
    return counts


def _check_log_size():
    log_path = BASE_DIR / "eris.log"
    if not log_path.exists():
        return None
    size_mb = log_path.stat().st_size / (1024 * 1024)
    if size_mb > 50:
        return {"issue": "log_size", "detail": f"eris.log tiene {size_mb:.1f} MB", "suggestion": "Limpiar o rotar eris.log para liberar espacio"}
    return None


def _check_startup_errors():
    for f in ["stderr.txt", "startup_error.log", "stderr_debug.txt"]:
        content = _read_log_file(f)
        if content and len(content.strip()) > 10:
            return {"issue": "startup_error", "detail": f"{f} tiene contenido ({len(content)} chars)", "suggestion": f"Revisar {f} para diagnosticar errores de inicio"}
    return None


def _check_performance():
    """Analiza la tendencia de calidad de respuestas (self_evaluation.json).

    Devuelve una sugerencia concreta si la calidad está empeorando o el
    promedio es bajo. None si todo va bien o no hay datos.
    """
    eval_file = MEMORY_DIR / "self_evaluation.json"
    try:
        if not eval_file.exists():
            return None
        evaluations = json.loads(eval_file.read_text("utf-8"))
        if not isinstance(evaluations, list) or not evaluations:
            return None
        recent = [e.get("overall_score", 0.5) for e in evaluations[-10:]]
        older = [e.get("overall_score", 0.5) for e in evaluations[-20:-10]]
        recent_avg = sum(recent) / len(recent)
        older_avg = (sum(older) / len(older)) if older else recent_avg
        if recent_avg < older_avg - 0.1:
            return {
                "issue": "quality_drop",
                "detail": (f"Calidad de respuestas bajando: {older_avg:.0%} → {recent_avg:.0%} "
                           f"en las últimas 10 interacciones"),
                "suggestion": "Revisar prompts del sistema o contexto de la sesión para estabilizar calidad",
            }
        if recent_avg < 0.5:
            return {
                "issue": "low_quality",
                "detail": f"Calidad promedio baja ({recent_avg:.0%})",
                "suggestion": "Ajustar estrategia de respuesta y verificar contexto",
            }
        return None
    except Exception:
        return None


def generate_suggestions():
    with _LOCK:
        cached = _load_json(_ERROR_CACHE_FILE)
        now = time.time()
        if cached and (now - cached.get("last_scan", 0)) < 300:
            return cached.get("suggestions", [])

        suggestions = []
        errors = _scan_errors()

        counts = _count_errors_by_type(errors)
        for error_type, count in counts.items():
            if count >= 3:
                sample_err = next((e for e in errors if e["type"] == error_type), None)
                sample = sample_err["line"] if sample_err else ""
                context = sample_err["context"] if sample_err else ""
                suggestions.append({
                    "type": "error_pattern",
                    "severity": "alta" if count >= 10 else "media",
                    "title": f"Error recurrente: {error_type} ({count} veces)",
                    "detail": sample[:150],
                    "context": context,
                    "code_action": None,
                    "timestamp": now,
                })

        log_size = _check_log_size()
        if log_size:
            suggestions.append({
                "type": "maintenance",
                "severity": "baja",
                "title": log_size["issue"],
                "detail": log_size["detail"],
                "code_action": None,
                "timestamp": now,
            })

        startup = _check_startup_errors()
        if startup:
            suggestions.append({
                "type": "startup",
                "severity": "alta",
                "title": "Error de inicio detectado",
                "detail": startup["detail"],
                "code_action": None,
                "timestamp": now,
            })

        performance = _check_performance()
        if performance:
            suggestions.append({
                "type": "performance",
                "severity": "media",
                "title": performance["issue"],
                "detail": performance["detail"],
                "code_action": None,
                "timestamp": now,
            })

        _save_json(_ERROR_CACHE_FILE, {"last_scan": now, "suggestions": suggestions})
        return suggestions


def get_stored_suggestions():
    return _load_json(_SUGGESTIONS_FILE, [])


def save_suggestion(suggestion):
    """Guarda una sugerencia, deduplicando por título para no acumular spam."""
    suggestions = get_stored_suggestions()
    title = (suggestion or {}).get("title", "")
    if title:
        existing = [s for s in suggestions if s.get("title", "") == title]
        if existing:
            existing[0]["timestamp"] = suggestion.get("timestamp", time.time())
            existing[0]["count"] = existing[0].get("count", 1) + 1
            _save_json(_SUGGESTIONS_FILE, suggestions)
            return
    suggestions.append(suggestion)
    if len(suggestions) > 50:
        suggestions = suggestions[-50:]
    _save_json(_SUGGESTIONS_FILE, suggestions)


def get_applied():
    return _load_json(_APPLIED_FILE, [])


def save_applied(item):
    """Guarda una mejora aplicada, deduplicando por título."""
    applied = get_applied()
    title = (item or {}).get("title", "")
    if title:
        existing = [a for a in applied if a.get("title", "") == title]
        if existing:
            existing[0]["timestamp"] = item.get("timestamp", time.time())
            _save_json(_APPLIED_FILE, applied)
            return
    applied.append(item)
    if len(applied) > 50:
        applied = applied[-50:]
    _save_json(_APPLIED_FILE, applied)


def self_improvement_loop(parameters: dict, player=None) -> str:
    action = parameters.get("action", "").lower()

    if action == "scan":
        suggestions = generate_suggestions()
        for s in suggestions:
            save_suggestion(s)
        if not suggestions:
            return "✅ Escaneo completado. No se detectaron problemas."

        lines = ["🔍 Sugerencias de mejora:"]
        for s in suggestions:
            lines.append(f"  [{s['severity'].upper()}] {s['title']}")
            lines.append(f"         {s['detail'][:100]}")
        return "\n".join(lines)

    elif action == "list_suggestions":
        suggestions = get_stored_suggestions()
        if not suggestions:
            return "No hay sugerencias guardadas."
        lines = [f"📋 Sugerencias ({len(suggestions)}):"]
        for i, s in enumerate(suggestions[-10:], 1):
            lines.append(f"  {i}. [{s.get('severity','?').upper()}] {s.get('title','?')}")
        return "\n".join(lines)

    elif action == "list_applied":
        applied = get_applied()
        if not applied:
            return "No hay mejoras aplicadas aún."
        lines = [f"✅ Mejoras aplicadas ({len(applied)}):"]
        for a in applied[-10:]:
            lines.append(f"  • {a.get('title', '?')} — {a.get('result', '?')[:60]}")
        return "\n".join(lines)

    elif action == "report":
        suggestions = get_stored_suggestions()
        applied = get_applied()
        lines = [
            "═══════════════════════════════════════",
            "  REPORTE DE AUTO-MEJORA",
            "═══════════════════════════════════════",
            "",
            f"  Sugerencias pendientes: {len(suggestions)}",
            f"  Mejoras aplicadas: {len(applied)}",
            "",
        ]
        if suggestions:
            lines.append("  Últimas sugerencias:")
            for s in suggestions[-5:]:
                lines.append(f"    [{s.get('severity','?').upper()}] {s.get('title','?')}")
        if applied:
            lines.append("  Últimas mejoras:")
            for a in applied[-5:]:
                lines.append(f"    ✅ {a.get('title','?')}")
        return "\n".join(lines)

    else:
        return (
            "Acciones de self_improvement_loop:\n"
            "  scan: Escanear logs y sistema en busca de problemas\n"
            "  list_suggestions: Ver sugerencias pendientes\n"
            "  list_applied: Ver mejoras ya aplicadas\n"
            "  report: Reporte completo del estado de auto-mejora"
        )
