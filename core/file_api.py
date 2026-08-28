"""
core/file_api.py — Unified file operations API for ERIS.

Merges the functionality of file_editor.py, file_controller.py,
and code_engineer.py into a single coherent interface.

All file operations in one place with AST validation,
backup management, and consistent parameter schemas.
"""
from __future__ import annotations

import ast
import os
import shutil
import time
import re
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent
BACKUP_DIR = BASE_DIR / "data" / "backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

MAX_READ_CHARS = 100_000
MAX_BACKUPS = 20


class FileResult:
    def __init__(self, success: bool, message: str, data: any = None):
        self.success = success
        self.message = message
        self.data = data

    def __str__(self):
        return self.message


# ── READ ──────────────────────────────────────────────────────────────────────

def read_file(filepath: str, offset: int = 0, limit: int = 0) -> FileResult:
    """Read a file with optional line offset and limit."""
    try:
        p = Path(filepath)
        if not p.exists():
            return FileResult(False, f"Archivo no existe: {filepath}")
        if p.stat().st_size > MAX_READ_CHARS * 2:
            return FileResult(False, f"Archivo muy grande: {p.stat().st_size} bytes")

        with open(p, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        total = len(lines)
        if offset > 0:
            lines = lines[offset - 1:]
        if limit > 0:
            lines = lines[:limit]

        content = "".join(lines)
        return FileResult(True, content, {"total_lines": total, "shown": len(lines)})
    except Exception as e:
        return FileResult(False, f"Error leyendo archivo: {e}")


# ── WRITE ─────────────────────────────────────────────────────────────────────

def write_file(filepath: str, content: str, backup: bool = True) -> FileResult:
    """Write content to a file. Creates backup if file exists."""
    try:
        p = Path(filepath)
        p.parent.mkdir(parents=True, exist_ok=True)

        if backup and p.exists():
            _make_backup(filepath)

        with open(p, "w", encoding="utf-8") as f:
            f.write(content)

        return FileResult(True, f"Escrito: {filepath} ({len(content)} chars)")
    except Exception as e:
        return FileResult(False, f"Error escribiendo: {e}")


# ── EDIT (surgical) ──────────────────────────────────────────────────────────

def edit_file(filepath: str, old_text: str, new_text: str, validate_ast: bool = False) -> FileResult:
    """Surgically edit a file by replacing exact text. Validates with AST if requested."""
    try:
        p = Path(filepath)
        if not p.exists():
            return FileResult(False, f"Archivo no existe: {filepath}")

        with open(p, "r", encoding="utf-8") as f:
            source = f.read()

        if old_text not in source:
            return FileResult(False, "Texto no encontrado en el archivo")

        count = source.count(old_text)
        if count > 1:
            return FileResult(False, f"El texto aparece {count} veces — no puedo hacer edit seguro")

        new_source = source.replace(old_text, new_text, 1)

        if validate_ast:
            try:
                ast.parse(new_source)
            except SyntaxError as e:
                return FileResult(False, f"El edit genera syntax error: {e}")

        _make_backup(filepath)

        with open(p, "w", encoding="utf-8") as f:
            f.write(new_source)

        return FileResult(True, f"Edit aplicado en {filepath}")
    except Exception as e:
        return FileResult(False, f"Error en edit: {e}")


def multi_edit(filepath: str, edits: list[dict], validate_ast: bool = False) -> FileResult:
    """Apply multiple edits to a file in order. Each edit: {"old": ..., "new": ...}."""
    try:
        p = Path(filepath)
        if not p.exists():
            return FileResult(False, f"Archivo no existe: {filepath}")

        with open(p, "r", encoding="utf-8") as f:
            source = f.read()

        for i, ed in enumerate(edits):
            old = ed.get("old", "")
            new = ed.get("new", "")
            if old not in source:
                return FileResult(False, f"Edit {i+1}: texto no encontrado")
            if source.count(old) > 1:
                return FileResult(False, f"Edit {i+1}: texto ambiguo ({source.count(old)} ocurrencias)")
            source = source.replace(old, new, 1)

        if validate_ast:
            try:
                ast.parse(source)
            except SyntaxError as e:
                return FileResult(False, f"Los edits generan syntax error: {e}")

        _make_backup(filepath)
        with open(p, "w", encoding="utf-8") as f:
            f.write(source)

        return FileResult(True, f"{len(edits)} edits aplicados en {filepath}")
    except Exception as e:
        return FileResult(False, f"Error en multi_edit: {e}")


def insert_in_file(filepath: str, after: str = "", before: str = "", text: str = "") -> FileResult:
    """Insert text after or before a pattern in a file."""
    try:
        p = Path(filepath)
        if not p.exists():
            return FileResult(False, f"Archivo no existe: {filepath}")

        with open(p, "r", encoding="utf-8") as f:
            source = f.read()

        if after:
            if after not in source:
                return FileResult(False, f"Patrón 'after' no encontrado: {after}")
            new_source = source.replace(after, after + text, 1)
        elif before:
            if before not in source:
                return FileResult(False, f"Patrón 'before' no encontrado: {before}")
            new_source = source.replace(before, text + before, 1)
        else:
            return FileResult(False, "Especificá 'after' o 'before'")

        _make_backup(filepath)
        with open(p, "w", encoding="utf-8") as f:
            f.write(new_source)

        return FileResult(True, f"Texto insertado en {filepath}")
    except Exception as e:
        return FileResult(False, f"Error insertando: {e}")


# ── DELETE ────────────────────────────────────────────────────────────────────

def delete_file(filepath: str, backup: bool = True) -> FileResult:
    """Delete a file (with optional backup)."""
    try:
        p = Path(filepath)
        if not p.exists():
            return FileResult(False, f"Archivo no existe: {filepath}")

        if backup:
            _make_backup(filepath)

        if p.is_dir():
            shutil.rmtree(p)
            return FileResult(True, f"Directorio eliminado: {filepath}")
        else:
            p.unlink()
            return FileResult(True, f"Archivo eliminado: {filepath}")
    except Exception as e:
        return FileResult(False, f"Error eliminando: {e}")


# ── DIRECTORY ─────────────────────────────────────────────────────────────────

def list_dir(filepath: str = ".", pattern: str = "") -> FileResult:
    """List directory contents with optional glob pattern."""
    try:
        p = Path(filepath)
        if not p.exists():
            return FileResult(False, f"Directorio no existe: {filepath}")
        if not p.is_dir():
            return FileResult(False, f"No es directorio: {filepath}")

        if pattern:
            items = sorted(p.glob(pattern))
        else:
            items = sorted(p.iterdir())

        result = []
        for item in items:
            kind = "dir" if item.is_dir() else "file"
            size = item.stat().st_size if item.is_file() else 0
            result.append({"name": item.name, "type": kind, "size": size, "path": str(item)})

        listing = "\n".join(f"{'[D]' if r['type'] == 'dir' else '   '} {r['name']} ({r['size']}B)" for r in result)
        return FileResult(True, listing, result)
    except Exception as e:
        return FileResult(False, f"Error listando directorio: {e}")


def create_dir(filepath: str) -> FileResult:
    """Create a directory (including parents)."""
    try:
        Path(filepath).mkdir(parents=True, exist_ok=True)
        return FileResult(True, f"Directorio creado: {filepath}")
    except Exception as e:
        return FileResult(False, f"Error creando directorio: {e}")


# ── SEARCH ────────────────────────────────────────────────────────────────────

def grep_files(directory: str, pattern: str, file_pattern: str = "*.py") -> FileResult:
    """Search for pattern in files matching file_pattern."""
    try:
        d = Path(directory)
        if not d.exists():
            return FileResult(False, f"Directorio no existe: {directory}")

        matches = []
        regex = re.compile(pattern, re.IGNORECASE)
        for f in d.rglob(file_pattern):
            if f.stat().st_size > MAX_READ_CHARS:
                continue
            try:
                with open(f, "r", encoding="utf-8", errors="replace") as fh:
                    for i, line in enumerate(fh, 1):
                        if regex.search(line):
                            matches.append({"file": str(f), "line": i, "text": line.rstrip()[:200]})
            except Exception:
                continue

        if not matches:
            return FileResult(True, "Sin resultados")

        output = "\n".join(f"{m['file']}:{m['line']}: {m['text']}" for m in matches[:100])
        return FileResult(True, output, matches)
    except Exception as e:
        return FileResult(False, f"Error en grep: {e}")


def glob_files(directory: str, pattern: str) -> FileResult:
    """Find files matching a glob pattern."""
    try:
        d = Path(directory)
        if not d.exists():
            return FileResult(False, f"Directorio no existe: {directory}")

        files = sorted(str(f) for f in d.rglob(pattern) if f.is_file())
        if not files:
            return FileResult(True, "Sin resultados")

        output = "\n".join(files[:200])
        return FileResult(True, output, files)
    except Exception as e:
        return FileResult(False, f"Error en glob: {e}")


# ── MOVE / COPY / RENAME ────────────────────────────────────────────────────

def move_file(src: str, dst: str) -> FileResult:
    try:
        shutil.move(src, dst)
        return FileResult(True, f"Movido: {src} → {dst}")
    except Exception as e:
        return FileResult(False, f"Error moviendo: {e}")


def copy_file(src: str, dst: str) -> FileResult:
    try:
        shutil.copy2(src, dst)
        return FileResult(True, f"Copiado: {src} → {dst}")
    except Exception as e:
        return FileResult(False, f"Error copiando: {e}")


def rename_file(src: str, new_name: str) -> FileResult:
    try:
        p = Path(src)
        if not p.exists():
            return FileResult(False, f"Archivo no existe: {src}")
        new_path = p.parent / new_name
        p.rename(new_path)
        return FileResult(True, f"Renombrado: {src} → {new_path}")
    except Exception as e:
        return FileResult(False, f"Error renombrando: {e}")


# ── INFO ──────────────────────────────────────────────────────────────────────

def file_info(filepath: str) -> FileResult:
    try:
        p = Path(filepath)
        if not p.exists():
            return FileResult(False, f"Archivo no existe: {filepath}")
        stat = p.stat()
        info = {
            "path": str(p.absolute()),
            "name": p.name,
            "extension": p.suffix,
            "is_file": p.is_file(),
            "is_dir": p.is_dir(),
            "size": stat.st_size,
            "modified": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime)),
            "created": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_ctime)),
        }
        return FileResult(True, json.dumps(info, indent=2), info)
    except Exception as e:
        return FileResult(False, f"Error: {e}")


# ── BACKUP ────────────────────────────────────────────────────────────────────

def _make_backup(filepath: str):
    """Create a timestamped backup of a file."""
    try:
        p = Path(filepath)
        if not p.exists():
            return
        ts = time.strftime("%Y%m%d_%H%M%S")
        safe_name = str(p.name).replace("/", "_").replace("\\", "_")
        backup_path = BACKUP_DIR / f"{safe_name}.{ts}.bak"
        shutil.copy2(p, backup_path)

        # Clean old backups (keep MAX_BACKUPS per file)
        backups = sorted(BACKUP_DIR.glob(f"{safe_name}.*.bak"))
        while len(backups) > MAX_BACKUPS:
            backups[0].unlink()
            backups.pop(0)
    except Exception:
        pass


def list_backups(filepath: str = "") -> FileResult:
    """List backups, optionally filtered by filename."""
    try:
        if filepath:
            name = Path(filepath).name
            backups = sorted(BACKUP_DIR.glob(f"{name}.*.bak"), reverse=True)
        else:
            backups = sorted(BACKUP_DIR.glob("*.bak"), reverse=True)

        result = [{"name": b.name, "size": b.stat().st_size, "time": b.stat().st_mtime} for b in backups[:50]]
        output = "\n".join(f"{r['name']} ({r['size']}B)" for r in result)
        return FileResult(True, output or "Sin backups", result)
    except Exception as e:
        return FileResult(False, f"Error: {e}")


def restore_backup(backup_name: str, target_path: str) -> FileResult:
    """Restore a backup to its original location."""
    try:
        src = BACKUP_DIR / backup_name
        if not src.exists():
            return FileResult(False, f"Backup no existe: {backup_name}")
        shutil.copy2(src, target_path)
        return FileResult(True, f"Restaurado: {backup_name} → {target_path}")
    except Exception as e:
        return FileResult(False, f"Error restaurando: {e}")


# ── UNIFIED DISPATCH ──────────────────────────────────────────────────────────

import json

def file_api(params: dict) -> str:
    """
    Unified file operations dispatcher.
    
    Actions: read, write, edit, multi_edit, insert, delete,
             list, mkdir, grep, glob, move, copy, rename, info,
             backups, restore
    """
    action = params.get("action", "read")
    filepath = params.get("path", "") or params.get("file", "") or params.get("filepath", "")

    if action == "read":
        r = read_file(filepath, params.get("offset", 0), params.get("limit", 0))
    elif action == "write":
        r = write_file(filepath, params.get("content", ""), params.get("backup", True))
    elif action == "edit":
        r = edit_file(filepath, params.get("old", "") or params.get("old_text", ""),
                       params.get("new", "") or params.get("new_text", ""),
                       params.get("validate_ast", False))
    elif action == "multi_edit":
        r = multi_edit(filepath, params.get("edits", []), params.get("validate_ast", False))
    elif action == "insert":
        r = insert_in_file(filepath, params.get("after", ""), params.get("before", ""), params.get("text", ""))
    elif action == "delete":
        r = delete_file(filepath, params.get("backup", True))
    elif action == "list":
        r = list_dir(filepath or ".", params.get("pattern", ""))
    elif action == "mkdir":
        r = create_dir(filepath)
    elif action == "grep":
        r = grep_files(filepath or ".", params.get("pattern", ""), params.get("file_pattern", "*.py"))
    elif action == "glob":
        r = glob_files(filepath or ".", params.get("pattern", "*"))
    elif action == "move":
        r = move_file(filepath, params.get("destination", "") or params.get("dst", ""))
    elif action == "copy":
        r = copy_file(filepath, params.get("destination", "") or params.get("dst", ""))
    elif action == "rename":
        r = rename_file(filepath, params.get("new_name", ""))
    elif action == "info":
        r = file_info(filepath)
    elif action == "backups":
        r = list_backups(filepath)
    elif action == "restore":
        r = restore_backup(params.get("backup_name", ""), filepath)
    else:
        return f"Acción desconocida: {action}. Disponibles: read, write, edit, multi_edit, insert, delete, list, mkdir, grep, glob, move, copy, rename, info, backups, restore"

    return str(r.message) if not r.success else (r.message[:3000] if isinstance(r.message, str) else str(r.message)[:3000])
