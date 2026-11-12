# -*- coding: utf-8 -*-
"""
gui/widgets/glass.py — Widgets de glassmorphism de ERIS.

Extraído de ui.py durante el refactor T4 (partir ui.py en gui/).
Contiene:
  - GlassWidget: base con barra de título, cierre y arrastre
  - SystemWidget: CPU / RAM / DISK (psutil)
  - WeatherWidget: clima (ciudad, temp, desc, ícono)
  - TodoWidget: lista de tareas
  - SpotifyWidget: canción / artista / progreso / controles
  - NotesWidget: área de notas

Dependencias: PyQt6 + psutil (SystemWidget) + gui.styles (C).
"""
from __future__ import annotations

import psutil

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QPen, QFont
from PyQt6.QtWidgets import (
    QCheckBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QProgressBar,
    QPushButton, QScrollArea, QVBoxLayout, QWidget, QTextEdit,
)

from gui.styles import C


class GlassWidget(QFrame):
    """Base de glassmorphism: barra de título, botón cerrar, arrastre, área de contenido."""
    closed = pyqtSignal(str)

    def __init__(self, title="", parent=None, floating=False):
        super().__init__(parent)
        self._title = title
        self._drag_pos = None
        self._floating = floating
        if floating:
            self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            self.setFixedSize(320, 260)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        self._header = QWidget()
        self._header.setFixedHeight(36)
        hl = QHBoxLayout(self._header)
        hl.setContentsMargins(12, 0, 4, 0)
        self._title_label = QLabel(title)
        self._title_label.setStyleSheet(f"color: {C.PRI}; font-size: 11px; font-weight: bold;")
        close_btn = QPushButton("×")
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet(f"""
            QPushButton {{ color: {C.TEXT_DIM}; background: transparent; border: none; font-size: 16px; }}
            QPushButton:hover {{ color: {C.ERROR}; }}
        """)
        close_btn.clicked.connect(lambda: self.closed.emit(self._title))
        hl.addWidget(self._title_label)
        hl.addStretch()
        hl.addWidget(close_btn)

        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(12, 8, 12, 12)

        self._layout.addWidget(self._header)
        self._layout.addWidget(self._content, 1)

        self._apply_style()

    def _apply_style(self):
        self.setStyleSheet(f"""
            GlassWidget {{
                background: rgba(15,10,2,180);
                border: 1px solid {C.BORDER};
                border-radius: 12px;
            }}
            GlassWidget .QWidget {{
                background: transparent;
            }}
        """)
        self._header.setStyleSheet(f"""
            background: transparent;
            border-bottom: 1px solid {C.BORDER};
            border-top-left-radius: 12px;
            border-top-right-radius: 12px;
        """)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and e.position().y() < 36:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
            e.accept()

    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.MouseButton.LeftButton and self._drag_pos is not None:
            self.move(e.globalPosition().toPoint() - self._drag_pos)
            e.accept()

    def mouseReleaseEvent(self, e):
        self._drag_pos = None

    def content(self) -> QVBoxLayout:
        return self._content_layout


# ── System Monitor Widget ───────────────────────────────────────────────────────
class SystemWidget(GlassWidget):
    def __init__(self, parent=None, floating=False):
        super().__init__("SYSTEM", parent, floating=floating)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(2000)
        self._cpu_bar = self._make_bar("CPU", C.PRI)
        self._ram_bar = self._make_bar("RAM", C.PRI_LIGHT)
        self._disk_bar = self._make_bar("DISK", C.SUCCESS)
        self._refresh()

    def _make_bar(self, label, color):
        w = QWidget()
        wl = QVBoxLayout(w)
        wl.setContentsMargins(0, 4, 0, 4)
        hl = QHBoxLayout()
        lbl = QLabel(label)
        lbl.setStyleSheet(f"color: {color}; font-size: 10px; font-family: monospace;")
        self_val = QLabel("0%")
        self_val.setStyleSheet(f"color: {C.TEXT}; font-size: 10px; font-family: monospace;")
        hl.addWidget(lbl)
        hl.addStretch()
        hl.addWidget(self_val)
        bar = QProgressBar()
        bar.setFixedHeight(4)
        bar.setTextVisible(False)
        bar.setStyleSheet(f"""
            QProgressBar {{ background: {C.BG3}; border: none; border-radius: 2px; }}
            QProgressBar::chunk {{ background: {color}; border-radius: 2px; }}
        """)
        wl.addLayout(hl)
        wl.addWidget(bar)
        self.content().addWidget(w)
        return (self_val, bar)

    def _refresh(self):
        self._cpu_bar[0].setText(f"{psutil.cpu_percent():.0f}%")
        self._cpu_bar[1].setValue(int(psutil.cpu_percent()))
        self._ram_bar[0].setText(f"{psutil.virtual_memory().percent:.0f}%")
        self._ram_bar[1].setValue(int(psutil.virtual_memory().percent))
        self._disk_bar[0].setText(f"{psutil.disk_usage('/').percent:.0f}%")
        self._disk_bar[1].setValue(int(psutil.disk_usage('/').percent))


# ── Weather Widget ──────────────────────────────────────────────────────────────
class WeatherWidget(GlassWidget):
    def __init__(self, parent=None, floating=False):
        super().__init__("WEATHER", parent, floating=floating)
        self._temp_label = QLabel("--°C")
        self._temp_label.setStyleSheet(f"color: {C.TEXT_BRIGHT}; font-size: 36px; font-weight: bold;")
        self._desc_label = QLabel("--")
        self._desc_label.setStyleSheet(f"color: {C.TEXT_DIM}; font-size: 12px;")
        self._city_label = QLabel("--")
        self._city_label.setStyleSheet(f"color: {C.PRI}; font-size: 11px;")
        self._icon_label = QLabel("")
        self._icon_label.setFixedSize(64, 64)
        cl = QHBoxLayout()
        cl.addWidget(self._icon_label)
        cl.addWidget(self._temp_label)
        cl.addStretch()
        self.content().addLayout(cl)
        self.content().addWidget(self._desc_label)
        self.content().addWidget(self._city_label)

    def update_weather(self, city, temp, desc, icon_code=""):
        self._city_label.setText(city)
        self._temp_label.setText(f"{temp}°C")
        self._desc_label.setText(desc.capitalize())


# ── Todo Widget ─────────────────────────────────────────────────────────────────
class TodoWidget(GlassWidget):
    def __init__(self, parent=None, floating=False):
        super().__init__("TODO", parent, floating=floating)
        self._items = []
        self._list = QVBoxLayout()
        self._list.setSpacing(4)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"background: transparent; border: none;")
        scroll_w = QWidget()
        scroll_w.setLayout(self._list)
        scroll.setWidget(scroll_w)
        self.content().addWidget(scroll)

        input_row = QHBoxLayout()
        self._input = QLineEdit()
        self._input.setPlaceholderText("New task...")
        self._input.setStyleSheet(f"""
            QLineEdit {{ background: {C.BG3}; color: {C.TEXT}; border: 1px solid {C.BORDER};
            border-radius: 4px; padding: 4px 8px; font-size: 11px; }}
            QLineEdit:focus {{ border-color: {C.PRI}; }}
        """)
        add_btn = QPushButton("+")
        add_btn.setFixedSize(28, 28)
        add_btn.setStyleSheet(f"""
            QPushButton {{ background: {C.PRI}; color: {C.BG}; border: none; border-radius: 4px;
            font-weight: bold; }}
            QPushButton:hover {{ background: {C.PRI_LIGHT}; }}
        """)
        add_btn.clicked.connect(self._add)
        self._input.returnPressed.connect(self._add)
        input_row.addWidget(self._input)
        input_row.addWidget(add_btn)
        self.content().addLayout(input_row)

    def _add(self):
        text = self._input.text().strip()
        if text:
            self.add_todo(text)
            self._input.clear()

    def add_todo(self, text):
        row = QHBoxLayout()
        cb = QCheckBox()
        cb.setStyleSheet(f"color: {C.TEXT};")
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {C.TEXT}; font-size: 11px;")
        lbl.setWordWrap(True)
        row.addWidget(cb)
        row.addWidget(lbl, 1)
        self._list.addLayout(row)
        self._items.append(text)


# ── Spotify Widget ──────────────────────────────────────────────────────────────
class SpotifyWidget(GlassWidget):
    def __init__(self, parent=None, floating=False):
        super().__init__("SPOTIFY", parent, floating=floating)
        self._song = QLabel("--")
        self._song.setStyleSheet(f"color: {C.TEXT_BRIGHT}; font-size: 13px; font-weight: bold;")
        self._artist = QLabel("--")
        self._artist.setStyleSheet(f"color: {C.TEXT_DIM}; font-size: 11px;")
        self._progress = QProgressBar()
        self._progress.setFixedHeight(3)
        self._progress.setTextVisible(False)
        self._progress.setStyleSheet(f"""
            QProgressBar {{ background: {C.BG3}; border: none; border-radius: 1px; }}
            QProgressBar::chunk {{ background: {C.PRI}; border-radius: 1px; }}
        """)
        controls = QHBoxLayout()
        for sym, color in [("⏮", C.TEXT_DIM), ("▶", C.PRI), ("⏭", C.TEXT_DIM)]:
            btn = QPushButton(sym)
            btn.setFixedSize(32, 32)
            btn.setStyleSheet(f"""
                QPushButton {{ color: {color}; background: transparent; border: none; font-size: 16px; }}
                QPushButton:hover {{ color: {C.TEXT_BRIGHT}; }}
            """)
            controls.addWidget(btn)
        controls.addStretch()
        self.content().addWidget(self._song)
        self.content().addWidget(self._artist)
        self.content().addWidget(self._progress)
        self.content().addLayout(controls)

    def update_spotify(self, song, artist, album, duration_ms, progress_ms, is_playing):
        self._song.setText(song[:40])
        self._artist.setText(artist[:30])
        if duration_ms > 0:
            self._progress.setValue(int(progress_ms / duration_ms * 100))


# ── Notes Widget ────────────────────────────────────────────────────────────────
class NotesWidget(GlassWidget):
    def __init__(self, parent=None, floating=False):
        super().__init__("NOTES", parent, floating=floating)
        self._text = QTextEdit()
        self._text.setPlaceholderText("Write something...")
        self._text.setStyleSheet(f"""
            QTextEdit {{ background: {C.BG3}; color: {C.TEXT}; border: 1px solid {C.BORDER};
            border-radius: 6px; padding: 8px; font-size: 12px; }}
            QTextEdit:focus {{ border-color: {C.PRI}; }}
        """)
        self.content().addWidget(self._text)
