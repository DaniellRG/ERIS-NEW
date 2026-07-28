"""
theme_manager.py — Gestión de temas: Dark/Light mode para la UI de ERIS.
Guarda preferencia del usuario y aplica colores consistentes.
"""
import json
from pathlib import Path
from datetime import datetime

_BASE = Path(__file__).resolve().parent.parent
_THEME_FILE = _BASE / "config" / "theme.json"

THEMES = {
    "dark": {
        "name": "Dark Mode",
        "bg_primary": "#1a1a2e",
        "bg_secondary": "#16213e",
        "bg_tertiary": "#0f3460",
        "text_primary": "#e0e0e0",
        "text_secondary": "#b0b0b0",
        "accent": "#4FC3F7",
        "accent_hover": "#29B6F6",
        "success": "#81C784",
        "warning": "#FFB74D",
        "error": "#E57373",
        "border": "#2a2a4a",
        "scrollbar": "#3a3a5a",
        "input_bg": "#1e1e3e",
        "orb_bg": "#0a0a1e",
    },
    "light": {
        "name": "Light Mode",
        "bg_primary": "#f5f5f5",
        "bg_secondary": "#ffffff",
        "bg_tertiary": "#e8e8e8",
        "text_primary": "#212121",
        "text_secondary": "#616161",
        "accent": "#1976D2",
        "accent_hover": "#1565C0",
        "success": "#388E3C",
        "warning": "#F57C00",
        "error": "#D32F2F",
        "border": "#e0e0e0",
        "scrollbar": "#bdbdbd",
        "input_bg": "#ffffff",
        "orb_bg": "#e3f2fd",
    },
    "midnight": {
        "name": "Midnight Blue",
        "bg_primary": "#0d1117",
        "bg_secondary": "#161b22",
        "bg_tertiary": "#21262d",
        "text_primary": "#c9d1d9",
        "text_secondary": "#8b949e",
        "accent": "#58a6ff",
        "accent_hover": "#79c0ff",
        "success": "#3fb950",
        "warning": "#d29922",
        "error": "#f85149",
        "border": "#30363d",
        "scrollbar": "#484f58",
        "input_bg": "#0d1117",
        "orb_bg": "#010409",
    },
    "sunset": {
        "name": "Sunset Warm",
        "bg_primary": "#2d1b33",
        "bg_secondary": "#3d2547",
        "bg_tertiary": "#4a2d57",
        "text_primary": "#f0e6f6",
        "text_secondary": "#c8a8d8",
        "accent": "#ff6b9d",
        "accent_hover": "#ff8fb5",
        "success": "#6bcb77",
        "warning": "#ffd93d",
        "error": "#ff6b6b",
        "border": "#5a3d6a",
        "scrollbar": "#6a4d7a",
        "input_bg": "#2a1830",
        "orb_bg": "#1a0b22",
    },
    "forest": {
        "name": "Forest Green",
        "bg_primary": "#1a2e1a",
        "bg_secondary": "#1e3a1e",
        "bg_tertiary": "#2a4a2a",
        "text_primary": "#d0e8d0",
        "text_secondary": "#90b890",
        "accent": "#4CAF50",
        "accent_hover": "#66BB6A",
        "success": "#81C784",
        "warning": "#AED581",
        "error": "#E57373",
        "border": "#3a5a3a",
        "scrollbar": "#4a6a4a",
        "input_bg": "#162816",
        "orb_bg": "#0a1a0a",
    },
}


def theme_manager(parameters: dict = None, player=None) -> str:
    """Gestión de temas."""
    params = parameters or {}
    action = params.get("action", "status").lower()

    if action == "set":
        return _set_theme(params)
    elif action == "get":
        return _get_current_theme()
    elif action == "list":
        return _list_themes()
    elif action == "preview":
        return _preview_theme(params)
    elif action == "custom":
        return _create_custom(params)
    elif action == "reset":
        return _reset_theme()
    elif action == "status":
        return _get_status()
    elif action == "css":
        return _get_css()
    return "Acciones: set, get, list, preview, custom, reset, status, css"


def _set_theme(params: dict) -> str:
    name = params.get("theme", "").lower()
    if not name:
        return "Error: se requiere 'theme'. Usa: " + ", ".join(THEMES.keys())
    if name not in THEMES:
        return "Tema '{}' no encontrado. Disponibles: {}".format(name, ", ".join(THEMES.keys()))
    _save({"current": name, "changed_at": datetime.now().isoformat()})
    return "Tema cambiado a: {} ({})".format(name, THEMES[name]["name"])


def _get_current_theme() -> str:
    config = _load()
    current = config.get("current", "dark")
    theme = THEMES.get(current, THEMES["dark"])
    lines = ["═══ TEMA ACTUAL: {} ═══".format(theme["name"]), ""]
    for k, v in theme.items():
        if k != "name":
            lines.append("  {:20s} {}".format(k, v))
    return "\n".join(lines)


def _list_themes() -> str:
    config = _load()
    current = config.get("current", "dark")
    lines = ["═══ TEMAS DISPONIBLES ═══", ""]
    for key, theme in THEMES.items():
        marker = " ← ACTUAL" if key == current else ""
        lines.append("  {:15s} {}{}".format(key, theme["name"], marker))
        lines.append("    Accent: {} | BG: {}".format(theme["accent"], theme["bg_primary"]))
        lines.append("")
    return "\n".join(lines)


def _preview_theme(params: dict) -> str:
    name = params.get("theme", "")
    if name not in THEMES:
        return "Tema no encontrado: {}".format(name)
    theme = THEMES[name]
    lines = ["═══ PREVIEW: {} ═══".format(theme["name"]), ""]
    for k, v in theme.items():
        if k != "name":
            lines.append("  {:20s} {}".format(k, v))
    lines.append("")
    lines.append("  Para aplicar: set theme='{}'".format(name))
    return "\n".join(lines)


def _create_custom(params: dict) -> str:
    custom = {}
    for key in ["bg_primary", "bg_secondary", "text_primary", "text_secondary", "accent"]:
        val = params.get(key, "")
        if val:
            custom[key] = val
    if not custom:
        return "Error: proveer al menos un color (bg_primary, accent, etc.)"
    current = _load()
    custom_theme = {**THEMES.get(current.get("current", "dark"), THEMES["dark"]), **custom}
    custom_theme["name"] = "Custom"
    THEMES["custom"] = custom_theme
    _save({"current": "custom", "changed_at": datetime.now().isoformat()})
    return "Tema custom creado y aplicado"


def _reset_theme() -> str:
    _save({"current": "dark", "changed_at": datetime.now().isoformat()})
    return "Tema reseteado a: dark"


def _get_status() -> str:
    config = _load()
    current = config.get("current", "dark")
    theme = THEMES.get(current, THEMES["dark"])
    return "Tema: {} ({}), cambiado: {}".format(
        current, theme["name"], config.get("changed_at", "nunca"))


def _get_css() -> str:
    config = _load()
    current = config.get("current", "dark")
    theme = THEMES.get(current, THEMES["dark"])
    css = "/* ERIS Theme: {} */\n".format(theme["name"])
    css += ":root {\n"
    for k, v in theme.items():
        if k != "name":
            css += "  --eris-{}: {};\n".format(k, v)
    css += "}\n"
    css += ".eris-bg { background-color: var(--eris-bg-primary); }\n"
    css += ".eris-text { color: var(--eris-text-primary); }\n"
    css += ".eris-accent { color: var(--eris-accent); }\n"
    css += ".eris-button { background: var(--eris-accent); color: white; border-radius: 8px; padding: 8px 16px; }\n"
    css += ".eris-input { background: var(--eris-input_bg); color: var(--eris-text-primary); border: 1px solid var(--eris-border); border-radius: 6px; padding: 8px; }\n"
    return css


def _load() -> dict:
    if _THEME_FILE.exists():
        try:
            return json.loads(_THEME_FILE.read_text(encoding="utf-8"))
        except:
            pass
    return {"current": "dark"}


def _save(data: dict):
    _THEME_FILE.parent.mkdir(parents=True, exist_ok=True)
    _THEME_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
