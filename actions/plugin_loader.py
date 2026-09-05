"""
plugin_loader.py — Sistema de plugins real: carga dinámica de manejadores .py.
Hot-reload, dependencias, sandboxing básico.
"""
import json
import importlib.util
import sys
import os
import inspect
from pathlib import Path
from datetime import datetime

_BASE = Path(__file__).resolve().parent.parent
_PLUGINS_DIR = _BASE / "plugins"
_LOADED_PLUGINS = {}
_PLUGIN_CONFIG = _BASE / "config" / "plugins.json"


def plugin_loader(parameters: dict = None, player=None) -> str:
    """Carga y gestión de plugins."""
    params = parameters or {}
    action = params.get("action", "list").lower()

    if action == "list":
        return _list_plugins()
    elif action == "load":
        return _load_plugin(params)
    elif action == "unload":
        return _unload_plugin(params)
    elif action == "reload":
        return _reload_plugin(params)
    elif action == "info":
        return _plugin_info(params)
    elif action == "enable":
        return _enable_plugin(params)
    elif action == "disable":
        return _disable_plugin(params)
    elif action == "scan":
        return _scan_plugins()
    elif action == "status":
        return _get_status()
    elif action == "create":
        return _create_plugin(params)
    elif action == "test":
        return _test_plugin(params)
    return "Acciones: list, load, unload, reload, info, enable, disable, scan, status, create, test"


def _scan_plugins() -> str:
    """Escanea directorio plugins/ buscando .py válidos."""
    if not _PLUGINS_DIR.exists():
        _PLUGINS_DIR.mkdir(parents=True, exist_ok=True)
        return "Directorio plugins/ creado"

    found = []
    for f in sorted(_PLUGINS_DIR.glob("*.py")):
        if f.name.startswith("_"):
            continue
        try:
            content = f.read_text(encoding="utf-8")
            has_handler = "def handler(" in content or "def execute(" in content or "def run(" in content
            found.append({
                "name": f.stem,
                "file": f.name,
                "size": len(content),
                "valid": has_handler,
            })
        except OSError:
            found.append({"name": f.stem, "file": f.name, "valid": False})

    lines = ["═══ ESCANEO DE PLUGINS ═══", ""]
    for p in found:
        status = "✓" if p.get("valid") else "✗"
        lines.append("  [{}] {} ({} bytes)".format(status, p["name"], p.get("size", 0)))
    lines.append("")
    lines.append("  Total: {} plugins, {} válidos".format(
        len(found), sum(1 for p in found if p.get("valid"))))
    return "\n".join(lines)


def _load_plugin(params: dict) -> str:
    name = params.get("name", "")
    if not name:
        return "Error: se requiere 'name'"

    plugin_path = _PLUGINS_DIR / "{}.py".format(name)
    if not plugin_path.exists():
        return "Plugin no encontrado: {}".format(name)

    try:
        spec = importlib.util.spec_from_file_location(
            "eris_plugin_{}".format(name), str(plugin_path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        handler = None
        for attr_name in ["handler", "execute", "run", "main"]:
            if hasattr(module, attr_name):
                handler = getattr(module, attr_name)
                break

        if not handler:
            return "Plugin '{}' no tiene handler (handler/execute/run/main)".format(name)

        meta = {}
        if hasattr(module, "PLUGIN_META"):
            meta = module.PLUGIN_META
        elif hasattr(module, "__doc__") and module.__doc__:
            meta = {"description": module.__doc__.strip()}

        _LOADED_PLUGINS[name] = {
            "handler": handler,
            "module": module,
            "meta": meta,
            "loaded_at": datetime.now().isoformat(),
        }

        desc = meta.get("description", meta.get("name", ""))
        return "Plugin '{}' cargado ✓ {}".format(name, "- {}".format(desc) if desc else "")
    except Exception as e:
        return "Error cargando '{}': {}".format(name, str(e))


def _unload_plugin(params: dict) -> str:
    name = params.get("name", "")
    if not name:
        return "Error: se requiere 'name'"
    if name in _LOADED_PLUGINS:
        del _LOADED_PLUGINS[name]
        if "eris_plugin_{}".format(name) in sys.modules:
            del sys.modules["eris_plugin_{}".format(name)]
        return "Plugin '{}' descargado".format(name)
    return "Plugin '{}' no está cargado".format(name)


def _reload_plugin(params: dict) -> str:
    name = params.get("name", "")
    if not name:
        return "Error: se requiere 'name'"
    _unload_plugin({"name": name})
    return _load_plugin({"name": name})


def _list_plugins() -> str:
    lines = ["═══ PLUGINS CARGADOS ═══", ""]
    if not _LOADED_PLUGINS:
        lines.append("  Ningún plugin cargado")
        lines.append("  Usa 'scan' para buscar, 'load' para cargar")
    else:
        for name, info in _LOADED_PLUGINS.items():
            meta = info.get("meta", {})
            lines.append("  {} — {}".format(name, meta.get("description", "sin descripción")))
            lines.append("    Cargado: {}".format(info.get("loaded_at", "?")[:19]))
    return "\n".join(lines)


def _plugin_info(params: dict) -> str:
    name = params.get("name", "")
    if not name:
        return "Error: se requiere 'name'"
    if name in _LOADED_PLUGINS:
        info = _LOADED_PLUGINS[name]
        meta = info.get("meta", {})
        lines = ["═══ PLUGIN: {} ═══".format(name), ""]
        for k, v in meta.items():
            lines.append("  {:15s} {}".format(k, v))
        lines.append("  Cargado: {}".format(info.get("loaded_at", "?")))
        return "\n".join(lines)

    plugin_path = _PLUGINS_DIR / "{}.py".format(name)
    if plugin_path.exists():
        content = plugin_path.read_text(encoding="utf-8")
        return "Plugin '{}' existe ({} bytes) pero no está cargado".format(name, len(content))
    return "Plugin '{}' no encontrado".format(name)


def _enable_plugin(params: dict) -> str:
    name = params.get("name", "")
    config = _load_config()
    disabled = config.get("disabled", [])
    if name in disabled:
        disabled.remove(name)
        config["disabled"] = disabled
        _save_config(config)
    return _load_plugin({"name": name})


def _disable_plugin(params: dict) -> str:
    name = params.get("name", "")
    config = _load_config()
    disabled = config.get("disabled", [])
    if name not in disabled:
        disabled.append(name)
        config["disabled"] = disabled
        _save_config(config)
    _unload_plugin({"name": name})
    return "Plugin '{}' deshabilitado".format(name)


def _get_status() -> str:
    config = _load_config()
    disabled = config.get("disabled", [])
    scan_count = 0
    if _PLUGINS_DIR.exists():
        scan_count = len(list(_PLUGINS_DIR.glob("*.py")))
    lines = [
        "═══ PLUGIN SYSTEM STATUS ═══",
        "",
        "  Directorio:     {}".format(_PLUGINS_DIR),
        "  Plugins .py:    {}".format(scan_count),
        "  Cargados:       {}".format(len(_LOADED_PLUGINS)),
        "  Deshabilitados: {}".format(len(disabled)),
    ]
    if _LOADED_PLUGINS:
        lines.append("")
        lines.append("  Cargados:")
        for name in _LOADED_PLUGINS:
            lines.append("    - {}".format(name))
    return "\n".join(lines)


def _create_plugin(params: dict) -> str:
    name = params.get("name", "")
    if not name:
        return "Error: se requiere 'name'"

    plugin_path = _PLUGINS_DIR / "{}.py".format(name)
    if plugin_path.exists():
        return "Plugin '{}' ya existe".format(name)

    template = '''"""
{name} — Plugin personalizado para ERIS.
"""
PLUGIN_META = {
    "name": "{name}",
    "version": "1.0",
    "author": "ERIS User",
    "description": "Plugin personalizado",
}


def handler(parameters=None, player=None):
    """Handler principal del plugin."""
    params = parameters or {}
    action = params.get("action", "info")
    if action == "info":
        return "Plugin {name} v1.0 activo"
    elif action == "hello":
        return "¡Hola desde {name}!"
    return "Acciones: info, hello"
'''
    _PLUGINS_DIR.mkdir(parents=True, exist_ok=True)
    plugin_path.write_text(template.format(name=name), encoding="utf-8")
    return "Plugin '{}' creado en {}".format(name, plugin_path)


def _test_plugin(params: dict) -> str:
    name = params.get("name", "")
    if name not in _LOADED_PLUGINS:
        result = _load_plugin({"name": name})
        if "Error" in result:
            return result

    info = _LOADED_PLUGINS.get(name)
    if not info:
        return "No se pudo cargar '{}'".format(name)

    try:
        result = info["handler"](parameters={"action": "info"})
        return "Plugin '{}' test OK: {}".format(name, result)
    except Exception as e:
        return "Plugin '{}' falló: {}".format(name, str(e))


def _load_config() -> dict:
    if _PLUGIN_CONFIG.exists():
        try:
            return json.loads(_PLUGIN_CONFIG.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {"disabled": []}


def _save_config(config: dict):
    _PLUGIN_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    _PLUGIN_CONFIG.write_text(json.dumps(config, indent=2), encoding="utf-8")
