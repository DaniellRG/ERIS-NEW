"""Tests for core/agent_router.py"""
import json
import tempfile
from pathlib import Path
from unittest.mock import patch


def test_agent_definitions_complete():
    from core.agent_router import AGENT_DEFINITIONS
    required_agents = {"vision", "search", "security", "system", "media", "productivity", "dev", "home", "reverse", "self"}
    assert required_agents == set(AGENT_DEFINITIONS.keys())


def test_all_agents_have_required_fields():
    from core.agent_router import AGENT_DEFINITIONS
    for key, agent in AGENT_DEFINITIONS.items():
        assert "name" in agent, f"{key} missing 'name'"
        assert "description" in agent, f"{key} missing 'description'"
        assert "keywords" in agent, f"{key} missing 'keywords'"
        assert "tools" in agent, f"{key} missing 'tools'"
        assert len(agent["keywords"]) > 0, f"{key} has no keywords"
        assert len(agent["tools"]) > 0, f"{key} has no tools"


def test_classify_intent_vision():
    from core.agent_router import get_router
    router = get_router()
    # "que ves en la pantalla" should route to vision
    result = router.classify_intent("que ves en la pantalla")
    assert result == "vision"


def test_classify_intent_search():
    from core.agent_router import get_router
    router = get_router()
    result = router.classify_intent("busca informacion sobre python")
    assert result == "search"


def test_classify_intent_media():
    from core.agent_router import get_router
    router = get_router()
    result = router.classify_intent("pon musica en spotify")
    assert result == "media"


def test_classify_intent_none_for_ambiguous():
    from core.agent_router import get_router
    router = get_router()
    # Very short/ambiguous text should return None
    result = router.classify_intent("hola")
    assert result is None


def test_classify_intent_penalty_reduces_score():
    from core.agent_router import get_router
    router = get_router()
    # "busca virus" — "busca" matches search, "virus" penalizes search
    # Should NOT route to search
    result = router.classify_intent("busca virus en mi computadora")
    # Should route to security instead of search
    assert result != "search"


def test_classify_intent_multiword_bonus():
    from core.agent_router import get_router
    router = get_router()
    # Multi-word phrases should get bonus
    result = router.classify_intent("reproducir musica en spotify")
    assert result == "media"


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
    assert len(agents) == 10
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
    assert stats["agents_available"] == 10


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
    from core.agent_router import AGENT_DEFINITIONS
    for key, agent in AGENT_DEFINITIONS.items():
        penalties = set(kw.lower() for kw in agent.get("penalty_keywords", []))
        own_kws = set(kw.lower() for kw in agent["keywords"])
        overlap = penalties & own_kws
        assert not overlap, f"{key} has overlapping penalty/own keywords: {overlap}"
