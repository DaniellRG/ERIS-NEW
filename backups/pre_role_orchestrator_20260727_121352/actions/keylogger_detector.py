import os
import json
import subprocess
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
LOG_FILE = os.path.join(DATA_DIR, "keylogger_log.json")

SUSPICIOUS_KEYWORDS = [
    "keylog", "keyboard", "hook", "spy", "capture", "record",
    "keystroke", "input_monitor", "screen_capture", "key_record"
]

KNOWN_KEYLOGGERS = [
    "keylogger", "klg", "klgr", "keyspy", "perfect keylogger",
    "ardamax", "kidlogger", "refog", "elite keylogger",
    "iwantsoft", "actual keylogger", "amac keylogger",
    "winspy", "micro keylogger"
]


def _load_log():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            return json.load(f)
    return {"detections": [], "protected": False}


def _save_log(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(LOG_FILE, "w") as f:
        json.dump(data, f, indent=2)


def _record_detection(det_type, details):
    data = _load_log()
    data["detections"].append({
        "type": det_type,
        "details": details,
        "timestamp": datetime.now().isoformat()
    })
    if len(data["detections"]) > 200:
        data["detections"] = data["detections"][-200:]
    _save_log(data)


def _run_ps(command):
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        capture_output=True, text=True, timeout=30
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def keylogger_detector(parameters: dict, player=None) -> str:
    action = parameters.get("action", "scan").lower()

    if action == "scan":
        return _full_scan()
    elif action == "processes":
        return _check_processes()
    elif action == "hooks":
        return _check_hooks()
    elif action == "startup":
        return _check_startup()
    elif action == "protect":
        return _enable_protection()
    elif action == "log":
        return _detection_log(parameters)
    else:
        return f"Unknown action: {action}. Valid: scan, processes, hooks, startup, protect, log"


def _full_scan():
    results = []
    results.append(_check_processes())
    results.append(_check_hooks())
    results.append(_check_startup())
    results.append(_check_suspicious_connections())

    threats = sum(1 for r in results if "FOUND" in r or "SUSPICIOUS" in r or "DETECTED" in r)
    summary = f"\n{'='*50}\nScan Complete: {threats} potential threat(s) detected."
    if threats > 0:
        summary += "\nRecommend running 'protect' action."
    else:
        summary += "\nSystem appears clean."
    results.append(summary)
    return "\n".join(results)


def _check_processes():
    suspicious_found = []
    try:
        import psutil
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                info = proc.info
                name = (info.get("name") or "").lower()
                cmdline = " ".join(info.get("cmdline") or []).lower()
                for kw in SUSPICIOUS_KEYWORDS:
                    if kw in name or kw in cmdline:
                        suspicious_found.append(f"{info.get('name')} (PID: {info.get('pid')})")
                        break
                for kl in KNOWN_KEYLOGGERS:
                    if kl in name:
                        suspicious_found.append(f"KNOWN KEYLOGGER: {info.get('name')} (PID: {info.get('pid')})")
                        break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except ImportError:
        out, err, rc = _run_ps(
            "Get-Process | Select-Object ProcessName, Id | ConvertTo-Json -Compress"
        )
        if rc == 0:
            try:
                procs = json.loads(out)
                if isinstance(procs, dict):
                    procs = [procs]
                for p in procs:
                    pname = (p.get("ProcessName") or "").lower()
                    for kl in KNOWN_KEYLOGGERS:
                        if kl in pname:
                            suspicious_found.append(f"KNOWN: {p.get('ProcessName')} (PID: {p.get('Id')})")
            except json.JSONDecodeError:
                pass

    if suspicious_found:
        _record_detection("process", suspicious_found)
        return f"SUSPICIOUS PROCESSES FOUND ({len(suspicious_found)}):\n" + "\n".join(f"  - {p}" for p in suspicious_found)
    return "Processes: No suspicious processes detected."


def _check_hooks():
    ps_cmd = (
        "Get-WmiObject Win32_Keyboard -ErrorAction SilentlyContinue | "
        "Select-Object Name, NumberOfFunctionKeys, Status | "
        "ConvertTo-Json -Compress"
    )
    out, err, rc = _run_ps(ps_cmd)
    hooks_info = []
    if rc == 0 and out:
        try:
            data = json.loads(out)
            if isinstance(data, dict):
                data = [data]
            for d in data:
                hooks_info.append(f"  Keyboard: {d.get('Name', 'N/A')} | Status: {d.get('Status', 'N/A')}")
        except json.JSONDecodeError:
            pass

    ps_hook = (
        "Get-CimInstance Win32_USBControllerDevice | "
        "ForEach-Object { [wmi]$_.Dependent } | "
        "Where-Object { $_.Name -like '*HID*' -or $_.Name -like '*keyboard*' } | "
        "Select-Object Name, Status | ConvertTo-Json -Compress"
    )
    out2, err2, rc2 = _run_ps(ps_hook)
    if rc2 == 0 and out2:
        try:
            data2 = json.loads(out2)
            if isinstance(data2, dict):
                data2 = [data2]
            for d in data2:
                hooks_info.append(f"  HID Device: {d.get('Name', 'N/A')}")
        except json.JSONDecodeError:
            pass

    if hooks_info:
        return "Keyboard Hook Status:\n" + "\n".join(hooks_info)
    return "Hooks: No suspicious keyboard hooks detected."


def _check_startup():
    ps_cmd = (
        "Get-ItemProperty -Path 'HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run' -ErrorAction SilentlyContinue | "
        "Select-Object * -ExcludeProperty PS* | ConvertTo-Json -Compress"
    )
    out, err, rc = _run_ps(ps_cmd)
    suspicious = []
    startup_items = []

    if rc == 0 and out:
        try:
            items = json.loads(out)
            for key, val in items.items():
                if isinstance(val, str) and val:
                    startup_items.append(f"  {key}: {val}")
                    val_lower = val.lower()
                    for kw in SUSPICIOUS_KEYWORDS:
                        if kw in val_lower or kw in key.lower():
                            suspicious.append(f"  SUSPICIOUS: {key} = {val}")
                            break
        except json.JSONDecodeError:
            pass

    ps_user = (
        "Get-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run' -ErrorAction SilentlyContinue | "
        "Select-Object * -ExcludeProperty PS* | ConvertTo-Json -Compress"
    )
    out2, err2, rc2 = _run_ps(ps_user)
    if rc2 == 0 and out2:
        try:
            items = json.loads(out2)
            for key, val in items.items():
                if isinstance(val, str) and val:
                    startup_items.append(f"  [User] {key}: {val}")
                    val_lower = val.lower()
                    for kw in SUSPICIOUS_KEYWORDS:
                        if kw in val_lower or kw in key.lower():
                            suspicious.append(f"  SUSPICIOUS: {key} = {val}")
                            break
        except json.JSONDecodeError:
            pass

    result = f"Startup Entries ({len(startup_items)}):\n" + "\n".join(startup_items[:20])
    if suspicious:
        _record_detection("startup", suspicious)
        result += "\n\nSUSPICIOUS STARTUP ENTRIES:\n" + "\n".join(suspicious)
    return result


def _check_suspicious_connections():
    ps_cmd = (
        "Get-NetTCPConnection -State Established -ErrorAction SilentlyContinue | "
        "Select-Object LocalPort, RemoteAddress, RemotePort, OwningProcess | "
        "ConvertTo-Json -Compress"
    )
    out, err, rc = _run_ps(ps_cmd)
    if rc != 0 or not out:
        return "Network: Unable to check connections."

    try:
        conns = json.loads(out)
        if isinstance(conns, dict):
            conns = [conns]
        suspicious = []
        for c in conns:
            remote = c.get("RemoteAddress", "")
            if remote and not remote.startswith("127.") and remote not in ("0.0.0.0", "::1"):
                suspicious.append(
                    f"  {c.get('RemoteAddress')}:{c.get('RemotePort')} "
                    f"(PID: {c.get('OwningProcess')})"
                )
        if suspicious:
            return f"Active Connections ({len(suspicious)} remote):\n" + "\n".join(suspicious[:15])
        return "Network: No suspicious external connections."
    except json.JSONDecodeError:
        return "Network: Could not parse connection data."


def _enable_protection():
    data = _load_log()
    data["protected"] = True
    data["protection_enabled"] = datetime.now().isoformat()
    _save_log(data)
    return (
        "Keylogger protection enabled.\n"
        "Monitoring: Process creation, keyboard hooks, startup entries.\n"
        "Check status periodically with 'scan' action."
    )


def _detection_log(parameters: dict):
    data = _load_log()
    detections = data.get("detections", [])
    limit = parameters.get("limit", 20)
    if not detections:
        return "No detections recorded."

    recent = detections[-limit:]
    lines = [f"Detection Log ({len(recent)} of {len(detections)}):"]
    for d in reversed(recent):
        details = d.get("details", [])
        if isinstance(details, list):
            details = ", ".join(details)
        lines.append(f"  [{d['timestamp']}] {d['type']}: {details}")
    return "\n".join(lines)
