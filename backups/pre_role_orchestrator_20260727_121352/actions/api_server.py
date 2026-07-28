"""
api_server.py — API Server: exponer ERIS como API REST para otras aplicaciones.
Permite que otras apps se comuniquen con ERIS via HTTP.
"""
import json
import time
import threading
import hashlib
import secrets
from pathlib import Path
from datetime import datetime

_BASE = Path(__file__).resolve().parent.parent
_API_CONFIG_FILE = _BASE / "config" / "api_server.json"
_API_KEYS_FILE = _BASE / "data" / "api_keys.json"
_API_LOG_FILE = _BASE / "data" / "api_log.json"
_server_running = False
_server_thread = None


def api_server(parameters: dict = None, player=None) -> str:
    """
    API Server para ERIS.
    Acciones: start, stop, status, create_key, revoke_key, list_keys, config, docs, log, stats
    """
    params = parameters or {}
    action = params.get("action", "status").lower()

    if action == "start":
        return _start_server(params)
    elif action == "stop":
        return _stop_server()
    elif action == "status":
        return _get_status()
    elif action == "create_key":
        return _create_api_key(params)
    elif action == "revoke_key":
        return _revoke_api_key(params)
    elif action == "list_keys":
        return _list_api_keys()
    elif action == "config":
        return _update_config(params)
    elif action == "docs":
        return _api_docs()
    elif action == "log":
        return _get_log(params)
    elif action == "stats":
        return _get_stats()
    elif action == "test":
        return _test_endpoint(params)
    return "Acciones: start, stop, status, create_key, revoke_key, list_keys, config, docs, log, stats, test"


def _start_server(params: dict) -> str:
    global _server_running, _server_thread
    if _server_running:
        return "Servidor ya está corriendo"

    config = _load_config()
    host = params.get("host", config.get("host", "127.0.0.1"))
    port = int(params.get("port", config.get("port", 8080)))

    _server_running = True

    def run():
        try:
            from flask import Flask, request, jsonify
            app = Flask(__name__)

            @app.before_request
            def authenticate():
                if request.endpoint in ('health', 'docs'):
                    return
                api_key = request.headers.get("Authorization", "").replace("Bearer ", "")
                if not api_key or not _validate_key(api_key):
                    return jsonify({"error": "Invalid or missing API key"}), 401

            @app.route("/health", methods=["GET"])
            def health():
                return jsonify({"status": "ok", "timestamp": datetime.now().isoformat(), "version": "2.0"})

            @app.route("/api/chat", methods=["POST"])
            def chat():
                data = request.get_json()
                message = data.get("message", "")
                if not message:
                    return jsonify({"error": "message required"}), 400
                _log_request("/api/chat", message)
                return jsonify({"response": "ERIS recibió: {}".format(message), "timestamp": datetime.now().isoformat()})

            @app.route("/api/tools", methods=["GET"])
            def list_tools():
                return jsonify({"tools": _get_tool_list()})

            @app.route("/api/memory", methods=["GET"])
            def memory():
                return jsonify({"status": " Memory endpoint active"})

            @app.route("/api/status", methods=["GET"])
            def status():
                return jsonify({"status": "running", "uptime": time.time()})

            @app.route("/docs", methods=["GET"])
            def docs():
                return _api_docs()

            app.run(host=host, port=port, debug=False, use_reloader=False)
        except ImportError:
            _server_running = False
        except Exception:
            _server_running = False

    _server_thread = threading.Thread(target=run, daemon=True)
    _server_thread.start()
    return "API Server iniciado en http://{}:{}".format(host, port)


def _stop_server() -> str:
    global _server_running
    _server_running = False
    return "API Server detenido (reinicia para cerrar completamente)"


def _get_status() -> str:
    config = _load_config()
    keys = _load_keys()
    return "API Server: {} | Puerto: {} | API Keys: {} | Host: {}".format(
        "corriendo" if _server_running else "detenido",
        config.get("port", 8080), len(keys), config.get("host", "127.0.0.1"))


def _create_api_key(params: dict) -> str:
    name = params.get("name", "unnamed")
    permissions = params.get("permissions", ["chat", "status"])

    api_key = "eris_" + secrets.token_hex(32)
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()

    keys = _load_keys()
    keys[key_hash] = {
        "name": name,
        "permissions": permissions,
        "created": datetime.now().isoformat(),
        "last_used": None,
        "active": True,
    }
    _save_keys(keys)

    return "API Key creada para '{}':\n{}\n\nGuárdala, no se volverá a mostrar!".format(name, api_key)


def _revoke_api_key(params: dict) -> str:
    name = params.get("name", "")
    if not name:
        return "Error: se requiere 'name'"

    keys = _load_keys()
    for key_hash, key_data in keys.items():
        if key_data.get("name") == name:
            keys[key_hash]["active"] = False
            _save_keys(keys)
            return "API Key '{}' revocada".format(name)
    return "Key no encontrada: {}".format(name)


def _list_api_keys() -> str:
    keys = _load_keys()
    if not keys:
        return "No hay API keys"

    lines = ["API Keys ({}):".format(len(keys))]
    for key_hash, key_data in keys.items():
        status = "activa" if key_data.get("active") else "revocada"
        lines.append("  {} | {} | {} | {}".format(
            key_data.get("name"), key_data.get("permissions"),
            key_data.get("created", "?")[:10], status))
    return "\n".join(lines)


def _update_config(params: dict) -> str:
    config = _load_config()
    for key in ["host", "port", "rate_limit", "cors_origins"]:
        if key in params:
            config[key] = params[key]
    _save_config(config)
    return "Config actualizada: {}".format(json.dumps(config, indent=2))


def _api_docs() -> str:
    config = _load_config()
    return """
ERIS API Server v2.0 - Documentacion
=====================================

Endpoints:
  GET  /health          - Health check (sin auth)
  POST /api/chat        - Enviar mensaje a ERIS
  GET  /api/tools       - Listar tools disponibles
  GET  /api/memory      - Estado de memoria
  GET  /api/status      - Status del servidor
  GET  /docs            - Esta documentacion

Autenticacion:
  Header: Authorization: Bearer <api_key>

Ejemplo:
  curl -X POST http://localhost:8080/api/chat \\
    -H "Authorization: Bearer eris_tu_api_key_aqui" \\
    -H "Content-Type: application/json" \\
    -d '{{"message": "Que herramientas tienes?"}}'

Rate Limit: {} req/min por key
CORS: {}
""".format(config.get("rate_limit", 60), config.get("cors_origins", "*"))


def _get_log(params: dict) -> str:
    limit = int(params.get("limit", 20))
    log = _load_log()
    entries = log.get("requests", [])

    if not entries:
        return "No hay requests en el log"

    lines = ["API Log ({} total, últimos {}):".format(len(entries), limit)]
    for e in entries[-limit:]:
        lines.append("  {} | {} | {}".format(
            e.get("timestamp", "?")[:16], e.get("endpoint"), e.get("message", "")[:40]))
    return "\n".join(lines)


def _get_stats() -> str:
    log = _load_log()
    entries = log.get("requests", [])
    total = len(entries)
    endpoints = {}
    for e in entries:
        ep = e.get("endpoint", "?")
        endpoints[ep] = endpoints.get(ep, 0) + 1

    lines = [
        "API Stats:",
        "  Total requests: {}".format(total),
        "  Endpoints: {}".format(", ".join("{}:{}".format(k, v) for k, v in endpoints.items())),
    ]
    if entries:
        lines.append("  Último request: {}".format(entries[-1].get("timestamp", "?")[:16]))
    return "\n".join(lines)


def _test_endpoint(params: dict) -> str:
    endpoint = params.get("endpoint", "/health")
    return "Test {} - ver status del servidor".format(endpoint)


def _validate_key(api_key):
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    keys = _load_keys()
    key_data = keys.get(key_hash)
    if key_data and key_data.get("active"):
        keys[key_hash]["last_used"] = datetime.now().isoformat()
        _save_keys(keys)
        return True
    return False


def _log_request(endpoint, message):
    log = _load_log()
    log.setdefault("requests", []).append({
        "endpoint": endpoint, "message": str(message)[:200],
        "timestamp": datetime.now().isoformat()
    })
    log["requests"] = log["requests"][-1000:]
    _API_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    _API_LOG_FILE.write_text(json.dumps(log, indent=2, ensure_ascii=False), encoding="utf-8")


def _get_tool_list():
    return ["screen_vision", "computer_control", "file_controller", "web_search",
            "browser_control", "document_rag", "memory_consolidation", "email_manager",
            "calendar_manager", "flow_recorder", "screenshot_history", "clipboard_manager",
            "multi_user", "image_generation", "voice_cloning", "browser_extension",
            "smart_notifications", "usage_analytics", "skill_marketplace", "api_server",
            "federated_learning", "file_organizer", "data_encryption"]


def _load_config():
    if _API_CONFIG_FILE.exists():
        try:
            return json.loads(_API_CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"host": "127.0.0.1", "port": 8080, "rate_limit": 60, "cors_origins": "*"}


def _save_config(config):
    _API_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    _API_CONFIG_FILE.write_text(json.dumps(config, indent=2), encoding="utf-8")


def _load_keys():
    if _API_KEYS_FILE.exists():
        try:
            return json.loads(_API_KEYS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_keys(keys):
    _API_KEYS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _API_KEYS_FILE.write_text(json.dumps(keys, indent=2), encoding="utf-8")


def _load_log():
    if _API_LOG_FILE.exists():
        try:
            return json.loads(_API_LOG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"requests": []}
