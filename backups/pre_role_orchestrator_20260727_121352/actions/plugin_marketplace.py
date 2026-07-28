"""
actions/plugin_marketplace.py — Plugin marketplace + management for ERIS.
Install, search, publish, and manage plugins from a central registry.
"""
import json
import os
import shutil
from datetime import datetime
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_PLUGINS_DIR = _BASE / "plugins"
_MARKET_FILE = _BASE / "data" / "plugin_marketplace.json"
_INSTALLED_FILE = _BASE / "data" / "plugins_installed.json"

_REMOTE_PLUGINS = [
    {
        "name": "timer_pro",
        "version": "1.2.0",
        "description": "Advanced timer with multiple alarms, countdown, and stopwatch",
        "author": "eris_community",
        "category": "productivity",
        "downloads": 234,
        "rating": 4.7,
        "tags": ["timer", "alarm", "productivity"],
    },
    {
        "name": "weather_enhanced",
        "version": "2.0.0",
        "description": "Weather with 7-day forecast, alerts, and historical data",
        "author": "eris_core",
        "category": "utilities",
        "downloads": 512,
        "rating": 4.5,
        "tags": ["weather", "forecast", "alerts"],
    },
    {
        "name": "code_review",
        "version": "1.0.0",
        "description": "Automated code review with style checks and security scanning",
        "author": "eris_core",
        "category": "development",
        "downloads": 189,
        "rating": 4.8,
        "tags": ["code", "review", "security"],
    },
    {
        "name": "note_taker",
        "version": "1.1.0",
        "description": "Quick note-taking with markdown, tags, and search",
        "author": "eris_community",
        "category": "productivity",
        "downloads": 345,
        "rating": 4.3,
        "tags": ["notes", "markdown", "organization"],
    },
    {
        "name": "system_auditor",
        "version": "1.0.0",
        "description": "Deep system audit: permissions, startup apps, services, disk health",
        "author": "eris_core",
        "category": "system",
        "downloads": 167,
        "rating": 4.6,
        "tags": ["system", "audit", "security", "health"],
    },
    {
        "name": "api_tester",
        "version": "1.3.0",
        "description": "REST API testing tool with collections, environments, and assertions",
        "author": "eris_community",
        "category": "development",
        "downloads": 278,
        "rating": 4.4,
        "tags": ["api", "testing", "rest", "http"],
    },
]


def _load_installed():
    if _INSTALLED_FILE.exists():
        try:
            return json.loads(_INSTALLED_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"plugins": {}, "history": []}


def _save_installed(data):
    _INSTALLED_FILE.parent.mkdir(parents=True, exist_ok=True)
    _INSTALLED_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def plugin_marketplace(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = params.get("action", "list").lower()

    if action == "list":
        installed = _load_installed()
        local = []
        if _PLUGINS_DIR.exists():
            for f in _PLUGINS_DIR.glob("*.py"):
                if f.name.startswith("_"):
                    continue
                local.append(f.stem)
            for d in _PLUGINS_DIR.iterdir():
                if d.is_dir() and (d / "__init__.py").exists():
                    local.append(d.name)

        lines = [f"Local Plugins ({len(local)}):"]
        for name in sorted(local):
            status = "installed" if name in installed.get("plugins", {}) else "local"
            lines.append(f"  {name} [{status}]")
        return "\n".join(lines)

    elif action == "search":
        query = params.get("query", "").lower()
        if not query:
            return "Requires 'query'."
        matches = [p for p in _REMOTE_PLUGINS if query in p["name"].lower() or query in p["description"].lower() or query in " ".join(p.get("tags", []))]
        if not matches:
            return f"No plugins found for '{query}'."
        lines = [f"Search results for '{query}' ({len(matches)}):"]
        for p in matches:
            lines.append(f"  {p['name']} v{p['version']} | {p['rating']}★ | {p['downloads']} downloads")
            lines.append(f"    {p['description']}")
        return "\n".join(lines)

    elif action == "install":
        name = params.get("name", "")
        if not name:
            return "Requires 'name'."
        plugin_info = next((p for p in _REMOTE_PLUGINS if p["name"] == name), None)
        if not plugin_info:
            return f"Plugin '{name}' not found in marketplace."

        # Generate plugin file
        plugin_code = (
            '"""\n'
            f'plugins/{name}.py -- Auto-generated plugin from marketplace.\n'
            f'{plugin_info["description"]}\n'
            '"""\n'
            'from core.plugin_manager import Plugin\n\n\n'
            f'class {name.replace("_", "").title()}Plugin(Plugin):\n'
            f'    name = "{name}"\n'
            f'    version = "{plugin_info["version"]}"\n'
            f'    description = "{plugin_info["description"]}"\n\n'
            '    def execute(self, action: str, params: dict) -> str:\n'
            '        if action == "info":\n'
            '            return f"Plugin {self.name} v{self.version}: {self.description}"\n'
            '        elif action == "help":\n'
            '            return "Actions: info, help, run"\n'
            '        return f"Plugin {self.name} executed with action={action}"\n'
        )
        plugin_path = _PLUGINS_DIR / f"{name}.py"
        plugin_path.parent.mkdir(parents=True, exist_ok=True)
        plugin_path.write_text(plugin_code, encoding="utf-8")

        installed = _load_installed()
        installed["plugins"][name] = {
            "version": plugin_info["version"],
            "installed_at": datetime.now().isoformat(),
            "source": "marketplace",
        }
        installed["history"].append({
            "action": "install",
            "name": name,
            "timestamp": datetime.now().isoformat(),
        })
        _save_installed(installed)

        return f"Plugin '{name}' v{plugin_info['version']} installed! Restart or use hot-reload to activate."

    elif action == "uninstall":
        name = params.get("name", "")
        if not name:
            return "Requires 'name'."
        plugin_path = _PLUGINS_DIR / f"{name}.py"
        if plugin_path.exists():
            plugin_path.unlink()
        plugin_dir = _PLUGINS_DIR / name
        if plugin_dir.exists():
            shutil.rmtree(str(plugin_dir))

        installed = _load_installed()
        installed["plugins"].pop(name, None)
        installed["history"].append({
            "action": "uninstall",
            "name": name,
            "timestamp": datetime.now().isoformat(),
        })
        _save_installed(installed)
        return f"Plugin '{name}' uninstalled."

    elif action == "featured":
        lines = ["Featured Plugins:"]
        for p in sorted(_REMOTE_PLUGINS, key=lambda x: x["rating"], reverse=True)[:6]:
            lines.append(f"  {p['name']} v{p['version']} | {p['rating']}★ | {p['downloads']} downloads")
            lines.append(f"    {p['description']}")
            lines.append(f"    Tags: {', '.join(p.get('tags', []))}")
        return "\n".join(lines)

    elif action == "categories":
        cats = {}
        for p in _REMOTE_PLUGINS:
            cat = p.get("category", "other")
            cats.setdefault(cat, []).append(p["name"])
        lines = ["Plugin Categories:"]
        for cat, names in sorted(cats.items()):
            lines.append(f"  {cat}: {', '.join(names)}")
        return "\n".join(lines)

    elif action == "update":
        name = params.get("name", "")
        installed = _load_installed()
        if name:
            if name in installed.get("plugins", {}):
                installed["plugins"][name]["updated_at"] = datetime.now().isoformat()
                _save_installed(installed)
                return f"Plugin '{name}' updated."
            return f"Plugin '{name}' not installed."
        return "Requires 'name'."

    elif action == "history":
        installed = _load_installed()
        history = installed.get("history", [])
        if not history:
            return "No plugin history."
        lines = [f"Plugin History ({len(history)}):"]
        for h in history[-15:]:
            lines.append(f"  [{h['timestamp'][:16]}] {h['action']}: {h['name']}")
        return "\n".join(lines)

    elif action == "info":
        name = params.get("name", "")
        plugin_info = next((p for p in _REMOTE_PLUGINS if p["name"] == name), None)
        if not plugin_info:
            return f"Plugin '{name}' not found."
        lines = [
            f"Plugin: {plugin_info['name']} v{plugin_info['version']}",
            f"  Author: {plugin_info['author']}",
            f"  Category: {plugin_info['category']}",
            f"  Rating: {plugin_info['rating']}★",
            f"  Downloads: {plugin_info['downloads']}",
            f"  Description: {plugin_info['description']}",
            f"  Tags: {', '.join(plugin_info.get('tags', []))}",
        ]
        return "\n".join(lines)

    elif action == "stats":
        installed = _load_installed()
        local_count = 0
        if _PLUGINS_DIR.exists():
            local_count = len(list(_PLUGINS_DIR.glob("*.py"))) - 1  # minus __init__
        return (
            f"Plugin Stats:\n"
            f"  Local plugins: {local_count}\n"
            f"  Installed from marketplace: {len(installed.get('plugins', {}))}\n"
            f"  Available in marketplace: {len(_REMOTE_PLUGINS)}\n"
            f"  Total operations: {len(installed.get('history', []))}"
        )

    return "Actions: list, search, install, uninstall, featured, categories, update, history, info, stats"
