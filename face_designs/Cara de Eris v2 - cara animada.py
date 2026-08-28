"""ERIS Face — cara animada con muchas expresiones estilo emoji.

Sistema paramétrico: ojos, cejas, boca + overlays (lengua, lágrimas,
sudor, rubor, corazones, beso, gafas, gorrito, cuernos, manos...).
Dibuja en un espacio local de 200x200.

FaceWidget es la versión animada (parpadea, mueve ojos, transiciones).
"""
import math
import random

from PyQt6.QtCore import QRectF, QPointF, Qt, QTimer
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QPainterPath, QFont,
)
from PyQt6.QtWidgets import QWidget

# ── Paleta ──────────────────────────────────────────────────────────────
_BLUE     = QColor("#5fa8ff")
_PUPIL    = QColor("#24487a")
_LBLUE    = QColor("#9fc8ff")
_DROP     = QColor("#8fc4ff")
_WHITE    = QColor("#dff1ff")
_BLUSH    = QColor(255, 150, 160, 120)
_HEART_P  = QColor(255, 110, 155)
_HEART_L  = QColor(255, 175, 200)
_DARK     = QColor("#16202e")
_HORN     = QColor("#4a3a7a")
_PARTY1   = QColor("#ff7fb0")
_PARTY2   = QColor("#7ec3ff")
_PARTY3   = QColor("#ffe066")

_EYE_X = 30.0
_EYE_Y = 95.0
_MOUTH_Y = 140.0


def _pen(color, w=4.0, cap=Qt.PenCapStyle.RoundCap, join=Qt.PenJoinStyle.RoundJoin):
    pen = QPen(color, w)
    pen.setCapStyle(cap)
    pen.setJoinStyle(join)
    return pen


def _heart_path(x, y, s):
    path = QPainterPath()
    path.moveTo(x, y + s * 0.9)
    path.cubicTo(x + s * 1.3, y - s * 0.2, x + s * 2.0, y - s * 1.1, x + s * 1.85, y - s * 1.55)
    path.cubicTo(x + s * 1.7, y - s * 2.0, x + s * 0.9, y - s * 2.15, x, y - s * 1.55)
    path.cubicTo(x - s * 0.9, y - s * 2.15, x - s * 1.7, y - s * 2.0, x - s * 1.85, y - s * 1.55)
    path.cubicTo(x - s * 2.0, y - s * 1.1, x - s * 1.3, y - s * 0.2, x, y + s * 0.9)
    path.closeSubpath()
    return path


# ── Expresiones ─────────────────────────────────────────────────────────
_MOOD_POOL = ("neutral", "smiling", "thinking", "sleepy", "happy", "loved", "blush_smile", "wink")

_EXPRESSIONS = {
    "neutral":         {},
    "grinning":        dict(mouth_open=0.85, mouth_curve=0.7, eye_open=0.85, brow=-0.1),
    "rofl":            dict(mouth_open=0.95, mouth_curve=0.8, eye_open=0.15, tear=0.7, brow=-0.25, eye_arc=1.0),
    "tears_of_joy":    dict(mouth_open=0.65, mouth_curve=0.8, eye_open=0.3, tear=0.5, brow=-0.15, eye_arc=1.0),
    "wink":            dict(eye_open_l=0.12, mouth_open=0.25, mouth_curve=0.6, brow=0.1),
    "smiling":         dict(mouth_open=0.4, mouth_curve=0.7, eye_open=0.35, blush=0.4, brow=-0.05, eye_arc=0.95),
    "loved":           dict(heart=True, mouth_open=0.5, mouth_curve=0.8, blush=0.5),
    "in_love":         dict(hearts=0.8, mouth_open=0.45, mouth_curve=0.75, blush=0.5, eye_open=0.5, eye_arc=0.7),
    "kiss":            dict(eye_open_l=0.1, kiss=True, round_mouth=True, mouth_open=0.3, blush=0.3),
    "blush_smile":     dict(mouth_open=0.3, mouth_curve=0.5, eye_open=0.4, blush=0.35, eye_arc=0.85),
    "smile_tear":      dict(mouth_open=0.3, mouth_curve=0.55, eye_open=0.5, tear=0.45, brow=0.15),
    "yum":             dict(mouth_open=0.7, mouth_curve=0.5, eye_open=0.3, tongue=1.0, eye_arc=0.65),
    "money":           dict(money=True, mouth_open=0.35, mouth_curve=0.3, eye_open=0.6, brow=-0.15),
    "hug":             dict(hands="hug", mouth_open=0.5, mouth_curve=0.7, eye_open=0.5, blush=0.3),
    "thinking":        dict(eye_open=0.8, px=0.6, py=-0.6, brow=0.3, brow_l=0.2, brow_r=0.9,
                            mouth_curve=-0.2, mouth_open=0.1),
    "hmm":             dict(eye_open=0.6, brow_l=0.0, brow_r=1.0, mouth_curve=-0.05, mouth_open=0.15),
    "rolling_eyes":    dict(roll=True, mouth_curve=-0.1, mouth_open=0.12, brow_l=-0.4, brow_r=-0.4),
    "wry":             dict(eye_open=0.6, brow_l=-0.5, brow_r=0.1, mouth_curve=0.25, mouth_open=0.2),
    "wry_shake":       dict(eye_open=0.6, brow_l=-0.5, brow_r=0.1, mouth_curve=0.25, mouth_open=0.2),
    "wry_nod":         dict(eye_open=0.6, brow_l=-0.5, brow_r=0.1, mouth_curve=0.25, mouth_open=0.2),
    "nausea":          dict(tongue=1.0, eye_open=0.2, mouth_curve=-0.2, mouth_open=0.4, sweat=0.5),
    "hot":             dict(sweat=1.0, tongue=1.0, blush=0.8, eye_open=0.25, mouth_curve=0.3, mouth_open=0.5),
    "cold":            dict(shiver=True, teeth=True, eye_open=1.1, mouth_curve=0.0, mouth_open=0.3, brow=0.2),
    "party":           dict(party=True, mouth_open=0.7, mouth_curve=0.8, eye_open=0.5, blush=0.4),
    "cool":            dict(glasses=True, mouth_curve=0.2, mouth_open=0.15, eye_open=0.8, brow=-0.1),
    "astonished":      dict(round_mouth=True, mouth_open=0.95, eye_open=1.2, brow=0.6, brow_lift=0.4),
    "flushed":         dict(blush=0.9, round_mouth=True, mouth_open=0.4, eye_open=1.1, sweat=0.3, brow=0.3),
    "pleading":        dict(eye_open=1.15, brow=0.55, brow_lift=0.2, hands="plead",
                            mouth_curve=-0.15, mouth_open=0.12),
    "holding_tears":   dict(tear=0.8, mouth_curve=0.55, mouth_open=0.35, eye_open=0.6,
                            brow=0.45, brow_lift=0.15, blush=0.3),
    "fearful":         dict(eye_open=1.2, brow=0.8, brow_lift=0.4, hands="scream",
                            mouth_curve=-0.25, mouth_open=0.35, sweat=0.3),
    "relieved":        dict(tear=0.4, sweat=0.4, eye_open=0.5, brow=0.45,
                            mouth_curve=-0.25, mouth_open=0.2),
    "crying":          dict(tear=0.9, eye_open=0.45, brow=0.6, mouth_curve=-0.5, mouth_open=0.25),
    "sobbing":         dict(tear=1.2, eye_open=0.35, brow=0.75, mouth_curve=-0.5, mouth_open=0.75),
    "screaming":       dict(eye_open=1.25, brow=0.85, brow_lift=0.4, hands="scream",
                            mouth_curve=-0.1, mouth_open=0.95, sweat=0.5),
    "pouting":         dict(brow=-0.9, eye_slant=-0.8, eye_open=0.5, blush=0.4,
                            mouth_curve=-0.5, mouth_open=0.35),
    "angry":           dict(brow=-0.95, brow_lift=-0.25, eye_open=0.45, eye_slant=-0.9,
                            mouth_curve=-0.15, mouth_open=0.35, teeth=True),
    "devil":           dict(horns=True, brow=-0.8, eye_slant=-0.5, eye_open=0.55,
                            mouth_curve=0.35, mouth_open=0.35),
    "happy":           dict(mouth_open=0.7, mouth_curve=0.8, eye_open=0.7, eye_arc=0.9,
                            brow=-0.05, blush=0.2),
    "sleepy":          dict(eye_open=0.12, mouth_curve=-0.05, mouth_open=0.08, brow=0.2),
    "music":           dict(eye_open=0.32, eye_arc=0.7, mouth_open=0.22, mouth_curve=0.6,
                            blush=0.35, notes=0.9, brow=-0.1),
}

_BASE = dict(brow=0.0, brow_lift=0.0, eye_open=1.0, eye_slant=0.0, heart=False,
             eye_arc=0.0,
             px=0.0, py=0.0, mouth_curve=0.25, mouth_open=0.05,
             teeth=False, round_mouth=False, tongue=0.0, tear=0.0, sweat=0.0,
             blush=0.0, hearts=0.0, money=False, kiss=False, glasses=False,
             party=False, horns=False, roll=False, hands="", shiver=False,
             notes=0.0)


def _params_for(expr):
    p = dict(_BASE)
    p.update(_EXPRESSIONS.get(expr, {}))
    p["eye_open_l"] = p.get("eye_open_l", p["eye_open"])
    p["eye_open_r"] = p.get("eye_open_r", p["eye_open"])
    p["eye_slant_l"] = p.get("eye_slant_l", p["eye_slant"])
    p["eye_slant_r"] = p.get("eye_slant_r", p["eye_slant"])
    p["brow_l"] = p.get("brow_l", p["brow"])
    p["brow_r"] = p.get("brow_r", p["brow"])
    return p


# ── Dibujo base ─────────────────────────────────────────────────────────
def _draw_brows(p, prm):
    for sign, key in ((-1, "brow_l"), (1, "brow_r")):
        tilt = prm[key]
        x = 100 + sign * _EYE_X
        y = 82 - prm["brow_lift"] * 8
        outer = x - sign * 13
        inner = x + sign * 13
        p.setPen(_pen(_BLUE, 4))
        p.drawLine(QPointF(outer, y - tilt * 4), QPointF(inner, y + tilt * 4))


def _draw_eye(p, x, prm, sign, off, blink):
    y = _EYE_Y + off[1]
    x = x + off[0]
    if prm["heart"]:
        p.setBrush(QBrush(_BLUE))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPath(_heart_path(x, y + 2, 16))
        return
    if prm["roll"]:
        p.setBrush(QBrush(_WHITE))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(x, y), 15, 15)
        p.setBrush(QBrush(_PUPIL))
        p.drawEllipse(QPointF(x, y - 9), 4.5, 4.5)
        return
    open_ = prm["eye_open_l"] if sign < 0 else prm["eye_open_r"]
    slant = prm["eye_slant_l"] if sign < 0 else prm["eye_slant_r"]
    if prm["eye_arc"] > 0.05:
        r = 17.0
        ctrl = y - 7 * prm["eye_arc"]
        if prm["tear"] > 0.4:
            ctrl = y + 6 * prm["eye_arc"]
        path = QPainterPath()
        path.moveTo(x - r, y + 3)
        path.quadTo(x, ctrl, x + r, y + 3)
        p.setPen(_pen(_BLUE, 5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)
        return
    open_ = open_ * (1.0 - 0.92 * blink)
    open_ = max(0.0, min(1.5, open_))
    w = 38.0 * (1.0 if open_ <= 1.05 else open_)
    h_full = 42.0
    if open_ < 0.06:
        p.setPen(_pen(_BLUE, 4))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawLine(QPointF(x - w / 2 + 2, y), QPointF(x + w / 2 - 2, y))
        return
    lid_y = y + h_full / 2 - h_full * open_
    p.save()
    p.setClipRect(QRectF(x - w / 2, lid_y, w, h_full * 2))
    p.translate(x, y)
    p.rotate(slant * 10 * sign)
    p.translate(-x, -y)
    p.setBrush(QBrush(_BLUE))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(QRectF(x - w / 2, y - h_full / 2, w, h_full))
    p.setBrush(QBrush(QColor(255, 255, 255, 190)))
    p.drawEllipse(QPointF(x - w * 0.16, y - h_full * 0.14), 4.2, 4.2)
    p.restore()


def _draw_mouth(p, prm):
    cx, base = 100.0, _MOUTH_Y
    curve = prm["mouth_curve"]
    open_ = prm["mouth_open"]
    hw = 20.0
    if prm["money"]:
        p.setBrush(QBrush(_BLUE))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(cx - 9, base - 5, 18, 14), 4, 4)
        p.setPen(_pen(_PUPIL, 2))
        p.drawLine(QPointF(cx, base - 3), QPointF(cx, base + 7))
        p.drawLine(QPointF(cx - 4, base - 1), QPointF(cx + 4, base - 1))
        p.drawLine(QPointF(cx - 4, base + 3), QPointF(cx + 4, base + 3))
        return
    if prm["round_mouth"]:
        r = 8 + 6 * open_
        p.setBrush(QBrush(_BLUE))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(cx, base), r, r * 1.15)
        return
    if open_ < 0.12:
        path = QPainterPath()
        path.moveTo(cx - hw, base + curve * 1.5)
        path.quadTo(cx, base + 12 * curve, cx + hw, base + curve * 1.5)
        p.setPen(_pen(_BLUE, 4))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)
        return
    corner = base + curve * 2
    top_y = base - 8 * open_ - 2 * curve
    bot_y = base + 24 * open_ + 2 * curve
    path = QPainterPath()
    path.moveTo(cx - hw, corner)
    path.quadTo(cx, bot_y, cx + hw, corner)
    path.quadTo(cx, top_y, cx - hw, corner)
    path.closeSubpath()
    p.setBrush(QBrush(_BLUE))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawPath(path)
    if prm["teeth"]:
        ty = top_y + (bot_y - top_y) * 0.28
        p.setPen(_pen(_PUPIL, 3))
        p.drawLine(QPointF(cx - hw + 3, ty), QPointF(cx + hw - 3, ty))


# ── Overlays ────────────────────────────────────────────────────────────
def _draw_tongue(p, prm, clk):
    amt = prm["tongue"]
    if amt <= 0:
        return
    cx = 100.0
    y0 = _MOUTH_Y + 6
    h = 13 * amt
    w = 14.0
    wob = math.sin(clk * 4) * 1.5
    p.setBrush(QBrush(_LBLUE))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(QRectF(cx - w / 2, y0, w, h), 6, 6)
    p.setPen(_pen(QColor("#5f92c9"), 2))
    p.drawLine(QPointF(cx + wob, y0 + 2), QPointF(cx + wob, y0 + h - 3))


def _draw_tears(p, prm, clk):
    amt = prm["tear"]
    if amt <= 0:
        return
    n = 2 if amt < 0.7 else 3
    p.setBrush(QBrush(_DROP))
    p.setPen(Qt.PenStyle.NoPen)
    for sign in (-1, 1):
        x = 100 + sign * _EYE_X
        for i in range(n):
            fall = ((clk * 40 + i * 17) % 26) - 13
            yy = _EYE_Y + 14 + i * 8 + fall * 0.35
            if yy > _EYE_Y + 34:
                yy -= 26
            p.drawEllipse(QPointF(x - 5 + i * 4, yy), 3, 4)


def _draw_sweat(p, prm, clk):
    amt = prm["sweat"]
    if amt <= 0:
        return
    p.setBrush(QBrush(_DROP))
    p.setPen(Qt.PenStyle.NoPen)
    for i in range(3):
        fall = ((clk * 30 + i * 17) % 34) - 10
        p.drawEllipse(QPointF(158 - i * 5, 78 + i * 11 + fall), 2.5, 4)


def _draw_blush(p, prm):
    amt = prm["blush"]
    if amt <= 0:
        return
    col = QColor(255, 150, 160, int(130 * min(1.0, amt)))
    p.setBrush(QBrush(col))
    p.setPen(Qt.PenStyle.NoPen)
    for sign in (-1, 1):
        p.drawEllipse(QPointF(100 + sign * 44, 112), 9, 5.5)


def _draw_hearts(p, prm, clk):
    amt = prm["hearts"]
    if amt <= 0:
        return
    for i in range(3):
        bob = math.sin(clk * 2 + i * 2.1) * 3
        pulse = 8 + math.sin(clk * 3.5 + i * 1.8) * 1.4
        x = 42 + i * 38
        y = 34 + bob + (i % 2) * 10
        p.setBrush(QBrush(_HEART_P if i % 2 == 0 else _HEART_L))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPath(_heart_path(x, y, pulse))


def _note(p, x, y, s, kind):
    p.save()
    p.translate(x, y)
    p.scale(s, s)
    p.setPen(_pen(_LBLUE, 3))
    p.drawLine(QPointF(0, 0), QPointF(0, -13))
    p.setBrush(QBrush(_LBLUE))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(QPointF(-3.5, 0.5), 4.6, 3.4)
    p.setPen(_pen(_LBLUE, 3))
    if kind % 3 == 0:
        p.drawLine(QPointF(0, -13), QPointF(4.5, -9))
        p.drawLine(QPointF(0, -13), QPointF(4.5, -5))
    elif kind % 3 == 1:
        p.drawLine(QPointF(0, -13), QPointF(4.5, -9))
    else:
        p.drawEllipse(QPointF(4.5, -8), 3.4, 2.6)
    p.restore()


def _draw_notes(p, prm, clk):
    amt = prm["notes"]
    if amt <= 0.05:
        return
    for i, (dx, ph) in enumerate(((-46, 0.0), (46, 0.6), (-24, 1.4))):
        t = (clk * 0.55 + ph) % 1.0
        x = 100 + dx + math.sin(clk * 1.4 + i * 2.0) * 5
        y = 60 - t * 30
        s = 0.5 + 0.5 * t
        a = int(200 * t)
        p.setOpacity(0.25 + 0.75 * t)
        _note(p, x, y, s, i)
        p.setOpacity(1.0)


def _draw_kiss(p, prm, clk):
    if not prm["kiss"]:
        return
    bob = math.sin(clk * 3) * 2.5
    p.setBrush(QBrush(_HEART_P))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawPath(_heart_path(132, 152 + bob, 7))


def _draw_glasses(p, prm):
    if not prm["glasses"]:
        return
    p.setBrush(QBrush(_DARK))
    p.setPen(_pen(_DARK, 2))
    for sign in (-1, 1):
        p.drawEllipse(QPointF(100 + sign * _EYE_X, _EYE_Y), 22, 17)
    p.setPen(_pen(_DARK, 3))
    p.drawLine(QPointF(100 + 12, _EYE_Y), QPointF(100 - 12, _EYE_Y))
    p.drawLine(QPointF(100 + 52, _EYE_Y - 2), QPointF(100 + 74, _EYE_Y - 5))
    p.drawLine(QPointF(100 - 52, _EYE_Y - 2), QPointF(100 - 74, _EYE_Y - 5))


def _draw_party(p, prm, clk):
    if not prm["party"]:
        return
    p.setBrush(QBrush(_PARTY1))
    p.setPen(Qt.PenStyle.NoPen)
    path = QPainterPath()
    path.moveTo(88, 34)
    path.lineTo(112, 34)
    path.lineTo(100, 8)
    path.closeSubpath()
    p.drawPath(path)
    p.setPen(_pen(QColor("#ffffff"), 2))
    p.drawLine(QPointF(91, 27), QPointF(109, 27))
    p.setBrush(QBrush(_PARTY3))
    p.drawEllipse(QPointF(100, 5), 4, 4)
    for i in range(8):
        x = 28 + (i * 22 + int(clk * 24)) % 144
        y = 16 + (i * 13) % 42
        p.setBrush(QBrush([_PARTY1, _PARTY2, _PARTY3][i % 3]))
        p.drawEllipse(QPointF(x, y), 2, 3)


def _draw_horns(p, prm):
    if not prm["horns"]:
        return
    p.setBrush(QBrush(_HORN))
    p.setPen(Qt.PenStyle.NoPen)
    for sign in (-1, 1):
        x = 100 + sign * 40
        path = QPainterPath()
        path.moveTo(x - 8, 44)
        path.quadTo(x, 16, x + 8, 42)
        path.quadTo(x, 30, x - 8, 44)
        path.closeSubpath()
        p.drawPath(path)


def _draw_hands(p, prm, clk):
    mode = prm["hands"]
    if not mode:
        return
    p.setBrush(QBrush(_BLUE))
    p.setPen(Qt.PenStyle.NoPen)
    if mode == "hug":
        for sign in (-1, 1):
            x = 100 + sign * 48
            p.drawRoundedRect(QRectF(x - 11, 132, 22, 18), 9, 9)
            p.drawRoundedRect(QRectF(x + sign * 6, 126, 9, 9), 4, 4)
    elif mode == "scream":
        for sign in (-1, 1):
            x = 100 + sign * 50
            y = 98 + math.sin(clk * 5) * 1.5
            p.drawRoundedRect(QRectF(x - 12, y - 9, 24, 20), 10, 10)
            p.drawRoundedRect(QRectF(x + sign * 8, y - 15, 9, 10), 4, 4)
    elif mode == "plead":
        p.drawRoundedRect(QRectF(86, 148, 15, 16), 7, 7)
        p.drawRoundedRect(QRectF(99, 148, 15, 16), 7, 7)


def _draw_shiver(p, prm, clk):
    if not prm["shiver"]:
        return
    col = QColor("#9fc8ff")
    for i in range(2):
        off = math.sin(clk * 6 + i * 2) * 2
        p.setPen(_pen(col, 2.5))
        p.drawLine(QPointF(36, 62 + i * 14 + off), QPointF(27, 54 + i * 14 + off))
        p.drawLine(QPointF(164, 62 + i * 14 - off), QPointF(173, 54 + i * 14 - off))


# ── Ensamble ────────────────────────────────────────────────────────────
def _draw(p, prm, eye_offs=((0.0, 0.0), (0.0, 0.0)), blink=0.0, bob=0.0, clk=0.0, sway=1.2):
    p.save()
    sway = math.sin(clk * 0.7) * sway
    p.translate(100.0, 100.0)
    p.rotate(sway)
    p.translate(-100.0, -100.0 + bob)
    _draw_brows(p, prm)
    for sign, off in zip((-1, 1), eye_offs):
        _draw_eye(p, 100 + sign * _EYE_X, prm, sign, off, blink)
    _draw_mouth(p, prm)
    _draw_tongue(p, prm, clk)
    _draw_tears(p, prm, clk)
    _draw_sweat(p, prm, clk)
    _draw_blush(p, prm)
    _draw_hearts(p, prm, clk)
    _draw_notes(p, prm, clk)
    _draw_kiss(p, prm, clk)
    _draw_glasses(p, prm)
    _draw_party(p, prm, clk)
    _draw_horns(p, prm)
    _draw_hands(p, prm, clk)
    _draw_shiver(p, prm, clk)
    p.restore()


def draw_face(p, expr="neutral", blink=False):
    _draw(p, _params_for(expr), blink=1.0 if blink else 0.0)


def draw_face_in(p, rect: QRectF, expr="neutral", blink=False):
    p.save()
    p.scale(rect.width() / 200.0, rect.height() / 200.0)
    p.translate(rect.x(), rect.y())
    draw_face(p, expr, blink)
    p.restore()


_NUMERIC = ("brow", "brow_l", "brow_r", "brow_lift", "eye_open", "eye_open_l", "eye_open_r",
            "eye_slant", "eye_slant_l", "eye_slant_r", "eye_arc", "px", "py",
            "mouth_curve", "mouth_open", "tongue", "tear", "sweat", "blush",
            "hearts", "notes")
_SNAP = ("heart", "teeth", "round_mouth", "money", "kiss", "glasses",
         "party", "horns", "roll", "hands", "shiver")


def _lerp_params(a, b, t):
    out = {}
    for k in _NUMERIC:
        out[k] = a[k] + (b[k] - a[k]) * t
    for k in _SNAP:
        out[k] = b[k]
    return out


class FaceWidget(QWidget):
    """Cara animada: parpadea, mueve ojos, transiciones suaves."""
    def __init__(self, expr="neutral", autostart=True):
        super().__init__()
        self.expr = expr
        self.cur = _params_for(expr)
        self.start = self.cur
        self.target = self.cur
        self.t = 1.0
        self.clock = 0.0
        self.blink = 0.0
        self.blink_phase = None
        self.blink_extra = 0.0
        self.next_blink = random.uniform(2.0, 4.5)
        self.eye_offs = ((0.0, 0.0), (0.0, 0.0))
        self.look = (0.0, 0.0)
        self.look_target = (0.0, 0.0)
        self.look_t = 0.0
        self.wob = (random.uniform(0, math.tau), random.uniform(0, math.tau),
                    random.uniform(0.6, 1.4), random.uniform(0.6, 1.4))
        self.audio = 0.0
        self.audio_target = 0.0
        self.intensity = 1.0
        self.neutral = _params_for("neutral")
        self.mood = True
        self.last_set = 0.0
        self.next_mood = random.uniform(12, 28)
        self.reaction = None
        self.reaction_t = 0.0
        self.reaction_dur = 1.0
        self.next_reaction = random.uniform(10, 22)
        self.glitch = 0.0
        self.next_glitch = random.uniform(15, 40)
        self.music = 0.0
        self._saved_expr = None
        self.setMinimumSize(220, 260)
        self.timer = QTimer(self)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self._tick)
        if autostart:
            self.timer.start()

    def set_expr(self, expr):
        self.expr = expr
        self.start = self.cur
        self.target = _params_for(expr)
        self.t = 0.0
        self.last_set = self.clock

    def set_mood(self, on):
        self.mood = on

    def set_music(self, level):
        level = max(0.0, min(1.0, level))
        if level > 0 and self.music <= 0:
            self._saved_expr = self.expr
            self.set_mood(False)
            self.set_expr("music")
        elif level <= 0 and self.music > 0:
            self.set_mood(True)
            self.set_expr(self._saved_expr or "neutral")
        self.music = level

    def set_audio(self, level):
        self.audio_target = max(0.0, min(1.0, level))

    def set_intensity(self, level):
        self.intensity = max(0.05, min(1.0, level))

    def trigger_reaction(self, name=None):
        if self.reaction is not None:
            return
        self.reaction = name or random.choice(("sigh", "yawn", "flinch", "laugh", "cry"))
        self.reaction_dur = {"sigh": 1.6, "yawn": 2.2, "flinch": 0.7,
                             "laugh": 1.8, "cry": 2.6}[self.reaction]
        self.reaction_t = 0.0

    def _effective(self):
        prm = {}
        for k in _NUMERIC:
            prm[k] = self.neutral[k] + (self.cur[k] - self.neutral[k]) * self.intensity
        for k in _SNAP:
            prm[k] = self.cur[k]
        prm["mouth_open"] = max(0.0, min(1.0, prm["mouth_open"] + self.audio * 0.7))
        if self.reaction:
            env = math.sin(math.pi * min(1.0, self.reaction_t / self.reaction_dur))
            if self.reaction == "flinch":
                prm["eye_open_l"] += 0.8 * env
                prm["eye_open_r"] += 0.8 * env
                prm["brow_l"] += 0.5 * env
                prm["brow_r"] += 0.5 * env
            elif self.reaction == "sigh":
                prm["mouth_open"] = max(prm["mouth_open"], 0.15 + 0.35 * env)
                prm["mouth_curve"] = -0.15 * env
                prm["eye_open_l"] = min(prm["eye_open_l"], 1 - 0.7 * env)
                prm["eye_open_r"] = min(prm["eye_open_r"], 1 - 0.7 * env)
            elif self.reaction == "yawn":
                prm["mouth_open"] = max(prm["mouth_open"], 0.95 * env)
                prm["mouth_curve"] = -0.25 * env
                prm["round_mouth"] = False
                prm["eye_open_l"] = min(prm["eye_open_l"], 1 - env)
                prm["eye_open_r"] = min(prm["eye_open_r"], 1 - env)
            elif self.reaction == "laugh":
                prm["mouth_open"] = max(prm["mouth_open"], 0.5 + 0.45 * env)
                prm["mouth_curve"] = max(prm["mouth_curve"], 0.8 * env)
                prm["eye_arc"] = max(prm["eye_arc"], env)
                prm["tear"] = max(prm["tear"], 0.3 * env)
            elif self.reaction == "cry":
                prm["mouth_open"] = max(prm["mouth_open"], 0.5 + 0.3 * env)
                prm["mouth_curve"] = min(prm["mouth_curve"], -0.6 * env)
                prm["tear"] = max(prm["tear"], 1.2 * env)
                prm["eye_open_l"] = min(prm["eye_open_l"], 1 - 0.4 * env)
                prm["eye_open_r"] = min(prm["eye_open_r"], 1 - 0.4 * env)
                prm["brow_l"] += 0.4 * env
                prm["brow_r"] += 0.4 * env
        for k in ("eye_open", "eye_open_l", "eye_open_r", "mouth_open"):
            prm[k] = max(0.0, min(1.5, prm[k]))
        prm["brow"] = max(-1.0, min(1.0, prm["brow"]))
        prm["brow_l"] = max(-1.0, min(1.0, prm["brow_l"]))
        prm["brow_r"] = max(-1.0, min(1.0, prm["brow_r"]))
        return prm

    def _tick(self):
        dt = 16 / 1000.0
        self.clock += dt
        if self.t < 1.0:
            self.t = min(1.0, self.t + dt / 0.45)
            e = 1 - (1 - self.t) ** 3
            self.cur = _lerp_params(self.start, self.target, e)
        if self.audio_target > self.audio:
            self.audio = min(self.audio_target, self.audio + dt * 6)
        else:
            self.audio = max(self.audio_target, self.audio - dt * 3)
        self.next_reaction -= dt
        if self.next_reaction <= 0 and self.reaction is None and self.music <= 0:
            self.trigger_reaction()
            self.next_reaction = random.uniform(16, 40)
        if self.reaction:
            self.reaction_t += dt
            if self.reaction in ("laugh", "cry"):
                self.audio_target = 0.35 + 0.3 * abs(math.sin(self.clock * 13))
            if self.reaction_t >= self.reaction_dur:
                self.reaction = None
        if self.mood and self.clock - self.last_set > 8:
            self.next_mood -= dt
            if self.next_mood <= 0:
                pool = [e for e in _MOOD_POOL if e != self.expr]
                self.set_expr(random.choice(pool))
                self.next_mood = random.uniform(18, 45)
        self.next_glitch -= dt
        if self.next_glitch <= 0 and self.music <= 0:
            self.glitch = random.uniform(0.1, 0.22)
            self.next_glitch = random.uniform(15, 40)
        if self.glitch > 0:
            self.glitch -= dt
        self.next_blink -= dt
        if self.next_blink <= 0:
            self.blink_phase = 0.0
            if random.random() < 0.18:
                self.blink_extra = 0.14
            energy = (self.cur["mouth_open"] * 0.6 + abs(self.cur["mouth_curve"])
                      + self.cur["tear"] * 0.8 + abs(self.cur["brow_l"] - self.cur["brow_r"]) * 0.5
                      + (1 - (self.cur["eye_open_l"] + self.cur["eye_open_r"]) * 0.5) * 0.4)
            self.next_blink = random.uniform(1.8, 2.6) if energy > 0.45 else random.uniform(3.5, 6.5)
        if self.blink_extra > 0:
            self.blink_extra -= dt
            if self.blink_extra <= 0 and self.blink_phase is None:
                self.blink_phase = 0.0
        if self.blink_phase is not None:
            self.blink_phase += dt
            k = min(1.0, self.blink_phase / 0.24)
            self.blink = math.sin(math.pi * k)
            if k >= 1.0:
                self.blink_phase = None
                self.blink = 0.0
        self.look_t -= dt
        if self.look_t <= 0:
            self.look_target = (random.uniform(-4.5, 4.5), random.uniform(-3.5, 3.5))
            self.look_t = random.uniform(1.8, 4.0)
        k = 1 - math.exp(-dt * 5)
        self.look = (self.look[0] + (self.look_target[0] - self.look[0]) * k,
                     self.look[1] + (self.look_target[1] - self.look[1]) * k)
        p0, p1, s0, s1 = self.wob
        wl = (math.sin(self.clock * s0 + p0) * 1.6,
              math.cos(self.clock * s0 * 1.3 + p0) * 1.1)
        wr = (math.sin(self.clock * s1 + p1 + 0.9) * 1.6,
              math.cos(self.clock * s1 * 1.3 + p1 + 0.9) * 1.1)
        self.eye_offs = ((self.look[0] + wl[0], self.look[1] + wl[1]),
                         (self.look[0] + wr[0], self.look[1] + wr[1]))
        self.update()

    def render_to(self, p, rect):
        bob = math.sin(self.clock * 1.1) * 1.2 + math.sin(self.clock * 2.9) * 2.4 * self.music
        sway = 1.2 + 1.7 * self.music
        prm = self._effective()
        eo = self.eye_offs
        if self.glitch > 0:
            jx = math.sin(self.clock * 220) * 5
            jy = math.sin(self.clock * 180 + 1.3) * 5
            flick = 0.9 if int(self.clock * 90) % 2 == 0 else 0.25
            eo = ((eo[0][0] + jx, eo[0][1] + jy), (eo[1][0] - jx, eo[1][1] + jy * 0.7))
            prm["eye_open_l"] *= flick
            prm["eye_open_r"] *= 0.3 + 0.7 * (1 - flick)
            prm["mouth_curve"] += math.sin(self.clock * 150) * 0.2
        s = min(rect.width(), rect.height()) / 200.0
        ox = rect.x() + (rect.width() - 200 * s) / 2.0
        oy = rect.y() + (rect.height() - 200 * s) / 2.0
        p.save()
        p.translate(ox, oy)
        p.scale(s, s)
        p.translate(10, 0)
        _draw(p, prm, eo, self.blink, bob, self.clock, sway)
        p.restore()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.render_to(p, QRectF(0, 0, self.width(), self.height()))
        p.setPen(QColor("#9aa3b5"))
        font = QFont("Segoe UI", 12, QFont.Weight.DemiBold)
        p.setFont(font)
        p.drawText(QRectF(0, 200, 220, 30), Qt.AlignmentFlag.AlignCenter,
                   self.expr.upper())
        p.end()
