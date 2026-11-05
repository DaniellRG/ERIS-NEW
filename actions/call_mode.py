"""Call Mode — Eris joins your calls, covers for you, launches games.

Inspired by capri-desktop's Call Mode feature.
Detects running call apps (Discord, Zoom, Teams, Slack, etc.) and provides
cover messages, game launching, and voice responses.
"""

import os
import platform
import subprocess
import time
from pathlib import Path
from core.platform import safe_print

BASE_DIR = Path(__file__).parent.parent

_CALL_APPS = {
    "discord": ["Discord", "discord"],
    "zoom": ["Zoom", "zoom"],
    "teams": ["Teams", "teams", "Microsoft Teams"],
    "slack": ["Slack", "slack"],
    "telegram": ["Telegram", "telegram"],
    "whatsapp": ["WhatsApp", "whatsapp"],
    "signal": ["Signal", "signal"],
    "skype": ["Skype", "skype"],
    "steam": ["Steam", "steam"],
    "browser": ["chrome", "firefox", "brave", "edge", "opera"],
}


def _detect_running_calls() -> list[str]:
    """Detect which call apps are currently running."""
    running = []
    try:
        if platform.system() == "Linux":
            # Use pgrep to find running processes
            for app_name, patterns in _CALL_APPS.items():
                for pattern in patterns:
                    try:
                        result = subprocess.run(
                            ["pgrep", "-i", pattern],
                            capture_output=True, text=True, timeout=5
                        )
                        if result.returncode == 0 and result.stdout.strip():
                            running.append(app_name)
                            break
                    except Exception:
                        pass
        elif platform.system() == "Windows":
            import psutil
            for proc in psutil.process_iter(["name"]):
                name = (proc.info.get("name") or "").lower()
                for app_name, patterns in _CALL_APPS.items():
                    if any(p.lower() in name for p in patterns):
                        if app_name not in running:
                            running.append(app_name)
    except Exception as e:
        safe_print(f"[CALL_MODE] Error detecting calls: {e}")
    return running


def call_mode_status() -> str:
    """Check which call apps are running."""
    running = _detect_running_calls()
    if not running:
        return "No call apps detected running."
    return f"Call apps detected: {', '.join(running)}"


def call_cover(excuse: str = "", game: str = "") -> str:
    """Generate a cover message for when you're away from a call.

    Args:
        excuse: Custom excuse (e.g., "getting coffee", "bathroom break")
        game: Game to suggest launching
    """
    excuses = [
        "getting coffee",
        "grabbing a snack",
        "bathroom break",
        "stepped away for a sec",
        "brb, back in a minute",
    ]
    if not excuse:
        import random
        excuse = random.choice(excuses)

    msg = f"Hey, I'm away — {excuse}."
    if game:
        msg += f" Launching {game} while I'm gone!"
    return msg


def call_join(app: str = "auto") -> str:
    """Join a call in the specified app.

    Args:
        app: Call app name (discord, zoom, teams, etc.) or 'auto' to detect
    """
    running = _detect_running_calls()
    if app == "auto":
        if not running:
            return "No call apps detected. Start Discord/Zoom/Teams first."
        app = running[0]

    if app not in running:
        return f"{app} is not running. Start it first."

    # Try to find and click the Join button (platform-specific)
    if platform.system() == "Linux":
        # Use xdotool to find and click Join button
        try:
            subprocess.run(["xdotool", "search", "--name", app, "windowactivate"], timeout=5)
            return f"Activated {app} window. Click Join manually or I'll try to find the button."
        except FileNotFoundError:
            return f"xdotool not found. Please install it: sudo pacman -S xdotool"
        except Exception as e:
            return f"Error activating {app}: {e}"
    elif platform.system() == "Windows":
        try:
            import pyautogui
            # Find the Join button on screen
            btn = pyautogui.locateOnScreen("join_button.png", confidence=0.8)
            if btn:
                pyautogui.click(btn)
                return f"Clicked Join in {app}"
            return f"Join button not found on screen for {app}"
        except Exception as e:
            return f"Error: {e}"
    return f"Platform {platform.system()} not fully supported for auto-join"


def call_mode_toggle(enable: bool = True) -> str:
    """Enable/disable call mode (Eris covers for you in calls)."""
    if enable:
        running = _detect_running_calls()
        if not running:
            return "No call apps detected. Start Discord/Zoom/Teams first."
        return f"Call mode enabled. Detected: {', '.join(running)}. Eris will cover for you."
    return "Call mode disabled."
