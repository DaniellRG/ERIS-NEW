# -*- coding: utf-8 -*-
from __future__ import annotations

import ast
import json
import os
import re
import sys
import traceback
from collections import defaultdict
from datetime import datetime
from pathlib import Path

_DATA_DIR = Path(r"D:\Eris_Source\data")
_JOURNAL_FILE = _DATA_DIR / "auto_healer_journal.json"
_PROJECT_ROOT = Path(r"D:\Eris_Source")

_IGNORE_DIRS = {"__pycache__", ".venv", "venv", "site-packages", "node_modules", ".git", "backups"}


def _load_journal() -> dict:
    try:
        if _JOURNAL_FILE.exists():
            return json.loads(_JOURNAL_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"entries": [], "stats": {"total_analyzed": 0, "total_fixed": 0, "total_suggested": 0}}


def _save_journal(journal: dict):
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    if len(journal.get("entries", [])) > 500:
        journal["entries"] = journal["entries"][-500:]
    _JOURNAL_FILE.write_text(json.dumps(journal, ensure_ascii=False, indent=2), encoding="utf-8")


def _parse_traceback(tb_str: str) -> dict:
    result = {
        "error_type": "",
        "message": "",
        "file": "",
        "line": 0,
        "code_line": "",
        "traceback_raw": tb_str[:2000],
    }
    lines = tb_str.strip().splitlines()
    if not lines:
        return result
    for line in reversed(lines):
        m = re.match(r'^(\w+(?:Error|Warning|Exception|Exit))\s*:\s*(.*)', line)
        if m:
            result["error_type"] = m.group(1)
            result["message"] = m.group(2).strip()
            break
    tb_header = re.compile(r'File "(.+?)", line (\d+)')
    for line in lines:
        m = tb_header.search(line)
        if m:
            result["file"] = m.group(1)
            result["line"] = int(m.group(2))
    for i, line in enumerate(lines):
        if re.match(r'^\s{4}\S', line) and i > 0:
            prev = lines[i - 1].strip()
            if prev.startswith("File "):
                result["code_line"] = line.strip()
                break
    if not result["error_type"] and lines:
        last = lines[-1].strip()
        for etype in ("Error", "Exception", "Warning"):
            if etype in last:
                parts = last.split(":", 1)
                result["error_type"] = parts[0].strip()
                result["message"] = parts[1].strip() if len(parts) > 1 else ""
                break
    return result


def _handle_import_error(info: dict, file_content: str = "") -> list:
    suggestions = []
    combined = f"{info.get('message', '')} {info.get('traceback_raw', '')}"
    m = re.search(r"cannot import name '(\w+)' from '([\w.]+)'", combined)
    if m:
        name = m.group(1)
        module = m.group(2)
        suggestions.append(f"El nombre '{name}' no existe en el modulo '{module}'.")
        suggestions.append(f"Verificar que '{name}' esta exportado en '{module}' (revisar __init__.py o __all__).")
        suggestions.append(f"Alternativa: from {module} import {name} -> verificar typo o nombre correcto.")
    return suggestions


def _handle_module_not_found(info: dict, file_content: str = "") -> list:
    suggestions = []
    combined = f"{info.get('message', '')} {info.get('traceback_raw', '')}"
    m = re.search(r"No module named '?([\w.]+)'?", combined)
    module = m.group(1) if m else ""
    if not module:
        return suggestions
    top_module = module.split(".")[0]
    suggestions.append(f"Modulo '{module}' no encontrado.")
    suggestions.append(f"Intentar: pip install {top_module}")
    local_path = _PROJECT_ROOT / module.replace(".", "/")
    if local_path.exists():
        suggestions.append(f"Modulo local encontrado en: {local_path}")
        suggestions.append("Verificar que el directorio esta en sys.path o es un paquete valido.")
    else:
        suggestions.append(f"No se encontro como modulo local en {_PROJECT_ROOT}.")
        if top_module in ("core", "actions", "skills", "agent", "agents"):
            suggestions.append(f"Modulo '{module}' parece ser parte del proyecto. Verificar que el archivo existe y tiene syntax correcta.")
    return suggestions


def _handle_syntax_error(info: dict, file_content: str = "") -> list:
    suggestions = []
    msg = info.get("message", "")
    suggestions.append(f"Error de sintaxis: {msg}")
    file_path = info.get("file", "")
    if file_path and os.path.isfile(file_path):
        try:
            content = Path(file_path).read_text(encoding="utf-8")
            lines = content.splitlines()
            line_no = info.get("line", 0)
            if 1 <= line_no <= len(lines):
                code = lines[line_no - 1]
                if code.rstrip() != code.rstrip("\n"):
                    suggestions.append(f"Linea {line_no}: posible trailing whitespace.")
                open_parens = code.count("(") + code.count("[") + code.count("{")
                close_parens = code.count(")") + code.count("]") + code.count("}")
                if open_parens > close_parens:
                    suggestions.append(f"Linea {line_no}: parentesis/bracket sin cerrar ({open_parens - close_parens} faltantes).")
                if code.rstrip().endswith(":") and line_no < len(lines) and lines[line_no].strip() == "":
                    suggestions.append(f"Linea {line_no}: bloque vacio despues de ':'. Agregar 'pass' o implementar.")
        except Exception:
            pass
    suggestions.append("Intentar: ast.parse() para localizar error exacto.")
    return suggestions


def _handle_name_error(info: dict, file_content: str = "") -> list:
    suggestions = []
    msg = info.get("message", "")
    m = re.search(r"name '(\w+)' is not defined", msg)
    if m:
        var_name = m.group(1)
        suggestions.append(f"Variable '{var_name}' no esta definida.")
        suggestions.append(f"Verificar que '{var_name}' esta declarada antes de usarla.")
        suggestions.append(f"Verificar imports: puede que falte un import de '{var_name}'.")
    return suggestions


def _handle_type_error(info: dict, file_content: str = "") -> list:
    suggestions = []
    msg = info.get("message", "")
    suggestions.append(f"TypeError: {msg}")
    if "argument" in msg and "positional" in msg:
        suggestions.append("Verificar cantidad de argumentos pasados a la funcion.")
    if "unsupported operand" in msg:
        suggestions.append("Verificar que los operandos son del tipo correcto (str/int/float).")
    if "NoneType" in msg:
        suggestions.append("Una variable es None cuando no deberia serlo. Verificar retorno de funciones.")
    return suggestions


def _handle_file_not_found(info: dict, file_content: str = "") -> list:
    suggestions = []
    msg = info.get("message", "")
    m = re.search(r"'(.+?)'", msg)
    if m:
        path = m.group(1)
        suggestions.append(f"Archivo no encontrado: {path}")
        if os.path.isabs(path):
            suggestions.append(f"Ruta absoluta: existe={os.path.exists(path)}")
        else:
            abs_path = _PROJECT_ROOT / path
            suggestions.append(f"Ruta relativa al proyecto: {abs_path} (existe={abs_path.exists()})")
    return suggestions


def _handle_attribute_error(info: dict, file_content: str = "") -> list:
    suggestions = []
    msg = info.get("message", "")
    m = re.search(r"'(\w+)' object has no attribute '(\w+)'", msg)
    if m:
        obj_type = m.group(1)
        attr = m.group(2)
        suggestions.append(f"El tipo '{obj_type}' no tiene atributo '{attr}'.")
        suggestions.append(f"Verificar si el objeto es de tipo correcto o si '{attr}' es un metodo/atributo valido.")
    return suggestions

_HANDLE_MAP = {
    "ImportError": _handle_import_error,
    "ModuleNotFoundError": _handle_module_not_found,
    "SyntaxError": _handle_syntax_error,
    "NameError": _handle_name_error,
    "TypeError": _handle_type_error,
    "FileNotFoundError": _handle_file_not_found,
    "AttributeError": _handle_attribute_error,
}


def _record_entry(journal: dict, entry: dict):
    journal.setdefault("entries", []).append(entry)
    journal.setdefault("stats", {})
    journal["stats"]["total_analyzed"] = journal["stats"].get("total_analyzed", 0) + 1
    if entry.get("fix_applied"):
        journal["stats"]["total_fixed"] = journal["stats"].get("total_fixed", 0) + 1


def _find_broken_imports() -> list:
    problems = []
    for py_file in _iter_py_files():
        try:
            content = py_file.read_text(encoding="utf-8")
            lines = content.splitlines()
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                if stripped.startswith("import ") or stripped.startswith("from "):
                    m = re.match(r'^(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))', stripped)
                    if m:
                        module = m.group(1) or m.group(2)
                        if module and module.split(".")[0] in ("core", "actions", "skills", "agents", "agent"):
                            mod_path = _PROJECT_ROOT / module.replace(".", "/")
                            pkg_path = _PROJECT_ROOT / module.replace(".", "/") / "__init__.py"
                            file_path = _PROJECT_ROOT / (module.replace(".", "/") + ".py")
                            if not mod_path.exists() and not pkg_path.exists() and not file_path.exists():
                                problems.append({
                                    "file": str(py_file.relative_to(_PROJECT_ROOT)),
                                    "line": i,
                                    "import_line": stripped,
                                    "module": module,
                                })
        except Exception:
            continue
    return problems


def _iter_py_files():
    for py_file in _PROJECT_ROOT.rglob("*.py"):
        parts = py_file.parts
        if any(d in _IGNORE_DIRS for d in parts):
            continue
        yield py_file


def _attempt_fix_syntax(file_path: str) -> tuple:
    try:
        content = Path(file_path).read_text(encoding="utf-8")
        original = content
        fixed = False
        for open_c, close_c in [("(", ")"), ("[", "]"), ("{", "}")]:
            if content.count(open_c) > content.count(close_c):
                diff = content.count(open_c) - content.count(close_c)
                content += close_c * diff
                fixed = True
        if content and not content.endswith("\n"):
            content += "\n"
            fixed = True
        if fixed:
            try:
                ast.parse(content)
                Path(file_path).write_text(content, encoding="utf-8")
                return True, "Sintaxis auto-arreglada (parentesis/final)."
            except SyntaxError:
                Path(file_path).write_text(original, encoding="utf-8")
                return False, "Fix reversado: no resolvio el error."
        return False, "No se detectaron problemas comunes para auto-fix."
    except Exception as e:
        return False, f"Error leyendo archivo: {e}"


def _get_error_frequency(journal: dict) -> dict:
    freq = defaultdict(lambda: {"count": 0, "files": set(), "first_seen": "", "last_seen": "", "fixes": 0})
    for entry in journal.get("entries", []):
        key = f"{entry.get('error_type', '?')}:{entry.get('message', '')[:80]}"
        freq[key]["count"] += 1
        freq[key]["files"].add(entry.get("file", "?"))
        freq[key]["last_seen"] = entry.get("timestamp", "")
        if not freq[key]["first_seen"]:
            freq[key]["first_seen"] = entry.get("timestamp", "")
        if entry.get("fix_success"):
            freq[key]["fixes"] += 1
    return dict(freq)

def auto_healer(parameters: dict = None, player=None) -> str:
    if parameters is None:
        parameters = {}
    action = parameters.get("action", "status")

    if action == "analyze":
        journal = _load_journal()
        tb_str = parameters.get("traceback_str", "")
        file_path = parameters.get("file_path", "")
        if not tb_str and file_path:
            try:
                content = Path(file_path).read_text(encoding="utf-8")
                ast.parse(content)
                tb_str = f"Analyzing file: {file_path}"
            except SyntaxError as e:
                tb_str = f"SyntaxError: {e}"
            except Exception as e:
                tb_str = str(e)
        if not tb_str:
            return "Se requiere 'traceback_str' o 'file_path' para analizar."
        info = _parse_traceback(tb_str)
        suggestions = []
        for etype, pattern in _HANDLE_MAP.items():
            if info["error_type"] == etype:
                handler = _HANDLE_MAP.get(etype)
                if handler:
                    suggestions = handler(info)
                break
        if not suggestions:
            suggestions = [
                f"Tipo: {info['error_type']}",
                f"Mensaje: {info['message']}",
                f"Archivo: {info['file'] or 'desconocido'}",
                f"Linea: {info['line'] or '?'}",
                "No se encontro patron conocido para auto-sugerencia.",
            ]
        entry = {
            "error_type": info["error_type"],
            "message": info["message"][:300],
            "file": info["file"],
            "line": info["line"],
            "timestamp": datetime.now().isoformat(),
            "suggestions": suggestions,
            "fix_applied": False,
            "fix_success": False,
            "occurrence_count": 1,
        }
        for existing in journal.get("entries", []):
            if existing.get("error_type") == info["error_type"] and existing.get("file") == info["file"]:
                existing["occurrence_count"] = existing.get("occurrence_count", 0) + 1
                existing["last_seen"] = datetime.now().isoformat()
                entry["occurrence_count"] = existing["occurrence_count"]
                break
        else:
            journal.setdefault("entries", []).append(entry)
        _record_entry(journal, entry)
        _save_journal(journal)
        lines = [f"=== ANALISIS: {info['error_type']} ==="]
        lines.append(f"  Archivo: {info['file'] or '?'}")
        lines.append(f"  Linea: {info['line'] or '?'}")
        lines.append(f"  Mensaje: {info['message'][:120]}")
        lines.append(f"  Veces visto: {entry['occurrence_count']}")
        if entry["occurrence_count"] >= 3:
            lines.append(f"  PATRON RECORRENTE detectado ({entry['occurrence_count']} veces)")
        lines.append("")
        lines.append("  Sugerencias:")
        for s in suggestions:
            lines.append(f"    - {s}")
        return "\n".join(lines)

    elif action == "fix_imports":
        dry_run = parameters.get("dry_run", True)
        problems = _find_broken_imports()
        if not problems:
            return "No se encontraron imports rotos."
        lines = [f"=== IMPORTS ROTOS: {len(problems)} ===", ""]
        for p in problems:
            lines.append(f"  {p['file']}:{p['line']}")
            lines.append(f"    {p['import_line']}")
            lines.append(f"    Modulo '{p['module']}' no encontrado.")
            lines.append("")
        if dry_run:
            lines.append("(dry_run=True: no se aplicaron cambios)")
        else:
            lines.append("(dry_run=False: se registraron en journal)")
            journal = _load_journal()
            for p in problems:
                entry = {
                    "error_type": "ModuleNotFoundError",
                    "message": f"Import roto: {p['module']}",
                    "file": p["file"],
                    "line": p["line"],
                    "timestamp": datetime.now().isoformat(),
                    "fix_applied": False,
                    "fix_success": False,
                    "occurrence_count": 1,
                }
                _record_entry(journal, entry)
            _save_journal(journal)
        return "\n".join(lines)

    elif action == "error_journal":
        journal = _load_journal()
        entries = journal.get("entries", [])
        if not entries:
            return "El journal de errores esta vacio."
        freq = _get_error_frequency(journal)
        lines = [f"=== ERROR JOURNAL: {len(entries)} entradas ===", ""]
        lines.append("  Patron mas comun:")
        sorted_freq = sorted(freq.items(), key=lambda x: -x[1]["count"])
        for key, data in sorted_freq[:10]:
            count = data["count"]
            files_count = len(data["files"])
            flag = " RECORRENTE" if count >= 3 else ""
            lines.append(f"    [{count}x] {key} ({files_count} archivo(s)){flag}")
        lines.append("")
        lines.append("  Ultimas 10 entradas:")
        for entry in entries[-10:]:
            ts = entry.get("timestamp", "?")[:19]
            etype = entry.get("error_type", "?")
            msg = entry.get("message", "")[:60]
            fpath = entry.get("file", "?")
            if fpath:
                fpath = str(Path(fpath).name)
            lines.append(f"    [{ts}] {etype} en {fpath}: {msg}")
        return "\n".join(lines)

    elif action == "auto_fix":
        error_type = parameters.get("error_type", "")
        file_path = parameters.get("file_path", "")
        if error_type == "SyntaxError" and file_path:
            ok, msg = _attempt_fix_syntax(file_path)
            journal = _load_journal()
            entry = {
                "error_type": "SyntaxError",
                "message": msg,
                "file": file_path,
                "line": 0,
                "timestamp": datetime.now().isoformat(),
                "fix_applied": True,
                "fix_success": ok,
                "occurrence_count": 1,
            }
            _record_entry(journal, entry)
            _save_journal(journal)
            return f"Auto-fix SyntaxError: {'EXITO' if ok else 'FALLO'}\n  {msg}"
        if error_type == "ModuleNotFoundError":
            module = parameters.get("module", "")
            if not module:
                return "Para ModuleNotFoundError se requiere 'module'."
            top = module.split(".")[0]
            suggestions = [
                f"pip install {top}",
                f"Verificar que '{module}' existe en el proyecto.",
                f"Verificar sys.path si es modulo local.",
            ]
            return "Sugerencias para '{}':\n  {}".format(module, "\n  ".join(suggestions))
        return "Auto-fix no disponible para tipo: {}\nTipos soportados: SyntaxError, ModuleNotFoundError".format(error_type or "(no especificado)")

    elif action == "suggest":
        journal = _load_journal()
        freq = _get_error_frequency(journal)
        suggestions = []
        for key, data in sorted(freq.items(), key=lambda x: -x[1]["count"]):
            count = data["count"]
            if count < 3:
                continue
            files_str = ", ".join(str(Path(f).name) for f in data["files"])
            error_type = key.split(":")[0] if ":" in key else key
            if count >= 5:
                suggestions.append(
                    f"CRITICO: '{error_type}' en {files_str} ha ocurrido {count} veces. "
                    f"Se recomienda agregar manejo de errores (try/except) o corregir la causa raiz."
                )
            else:
                suggestions.append(
                    f"ATENCION: '{error_type}' en {files_str} ha ocurrido {count} veces. "
                    f"Considerar verificar logs y corregir antes de que se vuelva cronico."
                )
        if not suggestions:
            return "No hay patrones criticos detectados. Todo parece estable."
        lines = [f"=== SUGERENCIAS ({len(suggestions)}) ===", ""]
        for s in suggestions:
            lines.append(f"  {s}")
        return "\n".join(lines)

    elif action == "status":
        journal = _load_journal()
        stats = journal.get("stats", {})
        entries = journal.get("entries", [])
        freq = _get_error_frequency(journal)
        recurring = sum(1 for d in freq.values() if d["count"] >= 3)
        unique_types = len(freq)
        lines = [
            "=== AUTO HEALER STATUS ===",
            "",
            f"  Errores analizados: {stats.get('total_analyzed', 0)}",
            f"  Fixes aplicados: {stats.get('total_fixed', 0)}",
            f"  Entradas en journal: {len(entries)}",
            f"  Tipos de error unicos: {unique_types}",
            f"  Patrones recurrentes (3+): {recurring}",
            "",
        ]
        if entries:
            last = entries[-1]
            lines.append(f"  Ultimo error: [{last.get('timestamp', '?')[:19]}] {last.get('error_type', '?')}")
        else:
            lines.append("  No hay errores registrados.")
        return "\n".join(lines)

    return (
        "Acciones: analyze | fix_imports | error_journal | auto_fix | suggest | status\n"
        "  analyze: traceback_str o file_path\n"
        "  fix_imports: dry_run (bool)\n"
        "  auto_fix: error_type, file_path (para SyntaxError), module (para ModuleNotFoundError)\n"
        "  suggest: analiza patron y sugiere mejoras\n"
        "  status: estadisticas generales"
    )
