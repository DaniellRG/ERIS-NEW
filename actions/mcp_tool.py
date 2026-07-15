"""
mcp_tool.py — ERIS MCP tool handler.
Connects to MCP servers (filesystem, web, etc.) via custom and standard MCP clients.
"""
from __future__ import annotations

from actions.mcp_client import (
    discover_servers,
    list_all_tools,
    call_server_tool,
    list_servers,
    shutdown_all,
)

from actions.mcp_standard import (
    connect_standard,
    disconnect as std_disconnect,
    get_status as std_status,
    list_tools as std_list_tools,
    call_tool as std_call_tool,
    auto_connect as std_auto_connect,
    disconnect_all as std_disconnect_all,
    load_config as std_load_config,
    save_config as std_save_config,
)


def mcp_tool(parameters: dict, player=None, **kwargs) -> str:
    """
    Interfaz al Model Context Protocol (MCP). Permite a ERIS conectar
    herramientas externas de forma dinámica.

    Acciones para servidores personalizados (built-in):
      discover | list | call | servers | shutdown

    Acciones para servidores MCP estándar:
      connect_standard | list_standard | call_standard | disconnect | status_standard

    Otras acciones:
      config (ver/editar config de servidores estándar)
    """
    params = parameters or {}
    action = params.get("action", "").lower().strip()

    if not action:
        return "Especificá 'action': discover, list, call, servers, shutdown, connect_standard, list_standard, call_standard, disconnect, status_standard, config."

    # ── Standard MCP actions ──────────────────────────────────────────────

    if action == "connect_standard":
        name = params.get("server", "").strip()
        if not name:
            return "Especificá 'server' con el nombre del servidor a conectar."
        # Try from config first
        cfg = std_load_config()
        server_cfg = None
        for s in cfg.get("standard_servers", []):
            if s.get("name") == name:
                server_cfg = s
                break
        if server_cfg:
            return connect_standard(name, server_cfg.get("command", ""), server_cfg.get("args", []))
        # Inline connect: require command and args in params
        command = params.get("command", "")
        args = params.get("args", [])
        if not command:
            return f"Server '{name}' not found in config. Provide 'command' and 'args', or add it to memory/mcp_config.json first."
        return connect_standard(name, command, args)

    if action == "list_standard":
        name = params.get("server", "").strip()
        if not name:
            return "Especificá 'server'."
        try:
            tools = std_list_tools(name)
            if not tools:
                return f"No tools on '{name}'."
            lines = [f"Tools on '{name}' ({len(tools)}):"]
            for t in tools:
                desc = t.get("description", "")
                schema = t.get("inputSchema", {})
                props = list(schema.get("properties", {}).keys()) if schema else []
                lines.append(f"  - {t['name']}: {desc[:120]}")
                if props:
                    lines.append(f"    Args: {', '.join(props)}")
            return "\n".join(lines)
        except Exception as e:
            return f"Error: {e}"

    if action == "call_standard":
        name = params.get("server", "").strip()
        tool_name = params.get("tool", "").strip()
        call_args = params.get("args", {})
        if not name:
            return "Especificá 'server'."
        if not tool_name:
            return "Especificá 'tool'."
        return std_call_tool(name, tool_name, call_args)

    if action == "disconnect":
        name = params.get("server", "").strip()
        if not name:
            # Disconnect all standard
            std_disconnect_all()
            return "All standard MCP servers disconnected."
        return std_disconnect(name)

    if action == "status_standard":
        name = params.get("server", "").strip()
        return std_status(name if name else None)

    if action == "config":
        sub = params.get("server", "").strip().lower()
        if sub == "list":
            cfg = std_load_config()
            servers = cfg.get("standard_servers", [])
            if not servers:
                return "No standard MCP servers configured. Edit memory/mcp_config.json to add them."
            lines = ["Configured standard MCP servers:"]
            for s in servers:
                enabled = "ON" if s.get("enabled", True) else "OFF"
                cmd = s.get("command", "")
                args_preview = " ".join(s.get("args", []))[:60]
                lines.append(f"  {s['name']} [{enabled}]: {cmd} {args_preview}")
            return "\n".join(lines)
        elif sub == "add":
            name = params.get("tool", "").strip()
            command = params.get("command", "")
            args_list = params.get("args", [])
            if not name or not command:
                return "Specify 'tool' (server name), 'command', and 'args'."
            cfg = std_load_config()
            for s in cfg.get("standard_servers", []):
                if s.get("name") == name:
                    return f"Server '{name}' already in config."
            cfg.setdefault("standard_servers", []).append({
                "name": name, "enabled": True,
                "command": command, "args": args_list,
            })
            std_save_config(cfg)
            return f"Server '{name}' added to config. Use action=connect_standard to connect."
        return "config sub-actions: list, add"

    # ── Custom (built-in) MCP actions ─────────────────────────────────────

    if action == "discover":
        try:
            servers = discover_servers()
            if not servers:
                return "No se encontraron servidores MCP disponibles."
            lines = [f"Servidores MCP descubiertos ({len(servers)}):"]
            for s in servers:
                tools_str = ", ".join(t["name"] for t in s.get("tools", []))
                lines.append(f"  - {s['name']}: {s['description']}")
                if tools_str:
                    lines.append(f"    Herramientas: {tools_str}")
            return "\n".join(lines)
        except Exception as e:
            return f"Error al descubrir servidores MCP: {e}"

    if action == "list":
        try:
            tools = list_all_tools()
            if not tools:
                return "No hay herramientas MCP disponibles. Ejecutá action=discover primero."
            lines = [f"Herramientas MCP disponibles ({len(tools)}):"]
            for t in tools:
                lines.append(f"  - {t['server']}/{t['name']}: {t.get('description', '')[:80]}")
            return "\n".join(lines)
        except Exception as e:
            return f"Error al listar herramientas: {e}"

    if action == "servers":
        try:
            servers = list_servers()
            lines = [f"Estado de servidores MCP ({len(servers)}):"]
            for s in servers:
                status = "activo" if s["running"] else "detenido"
                lines.append(f"  - {s['name']}: {status} ({s['tools']} herramientas)")
            # Also show standard servers
            std_status_text = std_status()
            if "connected" in std_status_text.lower():
                lines.append("")
                lines.append(std_status_text)
            return "\n".join(lines)
        except Exception as e:
            return f"Error: {e}"

    if action == "call":
        server = params.get("server", "").lower().strip()
        tool = params.get("tool", "").strip()
        args = params.get("args", {})
        if not server:
            return "Especificá 'server' (filesystem, web, etc.)"
        if not tool:
            return "Especificá 'tool' (nombre de la herramienta)"
        try:
            return call_server_tool(server, tool, args)
        except Exception as e:
            return f"Error al llamar {server}/{tool}: {e}"

    if action == "shutdown":
        try:
            shutdown_all()
            std_disconnect_all()
            return "Todos los servidores MCP detenidos."
        except Exception as e:
            return f"Error al detener servidores: {e}"

    return f"Acción desconocida: '{action}'. Usar: discover, list, servers, call, shutdown, connect_standard, list_standard, call_standard, disconnect, status_standard, config."
