"""user_profile.py — Clean user habit & configuration recorder."""
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PROFILE_PATH = BASE_DIR / "config" / "user_profile.json"

def user_profile(parameters: dict, player=None) -> str:
    """Manage general user profile variables."""
    action = parameters.get("action", "").lower()
    if action in ("get", "get_profile"):
        profile = _load_profile()
        return f"Perfil del usuario: {json.dumps(profile)}"
    if action == "update":
        key = (parameters.get("key") or "").strip()
        value = parameters.get("value")
        if not key or value is None:
            return "Faltan 'key' y 'value' para actualizar el perfil."
        profile = _load_profile()
        profile[key] = value
        _save_profile(profile)
        return f"Perfil actualizado: {key} = {value}"
    if action == "add_preference":
        category = (parameters.get("category") or "preferencias").strip()
        key = (parameters.get("key") or "").strip()
        value = parameters.get("value")
        if not key or value is None:
            return "Faltan 'key' y 'value' para la preferencia."
        profile = _load_profile()
        prefs = profile.setdefault(category, {})
        prefs[key] = value
        _save_profile(profile)
        return f"Preferencia guardada: {category}.{key} = {value}"
    if action in ("get_habits", "habits"):
        profile = _load_profile()
        habits = profile.get("habits", {})
        if not habits:
            return "Aún no hay hábitos registrados."
        lines = [f"Hábitos registrados ({len(habits)}):"]
        for k, v in sorted(habits.items(), key=lambda x: -x[1]):
            lines.append(f"  - {k}: {v} veces")
        return "\n".join(lines)
    if action == "get_stats":
        profile = _load_profile()
        stats = {
            "campos": sorted(profile.keys()),
            "habitos": len(profile.get("habits", {})),
            "preferencias": sum(1 for k, v in profile.items() if isinstance(v, dict) and k != "habits"),
        }
        return f"Estadísticas del perfil: {json.dumps(stats)}"
    return "Acciones: get_profile, update, add_preference, get_habits, get_stats"

def _load_profile() -> dict:
    if not PROFILE_PATH.exists():
        return {"name": "Sir", "habits": {}}
    try:
        return json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"name": "Sir", "habits": {}}

def _save_profile(profile: dict) -> None:
    try:
        PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        PROFILE_PATH.write_text(json.dumps(profile, indent=2), encoding="utf-8")
    except Exception:
        pass

def record_action(name: str, args: dict) -> None:
    """Log executed actions to track user habits over time."""
    try:
        profile = _load_profile()
        habits = profile.setdefault("habits", {})
        count = habits.get(name, 0)
        habits[name] = count + 1
        _save_profile(profile)
    except Exception:
        pass
