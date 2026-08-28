"""
core/mcp_manager.py — MCP (Model Context Protocol) client for ERIS.

Connects to MCP servers via stdio or HTTP, lists their tools,
and calls them. Gives ERIS access to the MCP ecosystem.
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

# ── Configuration ──
MCP_CONFIG_FILE = "config/mcp_servers.json"
_mcp_servers: dict[str, dict] = {}
_mcp_connections: dict[str, _MCPConnection] = {}
_lock = threading.Lock()


class _MCPConnection:
    """Manages a single MCP server connection."""

    def __init__(self, server_id: str, config: dict):
        self.server_id = server_id
        self.config = config
        self._process: subprocess.Popen | None = None
        self._request_id = 0
        self._lock = threading.Lock()
        self._responses: dict[int, Any] = {}
        self._reader_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._initialized = False
        self._tools: list[dict] = []

    def start(self) -> bool:
        """Start the MCP server process."""
        try:
            transport = self.config.get("transport", "stdio")
            if transport == "stdio":
                return self._start_stdio()
            elif transport == "http":
                return self._start_http()
            return False
        except Exception:
            return False

    def _start_stdio(self) -> bool:
        """Start a stdio-based MCP server."""
        command = self.config.get("command", "")
        args = self.config.get("args", [])
        env = {**os.environ, **self.config.get("env", {})}

        if not command:
            return False

        self._process = subprocess.Popen(
            [command] + args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False,
            bufsize=0,
            env=env,
        )

        self._stop_event.clear()
        self._reader_thread = threading.Thread(
            target=self._read_loop, daemon=True, name=f"mcp-{self.server_id}"
        )
        self._reader_thread.start()

        # MCP initialize
        init_resp = self._send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "eris", "version": "2.0"},
        })
        if init_resp is not None:
            self._send_notification("notifications/initialized", {})
            self._initialized = True
            # List tools
            tools_resp = self._send_request("tools/list", {})
            if tools_resp and "tools" in tools_resp:
                self._tools = tools_resp["tools"]
            return True
        return False

    def _start_http(self) -> bool:
        """Connect to an HTTP-based MCP server."""
        url = self.config.get("url", "")
        if not url:
            return False
        # For HTTP, we use a simplified approach
        self._initialized = True
        self._tools = []
        return True

    def _read_loop(self):
        """Background thread reading JSON-RPC messages."""
        try:
            while not self._stop_event.is_set():
                header = self._read_line()
                if not header:
                    break
                content_length = 0
                while header.strip():
                    if header.lower().startswith("content-length:"):
                        content_length = int(header.split(":", 1)[1].strip())
                    header = self._read_line()
                    if not header:
                        break

                if content_length <= 0:
                    continue

                body = self._process.stdout.read(content_length)
                if not body:
                    break

                msg = json.loads(body.decode("utf-8"))
                msg_id = msg.get("id")
                if msg_id is not None:
                    self._responses[msg_id] = msg
        except Exception:
            pass

    def _read_line(self) -> str | None:
        try:
            line = b""
            while True:
                ch = self._process.stdout.read(1)
                if not ch:
                    return None
                if ch == b"\n":
                    return line.decode("utf-8", errors="replace")
                line += ch
        except Exception:
            return None

    def _send_request(self, method: str, params: dict | None = None, timeout: float = 15.0) -> Any:
        with self._lock:
            self._request_id += 1
            req_id = self._request_id

        msg = {"jsonrpc": "2.0", "id": req_id, "method": method}
        if params:
            msg["params"] = params

        self._responses[req_id] = None
        try:
            raw = json.dumps(msg)
            header = f"Content-Length: {len(raw.encode('utf-8'))}\r\n\r\n"
            self._process.stdin.write(header.encode("utf-8") + raw.encode("utf-8"))
            self._process.stdin.flush()
        except Exception:
            return None

        deadline = time.time() + timeout
        while time.time() < deadline:
            if self._responses[req_id] is not None:
                resp = self._responses.pop(req_id)
                if "error" in resp:
                    return None
                return resp.get("result")
            time.sleep(0.01)

        self._responses.pop(req_id, None)
        return None

    def _send_notification(self, method: str, params: dict | None = None):
        msg = {"jsonrpc": "2.0", "method": method}
        if params:
            msg["params"] = params
        try:
            raw = json.dumps(msg)
            header = f"Content-Length: {len(raw.encode('utf-8'))}\r\n\r\n"
            self._process.stdin.write(header.encode("utf-8") + raw.encode("utf-8"))
            self._process.stdin.flush()
        except Exception:
            pass

    def call_tool(self, tool_name: str, arguments: dict) -> str:
        """Call a tool on this MCP server."""
        resp = self._send_request("tools/call", {
            "name": tool_name,
            "arguments": arguments,
        })
        if resp:
            content = resp.get("content", [])
            if isinstance(content, list):
                texts = [c.get("text", str(c)) for c in content if isinstance(c, dict)]
                return "\n".join(texts) if texts else str(resp)
            return str(content)
        return f"Error calling {tool_name}"

    def list_tools(self) -> list[dict]:
        """List available tools."""
        return self._tools

    def stop(self):
        self._stop_event.set()
        if self._process:
            try:
                self._send_request("shutdown", timeout=3.0)
                self._send_notification("notifications/cancelled", {})
            except Exception:
                pass
            try:
                self._process.terminate()
            except Exception:
                pass
        self._initialized = False


def load_mcp_config():
    """Load MCP server configuration from file."""
    global _mcp_servers
    config_path = Path(__file__).parent.parent / MCP_CONFIG_FILE
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                _mcp_servers = json.load(f)
        except Exception:
            _mcp_servers = {}
    else:
        # Create default config
        _mcp_servers = {}
        save_mcp_config()


def save_mcp_config():
    """Save MCP server configuration to file."""
    config_path = Path(__file__).parent.parent / MCP_CONFIG_FILE
    config_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(_mcp_servers, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def _get_connection(server_id: str) -> _MCPConnection | None:
    """Get or create an MCP connection."""
    with _lock:
        if server_id in _mcp_connections and _mcp_connections[server_id]._initialized:
            return _mcp_connections[server_id]

    if server_id not in _mcp_servers:
        return None

    config = _mcp_servers[server_id]
    conn = _MCPConnection(server_id, config)
    if conn.start():
        with _lock:
            _mcp_connections[server_id] = conn
        return conn
    return None


# ── Public API ──

def mcp_add_server(server_id: str, command: str, args: list[str] | None = None,
                   env: dict | None = None, transport: str = "stdio",
                   url: str | None = None) -> str:
    """Add a new MCP server configuration."""
    load_mcp_config()
    config: dict[str, Any] = {"transport": transport}
    if transport == "stdio":
        config["command"] = command
        config["args"] = args or []
        if env:
            config["env"] = env
    elif transport == "http":
        config["url"] = url or ""

    _mcp_servers[server_id] = config
    save_mcp_config()
    return f"MCP server '{server_id}' added"


def mcp_remove_server(server_id: str) -> str:
    """Remove an MCP server."""
    load_mcp_config()
    if server_id in _mcp_servers:
        del _mcp_servers[server_id]
        save_mcp_config()
        # Stop connection if active
        with _lock:
            conn = _mcp_connections.pop(server_id, None)
        if conn:
            conn.stop()
        return f"MCP server '{server_id}' removed"
    return f"Server '{server_id}' not found"


def mcp_list_servers() -> str:
    """List all configured MCP servers and their tools."""
    load_mcp_config()
    if not _mcp_servers:
        return "No MCP servers configured. Use mcp_manage(action='add') to add one."

    lines = []
    for sid, config in _mcp_servers.items():
        transport = config.get("transport", "stdio")
        cmd = config.get("command", config.get("url", "?"))
        status = "disconnected"
        tool_count = 0
        with _lock:
            if sid in _mcp_connections and _mcp_connections[sid]._initialized:
                status = "connected"
                tool_count = len(_mcp_connections[sid]._tools)
        lines.append(f"- {sid}: {cmd} ({transport}) [{status}, {tool_count} tools]")
    return "MCP Servers:\n" + "\n".join(lines)


def mcp_connect(server_id: str) -> str:
    """Connect to an MCP server."""
    conn = _get_connection(server_id)
    if conn:
        tools = conn.list_tools()
        tool_names = [t.get("name", "?") for t in tools]
        return f"Connected to '{server_id}'. Tools: {', '.join(tool_names)}"
    return f"Failed to connect to '{server_id}'"


def mcp_call_tool(server_id: str, tool_name: str, arguments: dict | None = None) -> str:
    """Call a tool on an MCP server."""
    conn = _get_connection(server_id)
    if not conn:
        return f"Server '{server_id}' not connected"
    return conn.call_tool(tool_name, arguments or {})


def mcp_list_tools(server_id: str) -> str:
    """List tools on a specific MCP server."""
    conn = _get_connection(server_id)
    if not conn:
        return f"Server '{server_id}' not connected"
    tools = conn.list_tools()
    if not tools:
        return f"No tools on '{server_id}'"
    lines = []
    for t in tools:
        name = t.get("name", "?")
        desc = t.get("description", "")[:80]
        lines.append(f"- {name}: {desc}")
    return f"Tools on '{server_id}':\n" + "\n".join(lines)


def mcp_disconnect_all():
    """Stop all MCP connections."""
    with _lock:
        for conn in _mcp_connections.values():
            conn.stop()
        _mcp_connections.clear()


# ── Tool handler (called by tool_dispatcher) ──

def mcp_tool(parameters: dict = None, **kwargs) -> str:
    """Unified MCP tool handler."""
    if not parameters:
        return mcp_list_servers()
    action = parameters.get("action", "list")
    server_id = parameters.get("server", "")
    tool_name = parameters.get("tool", "")
    arguments = parameters.get("arguments", {})

    if action == "list":
        return mcp_list_servers()
    elif action == "add":
        command = parameters.get("command", "")
        args = parameters.get("args", [])
        env = parameters.get("env", {})
        transport = parameters.get("transport", "stdio")
        url = parameters.get("url", "")
        if not server_id:
            return "Error: server name required"
        if transport == "stdio" and not command:
            return "Error: command required for stdio transport"
        return mcp_add_server(server_id, command, args if isinstance(args, list) else [],
                              env if isinstance(env, dict) else {}, transport, url)
    elif action == "remove":
        if not server_id:
            return "Error: server name required"
        return mcp_remove_server(server_id)
    elif action == "connect":
        if not server_id:
            return "Error: server name required"
        return mcp_connect(server_id)
    elif action == "tools":
        if not server_id:
            return "Error: server name required"
        return mcp_list_tools(server_id)
    elif action == "call":
        if not server_id or not tool_name:
            return "Error: server and tool name required"
        return mcp_call_tool(server_id, tool_name, arguments)
    elif action == "disconnect":
        mcp_disconnect_all()
        return "All MCP servers disconnected"
    else:
        return f"Unknown MCP action: {action}. Use: list, add, remove, connect, tools, call, disconnect"
