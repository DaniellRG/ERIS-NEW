"""Vista previa standalone del diseño de la cara de ERIS.

Uso:
    python face_preview.py
    - Espacio: alternar ciclo automático
    - Clic / flechas: cambiar expresión manualmente
    - A: simular voz (la boca se mueve con el "audio")
    - R: forzar una reacción (suspiro/bostezo/sobresalto)
    - + / -: intensidad de la emoción
    - G: cuadrícula con todas las expresiones
    - Q: salir
"""
import math
import sys
from PyQt6.QtCore import Qt, QRectF, QTimer
from PyQt6.QtGui import QPainter, QColor, QFont
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget

from face_design import FaceWidget, _EXPRESSIONS, draw_face_in

EXPRS = list(_EXPRESSIONS.keys())


class GridWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ERIS Face — todas")
        self.setMinimumSize(100, 100)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor("#14161c"))
        w = self.width()
        h = self.height()
        cols = 6
        cell_w = w / cols
        cell_h = cell_w * 1.15
        f = QFont("Segoe UI", 9)
        for i, name in enumerate(EXPRS):
            cx = i % cols
            cy = i // cols
            x = cx * cell_w
            y = cy * cell_h
            if y + cell_h > h:
                break
            draw_face_in(p, QRectF(x + cell_w * 0.1, y + 4, cell_w * 0.8, cell_w * 0.8), name)
            p.setPen(QColor("#9aa3b5"))
            p.setFont(f)
            p.drawText(QRectF(x, y + cell_w * 0.82, cell_w, 24), Qt.AlignmentFlag.AlignCenter, name.upper())
        p.end()


class PreviewWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ERIS Face — diseño")
        self.setFixedSize(250, 340)
        self.idx = 0
        self.auto = True
        self.grid = None
        self.audio_on = False
        self.audio_clock = 0.0

        central = QWidget(self)
        self.setCentralWidget(central)
        lay = QVBoxLayout(central)
        self.face = FaceWidget(EXPRS[self.idx])
        lay.addWidget(self.face, alignment=Qt.AlignmentFlag.AlignCenter)
        self.hint = QLabel("")
        self.hint.setStyleSheet("color:#5a6270; font-family:Segoe UI; font-size:9px;")
        lay.addWidget(self.hint, alignment=Qt.AlignmentFlag.AlignCenter)
        self._update_hint()

        self.timer = QTimer(self)
        self.timer.setInterval(2800)
        self.timer.timeout.connect(self.next)
        self.timer.start()

        self.audio_timer = QTimer(self)
        self.audio_timer.setInterval(50)
        self.audio_timer.timeout.connect(self._audio_tick)

    def _update_hint(self):
        self.hint.setText(
            f"espacio:auto | clic/flechas:expr | A:voz | R:reaccion | M:animo "
            f"({self.face.mood and 'ON' or 'OFF'}) | N:musica "
            f"({self.face.music > 0 and 'ON' or 'OFF'}) | +/-:intensidad "
            f"({self.face.intensity:.1f}) | G:grid | Q:salir")

    def _audio_tick(self):
        self.audio_clock += 0.05
        if self.audio_on:
            level = max(0.0, math.sin(self.audio_clock * 7) * 0.6 + 0.25)
        else:
            level = 0.0
        self.face.set_audio(level)

    def next(self):
        self.idx = (self.idx + 1) % len(EXPRS)
        self.face.set_expr(EXPRS[self.idx])

    def prev(self):
        self.idx = (self.idx - 1) % len(EXPRS)
        self.face.set_expr(EXPRS[self.idx])

    def mousePressEvent(self, e):
        self.next()

    def keyPressEvent(self, e):
        k = e.key()
        if k == Qt.Key.Key_Q:
            self.close()
        elif k == Qt.Key.Key_A:
            self.audio_on = not self.audio_on
            self.audio_timer.start() if self.audio_on else self.audio_timer.stop()
            if not self.audio_on:
                self.face.set_audio(0.0)
        elif k == Qt.Key.Key_R:
            self.face.trigger_reaction()
        elif k == Qt.Key.Key_M:
            self.face.set_mood(not self.face.mood)
            self.timer.stop()
            self._update_hint()
        elif k == Qt.Key.Key_N:
            self.timer.stop()
            self.face.set_music(1.0 if self.face.music <= 0 else 0.0)
            self._update_hint()
        elif k == Qt.Key.Key_Plus or k == Qt.Key.Key_Equal:
            self.face.set_intensity(self.face.intensity + 0.1)
            self._update_hint()
        elif k == Qt.Key.Key_Minus:
            self.face.set_intensity(self.face.intensity - 0.1)
            self._update_hint()
        elif k == Qt.Key.Key_G:
            if self.grid is None or not self.grid.isVisible():
                rows = math.ceil(len(EXPRS) / 6)
                self.grid = GridWindow()
                self.grid.resize(1100, int(1100 / 6 * 1.15 * rows))
                self.grid.show()
        elif k == Qt.Key.Key_Space:
            self.auto = not self.auto
            self.timer.setInterval(0 if self.auto else 2800)
        elif k == Qt.Key.Key_Right:
            self.next()
        elif k == Qt.Key.Key_Left:
            self.prev()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = PreviewWindow()
    win.show()
    sys.exit(app.exec())
