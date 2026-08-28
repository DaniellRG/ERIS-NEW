# -*- coding: utf-8 -*-
"""
file_editor.py — Edición quirúrgica y búsqueda avanzada en archivos.

Diferencias frente a file_controller:
  * edit con VERIFICACIÓN DE UNICIDAD: si old_text aparece 0 o N veces, la
    edición se rechaza (no hay ediciones ambiguas ni destructivas).
  * backup automático antes de cada edición/escritura + diff del cambio.
  * grep con conteo, ignore_case, límite de archivos y contexto.
  * glob recursivo con límites.
"""
from __future__ import annotations

import difflib
import glob
import os
import re
from datetime import datetime

BACKUP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "memory", "editor_backups")

_PY_EXTS = {".py", ".pyw"}


def resolve_path(p: str) -> str:
    if not p:
        return os.getcwd()
    shortcuts = {
        "desktop": os.path.expanduser("~/Desktop"),
        "escritorio": os.path.expanduser("~/Desktop"),
        "downloads": os.path.expanduser("~/Downloads"),
        "descargas": os.path.expanduser("~/Downloads"),
        "documents": os.path.expanduser("~/Documents"),
        "documentos": os.path.expanduser("~/Documents"),
        "home": os.path.expanduser("~"),
        "casa": os.path.expanduser("~"),
    }
    key = p.strip().lower()
    if key in shortcuts:
        return shortcuts[key]
    if p == ".":
        return os.getcwd()
    if key.startswith("eris:"):
        return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            p.split(":", 1)[1].lstrip("/\\"))
    return os.path.abspath(os.path.expanduser(p))


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def _backup(path: str) -> str | None:
    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        name = os.path.basename(path)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        target = os.path.join(BACKUP_DIR, f"{stamp}__{name}")
        with open(path, "rb") as src, open(target, "wb") as dst:
            dst.write(src.read())
        return target
    except Exception:
        return None


def _pycheck(path: str) -> str:
    if os.path.splitext(path)[1].lower() not in _PY_EXTS:
        return ""
    try:
        import py_compile
        py_compile.compile(path, doraise=True)
        return "\n[PY_COMPILE] Sintaxis OK"
    except py_compile.PyCompileError as e:
        return f"\n[PY_COMPILE] ERROR: {str(e)[:300]}"


def _diff(original: str, modified: str, path: str) -> str:
    diff = list(difflib.unified_diff(original.splitlines(), modified.splitlines(),
                                     "antes", "despues", lineterm=""))
    return f"\nDiff ({len(diff)} lineas):\n" + "\n".join(diff[:60])


def _action_read(parameters: dict, player=None) -> str:
    path = resolve_path(parameters.get("path") or ".")
    base = resolve_path(parameters.get("base_path") or "") or path
    target = os.path.join(base, path) if path != base and not os.path.exists(path) and os.path.isdir(base) else path
    if not os.path.exists(target):
        return f"Error: '{target}' no existe."
    if os.path.isdir(target):
        try:
            items = sorted(os.listdir(target))
        except Exception as e:
            return f"Error listando: {e}"
        head = [f"{i}  {'/' if os.path.isdir(os.path.join(target, i)) else ''}" for i in items[:100]]
        return f"Directorio {target} ({len(items)} entradas):\n" + "\n".join(head)
    try:
        content = _read(target)
    except Exception as e:
        return f"Error leyendo: {e}"
    lines = content.splitlines()
    offset = int(parameters.get("offset") or 1)
    limit = int(parameters.get("limit") or 0)
    if limit and limit > 0:
        chunk = lines[max(0, offset - 1): offset - 1 + limit]
        numbered = [f"{i}: {ln}" for i, ln in enumerate(chunk, offset)]
        return f"{os.path.basename(target)} ({len(lines)} lineas):\n" + "\n".join(numbered)
    return f"{os.path.basename(target)} ({len(lines)} lineas, {len(content)} chars):\n" + content[:5000]


def _action_write(parameters: dict, player=None) -> str:
    path = parameters.get("path") or ""
    content = parameters.get("content") or ""
    if not path:
        return "Error: se requiere 'path'."
    target = resolve_path(path)
    bdir = os.path.dirname(target)
    if bdir:
        os.makedirs(bdir, exist_ok=True)
    original = ""
    if os.path.exists(target):
        try:
            original = _read(target)
        except Exception:
            original = ""
    backup = _backup(target) if os.path.exists(target) else None
    with open(target, "w", encoding="utf-8", errors="replace") as f:
        f.write(content)
    out = f"Escrito: {target} ({len(content)} chars)"
    if backup:
        out += f" | backup: {os.path.basename(backup)}"
    if original and original != content:
        out += _diff(original, content, target)
    out += _pycheck(target)
    return out


def _action_edit(parameters: dict, player=None) -> str:
    path = parameters.get("path") or ""
    old_text = parameters.get("old_text") or ""
    new_text = parameters.get("new_text") or ""
    if not path or not old_text:
        return "Error: se requieren 'path' y 'old_text'."
    target = resolve_path(path)
    if not os.path.exists(target):
        return f"Error: '{target}' no existe."
    original = _read(target)
    count = original.count(old_text)
    if count == 0:
        return f"Error: old_text no encontrado en {target} (0 coincidencias)."
    if count > 1:
        return (f"Error: old_text es ambiguo ({count} coincidencias en {target}). "
                f"Incluye más contexto en 'old_text'.")
    backup = _backup(target)
    modified = original.replace(old_text, new_text, 1)
    with open(target, "w", encoding="utf-8", errors="replace") as f:
        f.write(modified)
    out = f"Editado (1 coincidencia unica): {target}"
    if backup:
        out += f"\nbackup: {os.path.basename(backup)}"
    out += _diff(original, modified, target)
    out += _pycheck(target)
    try:
        from core.edit_journal import log as _jlog
        _jlog("edit", target, old_text[:60])
    except Exception:
        pass
    return out


def _action_grep(parameters: dict, player=None) -> str:
    pattern = parameters.get("pattern") or ""
    base = resolve_path(parameters.get("base_path") or ".")
    ignore_case = bool(parameters.get("ignore_case", True))
    max_files = int(parameters.get("max_files") or 500)
    if not pattern:
        return "Error: se requiere 'pattern' (regex)."
    try:
        rx = re.compile(pattern, re.IGNORECASE if ignore_case else 0)
    except re.error as e:
        return f"Error en regex: {e}"
    exts = {".py", ".pyw", ".js", ".ts", ".tsx", ".json", ".md", ".txt", ".html", ".css", ".bat", ".ps1", ".sh", ".ini", ".toml", ".yaml", ".yml"}
    matches = []
    scanned = 0
    total = 0
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "__pycache__", "venv", ".venv")]
        for fn in files:
            if scanned >= max_files:
                break
            if os.path.splitext(fn)[1].lower() not in exts:
                continue
            scanned += 1
            fp = os.path.join(root, fn)
            try:
                with open(fp, "r", encoding="utf-8", errors="replace") as f:
                    for i, line in enumerate(f, 1):
                        if rx.search(line):
                            matches.append(f"{os.path.relpath(fp, base)}:{i}: {line.rstrip()[:200]}")
                            total += 1
                            if total >= 60:
                                break
                    if total >= 60:
                        break
            except Exception:
                continue
        if total >= 60 or scanned >= max_files:
            break
    if not matches:
        return f"Sin coincidencias para /{pattern}/ en {base}."
    head = [f"Coincidencias /{pattern}/ ({total}, archivos: {scanned}):"]
    return "\n".join(head + matches)


def _action_glob(parameters: dict, player=None) -> str:
    gpat = parameters.get("glob_pattern") or ""
    base = resolve_path(parameters.get("base_path") or ".")
    if not gpat:
        return "Error: se requiere 'glob_pattern' (ej: **/*.py)."
    hits = glob.glob(os.path.join(base, gpat), recursive=True)[:200]
    if not hits:
        return f"Sin coincidencias para {gpat} en {base}."
    rel = [os.path.relpath(h, base) for h in hits]
    return f"Glob {gpat} ({len(hits)}):\n" + "\n".join(rel[:100])


handlers = {"read": _action_read, "write": _action_write, "edit": _action_edit,
            "grep": _action_grep, "glob": _action_glob,}


def file_editor(parameters: dict = None, player=None) -> str:
    """Herramienta de edición quirúrgica y búsqueda. Acciones: read (leer archivo/directorio con offset/limit),
    write (escribir archivo con backup+diff), edit (reemplazo UNICO con verificación de ambigüedad),
    grep (regex en árbol, ignore_case), glob (patrón recursivo)."""
    action = str(parameters.get("action") or "read").lower() if parameters else "read"
    fn = handlers.get(action)
    if fn is None:
        return f"Accion no valida: {action}. Disponibles: {', '.join(sorted(handlers))}."
    if player:
        try:
            player.write_log(f"[file_editor] {action} {parameters.get('path') or parameters.get('base_path') or ''}")
        except Exception:
            pass
    return fn(parameters)
