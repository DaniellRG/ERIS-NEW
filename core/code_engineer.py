"""
ERIS Code Engineer — Code editing con contexto completo.

Reasoning loop: leer → entender → planificar → editar → verificar
Soporta: single-file edit, multi-file edit, create from scratch,
         insert after/before pattern, replace blocks, append, prepend.
"""
import os
import re
import time
import difflib
import hashlib
from pathlib import Path
from typing import Optional

_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "code_engineer"
_DATA_DIR.mkdir(parents=True, exist_ok=True)

_BACKUPS_DIR = _DATA_DIR / "backups"
_BACKUPS_DIR.mkdir(exist_ok=True)


def _backup_file(filepath: str) -> Optional[str]:
    """Create a backup before editing."""
    try:
        src = Path(filepath)
        if not src.exists():
            return None
        ts = time.strftime("%Y%m%d_%H%M%S")
        h = hashlib.md5(filepath.encode()).hexdigest()[:8]
        backup_name = f"{src.stem}_{ts}{src.suffix}.{h}.bak"
        backup_path = _BACKUPS_DIR / backup_name
        backup_path.write_bytes(src.read_bytes())
        return str(backup_path)
    except Exception:
        return None


def _read_file(filepath: str, offset: int = 0, limit: int = 0) -> dict:
    """Read a file with line numbers."""
    try:
        p = Path(filepath)
        if not p.exists():
            return {"ok": False, "error": f"File not found: {filepath}"}
        content = p.read_text(encoding="utf-8", errors="replace")
        lines = content.split("\n")
        total = len(lines)
        if offset > 0:
            lines = lines[offset - 1:]
        if limit > 0:
            lines = lines[:limit]
        numbered = [f"{i + offset}: {l}" for i, l in enumerate(lines)]
        return {"ok": True, "content": "\n".join(numbered), "total_lines": total, "shown": len(lines)}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


def _find_pattern(filepath: str, pattern: str) -> list:
    """Find lines matching a regex pattern."""
    try:
        content = Path(filepath).read_text(encoding="utf-8", errors="replace")
        matches = []
        regex = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
        for i, line in enumerate(content.split("\n"), 1):
            if regex.search(line):
                matches.append({"line": i, "content": line.rstrip()})
        return matches
    except Exception:
        return []


def _edit_file(filepath: str, old_text: str, new_text: str) -> dict:
    """Replace exact text in a file."""
    try:
        p = Path(filepath)
        if not p.exists():
            return {"ok": False, "error": f"File not found: {filepath}"}
        content = p.read_text(encoding="utf-8", errors="replace")
        if old_text not in content:
            # Try to find similar text
            lines = content.split("\n")
            old_lines = old_text.split("\n")
            for i, line in enumerate(lines):
                if old_lines[0].strip() and old_lines[0].strip() in line:
                    return {"ok": False, "error": f"Pattern found at line {i+1} but not exact match. Show more context.",
                            "hint_line": i + 1, "hint_content": line.rstrip()}
            return {"ok": False, "error": "Pattern not found in file."}
        count = content.count(old_text)
        if count > 1:
            return {"ok": False, "error": f"Pattern found {count} times. Need more context to make it unique."}
        backup = _backup_file(filepath)
        new_content = content.replace(old_text, new_text, 1)
        p.write_text(new_content, encoding="utf-8")
        old_lines = old_text.count("\n") + 1
        new_lines = new_text.count("\n") + 1
        return {"ok": True, "lines_changed": abs(new_lines - old_lines), "backup": backup}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


def _insert_in_file(filepath: str, after_text: str, insert_text: str, before_text: str = None) -> dict:
    """Insert text after (or before) a pattern."""
    try:
        p = Path(filepath)
        if not p.exists():
            return {"ok": False, "error": f"File not found: {filepath}"}
        content = p.read_text(encoding="utf-8", errors="replace")
        if before_text:
            if before_text not in content:
                return {"ok": False, "error": "before_text not found."}
            backup = _backup_file(filepath)
            content = content.replace(before_text, insert_text + "\n" + before_text, 1)
        elif after_text:
            if after_text not in content:
                return {"ok": False, "error": "after_text not found."}
            backup = _backup_file(filepath)
            content = content.replace(after_text, after_text + "\n" + insert_text, 1)
        else:
            return {"ok": False, "error": "Need 'after_text' or 'before_text'."}
        p.write_text(content, encoding="utf-8")
        return {"ok": True, "backup": backup}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


def _create_file(filepath: str, content: str) -> dict:
    """Create a new file."""
    try:
        p = Path(filepath)
        if p.exists():
            return {"ok": False, "error": f"File already exists: {filepath}"}
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        lines = content.count("\n") + 1
        return {"ok": True, "created": filepath, "lines": lines}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


def _multi_edit(filepath: str, edits: list) -> dict:
    """Apply multiple sequential edits to a file. Each edit: {old, new}."""
    try:
        p = Path(filepath)
        if not p.exists():
            return {"ok": False, "error": f"File not found: {filepath}"}
        content = p.read_text(encoding="utf-8", errors="replace")
        backup = _backup_file(filepath)
        applied = 0
        for edit in edits:
            old = edit.get("old", "")
            new = edit.get("new", "")
            if old and old in content:
                content = content.replace(old, new, 1)
                applied += 1
        p.write_text(content, encoding="utf-8")
        return {"ok": True, "edits_applied": applied, "total_edits": len(edits), "backup": backup}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


def _get_diff(filepath: str, old_text: str, new_text: str) -> str:
    """Show a unified diff preview without applying."""
    old_lines = old_text.splitlines(keepends=True)
    new_lines = new_text.splitlines(keepends=True)
    diff = difflib.unified_diff(old_lines, new_lines, fromfile=f"before/{filepath}", tofile=f"after/{filepath}", lineterm="")
    return "".join(diff)


def code_engineer(parameters: dict = None, player=None) -> str:
    """Tool entry point — full reasoning loop for code editing."""
    params = parameters or {}
    action = params.get("action", "read").lower()

    if action == "read":
        filepath = params.get("file", "")
        if not filepath:
            return "Necesito 'file' para leer."
        offset = int(params.get("offset", 0))
        limit = int(params.get("limit", 0))
        result = _read_file(filepath, offset, limit)
        if not result["ok"]:
            return result["error"]
        return f"Archivo: {filepath} (líneas {offset+1}-{offset+result['shown']}/{result['total_lines']})\n\n{result['content']}"

    elif action == "search":
        filepath = params.get("file", "")
        pattern = params.get("pattern", "")
        if not filepath or not pattern:
            return "Necesito 'file' y 'pattern'."
        matches = _find_pattern(filepath, pattern)
        if not matches:
            return f"Sin coincidencias para '{pattern}' en {filepath}"
        return f"Coincidencias ({len(matches)}):\n" + "\n".join(f"  L{m['line']}: {m['content']}" for m in matches[:50])

    elif action == "edit":
        filepath = params.get("file", "")
        old_text = params.get("old", "")
        new_text = params.get("new", "")
        if not all([filepath, old_text, new_text]):
            return "Necesito 'file', 'old' y 'new'."
        # Show diff first if requested
        if params.get("preview", "false").lower() == "true":
            p = Path(filepath)
            if p.exists():
                content = p.read_text(encoding="utf-8", errors="replace")
                if old_text in content:
                    preview_content = content.replace(old_text, new_text, 1)
                    diff = _get_diff(filepath, content, preview_content)
                    return f"Vista previa del diff:\n\n{diff[:3000]}"
        result = _edit_file(filepath, old_text, new_text)
        if not result["ok"]:
            return result["error"]
        return f"Editado: {filepath} ({result['lines_changed']} líneas cambiadas)"

    elif action == "insert":
        filepath = params.get("file", "")
        insert_text = params.get("text", "")
        if not filepath or not insert_text:
            return "Necesito 'file' y 'text'."
        result = _insert_in_file(filepath, params.get("after", ""), insert_text, params.get("before"))
        if not result["ok"]:
            return result["error"]
        return f"Insertado en {filepath}"

    elif action == "create":
        filepath = params.get("file", "")
        content = params.get("content", "")
        if not filepath or not content:
            return "Necesito 'file' y 'content'."
        result = _create_file(filepath, content)
        if not result["ok"]:
            return result["error"]
        return f"Creado: {filepath} ({result['lines']} líneas)"

    elif action == "multi_edit":
        filepath = params.get("file", "")
        edits_raw = params.get("edits", "[]")
        if not filepath:
            return "Necesito 'file'."
        try:
            import json
            edits = json.loads(edits_raw) if isinstance(edits_raw, str) else edits_raw
        except Exception:
            return "Error parseando 'edits'. Debe ser JSON array de {old, new}."
        result = _multi_edit(filepath, edits)
        if not result["ok"]:
            return result["error"]
        return f"Multi-edit: {result['edits_applied']}/{result['total_edits']} edits aplicados en {filepath}"

    elif action == "backup_list":
        backups = sorted(_BACKUPS_DIR.glob("*.bak"), reverse=True)[:20]
        if not backups:
            return "Sin backups."
        return "Backups recientes:\n" + "\n".join(f"  - {b.name}" for b in backups)

    elif action == "restore":
        backup_name = params.get("backup", "")
        target = params.get("file", "")
        if not backup_name or not target:
            return "Necesito 'backup' (nombre) y 'file' (destino)."
        backup_path = _BACKUPS_DIR / backup_name
        if not backup_path.exists():
            return f"Backup no encontrado: {backup_name}"
        content = backup_path.read_text(encoding="utf-8", errors="replace")
        Path(target).write_text(content, encoding="utf-8")
        return f"Restaurado: {backup_name} → {target}"

    return f"Acción '{action}' no reconocida. Usa: read, search, edit, insert, create, multi_edit, backup_list, restore"
