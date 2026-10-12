"""
tests/test_hermes_tools.py
──────────────────────────
Fase 0.5 / B9 + B10: las 7 herramientas Hermes existen de VERDAD y están
sincronizadas registry ↔ declarations.

Contexto: `_GEMINI_PRIORITY_TOOLS` prometía 12 tools `hermes_*` que no existían
(`action_imports` las dejaba en None). Gemini las "usaba", fallaban, y Eris lo
narraba como si hubiera pasado. Acá se fija que las 7 reales existan y que la
sync sagrada (len == len, 0 dupes) siga intacta.
"""

from __future__ import annotations

import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

HERMES = [
    "hermes_web_search",
    "hermes_web_scraper",
    "hermes_page_summarizer",
    "hermes_data_analyzer",
    "hermes_csv_processor",
    "hermes_code_review",
    "hermes_security_audit",
]


def test_hermes_module_imports_and_has_seven():
    from core import hermes_tools
    for name in HERMES:
        assert callable(getattr(hermes_tools, name)), f"{name} no es callable"


def test_registry_and_declarations_stay_in_sync():
    from core.tool_registry import _TOOLS
    from core.tool_declarations import TOOL_DECLARATIONS
    reg = set(_TOOLS)
    dec = [d["name"] for d in TOOL_DECLARATIONS]
    assert len(reg) == len(dec), f"sync rota: {len(reg)} registry vs {len(dec)} decls"
    assert len(dec) == len(set(dec)), "declarations con duplicados"
    assert reg == set(dec), (f"reg-only={sorted(reg - set(dec))} "
                             f"dec-only={sorted(set(dec) - reg)}")


def test_hermes_tools_resolve_in_registry():
    from core.tool_registry import get_tool, _TOOLS
    for name in HERMES:
        assert name in _TOOLS, f"{name} no está en el registry"
        assert callable(get_tool(name)), f"{name} no resuelve a callable"


def test_priority_list_has_no_phantoms():
    from core.gemini_text_chat import _GEMINI_PRIORITY_TOOLS
    from core.tool_registry import _TOOLS
    missing = [t for t in _GEMINI_PRIORITY_TOOLS if t not in _TOOLS]
    assert missing == [], f"tools fantasma en prioridad: {missing}"
    assert len(_GEMINI_PRIORITY_TOOLS) == len(set(_GEMINI_PRIORITY_TOOLS)), "dupes"


def test_action_imports_hermes_not_none():
    import core.action_imports as ai
    for name in HERMES:
        assert getattr(ai, name, None) is not None, f"{name} quedó None"


def test_hermes_tools_offline_paths_return_string():
    """Rutas sin red / entrada vacía: SIEMPRE string, nunca excepción."""
    from core import hermes_tools as h
    assert isinstance(h.hermes_web_search({}), str)
    assert isinstance(h.hermes_web_scraper({}), str)
    assert isinstance(h.hermes_code_review({}), str)
    assert isinstance(h.hermes_security_audit({}), str)


def test_hermes_data_analyzer_json():
    from core.hermes_tools import hermes_data_analyzer
    out = hermes_data_analyzer({"data": '[{"a":1,"b":2},{"a":3,"b":4}]'})
    assert "DATOS JSON" in out and "media=" in out


def test_hermes_csv_processor(tmp_path):
    from core.hermes_tools import hermes_csv_processor
    p = tmp_path / "d.csv"
    p.write_text("nombre,edad\nana,30\nleo,25\n", encoding="utf-8")
    out = hermes_csv_processor({"path": str(p), "action": "describe"})
    assert "2 filas" in out and "edad" in out


def test_hermes_code_review_detects_bare_except():
    from core.hermes_tools import hermes_code_review
    out = hermes_code_review({"code": "def f():\n    try:\n        x=1\n    except:\n        pass\n"})
    assert "except:" in out.lower()


def test_hermes_security_audit_flags_secret():
    from core.hermes_tools import hermes_security_audit
    out = hermes_security_audit({"code": 'password="abcdef123456"\n'})
    assert "secreto" in out.lower()
