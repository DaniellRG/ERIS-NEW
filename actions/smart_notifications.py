"""
smart_notifications.py — Notificaciones inteligentes: contextuales, no molestas.
Analiza contexto del usuario para decidir cuándo y cómo notificar.
"""
import json
import time
from pathlib import Path
from datetime import datetime, timedelta

_BASE = Path(__file__).resolve().parent.parent
_NOTIFICATIONS_FILE = _BASE / "data" / "notifications.json"
_NOTIFICATION_CONFIG = _BASE / "data" / "notification_config.json"
_MAX_NOTIFICATIONS = 100


def smart_notifications(parameters: dict = None, player=None) -> str:
    """
    Notificaciones inteligentes.
    Acciones: send, list, settings, clear, history, schedule, cancel, mute, unmute, stats, test
    """
    params = parameters or {}
    action = params.get("action", "list").lower()

    if action == "send":
        return _send_notification(params)
    elif action == "list":
        return _list_notifications(params)
    elif action == "settings":
        return _update_settings(params)
    elif action == "clear":
        return _clear_notifications()
    elif action == "history":
        return _notification_history(params)
    elif action == "schedule":
        return _schedule_notification(params)
    elif action == "cancel":
        return _cancel_scheduled(params)
    elif action == "mute":
        return _mute_notifications(params)
    elif action == "unmute":
        return _unmute_notifications()
    elif action == "stats":
        return _get_stats()
    elif action == "test":
        return _test_notification(params)
    elif action == "status":
        return _get_status()
    elif action == "priority":
        return _set_priority(params)
    elif action == "categories":
        return _list_categories()
    return "Acciones: send, list, settings, clear, history, schedule, cancel, mute, unmute, stats, test, status, priority, categories"


def _send_notification(params: dict) -> str:
    title = params.get("title", "")
    message = params.get("message", "")
    if not title or not message:
        return "Error: se requiere 'title' y 'message'"

    config = _load_config()
    if config.get("muted", False):
        until = config.get("mute_until")
        if until:
            try:
                if datetime.fromisoformat(until) > datetime.now():
                    return "Notificaciones mutadas hasta {}".format(until)
            except Exception:
                pass
        return "Notificaciones mutadas"

    priority = params.get("priority", "normal")
    category = params.get("category", "general")
    context = params.get("context", {})

    should_notify = _should_notify(context, config)
    if not should_notify:
        return "Notificación no enviada (contexto no apropiado). Guardada en historial"

    notification = {
        "id": "notif_{}".format(int(time.time() * 1000)),
        "title": title,
        "message": message,
        "priority": priority,
        "category": category,
        "timestamp": datetime.now().isoformat(),
        "read": False,
        "context": context,
        "actions": params.get("actions", []),
    }

    _save_notification(notification)
    _display_notification(notification)
    return "Notificación enviada: {} | Prioridad: {} | Categoría: {}".format(
        title, priority, category)


def _list_notifications(params: dict) -> str:
    notifications = _load_notifications()
    if not notifications:
        return "No hay notificaciones"

    limit = params.get("limit", 10)
    unread = [n for n in notifications if not n.get("read")]

    results = ["Notificaciones ({} total, {} sin leer):".format(len(notifications), len(unread))]
    for n in notifications[:limit]:
        read = "✓" if n.get("read") else "•"
        priority = "!" if n.get("priority") == "high" else ""
        results.append("  [{}] {}{} | {} | {}".format(
            read, priority, n.get("title", "?")[:30],
            n.get("category", "?"), n.get("timestamp", "?")[:16]))
    return "\n".join(results)


def _update_settings(params: dict) -> str:
    config = _load_config()
    for key in ["quiet_hours_start", "quiet_hours_end", "max_per_hour",
                "categories_enabled", "sound_enabled", "desktop_enabled"]:
        if key in params:
            config[key] = params[key]
    _save_config(config)
    return "Configuración de notificaciones actualizada"


def _clear_notifications() -> str:
    count = len(_load_notifications())
    _save_notifications([])
    return "Notificaciones limpiadas ({} removidas)".format(count)


def _notification_history(params: dict) -> str:
    days = int(params.get("days", 7))
    notifications = _load_notifications()
    cutoff = datetime.now() - timedelta(days=days)
    recent = [n for n in notifications if _parse_date(n.get("timestamp", "")) > cutoff]

    lines = ["Historial ({} días, {} notificaciones):".format(days, len(recent))]
    categories = {}
    for n in recent:
        cat = n.get("category", "general")
        categories[cat] = categories.get(cat, 0) + 1

    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        lines.append("  {}: {}".format(cat, count))
    return "\n".join(lines)


def _schedule_notification(params: dict) -> str:
    title = params.get("title", "")
    message = params.get("message", "")
    when = params.get("when", "")

    if not title or not when:
        return "Error: se requiere 'title' y 'when' (ISO datetime)"

    try:
        when_dt = datetime.fromisoformat(when)
    except Exception:
        return "Formato de fecha inválido: {}".format(when)

    notification = {
        "id": "sched_{}".format(int(time.time() * 1000)),
        "title": title,
        "message": message,
        "scheduled_for": when,
        "priority": params.get("priority", "normal"),
        "category": params.get("category", "scheduled"),
        "created": datetime.now().isoformat(),
    }

    notifications = _load_notifications()
    notifications.append(notification)
    _save_notifications(notifications)
    return "Notificación programada para: {}".format(when)


def _cancel_scheduled(params: dict) -> str:
    notif_id = params.get("id", "")
    if not notif_id:
        return "Error: se requiere 'id'"
    notifications = _load_notifications()
    notifications = [n for n in notifications if n.get("id") != notif_id]
    _save_notifications(notifications)
    return "Notificación {} cancelada".format(notif_id)


def _mute_notifications(params: dict) -> str:
    config = _load_config()
    duration_hours = int(params.get("hours", 1))
    config["muted"] = True
    config["mute_until"] = (datetime.now() + timedelta(hours=duration_hours)).isoformat()
    _save_config(config)
    return "Notificaciones mutadas por {} horas".format(duration_hours)


def _unmute_notifications() -> str:
    config = _load_config()
    config["muted"] = False
    config.pop("mute_until", None)
    _save_config(config)
    return "Notificaciones desmutadas"


def _get_stats() -> str:
    notifications = _load_notifications()
    total = len(notifications)
    unread = sum(1 for n in notifications if not n.get("read"))
    categories = {}
    priorities = {}
    for n in notifications:
        cat = n.get("category", "general")
        pri = n.get("priority", "normal")
        categories[cat] = categories.get(cat, 0) + 1
        priorities[pri] = priorities.get(pri, 0) + 1

    lines = [
        "Stats notificaciones:",
        "  Total: {} | Sin leer: {}".format(total, unread),
        "  Prioridades: {}".format(", ".join("{}:{}".format(k, v) for k, v in priorities.items())),
        "  Categorías: {}".format(", ".join("{}:{}".format(k, v) for k, v in sorted(categories.items(), key=lambda x: -x[1])[:5])),
    ]
    return "\n".join(lines)


def _test_notification(params: dict) -> str:
    return _send_notification({
        "title": "Test de notificación",
        "message": "Esta es una notificación de prueba de ERIS",
        "priority": "normal",
        "category": "test",
    })


def _get_status() -> str:
    config = _load_config()
    notifications = _load_notifications()
    unread = sum(1 for n in notifications if not n.get("read"))
    muted = config.get("muted", False)
    return "Notificaciones: {} total ({} sin leer) | Muted: {} | Categorías: {}".format(
        len(notifications), unread, muted,
        ", ".join(config.get("categories_enabled", {}).keys()) or "todas")


def _set_priority(params: dict) -> str:
    category = params.get("category", "")
    priority = params.get("priority", "normal")
    if not category:
        return "Error: se requiere 'category'"
    config = _load_config()
    config.setdefault("category_priorities", {})[category] = priority
    _save_config(config)
    return "Prioridad para '{}' establecida a {}".format(category, priority)


def _list_categories() -> str:
    config = _load_config()
    categories = config.get("categories_enabled", {})
    if not categories:
        return "Categorías: todas habilitadas por defecto"
    lines = ["Categorías configuradas:"]
    for cat, enabled in categories.items():
        lines.append("  {} ({})".format(cat, "habilitada" if enabled else "deshabilitada"))
    return "\n".join(lines)


def _should_notify(context, config):
    now = datetime.now()
    quiet_start = config.get("quiet_hours_start", "22:00")
    quiet_end = config.get("quiet_hours_end", "08:00")

    try:
        start_h, start_m = map(int, quiet_start.split(":"))
        end_h, end_m = map(int, quiet_end.split(":"))
        if start_h <= now.hour < end_h:
            return False
    except Exception:
        pass

    return True


def _display_notification(notification):
    try:
        import platform
        if platform.system() == "Windows":
            from win10toast import ToastNotifier
            toaster = ToastNotifier()
            toaster.show_toast(
                notification.get("title", "ERIS"),
                notification.get("message", ""),
                duration=5, threaded=True)
    except ImportError:
        pass
    except Exception:
        pass


def _save_notification(notification):
    notifications = _load_notifications()
    notifications.insert(0, notification)
    notifications = notifications[:_MAX_NOTIFICATIONS]
    _save_notifications(notifications)


def _load_notifications():
    if _NOTIFICATIONS_FILE.exists():
        try:
            data = json.loads(_NOTIFICATIONS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data.get("notifications", [])
            return data if isinstance(data, list) else []
        except Exception:
            pass
    return []


def _save_notifications(notifications):
    _NOTIFICATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _NOTIFICATIONS_FILE.write_text(json.dumps(notifications, indent=2, ensure_ascii=False), encoding="utf-8")


def _load_config():
    if _NOTIFICATION_CONFIG.exists():
        try:
            return json.loads(_NOTIFICATION_CONFIG.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"muted": False, "quiet_hours_start": "22:00", "quiet_hours_end": "08:00",
            "max_per_hour": 10, "sound_enabled": True, "desktop_enabled": True,
            "categories_enabled": {}}


def _save_config(config):
    _NOTIFICATION_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    _NOTIFICATION_CONFIG.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")


def _parse_date(date_str):
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00").replace("+00:00", ""))
    except Exception:
        return datetime(2000, 1, 1)
