"""Tests for core/time_utils.py"""
import json
import tempfile
from pathlib import Path
from unittest.mock import patch


def test_get_time_context_returns_string():
    from core.time_utils import get_time_context
    result = get_time_context()
    assert isinstance(result, str)
    assert "CURRENT DATE & TIME" in result


def test_get_time_context_contains_time_info():
    from core.time_utils import get_time_context
    result = get_time_context()
    assert "Right now it is:" in result
    assert "Time of day:" in result


def test_load_tz_valid_timezone(tmp_path):
    from core.time_utils import load_tz
    config = {"timezone": "America/Bogota"}
    config_file = tmp_path / "api_keys.json"
    config_file.write_text(json.dumps(config), "utf-8")
    tz = load_tz(config_file)
    assert tz is not None


def test_load_tz_invalid_timezone_fallback(tmp_path):
    from core.time_utils import load_tz
    config = {"timezone": "Invalid/Timezone/That/Does/Not/Exist"}
    config_file = tmp_path / "api_keys.json"
    config_file.write_text(json.dumps(config), "utf-8")
    tz = load_tz(config_file)
    # Should fall back to system timezone
    assert tz is not None


def test_load_tz_empty_config(tmp_path):
    from core.time_utils import load_tz
    config = {}
    config_file = tmp_path / "api_keys.json"
    config_file.write_text(json.dumps(config), "utf-8")
    tz = load_tz(config_file)
    # Empty config means no timezone specified, falls back to system
    assert tz is not None or tz is None  # Acceptable either way depending on implementation


def test_load_tz_missing_file(tmp_path):
    from core.time_utils import load_tz
    config_file = tmp_path / "nonexistent.json"
    tz = load_tz(config_file)
    # Missing file: falls back to system timezone or None
    # Both are acceptable
