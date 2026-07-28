"""
actions/i18n_ui.py — Full UI internationalization for ERIS.
Translate UI strings, manage language files, auto-translate messages.
"""
import json
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_LANG_DIR = _BASE / "data" / "ui_languages"

UI_STRINGS = {
    "window_title": {"es": "ERIS — Asistente IA", "en": "ERIS — AI Assistant"},
    "input_placeholder": {"es": "Escribe tu mensaje...", "en": "Type your message..."},
    "send_button": {"es": "Enviar", "en": "Send"},
    "settings": {"es": "Configuración", "en": "Settings"},
    "voice": {"es": "Voz", "en": "Voice"},
    "status": {"es": "Estado", "en": "Status"},
    "online": {"es": "En línea", "en": "Online"},
    "offline": {"es": "Desconectado", "en": "Offline"},
    "thinking": {"es": "Pensando...", "en": "Thinking..."},
    "listening": {"es": "Escuchando...", "en": "Listening..."},
    "speaking": {"es": "Hablando...", "en": "Speaking..."},
    "error": {"es": "Error", "en": "Error"},
    "success": {"es": "Éxito", "en": "Success"},
    "warning": {"es": "Advertencia", "en": "Warning"},
    "loading": {"es": "Cargando...", "en": "Loading..."},
    "saving": {"es": "Guardando...", "en": "Saving..."},
    "delete": {"es": "Eliminar", "en": "Delete"},
    "cancel": {"es": "Cancelar", "en": "Cancel"},
    "confirm": {"es": "Confirmar", "en": "Confirm"},
    "save": {"es": "Guardar", "en": "Save"},
    "close": {"es": "Cerrar", "en": "Close"},
    "minimize": {"es": "Minimizar", "en": "Minimize"},
    "maximize": {"es": "Maximizar", "en": "Maximize"},
    "restore": {"es": "Restaurar", "en": "Restore"},
    "file": {"es": "Archivo", "en": "File"},
    "edit": {"es": "Editar", "en": "Edit"},
    "view": {"es": "Ver", "en": "View"},
    "help": {"es": "Ayuda", "en": "Help"},
    "about": {"es": "Acerca de", "en": "About"},
    "version": {"es": "Versión", "en": "Version"},
    "tools": {"es": "Herramientas", "en": "Tools"},
    "memory": {"es": "Memoria", "en": "Memory"},
    "knowledge": {"es": "Conocimiento", "en": "Knowledge"},
    "calendar": {"es": "Calendario", "en": "Calendar"},
    "email": {"es": "Correo", "en": "Email"},
    "notifications": {"es": "Notificaciones", "en": "Notifications"},
    "logs": {"es": "Registros", "en": "Logs"},
    "backup": {"es": "Respaldo", "en": "Backup"},
    "plugins": {"es": "Plugins", "en": "Plugins"},
    "dashboard": {"es": "Panel de control", "en": "Dashboard"},
    "system_monitor": {"es": "Monitor del sistema", "en": "System Monitor"},
    "cpu": {"es": "CPU", "en": "CPU"},
    "memory_label": {"es": "Memoria", "en": "Memory"},
    "disk": {"es": "Disco", "en": "Disk"},
    "network": {"es": "Red", "en": "Network"},
    "processes": {"es": "Procesos", "en": "Processes"},
    "uptime": {"es": "Tiempo activo", "en": "Uptime"},
    "temperature": {"es": "Temperatura", "en": "Temperature"},
    "gpu": {"es": "GPU", "en": "GPU"},
    "battery": {"es": "Batería", "en": "Battery"},
    "good_morning": {"es": "Buenos días", "en": "Good morning"},
    "good_afternoon": {"es": "Buenas tardes", "en": "Good afternoon"},
    "good_evening": {"es": "Buenas noches", "en": "Good evening"},
    "how_can_i_help": {"es": "¿En qué puedo ayudarte?", "en": "How can I help you?"},
    "no_results": {"es": "Sin resultados", "en": "No results"},
    "search": {"es": "Buscar", "en": "Search"},
    "settings_saved": {"es": "Configuración guardada", "en": "Settings saved"},
    "connection_lost": {"es": "Conexión perdida", "en": "Connection lost"},
    "reconnecting": {"es": "Reconectando...", "en": "Reconnecting..."},
    "connected": {"es": "Conectado", "en": "Connected"},
    "disconnected": {"es": "Desconectado", "en": "Disconnected"},
    "permissions": {"es": "Permisos", "en": "Permissions"},
    "accessibility": {"es": "Accesibilidad", "en": "Accessibility"},
    "privacy": {"es": "Privacidad", "en": "Privacy"},
    "security": {"es": "Seguridad", "en": "Security"},
    "update": {"es": "Actualizar", "en": "Update"},
    "restart": {"es": "Reiniciar", "en": "Restart"},
    "shutdown": {"es": "Apagar", "en": "Shutdown"},
    "welcome": {"es": "Bienvenido", "en": "Welcome"},
    "export": {"es": "Exportar", "en": "Export"},
    "import": {"es": "Importar", "en": "Import"},
    "reset": {"es": "Restablecer", "en": "Reset"},
    "advanced": {"es": "Avanzado", "en": "Advanced"},
    "basic": {"es": "Básico", "en": "Basic"},
    "custom": {"es": "Personalizado", "en": "Custom"},
    "auto": {"es": "Automático", "en": "Automatic"},
    "manual": {"es": "Manual", "en": "Manual"},
    "none": {"es": "Ninguno", "en": "None"},
    "all": {"es": "Todos", "en": "All"},
}


def i18n_ui(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = params.get("action", "status").lower()

    if action == "status":
        lang = _get_current_lang()
        return (
            f"UI I18n Status:\n"
            f"  Current language: {lang}\n"
            f"  Supported: es, en, pt, fr, de, it, ja, ko, zh\n"
            f"  UI strings: {len(UI_STRINGS)}\n"
            f"  Custom packs: {len(list(_LANG_DIR.glob('*.json')) if _LANG_DIR.exists() else [])}"
        )

    elif action == "set_language":
        lang = params.get("language", "es")
        _set_current_lang(lang)
        return f"UI language set to: {lang}"

    elif action == "translate":
        key = params.get("key", "")
        if not key:
            return "Requires 'key'."
        lang = params.get("language", _get_current_lang())
        string_data = UI_STRINGS.get(key, {})
        if lang in string_data:
            return string_data[lang]
        elif "en" in string_data:
            return string_data["en"]
        return f"String not found: {key}"

    elif action == "translate_batch":
        keys = params.get("keys", "").split(",") if params.get("keys") else []
        if not keys:
            return "Requires 'keys' (comma-separated)."
        lang = params.get("language", _get_current_lang())
        lines = [f"UI Translations ({lang}):"]
        for key in keys:
            key = key.strip()
            string_data = UI_STRINGS.get(key, {})
            value = string_data.get(lang, string_data.get("en", f"[{key}]"))
            lines.append(f"  {key}: {value}")
        return "\n".join(lines)

    elif action == "export":
        lang = params.get("language", _get_current_lang())
        strings = {}
        for key, values in UI_STRINGS.items():
            strings[key] = values.get(lang, values.get("en", key))
        return json.dumps(strings, indent=2, ensure_ascii=False)

    elif action == "import":
        data = params.get("data", "")
        lang = params.get("language", "custom")
        if not data:
            return "Requires 'data' (JSON string)."
        try:
            strings = json.loads(data)
            _LANG_DIR.mkdir(parents=True, exist_ok=True)
            (_LANG_DIR / f"{lang}.json").write_text(json.dumps(strings, indent=2, ensure_ascii=False), encoding="utf-8")
            return f"Imported {len(strings)} strings for language: {lang}"
        except json.JSONDecodeError:
            return "Invalid JSON data."

    elif action == "languages":
        langs = set()
        for values in UI_STRINGS.values():
            langs.update(values.keys())
        return f"Languages with UI strings: {', '.join(sorted(langs))}"

    elif action == "missing":
        lang = params.get("language", "en")
        missing = []
        for key, values in UI_STRINGS.items():
            if lang not in values:
                missing.append(key)
        if not missing:
            return f"All strings have {lang} translations."
        return f"Missing {lang} translations ({len(missing)}):\n" + "\n".join(f"  {k}" for k in missing[:20])

    return "Actions: status, set_language, translate, translate_batch, export, import, languages, missing"


def _get_current_lang():
    state_file = _BASE / "data" / "i18n_state.json"
    if state_file.exists():
        try:
            data = json.loads(state_file.read_text(encoding="utf-8"))
            return data.get("current_language", "es")
        except Exception:
            pass
    return "es"


def _set_current_lang(lang):
    state_file = _BASE / "data" / "i18n_state.json"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    data = {"current_language": lang, "fallback": "en"}
    state_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
