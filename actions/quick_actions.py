"""Quick Actions / Atajos personalizados: macros que ejecutan comandos rapidos."""
import json
import os
from pathlib import Path


CONFIG_DIR = Path(os.environ.get("APPDATA", "")) / "ERIS" / "config"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
ACTIONS_FILE = CONFIG_DIR / "quick_actions.json"


def _load():
    if ACTIONS_FILE.exists():
        try:
            return json.loads(ACTIONS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save(data: dict):
    ACTIONS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def add(parameters: dict = None, player=None) -> str:
    """Crea un nuevo atajo."""
    params = parameters or {}
    name = (params.get("name") or "").strip().lower()
    command = (params.get("command") or "").strip()
    if not name or not command:
        return "Uso: add name=mi_atajo command='el comando a ejecutar'"
    data = _load()
    if name in data:
        return f"El atajo '{name}' ya existe. Usa update para actualizarlo."
    data[name] = {"command": command}
    _save(data)
    return f"Atajo '{name}' creado: {command}"


def update(parameters: dict = None, player=None) -> str:
    """Actualiza un atajo existente."""
    params = parameters or {}
    name = (params.get("name") or "").strip().lower()
    command = (params.get("command") or "").strip()
    if not name or not command:
        return "Uso: update name=mi_atajo command='nuevo comando'"
    data = _load()
    if name not in data:
        return f"El atajo '{name}' no existe. Usa add para crearlo."
    data[name] = {"command": command}
    _save(data)
    return f"Atajo '{name}' actualizado: {command}"


def remove(parameters: dict = None, player=None) -> str:
    """Elimina un atajo."""
    params = parameters or {}
    name = (params.get("name") or "").strip().lower()
    if not name:
        return "Uso: remove name=mi_atajo"
    data = _load()
    if name not in data:
        return f"Atajo '{name}' no encontrado."
    del data[name]
    _save(data)
    return f"Atajo '{name}' eliminado."


def list_actions(parameters: dict = None, player=None) -> str:
    """Lista todos los atajos guardados."""
    data = _load()
    if not data:
        return "No hay atajos guardados. Usa add para crear uno."
    lines = ["Quick Actions guardados:"]
    for name, info in sorted(data.items()):
        lines.append(f"  !{name}  ->  {info['command']}")
    return "\n".join(lines)


def execute(parameters: dict = None, player=None) -> tuple:
    """Ejecuta un atajo y devuelve (result_msg, command_to_inject)."""
    params = parameters or {}
    name = (params.get("name") or "").strip().lower()
    if not name:
        return "Uso: run name=mi_atajo"
    data = _load()
    if name not in data:
        return f"Atajo '{name}' no encontrado."
    cmd = data[name]["command"]
    return None, cmd


def run(parameters: dict = None, player=None) -> str:
    """Wrapper para execute."""
    result = execute(parameters)
    if isinstance(result, tuple):
        _, cmd = result
        return f"Ejecutando atajo: {cmd}"
    return result
