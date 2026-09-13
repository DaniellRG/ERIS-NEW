"""Servidor HTTP local para el avatar 3D (VRM).

QWebEngineView no puede cargar módulos ES / import maps desde file://
por restricciones CORS de Chromium. Este módulo levanta un servidor HTTP
de un solo hilo (daemon) sobre ``assets/vrm/`` en 127.0.0.1 con puerto
aleatorio, para que viewer.html pueda importar three.js + three-vrm.
"""

import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

_srv_dir = Path(__file__).resolve().parent.parent / "assets" / "vrm"
_lock = threading.Lock()
_state = {"server": None, "port": None}


class _Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args):  # silencio
        pass


def start_vrm_server() -> int:
    """Arranca (si hace falta) el servidor y devuelve el puerto."""
    with _lock:
        if _state["server"] is not None and _state["port"] is not None:
            return _state["port"]
        handler = lambda *a, **kw: _Quiet(*a, directory=str(_srv_dir), **kw)  # noqa: E731
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        _state["server"] = server
        _state["port"] = port
        return port


def vrm_server_url() -> str:
    port = start_vrm_server()
    return f"http://127.0.0.1:{port}/viewer.html"


def stop_vrm_server():
    with _lock:
        if _state["server"] is not None:
            _state["server"].shutdown()
            _state["server"].server_close()
            _state["server"] = None
            _state["port"] = None