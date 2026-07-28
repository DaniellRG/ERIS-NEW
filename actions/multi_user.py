"""
multi_user.py — Sistema multi-usuario: perfiles diferentes con personalizaciones.
Cada usuario tiene su propia memoria, preferencias, y configuración.
"""
import json
from pathlib import Path
from datetime import datetime

_BASE = Path(__file__).resolve().parent.parent
_PROFILES_DIR = _BASE / "data" / "user_profiles"
_CURRENT_PROFILE_FILE = _BASE / "data" / "current_profile.json"

DEFAULT_PROFILE = {
    "name": "",
    "display_name": "",
    "created": "",
    "language": "es",
    "voice_enabled": True,
    "notifications": True,
    "personality": "amigable",
    "memory_file": "",
    "preferences": {},
    "avatar": "",
    "theme": "default",
    "greeting": "",
    "timezone": "America/Bogota",
}


def multi_user(parameters: dict = None, player=None) -> str:
    """
    Gestión de usuarios/perfiles.
    Acciones: list, create, switch, delete, update, current, info, merge, export, import
    """
    params = parameters or {}
    action = params.get("action", "list").lower()
    _PROFILES_DIR.mkdir(parents=True, exist_ok=True)

    if action == "create":
        return _create_profile(params)
    elif action == "list":
        return _list_profiles()
    elif action == "switch":
        return _switch_profile(params)
    elif action == "delete":
        return _delete_profile(params)
    elif action == "update":
        return _update_profile(params)
    elif action == "current":
        return _current_profile_info()
    elif action == "info":
        return _profile_info(params)
    elif action == "merge":
        return _merge_profiles(params)
    elif action == "export":
        return _export_profile(params)
    elif action == "import":
        return _import_profile(params)
    elif action == "preferences":
        return _set_preferences(params)
    elif action == "stats":
        return _get_stats()
    return "Acciones: list, create, switch, delete, update, current, info, merge, export, import, preferences, stats"


def _list_profiles() -> str:
    profiles = _get_all_profiles()
    if not profiles:
        return "No hay perfiles. Crea uno con action: create"

    current = _get_current_profile_name()
    lines = ["Perfiles ({}):".format(len(profiles))]
    for name, p in profiles.items():
        marker = " [ACTUAL]" if name == current else ""
        lines.append("  {} | {} | Creado: {}{}".format(
            name, p.get("display_name", name), p.get("created", "?")[:10], marker))
    return "\n".join(lines)


def _create_profile(params: dict) -> str:
    name = params.get("name", "").lower().strip()
    if not name:
        return "Error: se requiere 'name'"

    profiles = _get_all_profiles()
    if name in profiles:
        return "Ya existe un perfil con ese nombre: {}".format(name)

    profile = dict(DEFAULT_PROFILE)
    profile["name"] = name
    profile["display_name"] = params.get("display_name", name.title())
    profile["created"] = datetime.now().isoformat()
    profile["language"] = params.get("language", "es")
    profile["personality"] = params.get("personality", "amigable")
    profile["greeting"] = params.get("greeting", "Hola {}! Soy ERIS, tu asistente.".format(
        params.get("display_name", name.title())))
    profile["timezone"] = params.get("timezone", "America/Bogota")

    profiles[name] = profile
    _save_all_profiles(profiles)

    _switch_profile({"name": name})
    return "Perfil '{}' creado. Ahora soy tu asistente personal, {}!".format(
        name, profile["display_name"])


def _switch_profile(params: dict) -> str:
    name = params.get("name", "").lower().strip()
    if not name:
        return "Error: se requiere 'name'"

    profiles = _get_all_profiles()
    if name not in profiles:
        return "Perfil no encontrado: {}. Usa list para ver perfiles".format(name)

    _save_current_profile(name)
    p = profiles[name]
    return "Cambiado a perfil '{}'. {} me recuerda que eres {}".format(
        name, p.get("greeting", "Hola!"), p.get("display_name", name))


def _delete_profile(params: dict) -> str:
    name = params.get("name", "").lower().strip()
    if not name:
        return "Error: se requiere 'name'"

    profiles = _get_all_profiles()
    if name not in profiles:
        return "Perfil no encontrado"

    if name == "default":
        return "No se puede eliminar el perfil default"

    del profiles[name]
    _save_all_profiles(profiles)

    if _get_current_profile_name() == name:
        _save_current_profile("default")

    return "Perfil '{}' eliminado".format(name)


def _update_profile(params: dict) -> str:
    name = params.get("name", _get_current_profile_name())
    profiles = _get_all_profiles()
    if name not in profiles:
        return "Perfil no encontrado: {}".format(name)

    for key in ["display_name", "language", "voice_enabled", "notifications",
                "personality", "avatar", "theme", "greeting", "timezone"]:
        if key in params:
            profiles[name][key] = params[key]

    _save_all_profiles(profiles)
    return "Perfil '{}' actualizado".format(name)


def _current_profile_info() -> str:
    name = _get_current_profile_name()
    profiles = _get_all_profiles()
    if name not in profiles:
        return "No hay perfil activo"

    p = profiles[name]
    lines = [
        "Perfil actual: {}".format(name),
        "  Nombre: {}".format(p.get("display_name", "?")),
        "  Idioma: {}".format(p.get("language", "?")),
        "  Personalidad: {}".format(p.get("personality", "?")),
        "  Zona horaria: {}".format(p.get("timezone", "?")),
        "  Tema: {}".format(p.get("theme", "?")),
        "  Creado: {}".format(p.get("created", "?")[:10]),
        "  Notificaciones: {}".format("sí" if p.get("notifications") else "no"),
        "  Voz: {}".format("activada" if p.get("voice_enabled") else "desactivada"),
    ]
    return "\n".join(lines)


def _profile_info(params: dict) -> str:
    name = params.get("name", _get_current_profile_name())
    profiles = _get_all_profiles()
    if name not in profiles:
        return "Perfil no encontrado: {}".format(name)

    p = profiles[name]
    lines = ["Perfil '{}':".format(name)]
    for k, v in p.items():
        if k != "preferences":
            lines.append("  {}: {}".format(k, str(v)[:100]))
    if p.get("preferences"):
        lines.append("  Preferencias:")
        for k, v in p["preferences"].items():
            lines.append("    {}: {}".format(k, v))
    return "\n".join(lines)


def _set_preferences(params: dict) -> str:
    prefs = params.get("preferences", {})
    if not prefs:
        return "Error: se requiere 'preferences' (dict)"

    name = _get_current_profile_name()
    profiles = _get_all_profiles()
    if name not in profiles:
        return "No hay perfil activo"

    profiles[name].setdefault("preferences", {}).update(prefs)
    _save_all_profiles(profiles)
    return "Preferencias actualizadas para '{}'".format(name)


def _merge_profiles(params: dict) -> str:
    source = params.get("source", "")
    target = params.get("target", "")
    if not source or not target:
        return "Error: se requiere 'source' y 'target'"

    profiles = _get_all_profiles()
    if source not in profiles:
        return "Perfil source no encontrado: {}".format(source)
    if target not in profiles:
        return "Perfil target no encontrado: {}".format(target)

    target_profile = profiles[target]
    source_prefs = profiles[source].get("preferences", {})
    target_profile.setdefault("preferences", {}).update(source_prefs)

    _save_all_profiles(profiles)
    return "Preferencias de '{}' mergeadas en '{}'".format(source, target)


def _export_profile(params: dict) -> str:
    name = params.get("name", _get_current_profile_name())
    profiles = _get_all_profiles()
    if name not in profiles:
        return "Perfil no encontrado"

    export_path = _BASE / "data" / "profile_export_{}.json".format(name)
    export_path.write_text(json.dumps(profiles[name], indent=2, ensure_ascii=False), encoding="utf-8")
    return "Perfil '{}' exportado a {}".format(name, str(export_path))


def _import_profile(params: dict) -> str:
    filepath = params.get("filepath", "")
    if not filepath:
        return "Error: se requiere 'filepath'"
    try:
        data = json.loads(Path(filepath).read_text(encoding="utf-8"))
        name = data.get("name", Path(filepath).stem)
        profiles = _get_all_profiles()
        profiles[name] = data
        _save_all_profiles(profiles)
        return "Perfil '{}' importado".format(name)
    except Exception as e:
        return "Error importando: {}".format(str(e))


def _get_stats() -> str:
    profiles = _get_all_profiles()
    current = _get_current_profile_name()
    total = len(profiles)
    total_prefs = sum(len(p.get("preferences", {})) for p in profiles.values())
    return "Usuarios: {} perfiles | {} preferencias totales | Actual: {}".format(
        total, total_prefs, current or "ninguno")


def _get_all_profiles() -> dict:
    profiles = {}
    for f in _PROFILES_DIR.glob("*.json"):
        try:
            p = json.loads(f.read_text(encoding="utf-8"))
            profiles[p.get("name", f.stem)] = p
        except Exception:
            pass
    default = _PROFILES_DIR / "default.json"
    if not default.exists():
        profile = dict(DEFAULT_PROFILE)
        profile["name"] = "default"
        profile["display_name"] = "Daniel"
        profile["created"] = datetime.now().isoformat()
        _save_profile("default", profile)
        profiles["default"] = profile
    elif "default" not in profiles:
        profiles["default"] = json.loads(default.read_text(encoding="utf-8"))
    return profiles


def _save_all_profiles(profiles: dict):
    _PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    for name, p in profiles.items():
        _save_profile(name, p)


def _save_profile(name: str, profile: dict):
    _PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    path = _PROFILES_DIR / "{}.json".format(name)
    path.write_text(json.dumps(profile, indent=2, ensure_ascii=False), encoding="utf-8")


def _get_current_profile_name() -> str:
    if _CURRENT_PROFILE_FILE.exists():
        try:
            data = json.loads(_CURRENT_PROFILE_FILE.read_text(encoding="utf-8"))
            return data.get("current_profile", "default")
        except Exception:
            pass
    return "default"


def _save_current_profile(name: str):
    _CURRENT_PROFILE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _CURRENT_PROFILE_FILE.write_text(json.dumps({"current_profile": name}, indent=2), encoding="utf-8")
