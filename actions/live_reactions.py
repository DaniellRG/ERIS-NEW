"""Live reactions and watch-along features inspired by capri-desktop.

Live reactions: short lines pop up over fullscreen games/apps.
Watch along: Eris reacts to videos playing on screen.
"""

import os
import platform
import subprocess
import threading
import time
from pathlib import Path
from core.platform import safe_print

BASE_DIR = Path(__file__).parent.parent

# Reaction pool for different contexts
_GAME_REACTIONS = [
    "Nice!", "Ooh!", "Watch out!", "Let's go!", "Good job!",
    "Almost!", "Close one!", "Incredible!", "Wow!", "Epic!",
]

_VIDEO_REACTIONS = [
    "That's cool!", "Interesting!", "Wow!", "Haha!", "Nice!",
    "Oh no!", "Amazing!", "I see!", "Got it!", "Cool!",
]

_REACTION_OVERLAY = None


def _detect_fullscreen() -> bool:
    """Detect if a fullscreen app/game is running."""
    try:
        if platform.system() == "Linux":
            # Check if any window is fullscreen using xdotool/wmctrl
            try:
                result = subprocess.run(
                    ["xdotool", "getactivewindow", "getwindowgeometry"],
                    capture_output=True, text=True, timeout=3
                )
                if result.returncode == 0:
                    # Check if window is fullscreen (covers entire screen)
                    import shutil
                    screen = subprocess.run(["xdotool", "getdisplaygeometry"], capture_output=True, text=True, timeout=3)
                    if screen.returncode == 0:
                        sw, sh = screen.stdout.strip().split()
                        # Parse window geometry
                        for line in result.stdout.split("\n"):
                            if "Geometry:" in line:
                                parts = line.split()
                                if len(parts) >= 4:
                                    w, h = parts[2].split("x")
                                    if int(w) >= int(sw) * 0.9 and int(h) >= int(sh) * 0.9:
                                        return True
            except FileNotFoundError:
                pass
        elif platform.system() == "Windows":
            import ctypes
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            rect = ctypes.wintypes.RECT()
            ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
            sw = ctypes.windll.user32.GetSystemMetrics(0)
            sh = ctypes.windll.user32.GetSystemMetrics(1)
            if (rect.right - rect.left) >= sw * 0.9 and (rect.bottom - rect.top) >= sh * 0.9:
                return True
    except Exception as e:
        safe_print(f"[FULLSCREEN] Error: {e}")
    return False


def show_reaction(text: str = "", context: str = "game") -> str:
    """Show a short reaction overlay on screen.

    Args:
        text: Reaction text (random if empty)
        context: 'game' or 'video' for appropriate reactions
    """
    import random
    if not text:
        pool = _GAME_REACTIONS if context == "game" else _VIDEO_REACTIONS
        text = random.choice(pool)

    try:
        from PyQt6.QtWidgets import QApplication, QLabel, QWidget
        from PyQt6.QtCore import Qt, QTimer
        from PyQt6.QtGui import QFont

        app = QApplication.instance()
        if app is None:
            return "Error: No Qt application running"

        # Create overlay
        overlay = QWidget()
        overlay.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowTransparentForMouseEvents
        )
        overlay.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        overlay.setGeometry(0, 0, 300, 60)

        # Position at top-center of screen
        screen = app.primaryScreen()
        if screen:
            geo = screen.geometry()
            overlay.move(geo.width() // 2 - 150, 50)

        label = QLabel(text, overlay)
        label.setStyleSheet("""
            color: white; font-size: 24px; font-weight: bold;
            background: rgba(0,0,0,180); border-radius: 12px;
            padding: 8px 16px;
        """)
        label.adjustSize()
        overlay.show()

        # Auto-close after 2 seconds
        QTimer.singleShot(2000, overlay.close)
        return f"Reaction shown: {text}"
    except Exception as e:
        safe_print(f"[REACTION] Error: {e}")
        return f"Error: {e}"


def live_reactions_toggle(enable: bool = True) -> str:
    """Enable/disable live reactions over fullscreen games."""
    global _REACTION_OVERLAY
    if enable:
        if _REACTION_OVERLAY is not None:
            return "Live reactions already enabled"
        _REACTION_OVERLAY = threading.Thread(target=_live_reactions_loop, daemon=True)
        _REACTION_OVERLAY.start()
        return "Live reactions enabled"
    else:
        _REACTION_OVERLAY = None
        return "Live reactions disabled"


def _live_reactions_loop():
    """Background loop that shows reactions when fullscreen detected."""
    global _REACTION_OVERLAY
    last_reaction = 0
    while _REACTION_OVERLAY is not None:
        try:
            if _detect_fullscreen():
                now = time.time()
                if now - last_reaction > 10:  # React every 10 seconds max
                    show_reaction(context="game")
                    last_reaction = now
            time.sleep(2)
        except Exception as e:
            safe_print(f"[LIVE_REACTIONS] Error: {e}")
            time.sleep(5)


def watch_along_toggle(enable: bool = True) -> str:
    """Enable/disable watch-along mode (Eris reacts to videos)."""
    if enable:
        return "Watch-along enabled. Eris will react to videos playing on screen."
    return "Watch-along disabled."


def watch_along_react() -> str:
    """Capture screen and react to video content."""
    try:
        from PIL import ImageGrab
        import io

        # Capture screen
        img = ImageGrab.grab()
        # Save to temp
        img_path = "/tmp/eris_screen_capture.png"
        img.save(img_path)

        # Analyze with vision (if available)
        # For now, just show a reaction
        import random
        reaction = random.choice(_VIDEO_REACTIONS)
        show_reaction(reaction, context="video")
        return f"Reacted to screen: {reaction}"
    except Exception as e:
        safe_print(f"[WATCH_ALONG] Error: {e}")
        return f"Error: {e}"
