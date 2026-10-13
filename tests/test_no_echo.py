"""
tests/test_no_echo.py
─────────────────────
Fase 1.3: fin del eco en `_run_agent_handoff`.

El bug: el resultado de un fragmento se le inyectaba a Gemini Live (`session.
send_realtime_input`), que lo dice por voz, y ADEMÁS se llamaba a `_announce`,
produciendo una SEGUNDA voz sobre la misma respuesta. La regla: si hay Live,
habla Live; `_announce` queda solo como respaldo local (texto/offline/CLI).

Se construye una instancia liviana de `ErisLive` (sin `__init__`, sin GUI) y se
stubea todo lo que toca borde (ui, session, loop, announce).
"""

from __future__ import annotations

import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))


def _load_main():
    """Import perezoso: `main.py` llama load_custom_tools()/install_custom_tools()
    a nivel de módulo, así que importarlo durante la COLECCIÓN de pytest
    contamina el registro de tools y rompe el chequeo de sync de otros tests.
    Se importa acá, ya en tiempo de ejecución."""
    import importlib
    return importlib.import_module("main")


class _FakeUI:
    def __init__(self):
        self.muted = False
        self.logs = []
        self.emotions = []
        self.states = []

    def write_log(self, msg):
        self.logs.append(msg)

    def express_emotion(self, *a, **k):
        self.emotions.append(a)

    def set_state(self, s):
        self.states.append(s)


class _FakeSession:
    """send_realtime_input como función normal: evita crear corrutinas colgadas."""

    def __init__(self):
        self.sent = []

    def send_realtime_input(self, **kwargs):
        self.sent.append(kwargs.get("text", ""))


def _bare(announce_calls):
    eris_main = _load_main()
    obj = object.__new__(eris_main.ErisLive)
    obj.ui = _FakeUI()
    obj._announce = lambda text, *a, **k: announce_calls.append(text)
    obj._auto_cont_on = False
    obj._gemini_text_chat = None
    obj._loop = None
    obj.session = None
    return obj


def _handler(text, player=None):
    return "El clima en Buenos Aires es 20 grados."


def test_no_announce_when_live_will_speak():
    calls = []
    obj = _bare(calls)
    obj.session = _FakeSession()
    obj._loop = object()  # "hay loop" → Live activo (aunque el scheduling falle, es lo correcto)

    obj._run_agent_handoff("web", _handler, "¿qué clima hace?")

    assert calls == [], f"_announce no debe sonar con Live activo: {calls}"
    assert obj.ui.emotions, "igual se muestra la emoción en la UI"
    assert obj.session.sent, "el resultado SÍ se le inyecta a Live"


def test_announce_as_fallback_without_live():
    calls = []
    obj = _bare(calls)
    obj.session = None
    obj._loop = None

    obj._run_agent_handoff("web", _handler, "¿qué clima hace?")

    assert calls == ["El clima en Buenos Aires es 20 grados."], f"sin Live debe anunciar local: {calls}"
    assert obj.ui.states and obj.ui.states[-1] == "LISTENING"
