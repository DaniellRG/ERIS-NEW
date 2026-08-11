# -*- coding: utf-8 -*-
"""
ERIS Health Endpoint – Servidor HTTP mínimo de liveness en el puerto 8765.
Solo responde a probes del watchdog; no hay chat móvil ni WebSocket.
"""

import json
import os
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MOBILE_PORT = 8765


def _get_local_ip() -> str:
    """Get the local network IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


class _HealthHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _json(self, payload: dict):
        body = json.dumps(payload).encode("utf-8")
        try:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError):
            pass

    def do_GET(self):
        self._json({"status": "ok", "service": "eris", "pid": os.getpid()})

    def do_POST(self):
        self._json({"status": "ok", "service": "eris", "pid": os.getpid()})


def start(port: int = 8765, inject_callback=None) -> str:
    """Start the health server in a daemon thread. Returns the HTTP URL."""
    server = ThreadingHTTPServer(("0.0.0.0", port), _HealthHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    print(f"[HEALTH] Endpoint de salud iniciado en puerto {port}")
    return f"http://{_get_local_ip()}:{port}"


def broadcast(text: str):
    """No-op: el chat móvil fue eliminado."""
    return
