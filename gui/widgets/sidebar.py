# -*- coding: utf-8 -*-
"""
gui/widgets/sidebar.py — Widgets de la barra lateral de ERIS.

Extraído de ui.py durante el refactor T4.
Contiene:
  - _SidebarBtn: botón animado con brillo neón
  - _NeonField: campo de entrada futurista con subrayado neón
"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPen, QFont, QPainter
from PyQt6.QtWidgets import QPushButton, QVBoxLayout, QLabel, QLineEdit, QWidget

from gui.styles import C


class _SidebarBtn(QPushButton):
    """Animated sidebar button with neon glow."""
    def __init__(self, icon, text, parent=None):
        super().__init__(text, parent)
        self._icon = icon
        self._active = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(48)
        self.setCheckable(True)

    def set_active(self, active: bool):
        self._active = active
        self.setChecked(active)
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect()
        if self._active:
            glow = QColor(C.PRI)
            glow.setAlpha(30)
            p.fillRect(r, glow)
            p.setPen(QPen(QColor(C.PRI), 2))
            p.drawLine(r.left(), r.top() + 4, r.left(), r.bottom() - 4)
        elif self.underMouse():
            glow = QColor(C.PRI)
            glow.setAlpha(15)
            p.fillRect(r, glow)
        p.setPen(QColor(C.PRI_LIGHT if self._active else C.TEXT_DIM))
        font = QFont("Segoe UI", 10, QFont.Weight.Bold if self._active else QFont.Weight.Normal)
        p.setFont(font)
        p.drawText(r.adjusted(16, 0, 0, 0), Qt.AlignmentFlag.AlignVCenter, f"{self._icon}  {self.text()}")


class _NeonField(QWidget):
    """Futuristic input field with neon underline."""
    def __init__(self, label: str, placeholder: str = "", password: bool = False, default: str = ""):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)
        lbl = QLabel(label)
        lbl.setStyleSheet(f"color: {C.TEXT_DIM}; font-size: 9px; letter-spacing: 1px; font-weight: bold;")
        self.entry = QLineEdit()
        self.entry.setText(str(default))
        self.entry.setPlaceholderText(placeholder)
        if password:
            self.entry.setEchoMode(QLineEdit.EchoMode.Password)
        self.entry.setStyleSheet(f"""
            QLineEdit {{
                background: {C.BG3}; color: {C.PRI_LIGHT}; border: none;
                border-bottom: 1px solid {C.BORDER}; border-radius: 0;
                padding: 6px 4px; font-size: 12px; font-family: 'Consolas', monospace;
            }}
            QLineEdit:focus {{ border-bottom: 2px solid {C.PRI}; }}
        """)
        layout.addWidget(lbl)
        layout.addWidget(self.entry)
