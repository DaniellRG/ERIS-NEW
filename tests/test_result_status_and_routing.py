"""
tests/test_result_status_and_routing.py
───────────────────────────────────────
Fase 0.6: corregir el estado (B11, B12).

  B11 — `_result_status` mira la clave booleana `ok`/`success` ANTES de la
        heurística de strings. `{"ok": false}` antes caía al `return "ok"` final
        y Eris aprendía éxito de un fallo (y lo narraba como logro).
  B12 — `classify_intent` salta agentes sin handler registrado: si el router ya
        tiene handlers cargados, un agente huérfano (deploy, system_monitor) no
        puede robarle el turno a uno vivo para morir con "no hay handler".
"""

from __future__ import annotations

import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))


def test_result_status_boolean_keys_win():
    from core.tool_dispatcher import _result_status
    # lo que antes estaba mal:
    assert _result_status({"ok": False}) == "error"
    assert _result_status({"success": False}) == "error"
    # y lo correcto sigue correcto:
    assert _result_status({"ok": True}) == "ok"
    assert _result_status({"success": True}) == "ok"
    assert _result_status({"error": "no configurado"}) == "error"
    assert _result_status({"result": {"ok": False, "msg": "x"}}) == "error"
    assert _result_status(None) == "vacío"
    assert _result_status("") == "vacío"
    assert _result_status("Error: timeout") == "error"
    assert _result_status("completado con éxito") == "ok"


def test_purge_learned_state_nunca_rompe(monkeypatch):
    from core.tool_dispatcher import purge_learned_state
    # force=True evita el marcador; no debe lanzar ni siquiera sin archivos.
    removed = purge_learned_state(force=True)
    assert isinstance(removed, list)


def test_classify_intent_salta_agente_sin_handler():
    """Con handlers cargados, un agente sin handler no puede ganar."""
    from core.agent_router import AgentRouter
    r = AgentRouter()
    # Sin handlers: no filtramos (comportamiento previo intacto).
    r._handlers.clear()
    assert r.classify_intent("desplegá la app en docker") in (None, "deploy", "dev")
    # Con un handler solo para 'web', deploy/system_monitor quedan fuera.
    r._handlers = {"web": lambda *a, **k: "ok"}
    # Un texto que antes caería en deploy/system_monitor ahora NO los elige.
    got = r.classify_intent("monitoreá el sistema y los procesos")
    assert got not in ("deploy", "system_monitor")
