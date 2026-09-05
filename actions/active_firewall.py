import subprocess
import json
from pathlib import Path
from datetime import datetime

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "firewall_rules.json"

def _load_rules():
    try:
        if DATA_FILE.exists():
            return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError): pass
    return {"blocked_ips": [], "blocked_ports": [], "rules": []}

def _save_rules(rules):
    try:
        DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        DATA_FILE.write_text(json.dumps(rules, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError: pass

def active_firewall(parameters: dict, player=None) -> str:
    action = (parameters.get("action") or "status").lower()
    ip = parameters.get("ip") or ""
    port = parameters.get("port") or ""
    rule_name = parameters.get("name") or "ERIS_Block"

    rules = _load_rules()

    if player:
        player.write_log(f"🛡️ Firewall: {action}")

    if action in ("block_ip", "bloquear_ip"):
        return _block_ip(ip, rules, rule_name)
    elif action in ("unblock_ip", "desbloquear_ip"):
        return _unblock_ip(ip, rules, rule_name)
    elif action in ("block_port", "bloquear_puerto"):
        return _block_port(port, rules, rule_name)
    elif action in ("unblock_port", "desbloquear_puerto"):
        return _unblock_port(port, rules, rule_name)
    elif action in ("list", "listar", "reglas"):
        return _list_rules(rules)
    elif action in ("status", "estado"):
        return _firewall_status()
    elif action in ("scan", "escanear"):
        return _scan_connections()
    elif action in ("clear", "limpiar"):
        return _clear_rules(rules)
    elif action in ("log", "registros"):
        return _show_log()
    else:
        return "Acciones: block_ip, unblock_ip, block_port, unblock_port, list, status, scan, clear, log"

def _block_ip(ip, rules, name):
    if not ip:
        return "¿Qué IP querés bloquear?"
    try:
        cmd = f'netsh advfirewall firewall add rule name="{name}_{ip}" dir=in action=block remoteip={ip}'
        result = subprocess.run(["netsh", "advfirewall", "firewall", "add", "rule",
                                 f"name={name}_{ip}", "dir=in", "action=block", f"remoteip={ip}"],
                                capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            rules["blocked_ips"].append({"ip": ip, "name": name, "time": datetime.now().isoformat()})
            _save_rules(rules)
            return f"🛡️ IP {ip} bloqueada (regla: {name}_{ip})"
        return f"Error: {result.stderr.strip() or 'permisos de admin requeridos'}"
    except Exception as e:
        return f"Error al bloquear IP: {e}"

def _unblock_ip(ip, rules, name):
    if not ip:
        return "¿Qué IP querés desbloquear?"
    try:
        result = subprocess.run(["netsh", "advfirewall", "firewall", "delete", "rule",
                                 f"name={name}_{ip}"],
                                capture_output=True, text=True, timeout=10)
        rules["blocked_ips"] = [r for r in rules["blocked_ips"] if r["ip"] != ip]
        _save_rules(rules)
        return f"✅ IP {ip} desbloqueada"
    except Exception as e:
        return f"Error: {e}"

def _block_port(port, rules, name):
    if not port:
        return "¿Qué puerto querés bloquear?"
    try:
        result = subprocess.run(
            ["netsh", "advfirewall", "firewall", "add", "rule",
             f"name={name}_port{port}", "dir=in", "action=block", f"protocol=tcp", f"localport={port}"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            rules["blocked_ports"].append({"port": port, "time": datetime.now().isoformat()})
            _save_rules(rules)
            return f"🛡️ Puerto {port} bloqueado"
        return f"Error: {result.stderr.strip() or 'permisos requeridos'}"
    except Exception as e:
        return f"Error: {e}"

def _unblock_port(port, rules, name):
    if not port:
        return "¿Qué puerto?"
    try:
        result = subprocess.run(["netsh", "advfirewall", "firewall", "delete", "rule",
                                 f"name={name}_port{port}"],
                                capture_output=True, text=True, timeout=10)
        rules["blocked_ports"] = [r for r in rules["blocked_ports"] if r["port"] != port]
        _save_rules(rules)
        return f"✅ Puerto {port} desbloqueado"
    except Exception as e:
        return f"Error: {e}"

def _list_rules(rules):
    lines = []
    if rules["blocked_ips"]:
        lines.append("IPs bloqueadas:")
        for r in rules["blocked_ips"]:
            lines.append(f"  • {r['ip']} (bloqueada {r.get('time', '')[:16]})")
    if rules["blocked_ports"]:
        lines.append("Puertos bloqueados:")
        for r in rules["blocked_ports"]:
            lines.append(f"  • Puerto {r['port']}")
    if not lines:
        return "No hay reglas de firewall configuradas."
    return "\n".join(lines)

def _firewall_status():
    try:
        result = subprocess.run(
            ["netsh", "advfirewall", "show", "allprofiles", "state"],
            capture_output=True, text=True, timeout=10
        )
        return f"Estado del firewall:\n{result.stdout.strip()}"
    except Exception as e:
        return f"Error: {e}"

def _scan_connections():
    try:
        result = subprocess.run(
            ["netstat", "-an"],
            capture_output=True, text=True, timeout=10
        )
        lines = result.stdout.strip().split("\n")
        established = [l for l in lines if "ESTABLISHED" in l]
        listening = [l for l in lines if "LISTENING" in l]
        return (
            f"Conexiones activas:\n"
            f"Establecidas: {len(established)}\n"
            f"Escuchando: {len(listening)}\n"
            f"\nPrimeras 10 establecidas:\n" + "\n".join(established[:10])
        )
    except Exception as e:
        return f"Error: {e}"

def _clear_rules(rules):
    for r in rules.get("blocked_ips", []):
        try:
            subprocess.run(["netsh", "advfirewall", "firewall", "delete", "rule",
                           f"name={r.get('name', 'ERIS_Block')}_{r['ip']}"],
                           capture_output=True, timeout=5)
        except Exception: pass
    for r in rules.get("blocked_ports", []):
        try:
            subprocess.run(["netsh", "advfirewall", "firewall", "delete", "rule",
                           f"name=ERIS_Block_port{r['port']}"],
                           capture_output=True, timeout=5)
        except Exception: pass
    rules["blocked_ips"] = []
    rules["blocked_ports"] = []
    _save_rules(rules)
    return "Todas las reglas de ERIS eliminadas."

def _show_log():
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             "Get-NetFirewallRule | Where-Object {$_.DisplayName -like 'ERIS_*'} | Select-Object DisplayName, Direction, Action, Enabled | Format-Table -AutoSize"],
            capture_output=True, text=True, timeout=15
        )
        if result.stdout.strip():
            return f"Reglas ERIS en Windows Firewall:\n{result.stdout.strip()}"
        return "No hay reglas ERIS en el firewall."
    except Exception as e:
        return f"Error: {e}"
