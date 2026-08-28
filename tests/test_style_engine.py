"""Tests for core/style_engine.py"""
import json
import tempfile
from pathlib import Path
from unittest.mock import patch


def test_load_defaults_on_missing_file(tmp_path):
    from core.style_engine import _load
    fake_file = tmp_path / "eris_style.json"
    with patch("core.style_engine._STYLE_FILE", fake_file):
        style = _load()
    assert "identidad" in style
    assert "auto_suficiencia" in style
    assert style["auto_suficiencia"]["min_intentos"] == 3
    assert style["identidad"]["trato"] == "usted"


def test_load_preserves_existing_identidad(tmp_path):
    from core.style_engine import _load
    fake_file = tmp_path / "eris_style.json"
    fake_file.write_text(json.dumps({"identidad": {"trato": "tú", "descripcion": "x"}}), "utf-8")
    with patch("core.style_engine._STYLE_FILE", fake_file):
        style = _load()
    assert style["identidad"]["trato"] == "tú"
    # Los defaults se completan
    assert "voz" in style


def test_inject_style_has_rules(tmp_path):
    from core.style_engine import inject_style
    fake_file = tmp_path / "eris_style.json"
    with patch("core.style_engine._STYLE_FILE", fake_file):
        text = inject_style()
    assert "[ESTILO" in text
    assert "Auto-suficiencia" in text
    assert "mil" in text.lower() or "intentos" in text


def test_get_saludo_picks_bucket(tmp_path):
    from core.style_engine import get_saludo
    fake_file = tmp_path / "eris_style.json"
    with patch("core.style_engine._STYLE_FILE", fake_file):
        assert get_saludo(9)   # manana
        assert get_saludo(15)  # tarde
        assert get_saludo(2)   # madrugada


def test_get_saludo_rotates(tmp_path):
    from core.style_engine import get_saludo, _load, _save
    fake_file = tmp_path / "eris_style.json"
    with patch("core.style_engine._STYLE_FILE", fake_file):
        # Añadir una segunda frase a la franja 'manana' para que la rotación tenga 2 opciones
        style = _load()
        style["voz"]["saludos"]["manana"].append("Segundo saludo de prueba.")
        _save(style)
        first = get_saludo(9)
        second = get_saludo(9)
        third = get_saludo(9)
    assert len({first, second, third}) == 2  # rota entre las frases de la franja


def test_get_despedida_returns_string(tmp_path):
    from core.style_engine import get_despedida
    fake_file = tmp_path / "eris_style.json"
    with patch("core.style_engine._STYLE_FILE", fake_file):
        desp = get_despedida()
    assert isinstance(desp, str)
    assert len(desp) > 0


def test_tool_status(tmp_path):
    from core.style_engine import eris_style
    fake_file = tmp_path / "eris_style.json"
    with patch("core.style_engine._STYLE_FILE", fake_file):
        result = eris_style({"action": "status"})
    assert "ESTILO DE ERIS" in result
    assert "Auto-suficiencia" in result


def test_tool_set_trato_persists(tmp_path):
    from core.style_engine import eris_style, _load
    fake_file = tmp_path / "eris_style.json"
    with patch("core.style_engine._STYLE_FILE", fake_file):
        result = eris_style({"action": "set_trato", "trato": "tú"})
        assert "tú" in result
        assert _load()["identidad"]["trato"] == "tú"


def test_tool_set_intentos_clamps(tmp_path):
    from core.style_engine import eris_style, _load
    fake_file = tmp_path / "eris_style.json"
    with patch("core.style_engine._STYLE_FILE", fake_file):
        eris_style({"action": "set_intentos", "value": "99"})
        assert _load()["auto_suficiencia"]["min_intentos"] == 10
        eris_style({"action": "set_intentos", "value": "0"})
        assert _load()["auto_suficiencia"]["min_intentos"] == 1


def test_tool_add_frase(tmp_path):
    from core.style_engine import eris_style, _load
    fake_file = tmp_path / "eris_style.json"
    with patch("core.style_engine._STYLE_FILE", fake_file):
        result = eris_style({"action": "add_frase", "lista": "despedidas", "text": "Chao."})
        assert "agregada" in result
        assert "Chao." in _load()["voz"]["despedidas"]


def test_tool_unknown_action_returns_help(tmp_path):
    from core.style_engine import eris_style
    fake_file = tmp_path / "eris_style.json"
    with patch("core.style_engine._STYLE_FILE", fake_file):
        result = eris_style({"action": "banana"})
    assert "Acciones de estilo" in result
