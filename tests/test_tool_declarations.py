"""Tests for core/tool_declarations.py"""


def test_tool_declarations_is_list():
    from core.tool_declarations import TOOL_DECLARATIONS
    assert isinstance(TOOL_DECLARATIONS, list)


def test_tool_declarations_not_empty():
    from core.tool_declarations import TOOL_DECLARATIONS
    assert len(TOOL_DECLARATIONS) > 50


def test_all_tools_have_required_fields():
    from core.tool_declarations import TOOL_DECLARATIONS
    for tool in TOOL_DECLARATIONS:
        assert "name" in tool, f"Tool missing 'name': {tool}"
        assert "description" in tool, f"Tool missing 'description': {tool}"
        assert "parameters" in tool, f"Tool missing 'parameters': {tool}"
        assert isinstance(tool["name"], str)
        assert isinstance(tool["description"], str)
        assert isinstance(tool["parameters"], dict)


def test_tool_names_are_unique():
    from core.tool_declarations import TOOL_DECLARATIONS
    names = [t["name"] for t in TOOL_DECLARATIONS]
    assert len(names) == len(set(names)), f"Duplicate tool names: {[n for n in names if names.count(n) > 1]}"


def test_known_tools_present():
    from core.tool_declarations import TOOL_DECLARATIONS
    names = {t["name"] for t in TOOL_DECLARATIONS}
    expected = {"open_app", "web_search", "browser_control", "computer_control",
                "file_controller", "whatsapp", "screen_vision"}
    assert expected.issubset(names)


def test_parameters_have_type():
    from core.tool_declarations import TOOL_DECLARATIONS
    for tool in TOOL_DECLARATIONS:
        params = tool["parameters"]
        assert "type" in params, f"{tool['name']} parameters missing 'type'"
        assert params["type"].upper() == "OBJECT", f"{tool['name']} parameters type is not OBJECT"
