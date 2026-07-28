"""Tests for core/emotional_state.py"""
import json
import time
import tempfile
from pathlib import Path
from unittest.mock import patch


def test_default_neutral_has_all_dimensions():
    from core.emotional_state import _DEFAULT_NEUTRAL
    required = {"happiness", "energy", "confidence", "curiosity", "patience", "gratitude", "boredom"}
    assert required.issubset(set(_DEFAULT_NEUTRAL.keys()))
    for v in _DEFAULT_NEUTRAL.values():
        assert 0.0 <= v <= 1.0


def test_load_returns_defaults_on_missing_file(tmp_path):
    from core.emotional_state import _load, _DEFAULT_NEUTRAL
    fake_file = tmp_path / "emotional_state.json"
    with patch("core.emotional_state._STATE_FILE", fake_file):
        state = _load()
    for k in _DEFAULT_NEUTRAL:
        assert k in state
    assert "last_update" in state


def test_load_preserves_existing_state(tmp_path):
    from core.emotional_state import _load
    fake_file = tmp_path / "emotional_state.json"
    custom = {"happiness": 0.99, "energy": 0.1, "confidence": 0.5, "curiosity": 0.5,
              "patience": 0.5, "gratitude": 0.5, "boredom": 0.5, "last_update": time.time()}
    fake_file.write_text(json.dumps(custom), "utf-8")
    with patch("core.emotional_state._STATE_FILE", fake_file):
        state = _load()
    assert state["happiness"] == 0.99
    assert state["energy"] == 0.1


def test_save_creates_file(tmp_path):
    from core.emotional_state import _save
    fake_file = tmp_path / "sub" / "emotional_state.json"
    with patch("core.emotional_state._STATE_FILE", fake_file):
        _save({"happiness": 0.5, "last_update": time.time()})
    assert fake_file.exists()


def test_decay_does_not_apply_within_60s():
    from core.emotional_state import _apply_decay, _DEFAULT_NEUTRAL
    state = {**_DEFAULT_NEUTRAL, "last_update": time.time()}
    original = state["happiness"]
    state = _apply_decay(state)
    assert state["happiness"] == original


def test_decay_applies_after_60s():
    from core.emotional_state import _apply_decay, _DEFAULT_NEUTRAL
    state = {**_DEFAULT_NEUTRAL, "happiness": 0.9, "last_update": time.time() - 600}
    state = _apply_decay(state)
    assert state["happiness"] < 0.9
    assert state["happiness"] > _DEFAULT_NEUTRAL["happiness"]


def test_get_emotional_state_no_disk_write_when_no_change(tmp_path):
    from core.emotional_state import get_emotional_state
    fake_file = tmp_path / "emotional_state.json"
    # Write a state that was just updated (no decay needed)
    state = {"happiness": 0.5, "energy": 0.5, "confidence": 0.5, "curiosity": 0.5,
             "patience": 0.5, "gratitude": 0.5, "boredom": 0.5, "last_update": time.time()}
    fake_file.write_text(json.dumps(state), "utf-8")
    mtime_before = fake_file.stat().st_mtime
    with patch("core.emotional_state._STATE_FILE", fake_file):
        result = get_emotional_state()
    mtime_after = fake_file.stat().st_mtime
    # File should NOT have been rewritten since no decay was needed
    assert mtime_before == mtime_after
    assert "happiness" in result


def test_adjust_emotion_clamps():
    from core.emotional_state import adjust_emotion, get_emotional_state
    with tempfile.TemporaryDirectory() as td:
        fake_file = Path(td) / "emotional_state.json"
        with patch("core.emotional_state._STATE_FILE", fake_file):
            adjust_emotion("happiness", 10.0)  # Way above 1.0
            state = get_emotional_state()
            assert state["happiness"] == 1.0

            adjust_emotion("happiness", -10.0)  # Way below 0.0
            state = get_emotional_state()
            assert state["happiness"] == 0.0


def test_react_to_success_boosts_happiness():
    from core.emotional_state import react_to_success, get_emotional_state
    with tempfile.TemporaryDirectory() as td:
        fake_file = Path(td) / "emotional_state.json"
        with patch("core.emotional_state._STATE_FILE", fake_file):
            before = get_emotional_state()
            react_to_success()
            after = get_emotional_state()
            assert after["happiness"] >= before["happiness"]


def test_react_to_failure_drops_happiness():
    from core.emotional_state import react_to_failure, get_emotional_state
    with tempfile.TemporaryDirectory() as td:
        fake_file = Path(td) / "emotional_state.json"
        with patch("core.emotional_state._STATE_FILE", fake_file):
            before = get_emotional_state()
            react_to_failure()
            after = get_emotional_state()
            assert after["happiness"] <= before["happiness"]


def test_mood_description_returns_string():
    from core.emotional_state import get_mood_description
    desc = get_mood_description()
    assert isinstance(desc, str)
    assert len(desc) > 0


def test_tone_instruction_returns_string():
    from core.emotional_state import get_tone_instruction
    tone = get_tone_instruction()
    assert isinstance(tone, str)


def test_emotional_state_tool_status():
    from core.emotional_state import emotional_state_tool
    result = emotional_state_tool({"action": "status"})
    assert "[EMOTIONAL STATE]" in result


def test_emotional_state_tool_adjust():
    from core.emotional_state import emotional_state_tool
    result = emotional_state_tool({"action": "adjust", "dimension": "happiness", "delta": 0.1})
    assert "Adjusted" in result


def test_emotional_state_tool_tone():
    from core.emotional_state import emotional_state_tool
    result = emotional_state_tool({"action": "tone"})
    assert isinstance(result, str)


def test_no_dead_default_state():
    """Verify _DEFAULT_STATE was removed (dead code)."""
    import core.emotional_state as mod
    assert not hasattr(mod, "_DEFAULT_STATE"), "_DEFAULT_STATE should have been removed"
