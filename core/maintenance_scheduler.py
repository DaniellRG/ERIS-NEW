"""
core/maintenance_scheduler.py — Mantenimiento PROACTIVO de ERIS.

Planifica tareas recurrentes (backups, limpieza de logs, reportes de salud)
que Eris agenda y ejecuta sola en un hilo, con estado persistente en
memory/maintenance.json. Tool `maintenance` para listar/gestionar/ejecutar.
"""
from __future__ import annotations

import os
import json
import shutil
import subprocess
import threading
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
STATE = BASE / "memory" / "maintenance.json"
REPORTS = BASE / "memory" / "maintenance_reports.md"
BACKUP_DIR = BASE / "backups"
VAULT = os.environ.get("ERIS_OBSIDIAN_VAULT", "")

_DAY = 86400
_WEEK = 7 * _DAY

_DEFAULTS = [
    {"name": "clean_logs", "kind": "builtin", "interval": _DAY, "last_run": 0, "enabled": True},
    {"name": "backup_workspace", "kind": "builtin", "interval": _WEEK, "last_run": 0, "enabled": True},
    {"name": "backup_vault", "kind": "builtin", "interval": _WEEK, "last_run": 0, "enabled": True,
     "note": "requiere ERIS_OBSIDIAN_VAULT"},
    {"name": "health_report", "kind": "builtin", "interval": _WEEK, "last_run": 0, "enabled": True},
]

_lock = threading.Lock()
_started = False


def _load() -> list[dict]:
    if STATE.exists():
        try:
            return json.loads(STATE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return _DEFAULTS.copy()


def _save(tasks: list[dict]):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(tasks, indent=2, ensure_ascii=False), encoding="utf-8")


def _append_report(text: str):
    REPORTS.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORTS, "a", encoding="utf-8") as f:
        f.write(f"\n## {time.strftime('%Y-%m-%d %H:%M')}\n{text}\n")


def _run_builtin(task: dict) -> str:
    name = task["name"]
    if name == "clean_logs":
        removed = 0
        for p in [BASE / "eris.log", (BASE / "data" / "logs"), (BASE / "memory" / "logs")]:
            if p.is_file():
                try:
                    if time.time() - p.stat().st_mtime > 14 * _DAY:
                        os.remove(str(p)); removed += 1
                except Exception:
                    pass
            elif p.is_dir():
                for f in p.glob("*.log*"):
                    try:
                        if time.time() - f.stat().st_mtime > 14 * _DAY:
                            os.remove(str(f)); removed += 1
                    except Exception:
                        pass
        t = " ".join(("eris.log" if x.name == "eris.log" else str(x)) for x in [BASE / "eris.log"] if x.exists())
        return f"Limpieza de logs: {removed} archivo(s) viejos (>14 días) {('(' + t + ')') if t else 'removidos'}"
    if name == "backup_workspace":
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d_%H%M")
        out = BACKUP_DIR / f"workspace_{stamp}.tar.gz"
        r = subprocess.run(
            ["tar", "-czf", str(out), "--exclude=.venv-linux", "--exclude=__pycache__",
             "--exclude=.git", "--exclude=backups", "."],
            cwd=BASE, capture_output=True, text=True, timeout=900)
        if r.returncode == 0:
            _prune(BACKUP_DIR, "workspace_*.tar.gz", 4)
            return f"Backup workspace → {out.name} ({out.stat().st_size//1024//1024} MB)"
        return f"Error tar: {r.stderr.strip()[:120]}"
    if name == "backup_vault":
        if not VAULT or not os.path.isdir(VAULT):
            task["note"] = "vault no disponible"
            return "Vault no disponible (falta ERIS_OBSIDIAN_VAULT)."
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d_%H%M")
        out = BACKUP_DIR / f"vault_{stamp}.tar.gz"
        r = subprocess.run(["tar", "-czf", str(out), "."], cwd=VAULT,
                           capture_output=True, text=True, timeout=1800)
        if r.returncode == 0:
            _prune(BACKUP_DIR, "vault_*.tar.gz", 4)
            return f"Backup vault → {out.name} ({out.stat().st_size//1024//1024} MB)"
        return f"Error tar vault: {r.stderr.strip()[:120]}"
    if name == "health_report":
        lines = []
        try:
            free = shutil.disk_usage(str(BASE))
            lines.append(f"Disco: {free.used//10**9}G usados de {free.total//10**9}G "
                         f"({100*free.used//free.total}%), libre {free.free//10**9}G")
        except Exception:
            pass
        try:
            r = subprocess.run(["free", "-h"], capture_output=True, text=True, timeout=10)
            r2 = subprocess.run(["uptime", "-p"], capture_output=True, text=True, timeout=10)
            lines.append(r.stdout.splitlines()[1] if r.stdout else "")
            lines.append("Activa desde: " + r2.stdout.strip() if r2.stdout else "")
        except Exception:
            pass
        cores = os.cpu_count()
        lines.append(f"CPU: {cores} núcleos")
        try:
            t = _load(); lines.append(f"Tareas de mantenimiento: {len([x for x in t if x['enabled']])} activas")
        except Exception:
            pass
        text = "\n".join(l for l in lines if l)
        _append_report(text)
        return "Reporte de salud generado → memory/maintenance_reports.md\n" + text
    return f"Tarea desconocida: {name}"


def _prune(folder: Path, pattern: str, keep: int):
    files = sorted(folder.glob(pattern), key=lambda f: f.stat().st_mtime, reverse=True)
    for f in files[keep:]:
        try:
            os.remove(str(f))
        except Exception:
            pass


def run_task(name: str) -> str:
    tasks = _load()
    for t in tasks:
        if t["name"] == name:
            if not t.get("enabled", True):
                return f"Tarea {name} deshabilitada."
            if t.get("kind") == "command":
                r = subprocess.run(str(t["cmd"]), shell=True, capture_output=True,
                                   text=True, timeout=t.get("timeout", 600), cwd=BASE)
                out = (r.stdout or "").strip()[:300]
                res = f"Comando: {(r.stderr or 'ok')[:200]}" if r.returncode != 0 else (out or "(ok)")
            else:
                res = _run_builtin(t)
            t["last_run"] = time.time()
            _save(tasks)
            return f"[{name}] ✓ {res}"
    return f"Tarea no encontrada: {name}. Usá list."


def maintenance(parameters: dict | None = None, player=None) -> str:
    """Mantenimiento proactivo. Acciones: list, run (name), run_all, add
    (name, interval, builtin|command), remove, status."""
    parameters = parameters or {}
    action = (parameters.get("action") or "list").lower()
    tasks = _load()

    if action in ("list", "lista"):
        if not tasks:
            return "Sin tareas."
        hours = {_DAY: "diaria", _WEEK: "semanal", 30 * _DAY: "mensual", _DAY // 12: "2h"}
        lines = []
        for t in tasks:
            interval = hours.get(t["interval"], f"cada {int(t['interval']//3600)}h")
            last = time.strftime("%d/%m %H:%M", time.localtime(t["last_run"])) if t["last_run"] else "nunca"
            state = "✅" if t.get("enabled", True) else "⏸"
            kind = ("bash:" + str(t["cmd"])[:30]) if t.get("kind") == "command" else t["name"]
            lines.append(f"{state} {t['name']:<16} {kind:<36} {interval:<8} última: {last}")
        return "Tareas de mantenimiento:\n" + "\n".join(lines)
    _save(tasks)

    if action in ("run", "ejecutar"):
        name = parameters.get("name") or parameters.get("task") or ""
        if not name:
            return "Falta 'name'."
        return run_task(name)

    if action in ("run_all", "todo"):
        out = []
        for t in tasks:
            if t.get("enabled", True):
                out.append(run_task(t["name"]))
        return "\n".join(out)

    if action in ("add", "agregar"):
        name = (parameters.get("name") or "").strip()
        interval = int(parameters.get("interval", _WEEK))
        builtin = (parameters.get("builtin") or "").strip()
        command = (parameters.get("command") or "").strip()
        if not name:
            return "Falta 'name'."
        if builtin and builtin in {t["name"] for t in _DEFAULTS}:
            tasks.append({"name": name, "kind": "builtin", "builtin_for": builtin,
                          "interval": interval, "last_run": 0, "enabled": True})
        elif command:
            tasks.append({"name": name, "kind": "command", "cmd": command,
                          "interval": interval, "last_run": 0, "enabled": True})
        else:
            return "Necesitás 'builtin' (clean_logs|backup_workspace|backup_vault|health_report) o 'command'."
        _save(tasks)
        return f"Tarea '{name}' agregada (cada {int(interval//3600)}h)."

    if action in ("remove", "borrar"):
        name = parameters.get("name") or parameters.get("task") or ""
        tasks = [t for t in tasks if t["name"] != name]
        _save(tasks)
        return f"Tarea '{name}' removida (si existía)."

    if action in ("status", "estado"):
        hilo = "activo" if _started else "inactivo"
        return (f"Estado: scheduler {hilo}\n"
                + maintenance({"action": "list"}))

    return ("Acciones: list, run (name), run_all, add (name, interval, "
            "builtin|command), remove (name), status.")


def maintenance_tick() -> list[str]:
    """Revisa tareas vencidas y las ejecuta. Devuelve resultados ejecutados."""
    tasks = _load()
    now = time.time()
    executed = []
    for t in tasks:
        if not t.get("enabled", True):
            continue
        if (now - t.get("last_run", 0)) >= t.get("interval", _WEEK):
            executed.append(run_task(t["name"]))
    return executed


def start_maintenance_scheduler(interval: float = 60.0) -> threading.Thread:
    """Hilo daemon: cada `interval` segundos corre mantenimiento_tick()."""
    global _started
    if _started:
        with _lock:
            if _started:
                return None
    with _lock:
        _started = True
    _save(_load())

    def _loop():
        while True:
            time.sleep(interval)
            try:
                done = maintenance_tick()
                if done:
                    print(f"[ERIS] 🧰 Mantenimiento: {len(done)} tarea(s) ejecutada(s)")
            except Exception:
                pass

    t = threading.Thread(target=_loop, daemon=True)
    t.start()
    return t