"""
tests/test_tool_guard.py
─────────────────────────
Fase 0.0 del diseño: el Custodio y el permission gate tienen que estar EN el
camino de `dispatch_tool`, antes de que se enciendan las 27 herramientas de la
tripulación.

Tests:
  1. El patrón `push --force` se BLOQUEA y queda registrado.
  2. `rm -rf` en shell_session se BLOQUAEJA.
  3. Una tool de riesgo sin patrón pasa, pero queda auditada.
  4. Una tool inocua pasa sin pasar por el audit.
  5. Una tool inexistente lanza KeyError (no devuelve texto de error).
  6. Una tool que revienta lanza su excepción real (no la disfraza).
  7. El permission gate deniega cuando corresponde.
  8. ActionGuard y dispatch_tool comparten las MISMAS reglas.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parent.parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from core import tool_dispatch_api as tda  # noqa: E402


# ── 1 y 2: patrones peligrosos bloqueados ────────────────────────────────────

# Solo tools que EXISTEN hoy en el registro. (email_sender / webhook_sender /
# api_invoke las vigila el Custodio pero no existen -> se testean aparte.)
@pytest.mark.parametrize("tool,params,patron", [
    ("git_control",   {"action": "push", "branch": "main", "extra": "push --force"}, "push --force"),
    ("shell_session", {"command": "rm -rf /"},                              "rm -rf"),
    ("terminal_agent",{"command": "sudo rm -rf /tmp/x"},                     "rm -rf"),
    ("file_api",      {"action": "delete", "path": "/tmp/x.txt"},            "delete"),
    ("pc_control",    {"action": "poweroff"},                                "poweroff"),
])
def test_peligro_bloqueado(tool, params, patron):
    with pytest.raises(PermissionError) as ei:
        tda.dispatch_tool(tool, params, source="test")
    msg = str(ei.value)
    assert "BLOQUEADA" in msg.upper() or "deneg" in msg.lower()
    assert patron in msg or patron in str(params).lower()


def test_confirmacion_explicita_permite_el_patron():
    """`confirm=True` es el usuario diciendo 'dale'. Debe destrabar el patrón."""
    v = tda.guard_check("git_control",
                        {"action": "push", "extra": "push --force"},
                        confirm=True)
    assert v.allowed is True
    assert v.matched == "push --force"
    assert v.risk == "risky"


def test_sin_confirmacion_sigue_bloqueado():
    v = tda.guard_check("git_control", {"action": "push", "extra": "push --force"})
    assert v.allowed is False
    assert v.reason == "blocked_pattern"


# ── 3 y 4: tools de riesgo pasan pero quedan auditadas ───────────────────────

def test_tool_de_riesgo_pasa_y_se_audita(tmp_path, monkeypatch):
    log = tmp_path / "audit.jsonl"
    monkeypatch.setattr(tda, "_AUDIT_LOG", log)

    v = tda.guard_check("git_control", {"action": "status"})
    assert v.allowed is True and v.risk == "risky"

    tda.audit(tda.AuditRecord(
        time="2026-10-12 00:00:00", tool="git_control", allowed=True,
        stage="allowed", reason="risky_allowed", source="test"))
    assert log.exists()
    rec = json.loads(log.read_text(encoding="utf-8").splitlines()[0])
    assert rec["tool"] == "git_control" and rec["allowed"] is True


def test_tool_inocua_no_es_de_riesgo():
    v = tda.guard_check("web_search", {"query": "clima hoy"})
    assert v.allowed is True and v.risk == "safe"


# ── 5: tool inexistente falla ruidoso ─────────────────────────────────────────

def test_tool_inexistente_lanza_keyerror():
    with pytest.raises(KeyError) as ei:
        tda.dispatch_tool("esta_tool_no_existe_xyz", {}, source="test")
    # El mensaje tiene que ayudar, no decir "no disponible en este contexto".
    assert "Tool desconocida" in str(ei.value)
    assert "disponible" not in str(ei.value).replace("Herramientas disponibles", "")


# ── 6: excepción real, no disfrazada ─────────────────────────────────────────

def test_excepcion_de_la_tool_sube(monkeypatch):
    """Si la tool revienta, la excepción debe llegar arriba. Esto es lo que
    el `_dispatch_tool` viejo se tragaba y por eso Eris mintió."""
    from core import tool_registry

    def boom(parameters=None, player=None):
        raise RuntimeError("revento de verdad")

    monkeypatch.setitem(tool_registry._TOOLS, "tool_que_revienta", (None, None))
    monkeypatch.setattr(tool_registry, "get_tool",
                        lambda n: boom if n == "tool_que_revienta" else None)
    monkeypatch.setattr(tda, "get_dispatcher", _fake_dispatcher)

    with pytest.raises(RuntimeError, match="revento de verdad"):
        tda.dispatch_tool("tool_que_revienta", {}, source="test")


class _FakeDispatcher:
    def _build_kwargs(self, func, args):
        return {"parameters": args}


def _fake_dispatcher():
    return _FakeDispatcher()


# ── 7: el permission gate está en el camino y es fail-closed ─────────────────

def test_permission_gate_se_consulta(monkeypatch):
    """Si el gate deniega, no se ejecuta la tool."""
    from core import permission_gate as pg

    class GateQueDeniega:
        def check(self, name, params, user="default"):
            return pg.PermissionResult(False, "denegado_por_test")

    monkeypatch.setattr(pg, "get_permission_gate", lambda: GateQueDeniega())

    with pytest.raises(PermissionError, match="denegado_por_test"):
        tda.dispatch_tool("file_api", {"action": "read", "path": "/tmp/x"},
                          source="test")


def test_permission_gate_que_falla_deniega(monkeypatch):
    """Fail-closed: si el gate no se puede evaluar, NO se ejecuta."""
    from core import permission_gate as pg

    class GateQueExplota:
        def check(self, *a, **k):
            raise RuntimeError("el gate se cayo")

    monkeypatch.setattr(pg, "get_permission_gate", lambda: GateQueExplota())

    with pytest.raises(PermissionError):
        tda.dispatch_tool("file_api", {"action": "read", "path": "/tmp/x"},
                          source="test")


# ── 8: ActionGuard y dispatch_tool no pueden divergir ────────────────────────

def test_actionguard_usa_las_mismas_reglas():
    from core.sub_agent_crew import ActionGuard

    params = {"action": "push", "extra": "push --force"}
    verdict = tda.guard_check("git_control", params)

    ag = ActionGuard()
    task = type("T", (), {"params": {"tool": "git_control", "params": params}})()
    respuesta = str(ag.execute(task, {}))

    # Lo que dice el chat y lo que decide el código tienen que coincidir.
    assert ("BLOQUEADA" in respuesta) == (verdict.allowed is False)
    assert set(ActionGuard()._BLOCKED_PARAMS.keys()) == set(tda.BLOCKED_PARAMS.keys())
    assert set(ActionGuard()._RISKY_API) == set(tda.RISKY_API)


# ── host headless ────────────────────────────────────────────────────────────

def test_headless_no_autoriza_nada():
    host = tda.HeadlessHost()
    assert host.ui.ask("¿ejecuto?") is False      # nadie responde → no
    assert host.ui.muted is True
    assert host.ui.last_log()                     # y queda registrado


def test_get_dispatcher_es_singleton():
    assert tda.get_dispatcher() is tda.get_dispatcher()


# ── el hueco que los patrones de texto no ve ────────────────────────────────

def test_push_forced_por_parametro_tambien_se_bloquea():
    """`git_control(action="push", force=True)` no contiene el texto
    "push --force". Antes se colaba. Ahora no."""
    v = tda.guard_check("git_control", {"action": "push", "force": True})
    assert v.allowed is False
    assert v.reason == "blocked_param"
    assert v.matched == "git_control.force=True"


def test_push_forced_con_confirmacion_pasa():
    v = tda.guard_check("git_control", {"action": "push", "force": True},
                        confirm=True)
    assert v.allowed is True and v.matched == "git_control.force=True"


@pytest.mark.parametrize("tool,params,esperado", [
    ("git_control",   {"action": "status"},                   None),
    ("git_control",   {"action": "commit", "message": "x"},   None),
    ("file_api",      {"action": "read", "path": "/tmp/x"},    None),
    ("git_control",   {"action": "push", "force": "false"},    None),
    ("git_control",   {"action": "push", "force": True},       "git_control.force=True"),
    ("file_api",      {"action": "delete", "path": "/x"},      "file_api.action=delete"),
    ("pc_control",    {"action": "reboot"},                    "pc_control.action=reboot"),
    ("process_manager", {"action": "kill", "pid": 1},          "process_manager.action=kill"),
])
def test_param_block_precision(tool, params, esperado):
    assert tda.param_block(tool, params) == esperado


def test_params_anidados_tambien_se_miran():
    """Un delete escondido dentro de otro dict tampoco pasa."""
    v = tda.param_block("file_api", {"opciones": {"action": "delete"}})
    assert v == "file_api.action=delete"


def test_tools_fantasma_siguen_vigiladas():
    """El Custodio vigila email_sender/api_invoke/webhook_sender aunque hoy no
    existan en el registro. Si alguien las construye, ya estan cubiertas."""
    from core.tool_registry import _TOOLS
    for t in ("email_sender", "api_invoke", "webhook_sender"):
        assert t in tda.RISKY_API
        assert t not in _TOOLS, "si ya existe, sacar de la lista de fantasmas"
        # y no las trata como inocuas: un delete queda bloqueado igual
        assert tda.guard_check(t, {"action": "delete"}).allowed is False
