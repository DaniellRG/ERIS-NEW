"""
tests/test_subagent_shared_context.py
─────────────────────────────────────
Fase 1.2: los subagentes reciben el SharedContext del proceso.

Verificación del plan: "un subagente responde con conocimiento del historial".
`dispatch_to_sub_agent` fusiona el contexto compartido en el `context` que
recibe `execute(task, context)`, sin pisar los params explícitos de la tarea.
"""

from __future__ import annotations

import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from core import shared_context as sc  # noqa: E402
from core.sub_agent_crew import dispatch_to_sub_agent, _with_shared_context  # noqa: E402


class _FakeTask:
    def __init__(self, tid, params):
        self.id = tid
        self.params = params


class _FakeAgent:
    def __init__(self):
        self.seen = None
        self.last_task = None

    def execute(self, task, context):
        self.seen = context
        self.last_task = task
        return "resultado del agente"


class _FakeRegistry:
    def __init__(self, agent):
        self._agent = agent

    def get_agent(self, key):
        return self._agent if key == "FakeAgent" else None

    def get_all_agents(self):
        return ["FakeAgent"]

    def create_task(self, key, desc, params):
        return _FakeTask("t1", params)

    def update_task_status(self, *a, **k):
        pass


def _setup(**fields):
    sc.reset_shared_context()
    ctx = sc.get_shared_context()
    for k, v in fields.items():
        if k == "note":
            ctx.note(v)
        elif k == "summary":
            ctx.set_session_summary(v)
        elif k == "project_root":
            ctx.set_project_root(v)
        elif k == "foreground_app":
            ctx.set_foreground_app(v)
        elif k == "read_only":
            ctx.set_read_only(v)
    return ctx


def test_subagent_receives_history_and_project():
    ctx = _setup(note="venimos hablando de failover", summary="sesión larga",
                 project_root="/tmp/proyecto", foreground_app="code")
    agent = _FakeAgent()
    out = dispatch_to_sub_agent("FakeAgent", {"request": "seguí con eso"},
                                registry=_FakeRegistry(agent))
    assert out == "resultado del agente"
    assert agent.seen["convo_ctx"] == ["venimos hablando de failover"]
    assert agent.seen["session_summary"] == "sesión larga"
    assert agent.seen["project_root"] == "/tmp/proyecto"
    assert agent.seen["foreground_app"] == "code"
    assert agent.seen["request"] == "seguí con eso"


def test_explicit_task_params_win_over_shared():
    _setup(project_root="/compartido")
    agent = _FakeAgent()
    dispatch_to_sub_agent("FakeAgent", {"request": "x", "project_root": "/explicito"},
                          registry=_FakeRegistry(agent))
    assert agent.seen["project_root"] == "/explicito"


def test_unknown_agent_is_honest():
    _setup()
    out = dispatch_to_sub_agent("NoExiste", {"request": "x"}, registry=_FakeRegistry(_FakeAgent()))
    assert "No existe el sub-agente" in out


def test_explicit_shared_context_dict_is_honored():
    merged = _with_shared_context({"request": "r"}, {"project_root": "/dict", "read_only": True})
    assert merged["project_root"] == "/dict"
    assert merged["read_only"] is True
    assert merged["request"] == "r"


def test_merge_never_raises_on_garbage():
    assert _with_shared_context(None, object()) == {}
    assert _with_shared_context({"a": 1}, object())["a"] == 1
