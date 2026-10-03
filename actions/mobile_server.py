# -*- coding: utf-8 -*-
"""
ERIS Health Endpoint – Servidor HTTP mínimo de liveness en el puerto 8765.

Además del probe de salud, expone POST /chat para inyectar texto en la GUI de
forma programática (sin keystrokes sintéticos, que en Wayland son frágiles).
El texto inyectado entra por el mismo camino que si el usuario lo escribiera:
`inject_callback(text)` → `_on_text_command`.

Rutas:
  GET  /            → {"status": "ok", "service": "eris", "pid": N}
  GET  /health      → idem
  POST /chat        → {"text": "..."} inyecta el texto en Eris
  POST /            → idem que /chat si el body trae "text"
"""

import json
import os
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MOBILE_PORT = 8765

# Callback que inyecta texto en la GUI (lo setea main.py al arrancar).
_inject_callback = None
_inject_lock = threading.Lock()


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

    def _json(self, payload: dict, code: int = 200):
        body = json.dumps(payload).encode("utf-8")
        try:
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError):
            pass

    def _health(self):
        self._json({"status": "ok", "service": "eris", "pid": os.getpid()})

    def do_GET(self):
        self._health()

    def do_POST(self):
        # Leer body si hay
        try:
            length = int(self.headers.get("Content-Length", 0) or 0)
        except Exception:
            length = 0
        raw = self.rfile.read(length) if length else b""

        # Sin body → es un probe de salud
        if not raw:
            self._health()
            return

        try:
            data = json.loads(raw.decode("utf-8", "replace"))
        except Exception:
            self._json({"error": "JSON inválido"}, 400)
            return

        text = (data.get("text") or data.get("message") or "").strip()
        if not text:
            self._json({"error": "Falta 'text'"}, 400)
            return

        with _inject_lock:
            cb = _inject_callback
        if cb is None:
            self._json({"error": "La GUI no expone canal de inyección"}, 503)
            return

        # Inyectar en un hilo para no bloquear la respuesta HTTP: el handler
        # de la GUI puede tardar (ejecuta tools, habla con el LLM, etc.).
        threading.Thread(target=cb, args=(text,), daemon=True).start()
        self._json({"status": "ok", "injected": text})


def start(port: int = 8765, inject_callback=None) -> str:
    """Start the health server in a daemon thread. Returns the HTTP URL."""
    global _inject_callback
    if inject_callback is not None:
        _inject_callback = inject_callback
    server = ThreadingHTTPServer(("0.0.0.0", port), _HealthHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    print(f"[HEALTH] Endpoint de salud iniciado en puerto {port}"
          + (" (+ /chat)" if _inject_callback else ""))
    return f"http://{_get_local_ip()}:{port}"


def broadcast(text: str):
    """No-op: el chat móvil fue eliminado."""
    return
