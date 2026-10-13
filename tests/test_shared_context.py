"""
tests/test_shared_context.py
────────────────────────────
Fase 1.1: `core/shared_context.py` es el contexto único por proceso.

Verifica el contrato que van a consumir GUI, CLI y subagentes: singleton,
historial acotado, detección honesta de la raíz del proyecto, bloque de prompt
y vista serializable — sin Qt, sin red, sin lanzar.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parent.parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from core import shared_context as sc  # noqa: E402


@pytest.fixture()
def ctx():
    c = sc.reset_shared_context()
    yield c
    sc.reset_shared_context()


def test_singleton_identity():
    a = sc.get_shared_context()
    b = sc.get_shared_context()
    assert a is b
    c = sc.reset_shared_context()
    assert c is not a
    assert sc.get_shared_context() is c


def test_note_is_bounded(ctx):
    for i in range(sc._CONVO_MAX + 10):
        ctx.note(f"turno {i}")
    assert len(ctx.convo_ctx) == sc._CONVO_MAX
    assert ctx.convo_ctx[-1] == f"turno {sc._CONVO_MAX + 9}"


def test_note_ignores_empty(ctx):
    ctx.note("")
    ctx.note(None)
    ctx.note("   ")
    assert ctx.convo_ctx == []


def test_recent_convo(ctx):
    ctx.set_conversation(["a", "b", "c", "d", "e"])
    assert ctx.recent_convo(2) == ["d", "e"]
    assert ctx.recent_convo(0) == []


def test_detect_project_root_finds_marker(ctx, tmp_path):
    root = tmp_path / "proj"
    (root / ".git").mkdir(parents=True)
    deep = root / "src" / "pkg"
    deep.mkdir(parents=True)
    found = ctx.detect_project_root(str(deep / "mod.py"))
    assert found == str(root)
    assert ctx.project_root == str(root)


def test_detect_project_root_falls_back_to_start(ctx, tmp_path):
    empty = tmp_path / "solo"
    empty.mkdir()
    found = ctx.detect_project_root(str(empty))
    assert found == str(empty)


def test_detect_project_root_never_raises(ctx):
    ctx.detect_project_root("\x00invalido\x00")  # no debe lanzar
    assert ctx.project_root is None or isinstance(ctx.project_root, str)


def test_context_block_empty_when_nothing(ctx):
    assert ctx.context_block() == ""


def test_context_block_includes_fields(ctx, tmp_path):
    ctx.set_project_root(str(tmp_path))
    ctx.set_active_file(str(tmp_path / "main.py"))
    ctx.set_foreground_app("code")
    ctx.set_session_summary("arreglando failover")
    ctx.note("hola")
    block = ctx.context_block()
    assert "[CONTEXTO COMPARTIDO]" in block
    assert "Proyecto" in block
    assert "Archivo activo" in block
    assert "App en foco" in block
    assert "Resumen de sesión" in block
    assert "Venimos hablando" in block


def test_read_only_is_reflected(ctx):
    ctx.set_read_only(True)
    assert "SOLO LECTURA" in ctx.context_block()
    ctx.set_read_only(False)
    assert "SOLO LECTURA" not in ctx.context_block()


def test_as_dict_is_serializable_view(ctx):
    ctx.note("x")
    ctx.set_identity(name="Eris", color="azul")
    d = ctx.as_dict()
    assert set(d) == {"convo_ctx", "session_summary", "project_root",
                      "active_file", "foreground_app", "identity", "read_only"}
    assert d["convo_ctx"] == ["x"]
    assert d["identity"]["color"] == "azul"
    # Es una copia: mutar la vista no toca el estado vivo.
    d["convo_ctx"].append("mutado")
    assert ctx.convo_ctx == ["x"]


def test_clear_resets_everything(ctx):
    ctx.note("x")
    ctx.set_project_root("/tmp")
    ctx.set_read_only(True)
    ctx.clear()
    assert ctx.convo_ctx == []
    assert ctx.project_root is None
    assert ctx.read_only is False
    assert ctx.identity["name"] == "Eris"


def test_thread_safety_smoke(ctx):
    import threading

    def worker(tag):
        for i in range(200):
            ctx.note(f"{tag}-{i}")

    ts = [threading.Thread(target=worker, args=(t,)) for t in range(6)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    assert len(ctx.convo_ctx) <= sc._CONVO_MAX
