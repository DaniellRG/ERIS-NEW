"""
tests/test_verify_before_done.py
────────────────────────────────
Fase 3.4: no digas "listo" sin verificar. El simétrico de "nunca digas no
puedo sin intentar 3 formas".

`core/truth_audit.audit_completion(text, tool_names)` marca cuando la respuesta
afirma que quedó listo/terminado pero en el turno se cambió código/archivos y NO
se corrió ninguna verificación (tests, py_compile, ruff, mission verify, releer).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parent.parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from core import truth_audit as ta  # noqa: E402


@pytest.fixture(autouse=True)
def _clean_state():
    with ta._LOCK:
        ta._TOOL_LOG.clear()
        ta._FLAGS.clear()
    yield
    with ta._LOCK:
        ta._TOOL_LOG.clear()
        ta._FLAGS.clear()


# ── audit_completion (puro) ──

def test_claim_with_mutation_without_verify_flags():
    flags = ta.audit_completion("Listo, quedó arreglado", tool_names=["file_api"])
    assert len(flags) == 1
    assert "Verificá" in flags[0]


def test_claim_with_verify_does_not_flag():
    flags = ta.audit_completion("Listo, quedó arreglado",
                                tool_names=["file_api", "py_compile"])
    assert flags == []
    flags = ta.audit_completion("Terminé", tool_names=["mission", "read_file"])
    assert flags == []


def test_claim_without_mutation_does_not_flag():
    # Solo charla / música: no cambió nada, no hay nada que verificar.
    assert ta.audit_completion("Listo!", tool_names=["music"]) == []
    assert ta.audit_completion("Quedó listo", tool_names=[]) == []


def test_no_claim_does_not_flag():
    assert ta.audit_completion("Cambié el archivo", tool_names=["file_api"]) == []


def test_none_and_garbage_never_raise():
    assert ta.audit_completion(None) == []
    assert ta.audit_completion("", tool_names=None) == []
    assert ta.audit_completion(123) == []


# ── audit_turn (integrado con el registro real) ──

def test_audit_turn_flags_completion_without_verify():
    ta.record_tool("file_api", "ok", "Edit aplicado: /x/a.py · a.py: +1 línea(s) [2]")
    flags = ta.audit_turn("Todo listo, quedó andando")
    assert flags and "Verificá" in flags[0]
    # queda inyectable en el próximo turno
    assert "[VERIFICACIÓN" in ta.evidence_block()


def test_audit_turn_no_flag_when_verified():
    ta.record_tool("file_api", "ok", "Edit aplicado")
    ta.record_tool("py_compile", "ok", "COMPILE OK")
    assert ta.audit_turn("Listo, quedó andando") == []


def test_audit_turn_no_flag_on_honest_failure():
    # Admite el fallo ("falló") → no la increpamos (negador).
    ta.record_tool("file_api", "ok", "Edit aplicado")
    assert ta.audit_turn("Terminé el edit pero falló al correr") == []


def test_audit_turn_contradiction_still_works():
    # Regresión: afirmó un éxito de un dominio que falló de verdad.
    ta.record_tool("terminal_agent", "error", "command not found")
    flags = ta.audit_turn("Ejecuté el comando y salió todo bien")
    assert flags and "Aseguraste un éxito" in flags[0]  # frase de contradicción
    assert "terminal_agent" in flags[0]
