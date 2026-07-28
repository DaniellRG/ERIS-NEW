"""
file_organizer.py — Organización automática de archivos: downloads, escritorio, etc.
Clasifica y organiza archivos por tipo, fecha, tamaño, o contenido.
"""
import json
import shutil
from pathlib import Path
from datetime import datetime

_BASE = Path(__file__).resolve().parent.parent
_ORGANIZER_LOG = _BASE / "data" / "file_organizer_log.json"

FILE_CATEGORIES = {
    "images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".ico", ".tiff"],
    "documents": [".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".pages", ".epub"],
    "spreadsheets": [".xls", ".xlsx", ".csv", ".ods", ".numbers"],
    "presentations": [".ppt", ".pptx", ".key", ".odp"],
    "videos": [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v"],
    "audio": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a"],
    "archives": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz"],
    "code": [".py", ".js", ".ts", ".html", ".css", ".java", ".c", ".cpp", ".go", ".rs", ".rb", ".php"],
    "executables": [".exe", ".msi", ".dmg", ".app", ".deb", ".rpm"],
    "fonts": [".ttf", ".otf", ".woff", ".woff2", ".eot"],
    "design": [".psd", ".ai", ".sketch", ".fig", ".xd", ".indd"],
    "data": [".json", ".xml", ".yaml", ".yml", ".toml", ".ini", ".cfg"],
}


def file_organizer(parameters: dict = None, player=None) -> str:
    """
    Organizador automático de archivos.
    Acciones: organize, scan, preview, rules, add_rule, undo, stats, categorize, find_duplicates, clean
    """
    params = parameters or {}
    action = params.get("action", "scan").lower()

    if action == "organize":
        return _organize_files(params)
    elif action == "scan":
        return _scan_directory(params)
    elif action == "preview":
        return _preview_organize(params)
    elif action == "rules":
        return _list_rules()
    elif action == "add_rule":
        return _add_rule(params)
    elif action == "remove_rule":
        return _remove_rule(params)
    elif action == "undo":
        return _undo_last()
    elif action == "stats":
        return _get_stats(params)
    elif action == "categorize":
        return _categorize_file(params)
    elif action == "find_duplicates":
        return _find_duplicates(params)
    elif action == "clean":
        return _clean_directory(params)
    elif action == "recent":
        return _recent_files(params)
    elif action == "big_files":
        return _big_files(params)
    return "Acciones: organize, scan, preview, rules, add_rule, remove_rule, undo, stats, categorize, find_duplicates, clean, recent, big_files"


def _organize_files(params: dict) -> str:
    source = params.get("source", str(Path.home() / "Downloads"))
    dest = params.get("dest", str(Path.home() / "Organized"))
    dry_run = params.get("dry_run", False)
    custom_rules = params.get("rules", {})

    source_path = Path(source)
    if not source_path.exists():
        return "Directorio no existe: {}".format(source)

    files = [f for f in source_path.iterdir() if f.is_file()]
    if not files:
        return "No hay archivos en: {}".format(source)

    moved = 0
    errors = 0
    actions = []

    for f in files:
        category = _categorize_by_extension(f, custom_rules)
        target_dir = Path(dest) / category
        target_file = target_dir / f.name

        if target_file.exists():
            stem = f.stem
            suffix = f.suffix
            counter = 1
            while target_file.exists():
                target_file = target_dir / "{}_{}{}".format(stem, counter, suffix)
                counter += 1

        actions.append({"source": str(f), "dest": str(target_file), "category": category})

        if not dry_run:
            try:
                target_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(f), str(target_file))
                moved += 1
            except Exception:
                errors += 1

    if not dry_run:
        _log_organize(actions)

    mode = "PREVIEW" if dry_run else "EJECUTADO"
    return "{}: {} archivos | {} movidos | {} errores | {}".format(
        mode, len(files), moved, errors, source)


def _scan_directory(params: dict) -> str:
    directory = params.get("directory", str(Path.home() / "Downloads"))
    dir_path = Path(directory)

    if not dir_path.exists():
        return "Directorio no existe: {}".format(directory)

    files = list(dir_path.iterdir())
    file_list = [f for f in files if f.is_file()]

    categories = {}
    total_size = 0
    for f in file_list:
        cat = _categorize_by_extension(f)
        categories.setdefault(cat, {"count": 0, "size": 0})
        categories[cat]["count"] += 1
        categories[cat]["size"] += f.stat().st_size
        total_size += f.stat().st_size

    lines = ["Escaneo de {} ({} archivos, {:.1f} MB):".format(directory, len(file_list), total_size / (1024*1024))]
    for cat, data in sorted(categories.items(), key=lambda x: -x[1]["count"]):
        lines.append("  {}: {} archivos ({:.1f} MB)".format(
            cat, data["count"], data["size"] / (1024*1024)))
    return "\n".join(lines)


def _preview_organize(params: dict) -> str:
    params["dry_run"] = True
    return _organize_files(params)


def _list_rules() -> str:
    rules = _load_rules()
    if not rules:
        return "Solo hay reglas por defecto (por extensión). Agrega reglas con add_rule"

    lines = ["Reglas personalizadas:"]
    for rule in rules:
        lines.append("  {} → {}".format(rule.get("pattern", ""), rule.get("category", "")))
    return "\n".join(lines)


def _add_rule(params: dict) -> str:
    pattern = params.get("pattern", "")
    category = params.get("category", "")
    if not pattern or not category:
        return "Error: se requiere 'pattern' y 'category'"

    rules = _load_rules()
    rules.append({
        "pattern": pattern,
        "category": category,
        "type": params.get("type", "extension"),
        "created": datetime.now().isoformat(),
    })
    _save_rules(rules)
    return "Regla agregada: {} → {}".format(pattern, category)


def _remove_rule(params: dict) -> str:
    pattern = params.get("pattern", "")
    if not pattern:
        return "Error: se requiere 'pattern'"

    rules = _load_rules()
    rules = [r for r in rules if r.get("pattern") != pattern]
    _save_rules(rules)
    return "Regla eliminada: {}".format(pattern)


def _undo_last() -> str:
    log = _load_log()
    actions = log.get("last_actions", [])
    if not actions:
        return "No hay acciones para deshacer"

    undone = 0
    for action in actions:
        try:
            dest = Path(action.get("dest", ""))
            source = Path(action.get("source", ""))
            if dest.exists():
                source.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(dest), str(source))
                undone += 1
        except Exception:
            pass

    log["last_actions"] = []
    _save_log(log)
    return "Deshecho: {} archivos movidos de vuelta".format(undone)


def _get_stats(params: dict) -> str:
    directory = params.get("directory", str(Path.home() / "Downloads"))
    dir_path = Path(directory)

    if not dir_path.exists():
        return "Directorio no existe: {}".format(directory)

    files = [f for f in dir_path.rglob("*") if f.is_file()]
    total_size = sum(f.stat().st_size for f in files)
    oldest = min((f.stat().st_mtime for f in files), default=0)
    newest = max((f.stat().st_mtime for f in files), default=0)

    return "Stats de {}: {} archivos | {:.1f} MB | Más antiguo: {} | Más reciente: {}".format(
        directory, len(files), total_size / (1024*1024),
        datetime.fromtimestamp(oldest).strftime("%Y-%m-%d") if oldest else "?",
        datetime.fromtimestamp(newest).strftime("%Y-%m-%d") if newest else "?")


def _categorize_file(params: dict) -> str:
    filename = params.get("filename", "")
    if not filename:
        return "Error: se requiere 'filename'"
    path = Path(filename)
    category = _categorize_by_extension(path)
    return "Archivo '{}' categorizado como: {}".format(filename, category)


def _find_duplicates(params: dict) -> str:
    directory = params.get("directory", str(Path.home() / "Downloads"))
    dir_path = Path(directory)

    if not dir_path.exists():
        return "Directorio no existe: {}".format(directory)

    files = [f for f in dir_path.rglob("*") if f.is_file()]
    size_groups = {}
    for f in files:
        size = f.stat().st_size
        size_groups.setdefault(size, []).append(f)

    duplicates = {size: paths for size, paths in size_groups.items() if len(paths) > 1}

    if not duplicates:
        return "No se encontraron duplicados en {}".format(directory)

    total_dupes = sum(len(paths) - 1 for paths in duplicates.values())
    lines = ["Duplicados encontrados ({} archivos duplicados):".format(total_dupes)]
    for size, paths in list(duplicates.items())[:10]:
        lines.append("  Tamaño {:.1f}KB:".format(size / 1024))
        for p in paths:
            lines.append("    {}".format(p.name))
    return "\n".join(lines)


def _clean_directory(params: dict) -> str:
    directory = params.get("directory", str(Path.home() / "Downloads"))
    min_age_days = int(params.get("min_age_days", 30))
    dry_run = params.get("dry_run", True)

    dir_path = Path(directory)
    if not dir_path.exists():
        return "Directorio no existe: {}".format(directory)

    cutoff = datetime.now().timestamp() - (min_age_days * 86400)
    old_files = [f for f in dir_path.iterdir() if f.is_file() and f.stat().st_mtime < cutoff]

    if not old_files:
        return "No hay archivos mayores a {} días en {}".format(min_age_days, directory)

    if dry_run:
        return "PREVIEW: {} archivos mayores a {} días serían eliminados".format(len(old_files), min_age_days)

    deleted = 0
    for f in old_files:
        try:
            f.unlink()
            deleted += 1
        except Exception:
            pass
    return "Eliminados {} archivos mayores a {} días".format(deleted, min_age_days)


def _recent_files(params: dict) -> str:
    directory = params.get("directory", str(Path.home() / "Downloads"))
    limit = int(params.get("limit", 10))

    dir_path = Path(directory)
    if not dir_path.exists():
        return "Directorio no existe"

    files = sorted([f for f in dir_path.iterdir() if f.is_file()],
                   key=lambda x: x.stat().st_mtime, reverse=True)

    lines = ["Archivos recientes en {}:".format(directory)]
    for f in files[:limit]:
        mtime = datetime.fromtimestamp(f.stat().st_mtime)
        lines.append("  {} | {:.1f}KB | {}".format(f.name, f.stat().st_size/1024, mtime.strftime("%Y-%m-%d %H:%M")))
    return "\n".join(lines)


def _big_files(params: dict) -> str:
    directory = params.get("directory", str(Path.home() / "Downloads"))
    limit = int(params.get("limit", 10))

    dir_path = Path(directory)
    if not dir_path.exists():
        return "Directorio no existe"

    files = sorted([f for f in dir_path.rglob("*") if f.is_file()],
                   key=lambda x: x.stat().st_size, reverse=True)

    lines = ["Archivos más grandes en {}:".format(directory)]
    for f in files[:limit]:
        lines.append("  {} | {:.1f}MB".format(f.name, f.stat().st_size / (1024*1024)))
    return "\n".join(lines)


def _categorize_by_extension(path, custom_rules=None):
    ext = path.suffix.lower()
    if custom_rules:
        for pattern, category in custom_rules.items():
            if ext == pattern or path.name.endswith(pattern):
                return category
    for category, extensions in FILE_CATEGORIES.items():
        if ext in extensions:
            return category
    return "other"


def _log_organize(actions):
    log = _load_log()
    log["last_actions"] = actions
    log.setdefault("history", []).append({
        "timestamp": datetime.now().isoformat(),
        "count": len(actions),
    })
    log["history"] = log["history"][-50:]
    _save_log(log)


def _load_rules():
    path = _BASE / "data" / "organizer_rules.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def _save_rules(rules):
    path = _BASE / "data" / "organizer_rules.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rules, indent=2, ensure_ascii=False), encoding="utf-8")


def _load_log():
    if _ORGANIZER_LOG.exists():
        try:
            return json.loads(_ORGANIZER_LOG.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"last_actions": [], "history": []}


def _save_log(log):
    _ORGANIZER_LOG.parent.mkdir(parents=True, exist_ok=True)
    _ORGANIZER_LOG.write_text(json.dumps(log, indent=2, ensure_ascii=False), encoding="utf-8")
