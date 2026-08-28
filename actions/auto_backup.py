"""
actions/auto_backup.py — Auto-backup system for ERIS.
Periodically backs up config, memory, knowledge, and data files.
"""
import json
import os
import shutil
import threading
import time
from datetime import datetime
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_BACKUP_DIR = _BASE / "backups" / "auto"
_STATE_FILE = _BASE / "data" / "auto_backup_state.json"
_CONFIG_FILE = _BASE / "config" / "auto_backup.json"

_DEFAULT_CONFIG = {
    "enabled": True,
    "interval_hours": 6,
    "max_backups": 10,
    "backup_items": [
        {"name": "memory", "path": "memory", "type": "dir"},
        {"name": "knowledge", "path": "data/knowledge", "type": "dir"},
        {"name": "self", "path": "data/self", "type": "dir"},
        {"name": "config", "path": "config", "type": "dir"},
        {"name": "plugins", "path": "plugins", "type": "dir"},
        {"name": "prompt", "path": "core/prompt.txt", "type": "file"},
        {"name": "tool_declarations", "path": "core/tool_declarations.py", "type": "file"},
        {"name": "action_imports", "path": "core/action_imports.py", "type": "file"},
        {"name": "version", "path": "core/version.py", "type": "file"},
        {"name": "rag_index", "path": "data/rag_index.json", "type": "file"},
        {"name": "idle_learning", "path": "data/idle_learning.json", "type": "file"},
        {"name": "auto_backup_state", "path": "data/auto_backup_state.json", "type": "file"},
    ],
}

_running = False
_thread = None


def _load_config():
    if _CONFIG_FILE.exists():
        try:
            return json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return _DEFAULT_CONFIG.copy()


def _save_config(config):
    _CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    _CONFIG_FILE.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")


def _load_state():
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"last_backup": None, "backup_count": 0, "history": []}


def _save_state(state):
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def _do_backup():
    config = _load_config()
    state = _load_state()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = _BACKUP_DIR / f"backup_{ts}"
    backup_path.mkdir(parents=True, exist_ok=True)

    items_backed = 0
    items_failed = 0
    details = []

    for item in config.get("backup_items", []):
        name = item["name"]
        src = _BASE / item["path"]
        item_type = item.get("type", "dir")

        if not src.exists():
            items_failed += 1
            details.append(f"  SKIP {name}: not found")
            continue

        try:
            dst = backup_path / name
            if item_type == "dir" and src.is_dir():
                shutil.copytree(str(src), str(dst), dirs_exist_ok=True)
            elif item_type == "file" and src.is_file():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(src), str(dst))
            items_backed += 1
            details.append(f"  OK {name}")
        except Exception as e:
            items_failed += 1
            details.append(f"  FAIL {name}: {str(e)[:60]}")

    # Save backup metadata
    meta = {
        "timestamp": datetime.now().isoformat(),
        "path": str(backup_path),
        "items_backed": items_backed,
        "items_failed": items_failed,
    }

    state["last_backup"] = meta["timestamp"]
    state["backup_count"] = state.get("backup_count", 0) + 1
    state["history"].append(meta)
    state["history"] = state["history"][-50:]
    _save_state(state)

    # Cleanup old backups
    max_backups = config.get("max_backups", 10)
    if _BACKUP_DIR.exists():
        backups = sorted([d for d in _BACKUP_DIR.iterdir() if d.is_dir()], key=lambda d: d.name)
        while len(backups) > max_backups:
            oldest = backups.pop(0)
            shutil.rmtree(str(oldest), ignore_errors=True)

    return meta, details


def auto_backup(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = params.get("action", "status").lower()

    if action == "backup":
        meta, details = _do_backup()
        lines = [
            "Auto Backup completado:",
            f"  Timestamp: {meta['timestamp']}",
            f"  Items: {meta['items_backed']} OK, {meta['items_failed']} FAIL",
            f"  Path: {meta['path']}",
        ]
        lines.extend(details)
        return "\n".join(lines)

    elif action == "status":
        config = _load_config()
        state = _load_state()
        lines = [
            "Auto Backup Status:",
            f"  Enabled: {config.get('enabled', True)}",
            f"  Interval: {config.get('interval_hours', 6)}h",
            f"  Max backups: {config.get('max_backups', 10)}",
            f"  Last backup: {state.get('last_backup', 'never')}",
            f"  Total backups: {state.get('backup_count', 0)}",
            f"  Items configured: {len(config.get('backup_items', []))}",
        ]
        return "\n".join(lines)

    elif action == "history":
        state = _load_state()
        history = state.get("history", [])
        if not history:
            return "No backup history."
        lines = [f"Backup History ({len(history)}):"]
        for h in history[-10:]:
            lines.append(f"  {h['timestamp']} | {h['items_backed']} items | {h.get('path', '?')[-30:]}")
        return "\n".join(lines)

    elif action == "config":
        config = _load_config()
        if "set" in params:
            key = params["set"]
            value = params.get("value", "")
            if key == "enabled":
                config["enabled"] = value.lower() in ("true", "1", "yes", "on")
            elif key == "interval_hours":
                config["interval_hours"] = int(value)
            elif key == "max_backups":
                config["max_backups"] = int(value)
            _save_config(config)
            return f"Config updated: {key} = {value}"
        return json.dumps(config, indent=2, ensure_ascii=False)

    elif action == "list":
        if not _BACKUP_DIR.exists():
            return "No backups found."
        backups = sorted([d for d in _BACKUP_DIR.iterdir() if d.is_dir()], key=lambda d: d.name, reverse=True)
        if not backups:
            return "No backups found."
        lines = [f"Backups ({len(backups)}):"]
        for b in backups[:20]:
            size = sum(f.stat().st_size for f in b.rglob("*") if f.is_file())
            size_str = f"{size / 1024:.1f}KB" if size < 1024 * 1024 else f"{size / (1024**2):.1f}MB"
            lines.append(f"  {b.name} | {size_str}")
        return "\n".join(lines)

    elif action == "start":
        config = _load_config()
        config["enabled"] = True
        _save_config(config)
        return "Auto-backup enabled."

    elif action == "stop":
        config = _load_config()
        config["enabled"] = False
        _save_config(config)
        return "Auto-backup disabled."

    elif action == "add_item":
        name = params.get("name", "")
        path = params.get("path", "")
        item_type = params.get("type", "file")
        if not name or not path:
            return "Requires 'name' and 'path'."
        config = _load_config()
        config["backup_items"].append({"name": name, "path": path, "type": item_type})
        _save_config(config)
        return f"Added backup item: {name} -> {path}"

    elif action == "remove_item":
        name = params.get("name", "")
        if not name:
            return "Requires 'name'."
        config = _load_config()
        config["backup_items"] = [i for i in config["backup_items"] if i["name"] != name]
        _save_config(config)
        return f"Removed backup item: {name}"

    return "Actions: backup, status, history, config, list, start, stop, add_item, remove_item"


def _scheduler_loop():
    """Loop daemon: corre un backup cada interval_hours si enabled."""
    global _running
    _running = True
    while _running:
        try:
            time.sleep(3600)
            config = _load_config()
            if not config.get("enabled", True):
                continue
            state = _load_state()
            last = state.get("last_backup")
            interval = config.get("interval_hours", 6)
            fmt = "%Y-%m-%dT%H:%M:%S"
            due = True
            if last:
                try:
                    last_dt = datetime.strptime(last[:19], fmt)
                    due = (datetime.now() - last_dt).total_seconds() >= interval * 3600
                except Exception:
                    due = True
            if due:
                meta, details = _do_backup()
                print(f"[AutoBackup] {meta['timestamp']} — {meta['items_backed']} OK, {meta['items_failed']} FAIL")
        except Exception as e:
            print(f"[AutoBackup] scheduler error: {e}")


def start_auto_backup_scheduler() -> bool:
    """Inicia (una sola vez) el scheduler de backups en background. Devuelve si está activo."""
    global _thread, _running
    if _thread and _thread.is_alive():
        return True
    _running = True
    _thread = threading.Thread(target=_scheduler_loop, daemon=True)
    _thread.start()
    return True
