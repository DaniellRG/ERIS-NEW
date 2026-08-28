"""
core/self_modify.py — Auto-mejora de codigo para Eris

Eris analiza su propio codigo, detecta mejoras, y las aplica
con backup automatico y rollback si falla.
"""
import json
import subprocess
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional

_BASE = Path(__file__).resolve().parent.parent
_MEMORY = _BASE / "memory"
_BACKUPS = _MEMORY / "self_modify_backups"
_STATE_FILE = _MEMORY / "self_modify_state.json"
_LOG_FILE = _MEMORY / "self_modify_log.json"
_CORE = _BASE / "core"

PROTECTED_FILES = ["main.py", "__init__.py"]
MAX_CHANGES_PER_DAY = 15


def _load_state() -> dict:
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "changes_today": 0,
        "total_changes": 0,
        "last_reset": datetime.now().isoformat(),
        "files_modified": [],
    }


def _save_state(state: dict):
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def _log(action: str, details: str, success: bool = True):
    entry = {
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "details": details[:300],
        "success": success,
    }
    logs = []
    if _LOG_FILE.exists():
        try:
            logs = json.loads(_LOG_FILE.read_text(encoding="utf-8"))
        except Exception:
            logs = []
    logs.append(entry)
    if len(logs) > 100:
        logs = logs[-100:]
    _LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    _LOG_FILE.write_text(json.dumps(logs, indent=2, ensure_ascii=False), encoding="utf-8")


def _reset_daily(state: dict) -> dict:
    last = state.get("last_reset", "")
    if last:
        try:
            last_dt = datetime.fromisoformat(last)
            if datetime.now().date() > last_dt.date():
                state["changes_today"] = 0
                state["last_reset"] = datetime.now().isoformat()
        except Exception:
            state["last_reset"] = datetime.now().isoformat()
    return state


def analyze_code(file_path: str) -> dict:
    path = Path(file_path)
    if not path.exists():
        return {"error": "Archivo no encontrado: {}".format(file_path)}
    try:
        content = path.read_text(encoding="utf-8")
        lines = content.split("\n")
    except Exception as e:
        return {"error": "No se pudo leer: {}".format(str(e))}

    issues = []
    suggestions = []

    func_name = None
    func_start = 0
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("def ") and "(" in stripped:
            if func_name and (i - func_start) > 50:
                issues.append({
                    "type": "long_function",
                    "line": func_start,
                    "detail": "Funcion '{}' tiene {} lineas".format(func_name, i - func_start),
                })
                suggestions.append("Refactorizar '{}' en funciones mas pequenas".format(func_name))
            func_name = stripped.split("def ")[1].split("(")[0]
            func_start = i

    for i in range(2, len(lines)):
        if (lines[i].strip() == lines[i - 1].strip() == lines[i - 2].strip()
                and lines[i].strip() and not lines[i].strip().startswith("#")):
            issues.append({
                "type": "duplicate_lines",
                "line": i + 1,
                "detail": "Linea repetida 3+ veces: '{}'".format(lines[i].strip()[:50]),
            })

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("def ") and "(" in stripped:
            fn = stripped.split("def ")[1].split("(")[0]
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if not next_line.startswith('"""') and not next_line.startswith("'''"):
                    issues.append({
                        "type": "no_docstring",
                        "line": i + 1,
                        "detail": "Funcion '{}' sin docstring".format(fn),
                    })

    return {
        "file": str(path),
        "total_lines": len(lines),
        "issues": issues,
        "suggestions": suggestions,
        "issue_count": len(issues),
    }


def _backup_file(file_path: Path) -> Path:
    _BACKUPS.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = "{}_{}".format(file_path.stem, timestamp)
    backup_path = _BACKUPS / "{}{}".format(backup_name, file_path.suffix)
    backup_path.write_text(file_path.read_text(encoding="utf-8"), encoding="utf-8")
    return backup_path


def _rollback_file(file_path: Path, backup_path: Path):
    if backup_path.exists():
        file_path.write_text(backup_path.read_text(encoding="utf-8"), encoding="utf-8")


def _verify_syntax(file_path: Path) -> bool:
    try:
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(file_path)],
            capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0
    except Exception:
        return False


def apply_change(file_path: str, old_code: str, new_code: str, reason: str = "") -> dict:
    state = _load_state()
    state = _reset_daily(state)
    if state["changes_today"] >= MAX_CHANGES_PER_DAY:
        return {"error": "Limite diario de cambios alcanzado"}
    path = Path(file_path)
    if not path.exists():
        return {"error": "Archivo no encontrado"}
    if path.name in PROTECTED_FILES:
        return {"error": "Archivo protegido: {}".format(path.name)}
    content = path.read_text(encoding="utf-8")
    if old_code not in content:
        return {"error": "Codigo original no encontrado en el archivo"}
    backup = _backup_file(path)
    new_content = content.replace(old_code, new_code, 1)
    path.write_text(new_content, encoding="utf-8")
    if not _verify_syntax(path):
        _rollback_file(path, backup)
        _log("apply_change", "ROLLBACK: {}".format(path.name), False)
        return {"error": "Rollback: nuevo codigo tiene errores de syntax"}
    state["changes_today"] += 1
    state["total_changes"] += 1
    state.setdefault("files_modified", []).append({
        "file": str(path.name),
        "timestamp": datetime.now().isoformat(),
        "reason": reason[:100],
    })
    _save_state(state)
    _log("apply_change", "Cambio: {} ({})".format(path.name, reason[:80]))
    return {"status": "aplicado", "file": str(path.name), "backup": str(backup), "reason": reason}


def self_improve() -> dict:
    results = {"files_analyzed": 0, "total_issues": 0, "improvements": []}
    py_files = list(_CORE.glob("*.py"))
    for py_file in py_files:
        if py_file.name in PROTECTED_FILES:
            continue
        analysis = analyze_code(str(py_file))
        results["files_analyzed"] += 1
        results["total_issues"] += analysis.get("issue_count", 0)
        if analysis.get("suggestions"):
            results["improvements"].append({
                "file": py_file.name,
                "suggestions": analysis["suggestions"][:3],
                "issue_count": analysis["issue_count"],
            })
    _log("self_improve", "Analisis: {} archivos, {} issues".format(
        results["files_analyzed"], results["total_issues"]
    ))
    return results


def self_modify_tool(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = params.get("action", "status")

    if action == "status":
        state = _load_state()
        state = _reset_daily(state)
        _save_state(state)
        return json.dumps({
            "changes_today": state["changes_today"],
            "max_daily": MAX_CHANGES_PER_DAY,
            "total_changes": state["total_changes"],
            "files_modified": len(state.get("files_modified", [])),
        }, indent=2)

    elif action == "analyze":
        file_path = params.get("file", "")
        if not file_path:
            return json.dumps({"error": "Archivo requerido"})
        return json.dumps(analyze_code(file_path), indent=2, default=str)

    elif action == "self_improve":
        return json.dumps(self_improve(), indent=2, default=str)

    elif action == "apply":
        file_path = params.get("file", "")
        old_code = params.get("old_code", "")
        new_code = params.get("new_code", "")
        reason = params.get("reason", "")
        if not all([file_path, old_code, new_code]):
            return json.dumps({"error": "file, old_code y new_code requeridos"})
        return json.dumps(apply_change(file_path, old_code, new_code, reason), indent=2)

    elif action == "rollback":
        backups = sorted(_BACKUPS.glob("*.py")) if _BACKUPS.exists() else []
        if not backups:
            return json.dumps({"error": "No hay backups"})
        last = backups[-1]
        stem = last.stem.rsplit("_", 1)[0]
        original = _CORE / "{}.py".format(stem)
        if original.exists():
            _rollback_file(original, last)
            _log("rollback", "Restaurado: {}".format(original.name))
            return json.dumps({"status": "restaurado", "file": original.name})
        return json.dumps({"error": "Original no encontrado"})

    return json.dumps({"error": "Accion desconocida: {}".format(action)})


if __name__ == "__main__":
    print("=== Test Self-Modify ===")
    print(self_modify_tool({"action": "status"}))
    r = json.loads(self_modify_tool({"action": "self_improve"}))
    print("Archivos:", r["files_analyzed"], "Issues:", r["total_issues"])
