# -*- coding: utf-8 -*-
"""
self_health.py — Monitor de auto-salud para ERIS.

Detecta PROACTIVAMENTE riesgos de la propia ERIS (no URLs externas):
  * config rota (api_keys.json inválido / con BOM)
  * disco lleno (>90%)
  * RAM/CPU del proceso disparada
  * errores recientes nuevos en los logs (genuinos, sin WARN)
  * tools core que dejan de resolver (degradación)

Cada tick compara contra el estado previo (memory/self_health_state.json) y
solo notifica cuando hay un NUEVO problema o uno resuelto (sin spam).

Uso:
  run_self_health_loop(on_alert)   → hilo daemon para main.py (tick cada 5 min)
  self_health_tool(parameters)     → tool para pedir estado / forzar check
"""
from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path

try:
    import psutil
    _PSUTIL_OK = True
except Exception:
    _PSUTIL_OK = False

BASE = Path(__file__).resolve().parent.parent
STATE_FILE = BASE / "memory" / "self_health_state.json"
TICK_SECONDS = 300
_alert_lock = threading.Lock()


def _load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text("utf-8"))
    except Exception:
        return {"since": [], "_last_full": {}}


def _save_state(state: dict):
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), "utf-8")
    except Exception:
        pass


def _now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _check_config() -> dict | None:
    cfg = BASE / "config" / "api_keys.json"
    if not cfg.exists():
        return {"level": "error", "area": "config", "msg": f"Falta config/api_keys.json"}
    try:
        raw = cfg.read_bytes()
        if raw.startswith(b"\xef\xbb\xbf"):
            return {"level": "error", "area": "config", "msg": "config/api_keys.json tiene BOM (rompe el arranque)"}
        json.loads(raw.decode("utf-8", errors="replace"))
    except Exception as e:
        return {"level": "error", "area": "config", "msg": f"config/api_keys.json inválido: {str(e)[:120]}"}
    return None


def _check_disk() -> dict | None:
    if not _PSUTIL_OK:
        return None
    try:
        du = psutil.disk_usage("/")
        if du.percent >= 90:
            return {"level": "warn", "area": "disco", "msg": f"Disco al {du.percent:.0f}% (solo {du.free / 1024 ** 3:.1f} GB libres)"}
    except Exception:
        pass
    return None


def _check_process() -> dict | None:
    if not _PSUTIL_OK:
        return None
    try:
        p = psutil.Process(os.getpid())
        rss = p.memory_info().rss / 1024 ** 3
        if rss > 3.5:
            return {"level": "warn", "area": "memoria", "msg": f"RAM del proceso en {rss:.2f} GiB (posible fuga)"}
    except Exception:
        pass
    return None


_NEW_ERROR_LOG = BASE / "memory" / "self_health_errores.md"


def _check_logs() -> dict | None:
    """Busca errores en logs con mtime posterior al último check."""
    try:
        import re as _re
        last = _load_state().get("_last_full", {}).get("log_scan", 0)
        logs = [
            p for p in (BASE / "logs").iterdir() if p.suffix in (".log", ".txt")
        ] if (BASE / "logs").exists() else []
        logs += [p for p in Path("/tmp").glob("eris*.log") if p.is_file()]
        newest_err = None
        newest_mtime = 0.0
        for p in logs:
            try:
                if p.stat().st_mtime <= last:
                    continue
                tail = p.read_text("utf-8", errors="replace").splitlines()[-400:]
            except Exception:
                continue
            for line in tail:
                if _re.search(r"Traceback|ERROR|CRITICAL|SIGSEGV|Segmentation fault", line):
                    if "WARN" in line and "ERROR" not in line:
                        continue
                    m = p.stat().st_mtime
                    if m > newest_mtime:
                        newest_mtime = m
                        newest_err = {"log": p.name, "line": line.strip()[:200]}
        if newest_err:
            return {"level": "warn", "area": "logs", "msg": f"Nuevo error en {newest_err['log']}: {newest_err['line']}"}
    except Exception:
        pass
    return None


def _check_tools() -> dict | None:
    """Verifica que un core set de tools siga resolviendo (degradación silenciosa)."""
    try:
        from core.tool_registry import get_tool
        core_names = ("git_control", "evolucion", "system_health", "skill_manage", "diagnostico")
        missing = [n for n in core_names if get_tool(n) is None]
        if missing:
            return {"level": "warn", "area": "tools", "msg": f"Tools que no resuelven: {', '.join(missing)}"}
    except Exception:
        pass
    return None


def run_self_health_check(on_alert=None) -> str:
    """Ejecuta un chequeo completo y notifica problemas nuevos (por callback)."""
    checks = [_check_config, _check_disk, _check_process, _check_logs, _check_tools]
    problems = []
    for fn in checks:
        try:
            p = fn()
        except Exception:
            p = None
        if p:
            problems.append(p)

    state = _load_state()
    since = state.get("since", [])
    active_keys = {f"{p['area']}:{p['msg'][:60]}" for p in problems}
    resolved = [s for s in since if f"{s['area']}:{s['msg'][:60]}" not in active_keys]

    new_problems = []
    for p in problems:
        key = f"{p['area']}:{p['msg'][:60]}"
        if key not in {f"{s['area']}:{s['msg'][:60]}" for s in since}:
            new_problems.append(p)

    if new_problems and on_alert:
        with _alert_lock:
            for p in new_problems:
                try:
                    on_alert(p)
                except Exception:
                    pass

    if resolved:
        for s in resolved:
            try:
                with open(_NEW_ERROR_LOG, "a", encoding="utf-8") as f:
                    f.write(f"[{_now()}] ✅ Resuelto: {s['area']} — {s['msg']}\n")
            except Exception:
                pass

    for p in new_problems:
        try:
            with open(_NEW_ERROR_LOG, "a", encoding="utf-8") as f:
                f.write(f"[{_now()}] 🚨 {p['level'].upper()} [{p['area']}] {p['msg']}\n")
        except Exception:
            pass

    state["since"] = problems
    state["_last_full"] = state.get("_last_full", {})
    state["_last_full"]["log_scan"] = time.time()
    state["_last_full"]["last_check"] = _now()
    _save_state(state)

    if not problems:
        return "SALUD OK"
    return "\n".join(f"[{p['level']}] {p['area']}: {p['msg']}" for p in problems)


def run_self_health_loop(on_alert=None):
    """Hilo daemon de monitoreo continuo (tick cada TICK_SECONDS)."""
    time.sleep(60)  # espera a que arranque todo
    while True:
        try:
            result = run_self_health_check(on_alert)
            if result != "SALUD OK" and on_alert is None:
                print(f"[ERIS] 🩺 Auto-salud: {result.splitlines()[0][:100]}")
        except Exception as _she:
            try:
                print(f"[ERIS] Auto-salud error: {_she}")
            except Exception:
                pass
        time.sleep(TICK_SECONDS)


def self_health_tool(parameters: dict | None = None, player=None) -> str:
    """Tool ERIS: estado de la auto-salud. Acciones: status (default), check (forzar chequeo)."""
    p = parameters or {}
    action = str(p.get("action") or "status").lower()

    if action in ("check", "forzar", "scan"):
        return run_self_health_check()

    state = _load_state()
    last = state.get("_last_full", {}).get("last_check", "nunca")
    since = state.get("since", [])
    if not since:
        return f"🩺 Auto-salud: sin problemas conocidos (último check: {last}). Usa action='check' para forzar."
    lines = [f"🩺 Auto-salud (último check {last}):"]
    for p in since:
        lines.append(f"  [{p['level']}] {p['area']}: {p['msg']}")
    return "\n".join(lines)