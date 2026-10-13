"""
tests/test_cli_intent.py
────────────────────────
Fase 3.1b: la CLI enchufa el modo de `core/intent_reader` al turno.

- `_turn_intent` clasifica el texto y devuelve (etiqueta, instrucción).
- `_intent_system` inyecta la instrucción en el system SOLO durante el turno
  y lo restaura siempre (incluso si el turno se cancela o falla).
- Charla sin señales no inyecta nada (no mete ruido).
"""

from __future__ import annotations

import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

import eris_cli  # noqa: E402


def _ctx(**kw):
    base = {"convo_ctx": [], "session_summary": "", "project_root": None,
            "active_file": None, "foreground_app": None, "identity": {},
            "read_only": False}
    base.update(kw)
    return base


class _DummyChat:
    def __init__(self, with_compact=True):
        self._system = "SYS"
        if with_compact:
            self._system_compact = "COMPACT"


# ── _turn_intent ──

def test_plain_chat_has_no_intent():
    tag, instr = eris_cli._turn_intent("hola, ¿cómo estás?", _ctx())
    assert tag == ""
    assert instr == ""


def test_strong_auto_is_tagged_autonomo():
    tag, instr = eris_cli._turn_intent("arreglalo", _ctx())
    assert tag == "AUTONOMO"
    assert "Modo AUTONOMO" in instr


def test_line_reference_is_editar():
    tag, instr = eris_cli._turn_intent("está en la línea 42, cambiala por return True", _ctx())
    assert tag == "EDITAR"
    assert "Modo EDITAR" in instr


def test_explicit_investigar_is_injected_but_not_tagged():
    # No es "accionable" (no etiqueta), pero SÍ se inyecta el "no edites".
    tag, instr = eris_cli._turn_intent("investigá por qué falla el login", _ctx())
    assert tag == ""
    assert "NO edites" in instr


def test_turn_intent_never_raises():
    assert eris_cli._turn_intent(None, None) == ("", "")
    assert eris_cli._turn_intent("", object()) == ("", "")


# ── _intent_system ──

def test_injects_and_restores_system():
    chat = _DummyChat()
    with eris_cli._intent_system(chat, "arreglalo", _ctx()) as tag:
        assert tag == "AUTONOMO"
        assert chat._system.startswith("SYS")
        assert "Modo AUTONOMO" in chat._system
        assert "Modo AUTONOMO" in chat._system_compact
    # restaurado exactamente
    assert chat._system == "SYS"
    assert chat._system_compact == "COMPACT"


def test_restores_system_even_on_exception():
    chat = _DummyChat()
    try:
        with eris_cli._intent_system(chat, "arreglalo", _ctx()):
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    assert chat._system == "SYS"
    assert chat._system_compact == "COMPACT"


def test_chat_turn_does_not_touch_system():
    chat = _DummyChat()
    with eris_cli._intent_system(chat, "hola, ¿cómo estás?", _ctx()) as tag:
        assert tag == ""
        assert chat._system == "SYS"
        assert chat._system_compact == "COMPACT"


def test_chat_without_compact_attr_still_works():
    chat = _DummyChat(with_compact=False)
    with eris_cli._intent_system(chat, "arreglalo", _ctx()) as tag:
        assert tag == "AUTONOMO"
        assert "Modo AUTONOMO" in chat._system
    assert chat._system == "SYS"
