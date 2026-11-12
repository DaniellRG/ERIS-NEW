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

from PyQt6.QtCore import QObject, pyqtSlot, Qt, QUrl, QTimer
from PyQt6.QtGui import QColor, QPainter, QBrush, QPen, QRadialGradient, QPointF, QPolygonF
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
        self._fast = False
        self._mouse_pos = None
        self._attract = False
        self._pulse = 0.0
        self._paint_trails = True
        self._sprite_cache = {}
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)
        self.setMouseTracking(True)

    def set_state(self, state: str):
        if state in self.states:
            self._state = state
            self._apply_frame_rate()

    def set_audio_level(self, level: float):
        self._audio_level = level * 0.5
        try:
            self._apply_frame_rate()
        except Exception:
            pass

    def set_emotional_color(self, hex_color: str, strength: float = 0.5, emotion: str = ""):
        """Tiñe el orbe con el sentimiento dominante (blend con el color de estado)
        y activa micro-acentos (corazones, chispas, lágrimas)."""
        try:
            self._emo_hex = hex_color
            self._emo_strength = max(0.0, min(1.0, strength))
            self._emo_name = str(emotion or "").lower()
        except Exception:
            pass

    def _apply_frame_rate(self):
        """FPS adaptativos con histéresis (sin sacudidas por fluctuación del
        nivel): base fluida 30 FPS, 60 FPS al hablar/pensar, respiro al ocultarse.
        Antes IDLE repintaba a 60 FPS continuos → un core al ~85% de CPU; y el
        salto 16ms↔110ms según nivel de audio causaba traba visible del orbe.

        En render POR SOFTWARE (QSG_RHI_BACKEND=software, el modo que evita el
        segfault de WebEngine en Linux) cada repintado cuesta CPU: a 60 FPS
        constantes el orbe se traba. Aquí se baja a 30 FPS de base y solo se
        sube a 60 FPS mientras habla (los bombeos se ven fluidos y el resto del
        tiempo la CPU se libera). Con aceleración (hardware) se mantiene 60 FPS."""
        import platform as _p
        _desktop_os = _p.system().lower() in ("windows", "linux")
        _soft = "soft" in os.environ.get("QSG_RHI_BACKEND", "").lower() or \
                "--disable-gpu" in os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "")
        if not self.isVisible():
            target = 300
        elif _soft:
            # Software renderer: 60 FPS SIEMPRE (el orbe se ve fluido). Para
            # compensar el costo de CPU, en paintEvent se omite el trail
            # (ahorra ~80% de las elipses) y se usa sprite cache para las
            # partículas individuales.
            self._paint_trails = False
            target = 16
        elif _desktop_os:
            target = 16   # 60 FPS constantes en cualquier SO con GPU
        elif self._state in ("MUTED", "ERROR"):
            target = 33
        elif self._state in ("THINKING", "SPEAKING"):
            target = 16   # 60 FPS reales
        elif self._audio_level > 0.12:
            self._fast = True
            target = 16
        elif self._audio_level < 0.05:
            self._fast = False
            target = 33
        else:
            target = 16 if getattr(self, "_fast", False) else 33
        if self._timer.interval() != target:
            self._timer.start(target)

    def showEvent(self, e):
        super().showEvent(e)
        self._apply_frame_rate()

    def hideEvent(self, e):
        super().hideEvent(e)
        self._apply_frame_rate()

    def _tick(self):
        self._phase += 0.02
        self._pulse = 0.5 + 0.5 * math.sin(self._phase * 2)
        cx, cy = self.width() / 2, self.height() / 2
        attract = self._attract and self._mouse_pos is not None
        mx, my = self._mouse_pos if self._mouse_pos else (cx, cy)

        # Menos partículas con render por software (120→60) para abaratar cada
        # repintado translúcido; en GPU se mantiene la densidad completa.
        target_count = 60 if "soft" in os.environ.get("QSG_RHI_BACKEND", "").lower() else 120
        if len(self._particles) < target_count:
            self._particles.append(Particle(
                cx + random.uniform(-80, 80),
                cy + random.uniform(-80, 80),
            ))

        lvl = self._audio_level
        for p in self._particles:
            d = math.hypot(p.x - cx, p.y - cy) + 1
            angle = math.atan2(p.y - cy, p.x - cx)
            if attract:
                p.update(mx, my, True)
            elif self._state == "SPEAKING":
                # ERIS hablando: bombeo radial fuerte al ritmo de su voz
                pump = 0.05 + 0.9 * lvl
                p.vx += math.cos(angle) * pump * (90.0 / d)
                p.vy += math.sin(angle) * pump * (90.0 / d)
                p.vx += math.cos(angle + math.pi / 2) * 0.04
                p.vy += math.sin(angle + math.pi / 2) * 0.04
                p.update()
            elif self._state == "THINKING":
                # ERIS trabajando: remolino orbital acelerado + respiración
                cur_r = d - 1
                target_r = 45 + 60 * (0.5 + 0.5 * math.sin(self._phase * 2 + p.x))
                pull = (target_r - cur_r) * 0.016
                p.vx += math.cos(angle) * pull
                p.vy += math.sin(angle) * pull
                p.vx += math.cos(angle + math.pi / 2) * 0.22
                p.vy += math.sin(angle + math.pi / 2) * 0.22
                p.update(cx, cy, True)
            elif self._state == "LISTENING":
                # Tú hablando: remolino suave + ondas radiales con tu voz
                p.vx += math.cos(angle + math.pi / 2) * 0.03
                p.vy += math.sin(angle + math.pi / 2) * 0.03
                p.vx += (cx - p.x) / d * 0.01
                p.vy += (cy - p.y) / d * 0.01
                push = 0.45 * lvl * (100.0 / d)
                p.vx += math.cos(angle) * push
                p.vy += math.sin(angle) * push
                p.update()
            else:
                # IDLE: siempre vivo — deriva orbital suave constante
                p.vx += math.cos(angle + math.pi / 2) * (0.03 + 0.06 * lvl)
                p.vy += math.sin(angle + math.pi / 2) * (0.03 + 0.06 * lvl)
                p.update()
            p.size = 1.5 + lvl * 3
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
        if self.isVisible():
            self.update()
        self._apply_frame_rate()

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
        base = {
            "IDLE": QColor(C.PRI),
            "LISTENING": QColor(C.SUCCESS),
            "THINKING": QColor(C.PRI),
            "SPEAKING": QColor(C.PRI_LIGHT),
            "INITIATING": QColor(C.PRI_LIGHT),
            "MUTED": QColor("#666666"),
            "ERROR": QColor(C.ERROR),
        }.get(self._state, QColor(C.PRI))
        emo = getattr(self, "_emo_hex", None)
        strength = getattr(self, "_emo_strength", 0.0)
        # El sentimiento tiñe solo estados "vivos" (no ERROR/MUTED) y respira con el pulso.
        if emo and strength > 0 and self._state not in ("MUTED", "ERROR"):
            try:
                blend = min(1.0, strength * (0.75 + 0.35 * self._pulse))
                ec = QColor(emo)
                r = int(base.red() * (1 - blend) + ec.red() * blend)
                g = int(base.green() * (1 - blend) + ec.green() * blend)
                b = int(base.blue() * (1 - blend) + ec.blue() * blend)
                return QColor(max(0, min(255, r)), max(0, min(255, g)),
                              max(0, min(255, b)))
            except Exception:
                pass
        return base

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
            if self._paint_trails:
                for i, (tx, ty) in enumerate(pt.trail):
                    ta = int(alpha * i / len(pt.trail) * 0.3)
                    if ta > 0:
                        tc = QColor(state_color)
                        tc.setAlpha(ta)
                        p.setBrush(QBrush(tc))
                        ts = sz * i / len(pt.trail) * 0.5
                        p.drawEllipse(QPointF(tx, ty), ts, ts)
        ring_color = QColor(state_color)
        ring_color.setAlpha(int(40 + 30 * self._pulse))
        pen = QPen(ring_color, 1)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        r = 30 + 14 * self._pulse
        p.drawEllipse(QPointF(cx, cy), r, r)

        # ── Efectos por estado ──
        lvl = self._audio_level

        def _comet(radius, speed, n_dots=12, spread=6, base_alpha=60, max_alpha=170):
            """Anillo de puntos con un punto brillante que viaja (movimiento asimétrico visible)."""
            for i in range(n_dots):
                ang = (self._phase * speed + i * (math.pi * 2 / n_dots))
                dx, dy = math.cos(ang), math.sin(ang)
                px, py = cx + dx * radius, cy + dy * radius
                br = 0.5 + 0.5 * math.sin(ang - self._phase * speed)
                br = max(0.0, min(1.0, br * (1.0 + spread)))
                rc = QColor(state_color)
                rc.setAlpha(int(base_alpha + (max_alpha - base_alpha) * br))
                rad = 2.5 + 3.0 * br
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QBrush(rc))
                p.drawEllipse(QRectF(px - rad, py - rad, rad * 2, rad * 2))

        if self._state == "IDLE":
            # Siempre vivo: cometa lento orbitando + respiración del anillo
            _comet(34, 1.6, n_dots=10, spread=5, base_alpha=40, max_alpha=130)
        elif self._state in ("LISTENING", "SPEAKING"):
            # Anillos expansivos al ritmo de la voz (onda sonora)
            n_rings = 3 if self._state == "LISTENING" else 4
            speed = 1.2 if self._state == "LISTENING" else 1.6
            for i in range(n_rings):
                t = (self._phase * speed + i / n_rings) % 1.0
                rr = 24 + t * (70 + 90 * lvl)
                rc = QColor(state_color)
                rc.setAlpha(int((1.0 - t) * 100))
                pen = QPen(rc, max(1, int(1 + t * 3)))
                p.setPen(pen)
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawEllipse(QPointF(cx, cy), rr, rr)
            # Cometa giratorio marcando actividad
            _comet(52, 2.6 if self._state == "SPEAKING" else 1.8,
                   n_dots=12, spread=6, base_alpha=60, max_alpha=180)
        elif self._state == "THINKING":
            # Cometa giratorio de puntos (anillo doble): señal clara de "estoy trabajando"
            _comet(62, 4.0, n_dots=12, spread=8, base_alpha=40, max_alpha=190)
            _comet(40, -3.0, n_dots=12, spread=8, base_alpha=30, max_alpha=150)
        self._draw_emotion_accent(p, cx, cy, state_color)
        p.end()

    # ── Micro-acentos del sentimiento (corazones, chispas, lágrimas) ──────
    def _draw_emotion_accent(self, p, cx, cy, state_color):
        name = getattr(self, "_emo_name", "")
        kind = _ORB_ACCENTS.get(name)
        strength = getattr(self, "_emo_strength", 0.0)
        if not kind or strength <= 0 or self._state in ("MUTED", "ERROR"):
            return
        alpha = int(50 + 130 * strength * (0.6 + 0.4 * self._pulse))
        clr = QColor(state_color)
        clr.setAlpha(alpha)
        p.setBrush(QBrush(clr))
        p.setPen(Qt.PenStyle.NoPen)
        if kind == "hearts":
            for i in range(3):
                ang = self._phase * 0.9 + i * math.pi * 2 / 3
                rr = 52 + 8 * math.sin(self._phase * 2 + i * 1.7)
                hx = cx + math.cos(ang) * rr
                hy = cy + math.sin(ang) * rr - 7
                s = 3.0 + 2.5 * strength + 1.5 * math.sin(self._phase * 3 + i)
                self._draw_heart(p, hx, hy, s)
        elif kind == "sparkles":
            for i in range(4):
                ang = self._phase * 1.3 + i * math.pi / 2 + math.pi / 4
                rr = 58 + 10 * math.sin(self._phase * 2.5 + i * 1.3)
                sx = cx + math.cos(ang) * rr
                sy = cy + math.sin(ang) * rr
                s = 4.0 + 3.5 * strength + 2.0 * math.sin(self._phase * 4 + i)
                self._draw_sparkle(p, sx, sy, s)
        elif kind == "tears":
            for i in range(2):
                ang = math.pi / 2 + i * 1.1 + self._phase * 0.45
                rr = 46 + 6 * math.sin(self._phase + i * 2.0)
                tx = cx + math.cos(ang) * rr
                ty = cy + math.sin(ang) * rr + 7
                s = 2.5 + 2.0 * strength
                self._draw_tear(p, tx, ty, s)

    @staticmethod
    def _draw_heart(p, x, y, s):
        p.drawEllipse(QPointF(x - s * 0.5, y - s * 0.45), s * 0.55, s * 0.55)
        p.drawEllipse(QPointF(x + s * 0.5, y - s * 0.45), s * 0.55, s * 0.55)
        tri = QPolygonF([QPointF(x - s * 0.9, y - s * 0.15),
                         QPointF(x + s * 0.9, y - s * 0.15),
                         QPointF(x, y + s * 1.15)])
        p.drawPolygon(tri)

    @staticmethod
    def _draw_sparkle(p, x, y, s):
        pts = []
        for k in range(8):
            a = k * math.pi / 4
            rad = s if k % 2 == 0 else s * 0.35
            pts.append(QPointF(x + math.cos(a) * rad, y + math.sin(a) * rad))
        p.drawPolygon(QPolygonF(pts))

    @staticmethod
    def _draw_tear(p, x, y, s):
        p.drawEllipse(QPointF(x, y), s, s * 1.25)
        tri = QPolygonF([QPointF(x - s, y - s * 0.25),
                         QPointF(x + s, y - s * 0.25),
                         QPointF(x, y - s * 1.8)])
        p.drawPolygon(tri)
