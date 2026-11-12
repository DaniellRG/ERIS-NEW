# -*- coding: utf-8 -*-
"""
gui/widgets/chat.py — Widgets del área de chat de ERIS.

Extraído de ui.py durante el refactor T4.
Contiene:
  - _ChatInput: QLineEdit con drag & drop de imágenes y documentos
  - FileDropZone: zona de soltar archivos con feedback visual
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QLineEdit, QWidget

from gui.styles import C

# Extensiones de archivo reconocidas por el chat
_IMAGE_EXTS = (
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tiff", ".tif"
)

_DOC_EXTS = (
    ".pdf", ".docx", ".docm", ".xlsx", ".xlsm", ".xlsb", ".xltx",
    ".pptx", ".pptm", ".potx", ".txt", ".text", ".md", ".markdown",
    ".rst", ".log", ".csv", ".tsv", ".json", ".jsonl", ".xml", ".html",
    ".htm", ".css", ".js", ".jsx", ".ts", ".tsx", ".py", ".pyw", ".java",
    ".c", ".h", ".cpp", ".hpp", ".cs", ".go", ".rs", ".rb", ".php",
    ".sql", ".sh", ".bat", ".cmd", ".ps1", ".ini", ".cfg", ".yaml",
    ".yml", ".toml", ".env", ".gitignore",
)


class _ChatInput(QLineEdit):
    """Chat input con soporte drag & drop de imágenes y documentos."""
    image_dropped = pyqtSignal(str)
    doc_dropped = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, e: QDragEnterEvent):
        if e.mimeData().hasUrls():
            for url in e.mimeData().urls():
                low = url.toLocalFile().lower()
                if low.endswith(_IMAGE_EXTS) or low.endswith(_DOC_EXTS):
                    e.acceptProposedAction()
                    return
        e.ignore()

    def dropEvent(self, e: QDropEvent):
        for url in e.mimeData().urls():
            path = url.toLocalFile()
            if not path:
                continue
            low = path.lower()
            if low.endswith(_IMAGE_EXTS):
                self.image_dropped.emit(path)
            elif low.endswith(_DOC_EXTS):
                self.doc_dropped.emit(path)
        e.acceptProposedAction()


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


# C importado al inicio con el resto de dependencias de gui.widgets.