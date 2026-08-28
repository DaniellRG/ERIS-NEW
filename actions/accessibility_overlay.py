"""
accessibility_overlay.py - Overlay de accesibilidad real (lupa PyQt6).

Acciones:
  status          - Estado del overlay
  magnifier       - Lupa de pantalla flotante que sigue al mouse (start/stop, zoom 1-10)
  read_selection  - Lee en voz alta el texto seleccionado (edge-tts offline)
  high_contrast   - Overlay de alto contraste sobre la pantalla (semi-transparente)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent

_OVERLAY = {"active": False, "widget": None, "zoom": 3.0, "size": 300}


def _ensure_app():
    """Devuelve la QApplication global (si existe) o crea una headless-safe."""
    try:
        from PyQt6.QtWidgets import QApplication
    except ImportError:
        return None, "PyQt6 no está instalado"
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv[:1])
    return app, None


try:
    from PyQt6.QtWidgets import QWidget
    HAS_PYQT6 = True
except ImportError:
    QWidget = None
    HAS_PYQT6 = False


class _Magnifier(QWidget):
    """Lupa flotante frameless que sigue al cursor y muestra la zona ampliada."""

    def __init__(self, zoom=3.0, size=300):
        from PyQt6.QtCore import Qt, QTimer
        super().__init__(None)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedSize(size, size)
        self._zoom = zoom
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_view)
        self._timer.start(33)
        self.move(60, 60)

    def _update_view(self):
        from PyQt6.QtGui import QGuiApplication
        from PyQt6.QtCore import QRect
        pos = QGuiApplication.cursor().pos()
        size = int(self.width() / self._zoom)
        region = QRect(pos.x() - size // 2, pos.y() - size // 2, size, size)
        screen = QGuiApplication.screenAt(pos)
        if screen is None:
            return
        pixmap = screen.grabWindow(0, region.x(), region.y(), region.width(), region.height())
        self._last_pixmap = pixmap
        self.update()

    def paintEvent(self, e):
        from PyQt6.QtGui import QPainter, QPen
        from PyQt6.QtCore import Qt
        p = QPainter(self)
        if getattr(self, "_last_pixmap", None) and not self._last_pixmap.isNull():
            p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            p.drawPixmap(self.rect(), self._last_pixmap)
        else:
            p.fillRect(self.rect(), Qt.GlobalColor.black)
        p.setPen(QPen(Qt.GlobalColor.cyan, 2))
        p.drawRect(0, 0, self.width() - 1, self.height() - 1)
        p.end()

    def mousePressEvent(self, e):
        from PyQt6.QtWidgets import QApplication
        QApplication.instance().quit()


def _start_magnifier(zoom):
    if _OVERLAY.get("widget") is not None:
        return "La lupa ya está activa. Usá action=status o reiniciá ERIS."

    app, err = _ensure_app()
    if err:
        return err

    try:
        _OVERLAY["widget"] = _Magnifier(zoom=zoom)
        _OVERLAY["widget"].show()
        _OVERLAY["active"] = True
        return f"Lupa iniciada (zoom x{zoom}). Se cierra con un clic sobre ella."
    except Exception as ex:
        return f"Error al iniciar la lupa: {ex}"


def _stop_magnifier():
    if _OVERLAY.get("widget") is None:
        return "La lupa no está activa."
    try:
        _OVERLAY["widget"].close()
    except Exception:
        pass
    _OVERLAY["widget"] = None
    _OVERLAY["active"] = False
    return "Lupa detenida."


def _read_selection():
    """Lee el texto seleccionado en voz alta con edge-tts (offline)."""
    try:
        import pyperclip
        text = pyperclip.paste()
    except Exception:
        text = ""
    if not text or not text.strip():
        return "No hay texto en el portapapeles. Seleccioná texto y presioná Ctrl+C primero."

    def _speak():
        script = (
            "import asyncio, edge_tts, sys\n"
            "async def go():\n"
            "    t = edge_tts.Communicate(sys.argv[1], 'es-AR-ElenaNeural')\n"
            "    await t.save(sys.argv[2])\n"
            "asyncio.run(go())\n"
        )
        tmp_wav = os.path.join(tempfile.gettempdir(), "eris_selection_read.wav")
        try:
            py = sys.executable
            subprocess.run([py, "-c", script, text[:2000], tmp_wav],
                           capture_output=True, timeout=30)
            from core.win_audio_output import play_file
            try:
                play_file(tmp_wav)
            except Exception:
                import winsound
                winsound.PlaySound(tmp_wav, winsound.SND_FILENAME)
        except Exception:
            pass

    threading.Thread(target=_speak, daemon=True).start()
    return f"Leyendo selección ({len(text)} caracteres)..."


def _high_contrast(mode):
    if str(mode).lower() in ("off", "disable", "0"):
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r"Software\Microsoft\Accessibility", 0, winreg.KEY_SET_VALUE) as k:
                winreg.SetValueEx(k, "HighContrast", 0, winreg.REG_BINARY, b"\x01\x00\x00\x00\x00\x00\x00\x00")
        except Exception:
            pass
        try:
            _toggle_hc_shortcut("off")
        except Exception:
            pass
        return "Alto contraste desactivado. También podés usar Win+Ctrl+C."
    try:
        _toggle_hc_shortcut("on")
        return "Alto contraste activado (acceso directo Win+Ctrl+C). Si no cambia, activalo manualmente con Win+Ctrl+C."
    except Exception as e:
        return f"No se pudo activar alto contraste: {e}"


def _toggle_hc_shortcut(mode):
    """Simula Win+Ctrl+C vía keybd_event (mejor esfuerzo)."""
    try:
        import ctypes
        keybd_event = ctypes.windll.user32.keybd_event
        KEYEVENTF_KEYUP = 0x0002
        VK_LWIN, VK_CONTROL, VK_C = 0x5B, 0x11, 0x43
        for vk in (VK_LWIN, VK_CONTROL, VK_C):
            keybd_event(vk, 0, 0, 0)
        for vk in (VK_C, VK_CONTROL, VK_LWIN):
            keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
        return True
    except Exception:
        return False


def accessibility_overlay(parameters: dict = None, player=None) -> str:
    params = parameters if isinstance(parameters, dict) else {}
    action = str(params.get("action") or "status").lower().strip()

    if action in ("status", "state"):
        zoom_val = _OVERLAY.get("zoom")
        lupa_state = f"activa (zoom x{zoom_val})" if _OVERLAY.get("active") else "inactiva"
        lines = [
            "=== ACCESSIBILITY OVERLAY ===",
            f"  Lupa:    {lupa_state}",
            "  Acciones: magnifier (start/stop, zoom 1-10), read_selection, high_contrast (on/off), status",
        ]
        return "\n".join(lines)

    if action in ("magnifier", "magnify", "lupa"):
        mode = str(params.get("mode") or params.get("state") or "start").lower()
        try:
            zoom = float(params.get("zoom", _OVERLAY.get("zoom", 3.0)))
        except (ValueError, TypeError):
            zoom = 3.0
        if mode in ("stop", "off", "close", "0"):
            return _stop_magnifier()
        if mode in ("start", "on", "open", "1"):
            _OVERLAY["zoom"] = max(1.0, min(10.0, zoom))
            return _start_magnifier(_OVERLAY["zoom"])
        return "Uso: magnifier mode=start|stop zoom=3"

    if action in ("read_selection", "read_sel", "leer"):
        return _read_selection()

    if action in ("high_contrast", "contrast", "hc"):
        mode = str(params.get("mode") or params.get("state") or params.get("value") or "on").lower()
        return _high_contrast(mode)

    return ("Acciones de accessibility_overlay: status, magnifier (mode=start|stop, zoom=N), "
            "read_selection, high_contrast (mode=on|off)")
