"""
mcp_bridge.py — Puente de ERIS con servidores MCP estándar.

Conecta automáticamente los servidores configurados en memory/mcp_config.json
y registra sus tools en el tool_registry de ERIS, para que Eris las use como
herramientas directas (y el LLM las vea como tool calls propias).
"""
from __future__ import annotations

import json
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_CONFIG = _BASE / "memory" / "mcp_config.json"

_bridged: dict = {}  # nombre_tool → server


def load_config() -> dict:
    try:
        if _CONFIG.exists():
            return json.loads(_CONFIG.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"standard_servers": []}


def bridge_standard_tools(silent: bool = False) -> list:
    """Conecta los servers estándar habilitados y registra sus tools en ERIS.

    Returns una lista de {server, tool, registered}.
    """
    global _bridged
    results = []
    cfg = load_config()
    servers = cfg.get("standard_servers", [])
    for s in servers:
        if not s.get("enabled", True):
            continue
        name = s.get("name", "")
        command = s.get("command", "")
        if not name or not command:
            continue
        try:
            from actions.mcp_standard import connect_standard, list_tools
            connect_standard(name, command, s.get("args", []))
            tools = list_tools(name)
        except Exception as e:
            if not silent:
                results.append({"server": name, "error": str(e)[:150]})
            continue
        for t in tools:
            tname = t.get("name", "")
            if not tname:
                continue
            # Tool con prefijo del server para evitar colisiones
            eris_name = f"mcp_{name}_{tname}" if not tname.startswith("mcp_") else tname

            def _make(server=name, tool_name=tname):
                def _call(parameters=None, player=None, **kw):
                    try:
                        args = parameters or {}
                        if isinstance(args, str):
                            args = json.loads(args)
                    except Exception:
                        args = {}
                    from actions.mcp_standard import call_tool
                    r = call_tool(server, tool_name, args if isinstance(args, dict) else {})
                    return str(r)[:2000]
                _call.__name__ = tool_name
                return _call

            try:
                from core.tool_registry import register_tool
                register_tool(eris_name, _make())
                _bridged[eris_name] = name
                results.append({"server": name, "tool": eris_name, "registered": True})
            except Exception:
                pass
    return results


def add_server(name: str, command: str, args: list = None, enabled: bool = True) -> str:
    """Agrega/configura un servidor MCP estándar y lo conecta al instante."""
    cfg = load_config()
    servers = cfg.setdefault("standard_servers", [])
    for i, s in enumerate(servers):
        if s.get("name") == name:
            servers[i] = {"name": name, "command": command, "args": args or [], "enabled": enabled}
            break
    else:
        servers.append({"name": name, "command": command, "args": args or [], "enabled": enabled})
    _CONFIG.parent.mkdir(parents=True, exist_ok=True)
    _CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    res = bridge_standard_tools(silent=True)
    return f"Servidor '{name}' configurado. Tools bridged: {len([r for r in res if r.get('registered')])}"


def estado() -> dict:
    config = load_config()
    try:
        from actions.mcp_standard import get_status
        status = get_status()
    except Exception as e:
        status = f"n/a: {e}"
    return {
        "servers_config": config.get("standard_servers", []),
        "bridged": len(_bridged),
        "tools_bridged": sorted(_bridged.keys()),
        "estado_servers": status,
    }


def mcp_bridge(parameters=None, player=None) -> str:
    """Tool puente MCP: bridge (conecta y expone tools MCP como propias), add_server, estado."""
    try:
        params = json.loads(parameters) if isinstance(parameters, str) else (parameters or {})
    except Exception:
        params = {}
    action = (params.get("action") or "estado").lower()
    if action in ("bridge", "connect", "conectar", "run"):
        res = bridge_standard_tools()
        reg = [r for r in res if r.get("registered")]
        return {"bridged": reg, "errores": [r for r in res if r.get("error")],
                "mensaje": f"{len(reg)} tool(s) MCP ahora son de ERIS." if reg else
                "No hay servers MCP configurados/activos todavía."}
    if action in ("add_server", "add", "agregar"):
        return {"status": add_server(params.get("name", ""), params.get("command", ""),
                                     params.get("args") or []), "name": params.get("name", "")}
    if action == "estado":
        return estado()
    return {"error": f"Acción desconocida: {action}. Acciones: bridge, add_server, estado."}


if __name__ == "__main__":
    print(json.dumps(estado(), ensure_ascii=False, indent=2))