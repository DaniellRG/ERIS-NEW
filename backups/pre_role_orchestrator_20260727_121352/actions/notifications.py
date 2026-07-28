"""
notifications.py — ERIS Push Notifications.
Sends notifications via ntfy (self-hostable) or Windows toast.
"""

from __future__ import annotations

import json
import sys
import urllib.request as _ur
from pathlib import Path


def _config() -> dict:
    try:
        base = Path(sys.argv[0]).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent
        cfg_path = base / "config" / "api_keys.json"
        return json.loads(cfg_path.read_text("utf-8"))
    except Exception:
        return {}


def send_ntfy(title: str, message: str, priority: int = 3) -> str:
    """Send push notification via ntfy.sh (or self-hosted)."""
    cfg = _config()
    ntfy_url = cfg.get("ntfy_url", "https://ntfy.sh")
    ntfy_topic = cfg.get("ntfy_topic", "")

    if not ntfy_topic:
        return "ntfy no configurado. Configurá ntfy_topic en api_keys.json."

    try:
        data = json.dumps({
            "topic": ntfy_topic,
            "title": title,
            "message": message,
            "priority": priority,
        }).encode("utf-8")

        req = _ur.Request(
            ntfy_url,
            data=data,
            headers={"Content-Type": "application/json"},
        )
        _ur.urlopen(req, timeout=5)
        return f"Notificación enviada a ntfy ({ntfy_topic})"
    except Exception as e:
        return f"Error ntfy: {e}"


def send_toast(title: str, message: str) -> str:
    """Send Windows toast notification."""
    try:
        from win10toast import ToastNotifier
        ToastNotifier().show_toast(title, message, duration=6, threaded=True)
        return "Notificación toast enviada."
    except ImportError:
        return "win10toast no instalado."
    except Exception as e:
        return f"Error toast: {e}"


def notify(action: str = "send", **kwargs) -> str:
    """Tool: send notifications."""
    if action == "send":
        title = kwargs.get("title", "ERIS")
        msg = kwargs.get("message", "")
        channel = kwargs.get("channel", "auto")

        if channel == "ntfy":
            return send_ntfy(title, msg)
        elif channel == "toast":
            return send_toast(title, msg)
        else:
            n_result = send_ntfy(title, msg)
            t_result = send_toast(title, msg)
            return f"{n_result}\n{t_result}"

    elif action == "config":
        cfg = _config()
        ntfy_topic = cfg.get("ntfy_topic", "")
        return f"ntfy_topic: {ntfy_topic or 'No configurado'}"

    return "Acciones: send, config"
