# -*- coding: utf-8 -*-
"""file_controller.py — Full file and directory operations for ERIS."""
import os
import re
import shutil
import glob
import traceback
from pathlib import Path


def resolve_path(p: str) -> str:
    try:
        from actions.path_helper import get_desktop_path, get_documents_path, get_downloads_path
        desktop_dir = str(get_desktop_path())
        documents_dir = str(get_documents_path())
        downloads_dir = str(get_downloads_path())
    except Exception:
        home = os.path.expanduser("~")
        desktop_dir = os.path.join(home, "Desktop")
        documents_dir = os.path.join(home, "Documents")
        downloads_dir = os.path.join(home, "Downloads")

    if not p:
        return desktop_dir

    p_lower = p.lower().strip()
    shortcuts = {
        "desktop": desktop_dir, "escritorio": desktop_dir,
        "downloads": downloads_dir, "descargas": downloads_dir,
        "documents": documents_dir, "documentos": documents_dir,
        "home": os.path.expanduser("~"),
        "pictures": os.path.join(os.path.expanduser("~"), "Pictures"),
        "music": os.path.join(os.path.expanduser("~"), "Music"),
        "videos": os.path.join(os.path.expanduser("~"), "Videos"),
    }

    for key, base in shortcuts.items():
        if p_lower == key or p_lower.startswith(key + "\\") or p_lower.startswith(key + "/"):
            rel = p[len(key):].lstrip("\\/")
            return os.path.join(base, rel) if rel else base

    return os.path.abspath(p)


def file_controller(parameters: dict, player=None) -> str:
    action = parameters.get("action", "").lower().strip()
    path_raw = parameters.get("path", "")
    destination_raw = parameters.get("destination", "")
    new_name = parameters.get("new_name", "")
    content = parameters.get("content", "")
    name = parameters.get("name", "")
    extension = parameters.get("extension", "")
    count = int(parameters.get("count", 10))
    old_text = parameters.get("old_text", "")
    new_text = parameters.get("new_text", "")
    mode = parameters.get("mode", "replace")
    confirm = parameters.get("confirm", False)
    offset = parameters.get("offset", None)
    limit = parameters.get("limit", None)
    pattern = parameters.get("pattern", "")
    glob_pattern = parameters.get("glob_pattern", "")

    if not action:
        return "Error: Se requiere 'action'."

    try:
        resolved_path = resolve_path(path_raw) if path_raw else ""

        if action == "list":
            return _list_dir(resolved_path, count)
        elif action == "create_folder":
            return _log_mut("create_folder", resolved_path, _create_folder(resolved_path))
        elif action == "create_file":
            return _log_mut("create_file", resolved_path, _create_file(resolved_path, content))
        elif action == "delete":
            return _log_mut("delete", resolved_path, _delete(resolved_path, confirm))
        elif action == "move":
            return _log_mut("move", resolved_path, _move(resolved_path, resolve_path(destination_raw)), resolve_path(destination_raw))
        elif action == "copy":
            return _log_mut("copy", resolved_path, _copy(resolved_path, resolve_path(destination_raw)), resolve_path(destination_raw))
        elif action == "rename":
            return _log_mut("rename", resolved_path, _rename(resolved_path, new_name), new_name)
        elif action == "read":
            return _read_file(resolved_path, offset, limit)
        elif action == "grep":
            return _grep(resolved_path, pattern)
        elif action == "write":
            return _log_mut("write", resolved_path, _write_file(resolved_path, content))
        elif action == "edit":
            return _log_mut("edit", resolved_path, _edit_file(resolved_path, old_text, new_text, mode))
        elif action == "journal":
            from core.edit_journal import recent as _jrecent
            return _jrecent(int(count or 20))
        elif action == "find":
            return _find_file(name, extension, resolved_path or os.path.expanduser("~"))
        elif action == "glob":
            return _glob_files(resolved_path or os.path.expanduser("~"), glob_pattern)
        elif action == "largest":
            return _largest_files(resolved_path or "C:\\", count)
        elif action == "disk_usage":
            return _disk_usage(resolved_path or "C:\\")
        elif action == "info":
            return _file_info(resolved_path)
        else:
            return f"Acción '{action}' no soportada."
    except Exception as e:
        traceback.print_exc()
        return f"Error: {e}"


def _list_dir(path: str, count: int = 30) -> str:
    if not path or not os.path.exists(path):
        return f"Error: '{path}' no existe."
    if not os.path.isdir(path):
        return f"Error: '{path}' no es una carpeta."

    items = sorted(os.listdir(path))
    lines = [f"Contenido de '{os.path.basename(path)}' ({len(items)} items):"]
    for item in items[:count]:
        full = os.path.join(path, item)
        suffix = "/" if os.path.isdir(full) else ""
        try:
            size = os.path.getsize(full)
            if size > 1024 * 1024:
                size_str = f" ({size / (1024**2):.1f} MB)"
            elif size > 1024:
                size_str = f" ({size / 1024:.1f} KB)"
            else:
                size_str = ""
        except Exception:
            size_str = ""
        lines.append(f"  {item}{suffix}{size_str}")
    if len(items) > count:
        lines.append(f"  ... y {len(items) - count} más")
    return "\n".join(lines)


def _create_folder(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return f"Carpeta creada: {path}"


def _create_file(path: str, content: str = "") -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content or "")
    return f"Archivo creado: {path}"


def _delete(path: str, confirm: bool = False) -> str:
    if not os.path.exists(path):
        return f"Error: '{path}' no existe."
    if not confirm:
        return f"⚠️ Confirmá con 'confirm=true' para eliminar: {path}"
    try:
        import send2trash
        send2trash.send2trash(path)
    except ImportError:
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
    return f"Eliminado: {path}"


def _move(src: str, dst: str) -> str:
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.move(src, dst)
    return f"Movido: {src} → {dst}"


def _copy(src: str, dst: str) -> str:
    if os.path.isdir(src):
        shutil.copytree(src, dst)
    else:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
    return f"Copiado: {src} → {dst}"


def _rename(path: str, new_name: str) -> str:
    if not os.path.exists(path):
        return f"Error: '{path}' no existe."
    if not new_name:
        return "Error: Se requiere 'new_name'."
    directory = os.path.dirname(path)
    new_path = os.path.join(directory, new_name)
    os.rename(path, new_path)
    return f"Renombrado: {os.path.basename(path)} → {new_name}"


def _read_file(path: str, offset=None, limit=None) -> str:
    if not os.path.exists(path):
        return f"Error: '{path}' no existe."
    size = os.path.getsize(path)
    if size > 5 * 1024 * 1024:
        return f"Error: Archivo muy grande ({size / (1024**2):.1f} MB). Usá offset/limit para leerlo por partes."
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception as e:
        return f"Error leyendo archivo: {e}"

    total = len(lines)

    if offset is not None or limit is not None:
        start = int(offset) if offset is not None else 0
        count = int(limit) if limit is not None else 50
        start = max(0, start - 1)
        chunk = lines[start:start + count]
        out = "".join(
            f"{i + 1}: {ln}" for i, ln in enumerate(chunk, start=start)
        )
        more = " (más líneas disponibles: usá offset=...) " if start + count < total else ""
        return f"Archivo '{path}' ({total} líneas). Líneas {start + 1}-{min(start + count, total)}:{more}\n" + out

    if total > 250:
        head = "".join(f"{i + 1}: {ln}" for i, ln in enumerate(lines[:250], start=1))
        return f"Archivo '{path}' ({total} líneas). Mostrando primeras 250: usá offset/limit para ver más.\n" + head

    return "".join(f"{i + 1}: {ln}" for i, ln in enumerate(lines, start=1))


def _grep(path: str, pattern: str) -> str:
    """Busca un patrón en un archivo o directorio y devuelve SOLO las líneas que coinciden (file:line)."""
    if not pattern:
        return "Error: se requiere 'pattern' para grep."
    try:
        rx = re.compile(pattern, re.IGNORECASE)
    except re.error as e:
        return f"Error en el patrón regex: {e}"

    matches = []
    if os.path.isdir(path):
        targets = [os.path.join(root, f) for root, _, files in os.walk(path)
                   for f in files if not f.startswith(".")]
        targets = [t for t in targets if t.lower().endswith((".py", ".js", ".ts", ".tsx", ".json", ".md", ".txt", ".html", ".css", ".bat", ".ps1", ".sh"))][:2000]
    else:
        targets = [path]

    for target in targets:
        try:
            with open(target, "r", encoding="utf-8", errors="replace") as f:
                for ln_no, line in enumerate(f, start=1):
                    if rx.search(line):
                        matches.append(f"{target}:{ln_no}: {line.rstrip()[:160]}")
                        if len(matches) >= 60:
                            break
        except Exception:
            continue
        if len(matches) >= 60:
            break

    if not matches:
        return f"Sin coincidencias para /{pattern}/ en {path}."
    return f"Coincidencias de /{pattern}/ ({len(matches)}):\n" + "\n".join(matches)


def _write_file(path: str, content: str) -> str:
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content or "")
    result = f"Archivo escrito: {path} ({len(content or '')} caracteres)"
    if path.lower().endswith(".py"):
        result += _pycheck(path)
    return result


def _edit_file(path: str, old_text: str, new_text: str, mode: str = "replace") -> str:
    if not os.path.exists(path):
        return f"Error: '{path}' no existe."
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    if mode == "replace":
        if old_text and old_text in content:
            content = content.replace(old_text, new_text, 1)
        elif old_text:
            return f"Error: Texto no encontrado en el archivo."
    elif mode == "append":
        content += new_text
    elif mode == "prepend":
        content = new_text + content
    elif mode == "overwrite":
        content = new_text
    else:
        return f"Modo '{mode}' no válido."

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    result = f"Archivo editado ({mode}): {path}"
    if path.lower().endswith(".py"):
        result += _pycheck(path)
    return result


def _pycheck(path: str) -> str:
    try:
        import py_compile
        py_compile.compile(path, doraise=True)
        return "\n[PY_COMPILE] ✅ Sintaxis válida."
    except py_compile.PyCompileError as e:
        return f"\n[PY_COMPILE] ⚠️ ERROR DE SINTAXIS: {str(e)[:300]}"


def _log_mut(action: str, path: str, result: str, extra: str = "") -> str:
    try:
        from core.edit_journal import log as _jlog
        detail = extra if extra else str(result).split("\n")[0][:80]
        _jlog(action, path, detail)
    except Exception:
        pass
    return result


def _find_file(name: str, extension: str, search_path: str) -> str:
    if not name and not extension:
        return "Error: Se requiere 'name' o 'extension'."
    pattern = f"*{name}*{extension}" if name else f"*{extension}"
    results = []
    for root, dirs, files in os.walk(search_path):
        for f in files:
            if fnmatch.fnmatch(f.lower(), pattern.lower()):
                results.append(os.path.join(root, f))
                if len(results) >= 20:
                    break
        if len(results) >= 20:
            break

    if not results:
        return f"No se encontraron archivos con '{name or extension}' en {search_path}."

    lines = [f"Encontrados {len(results)} archivos:"]
    for r in results[:15]:
        lines.append(f"  {r}")
    return "\n".join(lines)


def _glob_files(search_path: str, glob_pattern: str) -> str:
    """Búsqueda de archivos por patrón glob recursivo (ej: **/*.py, **/*.log)."""
    if not glob_pattern:
        return "Error: Se requiere 'glob_pattern' (ej: **/*.py)."
    try:
        matches = glob.glob(os.path.join(search_path, glob_pattern), recursive=True)
    except Exception as e:
        return f"Error: patrón inválido: {e}"
    if not matches:
        return f"No se encontraron archivos con '{glob_pattern}' en {search_path}."
    if len(matches) > 60:
        lines = [f"Encontrados {len(matches)} archivos (mostrando 60):"]
        shown = matches[:60]
    else:
        lines = [f"Encontrados {len(matches)} archivos:"]
        shown = matches
    for m in shown:
        try:
            rel = os.path.relpath(m, search_path)
        except Exception:
            rel = m
        lines.append(f"  {rel}")
    return "\n".join(lines)


def _largest_files(path: str, count: int = 10) -> str:
    files = []
    for root, dirs, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(root, f)
            try:
                size = os.path.getsize(fp)
                files.append((fp, size))
            except Exception:
                pass
    files.sort(key=lambda x: x[1], reverse=True)

    lines = [f"Archivos más grandes en {path}:"]
    for fp, size in files[:count]:
        if size > 1024 * 1024 * 1024:
            size_str = f"{size / (1024**3):.2f} GB"
        elif size > 1024 * 1024:
            size_str = f"{size / (1024**2):.1f} MB"
        else:
            size_str = f"{size / 1024:.1f} KB"
        lines.append(f"  {size_str:>10}  {fp}")
    return "\n".join(lines)


def _disk_usage(path: str) -> str:
    try:
        usage = shutil.disk_usage(path)
        return (
            f"Disco {path}: {usage.used / usage.total * 100:.1f}% | "
            f"Usado: {usage.used / (1024**3):.1f}/{usage.total / (1024**3):.1f} GB | "
            f"Libre: {usage.free / (1024**3):.1f} GB"
        )
    except Exception as e:
        return f"Error: {e}"


def _file_info(path: str) -> str:
    if not os.path.exists(path):
        return f"Error: '{path}' no existe."
    stat = os.stat(path)
    is_dir = os.path.isdir(path)
    size = stat.st_size
    modified = os.path.getmtime(path)
    import time
    mod_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(modified))

    if size > 1024 * 1024:
        size_str = f"{size / (1024**2):.1f} MB"
    elif size > 1024:
        size_str = f"{size / 1024:.1f} KB"
    else:
        size_str = f"{size} bytes"

    tipo = "Carpeta" if is_dir else "Archivo"
    ext = os.path.splitext(path)[1] if not is_dir else ""
    return f"{tipo}: {os.path.basename(path)} | Tamaño: {size_str} | Modificado: {mod_str} | Ext: {ext or 'N/A'}"


import fnmatch
