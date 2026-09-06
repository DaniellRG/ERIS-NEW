"""Tests for core/agent_router.py — 12-agent architecture (single source of truth)."""
import json
import tempfile
from pathlib import Path
from unittest.mock import patch


def test_agent_definitions_complete():
    from core.agent_definitions import AGENT_DEFINITIONS
    required_agents = {"core", "web", "file", "dev", "media", "comm",
                       "vision", "security", "study", "linux", "guardian", "mentora"}
    assert required_agents == set(AGENT_DEFINITIONS.keys())


def test_all_agents_have_required_fields():
    from core.agent_definitions import AGENT_DEFINITIONS
    for key, agent in AGENT_DEFINITIONS.items():
        assert "name" in agent, f"{key} missing 'name'"
        assert "description" in agent, f"{key} missing 'description'"
        assert "keywords" in agent, f"{key} missing 'keywords'"
        assert "penalty_keywords" in agent, f"{key} missing 'penalty_keywords'"
        assert "tools" in agent, f"{key} missing 'tools'"
        assert "handler" in agent, f"{key} missing 'handler'"
        assert len(agent["keywords"]) > 0, f"{key} has no keywords"
        assert len(agent["tools"]) > 0, f"{key} has no tools"


def test_router_uses_single_source():
    """The router must import (not duplicate) AGENT_DEFINITIONS."""
    import core.agent_router as AR
    from core.agent_definitions import AGENT_DEFINITIONS
    assert AR.AGENT_DEFINITIONS is AGENT_DEFINITIONS


def test_classify_intent_domains():
    from core.agent_router import get_router
    router = get_router()
    cases = {
        "core": ["apagá la computadora", "cómo anda mi sistema"],
        "web": ["busca informacion sobre python", "abrí la página de clima"],
        "file": ["creá una carpeta llamada proyectos", "renombrá este archivo"],
        "dev": ["escribime un script de python", "compilá este proyecto"],
        "media": ["pon musica en spotify", "reproducir musica en spotify"],
        "comm": ["mandá un email a juan", "creá un documento word"],
        "vision": ["que ves en la pantalla", "qué hay en la pantalla"],
        "security": ["busca virus en mi computadora", "analizá este puerto abierto"],
        "study": ["resumí este papel de estudio", "explicame que es blockchain"],
        "linux": ["grabá la pantalla 5 segundos", "mové el mouse a 500 300"],
        "guardian": ["revisá mi salud", "repará los errores del codebase"],
        "mentora": ["enseñame a resolver una crisis", "aprendé la lección X"],
    }
    for agent, frases in cases.items():
        for frase in frases:
            assert router.classify_intent(frase) == agent, f"{frase!r} should be {agent}"


def test_classify_intent_none_for_ambiguous():
    from core.agent_router import get_router
    router = get_router()
    # Very short/ambiguous text should return None
    assert router.classify_intent("hola") is None


def test_classify_intent_penalty_reduces_score():
    from core.agent_router import get_router
    router = get_router()
    # "busca virus" — "busca" matches web, "virus" penalizes web → security
    assert router.classify_intent("busca virus en mi computadora") == "security"


def test_toggle_agent():
    from core.agent_router import get_router
    router = get_router()
    result = router.toggle_agent("vision", False)
    assert "deshabilitado" in result
    # Re-enable
    router.toggle_agent("vision", True)


def test_get_agent_list():
    from core.agent_router import get_router
    router = get_router()
    agents = router.get_agent_list()
    assert isinstance(agents, list)
    assert len(agents) == 12
    for agent in agents:
        assert "key" in agent
        assert "name" in agent
        assert "enabled" in agent


def test_get_stats():
    from core.agent_router import get_router
    router = get_router()
    stats = router.get_stats()
    assert "handoff_count" in stats
    assert "agents_available" in stats
    assert stats["agents_available"] == 12


def test_registry_persists(tmp_path):
    from core.agent_router import _save_registry, _load_registry
    fake_path = tmp_path / "agent_registry.json"
    data = {"agents": {}, "handoff_count": 5, "last_handoff": None}
    with patch("core.agent_router._REGISTRY_PATH", fake_path):
        _save_registry(data)
        loaded = _load_registry()
    assert loaded["handoff_count"] == 5


def test_no_duplicate_keywords_across_agents():
    """Verify penalty keywords don't appear in own keywords."""
    from core.agent_definitions import AGENT_DEFINITIONS
    for key, agent in AGENT_DEFINITIONS.items():
        penalties = set(kw.lower() for kw in agent.get("penalty_keywords", []))
        own_kws = set(kw.lower() for kw in agent["keywords"])
        overlap = penalties & own_kws
        assert not overlap, f"{key} has overlapping penalty/own keywords: {overlap}"