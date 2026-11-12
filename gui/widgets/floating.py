# -*- coding: utf-8 -*-
"""
gui/widgets/floating.py — Orbe flotante (always-on-top) de ERIS.

Extraído de ui.py durante el refactor T4.
Contiene:
  - FloatingOrb: ventana flotante, sin bordes, siempre visible, que aloja un
    ParticleOrb y expone set_state / set_audio_level / set_emotional_color.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QWidget

from gui.widgets.orb import ParticleOrb


class FloatingOrb(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedSize(260, 260)

        self._orb = ParticleOrb(self)
        self._orb.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._orb.setGeometry(0, 0, 260, 260)

        self._drag_pos = None
        self._drag_start = None
        self._visible = False
        self._state = "IDLE"
        self.show_main_callback = None

    def _on_click(self, e):
        if self.show_main_callback:
            self.show_main_callback()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._drag_start = e.globalPosition().toPoint()
        if e.button() == Qt.MouseButton.RightButton:
            self._on_click(e)

    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.MouseButton.LeftButton and self._drag_pos is not None:
            self.move(e.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and self._drag_start is not None:
            dist = (e.globalPosition().toPoint() - self._drag_start).manhattanLength()
            if dist < 10:
                self._on_click(e)
        self._drag_pos = None
        self._drag_start = None

    def set_state(self, state: str):
        self._state = state
        self._orb.set_state(state)

    def set_audio_level(self, level: float):
        self._orb.set_audio_level(level)

    def set_emotional_color(self, hex_color: str, strength: float = 0.5, emotion: str = ""):
        self._orb.set_emotional_color(hex_color, strength, emotion)

    def show_float(self):
        self._visible = True
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - self.width() - 20, screen.height() // 3)
        self.show()
        self.raise_()
        self.activateWindow()

    def hide_float(self):
        self._visible = False
        self.hide()
