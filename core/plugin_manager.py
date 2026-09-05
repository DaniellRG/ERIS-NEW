"""
core/plugin_manager.py — Hot-loadable plugin system for ERIS.
Scans plugins/ for Python modules, loads them as callable tools,
and supports live reload via mtime polling.
"""
from __future__ import annotations

import importlib
import inspect
import os
import sys
import threading
import time
import traceback
from pathlib import Path
from typing import Any, Callable

PLUGINS_DIR = Path(__file__).resolve().parent.parent / "plugins"
POLL_INTERVAL = 15.0  # seconds between mtime checks


class Plugin:
    """Base class that plugins can extend. Optional — any callable with execute() works."""

    name: str = ""
    version: str = "1.0.0"
    description: str = ""

    def on_load(self):
        """Called when plugin is first loaded."""

    def on_unload(self):
        """Called when plugin is removed or reloaded."""

    def execute(self, action: str, params: dict) -> str:
        """Main entry point. Return a string response."""
        return "Not implemented."


class PluginManager:
    def __init__(self):
        self._plugins: dict[str, Plugin] = {}
        self._tools: dict[str, Callable] = {}
        self._mtime_cache: dict[str, float] = {}
        self._lock = threading.Lock()
        self._running = False
        self._thread: threading.Thread | None = None

        PLUGINS_DIR.mkdir(exist_ok=True)

    # ── Public API ──

    def discover(self):
        """Scan plugins/ directory and load all valid plugins."""
        loaded: list[str] = []
        errors: list[str] = []

        for entry in sorted(PLUGINS_DIR.iterdir()):
            if entry.is_dir():
                init_file = entry / "__init__.py"
                if init_file.exists():
                    mod_name = f"plugins.{entry.name}"
                    ok, p = self._load_module(mod_name, entry)
                    if ok:
                        loaded.append(entry.name)
                    else:
                        errors.append(p)
            elif entry.suffix == ".py" and entry.name != "__init__.py":
                mod_name = f"plugins.{entry.stem}"
                ok, p = self._load_module(mod_name, entry)
                if ok:
                    loaded.append(entry.name)
                else:
                    errors.append(p)

        return loaded, errors

    def reload(self) -> tuple[list[str], list[str]]:
        """Hot-reload all plugins (clears cache, re-discovers)."""
        with self._lock:
            names = list(self._plugins.keys())
            for n in names:
                try:
                    self._plugins[n].on_unload()
                except Exception:
                    pass
            self._plugins.clear()
            self._tools.clear()
            self._mtime_cache.clear()

            # Remove cached plugin modules from sys.modules
            for mod_name in list(sys.modules.keys()):
                if mod_name.startswith("plugins."):
                    del sys.modules[mod_name]

        return self.discover()

    def reload_one(self, plugin_name: str) -> bool:
        """Reload a single plugin by name (without .py extension)."""
        with self._lock:
            key = f"plugins.{plugin_name}"
            if plugin_name in self._plugins:
                try:
                    self._plugins[plugin_name].on_unload()
                except Exception:
                    pass
                del self._plugins[plugin_name]
            if plugin_name in self._tools:
                del self._tools[plugin_name]
            self._mtime_cache.pop(plugin_name, None)
            if key in sys.modules:
                del sys.modules[key]

        for entry in sorted(PLUGINS_DIR.iterdir()):
            stem = entry.stem if entry.suffix == ".py" else entry.name
            if stem == plugin_name:
                mod_name = f"plugins.{stem}"
                ok, msg = self._load_module(mod_name, entry)
                return ok
        return False

    def get_tool(self, name: str) -> Callable | None:
        """Get a plugin callable by tool name (prefixed 'plugin_').
        Used by tool_registry."""
        with self._lock:
            return self._tools.get(name)

    def get_plugin(self, name: str) -> Plugin | None:
        with self._lock:
            return self._plugins.get(name)

    def list_plugins(self) -> list[dict]:
        with self._lock:
            return [
                {"name": p.name, "version": p.version, "description": p.description}
                for p in self._plugins.values()
            ]

    # ── Hot-reload polling ──

    def start_polling(self):
        """Start background thread that checks mtime changes."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def stop_polling(self):
        self._running = False

    def _poll_loop(self):
        while self._running:
            time.sleep(POLL_INTERVAL)
            try:
                self._check_mtimes()
            except Exception:
                pass

    def _check_mtimes(self):
        changed: list[str] = []
        for entry in sorted(PLUGINS_DIR.iterdir()):
            if entry.suffix != ".py" and not (entry.is_dir() and (entry / "__init__.py").exists()):
                continue
            stem = entry.stem if entry.suffix == ".py" else entry.name
            current_mtime = entry.stat().st_mtime if entry.is_file() else (entry / "__init__.py").stat().st_mtime
            last_mtime = self._mtime_cache.get(stem)
            if last_mtime is not None and current_mtime != last_mtime:
                changed.append(stem)
            self._mtime_cache[stem] = current_mtime

        # Check for removed plugins
        for stem in list(self._mtime_cache.keys()):
            entry = PLUGINS_DIR / f"{stem}.py"
            if not entry.exists() and not (PLUGINS_DIR / stem / "__init__.py").exists():
                changed.append(stem)
                self._mtime_cache.pop(stem, None)

        for name in changed:
            self.reload_one(name)

    # ── Internal ──

    def _load_module(self, mod_name: str, entry: Path) -> tuple[bool, str]:
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(mod_name, entry if entry.is_file() else entry / "__init__.py")
            if spec is None or spec.loader is None:
                return False, f"No spec for {mod_name}"
            mod = importlib.util.module_from_spec(spec)
            sys.modules[mod_name] = mod
            spec.loader.exec_module(mod)

            # Find Plugin instance
            plugin_obj = None
            for _name, _obj in inspect.getmembers(mod, lambda x: isinstance(x, Plugin)):
                plugin_obj = _obj
                break

            if plugin_obj is None:
                # Look for class subclassing Plugin
                for _name, _cls in inspect.getmembers(mod, inspect.isclass):
                    if issubclass(_cls, Plugin) and _cls is not Plugin:
                        try:
                            plugin_obj = _cls()
                        except Exception as _ce:
                            return False, f"Failed to instantiate {_name}: {_ce}"
                        break

            if plugin_obj is None:
                return False, f"No Plugin class found in {mod_name}"

            plugin_obj.on_load()

            tool_name = f"plugin_{plugin_obj.name}"
            with self._lock:
                self._plugins[plugin_obj.name] = plugin_obj
                self._tools[tool_name] = lambda action="run", params=None, _p=plugin_obj: _p.execute(action, params or {})

            stem = entry.stem if entry.suffix == ".py" else entry.name
            self._mtime_cache[stem] = entry.stat().st_mtime if entry.is_file() else (entry / "__init__.py").stat().st_mtime

            print(f"[Plugins] Loaded: {plugin_obj.name} v{plugin_obj.version}")
            return True, plugin_obj.name

        except Exception as _e:
            traceback.print_exc()
            return False, f"Error loading {mod_name}: {_e}"


# ── Singleton ──
_plugin_manager: PluginManager | None = None
_lock = threading.Lock()


def get_plugin_manager() -> PluginManager:
    global _plugin_manager
    if _plugin_manager is None:
        with _lock:
            if _plugin_manager is None:
                _plugin_manager = PluginManager()
    return _plugin_manager
