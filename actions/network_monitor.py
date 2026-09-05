import subprocess
import json
import os
from pathlib import Path
from datetime import datetime

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "network_log.json"

_IS_LINUX = os.name != "nt"
_IS_WINDOWS = os.name == "nt"


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


# ── Helpers Linux (iproute2: ip / ss / ping, presente en cualquier distro) ──

def _linux_interfaces():
    """Devuelve lista de (nombre, estado, ipv4) con `ip -o`. Robustez ante parseo."""
    items = []
    try:
        r = subprocess.run(["ip", "-o", "link", "show"], capture_output=True, text=True, timeout=10)
        if r.returncode == 0 and r.stdout.strip():
            for line in r.stdout.splitlines():
                parts = line.split()
                if len(parts) >= 2:
                    items.append({"name": parts[1].rstrip(":"), "state": None, "ip": None})
    except Exception:
        pass
    try:
        r = subprocess.run(["ip", "-o", "-4", "addr", "show"], capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            ip_map = {}
            for line in r.stdout.splitlines():
                parts = line.split()
                # 2: wlan0    inet 192.168.1.5/24 brd ... scope global ...
                if len(parts) >= 4 and parts[2] == "inet":
                    name = parts[1].rstrip(":")
                    ip_map.setdefault(name, parts[3])
            for it in items:
                it["ip"] = ip_map.get(it["name"])
    except Exception:
        pass
    return items


def _linux_system_status():
    items = _linux_interfaces()
    lines = []
    for it in items:
        state = "🟢" if it["ip"] else "🔴"
        lines.append(f"  {state} {it['name']}: {it['ip'] or 'sin IP'}")
    default_ip = next((it["ip"] for it in items if it["ip"]), "No disponible")
    return f"🌐 Estado de red:\nIP: {default_ip}\nInterfaces:\n" + (("\n".join(lines)) if lines else "  (sin interfaces)")


def _linux_connections():
    """Conexiones establecidas vía `ss -tnp` (parsea local, remoto, PID)."""
    try:
        r = subprocess.run(["ss", "-tnp", "state", "established"],
                           capture_output=True, text=True, timeout=10)
        lines = r.stdout.strip().splitlines()
        established = []
        for line in lines:
            parts = line.split()
            if len(parts) >= 5 and parts[0] in ("tcp", "ESTAB", "LISTEN"):
                local, remote = parts[3] if parts[0] == "tcp" else parts[3], parts[4] if parts[0] == "tcp" else parts[4]
                pid = ""
                for tok in parts[5:]:
                    if "pid=" in tok:
                        pid = tok.split("pid=")[1].rstrip(")")
                        break
                established.append(f"  {local} → {remote}" + (f" (PID: {pid})" if pid else ""))
        return f"Conexiones establecidas ({len(established)}):\n" + "\n".join(established[:20])
    except Exception as e:
        return f"Error: {e}"


def _linux_connections_parsed():
    try:
        r = subprocess.run(["ss", "-tnp", "state", "established"],
                           capture_output=True, text=True, timeout=10)
        out = []
        for line in r.stdout.strip().splitlines():
            parts = line.split()
            if len(parts) >= 5 and parts[0] == "tcp":
                pid = ""
                for tok in parts[5:]:
                    if "pid=" in tok:
                        pid = tok.split("pid=")[1].rstrip(")")
                        break
                out.append({"local": parts[3], "remote": parts[4], "pid": pid})
        return out
    except Exception:
        return []


def _linux_dns(host):
    import socket
    try:
        ip = socket.gethostbyname(host)
        return f"DNS de {host}: {ip}"
    except socket.gaierror:
        return f"No se pudo resolver {host}."
    except Exception as e:
        return f"Error: {e}"


def _linux_ping(host):
    try:
        result = subprocess.run(["ping", "-c", "4", host], capture_output=True, text=True, timeout=15)
        return f"Ping a {host}:\n{result.stdout.strip() or result.stderr.strip()}"
    except Exception as e:
        return f"Error: {e}"


def _linux_traceroute(host):
    try:
        result = subprocess.run(["traceroute", "-n", "-m", "10", host],
                                capture_output=True, text=True, timeout=30)
        if result.returncode == 0 and result.stdout.strip():
            return f"Traceroute a {host}:\n{result.stdout.strip()}"
        stderr = (result.stderr or "").strip()
        if "not found" in stderr or "No such file" in stderr:
            return "traceroute no está instalado. Instalalo con: sudo pacman -S traceroute"
        return f"Traceroute a {host}:\n{stderr or 'sin salida'}"
    except Exception as e:
        return f"Error: {e}"


def _linux_block(pid):
    try:
        result = subprocess.run(["kill", "-9", str(pid)], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return f"Proceso {pid} terminado"
        err = (result.stderr or "").strip()
        return f"No pude terminar PID {pid}: {err}" if err else f"No pude terminar PID {pid}"
    except Exception as e:
        return f"Error: {e}"


# ── Acciones públicas ──

def _network_status():
    if _IS_LINUX:
        return _linux_system_status()
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
    if _IS_LINUX:
        return _linux_connections()
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
            except Exception:
                results.append(f"  {name}: No disponible")

        return f"Test de velocidad:\n" + "\n".join(results)
    except Exception as e:
        return f"Error: {e}"


def _list_interfaces():
    if _IS_LINUX:
        items = _linux_interfaces()
        if not items:
            return "No se pudieron listar interfaces (se espera iproute2)."
        lines = [f"  {'🟢' if it['ip'] else '🔴'} {it['name']}: {it['ip'] or 'sin IP'}" for it in items]
        return "Interfaces de red:\n" + "\n".join(lines)
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
    if _IS_LINUX:
        return _linux_dns(host)
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
    if _IS_LINUX:
        return _linux_ping(host)
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
    if _IS_LINUX:
        return _linux_traceroute(host)
    try:
        result = subprocess.run(
            ["tracert", "-d", "-h", "10", host],
            capture_output=True, text=True, timeout=30
        )
        return f"Traceroute a {host}:\n{result.stdout.strip()}"
    except Exception as e:
        return f"Error: {e}"


def _suspicious_connections():
    if _IS_LINUX:
        conns = _linux_connections_parsed()
        suspicious = []
        for c in conns:
            remote = c.get("remote") or ""
            remote_ip = remote.rsplit(":", 1)[0] if ":" in remote else remote
            if remote_ip and remote_ip not in ("0.0.0.0", "*"):
                private = (remote_ip.startswith("127.") or remote_ip.startswith("10.")
                           or remote_ip.startswith("192.168.")
                           or remote_ip in ("::1", "::", "0:0:0:0:0:0:0:1")
                           or (remote_ip.startswith("172.") and 16 <= int(remote_ip.split(".")[1] or 0) <= 31)
                           or remote_ip.startswith("169.254."))
                if not private:
                    suspicious.append(f"  {remote}" + (f" (PID: {c.get('pid')})" if c.get("pid") else ""))
        if suspicious:
            return f"Conexiones externas ({len(suspicious)}):\n" + "\n".join(suspicious[:15])
        return "No se detectaron conexiones externas sospechosas."
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
    if _IS_LINUX:
        return _linux_block(pid)
    try:
        result = subprocess.run(
            ["taskkill", "/F", "/PID", str(pid)],
            capture_output=True, text=True, timeout=5
        )
        return f"Proceso {pid} terminado" if result.returncode == 0 else f"No pude terminar PID {pid}"
    except Exception as e:
        return f"Error: {e}"