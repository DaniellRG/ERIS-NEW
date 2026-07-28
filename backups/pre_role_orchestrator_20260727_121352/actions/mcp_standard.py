"""
mcp_standard.py — Standard MCP (Model Context Protocol) client for ERIS.
Connects to ANY stdio-based MCP server using the official JSON-RPC 2.0 protocol.
Supports: initialize, tools/list, tools/call, resources/list, prompts/list.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Optional

_MCP_CONFIG_PATH = Path(__file__).resolve().parent.parent / "memory" / "mcp_config.json"

_SERVERS: dict[str, dict] = {}  # name -> {process, tools, info}
_SERVER_LOCK = threading.Lock()


class MCPStandardError(Exception):
    pass


def _safe_print(*args, **kwargs):
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        text = " ".join(str(a) for a in args)
        print(text.encode("utf-8", errors="replace").decode("utf-8", errors="replace"), **kwargs)


# ── Config ────────────────────────────────────────────────────────────────────

def load_config() -> dict:
    path = _MCP_CONFIG_PATH
    if not path.exists():
        return {"standard_servers": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        _safe_print(f"[MCP] Config load error: {e}")
        return {"standard_servers": []}


def save_config(cfg: dict):
    _MCP_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    _MCP_CONFIG_PATH.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")


# ── Standard MCP Client ───────────────────────────────────────────────────────

def _next_id() -> int:
    import random
    return random.randint(1, 999999)


def connect_standard(name: str, command: str, args: list[str] | None = None,
                     env: dict[str, str] | None = None, timeout: float = 15.0) -> str:
    """Connect to a standard MCP server via stdio subprocess.
    
    Performs the full JSON-RPC 2.0 initialize handshake (MCP spec 2024-11-05),
    discovers tools, and stores capabilities.
    """
    with _SERVER_LOCK:
        if name in _SERVERS:
            return f"Server '{name}' is already connected."

    args = args or []
    merged_env = {**os.environ, **(env or {})}

    # Start subprocess
    creation_flags = 0
    if sys.platform == "win32":
        creation_flags = subprocess.CREATE_NO_WINDOW

    try:
        proc = subprocess.Popen(
            [command] + args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=merged_env,
            creationflags=creation_flags,
        )
    except FileNotFoundError:
        return f"Command not found: {command}. Make sure it is installed and in PATH."
    except Exception as e:
        return f"Failed to start '{name}': {e}"

    # Initialize handshake
    try:
        init_result = _send_raw(proc, "initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "ERIS", "version": "2.6.0"}
        }, timeout)
    except MCPStandardError as e:
        proc.terminate()
        return f"Initialize handshake failed for '{name}': {e}"
    except Exception as e:
        proc.terminate()
        return f"Connection failed for '{name}': {e}"

    # Send initialized notification (fire-and-forget)
    _send_notification_raw(proc, "notifications/initialized")

    server_info = init_result.get("serverInfo", {})
    srv_name = server_info.get("name", name)
    srv_version = server_info.get("version", "?")
    protocol_ver = init_result.get("protocolVersion", "")
    srv_caps = init_result.get("capabilities", {})

    # Discover tools
    tools_list = []
    try:
        tools_result = _send_raw(proc, "tools/list", {}, timeout)
        tools_list = tools_result.get("tools", [])
    except Exception as e:
        _safe_print(f"[MCP] tools/list failed for '{name}': {e}")

    # Discover resources (optional — short timeout)
    resources_list = []
    try:
        resources_result = _send_raw(proc, "resources/list", {}, 3.0)
        resources_list = resources_result.get("resources", [])
    except Exception as e:
        pass

    # Discover prompts (optional — short timeout)
    prompts_list = []
    try:
        prompts_result = _send_raw(proc, "prompts/list", {}, 3.0)
        prompts_list = prompts_result.get("prompts", [])
    except Exception as e:
        pass

    with _SERVER_LOCK:
        _SERVERS[name] = {
            "process": proc,
            "info": {
                "server_name": srv_name,
                "server_version": srv_version,
                "protocol_version": protocol_ver,
                "capabilities": srv_caps,
            },
            "tools": tools_list,
            "resources": resources_list,
            "prompts": prompts_list,
            "command": command,
            "args": args,
        }

    return (
        f"Connected to MCP server '{srv_name}' v{srv_version}. "
        f"Protocol: {protocol_ver}. "
        f"Tools: {len(tools_list)}, "
        f"Resources: {len(resources_list)}, "
        f"Prompts: {len(prompts_list)}."
    )


def disconnect(name: str) -> str:
    """Disconnect from a standard MCP server."""
    with _SERVER_LOCK:
        entry = _SERVERS.pop(name, None)
    if entry is None:
        return f"Server '{name}' is not connected."
    try:
        entry["process"].terminate()
        entry["process"].wait(timeout=5)
    except Exception:
        try:
            entry["process"].kill()
        except Exception:
            pass
    return f"Disconnected from '{name}'."


def disconnect_all():
    """Disconnect from all standard MCP servers."""
    with _SERVER_LOCK:
        names = list(_SERVERS.keys())
    for name in names:
        disconnect(name)


def get_status(name: str | None = None) -> str:
    """Get status of connected standard servers."""
    with _SERVER_LOCK:
        if name:
            if name not in _SERVERS:
                return f"Server '{name}' is not connected."
            entry = _SERVERS[name]
            info = entry["info"]
            is_alive = entry["process"].poll() is None
            return (
                f"{'RUNNING' if is_alive else 'STOPPED'}: {info.get('server_name', name)} "
                f"v{info.get('server_version', '?')} "
                f"({len(entry['tools'])} tools, "
                f"{len(entry['resources'])} resources, "
                f"{len(entry['prompts'])} prompts)"
            )
        else:
            if not _SERVERS:
                return "No standard MCP servers connected."
            lines = ["Standard MCP Servers:"]
            for sname, entry in sorted(_SERVERS.items()):
                alive = entry["process"].poll() is None
                info = entry["info"]
                lines.append(
                    f"  {sname}: {'RUNNING' if alive else 'STOPPED'} | "
                    f"{info.get('server_name', '?')} v{info.get('server_version', '?')} | "
                    f"{len(entry['tools'])} tools"
                )
            return "\n".join(lines)


def list_tools(name: str) -> list[dict]:
    """List tools from a connected standard server."""
    with _SERVER_LOCK:
        if name not in _SERVERS:
            raise MCPStandardError(f"Server '{name}' not connected.")
        return list(_SERVERS[name].get("tools", []))


def call_tool(name: str, tool_name: str, arguments: dict | None = None) -> str:
    """Call a tool on a connected standard server."""
    arguments = arguments or {}
    with _SERVER_LOCK:
        if name not in _SERVERS:
            return f"Server '{name}' is not connected."
        proc = _SERVERS[name]["process"]
    try:
        result = _send_raw(proc, "tools/call", {
            "name": tool_name,
            "arguments": arguments,
        })
    except MCPStandardError as e:
        return f"Error calling {name}/{tool_name}: {e}"
    except Exception as e:
        return f"Error calling {name}/{tool_name}: {e}"

    # Format result
    content = result.get("content", [])
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                t = item.get("type", "")
                if t == "text":
                    parts.append(item.get("text", ""))
                elif t == "resource":
                    resource = item.get("resource", {})
                    parts.append(str(resource.get("text", resource)))
                else:
                    parts.append(str(item))
            else:
                parts.append(str(item))
        text = "\n".join(parts)
    else:
        text = str(content)

    is_error = result.get("isError", False)
    if is_error:
        return f"[MCP Error] {text}"
    return text if text else f"Tool '{tool_name}' completed (no output)."


def get_all_connected() -> dict:
    """Return all connected servers info (for external use)."""
    with _SERVER_LOCK:
        return dict(_SERVERS)


# ── Auto-connect at startup ───────────────────────────────────────────────────

def auto_connect() -> list[str]:
    """Auto-connect to all enabled standard MCP servers from config."""
    cfg = load_config()
    results = []
    for server in cfg.get("standard_servers", []):
        if not server.get("enabled", True):
            continue
        name = server.get("name", "unknown")
        command = server.get("command", "")
        args = server.get("args", [])
        if not command:
            results.append(f"{name}: no command specified, skipping")
            continue
        msg = connect_standard(name, command, args)
        results.append(f"{name}: {msg}")
    return results


# ── Internal JSON-RPC ─────────────────────────────────────────────────────────

def _readline_with_timeout(stream, timeout: float = 15.0) -> bytes:
    """Read a line from stream with timeout using non-blocking raw IO.
    
    Uses os.set_blocking/os.read on the raw file descriptor to avoid
    leaking daemon threads across timeouts.
    """
    raw = stream.raw  # underlying raw binary stream (FileIO)
    fd = raw.fileno()
    os.set_blocking(fd, False)

    buf = b""
    deadline = time.monotonic() + timeout

    try:
        while time.monotonic() < deadline:
            try:
                chunk = os.read(fd, 4096)
                if not chunk:
                    break
                buf += chunk
                if b"\n" in buf:
                    idx = buf.index(b"\n")
                    return buf[: idx + 1]
            except BlockingIOError:
                time.sleep(0.01)
        if buf:
            return buf
        raise MCPStandardError(f"Read timeout ({timeout}s)")
    finally:
        os.set_blocking(fd, True)


def _send_raw(proc: subprocess.Popen, method: str, params: dict,
              timeout: float = 15.0) -> dict:
    """Send JSON-RPC request, read response line, return result dict."""
    req_id = _next_id()
    request = {
        "jsonrpc": "2.0",
        "id": req_id,
        "method": method,
        "params": params,
    }
    request_bytes = (json.dumps(request) + "\n").encode("utf-8")

    try:
        proc.stdin.write(request_bytes)
        proc.stdin.flush()
    except BrokenPipeError:
        stderr_out = _read_stderr(proc)
        raise MCPStandardError(
            f"Broken pipe (process died). Stderr: {stderr_out[:500]}"
        )
    except Exception as e:
        raise MCPStandardError(f"Write error: {e}")

    # Read response from stdout (with timeout)
    try:
        line = _readline_with_timeout(proc.stdout, timeout)
    except MCPStandardError:
        raise
    except Exception as e:
        raise MCPStandardError(f"Read error: {e}")

    if not line:
        ret = proc.poll()
        stderr_out = _read_stderr(proc)
        raise MCPStandardError(
            f"No response (exit code: {ret}). Stderr: {stderr_out[:500]}"
        )

    try:
        response = json.loads(line.decode("utf-8"))
    except json.JSONDecodeError as e:
        raise MCPStandardError(f"Invalid JSON response: {e} | Raw: {line[:200]}")

    if "error" in response and response["error"] is not None:
        err = response["error"]
        raise MCPStandardError(
            f"MCP error: code={err.get('code')}, message={err.get('message')}"
        )

    return response.get("result", {})


def _send_notification_raw(proc: subprocess.Popen, method: str, params: dict | None = None):
    """Send JSON-RPC notification (no id, no response expected)."""
    notification = {"jsonrpc": "2.0", "method": method}
    if params:
        notification["params"] = params
    try:
        proc.stdin.write((json.dumps(notification) + "\n").encode("utf-8"))
        proc.stdin.flush()
    except Exception:
        pass


def _read_stderr(proc: subprocess.Popen) -> str:
    try:
        return proc.stderr.read().decode("utf-8", errors="replace")
    except Exception:
        return "(could not read stderr)"
