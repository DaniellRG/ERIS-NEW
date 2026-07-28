import subprocess
import json
import os
import shutil
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
BACKUP_DIR = os.path.join(DATA_DIR, "driver_backups")


def _run_ps(command):
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        capture_output=True, text=True, timeout=120
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def driver_manager(parameters: dict, player=None) -> str:
    action = parameters.get("action", "list").lower()

    if action == "list":
        return _list_drivers()
    elif action == "update":
        return _check_updates()
    elif action == "backup":
        return _backup_drivers(parameters)
    elif action == "restore":
        return _restore_drivers(parameters)
    elif action == "info":
        return _driver_info(parameters)
    elif action == "scan":
        return _scan_hardware()
    else:
        return f"Unknown action: {action}. Valid: list, update, backup, restore, info, scan"


def _list_drivers():
    ps = (
        "Get-WmiObject Win32_PnPSignedDriver | "
        "Select-Object DeviceName, DriverVersion, DriverDate, Manufacturer, InfName | "
        "ConvertTo-Json -Compress"
    )
    out, err, rc = _run_ps(ps)
    if rc != 0:
        return f"Error listing drivers: {err}"
    try:
        drivers = json.loads(out)
        if isinstance(drivers, dict):
            drivers = [drivers]
        lines = [f"Installed Drivers ({len(drivers)}):"]
        for d in drivers:
            name = d.get("DeviceName", "Unknown")
            ver = d.get("DriverVersion", "N/A")
            mfr = d.get("Manufacturer", "N/A")
            lines.append(f"  - {name} | v{ver} | {mfr}")
        return "\n".join(lines)
    except json.JSONDecodeError:
        return f"Raw output:\n{out}"


def _check_updates():
    ps = (
        "Get-WmiObject Win32_PnPSignedDriver | "
        "Select-Object DeviceName, DriverVersion, DriverDate | "
        "ConvertTo-Json -Compress"
    )
    out, err, rc = _run_ps(ps)
    if rc != 0:
        return f"Error: {err}"
    try:
        drivers = json.loads(out)
        if isinstance(drivers, dict):
            drivers = [drivers]
        old = []
        for d in drivers:
            date_str = d.get("DriverDate", "")
            if date_str:
                try:
                    dt = datetime.strptime(date_str[:8], "%Y%m%d")
                    if dt.year < 2023:
                        old.append(d)
                except (ValueError, TypeError):
                    pass
        if old:
            lines = [f"Potentially outdated drivers ({len(old)}):"]
            for d in old:
                lines.append(f"  - {d.get('DeviceName')} | Date: {d.get('DriverDate')} | Ver: {d.get('DriverVersion')}")
            return "\n".join(lines)
        return "All drivers appear current. Run 'update' action via Windows Update for definitive check."
    except json.JSONDecodeError:
        return f"Raw: {out}"


def _backup_drivers(parameters: dict):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = os.path.join(BACKUP_DIR, f"backup_{timestamp}")
    os.makedirs(dest, exist_ok=True)

    method = parameters.get("method", "export")
    if method == "dism":
        ps = f'Export-WindowsDriver -Destination "{dest}" -Online'
        out, err, rc = _run_ps(ps)
        if rc != 0:
            return f"DISM export error: {err}"
        return f"Drivers exported to: {dest}"
    else:
        ps = (
            "Get-WmiObject Win32_PnPSignedDriver | "
            "Select-Object DeviceName, DriverVersion, DriverDate, Manufacturer, InfName, DriverFileName | "
            "ConvertTo-Json -Compress"
        )
        out, err, rc = _run_ps(ps)
        manifest_path = os.path.join(dest, "driver_manifest.json")
        with open(manifest_path, "w") as f:
            f.write(out)
        meta_path = os.path.join(dest, "backup_info.json")
        meta = {
            "timestamp": timestamp,
            "method": method,
            "source": "WMI Driver Export",
            "backup_dir": dest
        }
        with open(meta_path, "w") as f:
            json.dump(meta, f, indent=2)
        return f"Driver manifest backed up to: {dest}"


def _restore_drivers(parameters: dict):
    backup_name = parameters.get("backup_name", "")
    if not backup_name:
        if not os.path.exists(BACKUP_DIR):
            return "No backups found."
        backups = sorted(os.listdir(BACKUP_DIR), reverse=True)
        if not backups:
            return "No backups found."
        backup_name = backups[0]

    src = os.path.join(BACKUP_DIR, backup_name)
    if not os.path.exists(src):
        return f"Backup not found: {backup_name}"

    manifest = os.path.join(src, "driver_manifest.json")
    if os.path.exists(manifest):
        ps = f'pnputil /add-driver "{src}\\*.inf" /subdirs /install'
        out, err, rc = _run_ps(ps)
        if rc != 0:
            return f"Restore error: {err}"
        return f"Drivers restored from backup: {backup_name}\n{out}"

    export_dir = os.path.join(src, "Drivers")
    if os.path.exists(export_dir):
        ps = f'pnputil /add-driver "{export_dir}\\*.inf" /subdirs /install'
        out, err, rc = _run_ps(ps)
        if rc != 0:
            return f"Restore error: {err}"
        return f"Drivers restored from: {backup_name}\n{out}"

    return f"Backup format not recognized: {backup_name}"


def _driver_info(parameters: dict):
    device = parameters.get("device", "")
    ps = "Get-WmiObject Win32_PnPSignedDriver | ConvertTo-Json -Compress"
    out, err, rc = _run_ps(ps)
    if rc != 0:
        return f"Error: {err}"
    try:
        drivers = json.loads(out)
        if isinstance(drivers, dict):
            drivers = [drivers]
        if device:
            found = [d for d in drivers if device.lower() in (d.get("DeviceName", "")).lower()]
            if not found:
                return f"No driver found matching: {device}"
            d = found[0]
            lines = [f"Driver Info: {d.get('DeviceName')}"]
            for k, v in d.items():
                if v:
                    lines.append(f"  {k}: {v}")
            return "\n".join(lines)
        return f"Total drivers: {len(drivers)}. Specify 'device' parameter to search."
    except json.JSONDecodeError:
        return f"Raw: {out}"


def _scan_hardware():
    ps = (
        "Get-WmiObject Win32_PnPEntity | "
        "Where-Object { $_.Status -ne 'OK' } | "
        "Select-Object Name, Status, PNPDeviceID | "
        "ConvertTo-Json -Compress"
    )
    out, err, rc = _run_ps(ps)
    if rc != 0:
        return f"Scan error: {err}"
    try:
        issues = json.loads(out)
        if isinstance(issues, dict):
            issues = [issues]
        if not issues:
            return "All hardware devices are functioning normally."
        lines = [f"Hardware issues found ({len(issues)}):"]
        for d in issues:
            lines.append(f"  - {d.get('Name')} | Status: {d.get('Status')} | ID: {d.get('PNPDeviceID')}")
        return "\n".join(lines)
    except json.JSONDecodeError:
        return f"Raw: {out}"
