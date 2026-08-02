# -*- coding: utf-8 -*-
"""
plugin_manage.py — Gestion de plugins de ERIS (via PluginManager).
Acciones: list, reload, reload_one (name), info (name).
"""
from __future__ import annotations


def plugin_manage(parameters: dict = None, player=None) -> str:
    if parameters is None:
        parameters = {}
    action = parameters.get("action", "list").lower()

    try:
        from core.plugin_manager import get_plugin_manager
        mgr = get_plugin_manager()
    except Exception as e:
        return f"Error: gestor de plugins no disponible ({e})"

    if action == "list":
        plugins = mgr.list_plugins()
        if not plugins:
            return "No hay plugins cargados."
        lines = [f"Plugins ({len(plugins)}):"]
        for p in plugins:
            name = p.get("name", "?")
            version = p.get("version", "?")
            status = p.get("status", "?")
            lines.append(f"  - {name} v{version} [{status}]")
        return "\n".join(lines)

    if action == "reload":
        loaded, errors = mgr.reload()
        return f"Plugins recargados: {len(loaded)}. Errores: {len(errors)}" + (f" -> {errors[:3]}" if errors else "")

    if action in ("reload_one", "info"):
        name = (parameters.get("name") or "").strip()
        if not name:
            return "Error: se requiere 'name'."
        if action == "reload_one":
            ok = mgr.reload_one(name)
            return f"Plugin '{name}' recargado." if ok else f"No se pudo recargar '{name}'."
        plugin = mgr.get_plugin(name)
        if not plugin:
            return f"Plugin '{name}' no encontrado."
        return f"Plugin: {name} (cargado: {plugin is not None})"

    return "Acciones: list, reload, reload_one (name), info (name)."
