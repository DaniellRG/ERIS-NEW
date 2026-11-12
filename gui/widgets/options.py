# -*- coding: utf-8 -*-
"""
gui/widgets/options.py — Menú interactivo de opciones de ERIS.

Extraído de ui.py durante el refactor T4.
Contiene:
  - _OptionCard: tarjeta clicable por opción (single = selección única, multi = checkbox)
  - OptionDialog: pregunta con opciones, recomendada, single/multi, respuesta custom y 'skip'
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QCheckBox, QDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QRadioButton, QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)

from gui.styles import C


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
        hint.setStyleSheet(f"color: {C.SUBALT if hasattr(C, 'SUBALT') else C.BORDER}; font-size: 10px;")
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
            QPushButton:hover {{ background: {C.PRI2 if hasattr(C, 'PRI2') else C.PRI};
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
