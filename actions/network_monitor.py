import subprocess
import json
from pathlib import Path
from datetime import datetime

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "network_log.json"

def network_monitor(parameters: dict, player=None) -> str:
    action = (parameters.get("action") or "status").lower()
    duration = parameters.get("duration") or 5

    if player:
        player.write_log(f"🌐 Network Monitor: {action}")

    if action in ("status", "estado"):
        return _network_status()
    elif action in ("connections", "conexiones"):
        return _list_connections()
    elif action in ("bandwidth", "ancho_banda"):
        return _bandwidth_test()
    elif action in ("interfaces", "interfaces"):
        return _list_interfaces()
    elif action in ("dns", "resolver"):
        return _dns_lookup(parameters.get("host") or "")
    elif action in ("ping", "probar"):
        return _ping(parameters.get("host") or "")
    elif action in ("traceroute", "ruta"):
        return _traceroute(parameters.get("host") or "")
    elif action in ("suspicious", "sospechosas"):
        return _suspicious_connections()
    elif action in ("block", "bloquear"):
        return _block_connection(parameters.get("pid") or "")
    else:
        return "Acciones: status, connections, bandwidth, interfaces, dns, ping, traceroute, suspicious, block"

def _network_status():
    try:
        result = subprocess.run(
            ["netsh", "interface", "show", "interface"],
            capture_output=True, text=True, timeout=10
        )
        interfaces = []
        for line in result.stdout.strip().split("\n"):
            if "Connected" in line or "Disconnected" in line:
                parts = line.split()
                if len(parts) >= 3:
                    state = "🟢" if "Connected" in line else "🔴"
                    name = " ".join(parts[3:])
                    interfaces.append(f"  {state} {name}: {parts[1]}")

        ip_result = subprocess.run(
            ["ipconfig"],
            capture_output=True, text=True, timeout=10
        )
        ip = "No disponible"
        for line in ip_result.stdout.split("\n"):
            if "IPv4" in line:
                ip = line.split(":")[-1].strip()
                break

        return f"🌐 Estado de red:\nIP: {ip}\nInterfaces:\n" + "\n".join(interfaces)
    except Exception as e:
        return f"Error: {e}"

def _list_connections():
    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True, text=True, timeout=10
        )
        lines = result.stdout.strip().split("\n")
        established = []
        for line in lines:
            if "ESTABLISHED" in line:
                parts = line.split()
                if len(parts) >= 5:
                    local = parts[1]
                    remote = parts[2]
                    pid = parts[-1]
                    established.append(f"  {local} → {remote} (PID: {pid})")

        return f"Conexiones establecidas ({len(established)}):\n" + "\n".join(established[:20])
    except Exception as e:
        return f"Error: {e}"

def _bandwidth_test():
    try:
        import time
        import urllib.request

        test_urls = [
            ("Google", "https://www.google.com"),
            ("GitHub", "https://github.com"),
        ]

        results = []
        for name, url in test_urls:
            start = time.time()
            try:
                req = urllib.request.Request(url, method="HEAD")
                urllib.request.urlopen(req, timeout=5)
                elapsed = time.time() - start
                speed = (1024 * 1024) / elapsed if elapsed > 0 else 0
                results.append(f"  {name}: {elapsed*1000:.0f}ms (~{speed/1024:.1f} MB/s)")
            except:
                results.append(f"  {name}: No disponible")

        return f"Test de velocidad:\n" + "\n".join(results)
    except Exception as e:
        return f"Error: {e}"

def _list_interfaces():
    try:
        result = subprocess.run(
            ["ipconfig", "/all"],
            capture_output=True, text=True, timeout=10
        )
        return f"Interfaces de red:\n{result.stdout[:2000]}"
    except Exception as e:
        return f"Error: {e}"

def _dns_lookup(host):
    if not host:
        return "¿Qué dominio querés resolver?"
    try:
        result = subprocess.run(
            ["nslookup", host],
            capture_output=True, text=True, timeout=10
        )
        return f"DNS de {host}:\n{result.stdout.strip()}"
    except Exception as e:
        return f"Error: {e}"

def _ping(host):
    if not host:
        host = "8.8.8.8"
    try:
        result = subprocess.run(
            ["ping", "-n", "4", host],
            capture_output=True, text=True, timeout=15
        )
        return f"Ping a {host}:\n{result.stdout.strip()}"
    except Exception as e:
        return f"Error: {e}"

def _traceroute(host):
    if not host:
        return "¿A qué host querés hacer traceroute?"
    try:
        result = subprocess.run(
            ["tracert", "-d", "-h", "10", host],
            capture_output=True, text=True, timeout=30
        )
        return f"Traceroute a {host}:\n{result.stdout.strip()}"
    except Exception as e:
        return f"Error: {e}"

def _suspicious_connections():
    try:
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True, text=True, timeout=10
        )
        suspicious = []
        for line in result.stdout.split("\n"):
            if "ESTABLISHED" in line:
                parts = line.split()
                if len(parts) >= 5:
                    remote = parts[2]
                    remote_ip = remote.split(":")[0] if ":" in remote else remote
                    if remote_ip and not remote_ip.startswith("127.") and not remote_ip.startswith("192.168."):
                        if remote_ip not in [s.split("→")[1].strip() if "→" in s else "" for s in suspicious]:
                            pid = parts[-1]
                            suspicious.append(f"  {remote} (PID: {pid})")

        if suspicious:
            return f"Conexiones externas ({len(suspicious)}):\n" + "\n".join(suspicious[:15])
        return "No se detectaron conexiones externas sospechosas."
    except Exception as e:
        return f"Error: {e}"

def _block_connection(pid):
    if not pid:
        return "¿Qué PID querés bloquear?"
    try:
        result = subprocess.run(
            ["taskkill", "/F", "/PID", str(pid)],
            capture_output=True, text=True, timeout=5
        )
        return f"Proceso {pid} terminado" if result.returncode == 0 else f"No pude terminar PID {pid}"
    except Exception as e:
        return f"Error: {e}"
