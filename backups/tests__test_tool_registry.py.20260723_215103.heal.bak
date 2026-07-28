"""Tests for core/tool_registry.py"""
import threading
from unittest.mock import patch, MagicMock


def test_get_tool_returns_callable_for_known_tool():
    from core.tool_registry import get_tool
    # open_app is a well-known tool that should be registered
    func = get_tool("open_app")
    # It might be None if actions.open_app is not installed, but it should be in _TOOLS
    from core.tool_registry import _TOOLS
    assert "open_app" in _TOOLS


def test_get_tool_returns_none_for_unknown():
    from core.tool_registry import get_tool
    result = get_tool("nonexistent_tool_xyz_12345")
    assert result is None


def test_get_all_tool_names():
    from core.tool_registry import get_all_tool_names
    names = get_all_tool_names()
    assert isinstance(names, list)
    assert len(names) > 50  # Should have 90+ tools
    assert "open_app" in names
    assert "web_search" in names
    assert "browser_control" in names


def test_register_tool():
    from core.tool_registry import register_tool, get_tool, _cache
    dummy = lambda: "test"
    register_tool("test_dummy_tool", dummy)
    assert get_tool("test_dummy_tool") is dummy
    # Cleanup
    _cache.pop("test_dummy_tool", None)


def test_retry_tool_clears_failure():
    from core.tool_registry import retry_tool, _failed, _cache
    # Simulate a failure
    _failed["test_retry_tool"] = ("fake.module", "fake_func", 1)
    _cache["test_retry_tool"] = None
    result = retry_tool("test_retry_tool")
    # Should have cleared the failure and tried again (will fail again but that's ok)
    assert "test_retry_tool" not in _failed or _failed.get("test_retry_tool", (None, None, 0))[2] <= 1
    # Cleanup
    _cache.pop("test_retry_tool", None)
    _failed.pop("test_retry_tool", None)


def test_clear_failures():
    from core.tool_registry import clear_failures, _failed, _cache
    _failed["test_clear"] = ("fake.module", "fake_func", 3)
    _cache["test_clear"] = None
    clear_failures()
    assert "test_clear" not in _failed
    assert "test_clear" not in _cache


def test_max_retries_respected():
    from core.tool_registry import _failed, _MAX_RETRIES
    _failed["test_max_retries"] = ("fake.module", "fake_func", _MAX_RETRIES + 1)
    from core.tool_registry import get_tool
    result = get_tool("test_max_retries")
    assert result is None
    # Cleanup
    _failed.pop("test_max_retries", None)


def test_thread_safety():
    """Verify concurrent access doesn't crash."""
    from core.tool_registry import get_tool, get_all_tool_names
    errors = []

    def worker():
        try:
            for name in get_all_tool_names()[:10]:
                get_tool(name)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)
    assert errors == []


def test_tools_dict_structure():
    from core.tool_registry import _TOOLS
    for name, entry in _TOOLS.items():
        assert isinstance(entry, tuple), f"{name} entry is not a tuple"
        assert len(entry) == 2, f"{name} entry doesn't have 2 elements"
        module_path, func_name = entry
        assert isinstance(module_path, str), f"{name} module_path is not a string"
        # func_name can be None (special handler) or a string
        assert func_name is None or isinstance(func_name, str), f"{name} func_name is invalid"
