"""
tests/test_context_builder.py
─────────────────────────────
Fase 1 (resto): el armado del contexto de `_build_config` vive en
`core/context_builder.build_system_prompt`, reutilizable por GUI/CLI/subagentes.

Los tests son herméticos: parchean los inyectores (memoria, cerebro, rituales,
RAG, estilo, ...) para no tocar estado real ni depender de red. Se verifica:

- devuelve un `str` no vacío y acotado a `MAX_SYSTEM_CHARS`;
- los bloques que dependen del `host` (conversación, shared, reconexión,
  resumen de sesión, voz) aparecen;
- nunca lanza con un host sin atributos o con `None`;
- `main.py:_build_config` delega en el módulo (el Live queda en main.py).
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parent.parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from core import context_builder as cb  # noqa: E402


def _patch(monkeypatch, modname, **attrs):
    try:
        mod = importlib.import_module(modname)
    except Exception:
        return
    for name, value in attrs.items():
        if hasattr(mod, name):
            monkeypatch.setattr(mod, name, value)


@pytest.fixture
def quiet(monkeypatch):
    """Silencia todos los inyectores para que el test sea determinista."""
    _patch(monkeypatch, "core.time_utils", get_time_context=lambda: "[TIME-CTX]")
    _patch(monkeypatch, "core.prompt_loader", load_system_prompt=lambda: "SYS_PROMPT_BASE")
    _patch(monkeypatch, "memory.memory_manager",
           load_memory=lambda: {}, format_memory_for_prompt=lambda m: "")
    # RAG de documentos: sin ping → bloque saltado.
    _patch(monkeypatch, "core.llm_bridge", ping=lambda *a, **k: False)
    # Inyectores que devuelven "" (o no-op) para no tocar estado real.
    for modname, fn in [
        ("core.daily_digest", "inject_digest"),
        ("core.cerebro", "get_brain_state"),
        ("core.expression_engine", "get_expression_injection"),
        ("core.expression_engine", "get_saludo_vivo"),
        ("core.expression_engine", "get_voz_propia"),
        ("core.relaciones", "inject_relaciones_vivas"),
        ("core.vida_interna", "inject_vida"),
        ("core.vida_interna", "maybe_ritual"),
        ("core.vida_interna", "recuperar_huella"),
        ("core.autoimagen", "get_autoimagen"),
        ("core.intereses", "inyect_intereses"),
        ("core.ambiente", "inyect_ambiente"),
        ("core.suenos", "inyect_suenos"),
        ("core.caprichos", "inyect_caprichos"),
        ("core.tiempo_interno", "inyect_tiempo_interno"),
        ("core.festejos", "inyect_festejos"),
        ("core.bienestar", "inyect_bienestar"),
        ("core.cuadernos", "inyect_cuadernos"),
        ("core.despedidas", "inyect_despedidas"),
        ("core.todo_yo", "inyect_todo_yo"),
    ]:
        _patch(monkeypatch, modname, **{fn: lambda *a, **k: ""})
    _patch(monkeypatch, "core.suenos", ilustrar_si_hay_sueno_nuevo=lambda *a, **k: None)
    _patch(monkeypatch, "core.ab_automated", get_active_style=lambda: "")
    _patch(monkeypatch, "core.truth_audit", evidence_block=lambda: "")
    _patch(monkeypatch, "core.repetition_guard", recent_replies=lambda: [])
    _patch(monkeypatch, "core.observer", get_situation_injection=lambda: "")
    # Personalidad/emoción/estilo: bloques opcionales, silenciados.
    _patch(monkeypatch, "actions.emotional_growth",
           _load=lambda: {}, get_prompt_injection=lambda s: "")
    _patch(monkeypatch, "core.personality_engine", get_tone_for_response=lambda: "")
    _patch(monkeypatch, "core.emotional_state", get_tone_instruction=None)
    _patch(monkeypatch, "actions.relationship", inject_relationship=lambda: "")
    _patch(monkeypatch, "core.style_engine", inject_style=lambda: "")
    _patch(monkeypatch, "core.emotional_core", get_core_injection=lambda: "")
    _patch(monkeypatch, "actions.gustos", inject_gustos=lambda: "")
    _patch(monkeypatch, "actions.eris_db",
           memory_all=lambda *a, **k: [], episodic_recent=lambda *a, **k: [])
    return monkeypatch


class _FakeShared:
    def context_block(self, include_convo=False, include_summary=False):
        assert include_convo is False and include_summary is False
        return "[SHARED-STUB proyecto=/x]"


class _Host:
    def __init__(self):
        self._convo_ctx = ["usuario: hola", "eris: buenas"]
        self._shared = _FakeShared()
        self._active_task = "arreglar login"
        self._last_tool_context = "file_api write"
        self._session_summary = "resumen previo"


def test_returns_string_without_host(quiet):
    out = cb.build_system_prompt(None)
    assert isinstance(out, str)
    assert "[TIME-CTX]" in out
    assert "SYS_PROMPT_BASE" in out
    assert "[VOZ]" in out


def test_host_blocks_appear(quiet):
    out = cb.build_system_prompt(_Host())
    assert "[CONTEXTO DE CONVERSACIÓN RECIENTE" in out
    assert "[SHARED-STUB proyecto=/x]" in out
    assert "RECONEXIÓN DE SESIÓN" in out
    assert "TAREA EN CURSO: arreglar login" in out
    assert "ÚLTIMO CONTEXTO: file_api write" in out
    assert "[RESUMEN DE SESIÓN LARGA" in out


def test_host_blocks_absent_without_host(quiet):
    out = cb.build_system_prompt(None)
    assert "[CONTEXTO DE CONVERSACIÓN RECIENTE" not in out
    assert "RECONEXIÓN DE SESIÓN" not in out
    assert "[RESUMEN DE SESIÓN LARGA" not in out


def test_never_raises_on_bare_object(quiet):
    out = cb.build_system_prompt(object())
    assert isinstance(out, str) and out


def test_output_is_bounded(quiet):
    out = cb.build_system_prompt(_Host())
    assert len(out) <= 30001  # MAX_SYSTEM_CHARS + "[CONTEXTO TRUNCADO]"


def test_main_build_config_delegates():
    src = (BASE / "main.py").read_text(encoding="utf-8")
    assert "from core.context_builder import build_system_prompt" in src
    assert "system_text = build_system_prompt(self)" in src
    # Lo específico de Live sigue en main.py:
    assert "types.LiveConnectConfig(**cfg_kwargs)" in src
