"""
actions/ide_integration.py
──────────────────────────
Integracion de ERIS con IDEs de programacion.

Detecta el IDE activo, lee codigo, lo analiza, y permite ediciones
quirurgicas (cambiar una letra, numero, palabra, o linea especifica)
sin reescribir todo el archivo.

Herramientas:
  ide_detect  — Detecta que IDE/programa esta activo y que archivo tiene abierto
  ide_read    — Lee el codigo completo del editor activo
  ide_explain — Explica una porcion de codigo
  ide_edit    — Edita partes especificas del codigo (find-and-replace, linea, bloque)
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pyperclip

try:
    import pygetwindow as gw
except ImportError:
    gw = None
except Exception:
    # En Linux/Wayland `import pygetwindow` no lanza ImportError sino
    # NotImplementedError (pygetwindow no soporta Linux). Degrada igual que
    # un ImportError para no reventar el import del módulo.
    gw = None

try:
    import pyautogui
    pyautogui.FAILSAFE = False
    pyautogui.PAUSE = 0.02
except Exception:
    pyautogui = None  # type: ignore[assignment]


# ── IDE Detection Patterns ────────────────────────────────────────────────────

_IDE_PATTERNS = {
    "vscode": {
        "title_keywords": ["Visual Studio Code", "VS Code"],
        "file_pattern": True,
        "language_hints": {".py": "python", ".js": "javascript", ".ts": "typescript",
                          ".java": "java", ".cpp": "cpp", ".c": "c", ".h": "c/c++ header",
                          ".cs": "csharp", ".go": "go", ".rs": "rust", ".rb": "ruby",
                          ".php": "php", ".html": "html", ".css": "css", ".json": "json",
                          ".xml": "xml", ".yaml": "yaml", ".yml": "yaml", ".md": "markdown",
                          ".sql": "sql", ".sh": "shell", ".bash": "shell", ".ps1": "powershell",
                          ".vue": "vue", ".jsx": "react", ".tsx": "react/typescript",
                          ".swift": "swift", ".kt": "kotlin", ".dart": "dart"},
    },
    "visual_studio": {
        "title_keywords": ["Visual Studio", "Microsoft Visual Studio"],
        "exclude_keywords": ["Visual Studio Code"],
        "file_pattern": True,
        "language_hints": {".cs": "csharp", ".vb": "vbnet", ".cpp": "cpp", ".c": "c",
                          ".h": "c/c++ header", ".fs": "fsharp", ".razor": "razor",
                          ".aspx": "aspnet", ".xaml": "xaml"},
    },
    "intellij": {
        "title_keywords": ["IntelliJ IDEA"],
        "file_pattern": True,
        "language_hints": {".java": "java", ".kt": "kotlin", ".groovy": "groovy",
                          ".scala": "scala", ".xml": "xml", ".gradle": "gradle"},
    },
    "pycharm": {
        "title_keywords": ["PyCharm"],
        "file_pattern": True,
        "language_hints": {".py": "python", ".pyi": "python stub", ".pyx": "cython"},
    },
    "webstorm": {
        "title_keywords": ["WebStorm"],
        "file_pattern": True,
        "language_hints": {".js": "javascript", ".ts": "typescript", ".jsx": "react",
                          ".tsx": "react/typescript", ".vue": "vue", ".html": "html"},
    },
    "netbeans": {
        "title_keywords": ["NetBeans", "Apache NetBeans"],
        "file_pattern": True,
        "language_hints": {".java": "java", ".php": "php", ".html": "html",
                          ".css": "css", ".js": "javascript", ".xml": "xml"},
    },
    "eclipse": {
        "title_keywords": ["Eclipse"],
        "file_pattern": True,
        "language_hints": {".java": "java", ".py": "python", ".c": "c",
                          ".cpp": "cpp", ".xml": "xml"},
    },
    "android_studio": {
        "title_keywords": ["Android Studio"],
        "file_pattern": True,
        "language_hints": {".java": "java", ".kt": "kotlin", ".xml": "xml",
                          ".gradle": "gradle", ".dart": "dart"},
    },
    "sublime": {
        "title_keywords": ["Sublime Text"],
        "file_pattern": True,
        "language_hints": {},
    },
    "notepadpp": {
        "title_keywords": ["Notepad++"],
        "file_pattern": True,
        "language_hints": {},
    },
    "phpstorm": {
        "title_keywords": ["PhpStorm"],
        "file_pattern": True,
        "language_hints": {".php": "php", ".js": "javascript", ".html": "html",
                          ".css": "css", ".twig": "twig"},
    },
    "rider": {
        "title_keywords": ["Rider"],
        "file_pattern": True,
        "language_hints": {".cs": "csharp", ".fs": "fsharp"},
    },
    "datagrip": {
        "title_keywords": ["DataGrip"],
        "file_pattern": False,
        "language_hints": {".sql": "sql"},
    },
    "mysql_workbench": {
        "title_keywords": ["MySQL Workbench"],
        "file_pattern": False,
        "language_hints": {".sql": "sql"},
    },
    "dbeaver": {
        "title_keywords": ["DBeaver"],
        "file_pattern": False,
        "language_hints": {".sql": "sql"},
    },
    "arduino": {
        "title_keywords": ["Arduino"],
        "file_pattern": True,
        "language_hints": {".ino": "arduino/c++", ".cpp": "cpp", ".h": "c/c++ header"},
    },
    "cursor": {
        "title_keywords": ["Cursor"],
        "file_pattern": True,
        "language_hints": {},
    },
    "zed": {
        "title_keywords": ["Zed"],
        "file_pattern": True,
        "language_hints": {},
    },
}


# ── Clipboard Helpers ──────────────────────────────────────────────────────────

def _save_clipboard():
    """Save current clipboard content."""
    try:
        return pyperclip.paste()
    except Exception:
        return ""


def _restore_clipboard(text):
    """Restore clipboard content."""
    try:
        if text:
            pyperclip.copy(text)
        else:
            pyperclip.copy("")
    except Exception:
        pass


def _copy_all():
    """Select all + copy in the active window. Returns copied text."""
    old_clip = _save_clipboard()
    try:
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.08)
        pyautogui.hotkey("ctrl", "c")
        time.sleep(0.12)
        text = pyperclip.paste()
        return text, old_clip
    except Exception as e:
        return "", old_clip


# ── IDE Detection ──────────────────────────────────────────────────────────────

def _hyprctl_windows() -> list[str]:
    """Titulos de ventanas vía hyprctl (Wayland/Hyprland). Devuelve lista vacía si no aplica."""
    try:
        out = subprocess.run(
            ["hyprctl", "clients", "-j"],
            capture_output=True, text=True, timeout=4,
        ).stdout
        import json as _j
        data = _j.loads(out)
        return [w.get("title", "") or "" for w in data if isinstance(w, dict)]
    except Exception:
        return []


def detect_active_ide_wayland():
    """Detecta el IDE activo en Linux/Wayland usando hyprctl (sin pygetwindow)."""
    titles = _hyprctl_windows()
    if not titles:
        return {"error": "No se pudo listar ventanas (sin hyprctl o sin ventanas)"}

    active_title = titles[0] if titles else ""
    ide_matches = []
    for title in titles:
        if not title or len(title) < 3:
            continue
        for ide_key, ide_info in _IDE_PATTERNS.items():
            if any(kw.lower() in title.lower() for kw in ide_info["title_keywords"]):
                if not any(ek.lower() in title.lower() for ek in ide_info.get("exclude_keywords", [])):
                    ide_matches.append((ide_key, ide_info, title))
                    break

    if not ide_matches:
        return {
            "detected": False,
            "title": active_title,
            "message": f"No se reconoce el programa activo. Titulo: {active_title}",
        }

    # Preferir la ventana que trae archivo abierto (con extensión)
    best = None
    for ide_key, ide_info, title in ide_matches:
        for sep in [" — ", " - ", " ─ ", " | ", " ● "]:
            if sep in title and any("." in p and len(p) < 200 for p in title.split(sep)):
                best = (ide_key, ide_info, title)
                break
        if best:
            break
    if not best:
        best = ide_matches[0]

    ide_key, ide_info, title = best
    detected_ide = None
    for k, info in _IDE_PATTERNS.items():
        if any(kw.lower() in title.lower() for kw in info["title_keywords"]):
            detected_ide = k
            break

    file_path = ""
    file_name = ""
    language = "text"
    for sep in [" — ", " - ", " ─ ", " | ", " ● "]:
        for part in title.split(sep):
            part = part.strip()
            for lane, hints in ide_info.get("file_pattern_paths", {}).items():
                if hints and any(h in part for h in hints):
                    file_path = part
                    break
            for ext, lang in ide_info.get("language_hints", {}).items():
                if part.endswith(ext):
                    file_name = part
                    language = lang
                    break
    if file_name and "/" in file_name:
        file_name = file_name.rsplit("/", 1)[-1]

    return {
        "detected": bool(detected_ide),
        "ide_friendly": detected_ide or "unknown",
        "ide": ide_key,
        "title": title,
        "file_path": file_path,
        "file_name": file_name,
        "language": language,
        "directory": "",
        "source": "hyprctl",
    }


def detect_active_ide():
    """
    Detect which IDE is currently open (not necessarily active/focused).
    Scans ALL windows to find IDEs, not just the active one.
    Returns dict with: ide, title, file_path, file_name, language, directory
    """
    if not gw:
        # Linux/Wayland: sin pygetwindow, usar hyprctl para listar ventanas.
        return detect_active_ide_wayland()

    try:
        # First try active window
        active = gw.getActiveWindow()
        active_title = active.title if active else ""

        # Also scan ALL windows for IDEs
        all_windows = gw.getAllWindows()
    except Exception as e:
        return {"error": f"No pudo detectar ventanas: {e}"}

    # Build list of all IDE windows found
    ide_matches = []

    for w in all_windows:
        title = w.title or ""
        if not title or len(title) < 3:
            continue

        for ide_key, ide_info in _IDE_PATTERNS.items():
            match = False
            for kw in ide_info["title_keywords"]:
                if kw.lower() in title.lower():
                    match = True
                    break
            if match:
                exclude = ide_info.get("exclude_keywords", [])
                excluded = any(ek.lower() in title.lower() for ek in exclude)
                if not excluded:
                    ide_matches.append((ide_key, ide_info, title, w))
                    break

    if not ide_matches:
        # Check active window anyway
        if active_title:
            return {
                "detected": False,
                "title": active_title,
                "message": f"No se reconoce el programa activo. Titulo: {active_title}",
            }
        return {"error": "No se encontro ningun IDE abierto"}

    # Prefer the window with an open file (has * in title = unsaved, or has file extension)
    best = None
    for ide_key, ide_info, title, window in ide_matches:
        # Check if title has a file name (pattern: "something - file.ext - IDE")
        has_file = False
        for sep in [" — ", " - ", " ─ ", " | ", " ● "]:
            if sep in title:
                parts = [p.strip() for p in title.split(sep)]
                for part in parts:
                    if "." in part and len(part) < 200:
                        has_file = True
                        break
            if has_file:
                break
        if has_file:
            best = (ide_key, ide_info, title, window)
            break

    if not best:
        best = ide_matches[0]

    ide_key, ide_info, title, window = best

    # Match IDE
    detected_ide = None
    for ide_key, ide_info in _IDE_PATTERNS.items():
        match = False
        for kw in ide_info["title_keywords"]:
            if kw.lower() in title.lower():
                match = True
                break
        if match:
            exclude = ide_info.get("exclude_keywords", [])
            excluded = any(ek.lower() in title.lower() for ek in exclude)
            if not excluded:
                detected_ide = ide_key
                break

    if not detected_ide:
        return {
            "detected": False,
            "title": title,
            "message": f"No se reconoce el programa activo. Titulo: {title}",
        }

    # Extract file path from title
    file_path = ""
    file_name = ""
    language = ""
    directory = ""

    ide_info = _IDE_PATTERNS[detected_ide]

    # Common patterns: "Project - filename.ext* - IDE" or "filename — folder" or "filename - folder - IDE"
    # Split by common separators
    for sep in [" — ", " - ", " ─ ", " | ", " ● "]:
        if sep in title:
            parts = [p.strip() for p in title.split(sep)]

            # Strategy: find the part that looks like a filename (has an extension)
            # and is NOT the IDE name
            ide_keywords = ["microsoft visual studio", "intellij", "pycharm", "webstorm",
                           "netbeans", "eclipse", "android studio", "sublime", "notepad++",
                           "phpstorm", "rider", "datagrip", "visual studio code", "vs code",
                           "cursor", "zed"]

            for i, part in enumerate(parts):
                part_lower = part.lower().strip()
                # Skip if it's the IDE name
                if any(ik in part_lower for ik in ide_keywords):
                    continue
                # Check if it looks like a filename (has extension, reasonable length)
                if "." in part and len(part) < 200 and len(part) > 1:
                    # Remove trailing * (unsaved indicator)
                    candidate = part.rstrip("*").strip()
                    if candidate:
                        file_name = candidate
                        # Look for directory in remaining parts
                        for other_part in parts:
                            other_clean = other_part.rstrip("*").strip()
                            if other_clean == candidate:
                                continue
                            if os.path.isdir(other_clean):
                                directory = other_clean
                                file_path = os.path.join(directory, file_name)
                                break
                            elif ":" in other_clean and ("\\" in other_clean or "/" in other_clean):
                                for p_candidate in [os.path.join(other_clean, file_name), other_clean + "\\" + file_name]:
                                    if os.path.exists(p_candidate):
                                        file_path = p_candidate
                                        directory = other_clean
                                        break
                        break
            break

    # Determine language from extension
    if file_name:
        ext = Path(file_name).suffix.lower()
        hints = ide_info.get("language_hints", {})
        language = hints.get(ext, ext.lstrip("."))

    # If we have a file_name but no file_path, try to find it on disk
    if file_name and not file_path:
        # Extract project name from title (first part before first separator)
        project_name = ""
        for sep in [" — ", " - ", " ─ ", " | ", " ● "]:
            if sep in title:
                project_name = title.split(sep)[0].strip()
                break

        search_dirs = [
            Path(os.environ.get("USERPROFILE", "")) / "source" / "repos",
            Path(os.environ.get("USERPROFILE", "")) / "Documents",
            Path(os.environ.get("USERPROFILE", "")) / "Desktop",
            Path("C:/Users") / os.environ.get("USERNAME", "") / "source" / "repos",
        ]
        for search_dir in search_dirs:
            if search_dir.exists():
                try:
                    # First try: find file inside a directory matching the project name
                    if project_name:
                        for match in search_dir.rglob(file_name):
                            if project_name.lower() in str(match.parent).lower():
                                file_path = str(match)
                                directory = str(match.parent)
                                break
                    # Fallback: just find any match
                    if not file_path:
                        found = list(search_dir.rglob(file_name))
                        if found:
                            file_path = str(found[0])
                            directory = str(found[0].parent)
                    if file_path:
                        break
                except Exception:
                    continue

    return {
        "detected": True,
        "ide": detected_ide,
        "ide_friendly": detected_ide.replace("_", " ").title(),
        "title": title,
        "file_name": file_name,
        "file_path": file_path,
        "directory": directory,
        "language": language,
    }


# ── Code Reading ───────────────────────────────────────────────────────────────

def read_code_from_editor():
    """
    Read the code from the currently open IDE.
    Scans all windows (not just active), finds the file on disk, reads it.
    Falls back to clipboard if disk read fails.
    """
    ide_info = detect_active_ide()

    if not ide_info.get("detected") and not ide_info.get("file_name"):
        return {
            "error": "No se encontro ningun IDE con un archivo abierto.",
            "hint": "Abri un archivo en tu IDE (VS Code, Visual Studio, etc) e intentalo de nuevo.",
        }

    file_path = ide_info.get("file_path", "")
    file_name = ide_info.get("file_name", "")
    language = ide_info.get("language", "")
    directory = ide_info.get("directory", "")
    ide_name = ide_info.get("ide", "unknown")

    # If we have a file path, try reading from disk first (more reliable)
    if file_path and os.path.isfile(file_path):
        try:
            content = Path(file_path).read_text(encoding="utf-8-sig", errors="replace")
            lines = content.split("\n")
            return {
                "source": "disk",
                "code": content,
                "lines": lines,
                "line_count": len(lines),
                "language": language,
                "file_name": file_name,
                "file_path": file_path,
                "directory": directory,
                "ide": ide_info.get("ide", "unknown"),
                "message": f"Codigo leido desde disco: {file_path}",
            }
        except Exception as e:
            pass  # Fall through to clipboard reading

    # Read from editor via clipboard
    code, old_clip = _copy_all()
    _restore_clipboard(old_clip)

    if not code or len(code.strip()) < 2:
        return {
            "error": "No se pudo leer codigo del editor. Asegurate de que hay un archivo abierto.",
            "ide": ide_info,
        }

    lines = code.split("\n")

    # If no language detected, try from file extension in title
    if not language and file_name:
        ext = Path(file_name).suffix.lower()
        language = ext.lstrip(".")

    return {
        "source": "clipboard",
        "code": code,
        "lines": lines,
        "line_count": len(lines),
        "language": language,
        "file_name": file_name,
        "file_path": file_path,
        "directory": directory,
        "ide": ide_info.get("ide", "unknown"),
        "char_count": len(code),
        "message": f"Codigo leido del editor ({len(lines)} lineas, {len(code)} caracteres)",
    }


# ── Code Editing ───────────────────────────────────────────────────────────────

def edit_find_replace(old_text, new_text, file_path=None):
    """
    Replace specific text in the code (find and replace).
    This is the safest editing method — changes only the exact text specified.
    """
    if not file_path or not os.path.isfile(file_path):
        return {"error": "No se encontro el archivo para editar. Necesito la ruta del archivo."}

    try:
        content = Path(file_path).read_text(encoding="utf-8-sig", errors="replace")
    except Exception as e:
        return {"error": f"No se pudo leer el archivo: {e}"}

    if old_text not in content:
        return {
            "error": f"El texto '{old_text[:80]}' no se encontro en el archivo.",
            "suggestion": "Verifica el texto exacto incluyendo espacios y sangria.",
        }

    count = content.count(old_text)
    new_content = content.replace(old_text, new_text, 1)

    # Create backup
    backup_path = file_path + ".eris_backup"
    try:
        Path(backup_path).write_text(content, encoding="utf-8")
    except Exception:
        pass

    try:
        Path(file_path).write_text(new_content, encoding="utf-8")
    except Exception as e:
        return {"error": f"No se pudo escribir el archivo: {e}"}

    return {
        "success": True,
        "changes": 1,
        "remaining_occurrences": count - 1,
        "backup": backup_path,
        "message": f"Texto reemplazado correctamente. {'Quedan ' + str(count-1) + ' ocurrencias mas.' if count > 1 else ''}",
    }


def edit_line(file_path, line_number, new_line_content):
    """
    Replace a specific line in the file.
    line_number is 1-indexed (line 1 = first line).
    """
    if not file_path or not os.path.isfile(file_path):
        return {"error": "No se encontro el archivo."}

    try:
        content = Path(file_path).read_text(encoding="utf-8-sig", errors="replace")
    except Exception as e:
        return {"error": f"No se pudo leer el archivo: {e}"}

    lines = content.split("\n")

    if line_number < 1 or line_number > len(lines):
        return {"error": f"Linea {line_number} fuera de rango. El archivo tiene {len(lines)} lineas."}

    old_line = lines[line_number - 1]
    lines[line_number - 1] = new_line_content
    new_content = "\n".join(lines)

    # Backup
    backup_path = file_path + ".eris_backup"
    try:
        Path(backup_path).write_text(content, encoding="utf-8")
    except Exception:
        pass

    try:
        Path(file_path).write_text(new_content, encoding="utf-8")
    except Exception as e:
        return {"error": f"No se pudo escribir: {e}"}

    return {
        "success": True,
        "line_changed": line_number,
        "old_line": old_line,
        "new_line": new_line_content,
        "backup": backup_path,
        "message": f"Linea {line_number} reemplazada.",
    }


def edit_lines(file_path, start_line, end_line, new_lines_text):
    """
    Replace a range of lines (start_line to end_line, inclusive).
    new_lines_text is a string that replaces the entire block.
    """
    if not file_path or not os.path.isfile(file_path):
        return {"error": "No se encontro el archivo."}

    try:
        content = Path(file_path).read_text(encoding="utf-8-sig", errors="replace")
    except Exception as e:
        return {"error": f"No se pudo leer: {e}"}

    lines = content.split("\n")

    if start_line < 1 or end_line > len(lines) or start_line > end_line:
        return {"error": f"Rango invalido: lineas {start_line}-{end_line} (archivo: {len(lines)} lineas)"}

    old_block = "\n".join(lines[start_line - 1:end_line])
    new_lines = new_lines_text.split("\n")
    lines[start_line - 1:end_line] = new_lines
    new_content = "\n".join(lines)

    backup_path = file_path + ".eris_backup"
    try:
        Path(backup_path).write_text(content, encoding="utf-8")
    except Exception:
        pass

    try:
        Path(file_path).write_text(new_content, encoding="utf-8")
    except Exception as e:
        return {"error": f"No se pudo escribir: {e}"}

    return {
        "success": True,
        "start_line": start_line,
        "end_line": end_line,
        "old_lines": end_line - start_line + 1,
        "new_lines": len(new_lines),
        "backup": backup_path,
        "message": f"Lineas {start_line}-{end_line} reemplazadas ({end_line - start_line + 1} → {len(new_lines)} lineas).",
    }


def delete_lines(file_path, start_line, end_line):
    """
    Delete a range of lines (start_line to end_line, inclusive).
    """
    if not file_path or not os.path.isfile(file_path):
        return {"error": "No se encontro el archivo."}

    try:
        content = Path(file_path).read_text(encoding="utf-8-sig", errors="replace")
    except Exception as e:
        return {"error": f"No se pudo leer: {e}"}

    lines = content.split("\n")

    if start_line < 1 or end_line > len(lines) or start_line > end_line:
        return {"error": f"Rango invalido: lineas {start_line}-{end_line} (archivo: {len(lines)} lineas)"}

    deleted_block = "\n".join(lines[start_line - 1:end_line])
    del lines[start_line - 1:end_line]
    new_content = "\n".join(lines)

    backup_path = file_path + ".eris_backup"
    try:
        Path(backup_path).write_text(content, encoding="utf-8")
    except Exception:
        pass

    try:
        Path(file_path).write_text(new_content, encoding="utf-8")
    except Exception as e:
        return {"error": f"No se pudo escribir: {e}"}

    return {
        "success": True,
        "deleted_lines": end_line - start_line + 1,
        "start_line": start_line,
        "end_line": end_line,
        "backup": backup_path,
        "message": f"Lineas {start_line}-{end_line} eliminadas ({end_line - start_line + 1} lineas).",
    }


def delete_text(file_path, old_text):
    """
    Delete a specific text from the file (find and remove).
    """
    if not file_path or not os.path.isfile(file_path):
        return {"error": "No se encontro el archivo."}

    try:
        content = Path(file_path).read_text(encoding="utf-8-sig", errors="replace")
    except Exception as e:
        return {"error": f"No se pudo leer: {e}"}

    if old_text not in content:
        return {"error": f"Texto no encontrado: '{old_text[:80]}'"}

    new_content = content.replace(old_text, "", 1)

    backup_path = file_path + ".eris_backup"
    try:
        Path(backup_path).write_text(content, encoding="utf-8")
    except Exception:
        pass

    try:
        Path(file_path).write_text(new_content, encoding="utf-8")
    except Exception as e:
        return {"error": f"No se pudo escribir: {e}"}

    return {
        "success": True,
        "message": f"Texto eliminado correctamente.",
    }


def create_file(file_path, content):
    """
    Create a new file with the given content.
    Creates parent directories if needed.
    """
    if not file_path:
        return {"error": "Necesito una ruta para el archivo."}

    try:
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        Path(file_path).write_text(content, encoding="utf-8")
    except Exception as e:
        return {"error": f"No se pudo crear el archivo: {e}"}

    return {
        "success": True,
        "file_path": file_path,
        "lines": len(content.split("\n")),
        "chars": len(content),
        "message": f"Archivo creado: {file_path} ({len(content.split(chr(10)))} lineas)",
    }


def insert_at_line(file_path, line_number, new_lines_text):
    """
    Insert new lines at a specific position (without replacing existing lines).
    """
    if not file_path or not os.path.isfile(file_path):
        return {"error": "No se encontro el archivo."}

    try:
        content = Path(file_path).read_text(encoding="utf-8-sig", errors="replace")
    except Exception as e:
        return {"error": f"No se pudo leer: {e}"}

    lines = content.split("\n")

    if line_number < 1 or line_number > len(lines) + 1:
        return {"error": f"Posicion invalida: linea {line_number} (archivo: {len(lines)} lineas)"}

    new_lines = new_lines_text.split("\n")
    lines[line_number - 1:line_number - 1] = new_lines
    new_content = "\n".join(lines)

    backup_path = file_path + ".eris_backup"
    try:
        Path(backup_path).write_text(content, encoding="utf-8")
    except Exception:
        pass

    try:
        Path(file_path).write_text(new_content, encoding="utf-8")
    except Exception as e:
        return {"error": f"No se pudo escribir: {e}"}

    return {
        "success": True,
        "inserted_at": line_number,
        "lines_inserted": len(new_lines),
        "backup": backup_path,
        "message": f"{len(new_lines)} lineas insertadas en la linea {line_number}.",
    }


def edit_in_editor(old_text, new_text):
    """
    Edit text directly in the IDE using keyboard simulation.
    Uses Find & Replace dialog (Ctrl+H).
    This works when we can't write to disk (e.g., unsaved buffer).
    """
    if not pyautogui:
        return {"error": "pyautogui no disponible para edicion en editor."}

    try:
        # Open Find & Replace (Ctrl+H in most IDEs)
        pyautogui.hotkey("ctrl", "h")
        time.sleep(0.3)

        # Type the search text
        pyautogui.hotkey("ctrl", "a")
        pyautogui.typewrite(old_text, interval=0.01) if old_text.isascii() else None
        if not old_text.isascii():
            # For non-ASCII, use clipboard
            old_clip = _save_clipboard()
            pyperclip.copy(old_text)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.05)
            _restore_clipboard(old_clip)

        time.sleep(0.1)

        # Tab to replace field
        pyautogui.press("tab")
        time.sleep(0.1)

        # Type replacement
        pyautogui.hotkey("ctrl", "a")
        if new_text.isascii():
            pyautogui.typewrite(new_text, interval=0.01)
        else:
            old_clip = _save_clipboard()
            pyperclip.copy(new_text)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.05)
            _restore_clipboard(old_clip)

        time.sleep(0.1)

        # Replace All (Alt+A) or Replace (Alt+R)
        pyautogui.hotkey("alt", "a")
        time.sleep(0.2)

        # Close dialog
        pyautogui.press("escape")
        time.sleep(0.1)

        return {
            "success": True,
            "method": "keyboard_simulation",
            "message": f"Reemplazo ejecutado en el editor: '{old_text[:50]}' → '{new_text[:50]}'",
        }
    except Exception as e:
        return {"error": f"Error en edicion por teclado: {e}"}


# ── Tool Entry Points ──────────────────────────────────────────────────────────

def ide_integration(parameters: dict, **kwargs) -> str:
    """
    Tool: Integracion con IDEs de programacion.
    Acciones: detect, read, explain, edit, edit_line, edit_lines, edit_in_editor
    """
    action = (parameters.get("action") or "detect").lower().strip()

    if action == "detect":
        result = detect_active_ide()
        return json.dumps(result, ensure_ascii=False, indent=2)

    elif action == "read":
        result = read_code_from_editor()
        if "error" in result:
            return json.dumps(result, ensure_ascii=False)
        # Truncate if too large
        code = result.get("code", "")
        max_chars = int(parameters.get("max_chars", 8000))
        if len(code) > max_chars:
            result["code"] = code[:max_chars] + f"\n\n... [troncado: {len(code)} chars totales, mostrando primeros {max_chars}]"
            result["truncated"] = True
        return json.dumps(result, ensure_ascii=False, indent=2)

    elif action == "edit":
        old_text = parameters.get("old_text", "")
        new_text = parameters.get("new_text", "")
        file_path = parameters.get("file_path", "") or parameters.get("path", "")
        if not old_text or not new_text:
            return "Necesito 'old_text' y 'new_text' para reemplazar."
        result = edit_find_replace(old_text, new_text, file_path)
        return json.dumps(result, ensure_ascii=False, indent=2)

    elif action == "edit_line":
        file_path = parameters.get("file_path", "") or parameters.get("path", "")
        line_number = parameters.get("line_number") or parameters.get("line", 0)
        new_content = parameters.get("new_content", "") or parameters.get("code", "")
        if not file_path or not line_number or not new_content:
            return "Necesito 'file_path', 'line_number' y 'new_content'."
        result = edit_line(file_path, int(line_number), new_content)
        return json.dumps(result, ensure_ascii=False, indent=2)

    elif action == "edit_lines":
        file_path = parameters.get("file_path", "") or parameters.get("path", "")
        start = parameters.get("start_line") or parameters.get("start", 0)
        end = parameters.get("end_line") or parameters.get("end", 0)
        new_text = parameters.get("new_code", "") or parameters.get("code", "")
        if not file_path or not start or not end or not new_text:
            return "Necesito 'file_path', 'start_line', 'end_line' y 'new_code'."
        result = edit_lines(file_path, int(start), int(end), new_text)
        return json.dumps(result, ensure_ascii=False, indent=2)

    elif action == "edit_in_editor":
        old_text = parameters.get("old_text", "")
        new_text = parameters.get("new_text", "")
        if not old_text or not new_text:
            return "Necesito 'old_text' y 'new_text'."
        result = edit_in_editor(old_text, new_text)
        return json.dumps(result, ensure_ascii=False, indent=2)

    elif action == "explain":
        # Read code and return it for the AI to explain
        result = read_code_from_editor()
        if "error" in result:
            return json.dumps(result, ensure_ascii=False)
        # Add context for explanation
        focus = parameters.get("focus", "general")
        result["explanation_request"] = f"Explica este codigo ({focus}). Enfocate en lo que el usuario necesita entender."
        return json.dumps(result, ensure_ascii=False, indent=2)

    elif action == "delete_lines":
        file_path = parameters.get("file_path", "") or parameters.get("path", "")
        start = parameters.get("start_line") or parameters.get("start", 0)
        end = parameters.get("end_line") or parameters.get("end", 0)
        if not file_path or not start or not end:
            return "Necesito 'file_path', 'start_line' y 'end_line'."
        result = delete_lines(file_path, int(start), int(end))
        return json.dumps(result, ensure_ascii=False, indent=2)

    elif action == "delete_text":
        file_path = parameters.get("file_path", "") or parameters.get("path", "")
        old_text = parameters.get("old_text", "")
        if not file_path or not old_text:
            return "Necesito 'file_path' y 'old_text'."
        result = delete_text(file_path, old_text)
        return json.dumps(result, ensure_ascii=False, indent=2)

    elif action == "create_file":
        file_path = parameters.get("file_path", "") or parameters.get("path", "")
        content = parameters.get("content", "") or parameters.get("code", "")
        if not file_path or not content:
            return "Necesito 'file_path' y 'content'."
        result = create_file(file_path, content)
        return json.dumps(result, ensure_ascii=False, indent=2)

    elif action == "insert_at_line":
        file_path = parameters.get("file_path", "") or parameters.get("path", "")
        line_number = parameters.get("line_number") or parameters.get("line", 0)
        new_text = parameters.get("code", "") or parameters.get("new_code", "")
        if not file_path or not line_number or not new_text:
            return "Necesito 'file_path', 'line_number' y 'code'."
        result = insert_at_line(file_path, int(line_number), new_text)
        return json.dumps(result, ensure_ascii=False, indent=2)

    else:
        return f"Accion desconocida: {action}. Acciones: detect, read, explain, edit, edit_line, edit_lines, delete_lines, delete_text, create_file, insert_at_line, edit_in_editor"
