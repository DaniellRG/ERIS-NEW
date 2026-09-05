"""
ERIS Refactoring Engine — Refactoring masivo multi-archivo.

Capacidades:
- Rename: renombrar función/clase/variable en todos los archivos
- Move: mover archivo y actualizar imports
- Extract: extraer bloque de código a función separada
- Find usages: encontrar todos los usos antes de renombrar
- Bulk rename: renombrar múltiples things de una vez
"""
import os
import re
import time
import shutil
from pathlib import Path
from typing import Optional

_WORKSPACE = Path(os.environ.get("ERIS_WORKSPACE",
                                 str(Path(__file__).resolve().parent.parent)))
_BACKUPS_DIR = Path(__file__).resolve().parent.parent / "data" / "code_engineer" / "backups"
_BACKUPS_DIR.mkdir(parents=True, exist_ok=True)


def _backup_file(filepath: str) -> Optional[str]:
    try:
        src = Path(filepath)
        if not src.exists():
            return None
        ts = time.strftime("%Y%m%d_%H%M%S")
        import hashlib
        h = hashlib.md5(filepath.encode()).hexdigest()[:8]
        backup_path = _BACKUPS_DIR / f"{src.stem}_{ts}{src.suffix}.{h}.bak"
        backup_path.write_bytes(src.read_bytes())
        return str(backup_path)
    except Exception:
        return None


def _find_python_files(path: str = None) -> list:
    search_path = Path(path) if path else _WORKSPACE
    files = []
    for root, dirs, filenames in os.walk(search_path):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in
                   ("__pycache__", "node_modules", ".git", ".venv", "venv", "chroma_db")]
        for f in filenames:
            if f.endswith((".py", ".js", ".ts")):
                files.append(str(Path(root) / f))
    return files


def _rename_symbol(old_name: str, new_name: str, file_filter: str = None, dry_run: bool = False) -> dict:
    """Rename a symbol across all files."""
    files = _find_python_files()
    if file_filter:
        files = [f for f in files if file_filter in f]

    changes = []
    for filepath in files:
        try:
            content = Path(filepath).read_text(encoding="utf-8", errors="replace")
            # Word-boundary replacement
            pattern = rf"\b{re.escape(old_name)}\b"
            if re.search(pattern, content):
                new_content = re.sub(pattern, new_name, content)
                if new_content != content:
                    changes.append({
                        "file": str(Path(filepath).relative_to(_WORKSPACE)),
                        "replacements": content.count(old_name) - new_content.count(old_name) + new_content.count(new_name) - content.count(new_name),
                    })
                    if not dry_run:
                        _backup_file(filepath)
                        Path(filepath).write_text(new_content, encoding="utf-8")
        except Exception:
            continue

    return {
        "ok": len(changes) > 0,
        "dry_run": dry_run,
        "old_name": old_name,
        "new_name": new_name,
        "files_changed": len(changes),
        "changes": changes,
    }


def _move_file(source: str, destination: str, update_imports: bool = True) -> dict:
    """Move a file and update all imports referencing it."""
    src = Path(source)
    dst = Path(destination)
    if not src.exists():
        return {"ok": False, "error": f"Source not found: {source}"}
    if dst.exists():
        return {"ok": False, "error": f"Destination exists: {destination}"}

    # Backup
    _backup_file(str(src))

    # Get old module path relative to workspace
    old_module = str(src.relative_to(_WORKSPACE)).replace(os.sep, "/").replace("/", ".").replace(".py", "")
    new_module = str(dst.relative_to(_WORKSPACE)).replace(os.sep, "/").replace("/", ".").replace(".py", "")

    # Move
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))

    # Update imports
    import_changes = 0
    if update_imports:
        files = _find_python_files()
        for filepath in files:
            try:
                content = Path(filepath).read_text(encoding="utf-8", errors="replace")
                new_content = content.replace(old_module, new_module)
                if new_content != content:
                    _backup_file(filepath)
                    Path(filepath).write_text(new_content, encoding="utf-8")
                    import_changes += 1
            except Exception:
                continue

    return {
        "ok": True,
        "source": source,
        "destination": destination,
        "old_module": old_module,
        "new_module": new_module,
        "import_updates": import_changes,
    }


def _extract_function(filepath: str, start_line: int, end_line: int, function_name: str,
                      params: str = "", indent: int = 0) -> dict:
    """Extract a block of code into a new function."""
    try:
        p = Path(filepath)
        content = p.read_text(encoding="utf-8", errors="replace")
        lines = content.split("\n")

        if start_line < 1 or end_line > len(lines) or start_line > end_line:
            return {"ok": False, "error": "Invalid line range."}

        # Get the block
        block = lines[start_line - 1:end_line]
        base_indent = len(block[0]) - len(block[0].lstrip())

        # Get indentation of the function body
        func_indent = " " * base_indent

        # Create function definition
        func_def = f"{func_indent}def {function_name}({params}):\n"
        func_body = "\n".join(" " * (base_indent + 4) + l.lstrip() for l in block)
        func_def += func_body + "\n"

        # Create call
        call_line = " " * base_indent + f"{function_name}({params})\n"

        # Replace block
        _backup_file(filepath)
        lines[start_line - 1:end_line] = [call_line]
        # Insert function before current block
        insert_pos = max(0, start_line - 2)
        lines.insert(insert_pos, func_def)

        p.write_text("\n".join(lines), encoding="utf-8")

        return {
            "ok": True,
            "function_name": function_name,
            "lines_extracted": end_line - start_line + 1,
            "inserted_at": insert_pos + 1,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


def _find_usages(name: str, path: str = None) -> list:
    """Find all usages of a name across all files."""
    files = _find_python_files(path)
    usages = []
    pattern = re.compile(rf"\b{re.escape(name)}\b")

    for filepath in files:
        try:
            content = Path(filepath).read_text(encoding="utf-8", errors="replace")
            for i, line in enumerate(content.split("\n"), 1):
                if pattern.search(line):
                    usages.append({
                        "file": str(Path(filepath).relative_to(_WORKSPACE)),
                        "line": i,
                        "content": line.rstrip()[:200],
                    })
        except Exception:
            continue
    return usages


def _bulk_rename(renames: list, path: str = None) -> dict:
    """Perform multiple renames at once. renames: [{old, new}]"""
    results = []
    for rename in renames:
        old = rename.get("old", "")
        new = rename.get("new", "")
        if old and new:
            result = _rename_symbol(old, new, path, dry_run=False)
            results.append({"old": old, "new": new, "files_changed": result["files_changed"], "ok": result["ok"]})
    total_changes = sum(r["files_changed"] for r in results)
    return {"ok": total_changes > 0, "renames": results, "total_files_changed": total_changes}


def refactoring_engine(parameters: dict = None, player=None) -> str:
    """Tool entry point."""
    params = parameters or {}
    action = params.get("action", "find_usages").lower()

    if action == "rename":
        old = params.get("old", "")
        new = params.get("new", "")
        if not old or not new:
            return "Necesito 'old' y 'new'."
        dry_run = params.get("dry_run", "false").lower() == "true"
        result = _rename_symbol(old, new, params.get("filter"), dry_run)
        mode = "PREVIEW (dry run)" if dry_run else "APLICADO"
        return f"{mode}: '{old}' → '{new}' en {result['files_changed']} archivos" + (
            "\n" + "\n".join(f"  {c['file']}: {c['replacements']} reemplazos" for c in result["changes"][:20])
            if result["changes"] else ""
        )

    elif action == "bulk_rename":
        renames_raw = params.get("renames", "[]")
        try:
            import json
            renames = json.loads(renames_raw) if isinstance(renames_raw, str) else renames_raw
        except Exception:
            return "Error parseando 'renames'. Debe ser JSON array de {old, new}."
        result = _bulk_rename(renames, params.get("path"))
        return f"Bulk rename: {result['total_files_changed']} archivos cambiados\n" + "\n".join(
            f"  '{r['old']}' → '{r['new']}': {r['files_changed']} archivos" for r in result["renames"]
        )

    elif action == "move":
        src = params.get("source", "")
        dst = params.get("destination", "")
        if not src or not dst:
            return "Necesito 'source' y 'destination'."
        result = _move_file(src, dst)
        if not result["ok"]:
            return result["error"]
        return f"Movido: {src} → {dst}\n  Módulo: {result['old_module']} → {result['new_module']}\n  Imports actualizados: {result['import_updates']}"

    elif action == "extract":
        filepath = params.get("file", "")
        if not filepath:
            return "Necesito 'file'."
        result = _extract_function(
            filepath,
            int(params.get("start_line", 1)),
            int(params.get("end_line", 1)),
            params.get("function_name", "extracted_func"),
            params.get("params", ""),
        )
        if not result["ok"]:
            return result["error"]
        return f"Extraído: {result['function_name']} ({result['lines_extracted']} líneas) en línea {result['inserted_at']}"

    elif action == "find_usages":
        name = params.get("name", "")
        if not name:
            return "Necesito 'name'."
        usages = _find_usages(name, params.get("path"))
        if not usages:
            return f"Sin usos de '{name}'."
        return f"Usos de '{name}' ({len(usages)}):\n" + "\n".join(
            f"  {u['file']}:{u['line']}: {u['content']}" for u in usages[:50]
        )

    return f"Acción '{action}' no reconocida. Usa: rename, bulk_rename, move, extract, find_usages"
