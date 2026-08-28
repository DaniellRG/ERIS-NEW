# -*- coding: utf-8 -*-
"""
eris_guardian.py — El Guardian de ERIS.

El fragmento de ERIS que cuida de ERIS en todo momento:

  VIGILA   → analiza continuamente el codigo, los logs y la salud del sistema
  REPARA   → corrige archivos rotos (con backup + validacion + rollback)
  EVOLUCIONA → propone y aplica mejoras, aprende de errores, adopta ideas nuevas
  APRENDE  → registra cada accion en un diario y guarda lecciones
  OBSERVA  → vigila actualizaciones / tecnologias nuevas

Ciclo agetico del Guardian:
  Escanear → Diagnosticar → Reparar → Validar → Registrar → Aprender

Seguridad: NUNCA se modifica un archivo sin backup previo, y todo cambio se
valida (sintaxis + AST) antes y despues de aplicar. Si algo falla, se hace
rollback automatico al backup.
"""
from __future__ import annotations

import ast
import json
import os
import py_compile
import shutil
import subprocess
import sys
import threading
import time
import traceback
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
BACKUP_DIR = BASE_DIR / "backups"
STATE_FILE = DATA_DIR / "guardian_state.json"
JOURNAL_FILE = DATA_DIR / "guardian_journal.json"
LOG_FILE = BASE_DIR / "eris.log"
HEALTH_PORT = 8765
MAX_JOURNAL = 500

PYTHON = sys.executable

# Directorios/archivos que el Guardian jamas toca
_EXCLUDE_PARTS = {"__pycache__", ".venv", "venv", "site-packages", "node_modules",
                  ".git", "backups", "dist", "build", "lib", "share", ".next"}
_CRITICAL_FILES = {"main.py", "run.py", "ui.py"}
_SKIP_LOOPS = {"eris_guardian.py", "self_healing_loop.py", "self_edit.py",
               "self_modify.py", "self_improvement_loop.py", "self_heal.py",
               "self_evolution.py", "updater.py"}

_lock = threading.RLock()
_state = None
_monitor_thread = None
_monitor_running = False


# ── JSON helpers ──────────────────────────────────────────────────────────────

def _load_json(path, default=None):
    try:
        if path.exists():
            return json.loads(path.read_text("utf-8"))
    except Exception:
        pass
    return default if default is not None else {}


def _save_json(path, data):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), "utf-8")
    except Exception:
        pass


# ── Estado y diario ───────────────────────────────────────────────────────────

def _default_state():
    return {
        "created": datetime.now().isoformat(),
        "last_scan": None,
        "last_fix": None,
        "last_evolution": None,
        "scans": 0,
        "files_scanned": 0,
        "issues_found": 0,
        "files_fixed": 0,
        "fixes_failed": 0,
        "proposals_made": 0,
        "lessons": 0,
        "monitor_active": False,
        "interval": 600,
    }


def _get_state():
    global _state
    with _lock:
        if _state is None:
            _state = _load_json(STATE_FILE) or _default_state()
            # rellenar campos faltantes
            base = _default_state()
            base.update(_state)
            _state = base
        return _state


def _save_state():
    with _lock:
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            STATE_FILE.write_text(json.dumps(_get_state(), indent=2, ensure_ascii=False), "utf-8")
        except Exception:
            pass


def _log(msg: str, level: str = "INFO"):
    """Registra una accion del Guardian en el diario."""
    try:
        entries = _load_json(JOURNAL_FILE, [])
        if not isinstance(entries, list):
            entries = []
        entries.append({
            "time": datetime.now().isoformat(),
            "level": level,
            "msg": str(msg)[:400],
        })
        if len(entries) > MAX_JOURNAL:
            entries = entries[-MAX_JOURNAL:]
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        JOURNAL_FILE.write_text(json.dumps(entries, indent=2, ensure_ascii=False), "utf-8")
    except Exception:
        pass


def _learn(lesson: str, category: str = "general"):
    """Registra una leccion aprendida (evita duplicados consecutivos)."""
    st = _get_state()
    lessons = st.get("lessons_list", [])
    if lessons and lessons[-1].get("lesson") == lesson:
        return
    lessons.append({
        "time": datetime.now().isoformat(),
        "category": category,
        "lesson": str(lesson)[:300],
    })
    if len(lessons) > 100:
        lessons = lessons[-100:]
    st["lessons_list"] = lessons
    st["lessons"] = len(lessons)
    _save_state()


# ── Exploracion del proyecto ─────────────────────────────────────────────────

def _iter_project_py():
    """Itera todos los .py del proyecto, excluyendo caches/entornos/backups."""
    for py_file in BASE_DIR.rglob("*.py"):
        s = str(py_file)
        if any(x in s for x in _EXCLUDE_PARTS):
            continue
        yield py_file


def _safe_rel(fp: Path) -> str:
    try:
        return str(fp.relative_to(BASE_DIR))
    except ValueError:
        return str(fp)


# ── Diagnostico ───────────────────────────────────────────────────────────────

def _syntax_check(fp: Path) -> tuple[bool, str]:
    try:
        py_compile.compile(str(fp), doraise=True)
        return True, "OK"
    except py_compile.PyCompileError as e:
        return False, str(e)[:300]


def _ast_issues(fp: Path) -> list[dict]:
    """Analisis AST basico: excepts desnudos y nombres indefinidos obvios."""
    issues = []
    try:
        source = fp.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except Exception:
        return issues
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            issues.append({"type": "bare_except", "line": node.lineno,
                           "message": "except desnudo (captura todo)"})
    return issues


def _detect_issues(fp: Path) -> list[dict]:
    issues = []
    ok, msg = _syntax_check(fp)
    if not ok:
        issues.append({"type": "syntax_error", "line": "?",
                       "message": msg, "severity": "CRITICAL"})
    for a in _ast_issues(fp):
        a["severity"] = "WARNING"
        issues.append(a)
    return issues


def _scan_all(target: str = None) -> dict:
    """Escaneo: sintaxis de todos los .py + analisis AST (o de un solo archivo)."""
    results = {"ok": 0, "issues": [], "fixed": []}
    if target:
        fp = Path(target)
        if not fp.is_absolute():
            fp = BASE_DIR / target
        files = [fp] if fp.exists() else []
    else:
        files = list(_iter_project_py())
    for fp in files:
        rel = _safe_rel(fp)
        if Path(rel).name in _SKIP_LOOPS:
            results["ok"] += 1
            continue
        issues = _detect_issues(fp)
        if issues:
            results["issues"].append({"file": rel, "issues": issues})
        else:
            results["ok"] += 1
    st = _get_state()
    st["scans"] = st.get("scans", 0) + 1
    st["last_scan"] = datetime.now().isoformat()
    st["files_scanned"] = st.get("files_scanned", 0) + len(files)
    st["issues_found"] = st.get("issues_found", 0) + len(results["issues"])
    _save_state()
    return results


def _scan_logs(max_lines: int = 200) -> list[dict]:
    """Busca errores recientes en eris.log."""
    if not LOG_FILE.exists():
        return []
    try:
        lines = LOG_FILE.read_text("utf-8", errors="replace").splitlines()
    except Exception:
        return []
    lines = [l for l in lines if l.strip()][-max_lines:]
    patterns = {
        "traceback": "Traceback",
        "import_error": "ModuleNotFoundError",
        "key_error": "KeyError",
        "attribute_error": "AttributeError",
        "type_error": "TypeError",
        "value_error": "ValueError",
        "connection": "ConnectionResetError",
        "timeout": "timed out",
    }
    found = []
    for i, line in enumerate(lines):
        for etype, token in patterns.items():
            if token in line:
                found.append({
                    "type": etype,
                    "line": line[:200],
                    "context": "\n".join(l[:160] for l in lines[max(0, i - 4):i])[-300:],
                    "time": time.time(),
                })
                break
    return found


# ── Salud del sistema ─────────────────────────────────────────────────────────

def _probe_health() -> dict:
    h = {"port8765": False, "ollama": False, "chromadb": False}
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{HEALTH_PORT}/health", timeout=4) as r:
            h["port8765"] = r.status == 200
    except Exception:
        pass
    try:
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=3) as r:
            h["ollama"] = r.status == 200
    except Exception:
        pass
    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(DATA_DIR / "chroma_db"))
        client.list_collections()
        h["chromadb"] = True
    except Exception:
        pass
    return h


# ── Reparacion ────────────────────────────────────────────────────────────────

def _backup(fp: Path) -> str:
    """Copia de seguridad antes de modificar. Devuelve la ruta del backup."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe = str(fp).replace(str(BASE_DIR), "").replace(os.sep, "__").replace("/", "__").lstrip("_")
    bak = BACKUP_DIR / f"guardian_{safe}.{ts}.bak"
    shutil.copy2(fp, bak)
    return str(bak)


def _deterministic_fix(fp: Path) -> tuple[bool, str]:
    """Arreglos simples y seguros: delimitadores sin cerrar, salto de linea final.

    Solo se aplica si el archivo queda valido; si no, se restaura el original.
    """
    try:
        content = fp.read_text(encoding="utf-8")
    except Exception as e:
        return False, f"No se pudo leer: {e}"
    original = content
    fixed = False

    for open_c, close_c in [("(", ")"), ("[", "]"), ("{", "}")]:
        if content.count(open_c) > content.count(close_c):
            content += close_c * (content.count(open_c) - content.count(close_c))
            fixed = True
    if content and not content.endswith("\n"):
        content += "\n"
        fixed = True

    if not fixed:
        return False, "Sin arreglos deterministicos aplicables"

    backup = _backup(fp)
    try:
        fp.write_text(content, encoding="utf-8")
    except Exception as e:
        return False, f"No se pudo escribir: {e}"

    ok, msg = _syntax_check(fp)
    if not ok:
        try:
            fp.write_text(original, encoding="utf-8")
        except Exception:
            pass
        return False, f"El arreglo no valido, rollback aplicado: {msg}"
    return True, f"Arreglo deterministico aplicado (backup: {Path(backup).name})"


def _llm_available() -> bool:
    try:
        from actions.ollama_provider import is_available
        return bool(is_available())
    except Exception:
        return False


def _llm_fix(fp: Path, issues: list[dict]) -> tuple[bool, str, str]:
    """Genera un arreglo via LLM local (Ollama) para un archivo con errores.

    Devuelve (ok, mensaje, codigo_candidato).
    """
    try:
        from actions.ollama_provider import chat
    except Exception:
        return False, "Ollama no disponible", ""
    try:
        current = fp.read_text(encoding="utf-8")
    except Exception as e:
        return False, f"No se pudo leer: {e}", ""
    if len(current) > 12000:
        return False, "Archivo muy grande para arreglo LLM automatico", ""

    summary = "\n".join(
        f"  [{i.get('severity', '?')}] L{i.get('line', '?')}: {i.get('type', '?')} — {i.get('message', '')}"
        for i in issues
    )
    system = (
        "Sos el Guardian de ERIS. Corregi SOLO los errores indicados del archivo Python. "
        "Respetá la funcionalidad original y el estilo del archivo. "
        "Respondé EXCLUSIVAMENTE con el código completo corregido, sin markdown ni explicaciones."
    )
    prompt = (
        f"Archivo: {_safe_rel(fp)}\n\n"
        f"Errores detectados:\n{summary}\n\n"
        f"Código actual:\n```python\n{current}\n```\n\n"
        f"Entregá el código corregido completo:"
    )
    candidate = chat(prompt=prompt, system=system, temperature=0.1, max_tokens=4096)
    if not candidate or len(candidate.strip()) < 10:
        return False, "El LLM no devolvio codigo", ""
    candidate = candidate.strip()
    if candidate.startswith("```"):
        candidate = candidate.split("```", 2)[1]
        if candidate.startswith("python"):
            candidate = candidate[len("python"):]
        candidate = candidate.strip()
    return True, "Arreglo LLM generado", candidate


def _validate_candidate(candidate: str) -> tuple[bool, str]:
    try:
        ast.parse(candidate)
        return True, "AST OK"
    except SyntaxError as e:
        return False, f"Error de sintaxis: {e}"


def _apply_candidate(fp: Path, candidate: str) -> tuple[bool, str]:
    """Valida y aplica el codigo candidato con backup y rollback si falla."""
    ok, msg = _validate_candidate(candidate)
    if not ok:
        return False, f"Rechazado: {msg}"
    backup = _backup(fp)
    try:
        fp.write_text(candidate, encoding="utf-8")
    except Exception as e:
        return False, f"No se pudo escribir: {e}"
    ok2, msg2 = _syntax_check(fp)
    if not ok2:
        try:
            shutil.copy2(backup, fp)
        except Exception:
            pass
        return False, f"Post-validacion fallo, rollback: {msg2}"
    return True, f"Aplicado (backup: {Path(backup).name})"


def _fix_file(file_ref: str, use_llm: bool = True) -> str:
    """Repara un archivo: deterministico primero, luego LLM si hace falta."""
    fp = (BASE_DIR / file_ref) if not Path(file_ref).is_absolute() else Path(file_ref)
    if not fp.exists():
        return f"Archivo no encontrado: {file_ref}"

    ok, _ = _syntax_check(fp)
    issues = [] if ok else [{"type": "syntax_error", "line": "?", "message": "sintaxis rota", "severity": "CRITICAL"}]
    issues += _ast_issues(fp)

    if ok and not issues:
        return f"{file_ref}: sin problemas detectados."

    # 1) Intento deterministico
    det_ok, det_msg = _deterministic_fix(fp)
    if det_ok:
        ok2, _ = _syntax_check(fp)
        if ok2:
            st = _get_state()
            st["files_fixed"] = st.get("files_fixed", 0) + 1
            st["last_fix"] = datetime.now().isoformat()
            _save_state()
            _log(f"REPARADO {file_ref}: {det_msg}", "FIX")
            _learn(f"Arreglo deterministico en {file_ref}: {det_msg}", "fix")
            return f"REPARADO: {file_ref}\n{det_msg}"

    # 2) Intento LLM
    if use_llm and _llm_available():
        issues_now = _detect_issues(fp)
        if issues_now:
            ok3, msg3, candidate = _llm_fix(fp, issues_now)
            if ok3:
                app_ok, app_msg = _apply_candidate(fp, candidate)
                if app_ok:
                    st = _get_state()
                    st["files_fixed"] = st.get("files_fixed", 0) + 1
                    st["last_fix"] = datetime.now().isoformat()
                    _save_state()
                    _log(f"REPARADO {file_ref} (LLM): {app_msg}", "FIX")
                    _learn(f"Arreglo LLM en {file_ref}", "fix")
                    return f"REPARADO (LLM): {file_ref}\n{app_msg}"
                return f"NO REPARADO: {file_ref}\n{app_msg}"

    st = _get_state()
    st["fixes_failed"] = st.get("fixes_failed", 0) + 1
    _save_state()
    _log(f"REPARACION FALLIDA: {file_ref}", "ERROR")
    return f"NO PUDE REPARAR: {file_ref}\nNo hay arreglo deterministico ni LLM disponible."


def _fix_all(auto: bool = True) -> str:
    """Escanea todo y repara los archivos rotos."""
    scan = _scan_all()
    broken = scan["issues"]
    if not broken:
        _log("ESCANEO completo: todo saludable", "INFO")
        return "Escaneo completo: no hay archivos rotos."

    lines = [f"Archivos con problemas: {len(broken)}"]
    fixed_list = []
    failed_list = []
    for item in broken:
        rel = item["file"]
        critical = any(i.get("severity") == "CRITICAL" for i in item["issues"])
        if Path(rel).name in _CRITICAL_FILES:
            lines.append(f"  CRITICO (no toco): {rel} → {item['issues'][0]['message'][:80]}")
            failed_list.append(rel)
            continue
        if not auto:
            lines.append(f"  Pendiente: {rel} ({len(item['issues'])} problemas)")
            continue
        result = _fix_file(rel)
        if result.startswith("REPARADO"):
            fixed_list.append(rel)
            lines.append(f"  REPARADO: {result.replace(chr(10), ' ')[:120]}")
        else:
            failed_list.append(rel)
            lines.append(f"  FALLO: {rel}")

    _log(f"ESCANEO/REPARACION: {len(broken)} con problemas, {len(fixed_list)} reparados, {len(failed_list)} sin reparar")
    return "\n".join(lines)


# ── Evolucion ─────────────────────────────────────────────────────────────────

def _propose_improvements(topic: str = "", use_llm: bool = True) -> list[dict]:
    """Genera propuestas de mejora a partir de logs y (si hay) LLM."""
    proposals = []
    errors = _scan_logs()
    counts = {}
    for e in errors:
        counts[e["type"]] = counts.get(e["type"], 0) + 1

    for etype, count in counts.items():
        if count >= 2:
            proposals.append({
                "type": "error_pattern",
                "title": f"Error recurrente '{etype}' ({count} veces)",
                "detail": "Revisar el flujo que lo dispara y blindarlo.",
            })

    # Propuesta por tamaño de log
    try:
        if LOG_FILE.exists() and LOG_FILE.stat().st_size > 50 * 1024 * 1024:
            proposals.append({
                "type": "maintenance",
                "title": "eris.log demasiado grande",
                "detail": "Rotar o limpiar eris.log para liberar espacio.",
            })
    except Exception:
        pass

    # Propuestas via LLM si se pide y esta disponible
    if use_llm and _llm_available():
        try:
            from actions.ollama_provider import chat
            system = (
                "Sos el Guardian de ERIS. Proponé mejoras concretas y accionables "
                "para el codigo de ERIS (estructura, robustez, rendimiento, features). "
                "Respondé SOLO con una lista numerada de 1 a 4 mejoras, cada una en una linea: "
                "'Mejora - archivo o area - accion concreta'."
            )
            prompt = (
                f"Tema sugerido: {topic or 'mejoras generales de robustez'}\n"
                f"Errores recientes: {[e['type'] for e in errors[-10:]] or 'ninguno'}\n\n"
                f"Proponé mejoras:"
            )
            raw = chat(prompt=prompt, system=system, temperature=0.5, max_tokens=800)
            for line in raw.splitlines():
                line = line.strip()
                if not line or len(line) < 10:
                    continue
                proposals.append({
                    "type": "llm_idea",
                    "title": line[:120],
                    "detail": line,
                })
        except Exception:
            pass

    st = _get_state()
    st["proposals_made"] = st.get("proposals_made", 0) + len(proposals)
    st["last_evolution"] = datetime.now().isoformat()
    st["proposals"] = proposals[-20:]
    _save_state()
    _log(f"EVOLUCION: {len(proposals)} propuesta(s) generadas")
    return proposals


# ── Observacion (tecnologias / updates) ───────────────────────────────────────

def _check_updates() -> dict | None:
    try:
        from core.updater import check_for_update
        return check_for_update()
    except Exception:
        return None


# ── Reinicio ──────────────────────────────────────────────────────────────────

def _restart_eris() -> str:
    """Mata los procesos ERIS de este proyecto y relanza run.py directamente."""
    import psutil
    killed = 0
    my_pid = os.getpid()
    try:
        for proc in psutil.process_iter(["pid", "cmdline"]):
            try:
                pid = proc.info["pid"]
                if pid == my_pid:
                    continue
                cmd = " ".join(proc.info["cmdline"] or [])
                if "run.py" in cmd and str(BASE_DIR) in cmd:
                    proc.kill()
                    killed += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except Exception as e:
        return f"No pude reiniciar: {e}"

    time.sleep(2)
    try:
        subprocess.Popen(
            [PYTHON, str(BASE_DIR / "run.py")],
            cwd=str(BASE_DIR),
            creationflags=0x08000010,  # CREATE_NO_WINDOW | DETACHED_PROCESS
        )
        _log(f"REINICIO: {killed} proceso(s) terminados, run.py relanzado")
        return f"Reinicio: {killed} proceso(s) terminados y run.py relanzado."
    except Exception as e:
        return f"Termine {killed} proceso(s) pero no pude relanzar: {e}"


# ── Ciclo del Guardian (una pasada) ───────────────────────────────────────────

def guardian_tick(repair: bool = True) -> dict:
    """Una pasada completa: salud + escaneo + reparacion automatica + aprendizaje."""
    tick = {
        "time": datetime.now().isoformat(),
        "health": _probe_health(),
        "errors_in_logs": len(_scan_logs()),
        "issues": 0,
        "fixed": 0,
    }
    scan = _scan_all()
    tick["issues"] = len(scan["issues"])

    if repair and scan["issues"]:
        for item in scan["issues"]:
            rel = item["file"]
            if Path(rel).name in _CRITICAL_FILES:
                continue
            if _syntax_check(BASE_DIR / rel)[0]:
                continue
            try:
                _fix_file(rel, use_llm=False)
                tick["fixed"] += 1
            except Exception:
                pass

    # Aprender si hay problemas que no se pudieron arreglar solos
    remaining = [i for i in scan["issues"] if _syntax_check(BASE_DIR / i["file"])[0] is False]
    if remaining:
        _learn(
            f"Quedan {len(remaining)} archivo(s) con sintaxis rota sin arreglo automatico: "
            + ", ".join(r["file"] for r in remaining[:5]),
            category="needs_attention",
        )

    _log(f"CICLO: salud {tick['health']}, {tick['issues']} problemas, {tick['fixed']} reparados")
    return tick


# ── Monitor de fondo ──────────────────────────────────────────────────────────

def start_monitor(interval: int = 600, initial_delay: int = 20) -> bool:
    """Arranca el loop de fondo del Guardian (thread daemon)."""
    global _monitor_thread, _monitor_running
    with _lock:
        if _monitor_running:
            return False
        _monitor_running = True

    def _loop():
        time.sleep(initial_delay)
        while _monitor_running:
            try:
                guardian_tick(repair=True)
            except Exception:
                _log(f"Fallo en ciclo del Guardian: {traceback.format_exc()[-300:]}", "ERROR")
            try:
                # Rotacion de log leve si crecio mucho
                if LOG_FILE.exists() and LOG_FILE.stat().st_size > 100 * 1024 * 1024:
                    backup_log = BASE_DIR / "backups" / f"eris_rotated_{datetime.now():%Y%m%d_%H%M%S}.log"
                    try:
                        shutil.copy2(LOG_FILE, backup_log)
                        LOG_FILE.write_text("")
                        _log(f"eris.log rotado ({Path(backup_log).name})")
                    except Exception:
                        pass
            except Exception:
                pass
            time.sleep(max(60, int(interval)))

    _monitor_thread = threading.Thread(target=_loop, daemon=True, name="ERIS-Guardian")
    _monitor_thread.start()

    st = _get_state()
    st["monitor_active"] = True
    st["interval"] = int(interval)
    _save_state()
    _log(f"Monitor del Guardian activado (intervalo {interval}s)")
    return True


def stop_monitor() -> bool:
    global _monitor_running
    with _lock:
        _monitor_running = False
    st = _get_state()
    st["monitor_active"] = False
    _save_state()
    _log("Monitor del Guardian detenido")
    return True


def get_guardian_status() -> str:
    """Reporte de estado del Guardian."""
    st = _get_state()
    lines = [
        "=" * 48,
        "  EL GUARDIAN DE ERIS",
        "=" * 48,
        "",
        f"  Monitor de fondo: {'ACTIVO' if st.get('monitor_active') else 'APAGADO'} "
        f"(intervalo {st.get('interval', 600)}s)",
        f"  Escaneos realizados: {st.get('scans', 0)}",
        f"  Archivos escaneados: {st.get('files_scanned', 0)}",
        f"  Problemas detectados: {st.get('issues_found', 0)}",
        f"  Archivos reparados: {st.get('files_fixed', 0)}",
        f"  Reparaciones fallidas: {st.get('fixes_failed', 0)}",
        f"  Propuestas de evolucion: {st.get('proposals_made', 0)}",
        f"  Lecciones aprendidas: {st.get('lessons', 0)}",
        "",
        f"  Ultimo escaneo: {st.get('last_scan', 'nunca')}",
        f"  Ultima reparacion: {st.get('last_fix', 'nunca')}",
        f"  Ultima evolucion: {st.get('last_evolution', 'nunca')}",
    ]

    lessons = st.get("lessons_list", [])
    if lessons:
        lines.append("")
        lines.append("  Ultimas lecciones:")
        for l in lessons[-3:]:
            lines.append(f"    • [{l.get('category', '?')}] {l.get('lesson', '')[:90]}")
    return "\n".join(lines)


# ── Tool ──────────────────────────────────────────────────────────────────────

def eris_guardian(parameters: dict = None, player=None) -> str:
    """El Guardian de ERIS: vigila, repara, evoluciona y aprende."""
    if parameters is None:
        parameters = {}
    action = (parameters.get("action") or "status").lower().strip()

    if player:
        try:
            player.write_log("Guardian: {}".format(action))
        except Exception:
            pass

    # ── STATUS / REPORT ──
    if action in ("status", "report"):
        out = get_guardian_status()
        health = _probe_health()
        out += "\n\n  Salud del sistema:"
        out += f"\n    Endpoint 8765: {'OK' if health['port8765'] else 'DOWN'}"
        out += f"\n    Ollama: {'OK' if health['ollama'] else 'DOWN'}"
        out += f"\n    ChromaDB: {'OK' if health['chromadb'] else 'DOWN'}"
        update = _check_updates()
        if update:
            out += f"\n    Actualizacion disponible: v{update['version']} (actual v{update['current']})"
        return out

    # ── SCAN ──
    elif action in ("scan", "scan_all"):
        target = (parameters.get("target") or "").strip()
        repair = bool(parameters.get("repair", True))
        scan = _scan_all(target or None)
        issues = scan["issues"]
        if not issues:
            scope = f" ({target})" if target else ""
            _log("ESCANEO: todo saludable" + scope, "INFO")
            return f"Escaneo completo{scope}: todo saludable."
        if target and repair:
            fixes = []
            for item in issues:
                fix_res = _fix_file(item["file"], use_llm=False)
                fixes.append(fix_res)
            return "\n".join(fixes)
        lines = [f"Escaneo completo: {scan['ok']} sanos, {len(issues)} con problemas"]
        for item in issues[:20]:
            first = item["issues"][0]
            lines.append(f"  {item['file']}: [{first.get('severity', '?')}] {first.get('message', '')[:90]}")
        if len(issues) > 20:
            lines.append(f"  ... y {len(issues) - 20} mas")
        return "\n".join(lines)

    # ── FIX / REPAIR ──
    elif action in ("fix", "repair"):
        file_ref = (parameters.get("file") or parameters.get("target") or "").strip()
        if not file_ref:
            return _fix_all(auto=parameters.get("auto", True))
        return _fix_file(file_ref)

    # ── EVOLVE ──
    elif action in ("evolve", "propose"):
        topic = (parameters.get("topic") or "").strip()
        proposals = _propose_improvements(topic)
        if not proposals:
            return "No se generaron propuestas de evolucion."
        lines = [f"Propuestas de evolucion ({len(proposals)}):"]
        for i, p in enumerate(proposals, 1):
            lines.append(f"  {i}. [{p.get('type', '?')}] {p.get('title', '')[:120]}")
        return "\n".join(lines)

    # ── WATCH (actualizaciones/tecnologias) ──
    elif action in ("watch", "updates", "update"):
        update = _check_updates()
        lines = ["Observador de tecnologias / updates:"]
        if update:
            lines.append(f"  Nueva version: {update['version']} (actual: {update['current']})")
            lines.append(f"  Notas: {update['notes'][:200]}")
            lines.append(f"  Tamano: {update['size_mb']} MB")
        else:
            lines.append("  Sin actualizaciones nuevas de GitHub.")
        lines.append(f"  Python: {sys.version.split()[0]}")
        try:
            import psutil
            lines.append(f"  CPU: {psutil.cpu_percent(interval=0.5)}% | Mem: {psutil.virtual_memory().percent}%")
        except Exception:
            pass
        return "\n".join(lines)

    # ── MONITOR ──
    elif action in ("monitor", "start", "stop"):
        mode = (parameters.get("mode") or parameters.get("action") or "").strip()
        if mode in ("stop", "off", "apagar"):
            stop_monitor()
            return "Monitor del Guardian apagado."
        interval = int(parameters.get("interval") or 600)
        started = start_monitor(interval=interval)
        return f"Monitor del Guardian {'arrancado' if started else 'ya estaba activo'} (cada {interval}s)."

    # ── TICK (una pasada manual) ──
    elif action == "tick":
        t = guardian_tick(repair=parameters.get("repair", True))
        return (f"Ciclo del Guardian completado.\n"
                f"  Salud: {t['health']}\n"
                f"  Errores en logs: {t['errors_in_logs']}\n"
                f"  Problemas: {t['issues']}\n"
                f"  Reparados: {t['fixed']}")

    # ── LOGS / JOURNAL ──
    elif action in ("history", "log", "logs", "journal"):
        entries = _load_json(JOURNAL_FILE, [])
        if not isinstance(entries, list) or not entries:
            return "El diario del Guardian esta vacio."
        limit = int(parameters.get("limit") or 10)
        lines = [f"Diario del Guardian ({len(entries)} entradas):"]
        for e in entries[-limit:]:
            lines.append(f"  [{e.get('time', '?')[:19]}] [{e.get('level', '?')}] {e.get('msg', '')[:120]}")
        return "\n".join(lines)

    # ── RESTART ──
    elif action in ("restart", "reiniciar"):
        return _restart_eris()

    # ── HELP ──
    else:
        return (
            "EL GUARDIAN DE ERIS — vigila, repara, evoluciona y aprende.\n\n"
            "Acciones:\n"
            "  status      — Reporte de estado del Guardian + salud del sistema\n"
            "  scan        — Escaneo completo del codigo de ERIS (target=archivo, repair=false)\n"
            "  fix/repair  — Repara un archivo (file=.../target=...) o todos si no se pasa\n"
            "  evolve      — Genera propuestas de mejora (topic=... opcional)\n"
            "  watch       — Observa updates / estado de recursos\n"
            "  monitor     — Activa el monitor de fondo (interval=600 por defecto)\n"
            "  monitor mode=stop — Apaga el monitor\n"
            "  tick        — Ejecuta un ciclo completo manual\n"
            "  history/journal — Diario de acciones del Guardian\n"
            "  restart     — Reinicia ERIS"
        )


# Singleton del Guardian
_guardian = None


def get_guardian():
    global _guardian
    if _guardian is None:
        _guardian = eris_guardian
    return _guardian
