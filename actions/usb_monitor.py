import os
import json
import subprocess
import hashlib
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
HISTORY_FILE = os.path.join(DATA_DIR, "usb_history.json")


def _load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return {"devices": [], "known_devices": [], "alerts": [], "blocked": False}


def _save_history(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(HISTORY_FILE, "w") as f:
        json.dump(data, f, indent=2)


def _run_ps(command):
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        capture_output=True, text=True, timeout=30
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def usb_monitor(parameters: dict, player=None) -> str:
    action = parameters.get("action", "list").lower()

    if action == "list":
        return _list_usb_devices()
    elif action == "history":
        return _device_history(parameters)
    elif action == "alert":
        return _set_alert(parameters)
    elif action == "block":
        return _block_usb(True)
    elif action == "unblock":
        return _block_usb(False)
    elif action == "scan":
        return _scan_suspicious()
    else:
        return f"Unknown action: {action}. Valid: list, history, alert, block, unblock, scan"


def _list_usb_devices():
    ps_cmd = (
        "Get-CimInstance Win32_USBControllerDevice | "
        "ForEach-Object { [wmi]$_.Dependent } | "
        "Select-Object Name, DeviceID, Description, Manufacturer, Status, "
        "PNPDeviceID, Service | ConvertTo-Json -Compress"
    )
    out, err, rc = _run_ps(ps_cmd)
    if rc != 0:
        return f"Error listing USB devices: {err}"

    try:
        devices = json.loads(out)
        if isinstance(devices, dict):
            devices = [devices]

        data = _load_history()
        current_ids = set()

        for d in devices:
            dev_id = d.get("DeviceID", "")
            current_ids.add(dev_id)
            known = [k for k in data["known_devices"] if k.get("device_id") == dev_id]
            if not known:
                data["known_devices"].append({
                    "device_id": dev_id,
                    "name": d.get("Name", "Unknown"),
                    "manufacturer": d.get("Manufacturer", "Unknown"),
                    "first_seen": datetime.now().isoformat()
                })

        _save_history(data)

        lines = [f"USB Devices ({len(devices)}):"]
        for d in devices:
            status = d.get("Status", "Unknown")
            name = d.get("Name", "Unknown")
            mfr = d.get("Manufacturer", "Unknown")
            did = d.get("DeviceID", "")
            lines.append(f"  - {name} | {mfr} | Status: {status} | ID: {did}")
        return "\n".join(lines)
    except json.JSONDecodeError:
        return f"Raw output:\n{out}"


def _device_history(parameters: dict):
    data = _load_history()
    devices = data.get("known_devices", [])
    if not devices:
        return "No device history recorded."

    limit = parameters.get("limit", 30)
    recent = devices[-limit:]
    lines = [f"Known USB Devices ({len(recent)} of {len(devices)}):"]
    for d in recent:
        lines.append(
            f"  - {d.get('name', 'Unknown')} | "
            f"{d.get('manufacturer', 'Unknown')} | "
            f"First seen: {d.get('first_seen', 'N/A')}"
        )
    return "\n".join(lines)


def _set_alert(parameters: dict):
    data = _load_history()
    alert_config = {
        "enabled": parameters.get("enabled", True),
        "notify_new": parameters.get("notify_new", True),
        "notify_unknown": parameters.get("notify_unknown", True),
        "created": datetime.now().isoformat()
    }
    data["alerts"].append(alert_config)
    _save_history(data)
    return (
        f"USB alerts enabled: new devices={alert_config['notify_new']}, "
        f"unknown devices={alert_config['notify_unknown']}"
    )


def _block_usb(block):
    if block:
        ps_cmd = (
            'New-ItemProperty -Path "HKLM:\\SYSTEM\\CurrentControlSet\\Services\\USBSTOR" '
            '-Name "Start" -Value 4 -PropertyType DWORD -Force'
        )
        action_text = "blocked"
    else:
        ps_cmd = (
            'New-ItemProperty -Path "HKLM:\\SYSTEM\\CurrentControlSet\\Services\\USBSTOR" '
            '-Name "Start" -Value 3 -PropertyType DWORD -Force'
        )
        action_text = "unblocked"

    out, err, rc = _run_ps(ps_cmd)
    data = _load_history()
    data["blocked"] = block
    _save_history(data)

    if rc == 0:
        return f"USB ports {action_text}. Requires admin privileges to take effect."
    return f"Error {action_text} USB: {err}. Run as administrator."


def _scan_suspicious():
    ps_cmd = (
        "Get-CimInstance Win32_USBControllerDevice | "
        "ForEach-Object { [wmi]$_.Dependent } | "
        "Select-Object Name, DeviceID, Description, PNPDeviceID, "
        "Service, Status | ConvertTo-Json -Compress"
    )
    out, err, rc = _run_ps(ps_cmd)
    if rc != 0:
        return f"Scan error: {err}"

    try:
        devices = json.loads(out)
        if isinstance(devices, dict):
            devices = [devices]

        data = _load_history()
        known_ids = {k.get("device_id") for k in data.get("known_devices", [])}
        suspicious = []

        for d in devices:
            dev_id = d.get("DeviceID", "")
            name = d.get("Name", "")
            service = d.get("Service", "")

            if dev_id not in known_ids:
                suspicious.append(f"  UNKNOWN: {name} (Service: {service}) | {dev_id}")

            sus_keywords = ["usbguard", "mass storage", "generic"]
            if any(kw in (service or "").lower() for kw in sus_keywords):
                if dev_id not in known_ids:
                    suspicious.append(f"  FLAGGED: {name} has suspicious service: {service}")

        if suspicious:
            return f"SUSPICIOUS DEVICES ({len(suspicious)}):\n" + "\n".join(suspicious)
        return f"Scan complete. {len(devices)} devices checked. All appear known."
    except json.JSONDecodeError:
        return f"Parse error. Raw: {out}"
