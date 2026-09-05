# -*- coding: utf-8 -*-
"""setup_wizard.py — Ventana de bienvenida y configuracion inicial de ERIS.

Aparece en el primer arranque (o con el comando `eris --wizard`).
Muestra el nombre ERIS en grande, las API keys REQUERIDAS (obligatorias
para que ERIS funcionen de verdad) y las OPCIONALES (pueden quedar vacias
y ERIS arranca igual de normal). Los datos se guardan en
config/api_keys.json (UTF-8 sin BOM, mismo formato que el resto del codigo).

Uso:
    python setup_wizard.py                 # modo GUI
    python setup_wizard.py --check         # modo headless (validar estado)
    python setup_wizard.py --save g=VAL f=VAL   # escritura scriptable
"""
import json
import os
import shutil
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
API_CONFIG_PATH = BASE / "config" / "api_keys.json"

# (clave, etiqueta, url de donde sacarla)
REQUIRED_FIELDS = [
    ("gemini_api_key", "Clave de Gemini API", "https://aistudio.google.com/apikey"),
]

OPTIONAL_FIELDS = [
    ("fish_api_key", "Fish Audio (voz de Eris)", "https://app.fish.audio/"),
    ("elevenlabs_api_key", "ElevenLabs (TTS alternativo)", "https://elevenlabs.io/api-keys"),
    ("telegram_bot_token", "Telegram Bot Token (control remoto)", "https://t.me/BotFather"),
    ("spotify_client_id", "Spotify Client ID", "https://developer.spotify.com/dashboard"),
    ("spotify_client_secret", "Spotify Client Secret", ""),
    ("openweather_api_key", "OpenWeather (clima)", "https://home.openweathermap.org/api_keys"),
    ("openrouter_api_key", "OpenRouter (LLM alternativo)", "https://openrouter.ai/keys"),
    ("groq_api_key", "Groq (LLM alternativo)", "https://console.groq.com/keys"),
    ("cerebras_api_key", "Cerebras (LLM alternativo)", "https://cloud.cerebras.ai/"),
    ("context7_api_key", "Context7 (documentacion)", "https://context7.com/"),
    ("hibp_api_key", "HaveIBeenPwned (seguridad)", "https://haveibeenpwned.com/API/Key"),
]


def load_config() -> dict:
    if API_CONFIG_PATH.exists():
        try:
            raw = API_CONFIG_PATH.read_text(encoding="utf-8")
            if raw.startswith("\ufeff"):
                raw = raw.lstrip("\ufeff")
            data = json.loads(raw)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return {}


def save_config(cfg: dict) -> Path:
    API_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    API_CONFIG_PATH.write_text(
        json.dumps(cfg, ensure_ascii=False, indent=4) + "\n",
        encoding="utf-8",
    )
    return API_CONFIG_PATH


def merge_and_save(filled: dict) -> Path:
    """Guarda solo lo que no este vacio, conservando lo existente."""
    cfg = load_config()
    for key, value in filled.items():
        value = (value or "").strip()
        if value:
            cfg[key] = value
    return save_config(cfg)


def chat_ready() -> bool:
    """Puede chatear? La key de Gemini alcanza (con internet). Ollama solo
    sirve si ademas hay un modelo descargado (el modelo NO se descarga aca).
    """
    cfg = load_config()
    if cfg.get("gemini_api_key", "").strip():
        return True
    if shutil.which("ollama"):
        try:
            out = os.popen("ollama list 2>/dev/null").read().strip()
            if out:
                return True
        except Exception:
            pass
    return False


def needs_setup() -> bool:
    cfg = load_config()
    return not cfg.get("gemini_api_key", "").strip()


# ── Modo headless ──────────────────────────────────────────────────────────
def _cmdline_check() -> int:
    cfg = load_config()
    print("ERIS")
    print("Estado de la configuracion")
    print("--------------------------")
    if not API_CONFIG_PATH.exists():
        print("config/api_keys.json  ->  AUN NO EXISTE")
    for key, label, _url in REQUIRED_FIELDS:
        print(f"[REQUERIDA] {label} ({key}): {'OK' if cfg.get(key, '').strip() else 'FALTA'}")
    for key, label, _url in OPTIONAL_FIELDS:
        val = cfg.get(key, "").strip()
        print(f"[opcional]  {label} ({key}): {'OK' if val else '(vacia)'}")
    print("chat_ready:", chat_ready())
    if not chat_ready():
        print("AVISO: para chatear hace falta la key de Gemini (Eris con internet).")
        print("       Ollama local es OPCIONAL y ademas hay que bajarle un modelo aparte.")
    print("Resumen:", "LISTA PARA INICIAR" if chat_ready() else "FALTA LA KEY DE GEMINI (u Ollama)")
    return 0


def _cmdline_save(pairs: list) -> int:
    filled = {}
    for item in pairs:
        if "=" in item:
            key, value = item.split("=", 1)
            filled[key] = value
    if filled:
        merge_and_save(filled)
        print("Guardado en", API_CONFIG_PATH, "->", sorted(load_config().keys()))
    return 0


# ── Modo GUI ───────────────────────────────────────────────────────────────
def _build_widgets(parent, launch_after: bool = True):
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QDesktopServices, QFont
    from PyQt6.QtWidgets import (
        QDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
        QScrollArea, QVBoxLayout, QWidget, QMessageBox,
    )
    from PyQt6.QtCore import QUrl

    dialog = QDialog(parent)
    dialog.setWindowTitle("Instalacion de ERIS")
    dialog.resize(560, 640)

    root = QVBoxLayout(dialog)
    root.setContentsMargins(24, 20, 24, 20)
    root.setSpacing(10)

    # ── Titulo grande ──
    title = QLabel("ERIS")
    title.setAlignment(Qt.AlignmentFlag.AlignCenter)
    title.setStyleSheet("font-size: 44px; font-weight: 800; letter-spacing: 8px; color: #3b82f6;")
    root.addWidget(title)

    subtitle = QLabel(
        "Asistente personal de codigo, control de sistema y memoria viva.\n"
        "Completa tus claves para empezar. Las opcionales pueden quedarse vacias."
    )
    subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
    subtitle.setStyleSheet("font-size: 13px; color: #555;")
    subtitle.setWordWrap(True)
    root.addWidget(subtitle)

    # ── Scroll con el formulario ──
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QScrollArea.Shape.NoFrame)
    form_host = QWidget()
    form = QVBoxLayout(form_host)
    form.setSpacing(8)
    scroll.setWidget(form_host)

    entries = {}

    def add_section(title_text, color):
        sec = QLabel(title_text)
        sec.setStyleSheet(f"font-size: 15px; font-weight: 700; margin-top: 10px; color: {color};")
        form.addWidget(sec)

    def add_field(key, label, url, required):
        row = QFormLayout()
        row.setHorizontalSpacing(10)
        lbl = QLabel(label)
        lbl.setStyleSheet("font-size: 12px; font-weight: 600;")
        inp = QLineEdit()
        if not required:
            inp.setPlaceholderText("opcional - puede quedar vacio")
        row.addRow(lbl, inp)
        if url:
            link = QLabel(f'<a href="{url}">obtener clave</a>')
            link.setStyleSheet("font-size: 10px; color: #3b82f6;")
            link.setOpenExternalLinks(True)
            row.addRow("", link)
        form.addLayout(row)
        entries[key] = inp

    add_section("REQUERIDAS", "#dc2626")
    add_field("gemini_api_key", "Clave de Gemini API", REQUIRED_FIELDS[0][2], True)

    add_section("OPCIONALES", "#16a34a")
    for key, label, url in OPTIONAL_FIELDS:
        add_field(key, label, url, False)

    # ── Estado Ollama ──
    ollama_here = shutil.which("ollama") is not None
    ollama_lbl = QLabel(
        "Ollama (OPCIONAL, chat sin internet): motor detectado" if ollama_here
        else "Ollama (OPCIONAL, chat sin internet): motor no instalado — "
              "basta con la key de Gemini; los modelos van aparte"
    )
    ollama_lbl.setStyleSheet("font-size: 11px; color: #777; margin-top: 6px;")
    form.addWidget(ollama_lbl)

    # ── Botones ──
    def on_start():
        gemini_filled = bool(
            entries["gemini_api_key"].text().strip()
            or (load_config().get("gemini_api_key", "") or "").strip()
        )
        if not gemini_filled and not chat_ready():
            QMessageBox.warning(
                dialog, "Falta algo",
                "ERIS necesita la clave de Gemini para chatear por internet.\n\n"
                "Si preferis 100% local es aparte: instalar Ollama y descargar un "
                "modelo (ollama pull qwen3:8b). No es necesario.",
            )
            return
        merge_and_save({k: w.text() for k, w in entries.items()})
        if launch_after:
            QMessageBox.information(
                dialog, "ERIS",
                "Configuracion guardada. Iniciando ERIS...",
            )
            _launch_main()
        dialog.accept()

    btn_start = QPushButton("Iniciar ERIS")
    btn_start.setStyleSheet(
        "font-size: 16px; font-weight: 700; padding: 12px; background: #3b82f6; color: white; border-radius: 8px;"
    )
    btn_start.clicked.connect(on_start)

    btn_skip = QPushButton("Ignorar y arrancar igual")
    btn_skip.setStyleSheet("font-size: 11px; color: #888; background: transparent; border: none;")
    btn_skip.clicked.connect(
        lambda: (merge_and_save({k: w.text() for k, w in entries.items()}),
                 (_launch_main() if launch_after else None),
                 dialog.accept())
    )

    root.addWidget(scroll)
    root.addWidget(btn_start)
    root.addWidget(btn_skip)
    return dialog, btn_start


def _launch_main():
    """Lanza main.py en un proceso separado y cierra el wizard."""
    import subprocess
    py = Path(sys.executable)
    cmd = [str(py), str(BASE / "main.py")]
    try:
        subprocess.Popen(cmd, cwd=str(BASE))
    except Exception as e:
        QMessageBox.critical(None, "ERIS", f"No se pudo iniciar ERIS:\n{e}")


def run_setup(launch_after: bool = True) -> int:
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    dialog, _ = _build_widgets(None, launch_after=launch_after)
    dialog.show()
    app.exec()
    return 0


if __name__ == "__main__":
    if "--check" in sys.argv:
        sys.exit(_cmdline_check())
    if "--save" in sys.argv:
        idx = sys.argv.index("--save")
        sys.exit(_cmdline_save(sys.argv[idx + 1:]))
    sys.exit(run_setup())