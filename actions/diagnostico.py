# -*- coding: utf-8 -*-
"""
diagnostico.py — Panel de diagnóstico en vivo para ERIS.

Responde "¿qué se rompió y por qué?" de forma accionable:
  * state   → resumen general (config válida, disco, proceso, logs recientes)
  * logs    → últimos errores/tracebacks de los logs de ERIS con contexto
  * config  → valida config/api_keys.json (JSON parseable + no BOM)
  * health  → chequeo rápido de core modules y tools clave
  * reporte → informe completo formateado para hablar/guardar

Se ejecuta solo con psutil/estándar (sin deps nuevas); si falta psutil,
degrada con graceful message (nunca crash).
"""
from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path

try:
    import psutil
    _PSUTIL_OK = True
except Exception:
    _PSUTIL_OK = False

BASE = Path(__file__).resolve().parent.parent
CONFIG_FILE = BASE / "config" / "api_keys.json"
LOG_LIKE = [
    BASE / "logs",
    BASE / "data" / "logs",
    BASE / "memory",
    Path("/tmp"),
]
_KNOWN_LOG_NAMES = (
    "eris.log", "eris2.log", "eris3.log", "app.log", "debug.log",
    "logs.log", "main.log", "eris_gemini.log", "eris_gemini2.log",
    "eris_gemini3.log", "eris_trace.log", "runtime.log",
)


def _tail(path: Path, n: int = 500) -> list[str]:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        return [l.rstrip("\n") for l in lines[-n:]]
    except Exception:
        return []


def _find_logs(limit: int = 8) -> list[Path]:
    found: list[Path] = []
    seen: set[Path] = set()
    for d in LOG_LIKE:
        if not d.exists():
            continue
        try:
            for p in sorted(d.iterdir()):
                if not p.is_file():
                    continue
                if p.suffix.lower() not in (".log", ".txt"):
                    continue
                if p.name.lower() not in _KNOWN_LOG_NAMES and not p.name.startswith("eris"):
                    continue
                if p not in seen:
                    seen.add(p)
                    found.append(p)
        except Exception:
            continue
        if len(found) >= limit:
            break
    # /tmp: solo los que contienen "eris" en el nombre
    try:
        for p in sorted(Path("/tmp").glob("eris*.log")):
            if p.is_file() and p not in seen:
                seen.add(p)
                found.append(p)
    except Exception:
        pass
    return sorted(found, key=lambda x: x.stat().st_mtime if x.exists() else 0, reverse=True)[:limit]


_ERROR_PATTERNS = (
    "Traceback", "ERROR", "Error", "EXCEPTION", "Exception",
    "CRITICAL", "FAILED", "Fallo", "crash", "Traceback (most recent call last)",
    "TimeoutError", "ConnectionError", "Segmentation fault", "SIGSEGV",
)


def _scan_log_errors(max_logs: int = 5) -> list[dict]:
    """Extrae los últimos errores de cada log con contexto de líneas."""
    findings: list[dict] = []
    for path in _find_logs(max_logs):
        if not path.exists():
            continue
        lines = _tail(path, 800)
        # agrupar por línea de error: recolectar la línea + contexto siguiente
        for i, line in enumerate(lines):
            if any(p in line for p in _ERROR_PATTERNS):
                if any(line.strip().startswith(("[", "202")) is False and "WARN" in line for p2 in []):
                    continue
                if "WARN" in line and "ERROR" not in line and "Traceback" not in line:
                    continue
                ctx = [line[:400]]
                for j in range(i + 1, min(i + 7, len(lines))):
                    ctx.append(lines[j][:400])
                    if "Traceback" not in lines[j] and "  File" not in lines[j] and lines[j].strip() == "":
                        break
                findings.append({
                    "log": path.name,
                    "mtime": time.strftime("%Y-%m-%d %H:%M", time.localtime(path.stat().st_mtime)),
                    "context": ctx,
                })
                if len(findings) >= 12:
                    return findings
    return findings


def _check_config() -> dict:
    if not CONFIG_FILE.exists():
        return {"ok": False, "detail": f"No existe {CONFIG_FILE.name}"}
    try:
        raw = CONFIG_FILE.read_bytes()
        if raw.startswith(b"\xef\xbb\xbf"):
            return {"ok": False, "detail": "BOM presente (crash en arranque). Reescribir UTF-8 sin BOM"}
        data = json.loads(raw.decode("utf-8", errors="replace"))
        tts = data.get("tts_backend")
        return {"ok": True, "detail": f"JSON válido, tts_backend={tts}"}
    except Exception as e:
        return {"ok": False, "detail": f"JSON inválido: {str(e)[:150]}"}


def _check_disk() -> list[dict]:
    if not _PSUTIL_OK:
        return [{"path": str(BASE), "ok": None, "detail": "psutil no disponible"}]
    out = []
    for p in ("/", str(BASE)):
        try:
            du = psutil.disk_usage(p)
            pct = du.percent
            out.append({
                "path": p,
                "ok": pct < 90,
                "detail": f"{pct:.0f}% usado, {du.free / 1024 ** 3:.1f} GB libres" if pct >= 90
                          else f"{pct:.0f}% usado ({du.free / 1024 ** 3:.0f} GB libres)",
            })
        except Exception:
            continue
    return out


def _check_process() -> dict:
    if not _PSUTIL_OK:
        return {"ok": None, "detail": "psutil no disponible"}
    try:
        pid = os.getpid()
        p = psutil.Process(pid)
        mem = p.memory_percent()
        cpu = p.cpu_percent(interval=0.2)
        rss_gb = p.memory_info().rss / 1024 ** 3
        return {"pid": pid, "ok": True, "detail": f"up {time.time() - p.create_time():.0f}s, RAM {rss_gb:.2f} GiB ({mem:.1f}%), CPU {cpu:.0f}%"}
    except Exception as e:
        return {"ok": False, "detail": str(e)[:150]}


def _check_system() -> dict:
    if not _PSUTIL_OK:
        return {"ok": None, "detail": "psutil no disponible"}
    try:
        return {
            "ok": True,
            "detail": f"CPU {psutil.cpu_percent(interval=0.3):.0f}%, RAM {psutil.virtual_memory().percent:.0f}%, "
                      f"{psutil.cpu_count()} cores",
        }
    except Exception as e:
        return {"ok": False, "detail": str(e)[:150]}


def _check_tools() -> list[dict]:
    names = ("git_control", "git_daily", "evolucion", "system_health",
             "skill_manage", "diagnostico")
    out = []
    for n in names:
        try:
            from core.tool_registry import get_tool
            fn = get_tool(n)
            out.append({"tool": n, "ok": fn is not None})
        except Exception as e:
            out.append({"tool": n, "ok": False, "detail": str(e)[:100]})
    return out


def _render_state() -> str:
    cfg = _check_config()
    lines = ["DIAGNÓSTICO ERIS — " + time.strftime("%Y-%m-%d %H:%M")]
    lines.append(f"• Config: {'✅ OK — ' + cfg['detail'] if cfg['ok'] else '❌ ' + cfg['detail']}")
    errs = _scan_log_errors(3)
    lines.append(f"• Errores recientes en logs: {len(errs)}")
    if errs:
        for e in errs[:3]:
            lines.append(f"   • {e['log']} ({e['mtime']}): {e['context'][0][:150]}")
    for d in _check_disk():
        lines.append(f"• Disco {d['path']}: {'✅' if d.get('ok') is True else '❌' if d.get('ok') is False else '•'} {d['detail']}")
    proc = _check_process()
    lines.append(f"• Proceso: {'✅ ' if proc.get('ok') else '❌ '}{proc['detail']}")
    sysx = _check_system()
    lines.append(f"• Sistema: {'✅ ' if sysx.get('ok') else '❌ '}{sysx['detail']}")
    tools = _check_tools()
    broken = [t for t in tools if not t.get("ok")]
    lines.append(f"• Tools clave: {len(tools) - len(broken)}/{len(tools)} OK"
                 + (f" — rotas: {[t['tool'] for t in broken]}" if broken else ""))
    return "\n".join(lines)


def _render_logs(parameters: dict) -> str:
    p = parameters or {}
    n_logs = int(p.get("logs") or 3)
    filtro = str(p.get("filtro") or "").lower()
    errs = _scan_log_errors(n_logs)
    if filtro:
        errs = [e for e in errs if filtro in "\n".join(e["context"]).lower() or filtro in e["log"].lower()]
    if not errs:
        return "No se encontraron errores recientes en los logs."
    lines = [f"ERRORES RECIENTES ({len(errs)}):"]
    for i, e in enumerate(errs):
        lines.append(f"\n[{i+1}] {e['log']} — {e['mtime']}")
        lines.extend("  " + c for c in e["context"][:5])
    return "\n".join(lines)


def diagnostico(parameters: dict | None = None, player=None) -> str:
    """Panel de diagnóstico ERIS. Acciones: state (default), logs, config, health, reporte."""
    p = parameters or {}
    action = str(p.get("action") or "state").lower()

    if player:
        try:
            player.write_log(f"🔬 Diagnóstico: {action}")
        except Exception:
            pass

    if action in ("state", "estado", "resumen"):
        return _render_state()

    if action in ("logs", "errores", "error"):
        return _render_logs(p)

    if action in ("config",):
        cfg = _check_config()
        return f"CONFIG: {'✅ OK' if cfg['ok'] else '❌ ' + cfg['detail']}\n{CONFIG_FILE}"

    if action in ("health", "salud"):
        tools = _check_tools()
        lines = ["HEALTH CHECK:"]
        lines += [f"  {'✅' if t.get('ok') else '❌'} {t['tool']}" + (f" — {t.get('detail', '')}" if not t.get('ok') else "") for t in tools]
        return "\n".join(lines)

    if action in ("reporte", "informe", "report"):
        return _render_state() + "\n\n" + _render_logs({"logs": 5})

    return _render_state() + "\n\nUsa action='logs'|'config'|'health'|'reporte' para detalle."