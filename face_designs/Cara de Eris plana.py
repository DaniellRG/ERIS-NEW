"""ERIS Face — cara de robot tierna (minimalista) mirando de frente.

Solo 2 ojos ovalados rellenos de azul + boca. Sin placa, sin cejas.
Dibuja en un espacio local de 200x200; usa draw_face(painter, expr, ...).

Expresiones: neutral, happy, sad, angry, determined, surprised,
thinking, sleepy, love, excited.
"""
from PyQt6.QtCore import QRectF, QPointF, Qt
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QPainterPath, QFont,
)
from PyQt6.QtWidgets import QWidget

# ── Paleta ──────────────────────────────────────────────────────────────
_BLUE = QColor("#5fa8ff")
_INK  = QColor("#1f2533")


def _pen(color, w=4.0, cap=Qt.PenCapStyle.RoundCap, join=Qt.PenJoinStyle.RoundJoin):
    pen = QPen(color, w)
    pen.setCapStyle(cap)
    pen.setJoinStyle(join)
    return pen


def _eye_fill(p, rect: QRectF):
    p.setBrush(QBrush(_BLUE))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(rect)


def _draw_eye(p, x, style, sign, blink):
    y = 95
    if blink:
        p.setBrush(QBrush(_BLUE))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(x - 18, y - 5, 36, 10), 5, 5)
        return
    if style == "round":
        rect = QRectF(x - 22, y - 28, 44, 56)
        _eye_fill(p, rect)
        return
    if style == "closed":
        p.setBrush(QBrush(_BLUE))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(x - 18, y - 5, 36, 10), 5, 5)
        return
    if style == "heart":
        h = _pen(_BLUE, 6)
        h.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(h)
        p.setBrush(QBrush(_BLUE))
        path = QPainterPath()
        path.moveTo(x, y + 7)
        path.cubicTo(x - 24, y - 5, x - 14, y - 20, x, y - 7)
        path.cubicTo(x + 14, y - 20, x + 24, y - 5, x, y + 7)
        p.drawPath(path)
        return
    if style == "slanted":
        p.save()
        p.translate(x, y)
        p.rotate(12 * sign)
        rect = QRectF(-19, -26, 38, 52)
        _eye_fill(p, rect)
        p.restore()
        return
    # oval (por defecto)
    rect = QRectF(x - 19, y - 26, 38, 52)
    _eye_fill(p, rect)


def _draw_mouth(p, style):
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(_pen(_BLUE, 4))
    if style == "smile":
        path = QPainterPath()
        path.moveTo(86, 138)
        path.quadTo(100, 150, 114, 138)
        p.drawPath(path)
    elif style == "big_smile":
        path = QPainterPath()
        path.moveTo(82, 136)
        path.quadTo(100, 160, 118, 136)
        path.quadTo(100, 146, 82, 136)
        p.drawPath(path)
    elif style == "frown":
        path = QPainterPath()
        path.moveTo(86, 148)
        path.quadTo(100, 136, 114, 148)
        p.drawPath(path)
    elif style == "line":
        p.drawLine(QPointF(88, 142), QPointF(112, 142))
    elif style == "determined":
        p.drawLine(QPointF(84, 138), QPointF(100, 144))
        p.drawLine(QPointF(100, 144), QPointF(116, 138))
    elif style == "grimace":
        p.drawLine(QPointF(82, 138), QPointF(118, 138))
        for i in range(4):
            x = 86 + i * 12
            p.drawLine(QPointF(x, 138), QPointF(x, 150))
    elif style == "o":
        p.setBrush(QBrush(_BLUE))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(94, 134, 14, 16))
    elif style == "wavy":
        path = QPainterPath()
        path.moveTo(86, 142)
        path.quadTo(93, 136, 100, 142)
        path.quadTo(107, 148, 114, 142)
        p.drawPath(path)
    elif style == "none":
        pass


_EXPRESSIONS = {
    "neutral":    dict(eyes="oval",    mouth="smile"),
    "happy":      dict(eyes="oval",    mouth="big_smile"),
    "sad":        dict(eyes="closed",  mouth="frown"),
    "angry":      dict(eyes="slanted", mouth="grimace"),
    "determined": dict(eyes="oval",    mouth="determined"),
    "surprised":  dict(eyes="round",   mouth="o"),
    "thinking":   dict(eyes="lookup",  mouth="wavy"),
    "sleepy":     dict(eyes="closed",  mouth="line"),
    "love":       dict(eyes="heart",   mouth="big_smile"),
    "excited":    dict(eyes="round",   mouth="big_smile"),
}


def draw_face(p, expr="neutral", blink=False):
    cfg = _EXPRESSIONS.get(expr, _EXPRESSIONS["neutral"])
    for sign in (-1, 1):
        _draw_eye(p, 100 + sign * 30, cfg["eyes"], sign, blink)
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
