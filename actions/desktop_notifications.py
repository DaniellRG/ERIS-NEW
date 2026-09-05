"""
desktop_notifications.py — Notificaciones de escritorio nativas para ERIS.
Soporta Windows toast notifications, prioridades, agrupación.
"""
import json
import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime

_IS_LINUX = sys.platform.startswith("linux")

_BASE = Path(__file__).resolve().parent.parent
_NOTIF_FILE = _BASE / "data" / "desktop_notifications.json"
_NOTIFICATIONS = []


def desktop_notifications(parameters: dict = None, player=None) -> str:
    """Notificaciones de escritorio."""
    params = parameters or {}
    action = params.get("action", "send").lower()

    if action == "send":
        return _send_notification(params)
    elif action == "send_many":
        return _send_many(params)
    elif action == "status":
        return _get_status()
    elif action == "history":
        return _get_history()
    elif action == "clear_history":
        return _clear_history()
    elif action == "settings":
        return _get_settings()
    elif action == "set_settings":
        return _set_settings(params)
    elif action == "test":
        return _test_notification()
    elif action == "pending":
        return _get_pending()
    elif action == "cancel":
        return _cancel_notification(params)
    elif action == "categories":
        return _get_categories()
    elif action == "set_category":
        return _set_category(params)
    return "Acciones: send, send_many, status, history, clear_history, settings, set_settings, test, pending, cancel, categories, set_category"


def _send_notification(params: dict) -> str:
    title = params.get("title", "ERIS")
    message = params.get("message", "")
    priority = params.get("priority", "normal")
    category = params.get("category", "general")
    silent = params.get("silent", False)

    if not message:
        return "Error: se requiere 'message'"

    notif = {
        "id": len(_NOTIFICATIONS) + 1,
        "title": title,
        "message": message,
        "priority": priority,
        "category": category,
        "silent": silent,
        "timestamp": datetime.now().isoformat(),
        "delivered": False,
    }

    delivered = _deliver(title, message, priority, silent)
    notif["delivered"] = delivered
    _NOTIFICATIONS.append(notif)
    _save_history()

    status = "entregada" if delivered else "en cola"
    return "Notificación {}: '{}' [{}]".format(status, title, priority)


def _send_many(params: dict) -> str:
    notifications = params.get("notifications", [])
    if not notifications:
        return "Error: se requiere 'notifications' (lista)"
    results = []
    for n in notifications:
        r = _send_notification(n)
        results.append(r)
    return "Enviadas: {}/{} notificaciones".format(
        sum(1 for r in results if "entregada" in r), len(results))


def _deliver(title: str, message: str, priority: str, silent: bool) -> bool:
    """Envía la notificación con el backend nativo de la plataforma."""
    if _IS_LINUX:
        return _deliver_linux(title, message, priority, silent)
    return _deliver_windows(title, message, priority, silent)


def _deliver_linux(title: str, message: str, priority: str, silent: bool) -> bool:
    """Envía notificación vía notify-send (libnotify)."""
    try:
        urgency = {
            "low": "low", "normal": "normal", "high": "critical",
            "critical": "critical", "urgent": "critical",
        }.get((priority or "normal").lower(), "normal")
        cmd = ["notify-send", "-a", "Eris", "-u", urgency, title, message]
        if silent:
            cmd += ["--hint", "int:transient:1"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
        return result.returncode == 0
    except Exception:
        return False


def _deliver_windows(title: str, message: str, priority: str, silent: bool) -> bool:
    """Envía notificación toast en Windows."""
    try:
        ps_script = """
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom, ContentType = WindowsRuntime] | Out-Null

$template = @"
<toast>
    <visual>
        <binding template="ToastGeneric">
            <text>{title}</text>
            <text>{message}</text>
        </binding>
    </visual>
    <audio src="ms-winsoundevent:Notification.Default"/>
</toast>
"@

$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
$xml.LoadXml($template)

$toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("ERIS").Show($toast)
""".format(title=title.replace("'", "''"), message=message.replace("'", "''"))

        result = subprocess.run(
            ["powershell", "-Command", ps_script],
            capture_output=True, text=True, timeout=10,
        )
        return result.returncode == 0
    except Exception:
        return False


def _test_notification() -> str:
    return _send_notification({
        "title": "ERIS Test",
        "message": "Esta es una notificacion de prueba. Si la ves, funciona!",
        "priority": "normal",
    })


def _get_status() -> str:
    settings = _load_settings()
    total = len(_NOTIFICATIONS)
    delivered = sum(1 for n in _NOTIFICATIONS if n.get("delivered"))
    lines = [
        "═══ DESKTOP NOTIFICATIONS STATUS ═══",
        "",
        "  Plataforma:    Linux (notify-send)" if _IS_LINUX else "  Plataforma:    Windows (Toast)",
        "  Habilitado:    {}".format("Si" if settings.get("enabled", True) else "No"),
        "  Sonido:        {}".format("Si" if settings.get("sound", True) else "No"),
        "  Total enviadas: {}".format(total),
        "  Entregadas:    {}".format(delivered),
        "  Cola:          {}".format(total - delivered),
    ]
    return "\n".join(lines)


def _get_history() -> str:
    if not _NOTIFICATIONS:
        return "Sin historial de notificaciones"
    lines = ["═══ HISTORIAL DE NOTIFICACIONES ═══", ""]
    for n in _NOTIFICATIONS[-15:]:
        status = "✓" if n.get("delivered") else "⏳"
        lines.append("  [{}] {} — '{}' [{}]".format(
            status, n.get("timestamp", "?")[:19],
            n.get("title", "?"), n.get("priority", "?")))
        lines.append("    {}".format(n.get("message", "")[:80]))
    return "\n".join(lines)


def _clear_history() -> str:
    count = len(_NOTIFICATIONS)
    _NOTIFICATIONS.clear()
    _save_history()
    return "Historial limpiado: {} notificaciones".format(count)


def _get_settings() -> str:
    s = _load_settings()
    lines = [
        "═══ CONFIGURACIÓN DE NOTIFICACIONES ═══",
        "",
        "  Enabled:   {}".format(s.get("enabled", True)),
        "  Sound:     {}".format(s.get("sound", True)),
        "  Priority:  {}".format(s.get("default_priority", "normal")),
    ]
    return "\n".join(lines)


def _set_settings(params: dict) -> str:
    s = _load_settings()
    for key in ["enabled", "sound", "default_priority"]:
        if key in params:
            s[key] = params[key]
    _save_settings(s)
    return "Settings actualizados"


def _get_pending() -> str:
    pending = [n for n in _NOTIFICATIONS if not n.get("delivered")]
    if not pending:
        return "Sin notificaciones pendientes"
    lines = ["═══ PENDIENTES ═══", ""]
    for n in pending:
        lines.append("  #{} — '{}' [{}]".format(n["id"], n.get("title"), n.get("priority")))
    return "\n".join(lines)


def _cancel_notification(params: dict) -> str:
    notif_id = params.get("id")
    if notif_id:
        for n in _NOTIFICATIONS:
            if n["id"] == notif_id:
                n["delivered"] = True
                return "Notificación #{} cancelada".format(notif_id)
    return "No encontrada"


def _get_categories() -> str:
    categories = {
        "general": "Notificaciones generales",
        "system": "Alertas del sistema",
        "email": "Notificaciones de email",
        "calendar": "Recordatorios de calendario",
        "backup": "Estado de backups",
        "security": "Alertas de seguridad",
        "learning": "Aprendizaje autónomo",
    }
    lines = ["═══ CATEGORÍAS ═══", ""]
    for cat, desc in categories.items():
        count = sum(1 for n in _NOTIFICATIONS if n.get("category") == cat)
        lines.append("  {:15s} {} ({})".format(cat, desc, count))
    return "\n".join(lines)


def _set_category(params: dict) -> str:
    return "Categoría '{}' configurada".format(params.get("category", "general"))


def _load_settings() -> dict:
    f = _BASE / "config" / "notification_settings.json"
    if f.exists():
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {"enabled": True, "sound": True, "default_priority": "normal"}


def _save_settings(s: dict):
    f = _BASE / "config" / "notification_settings.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(s, indent=2), encoding="utf-8")


def _save_history():
    _NOTIF_FILE.parent.mkdir(parents=True, exist_ok=True)
    _NOTIF_FILE.write_text(json.dumps(_NOTIFICATIONS[-100:], indent=2, ensure_ascii=False), encoding="utf-8")
