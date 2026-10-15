"""
server_forge.py — Crear y levantar servidores/APIs locales propios (diseño §8).

Eris expone algo PROPIO (una API chica, un servicio local) usando solo la
biblioteca estándar, siguiendo el patrón de `core/vrm_server.py` y
`core/opencode_bridge.py`. Para CONSUMIR APIs externas se usa lo que ya existe
(web/ConnectorHub); esto es para exponer.

- Escucha en `127.0.0.1` por defecto. Otra interfaz = zona protegida → el
  `permission_gate` la corta antes de llegar acá (se evalúa el campo `host`).
- Registro propio `data/servers.json` (runtime, gitignore).
- Ciclo de vida: crear / levantar / estado / parar / borrar, con `health`
  (`GET /health` → 200) como EVIDENCIA dura para el bucle (§5.6).
"""
from __future__ import annotations

import json
import os
import re
import signal
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_STATE_FILE = _BASE / "data" / "servers.json"
_SERVERS_DIR = _BASE / "data" / "servers"
_HOST_DEFECTO = "127.0.0.1"

_ESTADOS = {"creado", "corriendo", "detenido", "error"}


# ─────────────────────────── estado ──────────────────────────────────────────

def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _load() -> dict:
    try:
        if _STATE_FILE.exists():
            data = json.loads(_STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("servers"), list):
                return data
    except Exception:
        pass
    return {"servers": [], "updated_at": ""}


def _save(state: dict) -> None:
    try:
        _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        state["updated_at"] = _now()
        _STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2),
                               encoding="utf-8")
    except Exception:
        pass


def _safe_name(raw: str) -> str:
    return re.sub(r"[^a-z0-9_\-]", "", (raw or "").lower().strip().replace(" ", "_"))


def _get(state: dict, name: str) -> dict | None:
    name = _safe_name(name)
    for s in state["servers"]:
        if s.get("name") == name:
            return s
    return None


def _free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind((_HOST_DEFECTO, 0))
        return s.getsockname()[1]
    finally:
        s.close()


def _pid_vivo(pid) -> bool:
    try:
        pid = int(pid)
    except Exception:
        return False
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except Exception:
        return False


def health(name_or_port, host: str = _HOST_DEFECTO, timeout: float = 1.5) -> dict:
    """GET /health → evidencia. Acepta nombre o (puerto)."""
    port = name_or_port
    if isinstance(name_or_port, str) and not str(name_or_port).isdigit():
        s = _get(_load(), name_or_port)
        if not s:
            return {"ok": False, "error": f"No existe el servidor '{name_or_port}'."}
        port = s.get("port")
        host = s.get("host") or host
    url = f"http://{host}:{int(port)}/health"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            body = r.read(400).decode("utf-8", "replace")
            return {"ok": r.status == 200, "status": r.status, "url": url, "body": body}
    except Exception as e:
        return {"ok": False, "url": url, "error": f"{type(e).__name__}: {str(e)[:160]}"}


# ─────────────────────── generación de código ────────────────────────────────

_TEMPLATE = '''#!/usr/bin/env python3
"""__NAME__ — servidor HTTP local creado por Eris (server_forge).
__DESCRIPCION__
Escucha en __HOST__:__PORT__. /health responde 200 (evidencia del motor).
"""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROUTES = __ROUTES__


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "ErisServerForge/1.0"

    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else str(body).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _dispatch(self, metodo):
        path = (self.path or "/").split("?")[0]
        if path != "/":
            path = path.rstrip("/") or "/"
        if path == "/health":
            self._send(200, json.dumps({"status": "ok", "server": "__NAME__"}))
            return
        r = ROUTES.get(metodo + " " + path)
        if r:
            self._send(200, r.get("body", ""), r.get("content_type", "application/json"))
        else:
            self._send(404, json.dumps({"error": "not found", "path": path}))

    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(("__HOST__", __PORT__), Handler).serve_forever()
'''


def _rutas_normalizadas(rutas) -> dict:
    """Normaliza a {"GET /x": {"body":..., "content_type":...}}."""
    out: dict = {}
    for r in (rutas or []):
        if not isinstance(r, dict):
            continue
        path = str(r.get("path") or r.get("ruta") or "/").strip() or "/"
        if not path.startswith("/"):
            path = "/" + path
        metodo = str(r.get("metodo") or r.get("method") or "GET").upper()
        if metodo not in ("GET", "POST"):
            metodo = "GET"
        body = r.get("body")
        if body is None:
            body = r.get("respuesta") or r.get("respuesta_texto") or ""
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False)
        out[f"{metodo} {path}"] = {
            "body": str(body),
            "content_type": str(r.get("content_type") or ("application/json"
                             if str(r.get("body") or r.get("respuesta") or "").strip().startswith(("{", "["))
                             else "text/plain; charset=utf-8")),
        }
    return out


def crear(name: str, rutas=None, host: str = _HOST_DEFECTO, port: int = 0,
          descripcion: str = "") -> dict:
    """Genera el script del servidor (NO lo levanta). Devuelve la info."""
    name = _safe_name(name)
    if not name:
        return {"error": "Falta un nombre válido para el servidor."}
    state = _load()
    if _get(state, name):
        return {"error": f"Ya existe el servidor '{name}'. Usá `levantar`, `borrar` o elegí otro nombre."}
    host = (host or _HOST_DEFECTO).strip() or _HOST_DEFECTO
    try:
        port = int(port or 0)
    except Exception:
        port = 0
    if port <= 0:
        port = _free_port()
    _SERVERS_DIR.mkdir(parents=True, exist_ok=True)
    file_path = _SERVERS_DIR / f"{name}.py"
    code = (_TEMPLATE
            .replace("__NAME__", name)
            .replace("__DESCRIPCION__", (descripcion or "").strip())
            .replace("__HOST__", host)
            .replace("__PORT__", str(port))
            .replace("__ROUTES__", json.dumps(_rutas_normalizadas(rutas), ensure_ascii=False, indent=2)))
    try:
        file_path.write_text(code, encoding="utf-8")
        import py_compile
        py_compile.compile(str(file_path), doraise=True)
    except Exception as e:
        file_path.unlink(missing_ok=True)
        return {"error": f"El servidor generado no compila: {e}"}

    s = {"name": name, "host": host, "port": port, "path": str(file_path),
         "pid": 0, "health": "no_probado", "estado": "creado",
         "descripcion": descripcion, "created": _now()}
    state["servers"] = [x for x in state["servers"] if x.get("name") != name]
    state["servers"].append(s)
    _save(state)
    return {"status": "creado", "tipo": "server", "name": name, "host": host,
            "port": port, "path": str(file_path),
            "modo_uso": f'Levantalo con server_forge action="levantar" name="{name}"'}


def levantar(name: str, esperar: float = 4.0) -> dict:
    """Levanta el servidor en un proceso propio y espera a que /health responda."""
    state = _load()
    s = _get(state, name)
    if not s:
        return {"error": f"No existe el servidor '{name}'. Creálo primero."}
    if _pid_vivo(s.get("pid")) and health(s["name"]).get("ok"):
        return {"status": "ya_corriendo", "name": s["name"], "port": s["port"],
                "pid": s.get("pid"), "health": "ok"}

    log_path = _SERVERS_DIR / f"{s['name']}.log"
    try:
        with open(log_path, "ab") as logf:
            proc = subprocess.Popen(
                [sys.executable, s["path"]],
                stdout=logf, stderr=subprocess.STDOUT,
                start_new_session=True,
            )
    except Exception as e:
        s["estado"] = "error"
        s["health"] = f"error_arranque: {e}"
        _save(state)
        return {"error": f"No pude levantar '{s['name']}': {e}"}

    s["pid"] = proc.pid
    s["estado"] = "corriendo"
    s["levantado"] = _now()
    # Esperar el health (evidencia real, no la palabra de Eris).
    h = {"ok": False}
    fin = time.time() + max(0.5, float(esperar))
    while time.time() < fin:
        if proc.poll() is not None:
            break
        h = health(s["name"])
        if h.get("ok"):
            break
        time.sleep(0.2)
    s["health"] = "ok" if h.get("ok") else f"sin_health: {h.get('error', '')[:120]}"
    _save(state)
    if h.get("ok"):
        return {"status": "corriendo", "name": s["name"], "host": s["host"],
                "port": s["port"], "pid": s["pid"], "health": "ok",
                "health_url": f"http://{s['host']}:{s['port']}/health"}
    return {"status": "levantado_sin_health", "name": s["name"], "port": s["port"],
            "pid": s["pid"], "health": s["health"]}


def estado(name: str = "") -> dict:
    state = _load()
    if name:
        s = _get(state, name)
        if not s:
            return {"error": f"No existe el servidor '{name}'."}
        s = dict(s)
        s["proceso_vivo"] = _pid_vivo(s.get("pid"))
        s["health_ahora"] = health(s["name"]).get("ok")
        return s
    out = []
    for s in state["servers"]:
        out.append({"name": s["name"], "port": s["port"],
                    "vivo": _pid_vivo(s.get("pid")), "health": s.get("health")})
    return {"servers": out, "total": len(out)}


def parar(name: str) -> dict:
    state = _load()
    s = _get(state, name)
    if not s:
        return {"error": f"No existe el servidor '{name}'."}
    pid = s.get("pid")
    if _pid_vivo(pid):
        try:
            os.killpg(os.getpgid(int(pid)), signal.SIGTERM)
        except Exception:
            try:
                os.kill(int(pid), signal.SIGTERM)
            except Exception:
                pass
        for _ in range(15):
            if not _pid_vivo(pid):
                break
            time.sleep(0.2)
    s["pid"] = 0
    s["estado"] = "detenido"
    s["health"] = "detenido"
    _save(state)
    return {"status": "detenido", "name": s["name"]}


def borrar(name: str) -> dict:
    state = _load()
    s = _get(state, name)
    if not s:
        return {"error": f"No existe el servidor '{name}'."}
    parar(s["name"])
    try:
        Path(s["path"]).unlink(missing_ok=True)
        (_SERVERS_DIR / f"{s['name']}.log").unlink(missing_ok=True)
    except Exception:
        pass
    state = _load()
    state["servers"] = [x for x in state["servers"] if x.get("name") != _safe_name(name)]
    _save(state)
    return {"status": "borrado", "name": _safe_name(name)}


def buscar(query: str = "") -> list[dict]:
    """Busca un servidor propio por nombre/descripción (para no recrear de más)."""
    q = (query or "").lower().strip()
    out = []
    for s in _load()["servers"]:
        blob = f"{s.get('name','')} {s.get('descripcion','')}".lower()
        if not q or q in blob:
            out.append({"name": s.get("name"), "port": s.get("port"),
                        "estado": s.get("estado"), "path": s.get("path")})
    return out


# ─────────────────────────────── tool ────────────────────────────────────────

def server_forge(parameters: dict = None, player=None) -> str:
    """Tool `server_forge`: crear / levantar / estado / parar / borrar / health."""
    params = parameters or {}
    action = str(params.get("action") or "estado").strip().lower()
    name = params.get("name") or params.get("nombre") or ""

    if action in ("crear", "nuevo"):
        rutas = params.get("rutas") or params.get("routes") or []
        if isinstance(rutas, str):
            try:
                rutas = json.loads(rutas)
            except Exception:
                rutas = []
        r = crear(name, rutas=rutas,
                  host=params.get("host") or _HOST_DEFECTO,
                  port=params.get("port") or 0,
                  descripcion=params.get("descripcion") or params.get("description") or "")
        if r.get("error"):
            return f"⚠️ {r['error']}"
        return (f"🧩 Servidor '{r['name']}' creado en {r['path']} "
                f"(http://{r['host']}:{r['port']}). {r['modo_uso']}.")

    if action in ("levantar", "start", "iniciar"):
        r = levantar(name)
        if r.get("error"):
            return f"⚠️ {r['error']}"
        if r.get("health") == "ok":
            return (f"🟢 Servidor '{r['name']}' levantado (pid {r['pid']}) — /health 200 en "
                    f"{r.get('health_url')}.")
        return f"🟠 '{r['name']}' levantado sin health todavía ({r.get('health')})."

    if action in ("parar", "stop", "detener"):
        r = parar(name)
        return f"⚠️ {r['error']}" if r.get("error") else f"🔴 Servidor '{r['name']}' detenido."

    if action in ("borrar", "delete"):
        r = borrar(name)
        return f"⚠️ {r['error']}" if r.get("error") else f"🗑️ Servidor '{r['name']}' borrado."

    if action in ("health", "salud"):
        h = health(name)
        return (f"💚 {h.get('url')} → {h.get('status')}" if h.get("ok")
                else f"🔴 Sin health: {h.get('error')}")

    # default: estado
    e = estado(name)
    if e.get("error"):
        return f"⚠️ {e['error']}"
    if name:
        return (f"🧩 {e['name']}: {e['estado']} | host {e['host']} puerto {e['port']} | "
                f"vivo={e['proceso_vivo']} health={e['health_ahora']}")
    if not e.get("servers"):
        return "No hay servidores propios creados todavía."
    lineas = [f"· {s['name']} :{s['port']} vivo={s['vivo']} health={s['health']}"
              for s in e["servers"]]
    return f"🧩 Servidores propios ({e['total']}):\n" + "\n".join(lineas)


# Alias para el registro de tools
server_forge_tool = server_forge
