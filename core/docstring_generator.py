"""Auto-docstring generator for Eris."""
import re
import ast
import json
from pathlib import Path

def _extract_functions(filepath: str) -> list:
    try:
        content = Path(filepath).read_text(encoding="utf-8")
        tree = ast.parse(content)
        functions = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args = [a.arg for a in node.args.args if a.arg != "self"]
                docstring = ast.get_docstring(node)
                functions.append({
                    "name": node.name,
                    "args": args,
                    "has_docstring": docstring is not None,
                    "line": node.lineno,
                    "is_async": isinstance(node, ast.AsyncFunctionDef),
                })
        return functions
    except Exception as e:
        return [{"error": str(e)[:200]}]

def _generate_docstring(func_name: str, args: list) -> str:
    lines = ['    """TODO: Describe what this function does.', '']
    if args:
        lines.append('    Args:')
        for a in args:
            lines.append('        {} (TODO: describe parameter)'.format(a))
        lines.append('')
    lines.append('    Returns:')
    lines.append('        TODO: Describe return value')
    lines.append('    """')
    return '\n'.join(lines)

def docstring_generator_tool(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = params.get("action", "status")
    if action == "status":
        return json.dumps({"status": "ready"})
    elif action == "analyze":
        filepath = params.get("file", "")
        if not filepath or not Path(filepath).exists():
            return json.dumps({"error": "File not found"})
        functions = _extract_functions(filepath)
        missing = [f for f in functions if not f.get("has_docstring") and "name" in f]
        return json.dumps({"file": filepath, "functions": len(functions), "missing_docstrings": len(missing), "details": functions})
    elif action == "generate":
        filepath = params.get("file", "")
        if not filepath or not Path(filepath).exists():
            return json.dumps({"error": "File not found"})
        functions = _extract_functions(filepath)
        missing = [f for f in functions if not f.get("has_docstring") and "name" in f]
        generated = []
        for f in missing:
            docstring = _generate_docstring(f["name"], f["args"])
            generated.append({"name": f["name"], "line": f["line"], "docstring": docstring})
        return json.dumps({"file": filepath, "generated": len(generated), "details": generated})
    elif action == "scan_directory":
        directory = params.get("path", ".")
        results = []
        try:
            for py_file in Path(directory).rglob("*.py"):
                if ".venv" in py_file.parts or "__pycache__" in py_file.parts:
                    continue
                functions = _extract_functions(str(py_file))
                missing = sum(1 for f in functions if not f.get("has_docstring") and "name" in f)
                if missing > 0:
                    results.append({"file": str(py_file), "total": len(functions), "missing": missing})
        except Exception as e:
            return json.dumps({"error": str(e)[:300]})
        return json.dumps({"files_with_missing": len(results), "details": results[:30]})
    return json.dumps({"error": "Unknown action"})
