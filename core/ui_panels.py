"""
core/ui_panels.py — Terminal Panel + Floating Authorization Window for ERIS.

TerminalPanel: Panel derecho dentro de la ventana de Eris (dentro del splitter).
Muestra en tiempo real tool calls, resultados, errores y logs. Toggle con Ctrl+T.

FloatingPermiso: Ventana flotante siempre-visible que aparece cuando ERIS
necesita autorización del usuario (incluso en modo orbe).
"""
from __future__ import annotations

import time
import threading
from datetime import datetime

from PyQt6.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QVBoxLayout, QWidget,
    QGraphicsDropShadowEffect,
)


_theme = {
    "BG": "#0f0a02", "BG2": "#1a1308", "BG3": "#2a1f0a",
    "SURFACE": "#1f180d", "SURFACE2": "#2f2612",
    "PRI": "#f59e0b", "PRI_LIGHT": "#fbbf24", "PRI_DIM": "#b8830a",
    "TEXT": "#fde68a", "TEXT_DIM": "#a08858", "TEXT_BRIGHT": "#fffbeb",
    "BORDER": "rgba(245,158,11,0.45)",
    "SUCCESS": "#10b981", "ERROR": "#ef4444", "WARNING": "#f59e0b",
}


def apply_theme_from_ui(theme_dict: dict):
    _theme.update(theme_dict)


def _hex_to_rgb(hex_color: str) -> str:
    """Convert '#rrggbb' to 'r,g,b' for use in rgba()."""
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return "15,10,2"
    return f"{int(h[0:2],16)},{int(h[2:4],16)},{int(h[4:6],16)}"


# ── Terminal Panel (inside window, right side of splitter) ─────────────────────

class TerminalOverlay(QWidget):
    """Panel that lives inside the main Eris window's splitter.
    Shows real-time tool activity. Not a floating overlay."""

    _append_sig = pyqtSignal(str, str)
    _clear_sig = pyqtSignal()

    MAX_LINES = 200

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TerminalPanel")
        self.setMinimumWidth(280)
        self._total_lines = 0
        self._visible = False

        self._build_ui()
        self._apply_style()
        self._append_sig.connect(self._do_append)
        self._clear_sig.connect(self._do_clear)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        self._header = QWidget()
        self._header.setFixedHeight(32)
        header_layout = QHBoxLayout(self._header)
        header_layout.setContentsMargins(10, 2, 8, 2)
        header_layout.setSpacing(6)

        self._dot = QLabel("●")
        self._dot.setFixedWidth(10)
        self._title = QLabel("TERMINAL")
        self._line_count = QLabel("0")

        self._clear_btn = QPushButton("✕")
        self._clear_btn.setFixedSize(20, 20)
        self._clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clear_btn.clicked.connect(self._do_clear)

        header_layout.addWidget(self._dot)
        header_layout.addWidget(self._title)
        header_layout.addStretch()
        header_layout.addWidget(self._line_count)
        header_layout.addWidget(self._clear_btn)

        layout.addWidget(self._header)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {_theme['BORDER']};")
        layout.addWidget(sep)

        # Terminal text
        self._text = QTextEdit()
        self._text.setReadOnly(True)
        self._text.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._text.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._text.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        layout.addWidget(self._text, 1)

    def _apply_style(self):
        self.setStyleSheet(f"""
            #TerminalPanel {{
                background: rgba({_hex_to_rgb(_theme['BG2'])},210);
                border-left: 1px solid {_theme['BORDER']};
            }}
        """)
        self._header.setStyleSheet(f"""
            background: rgba({_hex_to_rgb(_theme['BG3'])},180);
            border-bottom: 1px solid {_theme['BORDER']};
        """)
        self._dot.setStyleSheet(f"color: {_theme['SUCCESS']}; font-size: 8px; background: transparent;")
        self._title.setStyleSheet(f"""
            color: {_theme['PRI_LIGHT']};
            font-family: 'Segoe UI', sans-serif;
            font-size: 11px; font-weight: bold;
            letter-spacing: 1px;
            background: transparent;
        """)
        self._line_count.setStyleSheet(f"""
            color: {_theme['TEXT_DIM']};
            font-family: 'Consolas', monospace;
            font-size: 10px; background: transparent;
        """)
        self._clear_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {_theme['TEXT_DIM']};
                border: none; font-size: 13px; font-weight: bold;
            }}
            QPushButton:hover {{ color: {_theme['ERROR']}; }}
        """)
        self._text.setStyleSheet(f"""
            QTextEdit {{
                background: rgba({_hex_to_rgb(_theme['BG'])},160);
                color: {_theme['TEXT']};
                border: none;
                padding: 6px 8px;
                font-family: 'Cascadia Code', 'Consolas', monospace;
                font-size: 10px;
                selection-background-color: {_theme['PRI']};
                selection-color: {_theme['BG']};
            }}
        """)

    def toggle(self):
        if self._visible:
            self.hide()
            self._visible = False
        else:
            self.show()
            self._visible = True

    def _ts(self) -> str:
        return datetime.now().strftime("%H:%M:%S")

    def log_tool_start(self, name: str, args: dict):
        args_str = ", ".join(f"{k}={str(v)[:40]}" for k, v in list(args.items())[:3])
        if len(args_str) > 100:
            args_str = args_str[:97] + "..."
        html = (
            f"<span style='color:rgba(255,255,255,0.3)'>{self._ts()}</span> "
            f"<span style='color:{_theme['PRI']}'>▸</span> "
            f"<span style='color:{_theme['PRI_LIGHT']};font-weight:bold'>{name}</span>"
            f"<span style='color:{_theme['TEXT_DIM']}'>({args_str})</span>"
        )
        self._append_sig.emit(_theme["PRI"], html)

    def log_tool_result(self, name: str, result: str, ok: bool = True):
        icon = "✓" if ok else "✗"
        color = _theme["SUCCESS"] if ok else _theme["ERROR"]
        res_short = str(result)[:100].replace("\n", " ")
        html = (
            f"<span style='color:rgba(255,255,255,0.3)'>{self._ts()}</span> "
            f"<span style='color:{color}'>{icon}</span> "
            f"<span style='color:{color}'>{name}</span> "
            f"<span style='color:{_theme['TEXT_DIM']}'>{res_short}</span>"
        )
        self._append_sig.emit(color, html)

    def log_info(self, msg: str):
        html = (
            f"<span style='color:rgba(255,255,255,0.3)'>{self._ts()}</span> "
            f"<span style='color:{_theme['PRI_DIM']}'>ℹ</span> "
            f"<span style='color:{_theme['TEXT_DIM']}'>{msg[:120]}</span>"
        )
        self._append_sig.emit(_theme["PRI_DIM"], html)

    def log_user(self, msg: str):
        html = (
            f"<span style='color:rgba(255,255,255,0.3)'>{self._ts()}</span> "
            f"<span style='color:#c084fc'>▸</span> "
            f"<span style='color:#c084fc;font-weight:bold'>TÚ:</span> "
            f"<span style='color:{_theme['TEXT']}'>{msg[:100]}</span>"
        )
        self._append_sig.emit("#c084fc", html)

    def log_error(self, msg: str):
        html = (
            f"<span style='color:rgba(255,255,255,0.3)'>{self._ts()}</span> "
            f"<span style='color:{_theme['ERROR']}'>✗</span> "
            f"<span style='color:{_theme['ERROR']}'>{msg[:120]}</span>"
        )
        self._append_sig.emit(_theme["ERROR"], html)

    def log_speak(self, msg: str):
        html = (
            f"<span style='color:rgba(255,255,255,0.3)'>{self._ts()}</span> "
            f"<span style='color:{_theme['SUCCESS']}'>🗣</span> "
            f"<span style='color:{_theme['TEXT_DIM']}'>{msg[:100]}</span>"
        )
        self._append_sig.emit(_theme["SUCCESS"], html)

    def log_permission(self, msg: str, granted: bool):
        icon = "●"
        color = _theme["SUCCESS"] if granted else _theme["ERROR"]
        label = "OK" if granted else "DENIED"
        html = (
            f"<span style='color:rgba(255,255,255,0.3)'>{self._ts()}</span> "
            f"<span style='color:{color}'>{icon}</span> "
            f"<span style='color:{color};font-weight:bold'>{label}</span> "
            f"<span style='color:{_theme['TEXT_DIM']}'>{msg[:100]}</span>"
        )
        self._append_sig.emit(color, html)

    @pyqtSlot(str, str)
    def _do_append(self, color: str, html: str):
        self._text.append(html)
        self._total_lines += 1
        self._line_count.setText(str(self._total_lines))
        sb = self._text.verticalScrollBar()
        if sb:
            sb.setValue(sb.maximum())
        doc = self._text.document()
        if doc.blockCount() > self.MAX_LINES:
            cursor = self._text.textCursor()
            cursor.movePosition(cursor.MoveOperation.Start)
            cursor.movePosition(cursor.MoveOperation.Down, cursor.MoveMode.KeepAnchor,
                                doc.blockCount() - self.MAX_LINES + 30)
            cursor.removeSelectedText()

    @pyqtSlot()
    def _do_clear(self):
        self._text.clear()
        self._total_lines = 0
        self._line_count.setText("0")

    def refresh_theme(self):
        self._apply_style()


# ── Command Deck Panel (cola de intents) ──────────────────────────────────────

class CommandDeckWidget(QWidget):
    """Panel derecho que muestra la cola de comandos (intents ejecutados por ERIS).
    Toggle con Ctrl+D. Se alimenta de data/command_deck.json via read_deck()."""

    MAX_ROWS = 25

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("CommandDeckPanel")
        self.setMinimumWidth(280)
        self._visible = False
        self._last_refresh = 0.0

        self._build_ui()
        self._apply_style()

        self._timer = QTimer(self)
        self._timer.setInterval(2000)
        self._timer.timeout.connect(self.refresh)
        self._timer.start()
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QWidget()
        header.setFixedHeight(32)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(10, 2, 8, 2)
        hl.setSpacing(6)

        self._dot = QLabel("▸")
        self._dot.setFixedWidth(12)
        self._title = QLabel("COMMAND DECK")
        self._status_lbl = QLabel("0 en curso")

        self._clear_btn = QPushButton("✕")
        self._clear_btn.setFixedSize(20, 20)
        self._clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        from core.command_deck import clear_deck
        self._clear_btn.clicked.connect(lambda: (clear_deck(), self.refresh()))

        hl.addWidget(self._dot)
        hl.addWidget(self._title)
        hl.addStretch()
        hl.addWidget(self._status_lbl)
        hl.addWidget(self._clear_btn)

        self._header = header
        layout.addWidget(header)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {_theme['BORDER']};")
        layout.addWidget(sep)

        self._text = QTextEdit()
        self._text.setReadOnly(True)
        self._text.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._text.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._text.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        layout.addWidget(self._text, 1)

    def _apply_style(self):
        self.setStyleSheet(f"""
            #CommandDeckPanel {{
                background: rgba({_hex_to_rgb(_theme['BG2'])},210);
                border-left: 1px solid {_theme['BORDER']};
            }}
        """)
        self._header_style = f"""
            background: rgba({_hex_to_rgb(_theme['BG3'])},180);
            border-bottom: 1px solid {_theme['BORDER']};
        """
        self._header.setStyleSheet(self._header_style)
        self._dot.setStyleSheet(f"color: {_theme['PRI']}; font-size: 10px; background: transparent;")
        self._title.setStyleSheet(f"""
            color: {_theme['PRI_LIGHT']};
            font-family: 'Segoe UI', sans-serif;
            font-size: 11px; font-weight: bold;
            letter-spacing: 1px;
            background: transparent;
        """)
        self._status_lbl.setStyleSheet(f"""
            color: {_theme['TEXT_DIM']};
            font-family: 'Consolas', monospace;
            font-size: 10px; background: transparent;
        """)
        self._clear_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {_theme['TEXT_DIM']};
                border: none; font-size: 13px; font-weight: bold;
            }}
            QPushButton:hover {{ color: {_theme['ERROR']}; }}
        """)
        self._text.setStyleSheet(f"""
            QTextEdit {{
                background: rgba({_hex_to_rgb(_theme['BG'])},160);
                color: {_theme['TEXT']};
                border: none;
                padding: 6px 8px;
                font-family: 'Cascadia Code', 'Consolas', monospace;
                font-size: 10px;
                selection-background-color: {_theme['PRI']};
                selection-color: {_theme['BG']};
            }}
        """)

    def toggle(self):
        if self._visible:
            self.hide()
            self._visible = False
        else:
            self.show()
            self._visible = True
            self.refresh()

    def refresh(self):
        try:
            from core.command_deck import read_deck, deck_status
            deck = read_deck(self.MAX_ROWS)
        except Exception:
            self._text.setHtml("<span style='color:#888'>command_deck no disponible</span>")
            self._status_lbl.setText("—")
            return

        st = deck_status()
        self._status_lbl.setText(f"{st['running']} en curso · {st['total']} total")

        if not deck:
            self._text.setHtml(
                "<span style='color:#a08858'>Sin comandos todavía.</span>")
            return

        rows = []
        now = time.time()
        for e in deck:
            status = e.get("status", "done")
            tool = e.get("tool", "?")
            agent = e.get("agent", "")
            args = e.get("args", "")
            ts = e.get("ts") or now
            hhmm = datetime.fromtimestamp(ts).strftime("%H:%M:%S")

            if status == "running":
                icon, color = "▸", _theme["PRI"]
                extra = f"<span style='color:{color}'>(en curso)</span>"
            elif status == "error":
                icon, color = "✗", _theme["ERROR"]
                res = str(e.get("result", ""))[:60]
                extra = f"<span style='color:{_theme['ERROR']}'>{res}</span>" if res else ""
            else:
                icon, color = "✓", _theme["SUCCESS"]
                extra = ""
            agent_tag = f"<span style='color:{_theme['PRI_DIM']}'>[{agent}]</span> " if agent else ""
            rows.append(
                f"<span style='color:rgba(255,255,255,0.3)'>{hhmm}</span> "
                f"<span style='color:{color}'>{icon}</span> "
                f"<span style='color:{_theme['PRI_LIGHT']};font-weight:bold'>{tool}</span> "
                f"{agent_tag}"
                f"<span style='color:{_theme['TEXT_DIM']}'>{args} {extra}</span>"
            )
        self._text.setHtml("<br/>".join(rows))

    def refresh_theme(self):
        self._apply_style()

class FloatingPermiso(QWidget):
    """Always-on-top floating window that asks for user authorization.
    Appears even when ERIS is in orb mode."""

    _instance = None
    _result = None
    _done_event = None

    def __init__(self, parent=None):
        super().__init__(parent)
        FloatingPermiso._instance = self

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, False)
        self.setFixedSize(380, 200)

        self._drag_pos = None
        self._timer_val = 0
        self._timeout = 30

        self._build_ui()

    def _build_ui(self):
        self._container = QWidget(self)
        self._container.setGeometry(4, 4, 372, 192)
        self._container.setStyleSheet(f"""
            QWidget {{
                background: rgba(15,10,2,240);
                border: 2px solid {_theme['PRI']};
                border-radius: 12px;
            }}
        """)

        layout = QVBoxLayout(self._container)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(6)

        header = QHBoxLayout()
        icon_lbl = QLabel("🔐")
        icon_lbl.setStyleSheet("font-size: 18px; background: transparent;")
        header.addWidget(icon_lbl)

        self._title_lbl = QLabel("Permiso Requerido")
        self._title_lbl.setStyleSheet(f"""
            color: {_theme['PRI_LIGHT']};
            font-family: 'Segoe UI', sans-serif;
            font-size: 13px; font-weight: bold;
            background: transparent;
        """)
        header.addWidget(self._title_lbl)
        header.addStretch()

        self._countdown_lbl = QLabel("30s")
        self._countdown_lbl.setStyleSheet(f"""
            color: {_theme['TEXT_DIM']};
            font-family: 'Consolas', monospace;
            font-size: 11px;
            background: transparent;
        """)
        header.addWidget(self._countdown_lbl)
        layout.addLayout(header)

        self._msg_lbl = QLabel("")
        self._msg_lbl.setWordWrap(True)
        self._msg_lbl.setStyleSheet(f"""
            color: {_theme['TEXT']};
            font-family: 'Segoe UI', sans-serif;
            font-size: 12px;
            background: transparent;
            padding: 4px 0;
        """)
        self._msg_lbl.setMinimumHeight(50)
        layout.addWidget(self._msg_lbl)
        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self._btn_deny = QPushButton("Denegar")
        self._btn_deny.setFixedSize(120, 34)
        self._btn_deny.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_deny.setStyleSheet(f"""
            QPushButton {{
                background: rgba(239,68,68,0.2); color: #f87171;
                border: 1px solid rgba(239,68,68,0.5); border-radius: 8px;
                font-family: 'Segoe UI', sans-serif; font-size: 12px; font-weight: bold;
            }}
            QPushButton:hover {{ background: rgba(239,68,68,0.35); border-color: #ef4444; }}
        """)
        self._btn_deny.clicked.connect(lambda: self._respond(False))

        self._btn_allow = QPushButton("Autorizar")
        self._btn_allow.setFixedSize(120, 34)
        self._btn_allow.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_allow.setStyleSheet(f"""
            QPushButton {{
                background: rgba(16,185,129,0.2); color: #34d399;
                border: 1px solid rgba(16,185,129,0.5); border-radius: 8px;
                font-family: 'Segoe UI', sans-serif; font-size: 12px; font-weight: bold;
            }}
            QPushButton:hover {{ background: rgba(16,185,129,0.35); border-color: #10b981; }}
        """)
        self._btn_allow.clicked.connect(lambda: self._respond(True))

        btn_row.addStretch()
        btn_row.addWidget(self._btn_deny)
        btn_row.addWidget(self._btn_allow)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(245, 158, 11, 80))
        shadow.setOffset(0, 0)
        self.setGraphicsEffect(shadow)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.MouseButton.LeftButton and self._drag_pos:
            self.move(e.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, e):
        self._drag_pos = None

    def _respond(self, authorized: bool):
        FloatingPermiso._result = authorized
        if FloatingPermiso._done_event:
            FloatingPermiso._done_event.set()
        self._timer.stop()
        self.hide()

    def _tick(self):
        self._timer_val -= 1
        self._countdown_lbl.setText(f"{self._timer_val}s")
        if self._timer_val <= 5:
            self._countdown_lbl.setStyleSheet(f"""
                color: {_theme['ERROR']};
                font-family: 'Consolas', monospace;
                font-size: 11px; font-weight: bold;
                background: transparent;
            """)
        if self._timer_val <= 0:
            self._respond(False)

    def ask_permission(self, message: str, title: str = "Permiso Requerido",
                       timeout: int = 30) -> bool:
        done = threading.Event()

        def _show():
            FloatingPermiso._done_event = done
            FloatingPermiso._result = None

            self._msg_lbl.setText(message)
            self._title_lbl.setText(title)
            self._timeout = timeout
            self._timer_val = timeout
            self._countdown_lbl.setText(f"{timeout}s")
            self._countdown_lbl.setStyleSheet(f"""
                color: {_theme['TEXT_DIM']};
                font-family: 'Consolas', monospace;
                font-size: 11px;
                background: transparent;
            """)

            screen = QApplication.primaryScreen().geometry()
            self.move(screen.width() // 2 - self.width() // 2,
                      screen.height() // 2 - self.height() // 2)
            self.show()
            self.raise_()
            self.activateWindow()

            self._timer.start(1000)

        if threading.current_thread() is threading.main_thread():
            _show()
        else:
            from PyQt6.QtCore import QTimer as _QT
            _QT.singleShot(0, _show)

        done.wait(timeout + 2)
        result = FloatingPermiso._result
        self.hide()
        return result if result is not None else False


# ── Singletons ─────────────────────────────────────────────────────────────────

_terminal_panel: TerminalOverlay | None = None
_floating_permiso: FloatingPermiso | None = None
_command_deck_panel: CommandDeckWidget | None = None


def get_terminal_panel() -> TerminalOverlay | None:
    return _terminal_panel


def get_command_deck_panel() -> CommandDeckWidget | None:
    return _command_deck_panel


def get_floating_permiso() -> FloatingPermiso | None:
    return _floating_permiso


def init_panels(parent=None) -> tuple:
    global _terminal_panel, _floating_permiso, _command_deck_panel
    _terminal_panel = TerminalOverlay(parent)
    _command_deck_panel = CommandDeckWidget(parent)
    _floating_permiso = FloatingPermiso(parent)
    return _terminal_panel, _command_deck_panel, _floating_permiso


def floating_ask(message: str, title: str = "Permiso Requerido",
                 timeout: int = 30) -> bool:
    if _floating_permiso is None:
        return False
    return _floating_permiso.ask_permission(message, title, timeout)
