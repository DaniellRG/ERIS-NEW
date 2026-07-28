import os
import json
import subprocess
import threading
import time
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
LOG_FILE = os.path.join(DATA_DIR, "ransomware_log.json")

_monitoring = False
_monitor_thread = None
_watch_dirs = [
    os.path.expanduser("~\\Documents"),
    os.path.expanduser("~\\Desktop"),
    os.path.expanduser("~\\Pictures"),
    os.path.expanduser("~\\Downloads"),
]


def _load_log():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            return json.load(f)
    return {
        "events": [],
        "quarantined": [],
        "whitelist": [],
        "monitoring": False,
        "stats": {"files_renamed": 0, "files_modified": 0, "alerts": 0}
    }


def _save_log(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(LOG_FILE, "w") as f:
        json.dump(data, f, indent=2)


def _record_event(event_type, details, severity="medium"):
    data = _load_log()
    event = {
        "type": event_type,
        "details": details,
        "severity": severity,
        "timestamp": datetime.now().isoformat()
    }
    data["events"].append(event)
    data["stats"]["alerts"] = data["stats"].get("alerts", 0) + 1
    if len(data["events"]) > 500:
        data["events"] = data["events"][-500:]
    _save_log(data)


def _run_ps(command):
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        capture_output=True, text=True, timeout=30
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def ransomware_shield(parameters: dict, player=None) -> str:
    action = parameters.get("action", "status").lower()

    if action == "status":
        return _protection_status()
    elif action == "scan":
        return _scan_system()
    elif action == "monitor":
        return _start_monitor(parameters)
    elif action == "stop":
        return _stop_monitor()
    elif action == "quarantine":
        return _quarantine(parameters)
    elif action == "log":
        return _detection_log(parameters)
    elif action == "whitelist":
        return _manage_whitelist(parameters)
    else:
        return f"Unknown action: {action}. Valid: status, scan, monitor, stop, quarantine, log, whitelist"


def _protection_status():
    data = _load_log()
    lines = [
        f"Ransomware Shield Status:",
        f"  Monitoring: {_monitoring}",
        f"  Total alerts: {data['stats'].get('alerts', 0)}",
        f"  Files renamed: {data['stats'].get('files_renamed', 0)}",
        f"  Files modified: {data['stats'].get('files_modified', 0)}",
        f"  Quarantined processes: {len(data.get('quarantined', []))}",
        f"  Whitelisted: {len(data.get('whitelist', []))}",
        f"  Watch directories: {len(_watch_dirs)}",
    ]
    last_event = data["events"][-1] if data["events"] else None
    if last_event:
        lines.append(f"  Last event: [{last_event['severity']}] {last_event['type']} at {last_event['timestamp']}")
    return "\n".join(lines)


def _scan_system():
    findings = []

    ps_cmd = (
        "Get-WmiObject Win32_Process | "
        "Select-Object ProcessId, Name, CommandLine, CreationDate | "
        "ConvertTo-Json -Compress"
    )
    out, err, rc = _run_ps(ps_cmd)
    if rc == 0 and out:
        try:
            procs = json.loads(out)
            if isinstance(procs, dict):
                procs = [procs]

            sus_keywords = [
                "vssadmin delete shadows", "bcdedit /set",
                "wmic shadowcopy delete", "cipher /w",
                "icacls", "attrib -h -r -s",
                "del /f /q", "cipher /s:"
            ]

            for p in procs:
                cmdline = (p.get("CommandLine") or "").lower()
                name = (p.get("Name") or "").lower()
                for kw in sus_keywords:
                    if kw in cmdline:
                        findings.append(
                            f"SUSPICIOUS PROCESS: {p.get('Name')} (PID: {p.get('ProcessId')}) "
                            f"CMD: {cmdline[:100]}"
                        )
                        _record_event("suspicious_process",
                            f"{p.get('Name')} PID:{p.get('ProcessId')} - {kw}",
                            "high")
                        break
                ransom_exts = [".encrypted", ".locked", ".crypto", ".crypt", ".enc"]
                for ext in ransom_exts:
                    if ext in name:
                        findings.append(f"RANSOMWARE-LIKE PROCESS: {p.get('Name')} (PID: {p.get('ProcessId')})")
                        _record_event("ransomware_process",
                            f"{p.get('Name')} PID:{p.get('ProcessId')}", "critical")
        except json.JSONDecodeError:
            pass

    ps_shadow = "vssadmin list shadows 2>&1"
    out2, err2, rc2 = _run_ps(ps_shadow)
    if "deleted" in (out2 + err2).lower():
        findings.append("WARNING: Volume Shadow Copies may have been deleted!")
        _record_event("shadow_delete", "Shadow copies deleted", "critical")

    ps_ransom = (
        "Get-ChildItem -Path $env:USERPROFILE -Recurse -Include "
        "*.encrypted,*.locked,*.crypto,*.crypt,*.enc -ErrorAction SilentlyContinue | "
        "Select-Object FullName, LastWriteTime | "
        "ConvertTo-Json -Compress"
    )
    out3, err3, rc3 = _run_ps(ps_ransom)
    if rc3 == 0 and out3:
        try:
            rfiles = json.loads(out3)
            if isinstance(rfiles, dict):
                rfiles = [rfiles]
            if rfiles:
                findings.append(f"RANSOMWARE-ENCRYPTED FILES FOUND ({len(rfiles)}):")
                for rf in rfiles[:10]:
                    findings.append(f"  - {rf.get('FullName')} ({rf.get('LastWriteTime')})")
                _record_event("encrypted_files", f"{len(rfiles)} encrypted files found", "critical")
        except json.JSONDecodeError:
            pass

    if findings:
        return f"SCAN RESULTS - {len(findings)} issue(s):\n" + "\n".join(findings)
    return "Scan complete. No ransomware indicators detected."


def _start_monitor(parameters: dict):
    global _monitoring, _monitor_thread
    if _monitoring:
        return "Monitor is already running."

    _monitoring = True
    interval = parameters.get("interval", 30)

    def _monitor_loop():
        file_snapshots = {}
        while _monitoring:
            for watch_dir in _watch_dirs:
                if not os.path.exists(watch_dir):
                    continue
                try:
                    current_files = {}
                    for root, dirs, files in os.walk(watch_dir):
                        for f in files:
                            fp = os.path.join(root, f)
                            try:
                                stat = os.stat(fp)
                                current_files[fp] = {
                                    "mtime": stat.st_mtime,
                                    "size": stat.st_size
                                }
                            except OSError:
                                pass

                    prev = file_snapshots.get(watch_dir, {})
                    renames = 0
                    modifications = 0

                    for fp, info in current_files.items():
                        if fp in prev:
                            if info["mtime"] != prev[fp]["mtime"]:
                                modifications += 1
                        else:
                            ext = os.path.splitext(fp)[1].lower()
                            if ext in [".encrypted", ".locked", ".crypto", ".crypt", ".enc"]:
                                _record_event("new_encrypted_file", fp, "critical")

                    data = _load_log()
                    data["stats"]["files_renamed"] = data["stats"].get("files_renamed", 0) + renames
                    data["stats"]["files_modified"] = data["stats"].get("files_modified", 0) + modifications
                    _save_log(data)

                    file_snapshots[watch_dir] = current_files
                except Exception:
                    pass
            time.sleep(interval)

    _monitor_thread = threading.Thread(target=_monitor_loop, daemon=True)
    _monitor_thread.start()

    data = _load_log()
    data["monitoring"] = True
    _save_log(data)

    return (
        f"Ransomware monitoring started (interval: {interval}s).\n"
        f"Watching {len(_watch_dirs)} directories."
    )


def _stop_monitor():
    global _monitoring
    _monitoring = False
    data = _load_log()
    data["monitoring"] = False
    _save_log(data)
    return "Ransomware monitoring stopped."


def _quarantine(parameters: dict):
    pid = parameters.get("pid", "")
    if not pid:
        return "'pid' parameter required."

    ps_cmd = (
        f"Stop-Process -Id {pid} -Force -ErrorAction SilentlyContinue; "
        f"if ($?) {{ 'killed' }} else {{ 'failed' }}"
    )
    out, err, rc = _run_ps(ps_cmd)

    data = _load_log()
    data["quarantined"].append({
        "pid": pid,
        "timestamp": datetime.now().isoformat(),
        "result": out
    })
    _save_log(data)

    if "killed" in out:
        _record_event("quarantine", f"Process {pid} terminated", "high")
        return f"Process {pid} terminated and quarantined."
    return f"Failed to terminate process {pid}. Error: {err}"


def _detection_log(parameters: dict):
    data = _load_log()
    events = data.get("events", [])
    limit = parameters.get("limit", 20)
    if not events:
        return "No ransomware events detected."

    recent = events[-limit:]
    lines = [f"Detection Log ({len(recent)} of {len(events)}):"]
    for e in reversed(recent):
        lines.append(f"  [{e['severity'].upper()}] {e['timestamp']} - {e['type']}: {e['details']}")
    return "\n".join(lines)


def _manage_whitelist(parameters: dict):
    sub_action = parameters.get("sub_action", "list")
    data = _load_log()

    if sub_action == "add":
        process = parameters.get("process", "")
        if not process:
            return "'process' parameter required."
        data["whitelist"].append({
            "process": process,
            "added": datetime.now().isoformat()
        })
        _save_log(data)
        return f"Whitelisted: {process}"

    elif sub_action == "remove":
        process = parameters.get("process", "")
        data["whitelist"] = [w for w in data["whitelist"] if w.get("process") != process]
        _save_log(data)
        return f"Removed from whitelist: {process}"

    elif sub_action == "list":
        wl = data.get("whitelist", [])
        if not wl:
            return "Whitelist is empty."
        lines = [f"Whitelist ({len(wl)}):"]
        for w in wl:
            lines.append(f"  - {w['process']} (added: {w.get('added', 'N/A')})")
        return "\n".join(lines)

    return "Unknown sub_action. Use: add, remove, list"
