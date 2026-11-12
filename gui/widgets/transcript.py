# -*- coding: utf-8 -*-
"""
gui/widgets/transcript.py — Área de transcripción (log visual) de ERIS.

Extraído de ui.py durante el refactor T4.
Contiene:
  - TranscriptArea: QWidget que pinta las últimas líneas del log (consola
    integrada en la interfaz).
"""
from __future__ import annotations

from collections import deque

from PyQt6.QtGui import QColor, QFont, QPainter
from PyQt6.QtWidgets import QWidget

from gui.styles import C


class TranscriptArea(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._lines = deque(maxlen=50)
        self._current_line = ""
        self._dirty = False
        self.setMinimumHeight(80)

    def append_text(self, text: str):
        if text == "__clear__":
            self._lines.clear()
            self._current_line = ""
        elif text == "\n":
            if self._current_line:
                self._lines.append(self._current_line)
                self._current_line = ""
        else:
            self._current_line += text
        self._dirty = True
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        y = self.height() - 16
        p.setFont(QFont("Consolas", 10))
        if self._current_line:
            p.setPen(QColor(C.PRI))
            p.drawText(12, y, self._current_line)
            y -= 18
        for line in reversed(list(self._lines)[-10:]):
            if y < 0:
                break
            p.setPen(QColor(C.TEXT_DIM))
            p.drawText(12, y, line[:120])
            y -= 18
        p.end()
