"""
ERIS MCP Server — Exponer tools de Eris como servidor MCP (Model Context Protocol).
Permite que otros agents/LLMs usen las tools de Eris vía JSON-RPC.
"""
import json
import sys
import time
from pathlib import Path
from typing import Any

_SERVER_INFO = {
    "name": "eris-mcp-server",
    "version": "1.0.0",
    "description": "Eris AI Assistant — MCP Server exposing all 370+ tools",
}


def _get_tool_list() -> list:
    """Get all registered tools as MCP tool definitions."""
    try:
        from core.tool_declarations import TOOL_DECLARATIONS
        return [
            {
                "name": t["name"],
                "description": t["description"],
                "inputSchema": t["parameters"],
            }
            for t in TOOL_DECLARATIONS
        ]
    except Exception:
        return []


def _call_tool(name: str, arguments: dict) -> str:
    """Call a tool by name."""
    try:
        from core.tool_registry import get_tool_fn
        fn = get_tool_fn(name)
        if fn is None:
            return json.dumps({"error": f"Tool '{name}' not found"})
        return fn(parameters=arguments)
    except Exception as e:
        return json.dumps({"error": str(e)[:500]})


def handle_jsonrpc(request: dict) -> dict:
    """Handle a JSON-RPC 2.0 request."""
    method = request.get("method", "")
    params = request.get("params", {})
    req_id = request.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": _SERVER_INFO,
            },
        }
    elif method == "tools/list":
        tools = _get_tool_list()
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": tools}}
    elif method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        result = _call_tool(tool_name, arguments)
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"content": [{"type": "text", "text": result}]},
        }
    elif method == "ping":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}
    elif method == "notifications/initialized":
        return None  # notification, no response
    else:
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Method not found: {method}"}}


def run_stdio_server():
    """Run MCP server over stdio (for local integration)."""
    print(f"[MCP] Starting {_SERVER_INFO['name']} v{_SERVER_INFO['version']}", file=sys.stderr)
    print("[MCP] Listening on stdin/stdout", file=sys.stderr)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            response = handle_jsonrpc(request)
            if response is not None:
                print(json.dumps(response), flush=True)
        except json.JSONDecodeError as e:
            error_resp = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": f"Parse error: {e}"}}
            print(json.dumps(error_resp), flush=True)
        except Exception as e:
            error_resp = {"jsonrpc": "2.0", "id": None, "error": {"code": -32603, "message": str(e)}}
            print(json.dumps(error_resp), flush=True)


def mcp_server_tool(parameters: dict = None, player=None) -> str:
    """Tool entry point — for when Gemini calls this tool."""
    params = parameters or {}
    action = params.get("action", "status").lower()

    if action == "status":
        tools = _get_tool_list()
        return f"MCP Server: {_SERVER_INFO['name']} v{_SERVER_INFO['version']}\nTools disponibles: {len(tools)}\nModo: stdio JSON-RPC 2.0"

    elif action == "start":
        return "Para iniciar el MCP server, ejecutá: python -m core.mcp_server (stdio mode). Integrá con Claude Desktop o cualquier MCP client."

    elif action == "tools":
        tools = _get_tool_list()
        return f"Tools MCP ({len(tools)}):\n" + "\n".join(f"  - {t['name']}: {t['description'][:80]}" for t in tools[:30]) + ("\n  ..." if len(tools) > 30 else "")

    elif action == "call":
        tool_name = params.get("tool_name", "")
        tool_args = json.loads(params.get("tool_args", "{}")) if params.get("tool_args") else {}
        if not tool_name:
            return "Necesito 'tool_name'."
        result = _call_tool(tool_name, tool_args)
        return f"Tool '{tool_name}' resultado:\n{result[:2000]}"

    return f"Acción '{action}' no reconocida. Usa: status, start, tools, call"
