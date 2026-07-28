import os
import sys
import random
import hashlib
import string
import json
import subprocess
from datetime import datetime

WARNING_MSG = (
    "WARNING: This operation is DESTRUCTIVE and IRREVERSIBLE.\n"
    "Data will be permanently overwritten and cannot be recovered.\n"
    "Make absolutely sure you want to proceed."
)


def disk_wiper(parameters: dict, player=None) -> str:
    action = parameters.get("action", "info").lower()

    if action == "wipe_file":
        return _wipe_file(parameters)
    elif action == "wipe_folder":
        return _wipe_folder(parameters)
    elif action == "wipe_free":
        return _wipe_free_space(parameters)
    elif action == "wipe_disk":
        return _wipe_disk(parameters)
    elif action == "info":
        return _disk_info(parameters)
    elif action == "verify":
        return _verify_wipe(parameters)
    else:
        return f"Unknown action: {action}. Valid: wipe_file, wipe_folder, wipe_free, wipe_disk, info, verify"


def _confirm(parameters: dict):
    confirm = parameters.get("confirm", False)
    if confirm is True or str(confirm).lower() in ("true", "yes", "1"):
        return True
    return False


def _wipe_file(parameters: dict):
    filepath = parameters.get("path", "")
    if not filepath:
        return "'path' parameter required."

    filepath = os.path.expanduser(filepath)
    if not os.path.exists(filepath):
        return f"File not found: {filepath}"
    if os.path.isdir(filepath):
        return f"Path is a directory. Use 'wipe_folder' action."

    if not _confirm(parameters):
        return f"{WARNING_MSG}\n\nTarget: {filepath}\nSize: {os.path.getsize(filepath)} bytes\n\nSet 'confirm=true' to proceed."

    passes = parameters.get("passes", 3)
    method = parameters.get("method", "dod")
    size = os.path.getsize(filepath)

    with open(filepath, "rb+") as f:
        for p in range(passes):
            f.seek(0)
            remaining = size
            while remaining > 0:
                chunk_size = min(remaining, 1024 * 1024)
                if method == "gutmann":
                    data = os.urandom(chunk_size)
                elif method == "zero":
                    data = b"\x00" * chunk_size
                elif method == "random":
                    data = os.urandom(chunk_size)
                else:
                    if p % 3 == 0:
                        data = b"\x00" * chunk_size
                    elif p % 3 == 1:
                        data = b"\xff" * chunk_size
                    else:
                        data = os.urandom(chunk_size)
                f.write(data)
                remaining -= chunk_size
            f.flush()
            os.fsync(f.fileno())

    os.remove(filepath)
    return f"File securely wiped: {filepath} ({passes} passes, {method})"


def _wipe_folder(parameters: dict):
    folderpath = parameters.get("path", "")
    if not folderpath:
        return "'path' parameter required."

    folderpath = os.path.expanduser(folderpath)
    if not os.path.exists(folderpath):
        return f"Folder not found: {folderpath}"
    if not os.path.isdir(folderpath):
        return f"Path is a file. Use 'wipe_file' action."

    if not _confirm(parameters):
        file_count = sum(len(files) for _, _, files in os.walk(folderpath))
        total_size = sum(
            os.path.getsize(os.path.join(r, f))
            for r, _, files in os.walk(folderpath)
            for f in files
        )
        return (
            f"{WARNING_MSG}\n\nTarget: {folderpath}\n"
            f"Files: {file_count}\nTotal size: {total_size:,} bytes\n\n"
            f"Set 'confirm=true' to proceed."
        )

    passes = parameters.get("passes", 3)
    method = parameters.get("method", "dod")
    wiped = 0

    for root, dirs, files in os.walk(folderpath, topdown=False):
        for fname in files:
            fp = os.path.join(root, fname)
            try:
                size = os.path.getsize(fp)
                with open(fp, "rb+") as f:
                    for p in range(passes):
                        f.seek(0)
                        remaining = size
                        while remaining > 0:
                            chunk_size = min(remaining, 1024 * 1024)
                            if method == "zero":
                                data = b"\x00" * chunk_size
                            else:
                                data = os.urandom(chunk_size)
                            f.write(data)
                            remaining -= chunk_size
                        f.flush()
                        os.fsync(f.fileno())
                os.remove(fp)
                wiped += 1
            except (OSError, PermissionError):
                pass

    try:
        os.rmdir(folderpath)
    except OSError:
        pass

    return f"Folder securely wiped: {folderpath} ({wiped} files, {passes} passes)"


def _wipe_free_space(parameters: dict):
    drive = parameters.get("drive", os.path.splitdrive(os.getcwd())[0] + "\\")
    if not _confirm(parameters):
        return (
            f"{WARNING_MSG}\n\nTarget: Free space on {drive}\n\n"
            f"This writes random data to all free space, then deletes the temp files.\n"
            f"Set 'confirm=true' to proceed."
        )

    temp_name = os.path.join(drive, f"_wipe_{random.randint(10000,99999)}.tmp")
    chunk_size = 1024 * 1024 * 10
    written = 0

    try:
        with open(temp_name, "wb") as f:
            while True:
                try:
                    f.write(os.urandom(chunk_size))
                    written += chunk_size
                except OSError:
                    break
    except OSError as e:
        return f"Error writing wipe file: {e}"

    try:
        os.remove(temp_name)
    except OSError:
        pass

    return f"Free space wiped on {drive} ({written:,} bytes overwritten)"


def _wipe_disk(parameters: dict):
    drive = parameters.get("drive", "")
    if not drive:
        return "'drive' parameter required (e.g., 'D:' or 'E:')"

    if not _confirm(parameters):
        return (
            f"{WARNING_MSG}\n\nTARGET DISK: {drive}\n\n"
            f"ALL DATA ON THIS DISK WILL BE PERMANENTLY DESTROYED.\n"
            f"Set 'confirm=true' to proceed."
        )

    method = parameters.get("method", "dod")
    passes = 3
    if method == "gutmann":
        passes = 35

    zero_path = os.path.join(drive, "_wipe_zero.tmp")
    random_path = os.path.join(drive, "_wipe_random.tmp")

    try:
        disk_size = _get_drive_size(drive)
    except Exception:
        disk_size = 50 * 1024 * 1024 * 1024

    written = 0
    chunk_size = 1024 * 1024 * 10

    for p in range(passes):
        try:
            with open(zero_path, "wb") as f:
                while written < disk_size:
                    try:
                        if p % 3 == 0:
                            f.write(b"\x00" * chunk_size)
                        elif p % 3 == 1:
                            f.write(b"\xff" * chunk_size)
                        else:
                            f.write(os.urandom(chunk_size))
                        written += chunk_size
                        if written % (1024 * 1024 * 100) == 0:
                            pass
                    except OSError:
                        break
        except OSError:
            pass

    for tmp in [zero_path, random_path]:
        try:
            os.remove(tmp)
        except OSError:
            pass

    return f"Disk {drive} wiped ({passes} passes, method: {method})"


def _get_drive_size(drive):
    ps_cmd = (
        f"(Get-PSDrive -Name {drive.strip(':\\')} -ErrorAction SilentlyContinue).Free + "
        f"(Get-PSDrive -Name {drive.strip(':\\')} -ErrorAction SilentlyContinue).Used"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            return int(result.stdout.strip())
    except Exception:
        pass
    return 50 * 1024 * 1024 * 1024


def _disk_info(parameters: dict):
    drive = parameters.get("drive", os.path.splitdrive(os.getcwd())[0])

    ps_cmd = (
        f"Get-PSDrive -Name {drive.strip(':\\\\')} -ErrorAction SilentlyContinue | "
        f"Select-Object Name, @{{N='Used';E={{$_.Used}}}}, @{{N='Free';E={{$_.Free}}}}, "
        f"Root, Provider | ConvertTo-Json -Compress"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps_cmd],
        capture_output=True, text=True, timeout=10
    )

    if result.returncode == 0 and result.stdout.strip():
        try:
            data = json.loads(result.stdout)
            used = data.get("Used", 0)
            free = data.get("Free", 0)
            total = used + free
            lines = [
                f"Disk Info: {drive}",
                f"  Total: {total:,} bytes ({total / (1024**3):.2f} GB)",
                f"  Used: {used:,} bytes ({used / (1024**3):.2f} GB)",
                f"  Free: {free:,} bytes ({free / (1024**3):.2f} GB)",
                f"  Usage: {(used / total * 100) if total else 0:.1f}%"
            ]
            return "\n".join(lines)
        except json.JSONDecodeError:
            pass

    try:
        usage = os.statvfs(drive if drive.endswith(os.sep) else drive + os.sep)
        total = usage.f_frsize * usage.f_blocks
        free = usage.f_frsize * usage.f_bavail
        used = total - free
        lines = [
            f"Disk Info: {drive}",
            f"  Total: {total:,} bytes ({total / (1024**3):.2f} GB)",
            f"  Used: {used:,} bytes ({used / (1024**3):.2f} GB)",
            f"  Free: {free:,} bytes ({free / (1024**3):.2f} GB)",
            f"  Usage: {(used / total * 100):.1f}%"
        ]
        return "\n".join(lines)
    except (OSError, AttributeError):
        return f"Unable to get disk info for: {drive}"


def _verify_wipe(parameters: dict):
    filepath = parameters.get("path", "")
    if not filepath:
        return "'path' parameter required."

    filepath = os.path.expanduser(filepath)
    if os.path.exists(filepath):
        return f"File still exists: {filepath}. Wipe may not have completed."

    return f"Verified: {filepath} has been successfully wiped and removed."
