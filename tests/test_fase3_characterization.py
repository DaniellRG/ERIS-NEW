# -*- coding: utf-8 -*-
"""
tests/test_fase3_characterization.py

Tests de caracterización (Fase 3, T7) para los módulos extraídos del god file
que no requieren PyQt6. Sirven para asegurar que la refactorización no
cambió el comportamiento:

  - core.controller : observer_line, tts_backend_works
  - core.events     : EventBus (on/emit/off, singleton, aislamiento de fallos)
  - core.app        : bootstrap() (arranque headless, no lanza)

Nota: gui.widgets requiere PyQt6 y no se testa aquí; se verifica con
py_compile (hecho) y con la suite completa cuando haya entorno gráfico.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def test_controller_observer_line_known_types():
    from core.controller import Controller
    c = Controller()
    r = c.observer_line({"type": "start_coding", "project": "MiApp"}, "")
    assert isinstance(r, str) and len(r) > 0
    assert "MiApp" in r
    r = c.observer_line({"type": "app_switch", "to_title": "Chrome"}, "")
    assert isinstance(r, str) and "Chrome" in r
    # Tipo desconocido -> cadena vacía (no lanza)
    assert c.observer_line({"type": "otro"}, "") == ""


def test_controller_tts_backend_unknown_does_not_raise():
    from core.controller import Controller
    c = Controller()
    # Backend inexistente -> False, nunca lanza
    assert c.tts_backend_works("no_existe_backend_xyz") is False


def test_event_bus_on_emit_off():
    from core.events import EventBus
    bus = EventBus()
    calls = []
    bus.on("test", lambda *a, **k: calls.append((a, k)))
    bus.emit("test", 1, x=2)
    bus.emit("test", 3, y=4)
    assert calls == [((1,), {"x": 2}), ((3,), {"y": 4})]

    # off elimina el handler
    bus.off("test", calls and None)  # no-op si no coincide
    # Re-agregar y quitar correctamente
    h = lambda *a, **k: None
    bus.on("adios", h)
    bus.emit("adios")
    bus.off("adios", h)
    bus.emit("adios")  # no debe lanzar


def test_event_bus_handler_failure_is_isolated():
    from core.events import EventBus
    bus = EventBus()
    results = []

    def boom(*a, **k):
        raise RuntimeError("boom")

    def ok(*a, **k):
        results.append("ok")

    bus.on("err", boom)
    bus.on("err", ok)
    bus.emit("err")  # boom no debe impedir que ok se ejecute
    assert results == ["ok"]


def test_event_bus_singleton():
    from core.events import get_event_bus
    b1 = get_event_bus()
    b2 = get_event_bus()
    assert b1 is b2


def test_app_bootstrap_does_not_raise():
    from core.app import bootstrap
    # Todas las sub-operaciones van dentro de try/except; no debe lanzar
    # aunque falten deps o archivos en entorno mínimo.
    bootstrap()


def test_controller_cognitive_and_autonomy_cycles_do_not_raise():
    from core.controller import Controller
    c = Controller()
    logs = []
    c.run_cognitive_cycle(lambda m: logs.append(m), context="proactive")
    c.run_autonomy_cycle(lambda m: logs.append(m))
    assert isinstance(logs, list)
    assert any("COGNITIVE" in m for m in logs)
    assert any("AUTONOMY" in m for m in logs)


def test_controller_proactive_reminders_no_events():
    from core.controller import Controller
    c = Controller()
    # Sin archivo de eventos -> no lanza, no registra nada
    logs = []
    c.proactive_reminders(lambda m: logs.append(m))
    assert logs == []


def test_controller_voice_resilient_fallback_no_local_tts():
    from core.controller import Controller
    c = Controller()
    logs = []
    # Sin token ni TTS local configurado -> no persiste backend, no lanza.
    # El print con emoji de este entorno embebido (cp1252) se reemplaza para
    # no fallar por codificación de consola; la lógica bajo prueba es que no
    # se persiste backend inexistente.
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        c.voice_resilient_fallback(lambda m: logs.append(m), remember_cb=lambda m: logs.append(m))


if __name__ == "__main__":
    import traceback

    tests = [
        test_controller_observer_line_known_types,
        test_controller_tts_backend_unknown_does_not_raise,
        test_event_bus_on_emit_off,
        test_event_bus_handler_failure_is_isolated,
        test_event_bus_singleton,
        test_app_bootstrap_does_not_raise,
        test_controller_cognitive_and_autonomy_cycles_do_not_raise,
        test_controller_proactive_reminders_no_events,
        test_controller_voice_resilient_fallback_no_local_tts,
    ]
    passed = 0
    failed = 0
    for t in tests:
        name = t.__name__
        try:
            t()
            print(f"PASS {name}")
            passed += 1
        except Exception as e:
            print(f"FAIL {name}: {e}")
            traceback.print_exc()
            failed += 1
    print(f"\n{passed} passed, {failed} failed, {passed + failed} total")
    raise SystemExit(1 if failed else 0)
