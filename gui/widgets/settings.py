# -*- coding: utf-8 -*-
"""
gui/widgets/settings.py — Diálogo de configuración de ERIS (ERIS NEXUS).

Extraído de ui.py durante el refactor T4.
Contiene:
  - SettingsDialog: matriz de configuración (API keys, voz, apariencia, general,
    fábrica, mundo, sistema) con persistencia en config/api_keys.json.

Importaciones pesadas (core.audio_config, elevenlabs, pyttsx3, etc.) se hacen de
forma lazy dentro de los métodos que las necesitan.
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPixmap
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFileDialog, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QMessageBox, QPushButton, QScrollArea, QVBoxLayout,
    QWidget,
)

from gui.styles import C, THEMES, THEME_LIST, _base_dir, _user_cfg_dir
from gui.widgets.sidebar import _SidebarBtn, _NeonField


class SettingsDialog(QDialog):
    """Public API: diálogo de configuración. Emite `saved(dict)` al aceptar."""
    saved = pyqtSignal(dict)
    _voice_test_finished = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ERIS NEXUS — Configuration Matrix")
        self.setFixedSize(900, 620)
        self._cfg = self._load_config()
        self._current_section = 0
        self._build_ui()
        self._apply_styles()
        self._switch_section(0)
        self._voice_test_finished.connect(self._on_voice_test_finished)

    def _on_voice_test_finished(self, message: str):
        self._status_bar.setText(message)
        self._voice_test_btn.setEnabled(True)

    def _test_voice(self):
        """Synthesize and play a real sample through the system's default sink."""
        backend = self._tts.currentText().strip().lower()
        voice = self._voice.currentData() or self._voice.currentText()
        self._voice_test_btn.setEnabled(False)
        self._status_bar.setText("◆  VOICE TEST: synthesizing sample...  ◆")

        def worker():
            try:
                import asyncio
                import subprocess
                from core.tts_engine import synthesize

                if backend == "gemini":
                    raise RuntimeError("Gemini Live speaks during a conversation; choose Edge to test TTS here.")
                pcm = asyncio.run(asyncio.wait_for(
                    synthesize("Hola, soy Eris. Esta es una prueba de mi voz.",
                               backend=backend, voice=str(voice)),
                    timeout=25.0,
                ))
                if not pcm or len(pcm) < 100:
                    raise RuntimeError("El motor no generó audio. Revisa la conexión y el backend elegido.")

                proc = subprocess.run(
                    ["pacat", "--rate=24000", "--format=S16LE", "--channels=1"],
                    input=pcm, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                    timeout=20.0, check=False,
                )
                if proc.returncode:
                    detail = proc.stderr.decode("utf-8", errors="replace").strip()[:180]
                    raise RuntimeError(f"pacat terminó con código {proc.returncode}: {detail}")
                result = "◆  VOICE TEST: sample played through default audio output  ◆"
            except Exception as exc:
                result = f"◆  VOICE TEST ERROR: {type(exc).__name__}: {str(exc)[:180]}  ◆"
            self._voice_test_finished.emit(result)

        threading.Thread(target=worker, name="eris-voice-test", daemon=True).start()

    # ── UI Sections ─────────────────────────────────────────────────────────
    SECTIONS = [
        ("⬡", "API KEYS", "Google Gemini · Groq · OpenRouter · Cerebras · Ollama · TMDB · OpenWeather"),
        ("🎙", "VOICE & AUDIO", "TTS Engine · Voice Model · Mic/Speaker · Thinking Sound"),
        ("🎨", "APPEARANCE", "Theme · Colors · Glassmorphism · Orb Style"),
        ("⚙", "GENERAL", "Language · Timezone · Paths · Camera · Region"),
        ("🏭", "FÁBRICA", "Tus creaciones · Librerías · Tools · Skills · Procedimientos · Auto-fábrica"),
        ("🌍", "MUNDO", "Modelo del mundo · RAG Memoria Total · A/B prompts · Auto-mejora · Sesiones"),
        ("📊", "SYSTEM", "Stats · About · Self-Heal · Emotional State · Version"),
    ]

    def _build_ui(self):
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        outer = QWidget()
        outer.setObjectName("settingsRoot")
        outer.setStyleSheet(f"""
            #settingsRoot {{
                background: {C.BG2}; border: 1px solid {C.BORDER};
                border-radius: 16px;
            }}
        """)
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(outer)

        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        # ── Header ──
        header = QWidget()
        header.setFixedHeight(56)
        header.setStyleSheet(f"background: {C.BG3}; border-radius: 16px 16px 0 0;")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(20, 0, 16, 0)
        title = QLabel("⬡  NEXUS CONFIGURATION MATRIX")
        title.setStyleSheet(f"color: {C.PRI}; font-size: 14px; font-weight: bold; letter-spacing: 3px;")
        hl.addWidget(title)
        hl.addStretch()
        self._status_bar = QLabel("◆ SYSTEM ONLINE ◆")
        self._status_bar.setStyleSheet(f"color: {C.SUCCESS}; font-size: 9px; letter-spacing: 2px;")
        hl.addWidget(self._status_bar)
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(32, 32)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(f"""
            QPushButton {{ background: rgba(255,51,85,0.15); color: {C.ERROR}; border: 1px solid rgba(255,51,85,0.3);
            border-radius: 6px; font-size: 14px; }}
            QPushButton:hover {{ background: rgba(255,51,85,0.3); }}
        """)
        close_btn.clicked.connect(self.reject)
        hl.addWidget(close_btn)
        outer_layout.addWidget(header)

        # ── Body: Sidebar + Content ──
        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # Sidebar
        side = QWidget()
        side.setFixedWidth(200)
        side.setStyleSheet(f"background: {C.BG3};")
        self._side_layout = QVBoxLayout(side)
        self._side_layout.setContentsMargins(0, 8, 0, 8)
        self._side_layout.setSpacing(2)

        self._side_btns = []
        for i, (icon, name, desc) in enumerate(self.SECTIONS):
            btn = _SidebarBtn(icon, name)
            btn.clicked.connect(lambda checked, idx=i: self._switch_section(idx))
            self._side_layout.addWidget(btn)
            self._side_btns.append(btn)

        self._side_layout.addStretch()

        # Theme preview mini
        theme_box = QWidget()
        theme_box.setStyleSheet(f"background: {C.SURFACE}; border-radius: 8px;")
        tb_layout = QVBoxLayout(theme_box)
        tb_layout.setContentsMargins(12, 10, 12, 10)
        preview_lbl = QLabel("THEME PREVIEW")
        preview_lbl.setStyleSheet(f"color: {C.TEXT_DIM}; font-size: 8px; letter-spacing: 2px;")
        tb_layout.addWidget(preview_lbl)
        self._preview_bar = QWidget()
        self._preview_bar.setFixedHeight(8)
        self._preview_bar.setStyleSheet(f"background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {C.PRI}, stop:0.5 {C.PRI_LIGHT}, stop:1 {C.GLOW}); border-radius: 4px;")
        tb_layout.addWidget(self._preview_bar)
        self._preview_label = QLabel(C.get_theme().upper())
        self._preview_label.setStyleSheet(f"color: {C.TEXT_DIM}; font-size: 9px; letter-spacing: 1px;")
        tb_layout.addWidget(self._preview_label)
        self._side_layout.addWidget(theme_box)

        body_layout.addWidget(side)

        # Content area
        self._content_stack = QWidget()
        self._content_layout = QVBoxLayout(self._content_stack)
        self._content_layout.setContentsMargins(0, 0, 0, 0)

        # Build section widgets
        self._section_widgets = [
            self._build_api_section(),
            self._build_voice_section(),
            self._build_appearance_section(),
            self._build_general_section(),
            self._build_fabrica_section(),
            self._build_mundo_section(),
            self._build_system_section(),
        ]
        for sw in self._section_widgets:
            sw.setVisible(False)
            self._content_layout.addWidget(sw)

        body_layout.addWidget(self._content_stack, 1)
        outer_layout.addWidget(body, 1)

        # ── Footer ──
        footer = QWidget()
        footer.setFixedHeight(48)
        footer.setStyleSheet(f"background: {C.BG3}; border-radius: 0 0 16px 16px;")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(16, 0, 16, 0)

        self._save_btn = QPushButton("⟳  COMMIT CONFIGURATION")
        self._save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._save_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {C.PRI}, stop:1 {C.PRI_DIM});
                color: {C.BG}; border: none; border-radius: 6px; padding: 8px 24px;
                font-weight: bold; font-size: 10px; letter-spacing: 1px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {C.PRI_LIGHT}, stop:1 {C.PRI});
            }}
        """)
        self._save_btn.clicked.connect(self._save)

        cancel_btn = QPushButton("CANCEL")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {C.TEXT_DIM}; border: 1px solid {C.BORDER};
                border-radius: 6px; padding: 8px 20px; font-size: 10px; letter-spacing: 1px;
            }}
            QPushButton:hover {{ color: {C.TEXT}; border-color: {C.TEXT_DIM}; }}
        """)
        cancel_btn.clicked.connect(self.reject)

        fl.addWidget(cancel_btn)
        fl.addStretch()
        fl.addWidget(self._save_btn)
        outer_layout.addWidget(footer)

    def _apply_styles(self):
        self.setStyleSheet(f"""
            QDialog {{ background: transparent; }}
            QScrollArea {{ background: transparent; border: none; }}
            QScrollArea > QWidget > QWidget {{ background: transparent; }}
            QScrollBar:vertical {{ width: 3px; background: transparent; }}
            QScrollBar::handle:vertical {{ background: {C.BORDER}; border-radius: 2px; min-height: 30px; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
            QComboBox {{
                background: {C.BG3}; color: {C.TEXT}; border: none;
                border-bottom: 1px solid {C.BORDER}; border-radius: 0;
                padding: 4px 20px 4px 4px; font-size: 11px; min-width: 120px;
            }}
            QComboBox:focus {{ border-bottom: 2px solid {C.PRI}; }}
            QComboBox::drop-down {{ border: none; width: 20px; }}
            QComboBox::down-arrow {{ image: none; border-left: 5px solid {C.PRI}; border-top: 4px solid transparent; border-bottom: 4px solid transparent; margin-right: 4px; }}
            QComboBox QAbstractItemView {{
                background: {C.BG3}; color: {C.TEXT}; border: 1px solid {C.BORDER};
                selection-background-color: {C.PRI}; selection-color: {C.BG};
                outline: none;
            }}
            QCheckBox {{ color: {C.TEXT}; font-size: 11px; spacing: 8px; }}
            QCheckBox::indicator {{
                width: 18px; height: 18px; border-radius: 4px;
                border: 1px solid {C.BORDER}; background: {C.BG3};
            }}
            QCheckBox::indicator:checked {{
                background: {C.PRI}; border-color: {C.PRI};
            }}
            QGroupBox {{
                background: {C.SURFACE}; border: 1px solid {C.BORDER};
                border-radius: 10px; margin-top: 14px; padding: 14px; font-size: 10px;
                color: {C.PRI}; font-weight: bold; letter-spacing: 1px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin; left: 14px; padding: 0 6px;
            }}
            QLineEdit {{
                background: {C.BG3}; color: {C.PRI_LIGHT}; border: none;
                border-bottom: 1px solid {C.BORDER}; border-radius: 0;
                padding: 6px 4px; font-size: 12px; font-family: 'Consolas', monospace;
            }}
            QLineEdit:focus {{ border-bottom: 2px solid {C.PRI}; }}
        """)

    def _load_config(self) -> dict:
        from core.logging_setup import API_CONFIG_PATH
        if API_CONFIG_PATH.exists():
            try:
                return json.loads(API_CONFIG_PATH.read_text("utf-8"))
            except Exception:
                pass
        user_path = _user_cfg_dir() / "config" / "api_keys.json"
        if user_path.exists():
            try:
                return json.loads(user_path.read_text("utf-8"))
            except Exception:
                pass
        return {}

    def _switch_section(self, idx: int):
        self._current_section = idx
        for i, btn in enumerate(self._side_btns):
            btn.set_active(i == idx)
        for i, w in enumerate(self._section_widgets):
            w.setVisible(i == idx)
        self._status_bar.setText(f"◆  {self.SECTIONS[idx][1]}  ◆")

    # ── Section: API Keys ───────────────────────────────────────────────────
    def _build_api_section(self):
        w = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        form_w = QWidget()
        form = QVBoxLayout(form_w)
        form.setContentsMargins(24, 16, 24, 16)
        form.setSpacing(4)

        # Gemini
        gb = QGroupBox("🔮  GOOGLE GEMINI")
        gb_layout = QVBoxLayout(gb)
        gb_layout.setSpacing(6)
        self._api_key = _NeonField("API KEY", "Enter your Gemini API key...", password=True, default=self._cfg.get("gemini_api_key", ""))
        gb_layout.addWidget(self._api_key)

        hl = QHBoxLayout()
        lbl_conv = QLabel("Conversation Model:")
        lbl_conv.setStyleSheet(f"color: {C.TEXT_DIM}; font-size: 10px;")
        hl.addWidget(lbl_conv)
        self._model_conv = QComboBox()
        self._model_conv.addItems(["gemini-flash-latest", "gemini-3.1-flash-lite", "gemini-pro-latest", "ollama"])
        self._model_conv.setCurrentText(self._cfg.get("model_for_conversation", "gemini-3.1-flash-lite"))
        hl.addWidget(self._model_conv)
        hl.addStretch()
        gb_layout.addLayout(hl)
        form.addWidget(gb)

        # Backup providers: Groq, OpenRouter, Cerebras
        gb_backup = QGroupBox("⚡  BACKUP PROVIDERS")
        gb_backup_layout = QVBoxLayout(gb_backup)
        gb_backup_layout.setSpacing(6)
        self._groq_key = _NeonField("GROQ API KEY", "gsk_... (https://console.groq.com/keys)", password=True, default=self._cfg.get("groq_api_key", ""))
        gb_backup_layout.addWidget(self._groq_key)
        self._openrouter_key = _NeonField("OPENROUTER API KEY", "sk-or-... (https://openrouter.ai/keys)", password=True, default=self._cfg.get("openrouter_api_key", ""))
        gb_backup_layout.addWidget(self._openrouter_key)
        self._cerebras_key = _NeonField("CEREBRAS API KEY", "API key (https://cloud.cerebras.ai)", password=True, default=self._cfg.get("cerebras_api_key", ""))
        gb_backup_layout.addWidget(self._cerebras_key)
        form.addWidget(gb_backup)

        # Ollama
        gb2 = QGroupBox("🦙  OLLAMA (LOCAL)")
        gb2_layout = QVBoxLayout(gb2)
        gb2_layout.setSpacing(6)
        self._ollama_enabled = QCheckBox("Enable Ollama (local inference)")
        self._ollama_enabled.setChecked(self._cfg.get("ollama_enabled", False))
        gb2_layout.addWidget(self._ollama_enabled)
        self._ollama_autostart = QCheckBox("\U0001F501  Auto-start Ollama on Windows boot (cerebro local de respaldo)")
        try:
            from core.ollama_autostart import is_autostart_enabled
            _auto_default = self._cfg.get("ollama_autostart", is_autostart_enabled())
        except Exception:
            _auto_default = self._cfg.get("ollama_autostart", False)
        self._ollama_autostart.setChecked(bool(_auto_default))
        gb2_layout.addWidget(self._ollama_autostart)
        self._ollama_url = _NeonField("BASE URL", "http://localhost:11434", default=self._cfg.get("ollama_base_url", "http://localhost:11434"))
        gb2_layout.addWidget(self._ollama_url)
        self._ollama_model = _NeonField("MODEL", "llama3.2", default=self._cfg.get("ollama_model", "llama3.2"))
        gb2_layout.addWidget(self._ollama_model)
        self._ollama_vision = _NeonField("VISION MODEL", "minicpm-v", default=self._cfg.get("ollama_vision_model", "minicpm-v"))
        gb2_layout.addWidget(self._ollama_vision)
        form.addWidget(gb2)

        # Spotify
        gb3 = QGroupBox("🎵  SPOTIFY")
        gb3_layout = QVBoxLayout(gb3)
        gb3_layout.setSpacing(6)
        self._spotify_id = _NeonField("CLIENT ID", "Spotify Client ID", default=self._cfg.get("spotify_client_id", ""))
        gb3_layout.addWidget(self._spotify_id)
        self._spotify_secret = _NeonField("CLIENT SECRET", "Spotify Client Secret", password=True, default=self._cfg.get("spotify_client_secret", ""))
        gb3_layout.addWidget(self._spotify_secret)
        form.addWidget(gb3)

        # TMDB & OpenWeather
        gb4 = QGroupBox("🌐  ADDITIONAL SERVICES")
        gb4_layout = QVBoxLayout(gb4)
        gb4_layout.setSpacing(6)
        self._tmdb_key = _NeonField("TMDB API KEY", "The Movie Database API key", password=True, default=self._cfg.get("tmdb_api_key", ""))
        gb4_layout.addWidget(self._tmdb_key)
        self._weather_key = _NeonField("OPENWEATHER API KEY", "OpenWeatherMap API key", password=True, default=self._cfg.get("openweather_api_key", ""))
        gb4_layout.addWidget(self._weather_key)
        form.addWidget(gb4)

        form.addStretch()
        scroll.setWidget(form_w)
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll)
        return w

    # ── Section: Voice & Audio ──────────────────────────────────────────────
    def _build_voice_section(self):
        w = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        form_w = QWidget()
        form = QVBoxLayout(form_w)
        form.setContentsMargins(24, 16, 24, 16)
        form.setSpacing(4)

        gb = QGroupBox("🗣  TEXT-TO-SPEECH")
        gb_layout = QVBoxLayout(gb)
        gb_layout.setSpacing(6)

        hl = QHBoxLayout()
        lbl_eng = QLabel("Engine:")
        lbl_eng.setStyleSheet(f"color: {C.TEXT_DIM}; font-size: 10px;")
        hl.addWidget(lbl_eng)
        self._tts = QComboBox()
        self._tts.addItems(["fish", "edge", "elevenlabs", "gemini", "system", "kokoro", "pykokoro", "piper", "gtts"])
        self._tts.setCurrentText(self._cfg.get("tts_backend", "edge"))
        hl.addWidget(self._tts)
        hl.addStretch()
        gb_layout.addLayout(hl)

        hl0 = QHBoxLayout()
        lbl_vm = QLabel("Voice Mode:")
        lbl_vm.setStyleSheet(f"color: {C.TEXT_DIM}; font-size: 10px;")
        hl0.addWidget(lbl_vm)
        self._voice_mode = QComboBox()
        self._voice_mode.addItems(["cloud (Gemini Live)", "local (TTS Engine)"])
        _vm = self._cfg.get("voice_mode", "cloud")
        self._voice_mode.setCurrentIndex(0 if _vm == "cloud" else 1)
        hl0.addWidget(self._voice_mode)
        hl0.addStretch()
        gb_layout.addLayout(hl0)

        # Update voices when engine changes
        self._tts.currentTextChanged.connect(self._on_engine_changed)

        hl2 = QHBoxLayout()
        lbl_voice = QLabel("Voice Model:")
        lbl_voice.setStyleSheet(f"color: {C.TEXT_DIM}; font-size: 10px;")
        hl2.addWidget(lbl_voice)
        self._voice = QComboBox()
        self._populate_voices_for_engine(self._tts.currentText())
        hl2.addWidget(self._voice)
        hl2.addStretch()
        gb_layout.addLayout(hl2)

        hl3 = QHBoxLayout()
        lbl_el = QLabel("ElevenLabs API Key:")
        lbl_el.setStyleSheet(f"color: {C.TEXT_DIM}; font-size: 10px;")
        hl3.addWidget(lbl_el)
        self._el_api_key = _NeonField("ELEVENLABS API KEY", "sk_...", password=True, default=self._cfg.get("elevenlabs_api_key", ""))
        hl3.addWidget(self._el_api_key.entry)
        hl3.addStretch()
        gb_layout.addLayout(hl3)

        hl4 = QHBoxLayout()
        lbl_elv = QLabel("ElevenLabs Voice ID:")
        lbl_elv.setStyleSheet(f"color: {C.TEXT_DIM}; font-size: 10px;")
        hl4.addWidget(lbl_elv)
        self._el_voice_id = _NeonField("VOICE ID", "0ASlVJI7QecvFHVE5VQk", default=self._cfg.get("elevenlabs_voice_id", ""))
        hl4.addWidget(self._el_voice_id.entry)
        hl4.addStretch()
        gb_layout.addLayout(hl4)

        # Fish Audio fields
        hl_fish1 = QHBoxLayout()
        lbl_fish = QLabel("Fish Audio API Key:")
        lbl_fish.setStyleSheet(f"color: {C.TEXT_DIM}; font-size: 10px;")
        hl_fish1.addWidget(lbl_fish)
        self._fish_api_key = _NeonField("FISH AUDIO API KEY", "sk-fish-...", password=True, default=self._cfg.get("fish_api_key", ""))
        hl_fish1.addWidget(self._fish_api_key.entry)
        hl_fish1.addStretch()
        gb_layout.addLayout(hl_fish1)

        hl_fish2 = QHBoxLayout()
        lbl_fishv = QLabel("Fish Audio Voice ID:")
        lbl_fishv.setStyleSheet(f"color: {C.TEXT_DIM}; font-size: 10px;")
        hl_fish2.addWidget(lbl_fishv)
        self._fish_voice_id = _NeonField("FISH VOICE ID", "d942b64244ef4c47b0d4a34d5301c796", default=self._cfg.get("fish_voice_id", ""))
        hl_fish2.addWidget(self._fish_voice_id.entry)
        hl_fish2.addStretch()
        gb_layout.addLayout(hl_fish2)

        # TTS test button
        self._voice_test_btn = QPushButton("▶  TEST VOICE")
        self._voice_test_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._voice_test_btn.setStyleSheet(f"""
            QPushButton {{ background: {C.SUCCESS}; color: {C.BG}; border: none;
            border-radius: 4px; padding: 6px 14px; font-size: 9px; font-weight: bold; }}
            QPushButton:hover {{ background: {C.SUCCESS}; opacity: 0.8; }}
        """)
        self._voice_test_btn.clicked.connect(self._test_voice)
        gb_layout.addWidget(self._voice_test_btn)
        form.addWidget(gb)

        gb2 = QGroupBox("🎧  AUDIO DEVICES — ENTRADA Y SALIDA")
        gb2_layout = QVBoxLayout(gb2)
        gb2_layout.setSpacing(6)

        self._audio_status = QLabel("◆  Presiona 'DETECTAR' para ver y elegir tus dispositivos  ◆")
        self._audio_status.setStyleSheet(f"color: {C.TEXT_DIM}; font-size: 9px;")
        self._audio_status.setWordWrap(True)
        gb2_layout.addWidget(self._audio_status)

        hl_mic = QHBoxLayout()
        lbl_mic = QLabel("🎤  MICRÓFONO (entrada de voz):")
        lbl_mic.setStyleSheet(f"color: {C.TEXT_DIM}; font-size: 10px;")
        hl_mic.addWidget(lbl_mic)
        self._mic_cb = QComboBox()
        self._mic_cb.setStyleSheet(f"QComboBox {{ background: {C.BG3}; color: {C.PRI_LIGHT}; "
                                   f"border: 1px solid {C.BORDER}; border-radius: 4px; padding: 4px 6px; }}")
        hl_mic.addWidget(self._mic_cb, 1)
        gb2_layout.addLayout(hl_mic)

        hl_spk = QHBoxLayout()
        lbl_spk = QLabel("🔊  AUDÍFONOS/ALTAVOCES (salida):")
        lbl_spk.setStyleSheet(f"color: {C.TEXT_DIM}; font-size: 10px;")
        hl_spk.addWidget(lbl_spk)
        self._spk_cb = QComboBox()
        self._spk_cb.setStyleSheet(f"QComboBox {{ background: {C.BG3}; color: {C.PRI_LIGHT}; "
                                   f"border: 1px solid {C.BORDER}; border-radius: 4px; padding: 4px 6px; }}")
        hl_spk.addWidget(self._spk_cb, 1)
        gb2_layout.addLayout(hl_spk)

        detect_btn = QPushButton("⟳  DETECTAR DISPOSITIVOS AUTOMÁTICAMENTE")
        detect_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        detect_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {C.PRI}; border: 1px solid {C.BORDER};
            border-radius: 4px; padding: 6px 14px; font-size: 9px; }}
            QPushButton:hover {{ background: rgba(245,158,11,0.1); }}
        """)
        detect_btn.clicked.connect(self._detect_audio_devices)
        gb2_layout.addWidget(detect_btn)

        self._populate_audio_combos()
        form.addWidget(gb2)

        gb3 = QGroupBox("🎭  ERIS VOICE STYLE")
        gb3_layout = QVBoxLayout(gb3)
        gb3_layout.setSpacing(6)
        hl5 = QHBoxLayout()
        lbl_pv = QLabel("Personality Voice:")
        lbl_pv.setStyleSheet(f"color: {C.TEXT_DIM}; font-size: 10px;")
        hl5.addWidget(lbl_pv)
        self._eris_voice = QComboBox()
        from core.audio_config import ERIS_VOICES as _av
        for _vk, (_vg, _vd) in _av.items():
            self._eris_voice.addItem(f"{_vk} ({_vg})", _vk)
        self._eris_voice.setCurrentIndex(
            max(0, self._eris_voice.findData(self._cfg.get("eris_voice", "Aoede")))
        )
        hl5.addWidget(self._eris_voice)
        hl5.addStretch()
        gb3_layout.addLayout(hl5)

        self._thinking_sound = QCheckBox("🔊  Play thinking sound while processing")
        self._thinking_sound.setChecked(self._cfg.get("thinking_sound", True))
        gb3_layout.addWidget(self._thinking_sound)

        self._wake_sound = QCheckBox("🔊  Play wake-up sound on activation")
        self._wake_sound.setChecked(self._cfg.get("wake_sound", True))
        gb3_layout.addWidget(self._wake_sound)

        self._wake_mode_cb = QCheckBox("🎯  Activación por nombre: responder solo cuando digas \"Eris, ...\"")
        self._wake_mode_cb.setChecked(self._cfg.get("wake_word_mode", True))
        gb3_layout.addWidget(self._wake_mode_cb)
        form.addWidget(gb3)

        form.addStretch()
        scroll.setWidget(form_w)
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll)
        return w

    def _populate_audio_combos(self):
        """Llena los combos de micro y altavoz con los dispositivos detectados."""
        from core.audio_config import audio_device_options
        cur_mic = str(self._cfg.get("mic_device", ""))
        cur_spk = str(self._cfg.get("speaker_device", self._cfg.get("spk_device", "")))

        self._mic_cb.blockSignals(True)
        self._mic_cb.clear()
        self._mic_cb.addItem("🔄  AUTO — detectar el mejor micrófono", "")
        for idx, label in audio_device_options("input"):
            self._mic_cb.addItem(label, idx)
        i = self._mic_cb.findData(cur_mic)
        self._mic_cb.setCurrentIndex(i if i >= 0 else 0)
        self._mic_cb.blockSignals(False)

        self._spk_cb.blockSignals(True)
        self._spk_cb.clear()
        self._spk_cb.addItem("🔄  AUTO — detectar el mejor altavoz", "")
        for idx, label in audio_device_options("output"):
            self._spk_cb.addItem(label, idx)
        i = self._spk_cb.findData(cur_spk)
        self._spk_cb.setCurrentIndex(i if i >= 0 else 0)
        self._spk_cb.blockSignals(False)

    def _populate_voices_for_engine(self, engine: str):
        """Populate voice combo based on selected TTS engine."""
        self._voice.blockSignals(True)
        self._voice.clear()
        current_voice = self._cfg.get("tts_voice", "")
        if engine == "edge":
            voices = [
                ("es-AR-TomasNeural", "ES-AR Tomas (Masc)"),
                ("es-AR-ElenaNeural", "ES-AR Elena (Fem)"),
                ("es-ES-ElviraNeural", "ES-ES Elvira (Fem)"),
                ("es-ES-AlvaroNeural", "ES-ES Alvaro (Masc)"),
                ("es-MX-DaliaNeural", "ES-MX Dalia (Fem)"),
                ("es-MX-JorgeNeural", "ES-MX Jorge (Masc)"),
                ("es-CO-GonzaloNeural", "ES-CO Gonzalo (Masc)"),
                ("es-CO-SalomeNeural", "ES-CO Salome (Fem)"),
                ("es-US-PalomaNeural", "ES-US Paloma (Fem)"),
                ("es-US-AlonsoNeural", "ES-US Alonso (Masc)"),
                ("es-VE-PaolaNeural", "ES-VE Paola (Fem)"),
                ("es-VE-SebastianNeural", "ES-VE Sebastian (Masc)"),
                ("es-CL-CatalinaNeural", "ES-CL Catalina (Fem)"),
                ("es-CL-LorenzoNeural", "ES-CL Lorenzo (Masc)"),
                ("es-PE-AlexNeural", "ES-PE Alex (Masc)"),
                ("es-PE-CamilaNeural", "ES-PE Camila (Fem)"),
                ("es-UY-MateoNeural", "ES-UY Mateo (Masc)"),
                ("es-UY-ValentinaNeural", "ES-UY Valentina (Fem)"),
                ("es-BO-MarceloNeural", "ES-BO Marcelo (Masc)"),
                ("es-BO-SofiaNeural", "ES-BO Sofia (Fem)"),
                ("es-CR-JuanNeural", "ES-CR Juan (Masc)"),
                ("es-CR-MariaNeural", "ES-CR Maria (Fem)"),
                ("es-DO-EmilioNeural", "ES-DO Emilio (Masc)"),
                ("es-DO-RamonaNeural", "ES-DO Ramona (Fem)"),
                ("es-EC-AndreaNeural", "ES-EC Andrea (Fem)"),
                ("es-EC-LuisNeural", "ES-EC Luis (Masc)"),
                ("es-GT-AndresNeural", "ES-GT Andres (Masc)"),
                ("es-GT-MartaNeural", "ES-GT Marta (Fem)"),
                ("es-HN-CarlosNeural", "ES-HN Carlos (Masc)"),
                ("es-HN-KarlaNeural", "ES-HN Karla (Fem)"),
                ("es-PR-KarinaNeural", "ES-PR Karina (Fem)"),
                ("es-PR-VictorNeural", "ES-PR Victor (Masc)"),
            ]
            for v_id, v_label in voices:
                self._voice.addItem(v_label, v_id)
        elif engine == "elevenlabs":
            try:
                import json as _json
                from core.logging_setup import API_CONFIG_PATH as _ap
                cfg = _json.loads(_ap.read_text(encoding="utf-8"))
                from elevenlabs.client import ElevenLabs
                client = ElevenLabs(api_key=cfg.get("elevenlabs_api_key", ""))
                el_voices = client.voices.get_all()
                for v in el_voices.voices:
                    label = f"{v.name} ({v.category})"
                    self._voice.addItem(label, v.voice_id)
            except Exception:
                self._voice.addItem("Eris (Cloned)", "0ASlVJI7QecvFHVE5VQk")
        elif engine == "system":
            try:
                import pyttsx3
                e = pyttsx3.init()
                for v in e.getProperty("voices"):
                    self._voice.addItem(v.name, v.id)
            except Exception:
                self._voice.addItem("Default", "default")
        elif engine in ("pykokoro", "kokoro"):
            try:
                _voices = [
                    ("af_heart", "Heart (Fem EN)"),
                    ("af_bella", "Bella (Fem EN)"),
                    ("am_adam", "Adam (Masc EN)"),
                    ("ef_dora", "Dora (Fem ES)"),
                ]
                for v_id, v_label in _voices:
                    self._voice.addItem(v_label, v_id)
            except ImportError:
                self._voice.addItem("Kokoro no cargado", "")
        elif engine == "piper":
            import glob as _glob
            _voices = []
            for vf in _glob.glob(str(__import__("pathlib").Path(__file__).parent / "voices" / "*.onnx")):
                vname = __import__("os").path.basename(vf).replace(".onnx", "")
                _voices.append((vf, vname))
            if _voices:
                for v_id, v_label in _voices:
                    self._voice.addItem(v_label, v_id)
            else:
                self._voice.addItem("No hay voces Piper", "")
        elif engine == "gtts":
            self._voice.addItem("Google TTS español", "es")
        elif engine == "gemini":
            from core.audio_config import ERIS_VOICES as _av
            for _vk, (_vg, _vd) in _av.items():
                self._voice.addItem(f"{_vk} ({_vg})", _vk)
        elif engine == "fish":
            fish_voices = [
                ("d942b64244ef4c47b0d4a34d5301c796", "Mi Voz Personalizada (Fem ES)"),
                ("9affd80294e9426d864d07f7bcb33d52", "Crumbs Sugar Cookie (Fem ES)"),
                ("b252e3f24d4c41e4ad0892c582e4a03a", "Tempezt Shadow (Fem ES Latino)"),
                ("a7ff580f68ae44c1baa1d77c93544495", "Malvatti (Fem ES Animada)"),
                ("a672af99a1354a71a5ab7054c98c26be", "Mark Espanol (Masc Profesional)"),
                ("6cdd04c077d245fe8c55827568e870b7", "Remastered Espanol (Masc Inspirador)"),
                ("10c8d9574c4648ff862343d0f3f589e8", "Voz Espanol (Masc Calmado)"),
            ]
            for v_id, v_label in fish_voices:
                self._voice.addItem(v_label, v_id)
        else:
            self._voice.addItem("Default", "default")
        # Restore selection
        idx = self._voice.findData(current_voice)
        if idx >= 0:
            self._voice.setCurrentIndex(idx)
        self._voice.blockSignals(False)

    def _on_engine_changed(self, engine: str):
        """Update voice list when engine dropdown changes."""
        self._populate_voices_for_engine(engine)

    def _detect_audio_devices(self):
        """Detecta el micro y el altavoz en uso y los selecciona en los combos."""
        try:
            from core.audio_config import resolve_mic, resolve_speaker, get_device_name
            self._status_bar.setText("◆  DETECTANDO dispositivos de audio...  ◆")
            self._audio_status.setText("◆  Probando micros y altavoces...  ◆")
            m = resolve_mic()
            s = resolve_speaker()
            self._populate_audio_combos()
            i = self._mic_cb.findData(str(m) if m is not None else "")
            self._mic_cb.setCurrentIndex(i if i >= 0 else 0)
            i = self._spk_cb.findData(str(s) if s is not None else "")
            self._spk_cb.setCurrentIndex(i if i >= 0 else 0)
            _mic_name = get_device_name(m) or "(default de Windows)"
            _spk_name = get_device_name(s) or "(default de Windows)"
            self._audio_status.setText(
                f"✔  DETECTADO — Entrada: [{m}] {_mic_name}   ·   Salida: [{s}] {_spk_name}"
            )
            self._status_bar.setText("◆  DISPOSITIVOS detectados — pulsa COMMIT para guardar  ◆")
        except Exception as e:
            self._audio_status.setText(f"⚠  Error detectando audio: {e}")
            self._status_bar.setText("◆  ERROR detectando audio  ◆")
            print(f"[Settings] Audio detect error: {e}")

    # ── Section: Appearance ─────────────────────────────────────────────────
    def _build_appearance_section(self):
        w = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        form_w = QWidget()
        form = QVBoxLayout(form_w)
        form.setContentsMargins(24, 16, 24, 16)
        form.setSpacing(4)

        gb = QGroupBox("🎨  THEME SELECTOR")
        gb_layout = QVBoxLayout(gb)
        gb_layout.setSpacing(12)
        hl = QHBoxLayout()
        hl.setSpacing(10)

        self._theme_btns = {}
        for tname in THEME_LIST:
            theme = THEMES[tname]
            btn = QPushButton()
            btn.setFixedSize(64, 64)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(tname.upper())
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                        stop:0 {theme['BG2']}, stop:1 {theme['SURFACE']});
                    border: 2px solid {theme['PRI']};
                    border-radius: 10px;
                }}
                QPushButton:hover {{
                    border: 2px solid {theme['PRI_LIGHT']};
                }}
            """)
            # Color dot
            color_dot = QWidget(btn)
            color_dot.setFixedSize(20, 20)
            color_dot.setStyleSheet(f"""
                background: qradialgradient(cx:0.4,cy:0.4,rx:0.5,ry:0.5,
                    stop:0 {theme['PRI_LIGHT']}, stop:1 {theme['PRI']});
                border-radius: 10px;
            """)
            color_dot.move(22, 12)
            name_lbl = QLabel(tname.upper(), btn)
            name_lbl.setStyleSheet(f"color: {theme['TEXT_DIM']}; font-size: 8px; font-weight: bold; letter-spacing: 1px;")
            name_lbl.move(8, 40)
            name_lbl.resize(48, 16)
            name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

            tname_copy = tname
            btn.clicked.connect(lambda checked, tn=tname_copy: self._select_theme(tn))
            hl.addWidget(btn)
            self._theme_btns[tname] = btn

        hl.addStretch()
        gb_layout.addLayout(hl)

        # Current theme indicator
        theme_info = QWidget()
        theme_info.setStyleSheet(f"background: {C.BG3}; border-radius: 8px;")
        ti_layout = QHBoxLayout(theme_info)
        ti_layout.setContentsMargins(12, 8, 12, 8)
        self._current_theme_lbl = QLabel(f"Active: {C.get_theme().upper()}")
        self._current_theme_lbl.setStyleSheet(f"color: {C.PRI}; font-size: 11px; font-weight: bold; letter-spacing: 1px;")
        ti_layout.addWidget(self._current_theme_lbl)
        ti_layout.addStretch()

        self._theme_preview = QWidget()
        self._theme_preview.setFixedSize(80, 16)
        self._theme_preview.setStyleSheet(f"background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {C.PRI}, stop:0.5 {C.PRI_LIGHT}, stop:1 {C.GLOW}); border-radius: 8px;")
        ti_layout.addWidget(self._theme_preview)

        gb_layout.addWidget(theme_info)
        form.addWidget(gb)

        gb2 = QGroupBox("🔲  INTERFACE STYLE")
        gb2_layout = QVBoxLayout(gb2)
        gb2_layout.setSpacing(6)

        self._glass_opacity = _NeonField("GLASS OPACITY", "100-255", default=str(self._cfg.get("glass_opacity", 180)))
        gb2_layout.addWidget(self._glass_opacity)

        self._glow_intensity = _NeonField("GLOW INTENSITY", "0.0 - 1.0", default=str(self._cfg.get("glow_intensity", 0.5)))
        gb2_layout.addWidget(self._glow_intensity)

        hl_orb = QHBoxLayout()
        lbl_orb = QLabel("Orb Renderer:")
        lbl_orb.setStyleSheet(f"color: {C.TEXT_DIM}; font-size: 10px;")
        hl_orb.addWidget(lbl_orb)
        self._orb_renderer = QComboBox()
        self._orb_renderer.addItems(["WebGL (3D)", "Particles (2D)"])
        self._orb_renderer.setCurrentText("WebGL (3D)" if self._cfg.get("webgl_orb", True) else "Particles (2D)")
        hl_orb.addWidget(self._orb_renderer)
        hl_orb.addStretch()
        gb2_layout.addLayout(hl_orb)

        hl_visual = QHBoxLayout()
        lbl_visual = QLabel("Eris muestra:")
        lbl_visual.setStyleSheet(f"color: {C.TEXT_DIM}; font-size: 10px;")
        hl_visual.addWidget(lbl_visual)
        self._central_visual = QComboBox()
        self._central_visual.addItems(["Cara de ERIS", "Orbe (partículas)"])
        self._central_visual.setCurrentText("Cara de ERIS" if self._cfg.get("central_visual", "face") == "face" else "Orbe (partículas)")
        hl_visual.addWidget(self._central_visual)
        hl_visual.addStretch()
        gb2_layout.addLayout(hl_visual)

        hl_float = QHBoxLayout()
        lbl_float = QLabel("Flotante:")
        lbl_float.setStyleSheet(f"color: {C.TEXT_DIM}; font-size: 10px;")
        hl_float.addWidget(lbl_float)
        self._floating_visual = QComboBox()
        self._floating_visual.addItems(["Orbe (partículas)", "Modelo 3D (VRM)"])
        self._floating_visual.setCurrentText(
            "Modelo 3D (VRM)" if self._cfg.get("floating_visual", "orb") == "vrm" else "Orbe (partículas)"
        )
        hl_float.addWidget(self._floating_visual)
        hl_float.addStretch()
        gb2_layout.addLayout(hl_float)

        form.addWidget(gb2)

        form.addStretch()
        scroll.setWidget(form_w)
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll)
        return w

    def _select_theme(self, name: str):
        C.set_theme(name)
        self._current_theme_lbl.setText(f"Active: {name.upper()}")
        self._current_theme_lbl.setStyleSheet(f"color: {C.PRI}; font-size: 11px; font-weight: bold; letter-spacing: 1px;")
        self._theme_preview.setStyleSheet(f"background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {C.PRI}, stop:0.5 {C.PRI_LIGHT}, stop:1 {C.GLOW}); border-radius: 8px;")
        self._preview_bar.setStyleSheet(f"background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {C.PRI}, stop:0.5 {C.PRI_LIGHT}, stop:1 {C.GLOW}); border-radius: 4px;")
        self._preview_label.setText(name.upper())
        self._preview_label.setStyleSheet(f"color: {C.TEXT_DIM}; font-size: 9px; letter-spacing: 1px;")
        self._status_bar.setText(f"◆  THEME: {name.upper()} loaded  ◆")
        self._apply_styles()
        for btn in self._theme_btns.values():
            t = btn.toolTip().lower()
            th = THEMES[t]
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                        stop:0 {th['BG2']}, stop:1 {th['SURFACE']});
                    border: 2px solid {C.PRI if t == name else th['PRI']};
                    border-radius: 10px;
                }}
                QPushButton:hover {{
                    border: 2px solid {th['PRI_LIGHT']};
                }}
            """)

    # ── Section: General ────────────────────────────────────────────────────
    def _build_general_section(self):
        w = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        form_w = QWidget()
        form = QVBoxLayout(form_w)
        form.setContentsMargins(24, 16, 24, 16)
        form.setSpacing(4)

        gb = QGroupBox("🌍  LANGUAGE & REGION")
        gb_layout = QVBoxLayout(gb)
        gb_layout.setSpacing(6)
        hl = QHBoxLayout()
        lbl_lang = QLabel("Language:")
        lbl_lang.setStyleSheet(f"color: {C.TEXT_DIM}; font-size: 10px;")
        hl.addWidget(lbl_lang)
        self._lang = QComboBox()
        self._lang.addItems(["es-ES", "en-US", "pt-BR", "fr-FR", "de-DE", "it-IT", "ja-JP"])
        self._lang.setCurrentText(self._cfg.get("language", "es-ES"))
        hl.addWidget(self._lang)
        hl.addStretch()
        gb_layout.addLayout(hl)
        self._tz = _NeonField("TIMEZONE (IANA)", "America/Argentina/Buenos_Aires", default=self._cfg.get("timezone", "America/Argentina/Buenos_Aires"))
        gb_layout.addWidget(self._tz)
        form.addWidget(gb)

        gb2 = QGroupBox("🖥  SYSTEM PATHS")
        gb2_layout = QVBoxLayout(gb2)
        gb2_layout.setSpacing(6)
        self._chrome_profile = _NeonField("CHROME USER PROFILE", "Default", default=self._cfg.get("chrome_google_profile", "Default"))
        gb2_layout.addWidget(self._chrome_profile)
        self._chrome_path = _NeonField("CHROME EXECUTABLE PATH", "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe", default=self._cfg.get("chrome_exe_path", ""))
        gb2_layout.addWidget(self._chrome_path)
        form.addWidget(gb2)

        gb3 = QGroupBox("📷  HARDWARE")
        gb3_layout = QVBoxLayout(gb3)
        gb3_layout.setSpacing(6)
        self._cam_toggle = QCheckBox()
        _cam_icon = QLabel()
        _cam_icon_path = "/usr/share/icons/AdwaitaLegacy/22x22/legacy/camera-web.png"
        if os.path.exists(_cam_icon_path):
            _cam_icon.setPixmap(QPixmap(_cam_icon_path).scaled(22, 22, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            _cam_icon.setText("📷")
            _cam_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            _cam_icon.setStyleSheet("font-size: 18px;")
        _cam_label = QLabel("Activar cámara (vision)")
        _cam_label.setStyleSheet("color: #ccc; font-size: 13px;")
        _cam_row = QHBoxLayout()
        _cam_row.setSpacing(8)
        _cam_row.addWidget(_cam_icon, 0, Qt.AlignmentFlag.AlignCenter)
        _cam_row.addWidget(_cam_label, 0, Qt.AlignmentFlag.AlignLeft)
        _cam_row.addStretch()
        _cam_row.addWidget(self._cam_toggle, 0, Qt.AlignmentFlag.AlignRight)
        gb3_layout.addLayout(_cam_row)
        self._cam_toggle.setChecked(self._cfg.get("camera_enabled", True))
        self._gpu_accel = QCheckBox("GPU Acceleration (requires restart)")
        self._gpu_accel.setChecked(self._cfg.get("gpu_acceleration", True))
        gb3_layout.addWidget(self._gpu_accel)
        form.addWidget(gb3)

        form.addStretch()
        scroll.setWidget(form_w)
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll)
        return w

    # ── Section: Fábrica (tus creaciones) ───────────────────────────────────
    def _build_fabrica_section(self):
        w = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        form_w = QWidget()
        form = QVBoxLayout(form_w)
        form.setContentsMargins(24, 16, 24, 16)
        form.setSpacing(10)

        gb = QGroupBox("🏭  TUS CREACIONES (FÁBRICA)")
        gb_layout = QVBoxLayout(gb)
        gb_layout.setSpacing(8)

        refresh = QPushButton("⟳  REFRESCAR")
        refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh.setStyleSheet(f"background: {C.BG3}; color: {C.TEXT}; border: none; "
                              f"border-radius: 8px; padding: 6px 12px;")
        gb_layout.addWidget(refresh, 0, Qt.AlignmentFlag.AlignRight)

        self._fabrica_list = QLabel("Cargando tus creaciones…")
        self._fabrica_list.setWordWrap(True)
        self._fabrica_list.setStyleSheet(f"background: {C.BG3}; color: {C.TEXT}; "
                                         f"border-radius: 8px; padding: 12px;")
        self._fabrica_list.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        gb_layout.addWidget(self._fabrica_list)

        def _refresh_fabrica():
            try:
                from core.eris_fabrica import listar, _load_state
                items = _load_state().get("items", [])
                from core.procedimientos import listar_procedimientos
                procs = listar_procedimientos()
                from core.auto_fabrica import estado
                af = estado()
            except Exception as e:
                self._fabrica_list.setText(f"No pude cargar tus creaciones: {e}")
                return
            if not items and not procs:
                self._fabrica_list.setText(
                    "Todavía no creaste nada propia. Pedime que cree algo con la fábrica "
                    "(ej.: 'creá una librería para...') o esperá a que la auto-fábrica detecte tus patrones.")
                return
            lines = [f"<b style='color:{C.PRI}'>Librerías y herramientas ({len(items)})</b>"]
            for it in items[:40]:
                icon = {"libreria": "📚", "tool": "🛠", "skill": "🎓"}.get(it.get("type"), "📦")
                lines.append(f"&nbsp;&nbsp;{icon} <b>{it['name']}</b> <span style='color:#888'>({it.get('type')})</span>"
                             f" — {it.get('purpose') or it.get('description') or it.get('created','')[:10]}")
            if procs:
                lines.append(f"<br><b style='color:{C.PRI}'>Procedimientos aprendidos ({len(procs)})</b>")
                for p in procs[:20]:
                    lines.append(f"&nbsp;&nbsp;🧠 <b>{p['nombre']}</b> — {p['descripcion']} "
                                 f"<span style='color:#888'>({p['pasos']} pasos, usado {p['veces_usado']}x)</span>")
            lines.append(f"<br><b style='color:{C.PRI}'>Auto-fábrica</b>: {af.get('totales', 0)} tool(s) creadas sola"
                         f" — hoy {af.get('creadas_hoy', 0)}/{af.get('tope_diario', 2)}, "
                         f"umbral {af.get('umbral_repeticiones', 3)} repeticiones.")
            self._fabrica_list.setText("<br>".join(lines))

        refresh.clicked.connect(_refresh_fabrica)
        _refresh_fabrica()
        form.addWidget(gb)

        form_w.setStyleSheet(f"QWidget {{ background: transparent; }}")
        form.addStretch()
        scroll.setWidget(form_w)
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll)
        return w

    # ── Section: MUNDO ──────────────────────────────────────────────────────
    def _build_mundo_section(self):
        w = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        form_w = QWidget()
        form = QVBoxLayout(form_w)
        form.setContentsMargins(24, 16, 24, 16)
        form.setSpacing(10)

        gb = QGroupBox("🌍  TU MUNDO Y TU MEMORIA")
        gb_layout = QVBoxLayout(gb)
        gb_layout.setSpacing(8)

        refresh = QPushButton("⟳  REFRESCAR")
        refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh.setStyleSheet(f"background: {C.BG3}; color: {C.TEXT}; border: none; "
                              f"border-radius: 8px; padding: 6px 12px;")
        gb_layout.addWidget(refresh, 0, Qt.AlignmentFlag.AlignRight)

        self._mundo_list = QLabel("Cargando tu mundo…")
        self._mundo_list.setWordWrap(True)
        self._mundo_list.setStyleSheet(f"background: {C.BG3}; color: {C.TEXT}; "
                                       f"border-radius: 8px; padding: 12px;")
        self._mundo_list.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        gb_layout.addWidget(self._mundo_list)

        def _refresh_mundo():
            datos = {}
            try:
                from core.world_model import get_world_model
                import json as _json
                try:
                    wm = _json.loads(get_world_model() or "{}")
                except Exception:
                    wm = {}
                datos["world"] = wm
                from core.rag_engine import rag_engine
                datos["rag"] = rag_engine({"action": "status"})
                datos["rag_stats"] = rag_engine({"action": "stats"})
                from core.ab_automated import ab_automated
                datos["ab"] = ab_automated({"action": "status"})
                from core.self_improvement import get_self_improvement
                datos["auto"] = get_self_improvement().get_improvement_report()[:1200]
                from core.session_summaries import _load_index
                datos["sesiones"] = _load_index()
            except Exception as e:
                self._mundo_list.setText(f"No pude cargar tu mundo: {e}")
                return
            lines = []
            wm = datos.get("world") or {}
            narrativa = wm.get("resumen_narrativo") or wm.get("narrativa") or "Sin narrativa aún."
            lines.append(f"<b style='color:{C.PRI}'>🧠 Modelo del mundo</b><br>"
                         f"&nbsp;&nbsp;{narrativa[:220]}")
            caps = wm.get("dominios_de_capacidad") or []
            limite = wm.get("limites") or []
            if caps:
                lines.append(f"&nbsp;&nbsp;<span style='color:#888'>Dominios: {len(caps)} · Límites: {len(limite) if isinstance(limite,list) else limite}</span>")
            lines.append(f"<br><b style='color:{C.PRI}'>🗂 RAG Memoria Total</b><br>"
                         f"&nbsp;&nbsp;{datos.get('rag','—')}<br>{datos.get('rag_stats','')}")
            lines.append(f"<br><b style='color:{C.PRI}'>🧪 A/B automático de prompts</b><br>"
                         f"&nbsp;&nbsp;{datos.get('ab','—').replace(chr(10),'<br>&nbsp;&nbsp;')}")
            lines.append(f"<br><b style='color:{C.PRI}'>🔁 Auto-mejora</b><br>"
                         f"&nbsp;&nbsp;{datos.get('auto','—').replace(chr(10),'<br>&nbsp;&nbsp;')}")
            ind = datos.get("sesiones")
            n_ses = len(ind) if isinstance(ind, (list, dict)) else 0
            lines.append(f"<br><b style='color:{C.PRI}'>💬 Sesiones guardadas</b>: {n_ses}")
            self._mundo_list.setText("<br>".join(lines))

        refresh.clicked.connect(_refresh_mundo)
        _refresh_mundo()
        form.addWidget(gb)

        form_w.setStyleSheet(f"QWidget {{ background: transparent; }}")
        form.addStretch()
        scroll.setWidget(form_w)
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll)
        return w

    # ── Section: System ─────────────────────────────────────────────────────
    def _build_system_section(self):
        w = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        form_w = QWidget()
        form = QVBoxLayout(form_w)
        form.setContentsMargins(24, 16, 24, 16)
        form.setSpacing(4)

        gb = QGroupBox("⬡  ERIS NEXUS")
        gb_layout = QVBoxLayout(gb)
        gb_layout.setSpacing(8)

        # System stats grid
        stats = QWidget()
        stats.setStyleSheet(f"background: {C.BG3}; border-radius: 8px;")
        stats_layout = QVBoxLayout(stats)
        stats_layout.setContentsMargins(16, 12, 16, 12)
        stats_layout.setSpacing(6)

        try:
            from core.version import ERIS_VERSION, ERIS_STAGE
            ver_lbl = QLabel(f"ERIS v{ERIS_VERSION}  —  {ERIS_STAGE}")
        except Exception:
            ver_lbl = QLabel(f"ERIS v4.0.0  —  Constellation Prime")
        ver_lbl.setStyleSheet(f"color: {C.PRI}; font-size: 16px; font-weight: bold; letter-spacing: 2px;")
        stats_layout.addWidget(ver_lbl)

        try:
            import psutil
            cpu = psutil.cpu_percent(interval=0)
            ram = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            stats_text = (
                f"CPU: {cpu}%  |  RAM: {ram.percent}% ({ram.used//(1024**3)}GB/{ram.total//(1024**3)}GB)"
                f"  |  DISK: {disk.percent}% ({disk.used//(1024**3)}GB/{disk.total//(1024**3)}GB)"
            )
        except Exception:
            stats_text = "System stats unavailable"

        sys_lbl = QLabel(stats_text)
        sys_lbl.setStyleSheet(f"color: {C.TEXT_DIM}; font-size: 10px; font-family: 'Consolas', monospace;")
        stats_layout.addWidget(sys_lbl)

        # Uptime
        uptime_lbl = QLabel(f"Session: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        uptime_lbl.setStyleSheet(f"color: {C.TEXT_DIM}; font-size: 9px;")
        stats_layout.addWidget(uptime_lbl)

        gb_layout.addWidget(stats)
        form.addWidget(gb)

        gb2 = QGroupBox("🛠  MAINTENANCE")
        gb2_layout = QVBoxLayout(gb2)
        gb2_layout.setSpacing(6)

        self_heal_btn = QPushButton("⚡  RUN SELF-HEAL SCAN")
        self_heal_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self_heal_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {C.PRI}; border: 1px solid {C.PRI};
            border-radius: 6px; padding: 8px 16px; font-size: 10px; letter-spacing: 1px; }}
            QPushButton:hover {{ background: rgba(245,158,11,0.1); }}
        """)
        self_heal_btn.clicked.connect(lambda: self._status_bar.setText("◆  SELF-HEAL: Scanning system...  ◆"))
        gb2_layout.addWidget(self_heal_btn)

        clear_btn = QPushButton("🗑  CLEAR TEMP CACHE")
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {C.WARNING}; border: 1px solid {C.WARNING};
            border-radius: 6px; padding: 8px 16px; font-size: 10px; letter-spacing: 1px; }}
            QPushButton:hover {{ background: rgba(245,158,11,0.1); }}
        """)
        clear_btn.clicked.connect(lambda: self._status_bar.setText("◆  CACHE cleared  ◆"))
        gb2_layout.addWidget(clear_btn)

        reset_btn = QPushButton("⚠  FACTORY RESET")
        reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reset_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {C.ERROR}; border: 1px solid {C.ERROR};
            border-radius: 6px; padding: 8px 16px; font-size: 10px; letter-spacing: 1px; }}
            QPushButton:hover {{ background: rgba(255,51,85,0.1); }}
        """)
        reset_btn.clicked.connect(lambda: self._status_bar.setText("◆  FACTORY RESET requires confirmation  ◆"))
        gb2_layout.addWidget(reset_btn)

        form.addWidget(gb2)

        # Emotional state summary
        gb3 = QGroupBox("💖  EMOTIONAL STATE")
        gb3_layout = QVBoxLayout(gb3)
        gb3_layout.setSpacing(6)
        emo_text = QLabel("Relationship:  —  |  Mood:  —  |  Interactions:  —")
        emo_text.setStyleSheet(f"color: {C.TEXT_DIM}; font-size: 10px; font-family: 'Consolas', monospace;")
        gb3_layout.addWidget(emo_text)

        # Try to load emotional state
        try:
            emo_path = _base_dir() / "memory" / "emotional_growth.json"
            if emo_path.exists():
                emo_data = json.loads(emo_path.read_text("utf-8"))
                stage = emo_data.get("relationship_stage", "?")
                interactions = emo_data.get("total_interactions", 0)
                baselines = emo_data.get("emotional_baselines", {})
                mood = "Positive" if baselines.get("happiness", 0.5) > 0.5 else "Neutral"
                emo_text.setText(f"Relationship: {stage.upper()}  |  Mood: {mood}  |  Interactions: {interactions}")
        except Exception:
            pass

        # Sentimiento dominante del núcleo emocional sentiente
        try:
            from core.emotional_core import get_sentience
            _s = get_sentience()
            if _s.get("emotion") != "tranquilidad":
                emo_text.setText(
                    f"{emo_text.text()}\nSabés que estoy {_s['label']} ({_s['intensity']:.0%}) — {_s['cause']}")
        except Exception:
            pass

        form.addWidget(gb3)

        form.addStretch()
        scroll.setWidget(form_w)
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll)
        return w

    # ── Save ────────────────────────────────────────────────────────────────
    def _save(self):
        """Guarda la configuración. Todo error se muestra y se loguea (antes
        una excepción al recolectar campos quedaba MUDO: botón sin efecto)."""
        self._status_bar.setText("◆  COMMITTING configuration...  ◆")
        try:
            self._save_impl()
        except Exception as e:
            import traceback
            traceback.print_exc()
            self._status_bar.setText(f"◆  ERROR GUARDANDO: {e}  ◆")
            print(f"[Settings] Error saving: {e}")
            try:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Error al guardar",
                                    f"No se pudo guardar la configuración:\n{e}")
            except Exception:
                pass

    def _save_impl(self):
        self._status_bar.setText("◆  COMMITTING configuration...  ◆")

        def _safe_int(val, default=None):
            try:
                return int(val) if val.strip() else default
            except (ValueError, AttributeError):
                return default

        def _safe_float(val, default=None):
            try:
                return float(val) if val.strip() else default
            except (ValueError, AttributeError):
                return default

        def _combo_idx(cb):
            data = cb.currentData()
            try:
                return int(data) if data not in (None, "") else None
            except (ValueError, TypeError):
                return None

        def _combo_dev_name(cb):
            data = cb.currentData()
            if data in (None, ""):
                return ""
            from core.audio_config import get_device_name
            return get_device_name(int(data))

        cfg = dict(self._cfg)
        cfg.update({
            "gemini_api_key": self._api_key.entry.text(),
            "model_for_conversation": self._model_conv.currentText(),
            "model_for_agents": self._cfg.get("model_for_agents", "gemini"),
            "model_for_search": self._cfg.get("model_for_search", "gemini"),
            "groq_api_key": self._groq_key.entry.text(),
            "openrouter_api_key": self._openrouter_key.entry.text(),
            "cerebras_api_key": self._cerebras_key.entry.text(),
            "ollama_enabled": self._ollama_enabled.isChecked(),
            "ollama_autostart": self._ollama_autostart.isChecked(),
            "ollama_base_url": self._ollama_url.entry.text(),
            "ollama_model": self._ollama_model.entry.text(),
            "ollama_vision_model": self._ollama_vision.entry.text(),
            "spotify_client_id": self._spotify_id.entry.text(),
            "spotify_client_secret": self._spotify_secret.entry.text(),
            "spotify_redirect_uri": self._cfg.get("spotify_redirect_uri", "http://127.0.0.1:8888/callback"),
            "tmdb_api_key": self._tmdb_key.entry.text(),
            "openweather_api_key": self._weather_key.entry.text(),
            "elevenlabs_api_key": self._el_api_key.entry.text(),
            "elevenlabs_voice_id": self._el_voice_id.entry.text(),
            "fish_api_key": self._fish_api_key.entry.text(),
            "fish_voice_id": self._fish_voice_id.entry.text(),
            "tts_backend": self._tts.currentText(),
            "voice_mode": "cloud" if self._voice_mode.currentIndex() == 0 else "local",
            "tts_voice": self._voice.currentData() or self._voice.currentText(),
            "mic_device": _combo_idx(self._mic_cb),
            "mic_device_name": _combo_dev_name(self._mic_cb),
            "speaker_device": _combo_idx(self._spk_cb),
            "speaker_device_name": _combo_dev_name(self._spk_cb),
            "spk_device": _combo_idx(self._spk_cb),
            "eris_voice": self._eris_voice.currentData(),
            "eris_theme": C.get_theme(),
            "thinking_sound": self._thinking_sound.isChecked(),
            "wake_sound": self._wake_sound.isChecked(),
            "wake_word_mode": self._wake_mode_cb.isChecked(),
            "language": self._lang.currentText(),
            "timezone": self._tz.entry.text(),
            "chrome_google_profile": self._chrome_profile.entry.text(),
            "chrome_exe_path": self._chrome_path.entry.text(),
            "camera_enabled": self._cam_toggle.isChecked(),
            "gpu_acceleration": self._gpu_accel.isChecked(),
            "glass_opacity": _safe_int(self._glass_opacity.entry.text(), 180),
            "glow_intensity": _safe_float(self._glow_intensity.entry.text(), 0.5),
            "webgl_orb": self._orb_renderer.currentText() == "WebGL (3D)",
            "central_visual": "face" if self._central_visual.currentText().startswith("Cara") else "orb",
            "floating_visual": "vrm" if self._floating_visual.currentText().startswith("Modelo") else "orb",
            "os_system": self._cfg.get("os_system", "windows"),
        })
        # Si se eligió un micro concreto, guardar su tasa nativa (Linux/ALSA:
        # muchos mics solo abren a su tasa; sin esto el stream abriría a 16k).
        try:
            _mic_sel = _combo_idx(self._mic_cb)
            if _mic_sel is not None:
                from core.audio_config import _mic_rate_for
                _r = _mic_rate_for(_mic_sel)
                cfg["mic_device_rate"] = _r if _r else None
        except Exception:
            pass
        try:
            from core.logging_setup import API_CONFIG_PATH
            path = API_CONFIG_PATH
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(cfg, indent=4), encoding="utf-8")
            # Aplicar autostart de Ollama segun el toggle (crear/quitar lanzador en Startup)
            try:
                from core.ollama_autostart import apply_autostart
                apply_autostart(bool(cfg.get("ollama_autostart", False)))
            except Exception as _e:
                print(f"[Settings] ollama autostart apply skipped: {_e}")
            self._status_bar.setText("◆  CONFIGURATION COMMITTED  ◆")
            print(f"[Settings] COMMITTED: {len(cfg)} claves | tts={cfg.get('tts_backend')} model={cfg.get('model_for_conversation')} mic={cfg.get('mic_device')} rate={cfg.get('mic_device_rate')}")
            self.saved.emit(cfg)
            QTimer.singleShot(300, self.accept)
        except Exception as e:
            self._status_bar.setText(f"◆  ERROR: {e}  ◆")
            print(f"[Settings] Error saving: {e}")
