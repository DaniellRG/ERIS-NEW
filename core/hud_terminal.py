"""
core/hud_terminal.py — HUD estilo terminal para ERIS (estilo "Jarvis OS").

Ventana flotante semitransparente (siempre encima) que muestra en vivo:
  - Vitales del sistema (CPU, RAM, disco, red, batería)
  - Agenda del día (tareas y recordatorios de la DB de ERIS)
  - Estado del audio (micro/altavoz, modo voz local, push-to-talk)
  - Últimos comandos / logs de la sesión

Se ejecuta en su propio hilo con su propia QApplication para no interferir
con la UI principal (orbe/caras) de ERIS.
"""
from __future__ import annotations

import json
import sys
import threading
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

_HUD_WINDOW = None
_HUD_THREAD = None
_HUD_LOCK = threading.Lock()
_STOP = threading.Event()


def _load_cfg() -> dict:
    try:
        return json.loads((BASE_DIR / "config" / "api_keys.json").read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def _system_vitals() -> str:
    lines = []
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=0.3)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("C:\\")
        net = psutil.net_io_counters()
        lines.append(f"  CPU  : {cpu:5.1f}%   Núcleos: {psutil.cpu_count(logical=False)}")
        lines.append(f"  RAM  : {mem.used/2**30:.1f} / {mem.total/2**30:.1f} GB  ({mem.percent:.0f}%)")
        lines.append(f"  DISCO: {disk.used/2**30:.0f} / {disk.total/2**30:.0f} GB  ({disk.percent:.0f}%)")
        lines.append(f"  RED  : ↓{net.bytes_recv/2**20:.1f}MB  ↑{net.bytes_sent/2**20:.1f}MB")
        try:
            bat = psutil.sensors_battery()
            if bat:
                lines.append(f"  BATER: {bat.percent:.0f}%  {'cargando' if bat.power_plugged else 'en batería'}")
        except Exception:
            pass
    except Exception as e:
        lines.append(f"  vitals error: {e}")
    return "\n".join(lines)


def _agenda() -> str:
    lines = []
    try:
        from actions.db_tasks import db_tasks
        res = db_tasks({"action": "list"})
        text = str(res)
        tasks = [t for t in text.splitlines() if t.strip()][:6]
        if tasks:
            lines.append("  ── Agenda ──")
            lines.extend("  " + t for t in tasks)
        else:
            lines.append("  Agenda: sin tareas pendientes.")
    except Exception as e:
        lines.append(f"  agenda error: {e}")
    return "\n".join(lines)


def _audio_status() -> str:
    lines = []
    try:
        import sounddevice as sd
        from core.audio_config import get_device_name
        try:
            in_dev = sd.query_devices(kind="input")
            out_dev = sd.query_devices(kind="output")
            in_name = in_dev.get("name", "?") if isinstance(in_dev, dict) else "?"
            out_name = out_dev.get("name", "?") if isinstance(out_dev, dict) else "?"
        except Exception:
            in_name, out_name = "auto", "auto"
        cfg = _load_cfg()
        vmode = cfg.get("voice_mode", "cloud")
        tts = cfg.get("tts_backend", "gemini")
        lines.append(f"  Voz   : {'100% local' if vmode == 'local' else 'cloud (Gemini)'}  TTS: {tts}")
        lines.append(f"  MIC   : {in_name}")
        lines.append(f"  SALIDA: {out_name}")
        lines.append(f"  PTT   : mantener ESPACIO para hablar")
    except Exception as e:
        lines.append(f"  audio error: {e}")
    return "\n".join(lines)


def _commands_log() -> str:
    lines = ["  ── Últimos comandos ──"]
    try:
        import actions.eris_db as edb
        if hasattr(edb, "get_recent_commands"):
            data = edb.get_recent_commands(5) or []
            for c in data:
                lines.append(f"  > {str(c)[:70]}")
        else:
            lines.append("  (sin historial de comandos)")
    except Exception:
        lines.append("  (sin historial de comandos)")
    return "\n".join(lines)


def _render() -> str:
    now = time.strftime("%d/%m/%Y %H:%M:%S")
    return (
        "╔══════════════════════════════════════════════════╗\n"
        f"║  ERIS • HUD en vivo                    {now}  ║\n"
        "╠══════════════════════════════════════════════════╣\n"
        + _system_vitals()
        + "\n"
        + _agenda()
        + "\n"
        + _audio_status()
        + "\n"
        + _commands_log()
        + "\n"
        "╚══════════════════════════════════════════════════╝"
    )


def _run_hud_window():
    try:
        from PyQt6.QtCore import Qt, QTimer
        from PyQt6.QtGui import QColor, QFont
        from PyQt6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

        app = QApplication.instance() or QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)

        win = QWidget()
        win.setWindowTitle("ERIS HUD")
        win.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        win.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        win.setStyleSheet("background: rgba(0,0,0,190); border-radius: 8px;")
        win.setFixedWidth(560)

        label = QLabel()
        label.setFont(QFont("Consolas", 10))
        label.setStyleSheet("color: #3fd68c; padding: 10px;")
        label.setTextFormat(Qt.TextFormat.PlainText)
        layout = QVBoxLayout(win)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(label)
        win.show()

        def _tick():
            label.setText(_render())
            win.adjustSize()

        _tick()
        timer = QTimer()
        timer.timeout.connect(_tick)
        timer.start(2000)

        while not _STOP.is_set():
            app.processEvents()
            time.sleep(0.1)
        win.close()
    except Exception as e:
        print(f"[HUD] error: {e}")


def start_hud() -> bool:
    """Arranca el HUD en su propio hilo. Devuelve True si ya estaba/arrancó."""
    global _HUD_WINDOW, _HUD_THREAD
    with _HUD_LOCK:
        if _HUD_WINDOW and _HUD_WINDOW.is_alive():
            return True
        _STOP.clear()
        _HUD_THREAD = threading.Thread(target=_run_hud_window, daemon=True)
        _HUD_THREAD.start()
        _HUD_WINDOW = _HUD_THREAD
        return True


def stop_hud() -> bool:
    """Detiene el HUD. Devuelve True si había un HUD corriendo."""
    global _HUD_WINDOW
    was_running = bool(_HUD_WINDOW and _HUD_WINDOW.is_alive())
    _STOP.set()
    _HUD_WINDOW = None
    return was_running


def hud_terminal(parameters: dict = None, player=None) -> str:
    """Tool: HUD estilo terminal (vitales, agenda, audio, comandos) en pantalla."""
    params = parameters or {}
    action = str(params.get("action") or "toggle").lower().strip()
    if action in ("stop", "off", "cerrar", "close"):
        stop_hud()
        return "HUD cerrado."
    if action in ("start", "on", "abrir", "open"):
        start_hud()
        return "HUD abierto (siempre encima). Actualiza cada 2s."
    if action in ("status", "estado"):
        return ("HUD activo." if (_HUD_WINDOW and _HUD_WINDOW.is_alive()) else "HUD inactivo.")
    if action in ("info", "render"):
        return _render()
    # default: toggle
    if _HUD_WINDOW and _HUD_WINDOW.is_alive():
        stop_hud()
        return "HUD cerrado."
    start_hud()
    return "HUD abierto (siempre encima). Actualiza cada 2s."
