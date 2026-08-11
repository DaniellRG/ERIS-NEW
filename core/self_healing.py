"""
core/self_healing.py — Auto-healing, auto-learning, self-maintenance for ERIS.
Detects errors, auto-fixes, auto-restarts, auto-learns from mistakes.
"""
from __future__ import annotations

import json
import os
import sys
import time
import traceback
import threading
import py_compile
from pathlib import Path
from datetime import datetime

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_SELF_HEAL_FILE = _DATA_DIR / "self_healing_state.json"
_ERROR_LOG = _DATA_DIR / "self_healing_errors.json"
_LEARNING_LOG = _DATA_DIR / "self_learning_log.json"


class SelfHealingSystem:
    """Monitors ERIS health, auto-detects errors, auto-fixes, auto-learns."""

    def __init__(self):
        self._state = self._load_state()
        self._error_count = 0
        self._fix_count = 0
        self._learning_count = 0
        self._lock = threading.Lock()
        self._running = False
        self._thread = None

    def _load_state(self) -> dict:
        try:
            if _SELF_HEAL_FILE.exists():
                return json.loads(_SELF_HEAL_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
        return {
            "total_errors": 0,
            "total_fixes": 0,
            "total_restarts": 0,
            "total_learning": 0,
            "last_check": None,
            "last_fix": None,
            "last_error": None,
            "known_errors": {},
        }

    def _save_state(self):
        try:
            _DATA_DIR.mkdir(parents=True, exist_ok=True)
            self._state["last_check"] = datetime.now().isoformat()
            _SELF_HEAL_FILE.write_text(json.dumps(self._state, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    def _log_error(self, error_type: str, message: str, traceback_str: str = ""):
        """Log an error for learning."""
        try:
            errors = []
            if _ERROR_LOG.exists():
                errors = json.loads(_ERROR_LOG.read_text(encoding="utf-8"))
            errors.append({
                "type": error_type,
                "message": message[:500],
                "traceback": traceback_str[:1000],
                "time": datetime.now().isoformat(),
            })
            if len(errors) > 500:
                errors = errors[-500:]
            _ERROR_LOG.write_text(json.dumps(errors, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    def _log_learning(self, action: str, detail: str):
        """Log a learning event (deduplica entradas idénticas consecutivas)."""
        try:
            logs = []
            if _LEARNING_LOG.exists():
                logs = json.loads(_LEARNING_LOG.read_text(encoding="utf-8"))
            detail = detail[:500]
            # No repetir la misma entrada consecutiva (evita spam de ollama_down)
            if logs and logs[-1].get("action") == action and logs[-1].get("detail") == detail:
                return
            logs.append({
                "action": action,
                "detail": detail,
                "time": datetime.now().isoformat(),
            })
            if len(logs) > 200:
                logs = logs[-200:]
            _LEARNING_LOG.write_text(json.dumps(logs, indent=2, ensure_ascii=False), encoding="utf-8")
            self._learning_count += 1
        except Exception:
            pass

    def check_syntax(self, file_path: str) -> tuple[bool, str]:
        """Check Python file syntax."""
        try:
            py_compile.compile(file_path, doraise=True)
            return True, "OK"
        except py_compile.PyCompileError as e:
            return False, str(e)[:200]

    def auto_fix_syntax(self, file_path: str) -> bool:
        """Attempt auto-fix for common syntax errors."""
        try:
            content = Path(file_path).read_text(encoding="utf-8")
            original = content
            fixed = False
            # Fix 1: unclosed parentheses
            for open_c, close_c in [("(", ")"), ("[", "]"), ("{", "}")]:
                if content.count(open_c) > content.count(close_c):
                    content += close_c * (content.count(open_c) - content.count(close_c))
                    fixed = True
            # Fix 2: missing trailing newline
            if content and not content.endswith("\n"):
                content += "\n"
                fixed = True
            if fixed:
                Path(file_path).write_text(content, encoding="utf-8")
                ok, msg = self.check_syntax(file_path)
                if ok:
                    self._log_learning("auto_fix_syntax", "Fixed: {}".format(file_path))
                    return True
                else:
                    Path(file_path).write_text(original, encoding="utf-8")
            return False
        except Exception:
            return False

    def _iter_project_py(self):
        """Yield project .py files, excluding caches and .venv/site-packages."""
        src = Path(__file__).resolve().parent.parent
        for py_file in src.rglob("*.py"):
            s = str(py_file)
            if any(x in s for x in ("__pycache__", "backups", ".venv", "site-packages", "node_modules", ".git")):
                continue
            yield py_file

    def check_all_modules(self) -> dict:
        """Scan all Python files for syntax errors."""
        results = {"ok": [], "errors": [], "fixed": []}
        for py_file in self._iter_project_py():
            ok, msg = self.check_syntax(str(py_file))
            if ok:
                results["ok"].append(str(py_file.name))
            else:
                if self.auto_fix_syntax(str(py_file)):
                    results["fixed"].append(str(py_file.name))
                else:
                    results["errors"].append({"file": str(py_file.name), "error": msg})
        return results

    def check_ollama(self) -> bool:
        """Check if Ollama is running."""
        try:
            import urllib.request
            resp = urllib.request.urlopen("http://localhost:11434/api/tags", timeout=3)
            resp.close()
            return True
        except Exception:
            return False

    def check_chromadb(self) -> bool:
        """Check if ChromaDB is accessible."""
        try:
            import chromadb
            client = chromadb.PersistentClient(path=str(_DATA_DIR / "chroma_db"))
            client.list_collections()
            return True
        except Exception:
            return False

    def health_check(self) -> dict:
        """Full system health check."""
        health = {
            "time": datetime.now().isoformat(),
            "ollama": self.check_ollama(),
            "chromadb": self.check_chromadb(),
            "syntax": self.check_all_modules(),
            "errors_total": self._state.get("total_errors", 0),
            "fixes_total": self._state.get("total_fixes", 0),
            "restarts_total": self._state.get("total_restarts", 0),
            "learning_total": self._state.get("total_learning", 0),
        }
        return health

    def handle_error(self, error_type: str, error_msg: str, tb: str = "") -> str:
        """Handle an error — log it, try to fix it, learn from it."""
        with self._lock:
            self._error_count += 1
            self._state["total_errors"] = self._state.get("total_errors", 0) + 1
            self._state["last_error"] = {
                "type": error_type,
                "message": error_msg[:200],
                "time": datetime.now().isoformat(),
            }
            self._log_error(error_type, error_msg, tb)
            known = self._state.get("known_errors", {})
            count = known.get(error_type, 0) + 1
            known[error_type] = count
            self._state["known_errors"] = known
            if count >= 3:
                self._log_learning("recurring_error", "Error recurrente: {}".format(error_type))
            self._save_state()
            return "Error registrado: {} ({} veces)".format(error_type, count)

    def fix_and_restart(self, error_type: str, fix_func: Callable | None = None) -> str:
        """Try to fix an error and report."""
        if fix_func:
            try:
                fix_func()
                self._fix_count += 1
                self._state["total_fixes"] = self._state.get("total_fixes", 0) + 1
                self._state["last_fix"] = {
                    "type": error_type,
                    "time": datetime.now().isoformat(),
                }
                self._log_learning("auto_fix", "Fixed: {}".format(error_type))
                self._save_state()
                return "Auto-fix aplicado: {}".format(error_type)
            except Exception as e:
                return "Auto-fix falló: {} - {}".format(error_type, str(e)[:100])
        return "No hay fix disponible para: {}".format(error_type)

    def learn_from_session(self, user_input: str, response: str, tool_used: str = None):
        """Learn from a conversation session."""
        detail = "Input: {} | Response: {} chars".format(user_input[:100], len(response))
        if tool_used:
            detail += " | Tool: {}".format(tool_used)
        self._log_learning("session", detail)
        self._state["total_learning"] = self._state.get("total_learning", 0) + 1
        self._save_state()

    def start_monitoring(self, interval: int = 300):
        """Start background health monitoring."""
        if self._running:
            return
        self._running = True
        def _loop():
            while self._running:
                try:
                    health = self.health_check()
                    if not health["ollama"]:
                        self.handle_error("ollama_down", "Ollama is not responding")
                    syntax = health["syntax"]
                    if syntax["errors"]:
                        for err in syntax["errors"]:
                            self.handle_error("syntax_error", err["file"], err["error"])
                    self._save_state()
                except Exception:
                    pass
                time.sleep(interval)
        self._thread = threading.Thread(target=_loop, daemon=True)
        self._thread.start()

    def stop_monitoring(self):
        self._running = False

    def status(self) -> str:
        """Return human-readable status."""
        lines = [
            "═══ SELF-HEALING STATUS ═══",
            "",
            "  Errores detectados: {}".format(self._state.get("total_errors", 0)),
            "  Auto-fixes aplicados: {}".format(self._state.get("total_fixes", 0)),
            "  Reinicios: {}".format(self._state.get("total_restarts", 0)),
            "  Aprendizajes: {}".format(self._state.get("total_learning", 0)),
            "",
            "  Ultimo check: {}".format(self._state.get("last_check", "nunca")),
            "  Ultimo fix: {}".format(self._state.get("last_fix", "nunca")),
        ]
        known = self._state.get("known_errors", {})
        if known:
            lines.append("")
            lines.append("  Errores conocidos:")
            for err_type, count in sorted(known.items(), key=lambda x: -x[1])[:10]:
                lines.append("    - {}: {} veces".format(err_type, count))
        return "\n".join(lines)


# Singleton
_healer: SelfHealingSystem | None = None


def get_healer() -> SelfHealingSystem:
    global _healer
    if _healer is None:
        _healer = SelfHealingSystem()
    return _healer


def self_healing_tool(parameters: dict = None, player=None) -> str:
    """Action handler for self-healing system with detailed structured reports."""
    if parameters is None:
        parameters = {}
    action = parameters.get("action", "status")
    healer = get_healer()

    if action == "status":
        return healer.status()

    elif action == "health":
        health = healer.health_check()
        lines = ["═══ HEALTH CHECK ═══", ""]
        lines.append("  Ollama: {}".format("OK" if health["ollama"] else "DOWN"))
        lines.append("  ChromaDB: {}".format("OK" if health["chromadb"] else "DOWN"))
        syn = health["syntax"]
        lines.append("  Syntax OK: {}".format(len(syn["ok"])))
        lines.append("  Syntax Errors: {}".format(len(syn["errors"])))
        lines.append("  Auto-fixed: {}".format(len(syn["fixed"])))
        if syn["errors"]:
            lines.append("")
            lines.append("  Errores de sintaxis:")
            for err in syn["errors"][:5]:
                lines.append("    - {}: {}".format(err["file"], err["error"][:60]))
        return "\n".join(lines)

    elif action == "scan_all":
        files = list(healer._iter_project_py())

        healthy = 0
        error_files = []
        total_errors = 0
        categories = {"core": 0, "actions": 0, "agents": 0, "other": 0}
        cat_errors = {"core": 0, "actions": 0, "agents": 0, "other": 0}

        for f in files:
            try:
                py_compile.compile(str(f), doraise=True)
                healthy += 1
                cat = "core" if "core" in str(f) else "actions" if "actions" in str(f) else "agents" if "agents" in str(f) else "other"
                categories[cat] = categories.get(cat, 0) + 1
            except py_compile.PyCompileError as e:
                total_errors += 1
                src = Path(__file__).resolve().parent.parent
                rel = str(f.relative_to(src))
                cat = "core" if "core" in rel else "actions" if "actions" in rel else "agents" if "agents" in rel else "other"
                cat_errors[cat] = cat_errors.get(cat, 0) + 1
                error_files.append({"file": rel, "error": str(e)[:120]})

        lines = ["═══ ESCANEO COMPLETO: {} ARCHIVOS ═══".format(len(files)), ""]
        lines.append("  Saludables: {} | Con errores: {} | Total errores: {}".format(
            healthy, len(error_files), total_errors))
        lines.append("")
        lines.append("  Por categoria:")
        for cat in ["core", "actions", "agents", "other"]:
            if categories.get(cat, 0) > 0:
                err = cat_errors.get(cat, 0)
                ok = categories[cat] - err
                lines.append("    {}: {} OK, {} errores".format(cat.upper(), ok, err))

        if error_files:
            lines.append("")
            lines.append("  Archivos con errores ({}):".format(len(error_files)))
            for ef in error_files[:15]:
                lines.append("    {} {}".format(ef["file"], ef["error"][:60]))
            if len(error_files) > 15:
                lines.append("    ... y {} mas".format(len(error_files) - 15))
        else:
            lines.append("")
            lines.append("  Todos los archivos saludables.")

        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": "scan_all",
            "files_scanned": len(files),
            "total_errors": total_errors,
            "healthy": healthy,
        }
        healer._log_learning("scan_all", "Scanned {} files, {} errors".format(len(files), total_errors))
        return "\n".join(lines)

    elif action == "health_report":
        files = list(healer._iter_project_py())

        total_lines = 0
        functions = 0
        classes = 0
        imports = 0
        comments = 0
        for f in files:
            try:
                content = f.read_text("utf-8", errors="ignore")
                lines_list = content.splitlines()
                total_lines += len(lines_list)
                for line in lines_list:
                    s = line.strip()
                    if s.startswith("def "): functions += 1
                    if s.startswith("class "): classes += 1
                    if s.startswith("import ") or s.startswith("from "): imports += 1
                    if s.startswith("#"): comments += 1
            except Exception:
                pass

        hist = healer._load_state()
        errors_log = []
        if _ERROR_LOG.exists():
            try:
                errors_log = json.loads(_ERROR_LOG.read_text(encoding="utf-8"))
            except Exception:
                pass
        learning_log = []
        if _LEARNING_LOG.exists():
            try:
                learning_log = json.loads(_LEARNING_LOG.read_text(encoding="utf-8"))
            except Exception:
                pass

        recent_errors = [e for e in errors_log if e.get("time", "") > datetime.now().isoformat()[:10]]
        recent_learning = [l for l in learning_log if l.get("time", "") > datetime.now().isoformat()[:10]]

        lines = ["═══ REPORTE DE SALUD COMPLETO ═══", ""]
        lines.append("  Archivos: {}".format(len(files)))
        lines.append("  Lineas totales: {:,}".format(total_lines))
        lines.append("  Funciones: {} | Clases: {} | Imports: {} | Comentarios: {}".format(
            functions, classes, imports, comments))
        lines.append("")
        lines.append("  ── ESTADO ──")
        lines.append("  Ollama: {}".format("UP" if healer.check_ollama() else "DOWN"))
        lines.append("  ChromaDB: {}".format("UP" if healer.check_chromadb() else "DOWN"))
        lines.append("")
        lines.append("  ── HISTORICO ──")
        lines.append("  Errores totales: {}".format(hist.get("total_errors", 0)))
        lines.append("  Fixes aplicados: {}".format(hist.get("total_fixes", 0)))
        lines.append("  Reinicios: {}".format(hist.get("total_restarts", 0)))
        lines.append("  Aprendizajes: {}".format(hist.get("total_learning", 0)))
        lines.append("")
        lines.append("  ── HOY ──")
        lines.append("  Errores hoy: {}".format(len(recent_errors)))
        lines.append("  Aprendizajes hoy: {}".format(len(recent_learning)))
        if recent_errors:
            lines.append("  Ultimos errores:")
            for e in recent_errors[-3:]:
                lines.append("    [{}] {}: {}".format(e.get("time", "?")[:16], e.get("type", "?"), e.get("message", "")[:50]))
        if recent_learning:
            lines.append("  Ultimos aprendizajes:")
            for l in recent_learning[-3:]:
                lines.append("    [{}] {}: {}".format(l.get("time", "?")[:16], l.get("action", "?"), l.get("detail", "")[:50]))
        if hist.get("last_check"):
            lines.append("")
            lines.append("  Ultimo check: {}".format(hist["last_check"][:19]))

        return "\n".join(lines)

    elif action == "fix_syntax":
        file_path = parameters.get("path", "")
        if not file_path:
            return "Especifico 'path' del archivo a analizar"
        ok, msg = healer.check_syntax(file_path)
        if ok:
            return "Syntax OK: {}".format(file_path)
        fixed = healer.auto_fix_syntax(file_path)
        if fixed:
            return "Auto-fix aplicado: {}".format(file_path)
        return "Error de syntax (no auto-fix): {}".format(msg)

    elif action == "learn":
        user_input = parameters.get("input", "")
        response = parameters.get("response", "")
        tool = parameters.get("tool", None)
        healer.learn_from_session(user_input, response, tool)
        return "Aprendizaje registrado"

    elif action == "errors":
        if _ERROR_LOG.exists():
            errors = json.loads(_ERROR_LOG.read_text(encoding="utf-8"))
            recent = errors[-20:]
            lines = ["═══ ERRORES RECIENTES ({}) ═══".format(len(errors)), ""]
            for e in recent:
                lines.append("  [{}] {}: {}".format(e.get("time", "?")[:16], e.get("type", "?"), e.get("message", "")[:60]))
            return "\n".join(lines)
        return "No hay errores registrados"

    elif action == "learning":
        if _LEARNING_LOG.exists():
            logs = json.loads(_LEARNING_LOG.read_text(encoding="utf-8"))
            recent = logs[-20:]
            lines = ["═══ APRENDIZAJE ({}) ═══".format(len(logs)), ""]
            for l in recent:
                lines.append("  [{}] {}: {}".format(l.get("time", "?")[:16], l.get("action", "?"), l.get("detail", "")[:60]))
            return "\n".join(lines)
        return "No hay aprendizaje registrado"

    elif action == "resilient":
        from core.resilient import get_manager
        m = get_manager()
        stats = m.get_stats()
        lines = ["═══ RESILIENT TASK QUEUE ═══", ""]
        lines.append("  Pending: {}".format(stats["pending"]))
        lines.append("  Awaiting delivery: {}".format(stats["awaiting_delivery"]))
        lines.append("  Retry queue: {}".format(stats["retry"]))
        lines.append("  Completed today: {}".format(stats["completed_today"]))
        lines.append("  Total completed: {}".format(stats["total_completed"]))
        pending = m.get_pending_tasks()
        if pending:
            lines.append("")
            lines.append("  Pendientes:")
            for t in pending[:5]:
                lines.append("    {} [{}] - {}".format(t.get("tool", "?"), t.get("status", "?"), t.get("created", "?")[:16]))
        return "\n".join(lines)

    else:
        return (
            "Acciones: status | health (check completo) | scan_all (escanear archivos) | "
            "health_report (reporte detallado) | fix_syntax (arreglar archivo) | "
            "learn (registrar aprendizaje) | errors (ver errores) | learning (ver aprendizajes) | "
            "resilient (ver cola de tareas pendientes)"
        )
        return "Acciones: status, health, fix_syntax, learn, errors, learning"
