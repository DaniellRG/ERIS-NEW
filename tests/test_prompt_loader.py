"""Tests for core/prompt_loader.py"""
from unittest.mock import patch
from pathlib import Path


def test_load_system_prompt_returns_string():
    from core.prompt_loader import load_system_prompt
    result = load_system_prompt()
    assert isinstance(result, str)
    assert len(result) > 100


def test_load_system_prompt_fallback():
    from core.prompt_loader import load_system_prompt
    with patch("pathlib.Path.read_text", side_effect=FileNotFoundError):
        result = load_system_prompt()
    # Should return fallback prompt
    assert "ERIS" in result
    assert "mujer" in result.lower() or "ser" in result.lower()
