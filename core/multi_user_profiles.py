"""
ERIS Multi-User Profiles — Distintos usuarios con permisos, personalidad, y contexto separado.
"""
import json
import time
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "user_profiles"
_DATA_DIR.mkdir(parents=True, exist_ok=True)

_PROFILES_FILE = _DATA_DIR / "profiles.json"
_CURRENT_FILE = _DATA_DIR / "current_user.json"

DEFAULT_PERMISSIONS = ["chat", "tools", "voice", "files", "browser", "code_sandbox"]
ADMIN_PERMISSIONS = DEFAULT_PERMISSIONS + ["config", "users", "delete"]


def _load_profiles() -> dict:
    if _PROFILES_FILE.exists():
        with open(_PROFILES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"users": {}, "default_user": "daniel"}


def _save_profiles(data: dict):
    with open(_PROFILES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _load_current() -> str:
    if _CURRENT_FILE.exists():
        with open(_CURRENT_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("user", "daniel")
    return "daniel"


def _save_current(user: str):
    with open(_CURRENT_FILE, "w", encoding="utf-8") as f:
        json.dump({"user": user, "switched_at": time.strftime("%Y-%m-%d %H:%M:%S")}, f)


def create_user(name: str, display_name: str = None, role: str = "user",
                personality_notes: str = "", permissions: list = None) -> dict:
    profiles = _load_profiles()
    key = name.lower().strip()
    if key in profiles["users"]:
        return {"ok": False, "error": f"User '{name}' already exists."}
    profiles["users"][key] = {
        "name": name,
        "display_name": display_name or name,
        "role": role,
        "permissions": permissions or (ADMIN_PERMISSIONS if role == "admin" else DEFAULT_PERMISSIONS),
        "personality_notes": personality_notes,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "last_seen": None,
        "interaction_count": 0,
    }
    _save_profiles(profiles)
    return {"ok": True, "user": name}


def switch_user(name: str) -> dict:
    profiles = _load_profiles()
    key = name.lower().strip()
    if key not in profiles["users"]:
        return {"ok": False, "error": f"User '{name}' not found."}
    profiles["users"][key]["last_seen"] = time.strftime("%Y-%m-%d %H:%M:%S")
    profiles["users"][key]["interaction_count"] += 1
    _save_profiles(profiles)
    _save_current(key)
    return {"ok": True, "user": profiles["users"][key]["display_name"], "role": profiles["users"][key]["role"]}


def get_current_user() -> dict:
    profiles = _load_profiles()
    current = _load_current()
    user = profiles["users"].get(current, {})
    return {"user": user.get("display_name", current), "role": user.get("role", "unknown"),
            "permissions": user.get("permissions", []), "personality": user.get("personality_notes", "")}


def list_users() -> list:
    profiles = _load_profiles()
    return [{"name": u["display_name"], "role": u["role"], "interactions": u["interaction_count"],
             "last_seen": u.get("last_seen", "never")} for u in profiles["users"].values()]


def delete_user(name: str) -> dict:
    profiles = _load_profiles()
    key = name.lower().strip()
    if key in profiles["users"]:
        del profiles["users"][key]
        _save_profiles(profiles)
        return {"ok": True, "deleted": name}
    return {"ok": False, "error": "User not found."}


def multi_user_tool(parameters: dict = None, player=None) -> str:
    """Tool entry point."""
    params = parameters or {}
    action = params.get("action", "current").lower()

    if action == "current":
        user = get_current_user()
        return f"Usuario actual: {user['user']} (rol: {user['role']}, permisos: {', '.join(user['permissions'])})"

    elif action == "list":
        users = list_users()
        if not users:
            return "No hay usuarios registrados."
        return "Usuarios:\n" + "\n".join(f"  - {u['name']} ({u['role']}, {u['interactions']} interacciones)" for u in users)

    elif action == "switch":
        name = params.get("name", "")
        if not name:
            return "Necesito 'name' para cambiar usuario."
        result = switch_user(name)
        return f"Cambiado a: {result['user']} ({result['role']})" if result["ok"] else result["error"]

    elif action == "create":
        name = params.get("name", "")
        if not name:
            return "Necesito 'name' para crear usuario."
        result = create_user(
            name=name,
            display_name=params.get("display_name"),
            role=params.get("role", "user"),
            personality_notes=params.get("personality", ""),
        )
        return f"Usuario '{name}' creado." if result["ok"] else result["error"]

    elif action == "delete":
        name = params.get("name", "")
        result = delete_user(name)
        return f"Usuario '{name}' eliminado." if result["ok"] else result["error"]

    return f"Acción '{action}' no reconocida. Usa: current, list, switch, create, delete"
