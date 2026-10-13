"""
tests/test_intent_reader.py
───────────────────────────
Fase 3.1: `core/intent_reader.py` clasifica el pedido en
INVESTIGAR / EDITAR / AUTONOMO combinando texto + SharedContext.

El caso rector del diseño: "Hay un error que no logro solucionar" es AUTONOMO
con un editor abierto y INVESTIGAR en un chat vacío. El contexto, no el verbo.
"""

from __future__ import annotations

import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from core import intent_reader as ir  # noqa: E402


def _ctx(**kw):
    """Dict con la forma de SharedContext.as_dict()."""
    base = {"convo_ctx": [], "session_summary": "", "project_root": None,
            "active_file": None, "foreground_app": None, "identity": {}, "read_only": False}
    base.update(kw)
    return base


def test_spec_example_error_with_editor_is_autonomo():
    res = ir.classify("Hay un error que no logro solucionar",
                      _ctx(foreground_app="code", active_file="/x/main.py"))
    assert res["mode"] == ir.AUTONOMO
    assert res["in_editor"] is True


def test_spec_example_same_text_empty_chat_is_investigar():
    res = ir.classify("Hay un error que no logro solucionar", _ctx())
    assert res["mode"] == ir.INVESTIGAR


def test_strong_auto_needs_no_context():
    assert ir.classify("arreglalo", _ctx())["mode"] == ir.AUTONOMO
    assert ir.classify("hacelo funcionar", _ctx())["mode"] == ir.AUTONOMO
    assert ir.classify("encargate vos", _ctx())["mode"] == ir.AUTONOMO


def test_explicit_investigar():
    assert ir.classify("investigá por qué falla el login", _ctx(foreground_app="code"))["mode"] == ir.INVESTIGAR
    assert ir.classify("sin tocar nada, explicame qué está pasando", _ctx())["mode"] == ir.INVESTIGAR


def test_editar_by_line_reference():
    res = ir.classify("está en la línea 42, cambiala por return True",
                      _ctx(foreground_app="code", active_file="/x/a.py"))
    assert res["mode"] == ir.EDITAR


def test_read_only_always_investigar():
    res = ir.classify("arreglalo ya", _ctx(foreground_app="code", read_only=True))
    assert res["mode"] == ir.INVESTIGAR
    assert res["read_only"] is True


def test_accepts_shared_context_object():
    from core import shared_context as sc
    sc.reset_shared_context()
    ctx = sc.get_shared_context()
    ctx.set_foreground_app("code")
    ctx.set_active_file("/x/a.py")
    assert ir.classify("hay un bug, no funciona", ctx)["mode"] == ir.AUTONOMO


def test_never_raises_on_garbage():
    assert ir.classify(None)["mode"] == ir.INVESTIGAR
    assert ir.classify("", object())["mode"] == ir.INVESTIGAR
    assert ir.classify("x", {"read_only": "no"})["mode"] in (ir.INVESTIGAR, ir.EDITAR, ir.AUTONOMO)


def test_instruction_block_per_mode():
    for mode in (ir.INVESTIGAR, ir.EDITAR, ir.AUTONOMO):
        assert ir.instruction(mode)
    assert "NO edites" in ir.instruction(ir.INVESTIGAR)
    assert "backup" in ir.instruction(ir.EDITAR)
    assert "verific" in ir.instruction(ir.AUTONOMO)


# ── Fase 3.1b (GUI): helpers compartidos con la CLI ──

def test_actionable_mode_quiet_chat_is_empty():
    # Charla y "sin señales" no son accionables: "" (cero ruido en el prompt).
    assert ir.actionable_mode("hola, ¿cómo estás?", _ctx()) == ""
    # Un problema SIN contexto es INVESTIGAR (no "quiet"): inyecta el "no edites".
    assert ir.actionable_mode("Hay un error que no logro solucionar", _ctx()) == ir.INVESTIGAR


def test_actionable_mode_strong_auto():
    assert ir.actionable_mode("arreglalo", _ctx()) == ir.AUTONOMO
    assert ir.actionable_mode("hacelo funcionar", _ctx()) == ir.AUTONOMO


def test_actionable_mode_explicit_investigar_is_returned():
    # INVESTIGAR explícito SÍ es accionable (inyecta el "no edites"), pero la CLI
    # no lo etiqueta como edición.
    assert ir.actionable_mode("investigá por qué falla el login", _ctx()) == ir.INVESTIGAR


def test_actionable_mode_editar():
    assert ir.actionable_mode(
        "está en la línea 42, cambiala por return True",
        _ctx(foreground_app="code", active_file="/x/a.py"),
    ) == ir.EDITAR


def test_actionable_mode_never_raises():
    assert ir.actionable_mode(None, None) == ""
    assert ir.actionable_mode("", object()) == ""


def test_turn_prefix_empty_for_chat():
    assert ir.turn_prefix("hola, ¿cómo estás?", _ctx()) == ""


def test_turn_prefix_wraps_mode_block():
    p = ir.turn_prefix("arreglalo", _ctx())
    assert p.startswith("[INSTRUCCIÓN INTERNA — MODO DEL TURNO: AUTONOMO]")
    assert p.rstrip().endswith("[FIN DE LA INSTRUCCIÓN INTERNA]")
    assert "No digas 'listo' sin verificar" in p


def test_turn_prefix_explicit_investigar_has_block_but_no_auto():
    p = ir.turn_prefix("investigá por qué falla el login", _ctx())
    assert "MODO DEL TURNO: INVESTIGAR" in p
    assert "NO edites" in p


def test_turn_prefix_never_raises():
    assert ir.turn_prefix(None, None) == ""


class _DummyChat:
    def __init__(self, with_compact=True):
        self._system = "SYS"
        if with_compact:
            self._system_compact = "COMPACT"


def test_mode_system_injects_and_restores():
    chat = _DummyChat()
    with ir.mode_system(chat, "arreglalo", _ctx()) as mode:
        assert mode == ir.AUTONOMO
        assert chat._system.startswith("SYS")
        assert "Modo AUTONOMO" in chat._system
        assert "Modo AUTONOMO" in chat._system_compact
    assert chat._system == "SYS"
    assert chat._system_compact == "COMPACT"


def test_mode_system_chat_turn_untouched():
    chat = _DummyChat()
    with ir.mode_system(chat, "hola, ¿cómo estás?", _ctx()) as mode:
        assert mode == ""
        assert chat._system == "SYS"
        assert chat._system_compact == "COMPACT"


def test_mode_system_restores_even_on_exception():
    chat = _DummyChat()
    try:
        with ir.mode_system(chat, "arreglalo", _ctx()):
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    assert chat._system == "SYS"
    assert chat._system_compact == "COMPACT"


def test_mode_system_without_compact_attr():
    chat = _DummyChat(with_compact=False)
    with ir.mode_system(chat, "arreglalo", _ctx()) as mode:
        assert mode == ir.AUTONOMO
        assert "Modo AUTONOMO" in chat._system
    assert chat._system == "SYS"

