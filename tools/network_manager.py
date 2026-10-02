#!/usr/bin/env python3
"""network_manager wrapper — gestión de red para Linux Arch"""
import subprocess
import socket
from pathlib import Path

TOOL_NAME = "network_manager"

ACTIONS_AVAILABLE = ["list_interfaces", "interface_info", "ping",
                     "dns_lookup", "wifi_status", "ip_info", "status"]

def tool_handler(params=None):
    """Handler para network_manager."""
    if params is None:
        params = {}

    action = params.get("action", "status")

    if action == "status":
        return f"network_manager: {', '.join(ACTIONS_AVAILABLE)}"
    elif action == "list_interfaces":
        result = subprocess.run(["ip", "link", "show"], capture_output=True, text=True, timeout=10)
        interfaces = [line.split(":")[1].strip() for line in result.stdout.strip().split("\n")[1:] if ":" in line]
        return f"Interfaces: {interfaces}"
    elif action == "interface_info":
        iface = params.get("interface", "eth0")
        result = subprocess.run(["ip", "addr", "show", iface], capture_output=True, text=True, timeout=10)
        return result.stdout[:500] if result.stdout else f"No info for {iface}"
    elif action == "ping":
        host = params.get("host", "8.8.8.8")
        result = subprocess.run(["ping", "-c", "4", host], capture_output=True, text=True, timeout=10)
        return result.stdout[-500:] if result.stdout else "Ping failed"
    elif action == "dns_lookup":
        hostname = params.get("hostname", "google.com")
        try:
            ip = socket.gethostbyname(hostname)
            return f"{hostname} → {ip}"
        except Exception as e:
            return f"DNS lookup failed: {e}"
    elif action == "wifi_status":
        result = subprocess.run(["iwconfig"], capture_output=True, text=True, timeout=10)
        return result.stdout[:500] if result.stdout else "No Wi-Fi info"
    elif action == "ip_info":
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        return f"Hostname: {hostname}, IP: {ip}"
    else:
        return f"Error: Unknown action '{action}'. Available: {', '.join(ACTIONS_AVAILABLE)}"

def get_declarations():
    return {
        "network_manager": "Gestión de red — interface, IP, conexión, Wi-Fi, DNS, ping",
    }

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        action = sys.argv[1]
    else:
        action = "status"
    print(tool_handler({"action": action}))
