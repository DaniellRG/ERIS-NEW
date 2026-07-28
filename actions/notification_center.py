import os
import json
import subprocess
import threading
import time
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
HISTORY_FILE = os.path.join(DATA_DIR, "notifications.json")


def _load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return {"notifications": []}


def _save_history(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(HISTORY_FILE, "w") as f:
        json.dump(data, f, indent=2)


def _record_notification(title, message, method):
    data = _load_history()
    data["notifications"].append({
        "title": title,
        "message": message,
        "method": method,
        "timestamp": datetime.now().isoformat()
    })
    if len(data["notifications"]) > 500:
        data["notifications"] = data["notifications"][-500:]
    _save_history(data)


def notification_center(parameters: dict, player=None) -> str:
    action = parameters.get("action", "send").lower()

    if action == "send":
        return _send_notification(parameters)
    elif action == "history":
        return _history(parameters)
    elif action == "clear":
        return _clear_history()
    elif action == "schedule":
        return _schedule_notification(parameters)
    elif action == "desktop":
        return _desktop_notification(parameters)
    else:
        return f"Unknown action: {action}. Valid: send, history, clear, schedule, desktop"


def _send_notification(parameters: dict):
    title = parameters.get("title", "Notification")
    message = parameters.get("message", "")
    if not message:
        return "'message' parameter required."

    method = parameters.get("method", "desktop").lower()

    if method == "desktop":
        return _desktop_notification(parameters)
    elif method == "console":
        _record_notification(title, message, "console")
        return f"[NOTIFICATION] {title}: {message}"
    elif method == "powershell":
        return _ps_notification(title, message)
    else:
        _record_notification(title, message, method)
        return f"Notification recorded ({method}): {title}"


def _desktop_notification(parameters: dict):
    title = parameters.get("title", "Notification")
    message = parameters.get("message", "")
    if not message:
        return "'message' parameter required."

    result = _ps_notification(title, message)
    _record_notification(title, message, "desktop")
    return result


def _ps_notification(title, message):
    ps_script = (
        f'[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, '
        f'ContentType = WindowsRuntime] | Out-Null; '
        f'[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom, '
        f'ContentType = WindowsRuntime] | Out-Null; '
        f'$template = @" '
        f'<toast launch="action=view&param=1" duration="short"> '
        f'  <visual bindingType="toastGeneric"> '
        f'    <text>{title}</text> '
        f'    <text>{message}</text> '
        f'  </visual> '
        f'  <audio src="ms-winsoundevent:Notification.Default"/> '
        f'</toast> '
        f'"@; '
        f'$xml = New-Object Windows.Data.Xml.Dom.XmlDocument; '
        f'$xml.LoadXml($template); '
        f'$toast = [Windows.UI.Notifications.ToastNotification]::new($xml); '
        f'[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("Eris").Show($toast)'
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            return f"Desktop notification sent: {title}"
        return f"Notification sent (fallback): {title} - {message}"
    except Exception as e:
        return f"Notification error: {e}. Message: {title} - {message}"


def _history(parameters: dict):
    data = _load_history()
    notifications = data.get("notifications", [])
    limit = parameters.get("limit", 20)
    if not notifications:
        return "No notification history."

    recent = notifications[-limit:]
    lines = [f"Notification History ({len(recent)} of {len(notifications)}):"]
    for n in reversed(recent):
        lines.append(f"  [{n['timestamp']}] {n['title']}: {n['message']}")
    return "\n".join(lines)


def _clear_history():
    _save_history({"notifications": []})
    return "Notification history cleared."


def _schedule_notification(parameters: dict):
    title = parameters.get("title", "Scheduled Notification")
    message = parameters.get("message", "")
    delay = parameters.get("delay_seconds", 60)

    if not message:
        return "'message' parameter required."

    def _delayed():
        time.sleep(delay)
        _ps_notification(title, message)
        _record_notification(title, message, "scheduled")

    thread = threading.Thread(target=_delayed, daemon=True)
    thread.start()

    return f"Notification scheduled in {delay} seconds: {title}"
