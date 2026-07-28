"""
browser_extension.py — Conexión con navegador del usuario: recibir datos, controlar pestañas, etc.
Funciona como un mini-servidor WebSocket que la extensión del navegador conecta.
"""
import json
import time
import threading
from pathlib import Path
from datetime import datetime

_BASE = Path(__file__).resolve().parent.parent
_BROWSER_DATA = _BASE / "data" / "browser_data.json"
_EXTENSION_LOG = _BASE / "data" / "browser_extension_log.json"
_connections = {}
_server_running = False


def browser_extension(parameters: dict = None, player=None) -> str:
    """
    Conexión con navegador.
    Acciones: start, stop, status, tabs, active_tab, navigate, get_page, search_history,
              bookmarks, screenshot_tab, send_to_eris, execute_js, close_tab
    """
    params = parameters or {}
    action = params.get("action", "status").lower()

    if action == "start":
        return _start_server(params)
    elif action == "stop":
        return _stop_server()
    elif action == "status":
        return _get_status()
    elif action == "tabs":
        return _list_tabs()
    elif action == "active_tab":
        return _get_active_tab()
    elif action == "navigate":
        return _navigate(params)
    elif action == "get_page":
        return _get_page_content(params)
    elif action == "search_history":
        return _search_history(params)
    elif action == "bookmarks":
        return _get_bookmarks()
    elif action == "screenshot_tab":
        return _screenshot_tab(params)
    elif action == "send_to_eris":
        return _send_to_eris(params)
    elif action == "execute_js":
        return _execute_js(params)
    elif action == "close_tab":
        return _close_tab(params)
    elif action == "open_url":
        return _open_url(params)
    elif action == "get_history":
        return _get_history(params)
    elif action == "highlight":
        return _highlight_element(params)
    return "Acciones: start, stop, status, tabs, active_tab, navigate, get_page, search_history, bookmarks, send_to_eris, execute_js, open_url, get_history"


def _start_server(params: dict) -> str:
    global _server_running
    if _server_running:
        return "Servidor ya está corriendo"

    port = int(params.get("port", 8765))
    _server_running = True

    def run_server():
        try:
            import websockets
            import asyncio

            async def handler(websocket, path):
                _connections[str(id(websocket))] = websocket
                try:
                    async for message in websocket:
                        data = json.loads(message)
                        _process_browser_message(data)
                except Exception:
                    pass
                finally:
                    _connections.pop(str(id(websocket)), None)

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            start_server = websockets.serve(handler, "localhost", port)
            loop.run_until_complete(start_server)
            loop.run_forever()
        except ImportError:
            _server_running = False
        except Exception:
            _server_running = False

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    return "Servidor WebSocket iniciado en puerto {}. Instala la extensión ERIS en tu navegador".format(port)


def _stop_server() -> str:
    global _server_running
    _server_running = False
    _connections.clear()
    return "Servidor detenido"


def _get_status() -> str:
    return "Browser Extension: {} | Conexiones: {} | Puerto: 8765".format(
        "activo" if _server_running else "inactivo", len(_connections))


def _list_tabs() -> str:
    if not _connections:
        return "No hay navegador conectado. Instala la extensión ERIS"
    return "Tabs conectados: {}".format(len(_connections))


def _get_active_tab() -> str:
    data = _load_data()
    active = data.get("active_tab", {})
    if not active:
        return "No hay pestaña activa registrada"
    return "Tab activa: {} | {}".format(active.get("title", "?"), active.get("url", "?"))


def _navigate(params: dict) -> str:
    url = params.get("url", "")
    if not url:
        return "Error: se requiere 'url'"
    _send_command({"action": "navigate", "url": url})
    return "Navegando a: {}".format(url)


def _get_page_content(params: dict) -> str:
    _send_command({"action": "get_content"})
    data = _load_data()
    content = data.get("page_content", "")
    if content:
        return "Contenido de página ({} chars): {}".format(len(content), content[:2000])
    return "No hay contenido disponible"


def _search_history(params: dict) -> str:
    query = params.get("query", "")
    if not query:
        return "Error: se requiere 'query'"
    _send_command({"action": "search_history", "query": query})
    data = _load_data()
    results = data.get("history_results", [])
    if not results:
        return "No se encontraron resultados para: {}".format(query)
    lines = ["Historial para '{}':".format(query)]
    for r in results[:10]:
        lines.append("  {} | {}".format(r.get("title", "?")[:40], r.get("url", "?")[:60]))
    return "\n".join(lines)


def _get_bookmarks() -> str:
    _send_command({"action": "get_bookmarks"})
    data = _load_data()
    bookmarks = data.get("bookmarks", [])
    if not bookmarks:
        return "No hay bookmarks disponibles"
    lines = ["Bookmarks ({}):".format(len(bookmarks))]
    for b in bookmarks[:20]:
        lines.append("  {} | {}".format(b.get("title", "?")[:40], b.get("url", "?")[:60]))
    return "\n".join(lines)


def _screenshot_tab(params: dict) -> str:
    _send_command({"action": "screenshot"})
    data = _load_data()
    screenshot = data.get("last_screenshot")
    if screenshot:
        return "Screenshot guardado: {}".format(screenshot)
    return "No se pudo tomar screenshot"


def _send_to_eris(params: dict) -> str:
    content = params.get("content", "")
    if not content:
        return "Error: se requiere 'content'"
    _send_command({"action": "send_to_eris", "content": content})
    return "Contenido enviado a ERIS"


def _execute_js(params: dict) -> str:
    code = params.get("code", "")
    if not code:
        return "Error: se requiere 'code'"
    _send_command({"action": "execute_js", "code": code})
    return "JavaScript enviado para ejecutar"


def _close_tab(params: dict) -> str:
    tab_id = params.get("tab_id", "")
    if not tab_id:
        return "Error: se requiere 'tab_id'"
    _send_command({"action": "close_tab", "tab_id": tab_id})
    return "Pestaña {} cerrada".format(tab_id)


def _open_url(params: dict) -> str:
    url = params.get("url", "")
    if not url:
        return "Error: se requiere 'url'"
    _send_command({"action": "open_url", "url": url})
    return "Abriendo: {}".format(url)


def _get_history(params: dict) -> str:
    days = int(params.get("days", 7))
    _send_command({"action": "get_history", "days": days})
    data = _load_data()
    history = data.get("browser_history", [])
    if not history:
        return "No hay historial disponible"
    lines = ["Historial (últimos {} días, {} entradas):".format(days, len(history))]
    for h in history[:15]:
        lines.append("  {} | {} | {}".format(
            h.get("timestamp", "?")[:10], h.get("title", "?")[:40], h.get("url", "?")[:50]))
    return "\n".join(lines)


def _highlight_element(params: dict) -> str:
    selector = params.get("selector", "")
    if not selector:
        return "Error: se requiere 'selector'"
    _send_command({"action": "highlight", "selector": selector})
    return "Elemento '{}' resaltado".format(selector)


def _process_browser_message(data):
    stored = _load_data()
    stored.update(data)
    stored["last_update"] = datetime.now().isoformat()
    _save_data(stored)


def _send_command(command):
    if not _connections:
        return
    try:
        import asyncio
        for conn_id, ws in list(_connections.items()):
            try:
                asyncio.get_event_loop().run_until_complete(ws.send(json.dumps(command)))
            except Exception:
                pass
    except Exception:
        pass


def _load_data():
    if _BROWSER_DATA.exists():
        try:
            return json.loads(_BROWSER_DATA.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_data(data):
    _BROWSER_DATA.parent.mkdir(parents=True, exist_ok=True)
    _BROWSER_DATA.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
