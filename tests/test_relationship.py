"""Tests for actions/relationship.py"""
import json
import tempfile
from pathlib import Path
from unittest.mock import patch


def test_load_defaults_on_missing_file(tmp_path):
    from actions.relationship import _load, DEFAULT_STATE
    fake_file = tmp_path / "relationship.json"
    with patch("actions.relationship.RELATIONSHIP_FILE", fake_file):
        state = _load()
    assert state["apodo"] == ""
    assert state["user_name"] == ""
    assert state["important_moments"] == []
    assert state["created"]


def test_set_apodo_persists(tmp_path):
    from actions.relationship import set_apodo, get_relationship
    fake_file = tmp_path / "relationship.json"
    with patch("actions.relationship.RELATIONSHIP_FILE", fake_file):
        set_apodo("Mi rey")
        assert get_relationship()["apodo"] == "Mi rey"
        # Persiste en disco
        data = json.loads(fake_file.read_text("utf-8"))
        assert data["apodo"] == "Mi rey"


def test_set_user_name_and_trato(tmp_path):
    from actions.relationship import set_user_name, set_formato_trato, get_relationship
    fake_file = tmp_path / "relationship.json"
    with patch("actions.relationship.RELATIONSHIP_FILE", fake_file):
        set_user_name("Daniel")
        set_formato_trato("tratame de tú")
        state = get_relationship()
        assert state["user_name"] == "Daniel"
        assert state["formato_trato"] == "tratame de tú"


def test_add_note_persists(tmp_path):
    from actions.relationship import add_note, get_relationship
    fake_file = tmp_path / "relationship.json"
    with patch("actions.relationship.RELATIONSHIP_FILE", fake_file):
        add_note("proyecto", "el sistema de Eris")
        assert get_relationship()["notes"]["proyecto"] == "el sistema de Eris"


def test_remember_moment_caps_at_30(tmp_path):
    from actions.relationship import remember_moment, get_relationship
    fake_file = tmp_path / "relationship.json"
    with patch("actions.relationship.RELATIONSHIP_FILE", fake_file):
        for i in range(40):
            remember_moment(f"momento {i}")
        moments = get_relationship()["important_moments"]
        assert len(moments) == 30
        assert moments[-1]["text"] == "momento 39"


def test_remember_moment_ignores_empty(tmp_path):
    from actions.relationship import remember_moment, get_relationship
    fake_file = tmp_path / "relationship.json"
    with patch("actions.relationship.RELATIONSHIP_FILE", fake_file):
        remember_moment("   ")
        assert get_relationship()["important_moments"] == []


def test_inject_empty_when_no_data(tmp_path):
    from actions.relationship import inject_relationship
    fake_file = tmp_path / "relationship.json"
    with patch("actions.relationship.RELATIONSHIP_FILE", fake_file):
        assert inject_relationship() == ""


def test_inject_includes_apodo(tmp_path):
    from actions.relationship import set_apodo, set_user_name, inject_relationship
    fake_file = tmp_path / "relationship.json"
    with patch("actions.relationship.RELATIONSHIP_FILE", fake_file):
        set_user_name("Daniel")
        set_apodo("Mi rey")
        result = inject_relationship()
        assert "[RELACIÓN" in result
        assert "Mi rey" in result
        assert "Daniel" in result


def test_tool_status_empty_shows_hint(tmp_path):
    from actions.relationship import relationship
    fake_file = tmp_path / "relationship.json"
    with patch("actions.relationship.RELATIONSHIP_FILE", fake_file):
        result = relationship({"action": "status"})
        assert "RELACIÓN CON EL USUARIO" in result
        assert "Aún no sé mucho" in result


def test_tool_set_apodo(tmp_path):
    from actions.relationship import relationship, get_relationship
    fake_file = tmp_path / "relationship.json"
    with patch("actions.relationship.RELATIONSHIP_FILE", fake_file):
        result = relationship({"action": "set_apodo", "apodo": "capi"})
        assert "capi" in result
        assert get_relationship()["apodo"] == "capi"


def test_tool_remember(tmp_path):
    from actions.relationship import relationship, get_relationship
    fake_file = tmp_path / "relationship.json"
    with patch("actions.relationship.RELATIONSHIP_FILE", fake_file):
        result = relationship({"action": "remember", "text": "Cerramos la feature"})
        assert "guardado" in result
        assert get_relationship()["important_moments"][0]["text"] == "Cerramos la feature"


def test_tool_unknown_action_returns_help(tmp_path):
    from actions.relationship import relationship
    fake_file = tmp_path / "relationship.json"
    with patch("actions.relationship.RELATIONSHIP_FILE", fake_file):
        result = relationship({"action": "banana"})
        assert "Acciones de relación" in result
