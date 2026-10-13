"""
tests/test_autonomy_shared.py
─────────────────────────────
Fase 3.3: la autonomía lee del SharedContext (un solo cerebro).

- SharedContext es la fuente de verdad del "idle" (un reloj para GUI/CLI/daemons).
- Los cooldowns/umbrales viven en `SharedContext.autonomy`, más bajos que antes.
- `core.autonomia` y `core.observer` respetan esa config (con fallback).
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parent.parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from core import shared_context as sc  # noqa: E402
from core import autonomia  # noqa: E402
from core import observer  # noqa: E402


@pytest.fixture()
def ctx():
    c = sc.reset_shared_context()
    yield c
    sc.reset_shared_context()


# ── SharedContext: reloj de actividad ──

def test_touch_activity_resets_idle(ctx):
    ctx.touch_activity(ts=time.time() - 120)
    assert ctx.idle_seconds() >= 119
    ctx.touch_activity()
    assert ctx.idle_seconds() < 2
    assert ctx.is_idle(0) is True
    assert ctx.is_idle(3600) is False


def test_idle_never_negative(ctx):
    ctx.touch_activity(ts=time.time() + 1000)  # futuro imposible
    assert ctx.idle_seconds() >= 0.0


# ── SharedContext: config de autonomía ──

def test_autonomy_defaults_are_lower(ctx):
    # "bajar cooldowns que hoy los hacen inaudibles"
    assert ctx.get_autonomy("iniciativa_cooldown_s") == 300   # antes 900
    assert ctx.get_autonomy("observer_voice_cooldown_min") == 4.0  # antes 7
    assert ctx.get_autonomy("observer_mirar_interval_min") == 6    # antes 10
    assert ctx.get_autonomy("enabled") is True


def test_set_autonomy_overrides(ctx):
    ctx.set_autonomy(enabled=False, iniciativa_cooldown_s=30)
    assert ctx.get_autonomy("enabled") is False
    assert ctx.get_autonomy("iniciativa_cooldown_s") == 30
    # None no pisa el valor existente
    ctx.set_autonomy(iniciativa_cooldown_s=None)
    assert ctx.get_autonomy("iniciativa_cooldown_s") == 30


def test_clear_resets_activity_and_autonomy(ctx):
    ctx.touch_activity(ts=time.time() - 999)
    ctx.set_autonomy(enabled=False)
    ctx.clear()
    assert ctx.idle_seconds() < 2
    assert ctx.get_autonomy("enabled") is True


# ── core.autonomia lee la config compartida ──

def test_autonomia_cooldown_from_shared(ctx):
    assert autonomia._cooldown_seconds() == 300
    ctx.set_autonomy(iniciativa_cooldown_s=42)
    assert autonomia._cooldown_seconds() == 42


def test_autonomia_disabled_returns_cooldown_prefix(ctx):
    ctx.set_autonomy(enabled=False)
    out = autonomia.turno_de_iniciativa()
    assert out.startswith("Iniciativa en cooldown")
    assert "desactivada" in out


def test_autonomia_runs_and_rotates(ctx, tmp_path, monkeypatch):
    # Aislar estado y capacidades: nunca corremos módulos reales en tests.
    monkeypatch.setattr(autonomia, "_STATE_FILE", tmp_path / "autonomia.json")
    monkeypatch.setattr(autonomia, "_notify", lambda *_: None)
    fake = [("uno", lambda: "resultado-uno"), ("dos", lambda: "resultado-dos")]
    monkeypatch.setattr(autonomia, "_CAPACIDADES", fake)
    ctx.set_autonomy(iniciativa_cooldown_s=0)

    r1 = autonomia.turno_de_iniciativa()
    assert "resultado-uno" in r1 and "uno" in r1
    r2 = autonomia.turno_de_iniciativa()
    assert "resultado-dos" in r2 and "dos" in r2
    assert "Iniciativa plena de ERIS" in autonomia.estado()


def test_autonomia_cooldown_blocks_second_run(ctx, tmp_path, monkeypatch):
    monkeypatch.setattr(autonomia, "_STATE_FILE", tmp_path / "autonomia.json")
    monkeypatch.setattr(autonomia, "_notify", lambda *_: None)
    monkeypatch.setattr(autonomia, "_CAPACIDADES", [("uno", lambda: "ok")])
    ctx.set_autonomy(iniciativa_cooldown_s=3600)

    assert "ok" in autonomia.turno_de_iniciativa()
    assert autonomia.turno_de_iniciativa().startswith("Iniciativa en cooldown")


# ── core.observer respeta la config compartida ──

def test_observer_voice_uses_shared_cooldown(ctx, monkeypatch):
    now = time.time()
    # Comentario hace 5 min; cooldown compartido por defecto = 4 min → permiso.
    monkeypatch.setattr(observer, "_load", lambda: {
        "voice": {"hour_start": now, "count_hour": 0},
        "config": {}, "comment": {"last": now - 5 * 60},
        "vista": {}, "coding": {}, "glimpses": []})
    assert observer.should_voice() is True

    # Con un cooldown compartido de 10 min → todavía no.
    ctx.set_autonomy(observer_voice_cooldown_min=10)
    assert observer.should_voice() is False


def test_observer_mirar_interval_uses_shared(ctx, monkeypatch):
    started = {"n": 0}

    class _FakeThread:
        def __init__(self, *a, **k):
            pass

        def start(self):
            started["n"] += 1

    monkeypatch.setattr(observer, "threading", type("T", (), {"Thread": _FakeThread}))
    monkeypatch.setattr(observer, "get_foreground", lambda: {"proc": "code", "title": "x.py"})
    monkeypatch.setattr(observer, "classify", lambda p, t: {"kind": "programacion"})

    now = time.time()
    state = {
        "vista": {"ok": True},
        "coding": {"session_start": now - 600},
        "config": {"mirar_min_coding_min": 5},
        "glimpses": [{"t": now - 5 * 60}],  # hace 5 min
    }
    monkeypatch.setattr(observer, "_load", lambda: state)

    # Cooldown compartido por defecto 6 min → todavía no toca mirar.
    ctx.set_autonomy(observer_mirar_interval_min=6)
    observer.maybe_glimpse()
    assert started["n"] == 0

    # Con 1 min → ya toca.
    ctx.set_autonomy(observer_mirar_interval_min=1)
    observer.maybe_glimpse()
    assert started["n"] == 1
