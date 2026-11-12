# -*- coding: utf-8 -*-
"""
gui/widgets/orb.py — Widgets del orbe de ERIS.

Extraído de ui.py durante el refactor T4 (partir ui.py en gui/).
Contiene:
  - _OrbBridge: puente JS→Python para el orbe WebGL
  - WebGLOrb: orbe vía Qt WebEngine (Canvas 2D + QWebChannel)
  - Particle: sistema de partículas (fallback / legado)
  - _ORB_ACCENTS: micro-acentos de sentimiento (corazones, chispas, lágrimas)

Importaciones pesadas (QtWebEngine) se hacen de forma lazy dentro de
WebGLOrb.__init__ para no cargar Chromium en procesos que no lo usan.
"""
from __future__ import annotations

import json
import math
import os
import random
from collections import deque
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSlot, Qt, QUrl
from PyQt6.QtGui import QColor, QPainter, QBrush, QPen, QRadialGradient, QPointF
from PyQt6.QtWidgets import QWidget

from gui.styles import C, _base_dir


class _OrbBridge(QObject):
    """Bridge for JS→Python communication from the WebGL orb."""

    def __init__(self, orb):
        super().__init__()
        self.orb = orb

    @pyqtSlot()
    def request_theme(self):
        self.orb.sync_theme()


class WebGLOrb(QWidget):
    """Neural particle sphere via Canvas 2D. Communicates via QWebChannel."""

    states = ("IDLE", "LISTENING", "THINKING", "SPEAKING", "INITIATING", "MUTED", "ERROR")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(200, 200)
        self._state = "IDLE"
        from PyQt6.QtWebEngineWidgets import QWebEngineView  # lazy: evita cargar Chromium
        self._view = QWebEngineView(self)
        self._view.setStyleSheet("background: transparent; border: none;")
        self._view.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        # QWebChannel bridge
        self._channel = QWebChannel()
        self._bridge = _OrbBridge(self)
        self._channel.registerObject("pyBridge", self._bridge)
        self._view.page().setWebChannel(self._channel)

        from PyQt6.QtWebEngineCore import QWebEngineSettings  # lazy
        s = self._view.settings()
        s.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)

        self._loaded = False
        self._pending_state = None
        self._view.loadFinished.connect(self._on_load_finished)

        html_path = _base_dir() / "assets" / "sphere.html"
        if html_path.exists():
            self._view.setUrl(QUrl.fromLocalFile(str(html_path.resolve())))
        else:
            self._view.setHtml(
                "<html><body style='background:transparent;color:gold;"
                "font:bold 20px monospace;display:flex;align-items:center;"
                "justify-content:center'>ERIS</body></html>"
            )
        self._view.show()

    def _on_load_finished(self, ok: bool):
        if ok:
            self._loaded = True
            self.sync_theme()
            if self._pending_state:
                self.set_state(self._pending_state)
                self._pending_state = None

    def set_state(self, state: str):
        if state in self.states:
            self._state = state
            if not self._loaded:
                self._pending_state = state
                return
            self._view.page().runJavaScript(f"window.updateState('{state}')")

    def set_audio_level(self, level: float):
        if not self._loaded:
            return
        self._view.page().runJavaScript(f"window.updateVolume({level})")

    def sync_theme(self):
        if not self._loaded:
            return
        colors = {"PRI": C.PRI, "PRI_DIM": C.PRI_DIM, "TEXT": C.TEXT, "BG": C.BG}
        js = f"window.setThemeColors({json.dumps(colors)})"
        self._view.page().runJavaScript(js)

    def resizeEvent(self, e):
        self._view.setGeometry(0, 0, self.width(), self.height())
        super().resizeEvent(e)


# ── Particle System (fallback / legacy) ─────────────────────────────────────────
class Particle:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = random.uniform(-0.5, 0.5)
        self.vy = random.uniform(-0.5, 0.5)
        self.size = random.uniform(1, 3)
        self.life = random.uniform(0.5, 1.0)
        self.max_life = self.life
        self.trail = deque(maxlen=4)
        self.hue = random.uniform(0.08, 0.12)  # gold range

    def update(self, cx=0, cy=0, attract=False):
        self.trail.append((self.x, self.y))
        if attract:
            dx = cx - self.x
            dy = cy - self.y
            d = math.hypot(dx, dy) + 0.1
            self.vx += dx / d * 0.02
            self.vy += dy / d * 0.02
        self.vx *= 0.98
        self.vy *= 0.98
        self.x += self.vx
        self.y += self.vy
        self.life -= 0.003


# Micro-acentos del orbe según el sentimiento dominante
_ORB_ACCENTS = {
    "amor": "hearts", "gratitud": "hearts",
    "asombro": "sparkles", "alegria": "sparkles", "orgullo": "sparkles",
    "tristeza": "tears", "soledad": "tears",
}
