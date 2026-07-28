import os
import json
import shutil
import hashlib
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
BACKUPS_DIR = os.path.join(DATA_DIR, "backups")
METADATA_FILE = os.path.join(DATA_DIR, "backups.json")


def _load_metadata():
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, "r") as f:
            return json.load(f)
    return {"backups": [], "schedules": []}


def _save_metadata(meta):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(METADATA_FILE, "w") as f:
        json.dump(meta, f, indent=2)


def _file_hash(path):
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()
    except (OSError, PermissionError):
        return None


def _scan_directory(directory):
    file_data = {}
    for root, dirs, files in os.walk(directory):
        for fname in files:
            full = os.path.join(root, fname)
            rel = os.path.relpath(full, directory)
            try:
                stat = os.stat(full)
                file_data[rel] = {
                    "size": stat.st_size,
                    "modified": stat.st_mtime,
                    "hash": _file_hash(full)
                }
            except (OSError, PermissionError):
                pass
    return file_data


def backup_system(parameters: dict, player=None) -> str:
    action = parameters.get("action", "create").lower()
    if action == "create":
        return _create_backup(parameters)
    elif action == "restore":
        return _restore_backup(parameters)
    elif action == "list":
        return _list_backups()
    elif action == "delete":
        return _delete_backup(parameters)
    elif action == "schedule":
        return _schedule_backup(parameters)
    elif action == "status":
        return _backup_status()
    elif action == "diff":
        return _diff_backups(parameters)
    else:
        return f"Unknown action: {action}. Valid: create, restore, list, delete, schedule, status, diff"


def _create_backup(parameters: dict):
    source = parameters.get("source", os.path.expanduser("~"))
    backup_type = parameters.get("type", "incremental").lower()
    name = parameters.get("name", f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")

    backup_dir = os.path.join(BACKUPS_DIR, name)
    os.makedirs(backup_dir, exist_ok=True)

    meta = _load_metadata()
    existing_names = [b["name"] for b in meta["backups"]]
    if name in existing_names:
        return f"Backup '{name}' already exists. Choose a different name."

    file_manifest = _scan_directory(source)
    manifest_path = os.path.join(backup_dir, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump({"files": file_manifest, "source": source, "type": backup_type}, f, indent=2)

    changed_files = []
    if backup_type == "incremental" and meta["backups"]:
        last_backup = meta["backups"][-1]
        last_manifest_path = os.path.join(BACKUPS_DIR, last_backup["name"], "manifest.json")
        if os.path.exists(last_manifest_path):
            with open(last_manifest_path, "r") as f:
                last_manifest = json.load(f)
            last_files = last_manifest.get("files", {})
            for rel_path, info in file_manifest.items():
                if rel_path not in last_files or info["hash"] != last_files[rel_path].get("hash"):
                    changed_files.append(rel_path)
        else:
            changed_files = list(file_manifest.keys())
    else:
        changed_files = list(file_manifest.keys())

    copied = 0
    for rel_path in changed_files:
        src = os.path.join(source, rel_path)
        dst = os.path.join(backup_dir, rel_path)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        try:
            shutil.copy2(src, dst)
            copied += 1
        except (OSError, PermissionError):
            pass

    backup_entry = {
        "name": name,
        "source": source,
        "type": backup_type,
        "timestamp": datetime.now().isoformat(),
        "files_count": len(changed_files),
        "copied_count": copied,
        "total_files": len(file_manifest)
    }
    meta["backups"].append(backup_entry)
    _save_metadata(meta)

    return (
        f"Backup '{name}' created ({backup_type}).\n"
        f"Source: {source}\n"
        f"Files backed up: {copied}/{len(changed_files)}\n"
        f"Location: {backup_dir}"
    )


def _restore_backup(parameters: dict):
    name = parameters.get("name", "")
    if not name:
        meta = _load_metadata()
        if not meta["backups"]:
            return "No backups available."
        name = meta["backups"][-1]["name"]

    backup_dir = os.path.join(BACKUPS_DIR, name)
    if not os.path.exists(backup_dir):
        return f"Backup not found: {name}"

    destination = parameters.get("destination", None)
    manifest_path = os.path.join(backup_dir, "manifest.json")
    if not os.path.exists(manifest_path):
        return f"Manifest not found in backup: {name}"

    with open(manifest_path, "r") as f:
        manifest = json.load(f)

    source = manifest.get("source", "")
    if not destination:
        destination = source

    restored = 0
    for rel_path in manifest.get("files", {}):
        src = os.path.join(backup_dir, rel_path)
        dst = os.path.join(destination, rel_path)
        if os.path.exists(src):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            try:
                shutil.copy2(src, dst)
                restored += 1
            except (OSError, PermissionError):
                pass

    return f"Restored {restored} files from '{name}' to: {destination}"


def _list_backups():
    meta = _load_metadata()
    if not meta["backups"]:
        return "No backups found."
    lines = [f"Backups ({len(meta['backups'])}):"]
    for b in meta["backups"]:
        lines.append(
            f"  - {b['name']} | {b['type']} | {b['timestamp']} | "
            f"{b.get('copied_count', 0)} files"
        )
    return "\n".join(lines)


def _delete_backup(parameters: dict):
    name = parameters.get("name", "")
    if not name:
        return "Specify 'name' parameter."

    meta = _load_metadata()
    found = [b for b in meta["backups"] if b["name"] == name]
    if not found:
        return f"Backup not found: {name}"

    backup_dir = os.path.join(BACKUPS_DIR, name)
    if os.path.exists(backup_dir):
        shutil.rmtree(backup_dir)

    meta["backups"] = [b for b in meta["backups"] if b["name"] != name]
    _save_metadata(meta)
    return f"Backup '{name}' deleted."


def _schedule_backup(parameters: dict):
    interval = parameters.get("interval", "daily")
    source = parameters.get("source", os.path.expanduser("~"))
    meta = _load_metadata()
    schedule = {
        "interval": interval,
        "source": source,
        "created": datetime.now().isoformat()
    }
    meta["schedules"].append(schedule)
    _save_metadata(meta)
    return f"Backup schedule set: {interval} for {source}"


def _backup_status():
    meta = _load_metadata()
    if not meta["backups"]:
        return "No backups have been created yet."
    last = meta["backups"][-1]
    lines = [
        "Last Backup Status:",
        f"  Name: {last['name']}",
        f"  Type: {last['type']}",
        f"  Timestamp: {last['timestamp']}",
        f"  Source: {last['source']}",
        f"  Files backed up: {last.get('copied_count', 0)}",
        f"  Total files in source: {last.get('total_files', 0)}",
        f"  Total backups: {len(meta['backups'])}"
    ]
    return "\n".join(lines)


def _diff_backups(parameters: dict):
    meta = _load_metadata()
    if len(meta["backups"]) < 2:
        return "Need at least 2 backups to diff."

    name1 = parameters.get("backup1", meta["backups"][-2]["name"])
    name2 = parameters.get("backup2", meta["backups"][-1]["name"])

    def _load_manifest(bname):
        mp = os.path.join(BACKUPS_DIR, bname, "manifest.json")
        if os.path.exists(mp):
            with open(mp, "r") as f:
                return json.load(f).get("files", {})
        return {}

    files1 = _load_manifest(name1)
    files2 = _load_manifest(name2)

    added = set(files2.keys()) - set(files1.keys())
    removed = set(files1.keys()) - set(files2.keys())
    modified = set()
    for f in set(files1.keys()) & set(files2.keys()):
        if files1[f].get("hash") != files2[f].get("hash"):
            modified.add(f)

    lines = [f"Diff between '{name1}' and '{name2}':"]
    if added:
        lines.append(f"  Added ({len(added)}):")
        for f in sorted(added):
            lines.append(f"    + {f}")
    if removed:
        lines.append(f"  Removed ({len(removed)}):")
        for f in sorted(removed):
            lines.append(f"    - {f}")
    if modified:
        lines.append(f"  Modified ({len(modified)}):")
        for f in sorted(modified):
            lines.append(f"    ~ {f}")
    if not added and not removed and not modified:
        lines.append("  No differences found.")
    return "\n".join(lines)
