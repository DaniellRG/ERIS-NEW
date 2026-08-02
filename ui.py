"""
ERIS UI v7.0 — Gold Glassmorphism
JARVIS-IA inspired: WebGL orb, bento-grid dashboard, gold/amber glassmorphism.
"""
from __future__ import annotations

import json
import math
import os
import random
import sys
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path

import psutil

os.environ.setdefault("QT_OPENGL", "desktop")

from PyQt6.QtCore import (
    Qt, QTimer, pyqtSignal, pyqtSlot, QRect, QUrl, QObject, QPointF,
)
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtGui import (
    QAction, QBrush, QColor, QConicalGradient, QDragEnterEvent, QDropEvent,
    QFont, QIcon, QImage, QKeySequence, QLinearGradient, QPainter,
    QPainterPath, QPalette, QPen, QPixmap, QRadialGradient, QRegion,
    QTransform, QWheelEvent, QWindow, QCursor, QFontDatabase,
)
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog,
    QFormLayout, QFrame, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QPushButton, QScrollArea, QSplashScreen, QSystemTrayIcon,
    QTextEdit, QVBoxLayout, QWidget, QMenu, QTabWidget,
)
from PyQt6.QtGui import QShortcut, QKeySequence
from PyQt6.QtWebEngineWidgets import QWebEngineView

try:
    from zoneinfo import ZoneInfo
    _BA_TZ = ZoneInfo("America/Argentina/Buenos_Aires")
except Exception:
    from datetime import timezone, timedelta
    _BA_TZ = timezone(timedelta(hours=-3))


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).parent
        internal = base / "_internal"
        if internal.exists():
            return internal
        return base
    return Path(__file__).resolve().parent


def _user_cfg_dir() -> Path:
    """User-writable config directory (%APPDATA%/ERIS)."""
    p = Path(os.environ.get("APPDATA", Path.home())) / "ERIS"
    p.mkdir(parents=True, exist_ok=True)
    return p


# ── Theme System (6 themes, gold default) ──────────────────────────────────────
THEMES = {
    "gold": {
        "BG": "#0f0a02", "BG2": "#1a1308", "BG3": "#2a1f0a",
        "SURFACE": "#1f180d", "SURFACE2": "#2f2612",
        "PRI": "#f59e0b", "PRI_LIGHT": "#fbbf24", "PRI_DIM": "#b8830a",
        "TEXT": "#fde68a", "TEXT_DIM": "#a08858", "TEXT_BRIGHT": "#fffbeb",
        "BORDER": "rgba(245,158,11,0.45)",
        "GLOW": "rgba(245,158,11,0.25)", "GLOW2": "rgba(251,191,36,0.15)",
        "SUCCESS": "#10b981", "ERROR": "#ef4444", "WARNING": "#f59e0b",
    },
    "cyan": {
        "BG": "#0a0a1a", "BG2": "#12122a", "BG3": "#1a1a3a",
        "SURFACE": "#1e1e3e", "SURFACE2": "#2a2a5e",
        "PRI": "#00f0ff", "PRI_LIGHT": "#66f0ff", "PRI_DIM": "#0090aa",
        "TEXT": "#c8c8d4", "TEXT_DIM": "#6a6a8a", "TEXT_BRIGHT": "#f0f0ff",
        "BORDER": "rgba(0,240,255,0.4)",
        "GLOW": "rgba(0,240,255,0.25)", "GLOW2": "rgba(102,240,255,0.15)",
        "SUCCESS": "#00ff88", "ERROR": "#ff3355", "WARNING": "#ffcc00",
    },
    "green": {
        "BG": "#0a0f0a", "BG2": "#0f1a0f", "BG3": "#1a2a1a",
        "SURFACE": "#122012", "SURFACE2": "#1a301a",
        "PRI": "#00ff88", "PRI_LIGHT": "#66ffaa", "PRI_DIM": "#00aa55",
        "TEXT": "#c8e8d4", "TEXT_DIM": "#6a8a7a", "TEXT_BRIGHT": "#f0fff5",
        "BORDER": "rgba(0,255,136,0.4)",
        "GLOW": "rgba(0,255,136,0.25)", "GLOW2": "rgba(102,255,170,0.15)",
        "SUCCESS": "#00ff88", "ERROR": "#ff3355", "WARNING": "#ffcc00",
    },
    "red": {
        "BG": "#0f0a0a", "BG2": "#1a0f0f", "BG3": "#2a1a1a",
        "SURFACE": "#201212", "SURFACE2": "#301a1a",
        "PRI": "#ff3355", "PRI_LIGHT": "#ff6688", "PRI_DIM": "#aa2244",
        "TEXT": "#e4c8c8", "TEXT_DIM": "#8a6a6a", "TEXT_BRIGHT": "#fff0f0",
        "BORDER": "rgba(255,51,85,0.4)",
        "GLOW": "rgba(255,51,85,0.25)", "GLOW2": "rgba(255,102,136,0.15)",
        "SUCCESS": "#00ff88", "ERROR": "#ff3355", "WARNING": "#ffcc00",
    },
    "purple": {
        "BG": "#0a0a12", "BG2": "#12121a", "BG3": "#1a1a2a",
        "SURFACE": "#1e1e2e", "SURFACE2": "#2a2a3e",
        "PRI": "#7b2d8e", "PRI_LIGHT": "#aa55cc", "PRI_DIM": "#5a1e6a",
        "TEXT": "#c8c8d4", "TEXT_DIM": "#6a6a7a", "TEXT_BRIGHT": "#f0f0ff",
        "BORDER": "rgba(123,45,142,0.45)",
        "GLOW": "rgba(123,45,142,0.25)", "GLOW2": "rgba(170,85,204,0.15)",
        "SUCCESS": "#00ff88", "ERROR": "#ff3355", "WARNING": "#ffcc00",
    },
    "white": {
        "BG": "#0a0a0a", "BG2": "#141414", "BG3": "#1e1e1e",
        "SURFACE": "#181818", "SURFACE2": "#282828",
        "PRI": "#cccccc", "PRI_LIGHT": "#eeeeee", "PRI_DIM": "#888888",
        "TEXT": "#cccccc", "TEXT_DIM": "#888888", "TEXT_BRIGHT": "#ffffff",
        "BORDER": "rgba(200,200,200,0.3)",
        "GLOW": "rgba(200,200,200,0.2)", "GLOW2": "rgba(255,255,255,0.1)",
        "SUCCESS": "#00ff88", "ERROR": "#ff3355", "WARNING": "#ffcc00",
    },
}

THEME_LIST = list(THEMES.keys())


class C:
    """Theme-aware color constants. Use C.COLOR_NAME anywhere in UI code."""
    _current = "gold"

    @classmethod
    def set_theme(cls, name: str):
        if name in THEMES:
            cls._current = name
            for k, v in THEMES[name].items():
                setattr(cls, k, v)

    @classmethod
    def get_theme(cls) -> str:
        return cls._current


def _load_saved_theme():
    try:
        from core.logging_setup import API_CONFIG_PATH
        if API_CONFIG_PATH.exists():
            cfg = json.loads(API_CONFIG_PATH.read_text("utf-8"))
        else:
            cfg = json.loads((_base_dir() / "config" / "api_keys.json").read_text("utf-8"))
        theme = cfg.get("eris_theme", "gold")
        if theme in THEMES:
            C.set_theme(theme)
    except Exception:
        pass


C.set_theme("gold")


# ── WebGL Orb (QWebEngineView + QWebChannel) ────────────────────────────────────
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
        self._view = QWebEngineView(self)
        self._view.setStyleSheet("background: transparent; border: none;")
        self._view.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        # QWebChannel bridge
        self._channel = QWebChannel()
        self._bridge = _OrbBridge(self)
        self._channel.registerObject("pyBridge", self._bridge)
        self._view.page().setWebChannel(self._channel)

        from PyQt6.QtWebEngineCore import QWebEngineSettings
        s = self._view.settings()
        s.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)

        self._loaded = False
        self._pending_state = None
        self._view.loadFinished.connect(self._on_load_finished)

        html_path = _base_dir() / "assets" / "sphere.html"
        if html_path.exists():
            self._view.setUrl(QUrl.fromLocalFile(str(html_path.resolve())))
        else:
            self._view.setHtml("<html><body style='background:transparent;color:gold;font:bold 20px monospace;display:flex;align-items:center;justify-content:center'>ERIS</body></html>")
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
        colors = {'PRI': C.PRI, 'PRI_DIM': C.PRI_DIM, 'TEXT': C.TEXT, 'BG': C.BG}
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
        self.trail = deque(maxlen=8)
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


class ParticleOrb(QWidget):
    """Pure PyQt painted particle orb (fallback if WebGL unavailable)."""
    states = ("IDLE", "LISTENING", "THINKING", "SPEAKING", "INITIATING", "MUTED", "ERROR")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(200, 200)
        self._state = "IDLE"
        self._particles = [Particle(
            self.width() / 2 + random.uniform(-100, 100),
            self.height() / 2 + random.uniform(-100, 100),
        ) for _ in range(120)]
        self._audio_level = 0.0
        self._phase = 0.0
        self._mouse_pos = None
        self._attract = False
        self._pulse = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)
        self.setMouseTracking(True)

    def set_state(self, state: str):
        if state in self.states:
            self._state = state

    def set_audio_level(self, level: float):
        self._audio_level = level * 0.5

    def _tick(self):
        self._phase += 0.02
        self._pulse = 0.5 + 0.5 * math.sin(self._phase * 2)
        cx, cy = self.width() / 2, self.height() / 2
        attract = self._attract and self._mouse_pos is not None
        mx, my = self._mouse_pos if self._mouse_pos else (cx, cy)

        target_count = 120
        if len(self._particles) < target_count:
            self._particles.append(Particle(
                cx + random.uniform(-80, 80),
                cy + random.uniform(-80, 80),
            ))

        for p in self._particles:
            if attract:
                p.update(mx, my, True)
            elif self._state == "SPEAKING":
                angle = math.atan2(p.y - cy, p.x - cx)
                p.vx += math.cos(angle) * 0.05 * self._audio_level
                p.vy += math.sin(angle) * 0.05 * self._audio_level
                p.update()
            elif self._state == "THINKING":
                angle = math.atan2(p.y - cy, p.x - cx) + self._phase
                p.vx += math.cos(angle + self._phase) * 0.3
                p.vy += math.sin(angle + self._phase) * 0.3
                p.update(cx, cy, True)
            elif self._state == "LISTENING":
                p.update(cx, cy, True)
            else:
                p.update()
            p.size = 1.5 + self._audio_level * 3
            if p.life <= 0:
                angle = random.uniform(0, 2 * math.pi)
                dist = random.uniform(0, 120)
                p.x = cx + math.cos(angle) * dist
                p.y = cy + math.sin(angle) * dist
                p.life = p.max_life
            dx = cx - p.x
            dy = cy - p.y
            d = math.hypot(dx, dy)
            if d > 200:
                p.vx += dx / d * 0.1
                p.vy += dy / d * 0.1
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._attract = True
            self._mouse_pos = (e.position().x(), e.position().y())
        elif e.button() == Qt.MouseButton.RightButton:
            self._attract = False
            self._mouse_pos = (e.position().x(), e.position().y())

    def mouseMoveEvent(self, e):
        self._mouse_pos = (e.position().x(), e.position().y())

    def mouseReleaseEvent(self, e):
        self._attract = False
        self._mouse_pos = None

    def resizeEvent(self, e):
        cx, cy = self.width() / 2, self.height() / 2
        for p in self._particles:
            p.x = cx + random.uniform(-100, 100)
            p.y = cy + random.uniform(-100, 100)
        super().resizeEvent(e)

    def _get_state_color(self):
        return {
            "IDLE": QColor(C.PRI),
            "LISTENING": QColor(C.SUCCESS),
            "THINKING": QColor(C.PRI),
            "SPEAKING": QColor(C.PRI_LIGHT),
            "INITIATING": QColor(C.PRI_LIGHT),
            "MUTED": QColor("#666666"),
            "ERROR": QColor(C.ERROR),
        }.get(self._state, QColor(C.PRI))

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx, cy = self.width() / 2, self.height() / 2
        state_color = self._get_state_color()
        glow_size = 80 + self._pulse * 30 + self._audio_level * 40
        grad = QRadialGradient(cx, cy, glow_size)
        glow = QColor(state_color)
        glow.setAlpha(15)
        grad.setColorAt(0, glow)
        glow.setAlpha(0)
        grad.setColorAt(1, glow)
        p.setBrush(QBrush(grad))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(cx, cy), glow_size, glow_size)
        for pt in self._particles:
            alpha = int(pt.life / pt.max_life * 200)
            clr = QColor(state_color)
            clr.setAlpha(alpha)
            sz = pt.size * (0.8 + 0.4 * math.sin(self._phase + pt.x))
            p.setBrush(QBrush(clr))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(pt.x, pt.y), sz, sz)
            for i, (tx, ty) in enumerate(pt.trail):
                ta = int(alpha * i / len(pt.trail) * 0.3)
                if ta > 0:
                    tc = QColor(state_color)
                    tc.setAlpha(ta)
                    p.setBrush(QBrush(tc))
                    ts = sz * i / len(pt.trail) * 0.5
                    p.drawEllipse(QPointF(tx, ty), ts, ts)
        ring_color = QColor(state_color)
        ring_color.setAlpha(int(40 + 20 * self._pulse))
        pen = QPen(ring_color, 1)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        r = 30 + 10 * self._pulse
        p.drawEllipse(QPointF(cx, cy), r, r)
        p.end()


# ── Glassmorphism Widget Base ───────────────────────────────────────────────────
class GlassWidget(QFrame):
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


# ── File Drop Zone ──────────────────────────────────────────────────────────────
class FileDropZone(QWidget):
    file_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumHeight(60)
        self._hover = False

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor(C.PRI) if self._hover else QColor(C.TEXT_DIM)
        color.setAlpha(60 if self._hover else 30)
        pen = QPen(QColor(C.PRI) if self._hover else QColor(C.TEXT_DIM), 1, Qt.PenStyle.DashLine)
        p.setPen(pen)
        p.setBrush(QBrush(color))
        rect = self.rect().adjusted(2, 2, -2, -2)
        p.drawRoundedRect(rect, 8, 8)
        p.setPen(QColor(C.TEXT_DIM))
        p.setFont(QFont("Consolas", 10))
        p.drawText(rect, Qt.AlignmentFlag.AlignCenter, "DROP FILES HERE")
        p.end()

    def dragEnterEvent(self, e: QDragEnterEvent):
        if e.mimeData().hasUrls():
            self._hover = True
            self.update()
            e.acceptProposedAction()

    def dragLeaveEvent(self, e):
        self._hover = False
        self.update()

    def dropEvent(self, e: QDropEvent):
        self._hover = False
        for url in e.mimeData().urls():
            path = url.toLocalFile()
            if path:
                self.file_selected.emit(path)
        self.update()


# ── Futuristic Settings Dialog ─────────────────────────────────────────────────
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


class SettingsDialog(QDialog):
    saved = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ERIS NEXUS — Configuration Matrix")
        self.setFixedSize(900, 620)
        self._cfg = self._load_config()
        self._current_section = 0
        self._build_ui()
        self._apply_styles()
        self._switch_section(0)

    # ── UI Sections ─────────────────────────────────────────────────────────
    SECTIONS = [
        ("⬡", "API KEYS", "Google Gemini · Ollama · Spotify · TMDB · OpenWeather"),
        ("🎙", "VOICE & AUDIO", "TTS Engine · Voice Model · Mic/Speaker · Thinking Sound"),
        ("🎨", "APPEARANCE", "Theme · Colors · Glassmorphism · Orb Style"),
        ("⚙", "GENERAL", "Language · Timezone · Paths · Camera · Region"),
        ("📊", "SYSTEM", "Stats · About · Self-Heal · Emotional State · Version"),
    ]

    def _build_ui(self):
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        outer = QWidget()
        outer.setObjectName("settingsRoot")
        outer.setStyleSheet(f"""
            #settingsRoot {{
                background: {C.BG2}; border: 1px solid {C.BORDER};
                border-radius: 16px;
            }}
        """)
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(outer)

        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        # ── Header ──
        header = QWidget()
        header.setFixedHeight(56)
        header.setStyleSheet(f"background: {C.BG3}; border-radius: 16px 16px 0 0;")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(20, 0, 16, 0)
        title = QLabel("⬡  NEXUS CONFIGURATION MATRIX")
        title.setStyleSheet(f"color: {C.PRI}; font-size: 14px; font-weight: bold; letter-spacing: 3px;")
        hl.addWidget(title)
        hl.addStretch()
        self._status_bar = QLabel("◆ SYSTEM ONLINE ◆")
        self._status_bar.setStyleSheet(f"color: {C.SUCCESS}; font-size: 9px; letter-spacing: 2px;")
        hl.addWidget(self._status_bar)
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(32, 32)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(f"""
            QPushButton {{ background: rgba(255,51,85,0.15); color: {C.ERROR}; border: 1px solid rgba(255,51,85,0.3);
            border-radius: 6px; font-size: 14px; }}
            QPushButton:hover {{ background: rgba(255,51,85,0.3); }}
        """)
        close_btn.clicked.connect(self.reject)
        hl.addWidget(close_btn)
        outer_layout.addWidget(header)

        # ── Body: Sidebar + Content ──
        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # Sidebar
        side = QWidget()
        side.setFixedWidth(200)
        side.setStyleSheet(f"background: {C.BG3};")
        self._side_layout = QVBoxLayout(side)
        self._side_layout.setContentsMargins(0, 8, 0, 8)
        self._side_layout.setSpacing(2)

        self._side_btns = []
        for i, (icon, name, desc) in enumerate(self.SECTIONS):
            btn = _SidebarBtn(icon, name)
            btn.clicked.connect(lambda checked, idx=i: self._switch_section(idx))
            self._side_layout.addWidget(btn)
            self._side_btns.append(btn)

        self._side_layout.addStretch()

        # Theme preview mini
        theme_box = QWidget()
        theme_box.setStyleSheet(f"background: {C.SURFACE}; border-radius: 8px;")
        tb_layout = QVBoxLayout(theme_box)
        tb_layout.setContentsMargins(12, 10, 12, 10)
        preview_lbl = QLabel("THEME PREVIEW")
        preview_lbl.setStyleSheet(f"color: {C.TEXT_DIM}; font-size: 8px; letter-spacing: 2px;")
        tb_layout.addWidget(preview_lbl)
        self._preview_bar = QWidget()
        self._preview_bar.setFixedHeight(8)
        self._preview_bar.setStyleSheet(f"background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {C.PRI}, stop:0.5 {C.PRI_LIGHT}, stop:1 {C.GLOW}); border-radius: 4px;")
        tb_layout.addWidget(self._preview_bar)
        self._preview_label = QLabel(C.get_theme().upper())
        self._preview_label.setStyleSheet(f"color: {C.TEXT_DIM}; font-size: 9px; letter-spacing: 1px;")
        tb_layout.addWidget(self._preview_label)
        self._side_layout.addWidget(theme_box)

        body_layout.addWidget(side)

        # Content area
        self._content_stack = QWidget()
        self._content_layout = QVBoxLayout(self._content_stack)
        self._content_layout.setContentsMargins(0, 0, 0, 0)

        # Build section widgets
        self._section_widgets = [
            self._build_api_section(),
            self._build_voice_section(),
            self._build_appearance_section(),
            self._build_general_section(),
            self._build_system_section(),
        ]
        for sw in self._section_widgets:
            sw.setVisible(False)
            self._content_layout.addWidget(sw)

        body_layout.addWidget(self._content_stack, 1)
        outer_layout.addWidget(body, 1)

        # ── Footer ──
        footer = QWidget()
        footer.setFixedHeight(48)
        footer.setStyleSheet(f"background: {C.BG3}; border-radius: 0 0 16px 16px;")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(16, 0, 16, 0)

        self._save_btn = QPushButton("⟳  COMMIT CONFIGURATION")
        self._save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._save_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {C.PRI}, stop:1 {C.PRI_DIM});
                color: {C.BG}; border: none; border-radius: 6px; padding: 8px 24px;
                font-weight: bold; font-size: 10px; letter-spacing: 1px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {C.PRI_LIGHT}, stop:1 {C.PRI});
            }}
        """)
        self._save_btn.clicked.connect(self._save)

        cancel_btn = QPushButton("CANCEL")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {C.TEXT_DIM}; border: 1px solid {C.BORDER};
                border-radius: 6px; padding: 8px 20px; font-size: 10px; letter-spacing: 1px;
            }}
            QPushButton:hover {{ color: {C.TEXT}; border-color: {C.TEXT_DIM}; }}
        """)
        cancel_btn.clicked.connect(self.reject)

        fl.addWidget(cancel_btn)
        fl.addStretch()
        fl.addWidget(self._save_btn)
        outer_layout.addWidget(footer)

    def _apply_styles(self):
        self.setStyleSheet(f"""
            QDialog {{ background: transparent; }}
            QScrollArea {{ background: transparent; border: none; }}
            QScrollArea > QWidget > QWidget {{ background: transparent; }}
            QScrollBar:vertical {{ width: 3px; background: transparent; }}
            QScrollBar::handle:vertical {{ background: {C.BORDER}; border-radius: 2px; min-height: 30px; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
            QComboBox {{
                background: {C.BG3}; color: {C.TEXT}; border: none;
                border-bottom: 1px solid {C.BORDER}; border-radius: 0;
                padding: 4px 20px 4px 4px; font-size: 11px; min-width: 120px;
            }}
            QComboBox:focus {{ border-bottom: 2px solid {C.PRI}; }}
            QComboBox::drop-down {{ border: none; width: 20px; }}
            QComboBox::down-arrow {{ image: none; border-left: 5px solid {C.PRI}; border-top: 4px solid transparent; border-bottom: 4px solid transparent; margin-right: 4px; }}
            QComboBox QAbstractItemView {{
                background: {C.BG3}; color: {C.TEXT}; border: 1px solid {C.BORDER};
                selection-background-color: {C.PRI}; selection-color: {C.BG};
                outline: none;
            }}
            QCheckBox {{ color: {C.TEXT}; font-size: 11px; spacing: 8px; }}
            QCheckBox::indicator {{
                width: 18px; height: 18px; border-radius: 4px;
                border: 1px solid {C.BORDER}; background: {C.BG3};
            }}
            QCheckBox::indicator:checked {{
                background: {C.PRI}; border-color: {C.PRI};
            }}
            QGroupBox {{
                background: {C.SURFACE}; border: 1px solid {C.BORDER};
                border-radius: 10px; margin-top: 14px; padding: 14px; font-size: 10px;
                color: {C.PRI}; font-weight: bold; letter-spacing: 1px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin; left: 14px; padding: 0 6px;
            }}
            QLineEdit {{
                background: {C.BG3}; color: {C.PRI_LIGHT}; border: none;
                border-bottom: 1px solid {C.BORDER}; border-radius: 0;
                padding: 6px 4px; font-size: 12px; font-family: 'Consolas', monospace;
            }}
            QLineEdit:focus {{ border-bottom: 2px solid {C.PRI}; }}
        """)

    def _load_config(self) -> dict:
        from core.logging_setup import API_CONFIG_PATH
        if API_CONFIG_PATH.exists():
            try:
                return json.loads(API_CONFIG_PATH.read_text("utf-8"))
            except Exception:
                pass
        user_path = _user_cfg_dir() / "config" / "api_keys.json"
        if user_path.exists():
            try:
                return json.loads(user_path.read_text("utf-8"))
            except Exception:
                pass
        return {}

    def _switch_section(self, idx: int):
        self._current_section = idx
        for i, btn in enumerate(self._side_btns):
            btn.set_active(i == idx)
        for i, w in enumerate(self._section_widgets):
            w.setVisible(i == idx)
        self._status_bar.setText(f"◆  {self.SECTIONS[idx][1]}  ◆")

    # ── Section: API Keys ───────────────────────────────────────────────────
    def _build_api_section(self):
        w = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        form_w = QWidget()
        form = QVBoxLayout(form_w)
        form.setContentsMargins(24, 16, 24, 16)
        form.setSpacing(4)

        # Gemini
        gb = QGroupBox("🔮  GOOGLE GEMINI")
        gb_layout = QVBoxLayout(gb)
        gb_layout.setSpacing(6)
        self._api_key = _NeonField("API KEY", "Enter your Gemini API key...", password=True, default=self._cfg.get("gemini_api_key", ""))
        gb_layout.addWidget(self._api_key)

        hl = QHBoxLayout()
        lbl_conv = QLabel("Conversation Model:")
        lbl_conv.setStyleSheet(f"color: {C.TEXT_DIM}; font-size: 10px;")
        hl.addWidget(lbl_conv)
        self._model_conv = QComboBox()
        self._model_conv.addItems(["gemini-2.0-flash", "gemini-2.0-pro", "gemini-1.5-pro", "ollama"])
        self._model_conv.setCurrentText(self._cfg.get("model_for_conversation", "gemini-2.0-flash"))
        hl.addWidget(self._model_conv)
        hl.addStretch()
        gb_layout.addLayout(hl)
        form.addWidget(gb)

        # Ollama
        gb2 = QGroupBox("🦙  OLLAMA (LOCAL)")
        gb2_layout = QVBoxLayout(gb2)
        gb2_layout.setSpacing(6)
        self._ollama_enabled = QCheckBox("Enable Ollama (local inference)")
        self._ollama_enabled.setChecked(self._cfg.get("ollama_enabled", False))
        gb2_layout.addWidget(self._ollama_enabled)
        self._ollama_url = _NeonField("BASE URL", "http://localhost:11434", default=self._cfg.get("ollama_base_url", "http://localhost:11434"))
        gb2_layout.addWidget(self._ollama_url)
        self._ollama_model = _NeonField("MODEL", "llama3.2", default=self._cfg.get("ollama_model", "llama3.2"))
        gb2_layout.addWidget(self._ollama_model)
        self._ollama_vision = _NeonField("VISION MODEL", "minicpm-v", default=self._cfg.get("ollama_vision_model", "minicpm-v"))
        gb2_layout.addWidget(self._ollama_vision)
        form.addWidget(gb2)

        # Spotify
        gb3 = QGroupBox("🎵  SPOTIFY")
        gb3_layout = QVBoxLayout(gb3)
        gb3_layout.setSpacing(6)
        self._spotify_id = _NeonField("CLIENT ID", "Spotify Client ID", default=self._cfg.get("spotify_client_id", ""))
        gb3_layout.addWidget(self._spotify_id)
        self._spotify_secret = _NeonField("CLIENT SECRET", "Spotify Client Secret", password=True, default=self._cfg.get("spotify_client_secret", ""))
        gb3_layout.addWidget(self._spotify_secret)
        form.addWidget(gb3)

        # TMDB & OpenWeather
        gb4 = QGroupBox("🌐  ADDITIONAL SERVICES")
        gb4_layout = QVBoxLayout(gb4)
        gb4_layout.setSpacing(6)
        self._tmdb_key = _NeonField("TMDB API KEY", "The Movie Database API key", password=True, default=self._cfg.get("tmdb_api_key", ""))
        gb4_layout.addWidget(self._tmdb_key)
        self._weather_key = _NeonField("OPENWEATHER API KEY", "OpenWeatherMap API key", password=True, default=self._cfg.get("openweather_api_key", ""))
        gb4_layout.addWidget(self._weather_key)
        form.addWidget(gb4)

        form.addStretch()
        scroll.setWidget(form_w)
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll)
        return w

    # ── Section: Voice & Audio ──────────────────────────────────────────────
    def _build_voice_section(self):
        w = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        form_w = QWidget()
        form = QVBoxLayout(form_w)
        form.setContentsMargins(24, 16, 24, 16)
        form.setSpacing(4)

        gb = QGroupBox("🗣  TEXT-TO-SPEECH")
        gb_layout = QVBoxLayout(gb)
        gb_layout.setSpacing(6)

        hl = QHBoxLayout()
        lbl_eng = QLabel("Engine:")
        lbl_eng.setStyleSheet(f"color: {C.TEXT_DIM}; font-size: 10px;")
        hl.addWidget(lbl_eng)
        self._tts = QComboBox()
        self._tts.addItems(["gemini", "system", "pykokoro"])
        self._tts.setCurrentText(self._cfg.get("tts_backend", "gemini"))
        hl.addWidget(self._tts)
        hl.addStretch()
        gb_layout.addLayout(hl)

        hl2 = QHBoxLayout()
        lbl_voice = QLabel("Voice Model:")
        lbl_voice.setStyleSheet(f"color: {C.TEXT_DIM}; font-size: 10px;")
        hl2.addWidget(lbl_voice)
        self._voice = QComboBox()
        self._voice.addItems(["Zephyr", "Aoede", "Puck", "Charon", "ef_dora"])
        self._voice.setCurrentText(self._cfg.get("tts_voice", "Zephyr"))
        hl2.addWidget(self._voice)
        hl2.addStretch()
        gb_layout.addLayout(hl2)

        # TTS test button
        test_tts = QPushButton("▶  TEST VOICE")
        test_tts.setCursor(Qt.CursorShape.PointingHandCursor)
        test_tts.setStyleSheet(f"""
            QPushButton {{ background: {C.SUCCESS}; color: {C.BG}; border: none;
            border-radius: 4px; padding: 6px 14px; font-size: 9px; font-weight: bold; }}
            QPushButton:hover {{ background: {C.SUCCESS}; opacity: 0.8; }}
        """)
        test_tts.clicked.connect(lambda: self._status_bar.setText("◆  VOICE TEST: Playing sample...  ◆"))
        gb_layout.addWidget(test_tts)
        form.addWidget(gb)

        gb2 = QGroupBox("🎧  AUDIO DEVICES")
        gb2_layout = QVBoxLayout(gb2)
        gb2_layout.setSpacing(6)
        self._mic = _NeonField("MICROPHONE DEVICE INDEX", "Default: empty", default=str(self._cfg.get("mic_device", "")))
        gb2_layout.addWidget(self._mic)
        self._spk = _NeonField("SPEAKER DEVICE INDEX", "Default: empty", default=str(self._cfg.get("spk_device", "")))
        gb2_layout.addWidget(self._spk)

        # Scan devices button
        scan_btn = QPushButton("⟳  SCAN AUDIO DEVICES")
        scan_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        scan_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {C.PRI}; border: 1px solid {C.BORDER};
            border-radius: 4px; padding: 6px 14px; font-size: 9px; }}
            QPushButton:hover {{ background: rgba(245,158,11,0.1); }}
        """)
        scan_btn.clicked.connect(lambda: self._status_bar.setText("◆  SCANNING audio devices...  ◆"))
        gb2_layout.addWidget(scan_btn)
        form.addWidget(gb2)

        gb3 = QGroupBox("🎭  ERIS VOICE STYLE")
        gb3_layout = QVBoxLayout(gb3)
        gb3_layout.setSpacing(6)
        hl5 = QHBoxLayout()
        lbl_pv = QLabel("Personality Voice:")
        lbl_pv.setStyleSheet(f"color: {C.TEXT_DIM}; font-size: 10px;")
        hl5.addWidget(lbl_pv)
        self._eris_voice = QComboBox()
        from core.audio_config import ERIS_VOICES as _av
        for _vk, (_vg, _vd) in _av.items():
            self._eris_voice.addItem(f"{_vk} ({_vg})", _vk)
        self._eris_voice.setCurrentIndex(
            max(0, self._eris_voice.findData(self._cfg.get("eris_voice", "Aoede")))
        )
        hl5.addWidget(self._eris_voice)
        hl5.addStretch()
        gb3_layout.addLayout(hl5)

        self._thinking_sound = QCheckBox("🔊  Play thinking sound while processing")
        self._thinking_sound.setChecked(self._cfg.get("thinking_sound", True))
        gb3_layout.addWidget(self._thinking_sound)

        self._wake_sound = QCheckBox("🔊  Play wake-up sound on activation")
        self._wake_sound.setChecked(self._cfg.get("wake_sound", True))
        gb3_layout.addWidget(self._wake_sound)

        self._wake_mode_cb = QCheckBox("🎯  Activación por nombre: responder solo cuando digas \"Eris, ...\"")
        self._wake_mode_cb.setChecked(self._cfg.get("wake_word_mode", True))
        gb3_layout.addWidget(self._wake_mode_cb)
        form.addWidget(gb3)

        form.addStretch()
        scroll.setWidget(form_w)
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll)
        return w

    # ── Section: Appearance ─────────────────────────────────────────────────
    def _build_appearance_section(self):
        w = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        form_w = QWidget()
        form = QVBoxLayout(form_w)
        form.setContentsMargins(24, 16, 24, 16)
        form.setSpacing(4)

        gb = QGroupBox("🎨  THEME SELECTOR")
        gb_layout = QVBoxLayout(gb)
        gb_layout.setSpacing(12)
        hl = QHBoxLayout()
        hl.setSpacing(10)

        self._theme_btns = {}
        for tname in THEME_LIST:
            theme = THEMES[tname]
            btn = QPushButton()
            btn.setFixedSize(64, 64)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(tname.upper())
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                        stop:0 {theme['BG2']}, stop:1 {theme['SURFACE']});
                    border: 2px solid {theme['PRI']};
                    border-radius: 10px;
                }}
                QPushButton:hover {{
                    border: 2px solid {theme['PRI_LIGHT']};
                }}
            """)
            # Color dot
            color_dot = QWidget(btn)
            color_dot.setFixedSize(20, 20)
            color_dot.setStyleSheet(f"""
                background: qradialgradient(cx:0.4,cy:0.4,rx:0.5,ry:0.5,
                    stop:0 {theme['PRI_LIGHT']}, stop:1 {theme['PRI']});
                border-radius: 10px;
            """)
            color_dot.move(22, 12)
            name_lbl = QLabel(tname.upper(), btn)
            name_lbl.setStyleSheet(f"color: {theme['TEXT_DIM']}; font-size: 8px; font-weight: bold; letter-spacing: 1px;")
            name_lbl.move(8, 40)
            name_lbl.resize(48, 16)
            name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

            tname_copy = tname
            btn.clicked.connect(lambda checked, tn=tname_copy: self._select_theme(tn))
            hl.addWidget(btn)
            self._theme_btns[tname] = btn

        hl.addStretch()
        gb_layout.addLayout(hl)

        # Current theme indicator
        theme_info = QWidget()
        theme_info.setStyleSheet(f"background: {C.BG3}; border-radius: 8px;")
        ti_layout = QHBoxLayout(theme_info)
        ti_layout.setContentsMargins(12, 8, 12, 8)
        self._current_theme_lbl = QLabel(f"Active: {C.get_theme().upper()}")
        self._current_theme_lbl.setStyleSheet(f"color: {C.PRI}; font-size: 11px; font-weight: bold; letter-spacing: 1px;")
        ti_layout.addWidget(self._current_theme_lbl)
        ti_layout.addStretch()

        self._theme_preview = QWidget()
        self._theme_preview.setFixedSize(80, 16)
        self._theme_preview.setStyleSheet(f"background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {C.PRI}, stop:0.5 {C.PRI_LIGHT}, stop:1 {C.GLOW}); border-radius: 8px;")
        ti_layout.addWidget(self._theme_preview)

        gb_layout.addWidget(theme_info)
        form.addWidget(gb)

        gb2 = QGroupBox("🔲  INTERFACE STYLE")
        gb2_layout = QVBoxLayout(gb2)
        gb2_layout.setSpacing(6)

        self._glass_opacity = _NeonField("GLASS OPACITY", "100-255", default=str(self._cfg.get("glass_opacity", 180)))
        gb2_layout.addWidget(self._glass_opacity)

        self._glow_intensity = _NeonField("GLOW INTENSITY", "0.0 - 1.0", default=str(self._cfg.get("glow_intensity", 0.5)))
        gb2_layout.addWidget(self._glow_intensity)

        hl_orb = QHBoxLayout()
        lbl_orb = QLabel("Orb Renderer:")
        lbl_orb.setStyleSheet(f"color: {C.TEXT_DIM}; font-size: 10px;")
        hl_orb.addWidget(lbl_orb)
        self._orb_renderer = QComboBox()
        self._orb_renderer.addItems(["WebGL (3D)", "Particles (2D)"])
        self._orb_renderer.setCurrentText("WebGL (3D)" if self._cfg.get("webgl_orb", True) else "Particles (2D)")
        hl_orb.addWidget(self._orb_renderer)
        hl_orb.addStretch()
        gb2_layout.addLayout(hl_orb)

        form.addWidget(gb2)

        form.addStretch()
        scroll.setWidget(form_w)
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll)
        return w

    def _select_theme(self, name: str):
        C.set_theme(name)
        self._current_theme_lbl.setText(f"Active: {name.upper()}")
        self._current_theme_lbl.setStyleSheet(f"color: {C.PRI}; font-size: 11px; font-weight: bold; letter-spacing: 1px;")
        self._theme_preview.setStyleSheet(f"background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {C.PRI}, stop:0.5 {C.PRI_LIGHT}, stop:1 {C.GLOW}); border-radius: 8px;")
        self._preview_bar.setStyleSheet(f"background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {C.PRI}, stop:0.5 {C.PRI_LIGHT}, stop:1 {C.GLOW}); border-radius: 4px;")
        self._preview_label.setText(name.upper())
        self._preview_label.setStyleSheet(f"color: {C.TEXT_DIM}; font-size: 9px; letter-spacing: 1px;")
        self._status_bar.setText(f"◆  THEME: {name.upper()} loaded  ◆")
        self._apply_styles()
        for btn in self._theme_btns.values():
            t = btn.toolTip().lower()
            th = THEMES[t]
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                        stop:0 {th['BG2']}, stop:1 {th['SURFACE']});
                    border: 2px solid {C.PRI if t == name else th['PRI']};
                    border-radius: 10px;
                }}
                QPushButton:hover {{
                    border: 2px solid {th['PRI_LIGHT']};
                }}
            """)

    # ── Section: General ────────────────────────────────────────────────────
    def _build_general_section(self):
        w = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        form_w = QWidget()
        form = QVBoxLayout(form_w)
        form.setContentsMargins(24, 16, 24, 16)
        form.setSpacing(4)

        gb = QGroupBox("🌍  LANGUAGE & REGION")
        gb_layout = QVBoxLayout(gb)
        gb_layout.setSpacing(6)
        hl = QHBoxLayout()
        lbl_lang = QLabel("Language:")
        lbl_lang.setStyleSheet(f"color: {C.TEXT_DIM}; font-size: 10px;")
        hl.addWidget(lbl_lang)
        self._lang = QComboBox()
        self._lang.addItems(["es-ES", "en-US", "pt-BR", "fr-FR", "de-DE", "it-IT", "ja-JP"])
        self._lang.setCurrentText(self._cfg.get("language", "es-ES"))
        hl.addWidget(self._lang)
        hl.addStretch()
        gb_layout.addLayout(hl)
        self._tz = _NeonField("TIMEZONE (IANA)", "America/Argentina/Buenos_Aires", default=self._cfg.get("timezone", "America/Argentina/Buenos_Aires"))
        gb_layout.addWidget(self._tz)
        form.addWidget(gb)

        gb2 = QGroupBox("🖥  SYSTEM PATHS")
        gb2_layout = QVBoxLayout(gb2)
        gb2_layout.setSpacing(6)
        self._chrome_profile = _NeonField("CHROME USER PROFILE", "Default", default=self._cfg.get("chrome_google_profile", "Default"))
        gb2_layout.addWidget(self._chrome_profile)
        self._chrome_path = _NeonField("CHROME EXECUTABLE PATH", "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe", default=self._cfg.get("chrome_exe_path", ""))
        gb2_layout.addWidget(self._chrome_path)
        form.addWidget(gb2)

        gb3 = QGroupBox("📷  HARDWARE")
        gb3_layout = QVBoxLayout(gb3)
        gb3_layout.setSpacing(6)
        self._cam_toggle = QCheckBox("Enable Camera")
        self._cam_toggle.setChecked(self._cfg.get("camera_enabled", True))
        gb3_layout.addWidget(self._cam_toggle)
        self._gpu_accel = QCheckBox("GPU Acceleration (requires restart)")
        self._gpu_accel.setChecked(self._cfg.get("gpu_acceleration", True))
        gb3_layout.addWidget(self._gpu_accel)
        form.addWidget(gb3)

        form.addStretch()
        scroll.setWidget(form_w)
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll)
        return w

    # ── Section: System ─────────────────────────────────────────────────────
    def _build_system_section(self):
        w = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        form_w = QWidget()
        form = QVBoxLayout(form_w)
        form.setContentsMargins(24, 16, 24, 16)
        form.setSpacing(4)

        gb = QGroupBox("⬡  ERIS NEXUS")
        gb_layout = QVBoxLayout(gb)
        gb_layout.setSpacing(8)

        # System stats grid
        stats = QWidget()
        stats.setStyleSheet(f"background: {C.BG3}; border-radius: 8px;")
        stats_layout = QVBoxLayout(stats)
        stats_layout.setContentsMargins(16, 12, 16, 12)
        stats_layout.setSpacing(6)

        ver_lbl = QLabel(f"ERIS v2.7.6  —  Constellation Core")
        ver_lbl.setStyleSheet(f"color: {C.PRI}; font-size: 16px; font-weight: bold; letter-spacing: 2px;")
        stats_layout.addWidget(ver_lbl)

        try:
            import psutil
            cpu = psutil.cpu_percent(interval=0)
            ram = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            stats_text = (
                f"CPU: {cpu}%  |  RAM: {ram.percent}% ({ram.used//(1024**3)}GB/{ram.total//(1024**3)}GB)"
                f"  |  DISK: {disk.percent}% ({disk.used//(1024**3)}GB/{disk.total//(1024**3)}GB)"
            )
        except Exception:
            stats_text = "System stats unavailable"

        sys_lbl = QLabel(stats_text)
        sys_lbl.setStyleSheet(f"color: {C.TEXT_DIM}; font-size: 10px; font-family: 'Consolas', monospace;")
        stats_layout.addWidget(sys_lbl)

        # Uptime
        uptime_lbl = QLabel(f"Session: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        uptime_lbl.setStyleSheet(f"color: {C.TEXT_DIM}; font-size: 9px;")
        stats_layout.addWidget(uptime_lbl)

        gb_layout.addWidget(stats)
        form.addWidget(gb)

        gb2 = QGroupBox("🛠  MAINTENANCE")
        gb2_layout = QVBoxLayout(gb2)
        gb2_layout.setSpacing(6)

        self_heal_btn = QPushButton("⚡  RUN SELF-HEAL SCAN")
        self_heal_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self_heal_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {C.PRI}; border: 1px solid {C.PRI};
            border-radius: 6px; padding: 8px 16px; font-size: 10px; letter-spacing: 1px; }}
            QPushButton:hover {{ background: rgba(245,158,11,0.1); }}
        """)
        self_heal_btn.clicked.connect(lambda: self._status_bar.setText("◆  SELF-HEAL: Scanning system...  ◆"))
        gb2_layout.addWidget(self_heal_btn)

        clear_btn = QPushButton("🗑  CLEAR TEMP CACHE")
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {C.WARNING}; border: 1px solid {C.WARNING};
            border-radius: 6px; padding: 8px 16px; font-size: 10px; letter-spacing: 1px; }}
            QPushButton:hover {{ background: rgba(245,158,11,0.1); }}
        """)
        clear_btn.clicked.connect(lambda: self._status_bar.setText("◆  CACHE cleared  ◆"))
        gb2_layout.addWidget(clear_btn)

        reset_btn = QPushButton("⚠  FACTORY RESET")
        reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reset_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {C.ERROR}; border: 1px solid {C.ERROR};
            border-radius: 6px; padding: 8px 16px; font-size: 10px; letter-spacing: 1px; }}
            QPushButton:hover {{ background: rgba(255,51,85,0.1); }}
        """)
        reset_btn.clicked.connect(lambda: self._status_bar.setText("◆  FACTORY RESET requires confirmation  ◆"))
        gb2_layout.addWidget(reset_btn)

        form.addWidget(gb2)

        # Emotional state summary
        gb3 = QGroupBox("💖  EMOTIONAL STATE")
        gb3_layout = QVBoxLayout(gb3)
        gb3_layout.setSpacing(6)
        emo_text = QLabel("Relationship:  —  |  Mood:  —  |  Interactions:  —")
        emo_text.setStyleSheet(f"color: {C.TEXT_DIM}; font-size: 10px; font-family: 'Consolas', monospace;")
        gb3_layout.addWidget(emo_text)

        # Try to load emotional state
        try:
            emo_path = _base_dir() / "memory" / "emotional_growth.json"
            if emo_path.exists():
                emo_data = json.loads(emo_path.read_text("utf-8"))
                stage = emo_data.get("relationship_stage", "?")
                interactions = emo_data.get("total_interactions", 0)
                baselines = emo_data.get("emotional_baselines", {})
                mood = "Positive" if baselines.get("happiness", 0.5) > 0.5 else "Neutral"
                emo_text.setText(f"Relationship: {stage.upper()}  |  Mood: {mood}  |  Interactions: {interactions}")
        except Exception:
            pass

        form.addWidget(gb3)

        form.addStretch()
        scroll.setWidget(form_w)
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll)
        return w

    # ── Save ────────────────────────────────────────────────────────────────
    def _save(self):
        self._status_bar.setText("◆  COMMITTING configuration...  ◆")

        def _safe_int(val, default=None):
            try:
                return int(val) if val.strip() else default
            except (ValueError, AttributeError):
                return default

        def _safe_float(val, default=None):
            try:
                return float(val) if val.strip() else default
            except (ValueError, AttributeError):
                return default

        cfg = {
            "gemini_api_key": self._api_key.entry.text(),
            "model_for_conversation": self._model_conv.currentText(),
            "model_for_agents": self._cfg.get("model_for_agents", "gemini"),
            "model_for_search": self._cfg.get("model_for_search", "gemini"),
            "ollama_enabled": self._ollama_enabled.isChecked(),
            "ollama_base_url": self._ollama_url.entry.text(),
            "ollama_model": self._ollama_model.entry.text(),
            "ollama_vision_model": self._ollama_vision.entry.text(),
            "spotify_client_id": self._spotify_id.entry.text(),
            "spotify_client_secret": self._spotify_secret.entry.text(),
            "spotify_redirect_uri": self._cfg.get("spotify_redirect_uri", "http://127.0.0.1:8888/callback"),
            "tmdb_api_key": self._tmdb_key.entry.text(),
            "openweather_api_key": self._weather_key.entry.text(),
            "tts_backend": self._tts.currentText(),
            "tts_voice": self._voice.currentText(),
            "mic_device": _safe_int(self._mic.entry.text()),
            "spk_device": _safe_int(self._spk.entry.text()),
            "eris_voice": self._eris_voice.currentData(),
            "eris_theme": C.get_theme(),
            "thinking_sound": self._thinking_sound.isChecked(),
            "wake_sound": self._wake_sound.isChecked(),
            "wake_word_mode": self._wake_mode_cb.isChecked(),
            "language": self._lang.currentText(),
            "timezone": self._tz.entry.text(),
            "chrome_google_profile": self._chrome_profile.entry.text(),
            "chrome_exe_path": self._chrome_path.entry.text(),
            "camera_enabled": self._cam_toggle.isChecked(),
            "gpu_acceleration": self._gpu_accel.isChecked(),
            "glass_opacity": _safe_int(self._glass_opacity.entry.text(), 180),
            "glow_intensity": _safe_float(self._glow_intensity.entry.text(), 0.5),
            "webgl_orb": self._orb_renderer.currentText() == "WebGL (3D)",
            "os_system": self._cfg.get("os_system", "windows"),
        }
        try:
            from core.logging_setup import API_CONFIG_PATH
            path = API_CONFIG_PATH
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(cfg, indent=4), encoding="utf-8")
            self._status_bar.setText("◆  CONFIGURATION COMMITTED  ◆")
            self.saved.emit(cfg)
            QTimer.singleShot(300, self.accept)
        except Exception as e:
            self._status_bar.setText(f"◆  ERROR: {e}  ◆")
            print(f"[Settings] Error saving: {e}")


# ── Transcript Area ─────────────────────────────────────────────────────────────
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


# ── Floating Orb (Always on Top) ────────────────────────────────────────────────
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


# ── Main Window (Minimal Constellation Orb) ──────────────────────────────────────
class MainWindow(QMainWindow):
    _log_sig = pyqtSignal(str)
    _state_sig = pyqtSignal(str)
    _chunk_sig = pyqtSignal(str)
    _shutdown_sig = pyqtSignal()

    def __init__(self, float_orb=None):
        super().__init__()
        self.on_text_command = None
        self.on_stop_command = None
        self.on_config_saved = None
        self.on_mute_command = None
        self._muted = False
        self._float_orb = float_orb
        self._eris_accum = ""

        self._setup_window()
        self._setup_ui()
        self._setup_tray()
        self._setup_signals()
        self._setup_shortcuts()
        self.showFullScreen()
        self._try_acrylic()

    def _setup_window(self):
        self.setWindowTitle("ERIS")
        self.setStyleSheet("QMainWindow { background: transparent; }")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, False)
        icon_path = str(_base_dir() / "assets" / "ICOERIS.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ERIS.Assistant.v2")
        except Exception:
            pass

    def _try_acrylic(self):
        try:
            import ctypes
            from ctypes import wintypes
            class _AP(ctypes.Structure):
                _fields_ = [("AccentState", wintypes.DWORD), ("AccentFlags", wintypes.DWORD), ("GradientColor", wintypes.DWORD), ("AnimationId", wintypes.DWORD)]
            class _WCD(ctypes.Structure):
                _fields_ = [("Attribute", wintypes.DWORD), ("Data", ctypes.POINTER(_AP)), ("SizeOfData", ctypes.c_size_t)]
            hwnd = int(self.winId())
            ap = _AP()
            ap.AccentState = 4  # ACCENT_ENABLE_ACRYLICBLURBEHIND
            bg = C.BG.lstrip("#")
            r, g, b = int(bg[0:2], 16), int(bg[2:4], 16), int(bg[4:6], 16)
            ap.GradientColor = (0xcc << 24) | (b << 16) | (g << 8) | r  # AABBGGRR
            wcd = _WCD()
            wcd.Attribute = 19  # WCA_ACCENT_POLICY
            wcd.SizeOfData = ctypes.sizeof(ap)
            wcd.Data = ctypes.pointer(ap)
            ctypes.windll.user32.SetWindowCompositionAttribute(hwnd, ctypes.pointer(wcd))
        except Exception:
            pass

    def _setup_ui(self):
        central = QWidget()
        central.setStyleSheet(f"background: rgba(10,7,3,100);")
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Top bar with settings gear
        top_bar = QWidget()
        top_bar.setStyleSheet("background: transparent;")
        top_bar.setFixedHeight(40)
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(6, 4, 16, 0)

        self._settings_btn = QPushButton("⚙")
        self._settings_btn.setToolTip("Settings (Ctrl+,)")
        self._settings_btn.setFixedSize(32, 32)
        self._settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._settings_btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(255,255,255,0.05); color: {C.TEXT_DIM};
                border: 1px solid {C.BORDER}; border-radius: 6px;
                font-size: 16px;
            }}
            QPushButton:hover {{
                background: rgba(255,255,255,0.12); color: {C.PRI};
            }}
        """)
        self._settings_btn.clicked.connect(self._open_settings)
        top_layout.addStretch()
        top_layout.addWidget(self._settings_btn)

        layout.addWidget(top_bar)

        self._orb = ParticleOrb()
        self._orb.set_state("IDLE")
        layout.addWidget(self._orb, 1)

        # Chat area (transcript + input)
        chat_container = QWidget()
        chat_container.setStyleSheet(f"background: rgba(10,7,3,160); border-top: 1px solid {C.BORDER};")
        chat_layout = QVBoxLayout(chat_container)
        chat_layout.setContentsMargins(20, 8, 20, 12)
        chat_layout.setSpacing(6)

        # Transcript scroll
        self._transcript = QTextEdit()
        self._transcript.setReadOnly(True)
        self._transcript.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._transcript.setFixedHeight(90)
        self._transcript.setStyleSheet(f"""
            QTextEdit {{
                background: transparent; color: {C.TEXT_DIM};
                border: none; font-size: 12px; font-family: 'Consolas', monospace;
                selection-background-color: {C.PRI}; selection-color: {C.BG};
            }}
        """)

        # Input row
        input_row = QHBoxLayout()
        input_row.setSpacing(8)

        self._chat_input = QLineEdit()
        self._chat_input.setPlaceholderText("Escribele a ERIS...")
        self._chat_input.setStyleSheet(f"""
            QLineEdit {{
                background: {C.BG3}; color: {C.TEXT};
                border: 1px solid {C.BORDER}; border-radius: 8px;
                padding: 8px 14px; font-size: 14px; font-family: 'Segoe UI', sans-serif;
            }}
            QLineEdit:focus {{ border-color: {C.PRI}; }}
        """)
        self._chat_input.returnPressed.connect(self._send_chat)
        self._chat_input.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)

        self._send_btn = QPushButton("Enviar")
        self._send_btn.setFixedSize(80, 34)
        self._send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._send_btn.setStyleSheet(f"""
            QPushButton {{
                background: {C.PRI}; color: {C.BG}; font-weight: bold;
                border: none; border-radius: 8px; font-size: 13px;
            }}
            QPushButton:hover {{ background: {C.PRI_LIGHT}; }}
            QPushButton:pressed {{ background: {C.PRI_DIM}; }}
        """)
        self._send_btn.clicked.connect(self._send_chat)

        input_row.addWidget(self._chat_input)
        input_row.addWidget(self._send_btn)

        chat_layout.addWidget(self._transcript)
        chat_layout.addLayout(input_row)

        layout.addWidget(chat_container)

        # Minimal caption overlay (kept for backward compat, hidden by default)
        self._caption = QLabel("")
        self._caption.setStyleSheet(f"""
            QLabel {{
                color: {C.TEXT_DIM}; background: transparent;
                font-size: 14px; font-family: 'Segoe UI', sans-serif;
                padding: 0px 40px 30px 40px;
            }}
        """)
        self._caption.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignBottom)
        self._caption.setWordWrap(True)
        self._caption.hide()

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+M"), self).activated.connect(self._toggle_mute)
        QShortcut(QKeySequence("Ctrl+,"), self).activated.connect(self._open_settings)
        QShortcut(QKeySequence("Escape"), self).activated.connect(lambda: (
            self._float_orb.show_float() if self._float_orb else None,
            self.hide(),
        ))
        QShortcut(QKeySequence("Ctrl+Q"), self).activated.connect(self._quit_app)

    def _setup_tray(self):
        icon_path = str(_base_dir() / "assets" / "ICOERIS.ico")
        icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()
        self._tray = QSystemTrayIcon(icon, self)
        self._tray.setToolTip("ERIS")
        menu = QMenu()
        show_a = menu.addAction("Show")
        show_a.triggered.connect(lambda: (self.showFullScreen(), self.raise_(), self.activateWindow()))
        quit_a = menu.addAction("Quit")
        quit_a.triggered.connect(self._quit_app)
        self._tray.setContextMenu(menu)
        self._tray.show()
        self._tray.activated.connect(lambda r: (self.showFullScreen(), self.raise_(), self.activateWindow()) if r == QSystemTrayIcon.ActivationReason.DoubleClick else None)

    def _setup_signals(self):
        self._state_sig.connect(self._apply_state)
        self._chunk_sig.connect(self._on_chunk)

    def _open_settings(self):
        current_theme = C.get_theme()
        dlg = SettingsDialog(self)
        dlg.saved.connect(self._on_config_saved)
        if dlg.exec():
            new_theme = C.get_theme()
            if new_theme != current_theme:
                self._apply_theme(new_theme)

    def _apply_theme(self, theme: str):
        C.set_theme(theme)
        self._setup_window()
        self._setup_ui()
        self._apply_state(self._orb._state)
        self._orb.set_state(self._orb._state)
        self.showFullScreen()

    def _on_config_saved(self, cfg: dict):
        if self.on_config_saved:
            self.on_config_saved(cfg)

    def _toggle_mute(self):
        self._muted = not self._muted
        self.set_state("MUTED" if self._muted else "IDLE")
        if self.on_mute_command:
            self.on_mute_command(self._muted)
        self.showFullScreen()
        self.raise_()

    def show_main(self):
        if self._float_orb:
            self._float_orb.hide_float()
        self.showFullScreen()
        self.raise_()
        self.activateWindow()

    def _apply_state(self, state: str):
        self._orb.set_state(state)

    def _send_chat(self):
        text = self._chat_input.text().strip()
        if not text:
            return
        self._chat_input.clear()
        # Show in transcript
        self._append_transcript(f"<b style='color:{C.PRI}'>Tú:</b> {text}")
        if self.on_text_command:
            self.on_text_command(text)

    def _append_transcript(self, html: str):
        self._transcript.append(html)
        sb = self._transcript.verticalScrollBar()
        if sb:
            sb.setValue(sb.maximum())

    def _update_eris_line(self, text: str):
        """Replace the last ERIS line in transcript with accumulated text."""
        doc = self._transcript.document()
        block = doc.lastBlock()
        if block.isValid() and block.text().startswith("ERIS:"):
            cursor = self._transcript.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            cursor.movePosition(cursor.MoveOperation.StartOfBlock)
            cursor.movePosition(cursor.MoveOperation.EndOfBlock, cursor.MoveMode.KeepAnchor)
            cursor.insertHtml(f"<span style='color:{C.PRI_LIGHT}'><b>ERIS:</b> {text}</span>")
        else:
            self._append_transcript(f"<span style='color:{C.PRI_LIGHT}'><b>ERIS:</b> {text}</span>")
        sb = self._transcript.verticalScrollBar()
        if sb:
            sb.setValue(sb.maximum())

    def _on_chunk(self, chunk: str):
        if chunk == "__clear__":
            self._caption.setText("")
            self._transcript.clear()
            self._eris_accum = ""
            return
        text = self._caption.text() + chunk
        if len(text) > 200:
            text = text[-200:]
        self._caption.setText(text)
        # Accumulate and show in transcript
        self._eris_accum = self._eris_accum + chunk
        self._update_eris_line(self._eris_accum)

    def _quit_app(self):
        self._shutdown_sig.emit()
        QApplication.quit()

    # ── Public API ─────────────────────────────────────────────────────────
    def set_state(self, state: str):
        self._state_sig.emit(state)
        if self._float_orb:
            self._float_orb.set_state(state)

    def write_log(self, text: str):
        if text == "__hide__":
            return
        if text.startswith("__"):
            return
        clean = text.replace("SYS: ", "").replace("ERIS: ", "").replace("⚡ ", "")
        if clean != text:
            clean = "\n" + clean
        current = self._caption.text()
        if len(current) + len(clean) > 300:
            current = current[-200:]
        self._caption.setText(current + clean)
        # Also show in transcript
        parts = text.split(":", 1)
        if len(parts) >= 2:
            label = parts[0].strip()
            msg = parts[1].strip()
            color = C.TEXT_DIM
            if label in ("SYS", "ERIS"):
                color = C.PRI_LIGHT
            elif label == "ERR":
                color = C.ERROR
            self._append_transcript(f"<span style='color:{color}'><b>{label}:</b> {msg}</span>")

    def stream_eris_chunk(self, chunk: str):
        self._chunk_sig.emit(chunk)

    def clear_eris_response(self):
        self._chunk_sig.emit("__clear__")

    def set_audio_level(self, level: float):
        self._orb.set_audio_level(level)
        if self._float_orb:
            self._float_orb.set_audio_level(level)

        # ── Public API Facade ───────────────────────────────────────────────────────────
class ErisUI:
    """Public API for main.py integration."""

    def __init__(self, face_png: str = ""):
        os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu --no-sandbox --disable-software-rasterizer")
        self._app = QApplication.instance() or QApplication(sys.argv)
        _load_saved_theme()
        self._app.setStyle("Fusion")
        self._app.setQuitOnLastWindowClosed(False)

        pixmap = QPixmap(400, 300)
        pixmap.fill(QColor(C.BG))
        self._splash = QSplashScreen(pixmap)
        self._splash.show()
        self._splash.showMessage("ERIS v2.7.6", Qt.AlignmentFlag.AlignCenter, QColor(C.PRI))
        self._app.processEvents()

        self._float_orb = FloatingOrb()
        try:
            self._win = MainWindow(float_orb=self._float_orb)
        except Exception as _mw_err:
            self._splash.close()
            from core.platform import show_messagebox
            show_messagebox(
                "ERIS — Error de interfaz",
                f"No se pudo crear la ventana principal.\n\n{_mw_err}\n\nRevisá drivers de video o recursos faltantes.",
                "error",
            )
            raise
        self._float_orb.show_main_callback = self._orb_clicked
        self._app.processEvents()
        self._splash.finish(self._win)
        self._win.show()

        class _RootShim:
            def mainloop(self):
                QApplication.instance().exec()
            def protocol(self, *a): pass
        self.root = _RootShim()
        self._ready = False

    @property
    def muted(self) -> bool:
        return self._win._muted

    @muted.setter
    def muted(self, v: bool):
        self._win._muted = v
        self._win.set_state("MUTED" if v else "IDLE")

    @property
    def current_file(self) -> str:
        return ""

    @property
    def on_text_command(self):
        return self._win.on_text_command

    @on_text_command.setter
    def on_text_command(self, cb):
        self._win.on_text_command = cb

    @property
    def on_stop_command(self):
        return self._win.on_stop_command

    @on_stop_command.setter
    def on_stop_command(self, cb):
        self._win.on_stop_command = cb

    @property
    def on_config_saved(self):
        return self._win.on_config_saved

    @on_config_saved.setter
    def on_config_saved(self, cb):
        self._win.on_config_saved = cb

    @property
    def on_mute_command(self):
        return self._win.on_mute_command

    @on_mute_command.setter
    def on_mute_command(self, cb):
        self._win.on_mute_command = cb

    def set_state(self, state: str):
        self._win.set_state(state)

    def write_log(self, text: str):
        self._win.write_log(text)

    def wait_for_api_key(self):
        self._ready = True

    def start_speaking(self):
        self._win.set_state("SPEAKING")

    def stop_speaking(self):
        self._win.set_state("LISTENING")

    def set_audio_level(self, level: float):
        self._win.set_audio_level(level)

    def _orb_clicked(self):
        """Clic en el orbe flotante: despierta a ERIS para escuchar,
        sin abrir la ventana completa ni robar foco."""
        cb = getattr(self, "_orb_wake_callback", None)
        if cb:
            try:
                cb()
                return
            except Exception:
                pass
        self._win.show_main()

    def stream_eris_chunk(self, chunk: str):
        self._win.stream_eris_chunk(chunk)

    def clear_eris_response(self):
        self._win.clear_eris_response()
