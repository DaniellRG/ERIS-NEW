# -*- coding: utf-8 -*-
"""
Eris Security Shield – Monitoreo de seguridad defensivo.
Detecta intrusiones, verifica fugas de datos, analiza actividad sospechosa,
y protege al usuario de amenazas.
"""
import os
import re
import json
import socket
import subprocess
from pathlib import Path
from datetime import datetime
from collections import Counter

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
ALERTS_FILE = DATA_DIR / "security_alerts.json"


def _run(cmd: str, timeout: int = 15) -> str:
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                           timeout=timeout, encoding="utf-8", errors="replace")
        return r.stdout.strip()
    except Exception:
        return ""


def _load_alerts() -> list:
    try:
        if ALERTS_FILE.exists():
            return json.loads(ALERTS_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return []


def _save_alerts(alerts: list):
    ALERTS_FILE.write_text(json.dumps(alerts[-200:], indent=2, ensure_ascii=False), encoding="utf-8")


def _add_alert(alert_type: str, severity: str, message: str):
    alerts = _load_alerts()
    alerts.append({
        "time": datetime.now().isoformat(),
        "type": alert_type,
        "severity": severity,
        "message": message,
    })
    _save_alerts(alerts)


# ═══════════════════════════════════════════════════════════════════
# SYSTEM INTRUSION DETECTION
# ═══════════════════════════════════════════════════════════════════

def _check_suspicious_processes() -> list:
    """Detect potentially malicious processes."""
    suspicious = []
    output = _run("tasklist /FO CSV /NH")
    known_suspicious = [
        "mimikatz", "procdump", "lazagne", "ncat", "netcat",
        "meterpreter", "cobalt", "beacon", "sliver",
        "psexec", "wce", "gsecdump", "dumpert",
        "sharpdump", "nanodump", "handlekatz",
        "rubeus", "kerberoast", "asreproast",
        "bloodhound", "sharphound", "sharpup",
        "certify", "certipy",
    ]
    for line in output.split("\n"):
        for sus in known_suspicious:
            if sus.lower() in line.lower():
                parts = line.split(",")
                suspicious.append({
                    "process": parts[0].strip('"') if parts else sus,
                    "pid": parts[1].strip('"') if len(parts) > 1 else "?",
                    "warning": f"Known pentesting tool detected: {sus}",
                    "severity": "HIGH",
                })
    return suspicious


def _check_network_connections() -> list:
    """Detect suspicious outbound connections."""
    suspicious = []
    output = _run("netstat -ano")
    suspicious_ports = {4444, 5555, 1234, 8080, 9001, 4433, 6667, 6697, 1337, 31337}
    suspicious_processes = ["nc", "ncat", "netcat", "socat", "plink", "rdesktop", "vnc"]

    current_pid = None
    for line in output.split("\n"):
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) >= 5:
            proto = parts[0]
            local = parts[1]
            remote = parts[2]
            state = parts[3]
            pid = parts[4]

            if state == "ESTABLISHED":
                # Check for suspicious remote ports
                try:
                    port = int(remote.split(":")[-1])
                    if port in suspicious_ports:
                        suspicious.append({
                            "type": "suspicious_port",
                            "remote": remote,
                            "port": port,
                            "pid": pid,
                            "severity": "MEDIUM",
                            "message": f"Outbound connection to suspicious port {port}",
                        })
                except ValueError:
                    pass

    return suspicious


def _check_startup_programs() -> list:
    """Check for suspicious startup entries."""
    results = []
    # Check Run keys
    for hive in ["HKCU", "HKLM"]:
        output = _run(f'reg query "{hive}\\Software\\Microsoft\\Windows\\CurrentVersion\\Run" 2>nul')
        for line in output.split("\n"):
            if "\\" in line and "REG_" in line:
                parts = line.split("REG_")
                if len(parts) >= 2:
                    name = parts[0].strip()
                    path = parts[-1].strip()
                    # Check if path points to temp or unusual location
                    if any(x in path.lower() for x in ["temp", "appdata\\local\\temp", "\\downloads\\", "update"]):
                        results.append({
                            "entry": name,
                            "path": path,
                            "hive": hive,
                            "warning": "Startup entry pointing to temp/downloads folder",
                            "severity": "HIGH",
                        })
    return results


def _check_password_strength() -> list:
    """Check system password policies."""
    results = []
    output = _run("net accounts")
    for line in output.split("\n"):
        if "Minimum password" in line:
            results.append({"policy": line.strip()})
        if "Maximum password" in line:
            results.append({"policy": line.strip()})
        if "Password history" in line:
            results.append({"policy": line.strip()})

    # Check if password is blank for current user
    user_output = _run("net user")
    if "Password required" in user_output.lower():
        results.append({"warning": "Some users may not require passwords"})

    return results


def _check_windows_defender() -> dict:
    """Check Windows Defender status."""
    result = {}
    output = _run('powershell -Command "Get-MpComputerStatus | Select-Object RealTimeProtectionEnabled, AntivirusEnabled, AntispywareEnabled, AntivirusSignatureLastUpdated"')
    for line in output.split("\n"):
        line = line.strip()
        if "RealTimeProtectionEnabled" in line:
            result["realtime"] = "True" in line
        if "AntivirusEnabled" in line:
            result["antivirus"] = "True" in line
        if "AntivirusSignatureLastUpdated" in line:
            result["last_update"] = line.split(":")[-1].strip() if ":" in line else line
    return result


def _check_firewall_status() -> dict:
    """Check Windows Firewall status."""
    result = {}
    output = _run("netsh advfirewall show allprofiles state")
    for line in output.split("\n"):
        line = line.strip()
        if "Domain Profile" in line:
            result["domain"] = "ON" in line.upper()
        if "Standard Profile" in line or "Private Profile" in line:
            result["private"] = "ON" in line.upper()
        if "Public Profile" in line:
            result["public"] = "ON" in line.upper()
    return result


def _check_open_ports() -> list:
    """List all listening ports and identify potentially dangerous ones."""
    listening = []
    known_dangerous = {
        21: "FTP (unencrypted)",
        23: "Telnet (unencrypted)",
        3389: "RDP (remote desktop)",
        445: "SMB (network shares)",
        135: "RPC",
        139: "NetBIOS",
        5985: "WinRM HTTP",
        5986: "WinRM HTTPS",
    }

    output = _run("netstat -ano -p TCP")
    for line in output.split("\n"):
        if "LISTENING" in line:
            parts = line.split()
            if len(parts) >= 4:
                local = parts[1]
                pid = parts[-1]
                try:
                    port = int(local.split(":")[-1])
                    entry = {"port": port, "address": local, "pid": pid}
                    if port in known_dangerous:
                        entry["warning"] = known_dangerous[port]
                        entry["severity"] = "HIGH" if port in (23, 21) else "MEDIUM"
                    listening.append(entry)
                except ValueError:
                    pass
    return listening


def _check_recent_logins() -> list:
    """Check recent login events for anomalies."""
    results = []
    output = _run('wevtutil qe Security /q:"*[System[EventID=4624]]" /f:text /c:10 /rd:true')
    for block in output.split("\n\n"):
        if "Logon Type:" in block:
            type_match = re.search(r"Logon Type:\s*(\d+)", block)
            user_match = re.search(r"New Logon.*?Account Name:\s*(\S+)", block, re.DOTALL)
            ip_match = re.search(r"Source Network Address:\s*(\S+)", block)
            if type_match:
                logon_type = type_match.group(1)
                # Type 10 = RemoteInteractive (RDP), Type 3 = Network
                if logon_type in ("10", "3"):
                    results.append({
                        "type": f"Logon Type {logon_type}",
                        "user": user_match.group(1) if user_match else "?",
                        "ip": ip_match.group(1) if ip_match else "?",
                        "warning": "Remote/network login detected" if logon_type == "10" else "Network login",
                    })
    return results


# ═══════════════════════════════════════════════════════════════════
# SECURITY ANALYSIS
# ═══════════════════════════════════════════════════════════════════

def _generate_security_score(checks: dict) -> int:
    """Calculate a security score from 0-100."""
    score = 100

    # Deductions
    if checks.get("defender", {}).get("realtime") == False:
        score -= 20
    if checks.get("firewall", {}).get("public") == False:
        score -= 15
    if checks.get("suspicious_processes"):
        score -= 15 * min(len(checks["suspicious_processes"]), 3)
    if checks.get("dangerous_ports"):
        score -= 10 * min(len(checks["dangerous_ports"]), 3)
    if checks.get("startup_warnings"):
        score -= 10 * min(len(checks["startup_warnings"]), 2)
    if checks.get("suspicious_connections"):
        score -= 10 * min(len(checks["suspicious_connections"]), 2)

    return max(0, score)


def _get_recommendations(checks: dict) -> list:
    """Generate security recommendations based on findings."""
    recs = []

    if checks.get("defender", {}).get("realtime") == False:
        recs.append("ENABLE Windows Defender real-time protection immediately")

    if checks.get("defender", {}).get("antivirus") == False:
        recs.append("Windows Defender is disabled — install antivirus")

    if checks.get("firewall", {}).get("public") == False:
        recs.append("Enable Windows Firewall for public networks")

    if checks.get("suspicious_processes"):
        recs.append("INVESTIGATE suspicious processes running on your system")

    if checks.get("suspicious_connections"):
        recs.append("Review suspicious outbound network connections")

    if checks.get("dangerous_ports"):
        recs.append("Close unnecessary open ports (RDP, FTP, Telnet)")

    if checks.get("startup_warnings"):
        recs.append("Review suspicious startup entries in registry")

    # Always recommend
    recs.append("Use 2FA/MFA on all important accounts")
    recs.append("Use unique passwords for each service")
    recs.append("Keep Windows and software updated")
    recs.append("Never click suspicious links in emails")
    recs.append("Use a VPN on public WiFi")

    return recs


# ═══════════════════════════════════════════════════════════════════
# MAIN FUNCTION
# ═══════════════════════════════════════════════════════════════════

def security_shield(parameters: dict, player=None) -> str:
    """
    Escudo de seguridad defensivo de Eris.
    Monitorea tu sistema, detecta amenazas y te protege.

    Acciones:
      - scan: Escaneo completo de seguridad (procesos, puertos, firewall, defender, startups)
      - threat: Buscar amenazas activas (procesos sospechosos, conexiones)
      - ports: Puertos abiertos y análisis de riesgo
      - firewall: Estado del firewall
      - defender: Estado de Windows Defender
      - startups: Programas de inicio sospechosos
      - score: Puntuación de seguridad general (0-100)
      - alerts: Ver historial de alertas de seguridad
      - protect: Plan de protección personalizado
      - password_check: Analizar fortaleza de contraseñas del sistema
    """
    action = parameters.get("action", "scan").lower()

    if action == "scan":
        result = "# SECURITY SHIELD - Full Scan\n\n"
        checks = {}

        # Run all checks
        checks["defender"] = _check_windows_defender()
        checks["firewall"] = _check_firewall_status()
        checks["suspicious_processes"] = _check_suspicious_processes()
        checks["suspicious_connections"] = _check_network_connections()
        checks["startup_warnings"] = _check_startup_programs()
        checks["open_ports"] = _check_open_ports()
        checks["dangerous_ports"] = [p for p in checks["open_ports"] if "warning" in p]
        checks["password_policies"] = _check_password_strength()

        score = _generate_security_score(checks)
        result += f"**Security Score: {score}/100**\n\n"

        # Windows Defender
        d = checks["defender"]
        result += f"## Windows Defender\n"
        result += f"  Real-time: {'ON' if d.get('realtime') else 'OFF'}\n"
        result += f"  Antivirus: {'ON' if d.get('antivirus') else 'OFF'}\n"
        result += f"  Last update: {d.get('last_update', '?')}\n\n"

        # Firewall
        f = checks["firewall"]
        result += f"## Firewall\n"
        for profile, enabled in f.items():
            result += f"  {profile}: {'ON' if enabled else 'OFF'}\n"

        # Suspicious processes
        if checks["suspicious_processes"]:
            result += f"\n## SUSPICIOUS PROCESSES ({len(checks['suspicious_processes'])})\n"
            for p in checks["suspicious_processes"]:
                result += f"  [{p['severity']}] {p['warning']} (PID: {p['pid']})\n"
        else:
            result += "\n## Suspicious Processes: NONE DETECTED\n"

        # Suspicious connections
        if checks["suspicious_connections"]:
            result += f"\n## SUSPICIOUS CONNECTIONS ({len(checks['suspicious_connections'])})\n"
            for c in checks["suspicious_connections"]:
                result += f"  [{c['severity']}] {c['message']} -> {c['remote']}\n"
        else:
            result += "\n## Suspicious Connections: NONE DETECTED\n"

        # Dangerous ports
        if checks["dangerous_ports"]:
            result += f"\n## DANGEROUS OPEN PORTS ({len(checks['dangerous_ports'])})\n"
            for p in checks["dangerous_ports"]:
                result += f"  [{p.get('severity','MEDIUM')}] Port {p['port']}: {p['warning']}\n"

        # Recommendations
        recs = _get_recommendations(checks)
        result += "\n## RECOMMENDATIONS\n"
        for i, rec in enumerate(recs[:8], 1):
            result += f"  {i}. {rec}\n"

        _add_alert("full_scan", "INFO", f"Security scan completed. Score: {score}/100")
        return result

    elif action == "threat":
        result = "**THREAT DETECTION**\n\n"
        procs = _check_suspicious_processes()
        conns = _check_network_connections()

        if procs:
            result += f"Suspicious processes: {len(procs)}\n"
            for p in procs:
                result += f"  [{p['severity']}] {p['warning']}\n"
        else:
            result += "Suspicious processes: NONE\n"

        if conns:
            result += f"\nSuspicious connections: {len(conns)}\n"
            for c in conns:
                result += f"  [{c['severity']}] {c['message']}\n"
        else:
            result += "\nSuspicious connections: NONE\n"

        if not procs and not conns:
            result += "\nNo active threats detected.\n"
        return result

    elif action == "ports":
        ports = _check_open_ports()
        result = "**OPEN PORTS ANALYSIS**\n\n"
        dangerous = [p for p in ports if "warning" in p]
        safe = [p for p in ports if "warning" not in p]

        if dangerous:
            result += f"DANGEROUS ({len(dangerous)}):\n"
            for p in dangerous:
                result += f"  Port {p['port']}: {p['warning']} (PID: {p['pid']})\n"
        result += f"\nLISTENING ({len(safe)} safe ports)\n"
        return result

    elif action == "firewall":
        f = _check_firewall_status()
        result = "**FIREWALL STATUS**\n\n"
        for profile, enabled in f.items():
            status = "ON" if enabled else "OFF"
            if not enabled:
                _add_alert("firewall", "HIGH", f"Firewall is OFF on {profile} profile")
            result += f"  {profile}: {status}\n"
        return result

    elif action == "defender":
        d = _check_windows_defender()
        result = "**WINDOWS DEFENDER STATUS**\n\n"
        for k, v in d.items():
            result += f"  {k}: {v}\n"
        if not d.get("realtime"):
            _add_alert("defender", "CRITICAL", "Windows Defender real-time protection is OFF")
        return result

    elif action == "startups":
        startups = _check_startup_programs()
        result = "**STARTUP ENTRIES ANALYSIS**\n\n"
        if startups:
            for s in startups:
                result += f"  [{s['severity']}] {s['entry']}: {s['warning']}\n"
                result += f"    Path: {s['path']}\n\n"
        else:
            result += "No suspicious startup entries found.\n"
        return result

    elif action == "score":
        checks = {
            "defender": _check_windows_defender(),
            "firewall": _check_firewall_status(),
            "suspicious_processes": _check_suspicious_processes(),
            "suspicious_connections": _check_network_connections(),
            "startup_warnings": _check_startup_programs(),
            "open_ports": _check_open_ports(),
            "dangerous_ports": [p for p in _check_open_ports() if "warning" in p],
        }
        score = _generate_security_score(checks)
        color = "GREEN" if score >= 80 else "YELLOW" if score >= 50 else "RED"
        return f"**Security Score: {score}/100** [{color}]"

    elif action == "alerts":
        alerts = _load_alerts()
        result = f"**SECURITY ALERTS ({len(alerts)} total)**\n\n"
        for a in alerts[-15:]:
            result += f"  [{a['time'][:16]}] [{a['severity']}] {a['type']}: {a['message']}\n"
        if not alerts:
            result += "No alerts recorded yet.\n"
        return result

    elif action == "protect":
        result = "**PERSONALIZED SECURITY PLAN**\n\n"
        d = _check_windows_defender()
        f = _check_firewall_status()
        procs = _check_suspicious_processes()

        result += "## IMMEDIATE ACTIONS\n"
        if not d.get("realtime"):
            result += "1. Enable Windows Defender real-time protection NOW\n"
        if not f.get("public"):
            result += "2. Enable Firewall for public networks\n"
        if procs:
            result += "3. Investigate and close suspicious processes\n"

        result += "\n## HARDENING\n"
        result += "1. Enable BitLocker on all drives\n"
        result += "2. Disable Remote Desktop if not needed\n"
        result += "3. Set Windows to auto-update\n"
        result += "4. Use a password manager (Bitwarden, KeePass)\n"
        result += "5. Enable 2FA on Google, GitHub, email\n"
        result += "6. Use DNS-over-HTTPS (Cloudflare 1.1.1.1)\n"

        result += "\n## MONITORING\n"
        result += "1. Run security_shield scan weekly\n"
        result += "2. Check breach data monthly\n"
        result += "3. Review startup programs quarterly\n"

        return result

    elif action == "password_check":
        result = "**PASSWORD POLICY CHECK**\n\n"
        policies = _check_password_strength()
        for p in policies:
            result += f"  {p.get('policy', p.get('warning', '?'))}\n"
        if not policies:
            result += "  Could not retrieve password policies.\n"
        return result

    available = "scan | threat | ports | firewall | defender | startups | score | alerts | protect | password_check"
    return f"Action '{action}' not found. Available: {available}"
