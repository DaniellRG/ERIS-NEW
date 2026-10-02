#!/usr/bin/env python3
"""file_system wrapper — gestión de sistema de archivos para Linux"""
import shutil
from pathlib import Path

TOOL_NAME = "file_system"

ACTIONS_AVAILABLE = ["list", "info", "copy", "move", "delete", "disk_usage", "find", "status"]

def tool_handler(params=None):
    """Handler para file_system."""
    if params is None:
        params = {}

    action = params.get("action", "status")

    if action == "status":
        return f"file_system: {', '.join(ACTIONS_AVAILABLE)}"
    elif action == "list":
        path = params.get("path", ".")
        p = Path(path)
        if not p.exists():
            return f"Error: Path does not exist: {path}"
        if p.is_dir():
            items = list(p.iterdir())
            dirs = [x.name for x in items if x.is_dir()]
            files = [x.name for x in items if x.is_file()]
            return f"Directorio: {path} | {len(dirs)} dirs, {len(files)} files\nDirs: {dirs[:10]}\nFiles: {files[:10]}"
        else:
            return f"Archivo: {path} | {p.stat().st_size} bytes"
    elif action == "info":
        path = params.get("path", ".")
        p = Path(path)
        if p.exists():
            stat = p.stat()
            return f"Path: {path} | Exists: True | Size: {stat.st_size} bytes | Modified: {stat.st_mtime}"
        else:
            return f"Path: {path} | Exists: False"
    elif action == "copy":
        src = params.get("src", "")
        dst = params.get("dst", "")
        shutil.copy2(src, dst)
        return f"Copied: {src} → {dst}"
    elif action == "move":
        src = params.get("src", "")
        dst = params.get("dst", "")
        shutil.move(str(src), str(dst))
        return f"Moved: {src} → {dst}"
    elif action == "delete":
        path = params.get("path", "")
        p = Path(path)
        if p.is_file():
            p.unlink()
        elif p.is_dir():
            shutil.rmtree(str(p))
        return f"Deleted: {path}"
    elif action == "disk_usage":
        path = params.get("path", ".")
        usage = shutil.disk_usage(str(path))
        return f"Disk: {path} | Total: {usage.total/(1024**3):.1f}GB | Used: {usage.used/(1024**3):.1f}GB | Free: {usage.free/(1024**3):.1f}GB"
    elif action == "find":
        path = params.get("path", ".")
        pattern = params.get("pattern", "*")
        p = Path(path)
        matches = list(p.rglob(pattern))
        return f"Found {len(matches)} files matching '{pattern}' in {path}"[:500]
    else:
        return f"Error: Unknown action '{action}'. Available: {', '.join(ACTIONS_AVAILABLE)}"

def get_declarations():
    return {
        "file_system": "Gestión de sistema de archivos — list, info, copy, move, delete, disk_usage, find",
    }

if __name__ == "__main__":
    import sys
    action = sys.argv[1] if len(sys.argv) > 1 else "status"
    print(tool_handler({"action": action}))
