"""
tests/test_intent_gui.py
────────────────────────
Fase 3.1b (GUI): `main.py` enchufa el modo del turno al chat.

`main.py` no se puede importar en pytest (crea QApplication y carga/instala
custom tools a nivel de módulo → contamina el registry). Por eso la LÓGICA se
prueba en `test_intent_reader.py` (helpers compartidos) y acá se verifica, sobre
el fuente, que el enganche sigue presente: si alguien lo borra, esto falla.

Los tres puntos del enganche:
  1. `_on_text_command` clasifica el turno y guarda `_turn_prefix`.
  2. El envío al Live antepone el prefijo (`send_realtime_input(text=_live_text)`).
  3. El fallback `GeminiTextChat` inyecta el modo con `mode_system`.
"""

from __future__ import annotations

from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
MAIN = BASE / "main.py"


def _src() -> str:
    return MAIN.read_text(encoding="utf-8")


def test_gui_imports_intent_helpers():
    src = _src()
    assert "from core.intent_reader import actionable_mode" in src
    assert "self._turn_mode" in src
    assert "self._turn_prefix" in src


def test_gui_computes_prefix_in_text_command():
    src = _src()
    # El prefijo se arma dentro de _on_text_command a partir de los helpers.
    assert "self._turn_prefix = _turn_prefix(text, self._shared)" in src


def test_live_send_uses_turn_prefix():
    src = _src()
    assert "_live_text = (self._turn_prefix + text) if self._turn_prefix else text" in src
    assert "self.session.send_realtime_input(text=_live_text)" in src


def test_text_chat_fallback_uses_mode_system():
    src = _src()
    assert "from core.intent_reader import mode_system as _mode_system" in src
    assert "with _cm:" in src
    assert "self._gemini_text_chat.chat(text)" in src


def test_main_still_compiles():
    import py_compile

    py_compile.compile(str(MAIN), doraise=True)
