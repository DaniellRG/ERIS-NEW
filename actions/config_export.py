"""
config_export.py — Exportar/Importar configuración completa de ERIS.
Backup y restore de todos los settings, themes, plugins, knowledge base.
"""
import json
import shutil
import zipfile
from pathlib import Path
from datetime import datetime

_BASE = Path(__file__).resolve().parent.parent
_EXPORT_DIR = _BASE / "data" / "exports"

CONFIG_DIRS = [
    "config",
    "data/self",
    "memory",
]
CONFIG_FILES = [
    "config/theme.json",
    "config/plugins.json",
    "config/email_credentials.json",
    "config/google_credentials.json",
    "data/autonomous_learn.json",
    "data/idle_learning.json",
    "data/smart_cache.json",
    "data/cache_stats.json",
]


def config_export(parameters: dict = None, player=None) -> str:
    """Export/Import configuración."""
    params = parameters or {}
    action = params.get("action", "status").lower()

    if action == "export":
        return _export_config(params)
    elif action == "import":
        return _import_config(params)
    elif action == "status":
        return _get_status()
    elif action == "list":
        return _list_exports()
    elif action == "diff":
        return _diff_exports(params)
    elif action == "delete":
        return _delete_export(params)
    elif action == "validate":
        return _validate_export(params)
    elif action == "backup":
        return _full_backup()
    elif action == "restore":
        return _full_restore(params)
    return "Acciones: export, import, status, list, diff, delete, validate, backup, restore"


def _export_config(params: dict) -> str:
    name = params.get("name", "backup_{}".format(datetime.now().strftime("%Y%m%d_%H%M%S")))
    include = params.get("include", "all")

    export_data = {"name": name, "exported_at": datetime.now().isoformat(), "files": {}}

    for rel_path in CONFIG_FILES:
        full_path = _BASE / rel_path
        if full_path.exists():
            try:
                content = full_path.read_text(encoding="utf-8")
                export_data["files"][rel_path] = content
            except:
                pass

    if include in ("all", "memory"):
        mem_dir = _BASE / "memory"
        if mem_dir.exists():
            for f in mem_dir.glob("*.json"):
                try:
                    export_data["files"]["memory/{}".format(f.name)] = f.read_text(encoding="utf-8")
                except:
                    pass

    if include in ("all", "knowledge"):
        kb_dir = _BASE / "data" / "knowledge"
        if kb_dir.exists():
            for f in kb_dir.glob("*.md"):
                try:
                    export_data["files"]["knowledge/{}".format(f.name)] = f.read_text(encoding="utf-8")
                except:
                    pass

    if include in ("all", "plugins"):
        plugins_dir = _BASE / "plugins"
        if plugins_dir.exists():
            for f in plugins_dir.glob("*.py"):
                try:
                    export_data["files"]["plugins/{}".format(f.name)] = f.read_text(encoding="utf-8")
                except:
                    pass

    _EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    export_path = _EXPORT_DIR / "{}.json".format(name)
    export_path.write_text(json.dumps(export_data, indent=2, ensure_ascii=False), encoding="utf-8")

    zip_path = _EXPORT_DIR / "{}.zip".format(name)
    with zipfile.ZipFile(str(zip_path), 'w', zipfile.ZIP_DEFLATED) as zf:
        for rel, content in export_data["files"].items():
            zf.writestr(rel, content)
        zf.writestr("manifest.json", json.dumps({
            "name": name,
            "exported_at": export_data["exported_at"],
            "file_count": len(export_data["files"]),
        }, indent=2))

    return "Config exportada: {} ({} files, {} zip)".format(
        name, len(export_data["files"]),
        "{}KB".format(int(zip_path.stat().st_size / 1024)) if zip_path.exists() else "N/A")


def _import_config(params: dict) -> str:
    name = params.get("name", "")
    if not name:
        return "Error: se requiere 'name'. Usa 'list' para ver disponibles"

    zip_path = _EXPORT_DIR / "{}.zip".format(name)
    if not zip_path.exists():
        return "Export no encontrado: {}".format(name)

    try:
        imported = 0
        with zipfile.ZipFile(str(zip_path), 'r') as zf:
            for info in zf.infolist():
                if info.filename == "manifest.json":
                    continue
                content = zf.read(info.filename).decode("utf-8")

                if info.filename.startswith("knowledge/"):
                    target = _BASE / "data" / "knowledge" / info.filename.split("/", 1)[1]
                elif info.filename.startswith("plugins/"):
                    target = _BASE / "plugins" / info.filename.split("/", 1)[1]
                else:
                    target = _BASE / info.filename

                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
                imported += 1

        return "Config importada: {} ({} files restaurados)".format(name, imported)
    except Exception as e:
        return "Error importando: {}".format(str(e))


def _full_backup() -> str:
    name = "full_{}".format(datetime.now().strftime("%Y%m%d_%H%M%S"))
    return _export_config({"name": name, "include": "all"})


def _full_restore(params: dict) -> str:
    exports = _list_exports_data()
    if not exports:
        return "No hay backups para restaurar"
    latest = exports[-1]
    return _import_config({"name": latest["name"]})


def _list_exports() -> str:
    exports = _list_exports_data()
    if not exports:
        return "Sin exports disponibles"
    lines = ["═══ EXPORTS DISPONIBLES ═══", ""]
    for e in exports:
        lines.append("  {} — {} ({} files)".format(
            e["name"], e.get("exported_at", "?")[:19], e.get("file_count", "?")))
    return "\n".join(lines)


def _list_exports_data() -> list:
    if not _EXPORT_DIR.exists():
        return []
    exports = []
    for f in sorted(_EXPORT_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            exports.append(data)
        except:
            pass
    return exports


def _diff_exports(params: dict) -> str:
    name = params.get("name", "")
    compare = params.get("compare", "")
    if not name:
        return "Error: se requiere 'name' (y opcional 'compare' para comparar contra otro backup)"
    target_path = _EXPORT_DIR / "{}.json".format(name)
    if not target_path.exists():
        return "Export no encontrado: {}".format(name)

    try:
        target = json.loads(target_path.read_text(encoding="utf-8"))
    except Exception as e:
        return "Error leyendo '{}': {}".format(name, e)

    if compare:
        cmp_path = _EXPORT_DIR / "{}.json".format(compare)
        if not cmp_path.exists():
            return "Export '{}' no encontrado para comparar".format(compare)
        try:
            other = json.loads(cmp_path.read_text(encoding="utf-8"))
        except Exception as e:
            return "Error leyendo '{}': {}".format(compare, e)
        other_files = other.get("files", {})
    else:
        other_files = {}

    target_files = target.get("files", {})
    changed, added, removed = [], [], []
    for rel, content in target_files.items():
        if rel in other_files:
            if other_files[rel] != content:
                changed.append(rel)
        else:
            added.append(rel)
    for rel in other_files:
        if rel not in target_files:
            removed.append(rel)

    lines = [
        "=== DIFF {} {} ===".format(name, "vs " + compare if compare else "vs estado actual"),
        "  Cambiados: {}".format(len(changed)),
        "  Agregados: {}".format(len(added)),
        "  Eliminados: {}".format(len(removed)),
        "",
    ]
    for rel in changed[:20]:
        lines.append("  ~ {}".format(rel))
    for rel in added[:20]:
        lines.append("  + {}".format(rel))
    for rel in removed[:20]:
        lines.append("  - {}".format(rel))
    if len(changed) + len(added) + len(removed) > 60:
        lines.append("  ... y más")
    return "\n".join(lines)


def _delete_export(params: dict) -> str:
    name = params.get("name", "")
    if not name:
        return "Error: se requiere 'name'"
    deleted = 0
    for ext in [".json", ".zip"]:
        p = _EXPORT_DIR / "{}{}".format(name, ext)
        if p.exists():
            p.unlink()
            deleted += 1
    return "Eliminados {} archivos de '{}'".format(deleted, name) if deleted else "No encontrado: {}".format(name)


def _validate_export(params: dict) -> str:
    name = params.get("name", "")
    if not name:
        return "Error: se requiere 'name'"
    zip_path = _EXPORT_DIR / "{}.zip".format(name)
    if not zip_path.exists():
        return "No encontrado: {}".format(name)
    try:
        with zipfile.ZipFile(str(zip_path), 'r') as zf:
            bad = zf.testzip()
            if bad:
                return "ZIP corrupto: {}".format(bad)
            files = [f for f in zf.namelist() if f != "manifest.json"]
            return "Export '{}' válido: {} files, sin errores".format(name, len(files))
    except Exception as e:
        return "Error validando: {}".format(str(e))


def _get_status() -> str:
    exports = _list_exports_data()
    kb_count = len(list((_BASE / "data" / "knowledge").glob("*.md"))) if (_BASE / "data" / "knowledge").exists() else 0
    plugin_count = len(list((_BASE / "plugins").glob("*.py"))) if (_BASE / "plugins").exists() else 0
    mem_count = len(list((_BASE / "memory").glob("*.json"))) if (_BASE / "memory").exists() else 0
    lines = [
        "═══ CONFIG EXPORT STATUS ═══",
        "",
        "  Exports:        {}".format(len(exports)),
        "  Knowledge docs: {}".format(kb_count),
        "  Plugins:        {}".format(plugin_count),
        "  Memory files:   {}".format(mem_count),
        "  Config files:   {}".format(len(CONFIG_FILES)),
    ]
    return "\n".join(lines)
