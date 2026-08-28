"""
core/tool_creation.py — Creacion de tools nuevas para Eris

Eris crea sus propias herramientas basandose en patrones de uso.
"""
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_MEMORY = _BASE / "memory"
_ACTIONS = _BASE / "actions" / "custom"
_STATE_FILE = _MEMORY / "tool_creation_state.json"
_LOG_FILE = _MEMORY / "tool_creation_log.json"


def _load_state() -> dict:
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"tools_created": 0, "created_list": [], "last_reset": datetime.now().isoformat()}


def _save_state(state: dict):
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def _log(action: str, details: str):
    entry = {"timestamp": datetime.now().isoformat(), "action": action, "details": details[:200]}
    logs = []
    if _LOG_FILE.exists():
        try:
            logs = json.loads(_LOG_FILE.read_text(encoding="utf-8"))
        except Exception:
            logs = []
    logs.append(entry)
    if len(logs) > 50:
        logs = logs[-50:]
    _LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    _LOG_FILE.write_text(json.dumps(logs, indent=2, ensure_ascii=False), encoding="utf-8")


def create_tool(name: str, description: str, functions: list) -> dict:
    """Crea una tool nueva basada en especificaciones."""
    _ACTIONS.mkdir(parents=True, exist_ok=True)

    safe_name = re.sub(r'[^a-z0-9_]', '', name.lower().replace(" ", "_"))
    file_path = _ACTIONS / "{}.py".format(safe_name)

    if file_path.exists():
        return {"error": "Tool ya existe: {}".format(safe_name)}

    func_code = ""
    for func in functions:
        func_name = func.get("name", "process")
        func_code += """
def {name}(parameters=None, player=None):
    \"\"\"{desc}\"\"\"
    params = parameters or {{}}
    # Implementacion basica
    return json.dumps({{"status": "ok", "tool": "{safe_name}", "function": "{name}", "params": params}}, indent=2)
""".format(
            name=func_name,
            desc=func.get("description", ""),
            safe_name=safe_name,
        )

    content = '"""\ncore/custom/{}.py — Tool auto-generada por Eris\n\n{}\n"""\nimport json\n\n'.format(
        safe_name, description
    )
    content += func_code

    content += """
def {safe_name}_tool(parameters=None, player=None):
    params = parameters or {{}}
    action = params.get("action", "status")
    return json.dumps({{"action": action, "tool": "{safe_name}", "status": "active"}}, indent=2)
""".format(safe_name=safe_name)

    file_path.write_text(content, encoding="utf-8")

    try:
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(file_path)],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            file_path.unlink()
            return {"error": "Error de syntax: {}".format(result.stderr[:200])}
    except Exception:
        pass

    state = _load_state()
    state["tools_created"] += 1
    state.setdefault("created_list", []).append({
        "name": safe_name,
        "file": str(file_path),
        "timestamp": datetime.now().isoformat(),
    })
    _save_state(state)
    _log("create_tool", "Tool creada: {}".format(safe_name))

    return {
        "status": "creada",
        "name": safe_name,
        "file": str(file_path),
        "description": description,
    }


def list_custom_tools() -> list:
    """Lista tools personalizadas creadas."""
    if not _ACTIONS.exists():
        return []
    return [{"name": f.stem, "file": str(f)} for f in _ACTIONS.glob("*.py")]


def delete_tool(name: str) -> dict:
    """Elimina una tool personalizada."""
    file_path = _ACTIONS / "{}.py".format(name)
    if not file_path.exists():
        return {"error": "Tool no encontrada"}
    file_path.unlink()
    _log("delete_tool", "Tool eliminada: {}".format(name))
    return {"status": "eliminada", "name": name}


def get_tool_creation_status() -> dict:
    state = _load_state()
    tools = list_custom_tools()
    return {
        "tools_created": state.get("tools_created", 0),
        "custom_tools": len(tools),
        "tools": tools,
    }


def tool_creation_tool(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = params.get("action", "status")

    if action == "status":
        return json.dumps(get_tool_creation_status(), indent=2)
    elif action == "create":
        name = params.get("name", "")
        desc = params.get("description", "")
        if not name:
            return json.dumps({"error": "Nombre requerido"})
        functions = [{"name": "process", "description": desc}]
        return json.dumps(create_tool(name, desc, functions), indent=2)
    elif action == "list":
        return json.dumps({"tools": list_custom_tools()}, indent=2)
    elif action == "delete":
        name = params.get("name", "")
        if not name:
            return json.dumps({"error": "Nombre requerido"})
        return json.dumps(delete_tool(name), indent=2)

    return json.dumps({"error": "Accion desconocida: {}".format(action)})


if __name__ == "__main__":
    print("=== Test Tool Creation ===")
    print(tool_creation_tool({"action": "status"}))
