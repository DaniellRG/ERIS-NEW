# -*- coding: utf-8 -*-
"""
self_heal.py — ERIS Self-Healing System.
Analiza su propio código fuente, detecta bugs, errores y daños,
y aplica correcciones automáticas con respaldo y validación.
"""
import ast
import builtins
import json
import os
import py_compile
import shutil
import sys
import traceback
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ACTIONS_DIR = BASE_DIR / "actions"
BACKUP_DIR = BASE_DIR / "backups"
HEALTH_LOG = BASE_DIR / "config" / "self_heal_history.json"
IGNORE_DIRS = {"__pycache__", ".git", "build", "lib", "share", "PyQt6.uic.widget-plugins"}
IGNORE_FILES = {"__init__.py", "custom_tools.json", "eris_sandbox_history.json"}


def _log(msg: str, player=None):
    if player:
        player.write_log(f"[self_heal] {msg}")


def _ensure_backup(file_path: Path) -> str:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    rel = str(file_path.relative_to(BASE_DIR)).replace(os.sep, "__").replace("/", "__")
    bak = BACKUP_DIR / f"{rel}.{ts}.heal.bak"
    shutil.copy2(file_path, bak)
    return str(bak)


def _load_history() -> list:
    try:
        if HEALTH_LOG.exists():
            return json.loads(HEALTH_LOG.read_text("utf-8"))
    except Exception:
        pass
    return []


def _save_entry(entry: dict):
    hist = _load_history()
    hist.append(entry)
    if len(hist) > 200:
        hist = hist[-200:]
    HEALTH_LOG.parent.mkdir(parents=True, exist_ok=True)
    HEALTH_LOG.write_text(json.dumps(hist, indent=2, ensure_ascii=False), "utf-8")


def _all_py_files(base: Path) -> list[Path]:
    files = []
    for f in base.rglob("*.py"):
        rel = f.relative_to(BASE_DIR)
        parts = rel.parts
        if any(p in IGNORE_DIRS for p in parts):
            continue
        if f.name in IGNORE_FILES:
            continue
        files.append(f)
    return sorted(files)


def _check_syntax(file_path: Path) -> list[dict]:
    errors = []
    try:
        py_compile.compile(str(file_path), doraise=True)
    except py_compile.PyCompileError as e:
        errors.append({
            "type": "syntax",
            "line": getattr(e, "lineno", 0),
            "message": str(e),
        })
    return errors


def _check_imports(file_path: Path) -> list[dict]:
    errors = []
    try:
        source = file_path.read_text("utf-8")
        tree = ast.parse(source)
    except SyntaxError:
        return errors

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                try:
                    __import__(alias.name)
                except ImportError:
                    pass
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                continue
            if node.module:
                try:
                    __import__(node.module)
                except ImportError:
                    pass
    return errors


def _check_ast(file_path: Path) -> list[dict]:
    errors = []
    try:
        source = file_path.read_text("utf-8")
        tree = ast.parse(source)
    except SyntaxError:
        return [{"type": "ast", "line": 0, "message": "SyntaxError impide análisis AST"}]

    defined_names = set()
    builtin_names = set(dir(builtins))
    used_names = {}
    annotation_names = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            defined_names.add(node.name)
            if node.returns:
                for n in ast.walk(node.returns):
                    if isinstance(n, ast.Name):
                        annotation_names.add(n.id)
        elif isinstance(node, ast.AsyncFunctionDef):
            defined_names.add(node.name)
        elif isinstance(node, ast.ClassDef):
            defined_names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    defined_names.add(target.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            defined_names.add(node.target.id)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                defined_names.add(alias.asname or alias.name)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                defined_names.add(alias.asname or alias.name)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            name = node.id
            if name not in used_names:
                used_names[name] = node.lineno

    for name, lineno in used_names.items():
        if name in annotation_names:
            continue
        if name in builtin_names:
            continue
        if name.startswith("_"):
            continue
        if name in defined_names:
            continue
        errors.append({
            "type": "undefined_name",
            "line": lineno,
            "message": f"Posible nombre no definido: '{name}'",
        })

    return errors


def _check_file_size(file_path: Path) -> list[dict]:
    errors = []
    try:
        lines = file_path.read_text("utf-8").splitlines()
        for i, line in enumerate(lines, 1):
            if len(line) > 500:
                errors.append({
                    "type": "long_line",
                    "line": i,
                    "message": f"Línea extremadamente larga ({len(line)} chars)",
                })
    except Exception:
        pass
    return errors


def _scan_file(file_path: Path, deep: bool = False) -> dict:
    errors = []
    errors.extend(_check_syntax(file_path))
    errors.extend(_check_ast(file_path))
    errors.extend(_check_file_size(file_path))
    if deep:
        errors.extend(_check_imports(file_path))

    rel = str(file_path.relative_to(BASE_DIR))
    return {
        "file": rel,
        "path": str(file_path),
        "errors": errors,
        "error_count": len(errors),
        "healthy": len(errors) == 0,
    }


IMPORT_SUGGESTIONS = {
    "Flask": "from flask import Flask",
    "deque": "from collections import deque",
    "render_template_string": "from flask import render_template_string",
    "jsonify": "from flask import jsonify",
    "request": "from flask import request",
    "redirect": "from flask import redirect",
    "url_for": "from flask import url_for",
    "psutil": "import psutil",
    "np": "import numpy as np",
    "pd": "import pandas as pd",
    "plt": "import matplotlib.pyplot as plt",
    "Image": "from PIL import Image",
}


def _auto_fix_syntax(file_path: Path, error: dict) -> tuple[bool, str]:
    return False, "Error de sintaxis requiere corrección manual. Usa subagent_task mode=code"


def _auto_fix_undefined(file_path: Path, error: dict) -> tuple[bool, str]:
    name = error.get("message", "").split("'")[1] if "'" in error.get("message", "") else ""
    if not name:
        return False, "No se pudo extraer el nombre"
    if name in IMPORT_SUGGESTIONS:
        imp = IMPORT_SUGGESTIONS[name]
        source = file_path.read_text("utf-8")
        if imp not in source:
            new_source = imp + "\n" + source
            file_path.write_text(new_source, "utf-8")
            return True, f"Agregado: {imp}"
        return False, f"Ya existe import para '{name}'"
    return False, f"No se conoce el import para '{name}'. Usa subagent_task mode=code"


def _auto_fix_long_line(file_path: Path, error: dict) -> tuple[bool, str]:
    return False, "División de líneas largas requiere criterio humano. Usa subagent_task mode=code"


def _auto_fix_bare_except(file_path: Path, error: dict) -> tuple[bool, str]:
    try:
        source = file_path.read_text("utf-8")
        lines = source.splitlines(keepends=True)
        lineno = error.get("line", 0)
        if lineno < 1 or lineno > len(lines):
            return False, "Línea inválida"
        stripped = lines[lineno - 1].lstrip()
        indent = lines[lineno - 1][:len(lines[lineno - 1]) - len(stripped)]
        if stripped.strip() == "except:":
            lines[lineno - 1] = indent + "except Exception:\n"
            file_path.write_text("".join(lines), "utf-8")
            return True, "except: → except Exception:"
        return False, "No es un except: directo"
    except Exception as e:
        return False, f"Error: {e}"


def _auto_fix_debug_print(file_path: Path, error: dict) -> tuple[bool, str]:
    try:
        source = file_path.read_text("utf-8")
        lines = source.splitlines(keepends=True)
        lineno = error.get("line", 0)
        if lineno < 1 or lineno > len(lines):
            return False, "Línea inválida"
        line = lines[lineno - 1]
        if "print(" in line:
            indent = line[:len(line) - len(line.lstrip())]
            lines[lineno - 1] = f"{indent}# DEBUG: {line.lstrip()}"
            file_path.write_text("".join(lines), "utf-8")
            return True, "print() comentado como DEBUG"
        return False, "No contiene print()"
    except Exception as e:
        return False, f"Error: {e}"


def self_heal(parameters: dict, player=None) -> str:
    """
    Sistema de auto-curación de ERIS. Analiza el código fuente,
    detecta bugs y aplica correcciones automáticas.
    """
    action = parameters.get("action", "scan_all").strip().lower()
    file_ref = parameters.get("file", "").strip()

    if action == "scan_all":
        files = _all_py_files(BASE_DIR)
        healthy_count = 0
        error_files = []
        total_errors = 0
        for f in files:
            r = _scan_file(f, deep=True)
            total_errors += r["error_count"]
            if r["healthy"]:
                healthy_count += 1
            else:
                error_files.append(r)

        report = (
            "=== ESCANEO: {} archivos ===\n"
            "Saludables: {} | Con errores: {} | Total errores: {}\n"
        ).format(len(files), healthy_count, len(error_files), total_errors)

        if error_files:
            report += "\nArchivos con errores:\n"
            for r in error_files[:10]:
                report += "  {} ({} errores)\n".format(r["file"], r["error_count"])
                for e in r["errors"][:2]:
                    report += "    L{}: [{}] {}\n".format(e["line"], e["type"], e["message"][:60])
            if len(error_files) > 10:
                report += "  ... y {} archivos mas\n".format(len(error_files) - 10)
        else:
            report += "\nTodos los archivos estan saludables."

        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": "scan_all",
            "files_scanned": len(files),
            "total_errors": total_errors,
            "healthy": healthy_count,
        }
        _save_entry(entry)
        return report

    elif action == "scan_file":
        if not file_ref:
            return "Error: Se requiere 'file' (ej: 'main.py', 'actions/spotify_control.py')"
        fp = BASE_DIR / file_ref
        if not fp.exists():
            return f"Error: Archivo '{file_ref}' no encontrado"
        r = _scan_file(fp, deep=True)
        if r["healthy"]:
            return f"✅ {r['file']}: saludable (0 errores)"
        lines = [f"❌ {r['file']}: {r['error_count']} errores"]
        for e in r["errors"]:
            lines.append(f"   L{e['line']}: [{e['type']}] {e['message']}")
        return "\n".join(lines)

    elif action == "health_report":
        files = _all_py_files(BASE_DIR)
        results = []
        total_errors = 0
        max_file = ""
        max_errors = 0
        for f in files:
            r = _scan_file(f, deep=False)
            results.append(r)
            total_errors += r["error_count"]
            if r["error_count"] > max_errors:
                max_errors = r["error_count"]
                max_file = r["file"]

        total_lines = 0
        for f in files:
            try:
                total_lines += len(f.read_text("utf-8").splitlines())
            except Exception:
                pass

        langs = {}
        for f in files:
            try:
                for line in f.read_text("utf-8").splitlines():
                    stripped = line.strip()
                    if "import " in stripped or "from " in stripped:
                        langs["imports"] = langs.get("imports", 0) + 1
                    if "def " in stripped:
                        langs["functions"] = langs.get("functions", 0) + 1
                    if "class " in stripped:
                        langs["classes"] = langs.get("classes", 0) + 1
                    if line.strip().startswith("#"):
                        langs["comments"] = langs.get("comments", 0) + 1
            except Exception:
                pass

        hist = _load_history()
        fixes_applied = sum(1 for h in hist if h.get("action") in ("auto_fix", "auto_fix_all"))

        return (
            f"=== REPORTE DE SALUD ===\n"
            f"Archivos: {len(files)}\n"
            f"Líneas totales: {total_lines}\n"
            f"Errores totales: {total_errors}\n"
            f"Archivo con más errores: {max_file} ({max_errors})\n"
            f"Funciones: {langs.get('functions', 0)}\n"
            f"Clases: {langs.get('classes', 0)}\n"
            f"Comentarios: {langs.get('comments', 0)}\n"
            f"Auto-fixes aplicados (histórico): {fixes_applied}\n"
            f"Último escaneo: {hist[-1]['timestamp'] if hist else 'nunca'}"
        )

    elif action == "auto_fix":
        if not file_ref:
            return "Error: Se requiere 'file' para auto-fix"
        fp = BASE_DIR / file_ref
        if not fp.exists():
            return f"Error: Archivo '{file_ref}' no encontrado"

        # Deep analysis to find fixable issues
        source = fp.read_text("utf-8")
        lines = source.splitlines()
        all_errors = _scan_file(fp, deep=True)["errors"]
        deep_errors = []
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if "except:" in stripped and "Exception" not in stripped:
                deep_errors.append({"type": "bare_except", "line": i, "message": "except: sin tipo"})
            if "print(" in stripped and not any(kw in stripped for kw in ("def ", "class ", "lambda ")):
                deep_errors.append({"type": "debug_print", "line": i, "message": "print() fuera de funcion puede ser residual"})
            for name in IMPORT_SUGGESTIONS:
                if stripped == name or stripped.startswith(name + ".") or stripped.startswith(name + "("):
                    if IMPORT_SUGGESTIONS[name] not in source:
                        deep_errors.append({"type": "undefined_name", "line": i, "message": f"Posible nombre no definido: '{name}'"})
                        break

        all_errors.extend(deep_errors)
        deduped = list({e["line"]: e for e in all_errors}.values())

        if not deduped:
            return f"✅ {file_ref}: no requiere corrección"

        backup = _ensure_backup(fp)
        source = fp.read_text("utf-8")
        lines = source.splitlines(keepends=True)
        patches = []
        new_imports = set()

        for e in deduped:
            lineno = e["line"]
            if lineno < 1 or lineno > len(lines):
                continue
            if e["type"] == "bare_except":
                stripped = lines[lineno - 1].lstrip()
                indent = lines[lineno - 1][:len(lines[lineno - 1]) - len(stripped)]
                if stripped.strip() == "except:\n" or stripped.strip() == "except:":
                    lines[lineno - 1] = indent + "except Exception:\n"
                    patches.append(f"L{lineno}: except: -> except Exception:")
            elif e["type"] == "debug_print":
                line = lines[lineno - 1]
                indent = line[:len(line) - len(line.lstrip())]
                stripped_body = line.strip()
                if stripped_body.endswith("\n"):
                    stripped_body = stripped_body[:-1]
                lines[lineno - 1] = f"{indent}if False: {stripped_body}\n"
                patches.append(f"L{lineno}: print() desactivado con if False")
            elif e["type"] == "undefined_name":
                msg = e.get("message", "")
                name = msg.split("'")[1] if "'" in msg else ""
                if name in IMPORT_SUGGESTIONS and IMPORT_SUGGESTIONS[name] not in source:
                    new_imports.add(IMPORT_SUGGESTIONS[name])

        # Add new imports at the top
        if new_imports:
            import_block = "\n".join(sorted(new_imports)) + "\n"
            lines.insert(0, import_block)
            for imp in new_imports:
                patches.append(f"[top] Agregado: {imp}")

        if patches:
            fp.write_text("".join(lines), "utf-8")
            return (
                f"✅ {file_ref}: {len(patches)} correcciones aplicadas\n"
                f"Backup: {backup}\n" + "\n".join(patches)
            )

        else:
            return (
                f"❌ {file_ref}: no se pudieron aplicar correcciones automáticas.\n"
                f"Backup: {backup}\n"
                f"Usa subagent_task mode=code para correcciones detalladas."
            )

        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": "auto_fix",
            "file": file_ref,
            "errors_fixed": len(patches),
            "backup": backup,
        }
        _save_entry(entry)
        return (
            f"✅ {file_ref}: {len(patches)} correcciones aplicadas\n"
            f"Backup: {backup}\n" + "\n".join(patches)
        )

    elif action == "auto_fix_all":
        files = _all_py_files(BASE_DIR)
        results = []
        total_fixed = 0
        for f in files:
            r = _scan_file(f, deep=True)
            if r["healthy"]:
                results.append(f"✅ {r['file']}: saludable")
                continue
            backup = _ensure_backup(f)
            fixed = 0
            for e in r["errors"]:
                if e["type"] == "syntax":
                    ok, msg = _auto_fix_syntax(f, e)
                elif e["type"] == "undefined_name":
                    ok, msg = _auto_fix_undefined(f, e)
                elif e["type"] == "long_line":
                    ok, msg = _auto_fix_long_line(f, e)
                elif e["type"] == "bare_except":
                    ok, msg = _auto_fix_bare_except(f, e)
                elif e["type"] == "debug_print":
                    ok, msg = _auto_fix_debug_print(f, e)
                else:
                    ok, msg = False, ""
                if ok:
                    fixed += 1
            if fixed:
                results.append(f"🔧 {r['file']}: {fixed} corregidos (backup: {Path(backup).name})")
                total_fixed += fixed
            else:
                results.append(f"❌ {r['file']}: {r['error_count']} errores (no auto-corregibles)")

        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": "auto_fix_all",
            "files_scanned": len(files),
            "total_fixed": total_fixed,
        }
        _save_entry(entry)
        return "=== AUTO-FIX COMPLETO ===\n" + "\n".join(results)

    elif action == "rollback":
        if not file_ref:
            files = sorted(BACKUP_DIR.glob("*.heal.bak"), key=lambda p: p.stat().st_mtime, reverse=True)
            if not files:
                return "No hay backups de self-heal disponibles"
            latest = files[0]
            parts = latest.stem.split(".")
            if len(parts) >= 2:
                orig_rel = parts[0].replace("__", os.sep)
                orig_path = BASE_DIR / orig_rel
                if orig_path.exists():
                    _ensure_backup(orig_path)
                shutil.copy2(latest, orig_path)
                entry = {
                    "timestamp": datetime.now().isoformat(),
                    "action": "rollback",
                    "file": orig_rel,
                    "restored_from": latest.name,
                }
                _save_entry(entry)
                return f"✅ Rollback: {orig_rel} restaurado desde {latest.name}"
            return f"Backup encontrado pero no se pudo determinar archivo original: {latest.name}"

        fp = BASE_DIR / file_ref
        rel_str = str(fp.relative_to(BASE_DIR)) if fp.exists() else file_ref
        safe_name = rel_str.replace(os.sep, "__").replace("/", "__")
        candidates = sorted(BACKUP_DIR.glob(f"{safe_name}.*.heal.bak"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not candidates:
            return f"No hay backups de self-heal para '{file_ref}'"
        latest = candidates[0]
        if fp.exists():
            _ensure_backup(fp)
        shutil.copy2(latest, fp)
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": "rollback",
            "file": file_ref,
            "restored_from": latest.name,
        }
        _save_entry(entry)
        return f"✅ Rollback: {file_ref} restaurado desde {latest.name}"

    elif action == "history":
        hist = _load_history()
        if not hist:
            return "No hay historial de auto-curación"
        lines = [f"Historial de auto-curación ({len(hist)} entradas):"]
        for h in hist[-20:]:
            ts = h.get("timestamp", "?")[11:19]
            act = h.get("action", "?")
            if act == "scan_all":
                lines.append(f"  [{ts}] Escaneo completo: {h.get('files_scanned', 0)} archivos, {h.get('total_errors', 0)} errores")
            elif act == "auto_fix":
                lines.append(f"  [{ts}] Auto-fix: {h.get('file', '?')} - {h.get('errors_fixed', 0)} corregidos")
            elif act == "auto_fix_all":
                lines.append(f"  [{ts}] Auto-fix completo: {h.get('total_fixed', 0)} corregidos")
            elif act == "rollback":
                lines.append(f"  [{ts}] Rollback: {h.get('file', '?')}")
            else:
                lines.append(f"  [{ts}] {act}")
        return "\n".join(lines)

    elif action == "deep_scan":
        file_ref = parameters.get("file", "")
        if not file_ref:
            return "Error: Se requiere 'file' para deep_scan"
        fp = BASE_DIR / file_ref
        if not fp.exists():
            return f"Error: Archivo '{file_ref}' no encontrado"

        source = fp.read_text("utf-8")
        lines = source.splitlines()
        issues = []
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if "print(" in stripped and "def " not in stripped:
                issues.append({"line": i, "type": "debug_print", "message": "print() fuera de función puede ser residual"})
            if "except:" in stripped and "Exception" not in stripped:
                issues.append({"line": i, "type": "bare_except", "message": "except: sin tipo específico atraga todo"})
            if "import *" in stripped:
                issues.append({"line": i, "type": "wildcard_import", "message": "from X import * contamina el namespace"})
            if "TODO" in stripped.upper() or "FIXME" in stripped.upper() or "HACK" in stripped.upper():
                issues.append({"line": i, "type": "todo", "message": f"Marcador: {stripped.strip()[:60]}"})
            if "pass" == stripped:
                if i < len(lines):
                    nxt = lines[i].strip() if i < len(lines) else ""
                    if nxt and not nxt.startswith(("def ", "class ", "if ", "elif ", "else", "try", "except", "finally", "for ", "while ", "with ")):
                        issues.append({"line": i, "type": "stray_pass", "message": "pass suelto que puede eliminarse"})

        if not issues:
            ts = datetime.now().isoformat()
            entry = {"timestamp": ts, "action": "deep_scan", "file": file_ref, "issues": 0}
            _save_entry(entry)
            return f"✅ {file_ref}: análisis profundo sin issues"

        ts = datetime.now().isoformat()
        entry = {"timestamp": ts, "action": "deep_scan", "file": file_ref, "issues": len(issues)}
        _save_entry(entry)

        report = f"🔍 Análisis profundo de {file_ref}:\n"
        for issue in issues:
            report += f"  L{issue['line']}: [{issue['type']}] {issue['message']}\n"
        report += f"\n{len(issues)} issues encontrados. Usa subagent_task mode=code para correcciones detalladas."
        return report

    else:
        return (
            f"Acción '{action}' no reconocida. Acciones:\n"
            "- scan_all: Escanear todos los archivos .py\n"
            "- scan_file: Escanear un archivo específico\n"
            "- deep_scan: Análisis profundo (bare except, print, TODO, etc.)\n"
            "- health_report: Reporte general de salud del código\n"
            "- auto_fix: Intentar corregir errores de un archivo\n"
            "- auto_fix_all: Intentar corregir todos los archivos\n"
            "- rollback: Restaurar último backup de self-heal\n"
            "- history: Ver historial de auto-curación"
        )
