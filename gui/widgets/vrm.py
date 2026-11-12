# -*- coding: utf-8 -*-
"""
gui/widgets/vrm.py — Avatar 3D VRM (flotante, Always on Top) de ERIS.

Extraído de ui.py durante el refactor T4.
Contiene:
  - _VrmBridge: puente JS→Python del visor VRM (QWebChannel)
  - VrmAvatar: ventana 340×480 frameless/transparente que carga assets/vrm/viewer.html
    servido por core.vrm_server
  - VrmAnimStudio: entorno de moldeado del avatar 3D en vivo (sliders por grupo),
    persiste en config/api_keys.json ("vrm_anim")
"""
from __future__ import annotations

import json
from pathlib import Path

from PyQt6.QtCore import QObject, QUrl, Qt, pyqtSlot
from PyQt6.QtGui import QColor
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtWebEngineCore import QWebEngineSettings
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QDialog, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QSlider, QVBoxLayout, QWidget,
)

from gui.styles import C, _base_dir


class _VrmBridge(QObject):
    """Bridge for JS→Python communication from the VRM viewer."""

    def __init__(self, avatar):
        super().__init__()
        self.avatar = avatar

    @pyqtSlot()
    def request_theme(self):
        self.avatar.sync_theme()


class VrmAvatar(QWidget):
    """Avatar 3D VRM: ventana 340×480 frameless/transparente.

    Carga assets/vrm/viewer.html servido por core.vrm_server (o un fallback HTML
    si no hay servidor). Expone la misma API pública que FloatingOrb/WebGLOrb:
    set_state, set_audio_level, set_expression, set_emotional_color,
    show_float, hide_float.
    """

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

        self._view = QWebEngineView(self)
        self._view.setStyleSheet("background: transparent; border: none;")
        self._view.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        # QWebChannel bridge
        self._channel = QWebChannel()
        self._bridge = _VrmBridge(self)
        self._channel.registerObject("pyBridge", self._bridge)
        self._view.page().setWebChannel(self._channel)

        s = self._view.settings()
        s.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)

        self._loaded = False
        self._pending_state = None
        self._view.loadFinished.connect(self._on_load_finished)

        self._anim_cfg = dict(self._default_anim_cfg())

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

    @staticmethod
    def _default_anim_cfg() -> dict:
        return {
            "abertura_brazos": 0.12, "swing_brazos": 0.015, "flex_codos": 0.55,
            "flex_munecas": 0.05, "curva_dedos": 0.15, "respiracion": 0.015,
            "balanceo_caderas": 0.005, "giro_cuerpo": 0.06, "peso_giro": 0.025,
            "contragiro_tronco": 0.35, "compensa_cabeza": 0.8,
            "mirada_cabeza": 0.035, "peso_piernas": 0.008, "flote": 0.004,
        }

    def _on_load_finished(self, ok: bool):
        self._loaded = ok
        if ok:
            self.apply_anim_config()
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
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._drag_start = e.globalPosition().toPoint()
        if e.button() == Qt.MouseButton.RightButton:
            if self.show_main_callback:
                self.show_main_callback()

    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.MouseButton.LeftButton and self._drag_pos is not None:
            self.move(e.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and self._drag_start is not None:
            dist = (e.globalPosition().toPoint() - self._drag_start).manhattanLength()
            if dist < 10:
                if self.show_main_callback:
                    self.show_main_callback()
        self._drag_pos = None
        self._drag_start = None

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
                "QPushButton:hover { background: %s; }" % (C.PRI, C.BG, C.PRI_LIGHT))
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
