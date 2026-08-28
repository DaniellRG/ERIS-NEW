"""
core/console_log.py — Centralized error/performance console.log for ERIS.
Logs errors, warnings, tool calls, performance, and system events.
Eris can read/search this log via the console_log tool.
"""
from __future__ import annotations

import json
import os
import time
import threading
import traceback
from pathlib import Path
from datetime import datetime
from typing import Any, Optional

_BASE = Path(__file__).resolve().parent.parent
_LOG_DIR = _BASE / "data" / "console_logs"
_LOG_FILE = _LOG_DIR / "console.log"
_ERROR_FILE = _LOG_DIR / "errors.log"
_PERF_FILE = _LOG_DIR / "performance.log"
_STATS_FILE = _LOG_DIR / "stats.json"

_lock = threading.Lock()
_initialized = False

# ── Init ────────────────────────────────────────────────────────────────────

def _ensure_init():
    global _initialized
    if _initialized:
        return
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    _initialized = True


def _rotate_if_needed(path: Path, max_mb: float = 5.0):
    """Rotate log file if it exceeds max_mb."""
    try:
        if path.exists() and path.stat().st_size > max_mb * 1024 * 1024:
            backup = path.with_suffix(".log.bak")
            if backup.exists():
                backup.unlink(missing_ok=True)
            path.rename(backup)
            path.write_text("", encoding="utf-8")
    except Exception:
        pass


# ── Core logging functions ──────────────────────────────────────────────────

def log(level: str, category: str, message: str, data: Optional[dict] = None):
    """Write a structured log entry."""
    _ensure_init()
    _rotate_if_needed(_LOG_FILE)

    entry = {
        "ts": datetime.now().isoformat(),
        "level": level.upper(),
        "cat": category,
        "msg": message,
    }
    if data:
        entry["data"] = data

    line = json.dumps(entry, ensure_ascii=False, default=str) + "\n"

    with _lock:
        try:
            with open(_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(line)
        except Exception:
            pass


def log_error(source: str, error: str, traceback_str: str = "", context: Optional[dict] = None):
    """Log an error with full context."""
    _ensure_init()
    _rotate_if_needed(_ERROR_FILE)
    _rotate_if_needed(_LOG_FILE)

    entry = {
        "ts": datetime.now().isoformat(),
        "level": "ERROR",
        "source": source,
        "error": error,
    }
    if traceback_str:
        entry["traceback"] = traceback_str[:3000]
    if context:
        entry["context"] = context

    line = json.dumps(entry, ensure_ascii=False, default=str) + "\n"

    # Write to both errors.log and console.log
    with _lock:
        try:
            with open(_ERROR_FILE, "a", encoding="utf-8") as f:
                f.write(line)
            with open(_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(line)
        except Exception:
            pass

    # Update error stats
    _update_stats("errors", source)


def log_warning(source: str, message: str, context: Optional[dict] = None):
    """Log a warning."""
    entry = {"source": source, "message": message}
    if context:
        entry["context"] = context
    log("WARN", source, message, context)


def log_tool_call(tool_name: str, params: dict, duration_ms: float, success: bool, result_preview: str = ""):
    """Log a tool execution."""
    _ensure_init()

    entry = {
        "ts": datetime.now().isoformat(),
        "level": "INFO",
        "cat": "tool",
        "tool": tool_name,
        "duration_ms": round(duration_ms, 1),
        "success": success,
        "params": {k: str(v)[:200] for k, v in params.items()} if params else {},
    }
    if result_preview:
        entry["result"] = result_preview[:500]

    line = json.dumps(entry, ensure_ascii=False, default=str) + "\n"

    with _lock:
        try:
            with open(_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(line)
        except Exception:
            pass

    _update_stats("tool_calls", tool_name)


def log_performance(metric: str, value: float, unit: str = "ms", context: Optional[dict] = None):
    """Log a performance metric."""
    _ensure_init()
    _rotate_if_needed(_PERF_FILE)

    entry = {
        "ts": datetime.now().isoformat(),
        "metric": metric,
        "value": round(value, 2),
        "unit": unit,
    }
    if context:
        entry["context"] = context

    line = json.dumps(entry, ensure_ascii=False, default=str) + "\n"

    with _lock:
        try:
            with open(_PERF_FILE, "a", encoding="utf-8") as f:
                f.write(line)
        except Exception:
            pass


def log_system(event: str, details: Optional[dict] = None):
    """Log a system event (startup, shutdown, reconnect, etc.)."""
    log("INFO", "system", event, details)


# ── Stats ───────────────────────────────────────────────────────────────────

def _update_stats(category: str, item: str):
    """Update running stats."""
    try:
        stats = {}
        if _STATS_FILE.exists():
            stats = json.loads(_STATS_FILE.read_text("utf-8"))

        if category not in stats:
            stats[category] = {}
        if item not in stats[category]:
            stats[category][item] = {"count": 0, "last": None}

        stats[category][item]["count"] += 1
        stats[category][item]["last"] = datetime.now().isoformat()

        _STATS_FILE.write_text(json.dumps(stats, indent=2, ensure_ascii=False, default=str), "utf-8")
    except Exception:
        pass


# ── Read/Search ─────────────────────────────────────────────────────────────

def read_log(lines: int = 50, level: Optional[str] = None, category: Optional[str] = None) -> str:
    """Read last N lines of console.log, optionally filtered."""
    _ensure_init()
    if not _LOG_FILE.exists():
        return "Console.log vacío."

    try:
        with open(_LOG_FILE, "r", encoding="utf-8") as f:
            all_lines = f.readlines()

        # Filter
        if level:
            all_lines = [l for l in all_lines if f'"level": "{level.upper()}"' in l or f'"level":"{level.upper()}"' in l]
        if category:
            all_lines = [l for l in all_lines if f'"cat": "{category}"' in l or f'"cat":"{category}"' in l or f'"source": "{category}"' in l]

        # Last N
        recent = all_lines[-lines:]

        if not recent:
            return "No hay entradas que coincidan con el filtro."

        # Format for readability
        output = []
        for line in recent:
            try:
                entry = json.loads(line.strip())
                ts = entry.get("ts", "?")[:19]
                level_str = entry.get("level", "?")
                msg = entry.get("msg", entry.get("error", entry.get("message", "")))
                source = entry.get("cat", entry.get("source", ""))
                output.append(f"[{ts}] {level_str} [{source}] {msg}")
            except json.JSONDecodeError:
                output.append(line.strip())

        return "\n".join(output)

    except Exception as e:
        return f"Error leyendo console.log: {e}"


def search_log(query: str, max_results: int = 20) -> str:
    """Search console.log for a query."""
    _ensure_init()
    if not _LOG_FILE.exists():
        return "Console.log vacío."

    try:
        results = []
        query_lower = query.lower()

        with open(_LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if query_lower in line.lower():
                    try:
                        entry = json.loads(line.strip())
                        ts = entry.get("ts", "?")[:19]
                        level = entry.get("level", "?")
                        msg = entry.get("msg", entry.get("error", entry.get("message", "")))
                        source = entry.get("cat", entry.get("source", ""))
                        results.append(f"[{ts}] {level} [{source}] {msg}")
                    except json.JSONDecodeError:
                        results.append(line.strip())

                if len(results) >= max_results:
                    break

        if not results:
            return f"No se encontraron resultados para '{query}'."

        return f"Resultados para '{query}' ({len(results)}):\n" + "\n".join(results)

    except Exception as e:
        return f"Error buscando en console.log: {e}"


def get_errors(lines: int = 30) -> str:
    """Read last N errors from errors.log."""
    _ensure_init()
    if not _ERROR_FILE.exists():
        return "Sin errores registrados."

    try:
        with open(_ERROR_FILE, "r", encoding="utf-8") as f:
            all_lines = f.readlines()

        recent = all_lines[-lines:]
        if not recent:
            return "Sin errores recientes."

        output = []
        for line in recent:
            try:
                entry = json.loads(line.strip())
                ts = entry.get("ts", "?")[:19]
                source = entry.get("source", "?")
                error = entry.get("error", "?")
                output.append(f"[{ts}] {source}: {error}")
            except json.JSONDecodeError:
                output.append(line.strip())

        return f"Últimos {len(output)} errores:\n" + "\n".join(output)

    except Exception as e:
        return f"Error leyendo errores: {e}"


def get_stats() -> str:
    """Get error/call statistics."""
    _ensure_init()
    if not _STATS_FILE.exists():
        return "Sin estadísticas."

    try:
        stats = json.loads(_STATS_FILE.read_text("utf-8"))
        output = ["=== Estadísticas de Console.log ===\n"]

        if "errors" in stats:
            output.append("Errores por fuente:")
            for source, info in sorted(stats["errors"].items(), key=lambda x: x[1]["count"], reverse=True):
                output.append(f"  {source}: {info['count']} (último: {info['last'][:19]})")

        if "tool_calls" in stats:
            output.append("\nTool calls:")
            for tool, info in sorted(stats["tool_calls"].items(), key=lambda x: x[1]["count"], reverse=True)[:15]:
                output.append(f"  {tool}: {info['count']} (último: {info['last'][:19]})")

        return "\n".join(output)

    except Exception as e:
        return f"Error leyendo stats: {e}"


def get_log_file_path() -> str:
    """Return the path to the console.log file."""
    _ensure_init()
    return str(_LOG_FILE)


def clear_log():
    """Clear all log files."""
    _ensure_init()
    with _lock:
        for f in [_LOG_FILE, _ERROR_FILE, _PERF_FILE]:
            try:
                f.write_text("", encoding="utf-8")
            except Exception:
                pass
    return "Console.log limpiado."


# ── Exception handler decorator ─────────────────────────────────────────────

def catch_and_log(source: str):
    """Decorator that catches exceptions and logs them."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                tb = traceback.format_exc()
                log_error(source, str(e), tb, {"args": str(args)[:200], "kwargs": str(kwargs)[:200]})
                raise
        return wrapper
    return decorator
