"""
ERIS UI v7.0 — Gold Glassmorphism
JARVIS-IA inspired: WebGL orb, bento-grid dashboard, gold/amber glassmorphism.
"""
from __future__ import annotations
import platform as _plat
_IS_WIN = _plat.system() == "Windows"
if not _IS_WIN:
    class _Noop:
        def __call__(self, *a, **kw): return 0
        def __getitem__(self, k): return _Noop()
        def __getattr__(self, n): return _Noop()
    _WIN32 = _Noop()
    _KERNEL32 = _Noop()
    _SHELL32 = _Noop()
    _WINMM = _Noop()
else:
    import ctypes as _ctypes
    _WIN32 = _ctypes.windll.user32
    _KERNEL32 = _ctypes.windll.kernel32
    _SHELL32 = _ctypes.windll.shell32
    _WINMM = _ctypes.windll.winmm

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
    Qt, QTimer, pyqtSignal, pyqtSlot, QRect, QRectF, QUrl, QObject, QPointF,
)
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtGui import (
    QAction, QBrush, QColor, QConicalGradient, QDragEnterEvent, QDropEvent,
    QFont, QIcon, QImage, QKeySequence, QLinearGradient, QPainter,
    QPainterPath, QPalette, QPen, QPixmap, QPolygonF, QRadialGradient, QRegion,
    QTransform, QWheelEvent, QWindow, QCursor, QFontDatabase,
)
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QFileDialog,
    QFormLayout, QFrame, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QPushButton, QScrollArea, QSplashScreen, QSystemTrayIcon,
    QTextEdit, QVBoxLayout, QWidget, QMenu, QTabWidget, QSlider,
    QSplitter, QSizePolicy, QRadioButton,
)
from PyQt6.QtGui import QShortcut, QKeySequence
# Nota: QtWebEngine (Chromium) se importa SOLO dentro de WebGLOrb.__init__
# (lazy). Importarlo al top cargaba Chromium en cada proceso y causaba
# crashes 0x80000003 en Qt6WebEngineCore aunque nunca se usara.
from face_design import FaceWidget
from core.ui_panels import TerminalOverlay, CommandDeckWidget, FloatingPermiso, apply_theme_from_ui

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


# ── Sistema de temas (se parte a gui/styles.py en el refactor T4) ────────────
# Durante la transición, ui.py re-exporta desde gui/styles para no romper
# las importaciones de main.py y de otros modulos.
from gui.styles import THEMES, THEME_LIST, C, _base_dir as _styles_base_dir, _user_cfg_dir as _styles_user_cfg_dir, _load_saved_theme  # noqa: F401
from gui.widgets.glass import GlassWidget, SystemWidget, WeatherWidget, TodoWidget, SpotifyWidget, NotesWidget  # noqa: F401
from gui.widgets.sidebar import _SidebarBtn, _NeonField  # noqa: F401
from gui.widgets.chat import _ChatInput, FileDropZone  # noqa: F401
from gui.widgets.settings import SettingsDialog  # noqa: F401
from gui.widgets.orb import _OrbBridge, WebGLOrb, Particle, ParticleOrb, _ORB_ACCENTS  # noqa: F401

# Aliases locales para que el resto de ui.py siga funcionando sin cambios:
_base_dir = _styles_base_dir
_user_cfg_dir = _styles_user_cfg_dir

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
        from PyQt6.QtWebEngineWidgets import QWebEngineView
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


# ParticleOrb ahora vive en gui/widgets/orb.py (refactor T4).


# ── Glassmorphism Widget Base ───────────────────────────────────────────────────
# GlassWidget y subclases (System, Weather, Todo, Spotify, Notes) movidos
# a gui/widgets/glass.py (refactor T4). Se re-importan arriba para
# mantener `from ui import GlassWidget` etc.


# ── Futuristic Settings Dialog ─────────────────────────────────────────────────
# _SidebarBtn y _NeonField movidos a gui/widgets/sidebar.py (refactor T4).


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


# ── VRM 3D Avatar (Modelo 3D de Eris, Always on Top) ────────────────────────────
class _VrmBridge(QObject):
    """Bridge JS→Python for the VRM viewer (model loaded / errores)."""
    def __init__(self, avatar):
        super().__init__()
        self.avatar = avatar

    @pyqtSlot(str)
    def log(self, msg):
        pass

    @pyqtSlot(str)
    def error(self, msg):
        pass

    @pyqtSlot()
    def model_loaded(self):
        self.avatar._on_model_loaded()


class VrmAvatar(QWidget):
    """Ventana flotante que renderiza el modelo 3D Eris.vrm (three-vrm).

    Usa un QWebEngineView transparente que carga viewer.html servido por un
    mini HTTP server local (los ES modules no cargan desde file://). Se
    comunica con Python vía QWebEngineView.runJavaScript (Python→JS) y
    QWebChannel (JS→Python, mínimos).
    """
    states = ("IDLE", "LISTENING", "THINKING", "SPEAKING", "INITIATING", "MUTED", "ERROR")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedSize(340, 480)

        from PyQt6.QtWebEngineWidgets import QWebEngineView
        from PyQt6.QtWebEngineCore import QWebEngineSettings

        self._view = QWebEngineView(self)
        self._view.setStyleSheet("background: transparent; border: none;")
        self._view.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._view.setGeometry(0, 0, 340, 480)
        self._view.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        try:
            self._view.page().setBackgroundColor(Qt.GlobalColor.transparent)
        except Exception:
            pass

        self._channel = QWebChannel()
        self._bridge = _VrmBridge(self)
        self._channel.registerObject("pyBridge", self._bridge)
        self._view.page().setWebChannel(self._channel)

        s = self._view.settings()
        s.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.ScreenCaptureEnabled, True)

        self._loaded = False
        self._pending_state = None
        self._view.loadFinished.connect(self._on_load_finished)

        # Parámetros de animación (espejo de window.ANIM en viewer.html)
        self._anim_cfg = {
            "abertura_brazos": 0.12, "swing_brazos": 0.015, "flex_codos": 0.55,
            "flex_munecas": 0.05, "curva_dedos": 0.15, "respiracion": 0.015,
            "balanceo_caderas": 0.005, "giro_cuerpo": 0.06, "peso_giro": 0.025,
            "contragiro_tronco": 0.35, "compensa_cabeza": 0.8,
            "mirada_cabeza": 0.035, "peso_piernas": 0.008, "flote": 0.004,
        }
        self.load_anim_config()

        try:
            from core.vrm_server import vrm_server_url
            self._view.setUrl(QUrl(vrm_server_url()))
        except Exception:
            self._view.setHtml(
                "<html><body style='background:transparent;color:white;font:12px sans-serif'>"
                "<div style='display:flex;align-items:center;justify-content:center;height:100%'>"
                "Eris — VRM no disponible</div></body></html>"
            )
        self._view.show()

        self._drag_pos = None
        self._drag_start = None
        self._visible = False
        self._state = "IDLE"
        self.show_main_callback = None

    def _on_load_finished(self, ok: bool):
        self._loaded = ok
        if ok:
            self.apply_anim_config()
            if self._pending_state:
                self.set_state(self._pending_state)
                self._pending_state = None

    def _on_model_loaded(self):
        if self._pending_state:
            self.set_state(self._pending_state)
            self._pending_state = None

    def _js(self, script: str):
        if not self._loaded:
            return
        try:
            self._view.page().runJavaScript(script)
        except Exception:
            pass

    # ── API pública (misma firma que FloatingOrb/WebGLOrb) ──
    def set_state(self, state: str):
        self._state = state
        if not self._loaded:
            self._pending_state = state
            return
        self._js(f"window.updateState && window.updateState({json.dumps(state)});")

    def set_audio_level(self, level: float):
        self._js(f"window.updateVolume && window.updateVolume({float(max(0.0, min(1.0, level)))});")

    def set_expression(self, emotion: str):
        self._js(f"window.setExpression && window.setExpression({json.dumps(emotion)});")

    def set_emotional_color(self, hex_color: str, strength: float = 0.5, emotion: str = ""):
        if emotion:
            self.set_expression(emotion)

    def show_float(self):
        self._visible = True
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - self.width() - 20, screen.height() // 3 - 40)
        self.show()
        self.raise_()
        self.activateWindow()
        self._js("window.updateState && window.updateState('IDLE');")

    def hide_float(self):
        self._visible = False
        self.hide()

    # ── drag & click (mismo patrón que FloatingOrb) ──
    def _on_click(self, e):
        if self.show_main_callback:
            self.show_main_callback()

    # ── Config de animación (persistente en config/api_keys.json → "vrm_anim") ──
    @staticmethod
    def _anim_cfg_path():
        from core.logging_setup import API_CONFIG_PATH
        return API_CONFIG_PATH

    def load_anim_config(self):
        try:
            p = self._anim_cfg_path()
            if p and p.exists():
                cfg = json.loads(p.read_text("utf-8"))
                anim = cfg.get("vrm_anim", {})
                if anim:
                    self._anim_cfg = dict(anim)
        except Exception:
            pass
        return dict(self._anim_cfg)

    def save_anim_config(self):
        try:
            p = self._anim_cfg_path()
            if p and p.exists():
                cfg = json.loads(p.read_text("utf-8"))
            else:
                cfg = {}
            cfg["vrm_anim"] = dict(self._anim_cfg)
            p.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), "utf-8")
        except Exception:
            pass

    def set_anim_param(self, name: str, value: float):
        self._anim_cfg[name] = float(value)
        self._js(f"window.setAnimParam && window.setAnimParam({json.dumps(name)}, {float(value)});")

    def apply_anim_config(self):
        cfg = dict(self._anim_cfg)
        self._js(f"window.applyAnimConfig && window.applyAnimConfig({json.dumps(cfg)});")

    def set_config_key(self, key: str, value):
        try:
            p = self._anim_cfg_path()
            if p and p.exists():
                cfg = json.loads(p.read_text("utf-8"))
            else:
                cfg = {}
            cfg[key] = value
            p.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), "utf-8")
        except Exception:
            pass

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

class VrmAnimStudio(QDialog):
    """Entorno de moldeado del avatar 3D: sliders por grupo (brazos, caderas,
    manos, dedos, peso de giro, respiración, cabeza) aplicados EN VIVO al
    VrmAvatar. Al guardar persiste en config/api_keys.json ("vrm_anim")."""

    def __init__(self, avatar, parent=None):
        super().__init__(parent)
        self._avatar = avatar
        self.setWindowTitle("ERIS — Studio de animación 3D")
        self.setMinimumWidth(460)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 12)

        hint = QLabel("Ajustá los movimientos en vivo. El modelo se actualiza mientras movés cada barra.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: %s; font-size: 11px;" % C.TEXT)
        layout.addWidget(hint)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        body = QWidget()
        form = QVBoxLayout(body)
        form.setContentsMargins(4, 4, 4, 4)
        form.setSpacing(10)
        scroll.setWidget(body)
        layout.addWidget(scroll, 1)

        self._sliders = {}
        for key, (label, lo, hi, step, default) in self._rows().items():
            row = QHBoxLayout()
            v = self._avatar._anim_cfg.get(key, default)
            lbl = QLabel(label)
            lbl.setFixedWidth(150)
            lbl.setStyleSheet("color: %s; font-size: 11px;" % C.TEXT)
            row.addWidget(lbl)
            sl = QSlider(Qt.Orientation.Horizontal)
            sl.setRange(int(lo / step), int(hi / step))
            sl.setValue(int(v / step))
            sl.setStyleSheet("QSlider::groove:horizontal { height: 4px; background: #444; border-radius: 2px; }"
                             "QSlider::handle:horizontal { width: 14px; background: %s; border-radius: 7px; margin: -5px 0; }" % C.PRI)
            val = QLabel("%.3f" % v)
            val.setFixedWidth(52)
            val.setStyleSheet("color: %s; font-size: 11px;" % C.ACC)
            row.addWidget(sl)
            row.addWidget(val)
            form.addLayout(row)
            self._sliders[key] = (sl, val, step)

            def _on_change(key=key, sl=sl, val=val, step=step):
                nv = sl.value() * step
                val.setText("%.3f" % nv)
                self._avatar.set_anim_param(key, nv)

            sl.valueChanged.connect(_on_change)

        btns = QHBoxLayout()
        btns.addStretch(1)
        reset = QPushButton("⏮ Restablecer")
        save = QPushButton("✔ Guardar")
        close = QPushButton("Cerrar")
        for b in (reset, save, close):
            b.setStyleSheet(
                "QPushButton { background: %s; color: %s; border: none; border-radius: 18px;"
                "padding: 8px 18px; font-size: 12px; font-weight: 600; }"
                "QPushButton:hover { background: %s; }" % (C.PRI, C.BG, C.ACC))
        reset.clicked.connect(self._reset_defaults)
        save.clicked.connect(self._save)
        close.clicked.connect(self.accept)
        btns.addWidget(reset)
        btns.addWidget(save)
        btns.addWidget(close)
        layout.addLayout(btns)

    @staticmethod
    def _rows():
        return {
            "abertura_brazos": ("Brazos: apertura A", 0.0, 0.4, 0.005, 0.12),
            "swing_brazos": ("Brazos: vaivén", 0.0, 0.08, 0.001, 0.015),
            "flex_codos": ("Codos: flexión", 0.0, 1.2, 0.01, 0.55),
            "flex_munecas": ("Muñecas: relajación", 0.0, 0.4, 0.005, 0.05),
            "curva_dedos": ("Manos: curva dedos", 0.0, 0.5, 0.005, 0.15),
            "respiracion": ("Pecho: respiración", 0.0, 0.08, 0.001, 0.015),
            "balanceo_caderas": ("Caderas: sway", 0.0, 0.04, 0.001, 0.005),
            "giro_cuerpo": ("Cuerpo: giro lento", 0.0, 0.25, 0.005, 0.06),
            "peso_giro": ("Peso en el giro", 0.0, 0.12, 0.001, 0.025),
            "contragiro_tronco": ("Torso contra-giro", 0.0, 1.0, 0.01, 0.35),
            "compensa_cabeza": ("Cabeza compensa", 0.0, 1.5, 0.01, 0.8),
            "mirada_cabeza": ("Cabeza: mirada", 0.0, 0.12, 0.001, 0.035),
            "peso_piernas": ("Piernas: peso", 0.0, 0.05, 0.001, 0.008),
            "flote": ("Flote vertical", 0.0, 0.02, 0.0005, 0.004),
        }

    def _reset_defaults(self):
        for key, (label, lo, hi, step, default) in self._rows().items():
            sl, val, st = self._sliders[key]
            sl.setValue(int(default / step))
            self._avatar.set_anim_param(key, default)
        self._avatar.save_anim_config()

    def _save(self):
        self._avatar.save_anim_config()

class _OptionCard(QWidget):
    """Tarjeta clicable por opción. Single = selección única; Multi = checkbox.

    self.toggled -> signal-esque: main dialog conecta callback al hacer click.
    """
    selected_changed = pyqtSignal(bool)

    def __init__(self, text: str, index: int, recommended: bool = False,
                 multi: bool = False, checked: bool = False, parent=None):
        super().__init__(parent)
        self.index = index
        self._selected = checked
        self._recommended = recommended
        self._multi = multi
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(46)
        self._build(text)
        self._apply(none=False)

    def _build(self, text):
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 6, 14, 6)
        self._rad = QRadioButton() if not self._multi else QCheckBox()
        self._rad.setChecked(self._selected)
        self._rad.setText("")
        self._rad.setFixedWidth(22)
        self._rad.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        lay.addWidget(self._rad)
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setStyleSheet("background: transparent; border: none; color: %s; font-size: 12px;" % C.TEXT)
        self._lbl = lbl
        lay.addWidget(lbl, 1)
        if self._recommended:
            rec = QLabel("⭐ Recomendado")
            rec.setAlignment(Qt.AlignmentFlag.AlignCenter)
            rec.setStyleSheet(
                "background: %s; color: %s; border-radius: 9px; padding: 2px 8px;"
                "font-size: 9px; font-weight: bold; letter-spacing: 1px;" % (C.PRI, C.BG))
            lay.addWidget(rec)
        self._rad.toggled.connect(self._on_toggled)
        self.mousePressEvent = self._on_click

    def _on_click(self, event):
        if self._multi:
            self._rad.toggle()   # checkbox: toggle sin cambiar
        else:
            self.set_selected(True)   # single: click = elegir
        self._apply()

    def _on_toggled(self, checked):
        self._selected = checked
        self._apply()

    def set_selected(self, selected: bool):
        self._selected = selected
        if hasattr(self, "_rad"):
            self._rad.setChecked(selected)
            self._apply()

    def is_selected(self) -> bool:
        return self._selected

    def _apply(self, none=True):
        if not hasattr(self, "_rad"):
            return
        sel = self._selected
        border = C.PRI if sel else C.BORDER
        bg = C.BG2 if not sel else C.BG3
        glow = C.PRI if sel else "transparent"
        self.setStyleSheet(
            f"QWidget {{ background: {bg}; border: 1px solid {border}; "
            f"border-radius: 12px; }}")
        if sel:
            self._lbl.setStyleSheet(
                "background: transparent; border: none; color: %s; font-size: 12px; font-weight: bold;" % C.PRI)


class OptionDialog(QDialog):
    """Menú interactivo de Eris: pregunta con opciones, recomendada, single/multi,
    respuesta custom y 'skip'. Estilo glassmorphism como el resto de la app."""

    def __init__(self, question: str, options, multi: bool = False,
                 recommended=None, allow_custom: bool = False,
                 default: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Eris te pregunta…")
        self.setWindowFlags(Qt.WindowType.Dialog
                            | Qt.WindowType.WindowStaysOnTopHint)
        self._multi = multi
        self._custom_text = ""
        self._result = [] if multi else None
        self._allow_custom = allow_custom

        # Recomendada: acepta índice (int) o texto (str) o "" nada
        rec = None
        if isinstance(recommended, int):
            rec = recommended
        elif isinstance(recommended, str):
            for i, o in enumerate(options):
                if str(o).strip().lower() == recommended.strip().lower():
                    rec = i
                    break
                if recommended.lower() in str(o).lower():
                    rec = i
                    break

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        outer = QWidget()
        outer.setObjectName("optRoot")
        outer.setStyleSheet(f"""
            #optRoot {{ background: {C.BG2}; border: 1px solid {C.BORDER};
                        border-radius: 16px; }}
        """)

        main = QVBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)
        main.addWidget(outer)
        olay = QVBoxLayout(outer)
        olay.setContentsMargins(20, 18, 20, 16)

        # Header
        hdr = QLabel("❓ ERIS PREGUNTA")
        hdr.setStyleSheet(f"color: {C.PRI}; font-size: 10px; font-weight: bold; letter-spacing: 3px;")
        olay.addWidget(hdr)

        qlbl = QLabel(question)
        qlbl.setWordWrap(True)
        qlbl.setStyleSheet(f"color: {C.TEXT}; font-size: 14px; font-weight: bold;")
        olay.addWidget(qlbl)
        olay.addSpacing(8)

        hint = QLabel("Seleccioná una opción" if not multi else "Podés seleccionar varias opciones")
        hint.setStyleSheet(f"color: {C.SUBALT if hasattr(C,'SUBALT') else C.BORDER}; font-size: 10px;")
        olay.addWidget(hint)
        olay.addSpacing(6)

        # Options area (scroll si hay muchas)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")
        body = QWidget()
        body.setStyleSheet("background: transparent;")
        bl = QVBoxLayout(body)
        bl.setContentsMargins(0, 0, 6, 0)
        bl.setSpacing(8)
        self._cards = []
        for i, opt in enumerate(options):
            card = _OptionCard(str(opt), i, recommended=(i == rec),
                               multi=multi,
                               checked=multi and rec is not None and i == rec)
            card.selected_changed.connect(lambda s, k=i: self._card_toggled(k, s))
            bl.addWidget(card)
            self._cards.append(card)
        bl.addStretch()
        scroll.setWidget(body)
        scroll.setFixedHeight(min(320, 56 + len(options) * 56))
        olay.addWidget(scroll)

        # Custom answer
        self._custom = QLineEdit()
        self._custom.setPlaceholderText("O escribí tu propia respuesta…")
        self._custom.setStyleSheet(f"""
            QLineEdit {{ background: {C.BG3}; color: {C.TEXT};
                border: 1px solid {C.BORDER}; border-radius: 10px;
                padding: 8px 12px; font-size: 12px; }}
            QLineEdit:focus {{ border: 1px solid {C.PRI}; }}
        """)
        if allow_custom:
            self._custom.setVisible(True)
            olay.addWidget(self._custom)
        else:
            self._custom.setVisible(False)
        if default:
            self._custom.setPlaceholderText(default)

        # Buttons
        btns = QHBoxLayout()
        skip = QPushButton("➖ Saltar (skip)")
        skip.setCursor(Qt.CursorShape.PointingHandCursor)
        skip.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {C.BORDER};
                border: 1px solid {C.BORDER}; border-radius: 10px;
                padding: 8px 16px; font-size: 11px; }}
            QPushButton:hover {{ color: {C.TEXT}; border-color: {C.TEXT}; }}
        """)
        skip.clicked.connect(lambda: self.done(QDialog.DialogCode.Rejected))
        self._ok = QPushButton("✅ Confirmar" if not multi else "✅ Confirmar selección")
        self._ok.setCursor(Qt.CursorShape.PointingHandCursor)
        self._ok.setStyleSheet(f"""
            QPushButton {{ background: {C.PRI}; color: {C.BG};
                border: none; border-radius: 10px; padding: 8px 22px;
                font-size: 12px; font-weight: bold; }}
            QPushButton:hover {{ background: {C.PRI2 if hasattr(C,'PRI2') else C.PRI};
                color: {C.BG}; }}
        """)
        self._ok.clicked.connect(self._confirm)
        btns.addWidget(skip)
        btns.addStretch()
        btns.addWidget(self._ok)
        olay.addLayout(btns)

        # Full width: topmost dialog with fixed size
        self.setFixedWidth(480)

    def _card_toggled(self, index, _s):
        if self._multi:
            return
        # single: al elegir una, se deseleccionan las otras
        for i, card in enumerate(self._cards):
            card.set_selected(i == index)
        self._ok.setEnabled(True)

    def _confirm(self):
        if self._multi:
            self._result = [c.index for c in self._cards if c.is_selected()]
        else:
            sel = [c.index for c in self._cards if c.is_selected()]
            self._result = sel[0] if sel else None
        cust = self._custom.text().strip() if self._allow_custom else ""
        self._custom_text = cust
        self._ok.setEnabled(True)
        self.done(QDialog.DialogCode.Accepted)

    def result_values(self):
        """Devuelve índice(s) o texto custom, según lo elegido."""
        if self._custom_text:
            return self._custom_text
        if self._multi:
            return self._result
        return self._result

class MainWindow(QMainWindow):
    _log_sig = pyqtSignal(str)
    _state_sig = pyqtSignal(str)
    _chunk_sig = pyqtSignal(str)
    _shutdown_sig = pyqtSignal()

    def __init__(self, float_orb=None, vrm_avatar=None):
        super().__init__()
        self.on_text_command = None
        self.on_stop_command = None
        self.on_config_saved = None
        self.on_mute_command = None
        self._muted = False
        self._float_orb = float_orb
        self._vrm_avatar = vrm_avatar
        self._eris_accum = ""
        self._floating_permiso = FloatingPermiso()
        self._drag_pos = None

        self._setup_window()
        self._setup_ui()
        self._setup_tray()
        self._setup_signals()
        self._setup_shortcuts()
        self.show()
        # Try acrylic only if frameless was enabled
        try:
            self._try_acrylic()
        except Exception:
            pass

    def _setup_window(self):
        self.setWindowTitle("ERIS-AGENT")
        self.setMinimumSize(500, 400)
        self.resize(1000, 750)
        # Center on screen
        screen = QApplication.primaryScreen().geometry()
        self.move(max(0, (screen.width() - 1000) // 2), max(0, (screen.height() - 750) // 2))
        # Dark background via palette (works with normal window)
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(C.BG))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(C.TEXT))
        palette.setColor(QPalette.ColorRole.Base, QColor(C.BG2))
        palette.setColor(QPalette.ColorRole.Text, QColor(C.TEXT))
        self.setPalette(palette)
        self.setStyleSheet(f"""
            QMainWindow {{ background-color: {C.BG}; }}
            QWidget {{ font-family: 'Segoe UI', sans-serif; }}
        """)
        icon_path = str(_base_dir() / "assets" / "ICOERIS.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        try:
            import ctypes
            _SHELL32.SetCurrentProcessExplicitAppUserModelID("ERIS.Assistant.v2")
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
            _WIN32.SetWindowCompositionAttribute(hwnd, ctypes.pointer(wcd))
        except Exception:
            pass

    def _setup_ui(self):
        central = QWidget()
        central.setStyleSheet(f"background: {C.BG};")
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── Splitter: main content | terminal panel (toggleable) ──
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background: {C.BORDER};
                width: 1px;
            }}
            QSplitter::handle:hover {{
                background: {C.PRI_LIGHT};
                width: 2px;
            }}
        """)
        self._splitter.setHandleWidth(1)

        # Left side: main content
        main_widget = QWidget()
        main_widget.setStyleSheet(f"background: {C.BG};")
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Terminal panel (right side of splitter) ──
        self._term_panel = TerminalOverlay()
        self._term_panel.hide()

        # ── Command Deck panel (cola de intents, toggle Ctrl+D) ──
        self._deck_panel = CommandDeckWidget()
        self._deck_panel.hide()

        self._splitter.addWidget(main_widget)
        self._splitter.addWidget(self._term_panel)
        self._splitter.addWidget(self._deck_panel)
        self._splitter.setSizes([700, 0, 0])
        self._splitter.setStretchFactor(0, 1)
        self._splitter.setStretchFactor(1, 0)
        self._splitter.setStretchFactor(2, 0)

        root_layout.addWidget(self._splitter)

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

        self._face = FaceWidget("neutral")
        layout.addWidget(self._face, 1)
        self._apply_central_visual()

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

        self._img_btn = QPushButton("🖼")
        self._img_btn.setFixedSize(34, 34)
        self._img_btn.setToolTip("Subir imagen (también puedes arrastrarla aquí)")
        self._img_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._img_btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(255,255,255,0.05); color: {C.PRI};
                border: 1px solid {C.BORDER}; border-radius: 8px; font-size: 15px;
            }}
            QPushButton:hover {{ background: rgba(255,255,255,0.12); color: {C.PRI_LIGHT}; }}
        """)
        self._img_btn.clicked.connect(self._pick_image)

        self._doc_btn = QPushButton("📄")
        self._doc_btn.setFixedSize(34, 34)
        self._doc_btn.setToolTip("Subir documento (PDF, Word, Excel, PowerPoint, txt, código… también puedes arrastrarlo aquí)")
        self._doc_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._doc_btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(255,255,255,0.05); color: {C.PRI};
                border: 1px solid {C.BORDER}; border-radius: 8px; font-size: 15px;
            }}
            QPushButton:hover {{ background: rgba(255,255,255,0.12); color: {C.PRI_LIGHT}; }}
        """)
        self._doc_btn.clicked.connect(self._pick_document)

        self._chat_input = _ChatInput()
        self._chat_input.setPlaceholderText("Escribele a ERIS...")
        self._chat_input.image_dropped.connect(self._send_image)
        self._chat_input.doc_dropped.connect(self._send_document)
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

        input_row.addWidget(self._img_btn)
        input_row.addWidget(self._doc_btn)
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
        QShortcut(QKeySequence("Ctrl+T"), self).activated.connect(self._toggle_terminal)
        QShortcut(QKeySequence("Ctrl+D"), self).activated.connect(self._toggle_deck)
        QShortcut(QKeySequence("Escape"), self).activated.connect(self._go_to_orb)
        QShortcut(QKeySequence("Ctrl+Alt+A"), self).activated.connect(self._open_anim_studio)
        QShortcut(QKeySequence("Ctrl+Q"), self).activated.connect(self._quit_app)

    def _go_to_orb(self):
        """Oculta la ventana principal, muestra orbe flotante o avatar 3D."""
        floating = self._central_visual_cfg("floating_visual", "orb") == "vrm"
        use_vrm = floating and self._vrm_avatar is not None
        if use_vrm:
            self._vrm_avatar.show_float()
        elif self._float_orb:
            self._float_orb.show_float()
        self.hide()

    def _open_anim_studio(self):
        """Abre el estudio de animación 3D (Ctrl+Alt+A)."""
        if self._vrm_avatar is None:
            return
        studio = VrmAnimStudio(self._vrm_avatar, self)
        studio.exec()

    def _setup_tray(self):
        icon_path = str(_base_dir() / "assets" / "ICOERIS.ico")
        icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()
        self._tray = QSystemTrayIcon(icon, self)
        self._tray.setToolTip("ERIS-AGENT")
        menu = QMenu()
        show_a = menu.addAction("Show")
        show_a.triggered.connect(lambda: (self.show(), self.raise_(), self.activateWindow()))
        quit_a = menu.addAction("Quit")
        quit_a.triggered.connect(self._quit_app)
        self._tray.setContextMenu(menu)
        self._tray.show()
        self._tray.activated.connect(lambda r: (self.show(), self.raise_(), self.activateWindow()) if r == QSystemTrayIcon.ActivationReason.DoubleClick else None)

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
        apply_theme_from_ui(THEMES.get(theme, THEMES["gold"]))
        self._setup_window()
        self._setup_ui()
        self._apply_state(self._orb._state)
        self._orb.set_state(self._orb._state)
        if hasattr(self, '_term_panel') and self._term_panel:
            self._term_panel.refresh_theme()
        self.show()

    def _central_visual_cfg(self, key: str = "central_visual", default: str = "face") -> str:
        try:
            from core.logging_setup import API_CONFIG_PATH
            if API_CONFIG_PATH.exists():
                return json.loads(API_CONFIG_PATH.read_text("utf-8")).get(key, default)
        except Exception:
            pass
        return default

    def _apply_central_visual(self, mode: str = ""):
        mode = mode or self._central_visual_cfg()
        if not hasattr(self, "_face"):
            return
        face_mode = mode == "face"
        self._face.setVisible(face_mode)
        self._orb.setVisible(not face_mode)
        self._visual_mode = "face" if face_mode else "orb"
        if face_mode:
            self._apply_state(getattr(self._orb, "_state", "IDLE"))

    def _on_config_saved(self, cfg: dict):
        self._apply_central_visual(cfg.get("central_visual", "face"))
        if self.on_config_saved:
            self.on_config_saved(cfg)

    def _toggle_mute(self):
        self._muted = not self._muted
        self.set_state("MUTED" if self._muted else "IDLE")
        if self.on_mute_command:
            self.on_mute_command(self._muted)
        self.show()
        self.raise_()

    def _toggle_terminal(self):
        if hasattr(self, '_term_panel') and self._term_panel:
            deck_vis = self._deck_panel is not None and self._deck_panel._visible
            if self._term_panel._visible:
                self._term_panel.hide()
                self._term_panel._visible = False
                self._splitter.setSizes([1, 0, 1] if deck_vis else [1, 0, 0])
            else:
                self._term_panel.show()
                self._term_panel._visible = True
                self._splitter.setSizes([1, 1, 1] if deck_vis else [1, 1, 0])

    def _toggle_deck(self):
        if hasattr(self, '_deck_panel') and self._deck_panel:
            term_vis = self._term_panel._visible
            if self._deck_panel._visible:
                self._deck_panel.hide()
                self._deck_panel._visible = False
                self._splitter.setSizes([1, 1 if term_vis else 0, 0])
            else:
                self._deck_panel.show()
                self._deck_panel._visible = True
                self._deck_panel.refresh()
                self._splitter.setSizes([1, 1 if term_vis else 0, 1])

    def show_main(self):
        if self._float_orb:
            self._float_orb.hide_float()
        if self._vrm_avatar:
            self._vrm_avatar.hide_float()
        self.show()
        self.raise_()
        self.activateWindow()

    def _apply_state(self, state: str):
        self._orb.set_state(state)
        face = getattr(self, "_face", None)
        if face is not None and face.isVisible():
            expr = {
                "IDLE": "neutral", "LISTENING": "smiling", "THINKING": "thinking",
                "SPEAKING": "happy", "INITIATING": "neutral", "MUTED": "neutral",
                "ERROR": "crying",
            }.get(state, "neutral")
            if face.music <= 0 and face.expr != expr:
                face.set_expr(expr)
            face.set_mood(state in ("IDLE", "LISTENING", "MUTED"))

    def _send_chat(self):
        text = self._chat_input.text().strip()
        if not text:
            return
        self._chat_input.clear()
        # Show in transcript
        self._append_transcript(f"<b style='color:{C.PRI}'>Tú:</b> {text}")
        if self.on_text_command:
            self.on_text_command(text)

    def _pick_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Selecciona una imagen para ERIS", "",
            "Imágenes (*.png *.jpg *.jpeg *.gif *.webp *.bmp *.tiff *.tif);;Todos los archivos (*.*)"
        )
        if path:
            self._send_image(path)

    def _send_image(self, path: str):
        path = path.strip()
        if not path:
            return
        name = os.path.basename(path)
        self._append_transcript(f"<b style='color:{C.PRI}'>Tú:</b> 🖼️ {name}")
        if self.on_text_command:
            self.on_text_command(f"[IMAGE_FILE] path={path}")

    def _pick_document(self):
        doc_filter = (
            "Documentos (*.pdf *.docx *.docm *.xlsx *.xlsm *.pptx *.pptm *.txt "
            "*.md *.csv *.json *.xml *.html *.py *.js *.ts *.java *.c *.cpp *.go "
            "*.rs *.rb *.php *.sql *.sh *.bat *.ps1 *.yaml *.yml *.toml);;"
            "Todos los archivos (*.*)"
        )
        path, _ = QFileDialog.getOpenFileName(
            self, "Selecciona un documento para ERIS", "", doc_filter
        )
        if path:
            self._send_document(path)

    def _send_document(self, path: str):
        path = path.strip()
        if not path:
            return
        name = os.path.basename(path)
        self._append_transcript(f"<b style='color:{C.PRI}'>Tú:</b> 📄 {name}")
        if self.on_text_command:
            self.on_text_command(f"[DOC_FILE] path={path}")

    def _append_transcript(self, html: str):
        self._transcript.append(html)
        sb = self._transcript.verticalScrollBar()
        if sb:
            sb.setValue(sb.maximum())

    def _append_thought(self, text: str):
        """Pensamiento interno de Eris en el transcript (cursiva y tenue)."""
        clean = text.replace("PENSANDO: ", "").replace("💭", "").strip()
        self._append_transcript(
            f"<i style='color:{getattr(C, 'TEXT_DIM', '#8a8a9a')}'>💭 {clean}</i>"
        )

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
        if self._float_orb and self._float_orb.isVisible():
            self._float_orb.set_state(state)
        if self._vrm_avatar and self._vrm_avatar.isVisible():
            self._vrm_avatar.set_state(state)

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
        # Also log to terminal panel
        if hasattr(self, '_term_panel') and self._term_panel is not None:
            if "ERR" in text or "error" in text.lower():
                self._term_panel.log_error(clean)
            else:
                self._term_panel.log_info(clean)

    def show_plan(self, steps, statuses=None):
        """Muestra el plan del agente autónomo en el transcript con estados."""
        if not steps:
            return
        statuses = statuses or []
        rows = []
        for i, step in enumerate(steps, 1):
            desc = step if isinstance(step, str) else (step.get("description", "") if isinstance(step, dict) else str(step))
            st = ""
            if i - 1 < len(statuses) and statuses[i - 1]:
                st = f" [{statuses[i - 1].upper()}]"
            rows.append(f"<b>{i}.</b> {desc}{st}")
        html = "<span style='color:#d4a94f'><b>AGENTE — PLAN</b></span><br/>" + "<br/>".join(rows)
        self._append_transcript(html)

    def _ask_dialog(self, question, options=None, multi=False, recommended=None,
                    allow_custom=False, default=""):
        """Diálogo modal interactivo (se ejecuta en el hilo Qt vía ErisUI.ask).
        Menú con opciones tipo tarjetas, opción recomendada, modo single/multi
        y respuesta custom."""
        opts = [str(o) for o in (options or [])]
        if opts:
            dlg = OptionDialog(question, opts, multi=multi,
                               recommended=recommended,
                               allow_custom=allow_custom, default=default)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                val = dlg.result_values()
                if val is None:
                    return "skip"
                return val
            return "skip"
        # Sin opciones → input libre estilo opencode
        from PyQt6.QtWidgets import QInputDialog
        text, ok = QInputDialog.getText(None, "ERIS — Pregunta", question)
        return str(text if ok else "skip")

    def stream_eris_chunk(self, chunk: str):
        self._chunk_sig.emit(chunk)

    def clear_eris_response(self):
        self._chunk_sig.emit("__clear__")

    def set_audio_level(self, level: float):
        face = getattr(self, "_face", None)
        if face is not None:
            face.set_audio(level)
        if self._orb.isVisible():
            self._orb.set_audio_level(level)
        if self._float_orb and self._float_orb.isVisible():
            self._float_orb.set_audio_level(level)
        if self._vrm_avatar and self._vrm_avatar.isVisible():
            self._vrm_avatar.set_audio_level(level)

    def set_face_speaking(self, value: bool):
        face = getattr(self, "_face", None)
        if face is not None:
            face.set_speaking(value)
        if self._vrm_avatar and self._vrm_avatar.isVisible():
            if value:
                self._vrm_avatar.set_state("SPEAKING")
            else:
                self._vrm_avatar.set_state("IDLE")

    def set_orb_audio_level(self, level: float):
        if self._orb.isVisible():
            self._orb.set_audio_level(level)
        if self._float_orb and self._float_orb.isVisible():
            self._float_orb.set_audio_level(level)
        if self._vrm_avatar and self._vrm_avatar.isVisible():
            self._vrm_avatar.set_audio_level(level)

    def set_emotional_color(self, hex_color: str, strength: float = 0.5, emotion: str = ""):
        """Tiñe el/los orbes con el sentimiento dominante de Eris."""
        if self._orb.isVisible():
            self._orb.set_emotional_color(hex_color, strength, emotion)
        if self._float_orb:
            self._float_orb.set_emotional_color(hex_color, strength, emotion)
        if self._vrm_avatar and self._vrm_avatar.isVisible():
            self._vrm_avatar.set_emotional_color(hex_color, strength, emotion)

    def set_music(self, level: float):
        face = getattr(self, "_face", None)
        if face is not None:
            face.set_music(level)

    def express_emotion(self, text: str):
        face = getattr(self, "_face", None)
        if face is not None and face.isVisible():
            face.express_emotion(text)

    def show_expression(self, name: str, text: str = ""):
        face = getattr(self, "_face", None)
        if face is not None and face.isVisible():
            face.show_expression(name, text)
            return "cara"
        return "orbe"

    def visual_mode(self) -> str:
        return getattr(self, "_visual_mode", "face")

        # ── Public API Facade ───────────────────────────────────────────────────────────
class _MarshalBridge(QObject):
    """Vive en el hilo principal de Qt. Su señal es thread-safe: emit desde
    cualquier hilo entrega el callable al event loop del hilo principal."""
    invoke = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.invoke.connect(self._run)

    def _run(self, fn):
        try:
            fn()
        except Exception as e:
            print(f"[MarshalBridge] error: {e}", flush=True)


class _NullWindow:
    """Stub window para server mode: accepta todos los llamados sin error."""
    _muted = False
    on_text_command = None
    on_stop_command = None
    on_config_saved = None
    on_mute_command = None

    def set_state(self, *a, **kw): pass
    def write_log(self, *a, **kw): pass
    def _append_thought(self, *a, **kw): pass
    def show_plan(self, *a, **kw): pass
    def _ask_dialog(self, *a, **kw): return ""
    def set_audio_level(self, *a, **kw): pass
    def set_orb_audio_level(self, *a, **kw): pass
    def set_emotional_color(self, *a, **kw): pass
    def set_face_speaking(self, *a, **kw): pass
    def set_music(self, *a, **kw): pass
    def express_emotion(self, *a, **kw): pass
    def show_expression(self, *a, **kw): pass
    def visual_mode(self): return "orb"
    def show_main(self): pass
    def stream_eris_chunk(self, *a, **kw): pass
    def clear_eris_response(self): pass
    def _toggle_terminal(self): pass
    def raise_(self): pass


class ErisUI:
    """Public API for main.py integration."""

    def __init__(self, face_png: str = "", server_mode: bool = False):
        # QtWebEngineWidgets exige importarse (o setear AA_ShareOpenGLContexts)
        # ANTES de crear la primera QApplication; si no, el import lazy dentro de
        # VrmAvatar lanza ImportError. Solo se carga si existe el modelo 3D.
        # Los flags GRÁFICOS de WebEngine los define core/gpu_config.py al
        # importar main.py (en Linux: QSG_RHI_BACKEND=opengl); aquí solo se
        # garantiza el orden del import sin tocar Chromium/Qt.
        self._vrm_model = _base_dir() / "assets" / "vrm" / "Eris.vrm"
        self._vrm_ok = False
        if self._vrm_model.exists():
            try:
                from PyQt6.QtCore import Qt as _QtC
                if QApplication.instance() is None:
                    QApplication.setAttribute(_QtC.ApplicationAttribute.AA_ShareOpenGLContexts)
                import PyQt6.QtWebEngineWidgets  # noqa: F401
                self._vrm_ok = True
            except Exception:
                self._vrm_ok = False
        self._app = QApplication.instance() or QApplication(sys.argv)
        _load_saved_theme()
        self._app.setStyle("Fusion")
        self._app.setQuitOnLastWindowClosed(False)

        # Puente al hilo principal (creado aquí, en el main thread)
        self._bridge = _MarshalBridge()

        pixmap = QPixmap(400, 300)
        pixmap.fill(QColor(C.BG))
        self._splash = QSplashScreen(pixmap)
        self._splash.show()
        try:
            from core.version import ERIS_VERSION, ERIS_STAGE
            _ver = ERIS_VERSION
            _stage = ERIS_STAGE
        except Exception:
            _ver = "4.0.0"
            _stage = "Constellation Prime"
        self._splash.showMessage(f"ERIS v{_ver} — {_stage}", Qt.AlignmentFlag.AlignCenter, QColor(C.PRI))
        self._app.processEvents()

        self._float_orb = FloatingOrb()
        self._vrm_avatar = VrmAvatar() if self._vrm_ok else None
        self._last_vol = 0.0
        if server_mode:
            # Headless: use null window stub so ErisLive/Eris motor works without GUI
            self._win = _NullWindow()
            print("[ERIS-UI] Server mode: MainWindow omitted (headless)")
        else:
            try:
                self._win = MainWindow(float_orb=self._float_orb, vrm_avatar=self._vrm_avatar)
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
        if self._vrm_avatar:
            self._vrm_avatar.show_main_callback = self._orb_clicked
        self._app.processEvents()
        if not server_mode:
            self._splash.finish(self._win)
            self._win.show()
            self._win.raise_()
            self._win.activateWindow()

        class _RootShim:
            def mainloop(self):
                if server_mode:
                    # Headless: process events in a polling loop
                    import time
                    while True:
                        QApplication.instance().processEvents()
                        time.sleep(0.05)
                else:
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
        self._marshal(self._win.set_state, "MUTED" if v else "IDLE")

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

    def _marshal(self, fn, *args, **kwargs):
        """Ejecuta fn en el hilo principal de Qt. El event loop de ERIS corre
        en un hilo separado (asyncio.run en runner thread); llamar a widgets
        Qt desde ahi causa crashes (Qt6Core fail-fast 0xc0000409 / Qt6Gui
        access violation). Uso un puente QObject con una señal (thread-safe):
        QTimer.singleShot(0, ...) desde un thread SIN event loop de Qt NUNCA
        dispara, por eso las actualizaciones de UI se perdian en silencio."""
        if threading.current_thread() is threading.main_thread():
            fn(*args, **kwargs)
        else:
            self._bridge.invoke.emit(lambda: fn(*args, **kwargs))

    def set_state(self, state: str):
        self._marshal(self._win.set_state, state)

    def inject_text(self, text: str):
        """API pública (thread-safe): inyecta texto en la GUI.

        Reusa el bridge de `_marshal` para correr el callback en el hilo de Qt,
        exactamente como si el usuario hubiera escrito en el campo de texto.
        """
        cb = self._win.on_text_command
        if cb:
            self._marshal(cb, text)

    def write_log(self, text: str):
        self._marshal(self._win.write_log, text)

    def show_thought(self, text: str):
        """Pensamiento interno de Eris (pipeline pensar→hablar): línea en
        cursiva/tenue en el transcript, no se habla."""
        self._marshal(self._win._append_thought, text)

    def show_plan(self, steps, statuses=None):
        self._marshal(self._win.show_plan, steps, statuses)

    def ask(self, question, options=None, timeout=90, multi=False,
            recommended=None, allow_custom=False, default=""):
        """Pregunta al usuario con menú interactivo: opciones en tarjetas,
        recomendada (⭐), modo single/multi y respuesta custom. Devuelve
        índice, lista de índices o texto custom. 'skip' si cancela/timeout."""
        box = {}
        done = threading.Event()

        def _show():
            try:
                box["text"] = self._win._ask_dialog(
                    question, options, multi=multi, recommended=recommended,
                    allow_custom=allow_custom, default=default)
            except Exception:
                box["text"] = "skip"
            finally:
                done.set()

        self._marshal(_show)
        if not done.wait(timeout):
            return "skip"
        return box.get("text", "skip")

    def wait_for_api_key(self):
        self._ready = True

    def start_speaking(self):
        self._marshal(self._win.set_state, "SPEAKING")

    def stop_speaking(self):
        self._marshal(self._win.set_state, "LISTENING")

    def set_audio_level(self, level: float):
        # Delegado al win (ParticleOrb actualiza atributo; FloatingOrb usa
        # runJavaScript). Se limita a ~12 Hz para no inundar el event loop
        # de Qt desde el hilo de audio.
        now = time.time()
        if now - self._last_vol > 0.08:
            self._last_vol = now
            self._marshal(self._win.set_audio_level, level)

    def set_orb_audio_level(self, level: float):
        now = time.time()
        if now - self._last_vol > 0.08:
            self._last_vol = now
            self._marshal(self._win.set_orb_audio_level, level)

    def set_orb_emotional_color(self, hex_color: str, strength: float = 0.5, emotion: str = ""):
        self._marshal(self._win.set_emotional_color, hex_color, strength, emotion)

    def set_face_speaking(self, value: bool):
        self._marshal(self._win.set_face_speaking, value)

    def set_music(self, level: float):
        self._marshal(self._win.set_music, level)

    def express_emotion(self, text: str):
        self._marshal(self._win.express_emotion, text)

    def show_expression(self, name: str, text: str = ""):
        self._marshal(self._win.show_expression, name, text)

    def visual_mode(self) -> str:
        return self._win.visual_mode()

    def _orb_clicked(self):
        """Clic en el orbe flotante: abre la interfaz completa de ERIS
        (la ventana principal). Escape (Esc) vuelve al orbe flotante."""
        self._win.show_main()

    def stream_eris_chunk(self, chunk: str):
        self._marshal(self._win.stream_eris_chunk, chunk)

    def clear_eris_response(self):
        self._marshal(self._win.clear_eris_response)

    @property
    def terminal_panel(self):
        return getattr(self._win, '_term_panel', None)


    def toggle_terminal(self):
        self._marshal(self._win._toggle_terminal)

    def log_terminal(self, msg: str, level: str = "info"):
        """Log to terminal panel from any thread."""
        tp = self.terminal_panel
        if tp is None:
            return
        def _log():
            if level == "error":
                tp.log_error(msg)
            elif level == "user":
                tp.log_user(msg)
            elif level == "speak":
                tp.log_speak(msg)
            elif level == "tool_start":
                pass  # handled by tool_dispatcher directly
            else:
                tp.log_info(msg)
        self._marshal(_log)
