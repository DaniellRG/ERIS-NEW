"""Ported from Eris2: 120-particle orb + floating overlay."""
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QPoint, QTimer
from PyQt6.QtGui import QMouseEvent, QPainter, QBrush, QColor, QRadialGradient, QPen
import math, random
from collections import deque

class _Particle:
    def __init__(self, x, y):
        self.x = x; self.y = y
        self.vx = random.uniform(-0.5, 0.5)
        self.vy = random.uniform(-0.5, 0.5)
        self.size = random.uniform(1, 3)
        self.life = random.uniform(0.5, 1.0)
        self.trail = deque(maxlen=6)
        self.hue = random.uniform(0.55, 0.62)

    def update(self, cx=0, cy=0, attract=False):
        self.trail.append((self.x, self.y))
        if attract:
            dx, dy = cx - self.x, cy - self.y
            d = math.hypot(dx, dy) + 0.1
            self.vx += dx / d * 0.02
            self.vy += dy / d * 0.02
        self.vx *= 0.98; self.vy *= 0.98
        self.x += self.vx; self.y += self.vy
        self.life -= 0.003

class ParticleOrb(QWidget):
    states = ("IDLE", "LISTENING", "THINKING", "SPEAKING", "MUTED")
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(200, 200)
        self._state = "IDLE"
        self._audio_level = 0.0
        self._target_audio = 0.0
        self._phase = 0.0
        self._pulse = 0.0
        self._mouse_pos = None
        self._attract = False
        self._particles = []
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)
        self.setMouseTracking(True)
        self._init_particles()
        
    def _init_particles(self):
        cx, cy = self.width()/2, self.height()/2
        self._particles = [_Particle(cx+random.uniform(-80,80), cy+random.uniform(-80,80)) for _ in range(120)]
        
    def set_state(self, state: str):
        if state in self.states:
            self._state = state
            
    def set_audio(self, level: float):
        self._target_audio = level * 0.4
        
    def set_audio_level(self, level: float):
        self.set_audio(level)
        
    def _tick(self):
        self._phase += 0.02
        self._pulse = 0.5 + 0.5 * math.sin(self._phase * 2)
        self._audio_level += (self._target_audio - self._audio_level) * 0.08
        cx, cy = self.width()/2, self.height()/2
        
        if len(self._particles) < 120:
            self._particles.append(_Particle(cx+random.uniform(-80,80), cy+random.uniform(-80,80)))
        
        for p in self._particles:
            if self._attract and self._mouse_pos:
                p.update(self._mouse_pos[0], self._mouse_pos[1], True)
            elif self._state == "SPEAKING":
                angle = math.atan2(p.y-cy, p.x-cx)
                p.vx += math.cos(angle)*0.05*self._audio_level
                p.vy += math.sin(angle)*0.05*self._audio_level
                p.update()
            elif self._state in ("THINKING", "LISTENING", "IDLE"):
                p.update(cx, cy, True)
            else:
                p.update()
            
            p.size = 1.5 + self._audio_level * 3
            
            if p.life <= 0:
                angle = random.uniform(0, 2*math.pi)
                dist = random.uniform(10, 60)
                p.x = cx + math.cos(angle)*dist
                p.y = cy + math.sin(angle)*dist
                p.vx = random.uniform(-0.5, 0.5)
                p.vy = random.uniform(-0.5, 0.5)
                p.life = random.uniform(0.5, 1.0)
        self.update()
        
    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        if self._state == "SPEAKING":
            hue = 0.10
        elif self._state == "THINKING":
            hue = 0.72
        elif self._state == "LISTENING":
            hue = 0.58
        else:
            hue = 0.58
        
        # Draw trails
        for pt in self._particles:
            trail = list(pt.trail)
            if len(trail) < 2: continue
            for i in range(len(trail)-1):
                alpha = int(80 * (i/len(trail)))
                p.setPen(QPen(QColor.fromHslF(hue, 0.8, 0.5 + 0.3*(i/len(trail)), alpha/255), pt.size*0.3*i/len(trail)))
                p.drawLine(int(trail[i][0]), int(trail[i][1]), int(trail[i+1][0]), int(trail[i+1][1]))
        
        # Draw particles
        for pt in self._particles:
            alpha = int(pt.life * 200)
            g = QRadialGradient(pt.x, pt.y, pt.size*3)
            g.setColorAt(0, QColor.fromHslF(hue, 0.8, 0.7, alpha/255))
            g.setColorAt(1, QColor.fromHslF(hue, 0.8, 0.4, 0))
            p.setBrush(QBrush(g))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(int(pt.x-pt.size*3), int(pt.y-pt.size*3), int(pt.size*6), int(pt.size*6))
            
            p.setPen(QColor.fromHslF(hue, 0.5, 0.9, alpha/255))
            p.drawPoint(int(pt.x), int(pt.y))
        p.end()
        
    def enterEvent(self, e): self._attract = True
    def leaveEvent(self, e): self._attract = False
    def mouseMoveEvent(self, e): self._mouse_pos = (e.position().x(), e.position().y())

class ErisOrb(QWidget):
    def __init__(self, parent=None):
        super().__init__(None)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint|Qt.WindowType.WindowStaysOnTopHint|Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedSize(200, 200)
        self._drag_pos = None
        self._drag_start = None
        self._parent_eris = parent
        
        self._orb = ParticleOrb(self)
        self._orb.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._orb.setGeometry(0, 0, 200, 200)
        
        s = self.screen().availableGeometry()
        self.move(s.right() - 235, s.bottom() - 250)
        
    def set_audio(self, level):
        self._orb.set_audio(level)
    def set_state(self, state):
        self._orb.set_state(state)
    def sync_theme(self):
        pass
        
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._drag_start = e.globalPosition().toPoint()
        if e.button() == Qt.MouseButton.RightButton:
            if self._parent_eris:
                self._parent_eris.show_and_activate()
                
    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.MouseButton.LeftButton and self._drag_pos is not None:
            self.move(e.globalPosition().toPoint() - self._drag_pos)
            
    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and self._drag_start is not None:
            dist = (e.globalPosition().toPoint() - self._drag_start).manhattanLength()
            if dist < 8 and self._parent_eris:
                self._parent_eris.show_and_activate()
        self._drag_pos = None
        self._drag_start = None
