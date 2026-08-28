"""ERIS Face — Cara de Eris LCD (pixeleada).

Ojos y boca formados por puntos/píxeles, como pantalla LCD.
Dibuja en un espacio local de 200x200; usa draw_face(painter, expr, ...).

Expresiones: neutral, happy, sad, angry, determined, surprised,
thinking, sleepy, love, excited.
"""
import math

from PyQt6.QtCore import QRectF, QPointF, Qt
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QPainterPath, QFont,
)
from PyQt6.QtWidgets import QWidget

# ── Paleta ──────────────────────────────────────────────────────────────
_BLUE = QColor("#5fa8ff")

# ── Tamaño de píxel LCD ────────────────────────────────────────────────
CELL = 5.0
DOT  = 4.2   # tamaño del punto (con separación entre píxeles)


def _pix(p, x, y, color=_BLUE):
    p.fillRect(QRectF(x - DOT / 2, y - DOT / 2, DOT, DOT), QBrush(color))


def _inside_ellipse(cx, cy, rect: QRectF, angle=0.0):
    dx, dy = cx - rect.center().x(), cy - rect.center().y()
    if angle:
        a = math.radians(angle)
        c, s = math.cos(a), math.sin(a)
        dx, dy = dx * c + dy * s, -dx * s + dy * c
    rx, ry = rect.width() / 2, rect.height() / 2
    if rx <= 0 or ry <= 0:
        return False
    return (dx / rx) ** 2 + (dy / ry) ** 2 <= 1.0


def _pix_fill(p, rect: QRectF, color=_BLUE, angle=0.0):
    gx0, gx1 = int(rect.left() / CELL), int(rect.right() / CELL) + 1
    gy0, gy1 = int(rect.top() / CELL), int(rect.bottom() / CELL) + 1
    for gy in range(gy0, gy1):
        for gx in range(gx0, gx1):
            cx = gx * CELL + CELL / 2
            cy = gy * CELL + CELL / 2
            if _inside_ellipse(cx, cy, rect, angle):
                _pix(p, cx, cy, color)


def _bezier(pts, t):
    while len(pts) > 1:
        pts = [((pts[i][0] * (1 - t) + pts[i + 1][0] * t),
                (pts[i][1] * (1 - t) + pts[i + 1][1] * t))
               for i in range(len(pts) - 1)]
    return pts[0]


def _pix_curve(p, pts, color=_BLUE):
    span = math.hypot(pts[-1][0] - pts[0][0], pts[-1][1] - pts[0][1])
    n = max(2, int(span / (CELL * 0.6)))
    for i in range(n + 1):
        x, y = _bezier(pts, i / n)
        _pix(p, x, y, color)


def _pix_line(p, x0, y0, x1, y1, color=_BLUE):
    span = math.hypot(x1 - x0, y1 - y0)
    n = max(2, int(span / (CELL * 0.6)))
    for i in range(n + 1):
        t = i / n
        _pix(p, x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, color)


def _pix_fill_path(p, path: QPainterPath, color=_BLUE):
    r = path.boundingRect()
    gx0, gx1 = int(r.left() / CELL), int(r.right() / CELL) + 1
    gy0, gy1 = int(r.top() / CELL), int(r.bottom() / CELL) + 1
    for gy in range(gy0, gy1):
        for gx in range(gx0, gx1):
            cx = gx * CELL + CELL / 2
            cy = gy * CELL + CELL / 2
            if path.contains(QPointF(cx, cy)):
                _pix(p, cx, cy, color)


def _draw_eye(p, x, style, sign, blink):
    y = 95
    if blink:
        _pix_line(p, x - 18, y, x + 18, y)
        return
    if style == "round":
        _pix_fill(p, QRectF(x - 22, y - 28, 44, 56))
    elif style == "closed":
        _pix_line(p, x - 18, y, x + 18, y)
    elif style == "heart":
        path = QPainterPath()
        path.moveTo(x, y + 10)
        path.cubicTo(x + 16, y - 2, x + 26, y - 14, x + 24, y - 20)
        path.cubicTo(x + 22, y - 26, x + 12, y - 28, x, y - 20)
        path.cubicTo(x - 12, y - 28, x - 22, y - 26, x - 24, y - 20)
        path.cubicTo(x - 26, y - 14, x - 16, y - 2, x, y + 10)
        path.closeSubpath()
        _pix_fill_path(p, path)
    elif style == "slanted":
        _pix_fill(p, QRectF(x - 19, y - 26, 38, 52), angle=18 * sign)
    else:
        _pix_fill(p, QRectF(x - 19, y - 26, 38, 52))


def _draw_brows(p, style):
    for sign in (-1, 1):
        x = 100 + sign * 30
        if style == "angry":
            _pix_line(p, x - 16 * sign, 84, x + 16 * sign, 92)
        elif style == "determined":
            _pix_line(p, x - 14, 87, x + 14, 90)


def _draw_mouth(p, style):
    if style == "smile":
        _pix_curve(p, [(86, 138), (100, 150), (114, 138)])
    elif style == "big_smile":
        path = QPainterPath()
        path.moveTo(80, 140)
        path.quadTo(100, 128, 120, 140)
        path.quadTo(100, 166, 80, 140)
        path.closeSubpath()
        _pix_fill_path(p, path)
    elif style == "frown":
        _pix_curve(p, [(86, 148), (100, 136), (114, 148)])
    elif style == "line":
        _pix_line(p, 88, 142, 112, 142)
    elif style == "determined":
        _pix_line(p, 84, 138, 100, 144)
        _pix_line(p, 100, 144, 116, 138)
    elif style == "grimace":
        _pix_line(p, 82, 138, 118, 138)
        for i in range(4):
            x = 86 + i * 12
            _pix_line(p, x, 138, x, 150)
    elif style == "o":
        _pix_fill(p, QRectF(93, 132, 16, 18))
    elif style == "wavy":
        _pix_curve(p, [(86, 142), (93, 136), (100, 142)])
        _pix_curve(p, [(100, 142), (107, 148), (114, 142)])
    elif style == "none":
        pass


_EXPRESSIONS = {
    "neutral":    dict(eyes="oval",    mouth="smile",    brows=None),
    "happy":      dict(eyes="oval",    mouth="big_smile", brows=None),
    "sad":        dict(eyes="closed",  mouth="frown",    brows=None),
    "angry":      dict(eyes="slanted", mouth="grimace",  brows="angry"),
    "determined": dict(eyes="oval",    mouth="determined", brows="determined"),
    "surprised":  dict(eyes="round",   mouth="o",        brows=None),
    "thinking":   dict(eyes="oval",    mouth="wavy",     brows=None),
    "sleepy":     dict(eyes="closed",  mouth="line",     brows=None),
    "love":       dict(eyes="heart",   mouth="big_smile", brows=None),
    "excited":    dict(eyes="round",   mouth="big_smile", brows=None),
}


def draw_face(p, expr="neutral", blink=False):
    cfg = _EXPRESSIONS.get(expr, _EXPRESSIONS["neutral"])
    for sign in (-1, 1):
        _draw_eye(p, 100 + sign * 30, cfg["eyes"], sign, blink)
    if cfg["brows"]:
        _draw_brows(p, cfg["brows"])
    _draw_mouth(p, cfg["mouth"])


def draw_face_in(p, rect: QRectF, expr="neutral", blink=False):
    p.save()
    p.scale(rect.width() / 200.0, rect.height() / 200.0)
    p.translate(rect.x(), rect.y())
    draw_face(p, expr, blink)
    p.restore()


class FaceWidget(QWidget):
    """Vista previa de la cara con nombre de expresión."""
    def __init__(self, expr="neutral"):
        super().__init__()
        self.expr = expr
        self.blink = False
        self.setMinimumSize(220, 260)

    def set_expr(self, expr):
        self.expr = expr
        self.update()

    def set_blink(self, blink):
        self.blink = blink

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        draw_face_in(p, QRectF(10, 0, 200, 200), self.expr, self.blink)
        p.setPen(QColor("#9aa3b5"))
        font = QFont("Segoe UI", 12, QFont.Weight.DemiBold)
        p.setFont(font)
        p.drawText(QRectF(0, 200, 220, 30), Qt.AlignmentFlag.AlignCenter, self.expr.upper())
        p.end()
