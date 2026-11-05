"""Desktop companion features inspired by capri-desktop.

Includes: hologram mode (click-through), draw on screen, keep awake,
auto-start, head pats, file drag-and-drop.
"""

import os
import sys
import platform
import subprocess
import threading
import time
from pathlib import Path
from core.platform import safe_print

BASE_DIR = Path(__file__).parent.parent


def hologram_toggle(enable: bool = True) -> str:
    """Toggle hologram mode (click-through window).

    When enabled, mouse clicks pass through Eris to the windows behind her.
    """
    try:
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import Qt
        app = QApplication.instance()
        if app is None:
            return "Error: No Qt application running"
        for w in app.topLevelWidgets():
            if "Eris" in w.windowTitle() or "eris" in w.objectName().lower():
                if enable:
                    w.setWindowFlags(w.windowFlags() | Qt.WindowType.WindowTransparentForMouseEvents)
                    w.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
                else:
                    w.setWindowFlags(w.windowFlags() & ~Qt.WindowType.WindowTransparentForMouseEvents)
                    w.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
                w.show()
                return f"Hologram mode {'enabled' if enable else 'disabled'}"
        return "Eris window not found"
    except Exception as e:
        safe_print(f"[HOLOGRAM] Error: {e}")
        return f"Error: {e}"


def keep_awake(enable: bool = True) -> str:
    """Prevent system sleep while Eris is running."""
    try:
        if platform.system() == "Windows":
            import ctypes
            ES_CONTINUOUS = 0x80000000
            ES_SYSTEM_REQUIRED = 0x00000001
            if enable:
                ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
            else:
                ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
        elif platform.system() == "Linux":
            if enable:
                subprocess.Popen(["systemd-inhibit", "--what=sleep", "--who=Eris", "--why=Keeping awake for tasks",
                                 "sleep", "infinity"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                subprocess.run(["pkill", "-f", "systemd-inhibit.*Eris"], capture_output=True)
        return f"Keep-awake {'enabled' if enable else 'disabled'}"
    except Exception as e:
        safe_print(f"[KEEP_AWAKE] Error: {e}")
        return f"Error: {e}"


def auto_start(enable: bool = True) -> str:
    """Enable/disable Eris auto-start on system boot."""
    try:
        if platform.system() == "Linux":
            autostart_dir = Path.home() / ".config" / "autostart"
            autostart_dir.mkdir(parents=True, exist_ok=True)
            desktop_file = autostart_dir / "eris.desktop"
            if enable:
                eris_path = BASE_DIR / "main.py"
                venv_python = BASE_DIR / ".venv-linux" / "bin" / "python"
                content = f"""[Desktop Entry]
Type=Application
Name=Eris
Exec={venv_python} {eris_path}
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
"""
                desktop_file.write_text(content)
                return "Auto-start enabled"
            else:
                if desktop_file.exists():
                    desktop_file.unlink()
                return "Auto-start disabled"
        elif platform.system() == "Windows":
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
            if enable:
                eris_path = BASE_DIR / "main.py"
                winreg.SetValueEx(key, "Eris", 0, winreg.REG_SZ, f'python "{eris_path}"')
            else:
                try:
                    winreg.DeleteValue(key, "Eris")
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
            return f"Auto-start {'enabled' if enable else 'disabled'}"
        return "Unsupported platform"
    except Exception as e:
        safe_print(f"[AUTO_START] Error: {e}")
        return f"Error: {e}"


def draw_on_screen(text: str, x: int = 100, y: int = 100, color: str = "red") -> str:
    """Draw text on screen using an overlay window."""
    try:
        from PyQt6.QtWidgets import QApplication, QLabel, QWidget
        from PyQt6.QtCore import Qt, QTimer
        from PyQt6.QtGui import QFont, QColor, QPainter
        app = QApplication.instance()
        if app is None:
            return "Error: No Qt application running"

        # Create overlay window
        overlay = QWidget()
        overlay.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        overlay.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        overlay.setGeometry(x, y, 400, 100)

        label = QLabel(text, overlay)
        label.setStyleSheet(f"color: {color}; font-size: 24px; font-weight: bold; background: transparent;")
        label.adjustSize()
        overlay.show()

        # Auto-close after 5 seconds
        QTimer.singleShot(5000, overlay.close)
        return f"Drew '{text}' at ({x}, {y})"
    except Exception as e:
        safe_print(f"[DRAW] Error: {e}")
        return f"Error: {e}"


def head_pat() -> str:
    """Trigger head pat reaction (interactive)."""
    try:
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if app is None:
            return "Error: No Qt application running"
        for w in app.topLevelWidgets():
            if "Eris" in w.windowTitle() or "eris" in w.objectName().lower():
                # Trigger a reaction animation
                if hasattr(w, 'set_state'):
                    w.set_state("HAPPY")
                return "Head pat! Eris is happy 💛"
        return "Eris window not found"
    except Exception as e:
        safe_print(f"[HEAD_PAT] Error: {e}")
        return f"Error: {e}"


def save_file_drop(file_path: str) -> str:
    """Process a file dropped onto Eris."""
    try:
        path = Path(file_path)
        if not path.exists():
            return f"File not found: {file_path}"
        ext = path.suffix.lower()
        if ext in (".pdf", ".docx", ".txt", ".md"):
            from actions.file_processor import process_file
            return process_file(str(path))
        elif ext in (".png", ".jpg", ".jpeg", ".gif", ".bmp"):
            return f"Image received: {path.name} ({path.stat().st_size} bytes)"
        else:
            return f"File received: {path.name} ({ext})"
    except Exception as e:
        safe_print(f"[FILE_DROP] Error: {e}")
        return f"Error: {e}"
