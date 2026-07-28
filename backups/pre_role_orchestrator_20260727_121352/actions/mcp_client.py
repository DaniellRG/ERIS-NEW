"""
mcp_client.py — ERIS MCP (Model Context Protocol) client.
Manages MCP server subprocesses and routes tool calls via JSON-RPC 2.0.
"""
from __future__ import annotations

import json
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Optional

_MCP_DIR = Path(__file__).resolve().parent / "mcp_servers"

# ── Built-in server definitions ───────────────────────────────────────────────

BUILTIN_SERVERS: list[dict] = [
    {
        "name": "filesystem",
        "description": "Operaciones de archivos: leer, escribir, listar, buscar",
        "script": "filesystem_server.py",
    },
    {
        "name": "web",
        "description": "Operaciones web: fetch URL, búsqueda, scraping",
        "script": "web_server.py",
    },
]

# ── Server Process Manager ────────────────────────────────────────────────────


class MCPServerProcess:
    """Manages a single MCP server subprocess."""

    def __init__(self, name: str, script_path: Path):
        self.name = name
        self.script_path = script_path
        self.process: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        self._tools_cache: list[dict] = []
        self._last_used = 0.0

    def start(self) -> str:
        """Start the server subprocess."""
        with self._lock:
            if self.process and self.process.poll() is None:
                return f"Servidor {self.name} ya está ejecutándose."

            try:
                self.process = subprocess.Popen(
                    [sys.executable, str(self.script_path)],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=str(_MCP_DIR),
                )
                # Wait for ready notification
                ready_line = self.process.stdout.readline() if self.process.stdout else ""
                self._last_used = time.time()
                return f"Servidor {self.name} iniciado."
            except Exception as e:
                return f"Error al iniciar {self.name}: {e}"

    def stop(self):
        """Stop the server subprocess."""
        with self._lock:
            if self.process and self.process.poll() is None:
                try:
                    req = {"jsonrpc": "2.0", "id": 999, "method": "shutdown"}
                    self.process.stdin.write(json.dumps(req) + "\n")
                    self.process.stdin.flush()
                except Exception:
                    pass
                try:
                    self.process.terminate()
                    self.process.wait(timeout=3)
                except Exception:
                    try:
                        self.process.kill()
                        self.process.wait(timeout=1)
                    except Exception:
                        pass
                self.process = None

    def _send_request(self, method: str, params: dict = None, timeout: float = 15) -> dict:
        """Send a JSON-RPC request and wait for response."""
        with self._lock:
            if not self.process or self.process.poll() is not None:
                raise RuntimeError(f"Servidor {self.name} no está ejecutándose.")

            req_id = int(time.time() * 1000) % 100000
            req = {"jsonrpc": "2.0", "id": req_id, "method": method}
            if params:
                req["params"] = params

            try:
                self.process.stdin.write(json.dumps(req) + "\n")
                self.process.stdin.flush()
                self._last_used = time.time()

                line = self.process.stdout.readline()
                if not line:
                    raise RuntimeError(f"Servidor {self.name} no respondió (stdout cerrado)")

                resp = json.loads(line.strip())
                if "error" in resp and resp["error"]:
                    error = resp["error"]
                    raise RuntimeError(f"Error del servidor {self.name}: {error.get('message', 'unknown')}")
                return resp.get("result", {})
            except json.JSONDecodeError as e:
                raise RuntimeError(f"Respuesta inválida de {self.name}: {e}")

    def list_tools(self) -> list[dict]:
        """Discover available tools from the server."""
        try:
            result = self._send_request("list_tools")
            tools = result.get("tools", [])
            self._tools_cache = tools
            return tools
        except Exception as e:
            print(f"[MCP] Error listing tools from {self.name}: {e}")
            return self._tools_cache

    def call_tool(self, tool_name: str, arguments: dict = None) -> str:
        """Call a tool on the server."""
        try:
            result = self._send_request("call_tool", {
                "name": tool_name,
                "arguments": arguments or {},
            })
            content = result.get("content", [])
            texts = [c.get("text", "") for c in content if c.get("type") == "text"]
            return "\n".join(texts) if texts else str(result)
        except Exception as e:
            return f"Error calling {self.name}/{tool_name}: {e}"

    def _send_notification(self, method: str, params: dict = None):
        """Send a JSON-RPC notification (no response expected)."""
        if not self.process or self.process.poll() is not None:
            return
        msg = {"jsonrpc": "2.0", "method": method}
        if params:
            msg["params"] = params
        try:
            self.process.stdin.write(json.dumps(msg) + "\n")
            self.process.stdin.flush()
        except Exception:
            pass

    def initialize(self) -> bool:
        """Initialize the server session."""
        try:
            result = self._send_request("initialize", {
                "protocolVersion": "2024-11-05",
                "clientInfo": {"name": "eris", "version": "1.0.0"},
            })
            # Send initialized notification (no response expected)
            self._send_notification("notifications/initialized")
            return bool(result)
        except Exception:
            return False


# ── Global client state ───────────────────────────────────────────────────────

_servers: dict[str, MCPServerProcess] = {}
_server_lock = threading.Lock()
_discovery_done = False


def _get_script_path(server_def: dict) -> Path:
    """Get the path to a server script."""
    return _MCP_DIR / server_def["script"]


def discover_servers() -> list[dict]:
    """Discover and start all available MCP servers. Returns server list."""
    global _discovery_done
    with _server_lock:
        available = []
        for sdef in BUILTIN_SERVERS:
            script = _get_script_path(sdef)
            if not script.exists():
                continue
            name = sdef["name"]
            if name not in _servers:
                proc = MCPServerProcess(name, script)
                msg = proc.start()
                print(f"[MCP] {msg}")
                if proc.process and proc.process.poll() is None:
                    ok = proc.initialize()
                    if ok:
                        tools = proc.list_tools()
                        _servers[name] = proc
                        available.append({
                            "name": name,
                            "description": sdef["description"],
                            "tools": tools,
                        })
                        print(f"[MCP] Servidor '{name}' listo con {len(tools)} herramientas")
            else:
                proc = _servers[name]
                tools = proc.list_tools()
                available.append({
                    "name": name,
                    "description": sdef["description"],
                    "tools": tools,
                })
        _discovery_done = True
        return available


def list_all_tools() -> list[dict]:
    """List all tools across all servers."""
    tools = []
    for name, proc in _servers.items():
        for t in proc._tools_cache:
            tools.append({
                "server": name,
                "name": t["name"],
                "description": t.get("description", ""),
            })
    return tools


def call_server_tool(server_name: str, tool_name: str, arguments: dict = None) -> str:
    """Call a tool on a specific server."""
    with _server_lock:
        if server_name not in _servers:
            # Try to discover
            discover_servers()
        if server_name not in _servers:
            return f"Servidor MCP '{server_name}' no disponible."
        return _servers[server_name].call_tool(tool_name, arguments or {})


def shutdown_all():
    """Stop all server processes."""
    with _server_lock:
        for name, proc in _servers.items():
            proc.stop()
        _servers.clear()
        global _discovery_done
        _discovery_done = False


def list_servers() -> list[dict]:
    """Return status of all servers."""
    available = []
    for sdef in BUILTIN_SERVERS:
        name = sdef["name"]
        if name in _servers:
            proc = _servers[name]
            is_alive = proc.process and proc.process.poll() is None
            available.append({
                "name": name,
                "description": sdef["description"],
                "running": is_alive,
                "tools": len(proc._tools_cache),
            })
        else:
            available.append({
                "name": name,
                "description": sdef["description"],
                "running": False,
                "tools": 0,
            })
    return available
