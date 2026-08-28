"""
core/ast_editor.py — AST-aware code editing for ERIS.

Provides safe code modifications using Python's AST module.
Supports: find function/class, insert before/after, replace node,
          add import, remove import, analyze file structure.
"""
from __future__ import annotations

import ast
import os
import re
from pathlib import Path
from typing import Optional


class ASTEditResult:
    def __init__(self, success: bool, message: str, changes: list | None = None):
        self.success = success
        self.message = message
        self.changes = changes or []


def analyze_file(filepath: str) -> dict:
    """Analyze a Python file's structure: imports, functions, classes, etc."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            source = f.read()
        tree = ast.parse(source)
    except SyntaxError as e:
        return {"error": f"Syntax error: {e}"}
    except Exception as e:
        return {"error": str(e)}

    result = {
        "imports": [],
        "functions": [],
        "classes": [],
        "top_level_code": [],
        "line_count": source.count("\n") + 1,
    }

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            else:
                names = [f"from {node.module} import ..."]
            result["imports"].append({
                "names": names,
                "line": node.lineno,
                "end_line": getattr(node, "end_lineno", node.lineno),
            })
        elif isinstance(node, ast.FunctionDef):
            result["functions"].append({
                "name": node.name,
                "line": node.lineno,
                "end_line": getattr(node, "end_lineno", node.lineno),
                "args": [a.arg for a in node.args.args],
                "decorators": [_unparse(d) for d in node.decorator_list],
            })
        elif isinstance(node, ast.AsyncFunctionDef):
            result["functions"].append({
                "name": node.name,
                "line": node.lineno,
                "end_line": getattr(node, "end_lineno", node.lineno),
                "args": [a.arg for a in node.args.args],
                "async": True,
                "decorators": [_unparse(d) for d in node.decorator_list],
            })
        elif isinstance(node, ast.ClassDef):
            methods = [n.name for n in ast.iter_child_nodes(node) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            result["classes"].append({
                "name": node.name,
                "line": node.lineno,
                "end_line": getattr(node, "end_lineno", node.lineno),
                "bases": [_unparse(b) for b in node.bases],
                "methods": methods,
            })
        else:
            result["top_level_code"].append({
                "type": type(node).__name__,
                "line": node.lineno,
            })

    return result


def find_node(filepath: str, name: str, node_type: str = "any") -> Optional[dict]:
    """Find a function, class, or variable by name in a file."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            source = f.read()
        tree = ast.parse(source)
    except Exception:
        return None

    for node in ast.walk(tree):
        if node_type in ("any", "function") and isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == name:
                return {"name": name, "line": node.lineno, "end_line": getattr(node, "end_lineno", node.lineno), "type": "function"}
        if node_type in ("any", "class") and isinstance(node, ast.ClassDef):
            if node.name == name:
                return {"name": name, "line": node.lineno, "end_line": getattr(node, "end_lineno", node.lineno), "type": "class"}
        if node_type in ("any", "import") and isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""]
            if name in names:
                return {"name": name, "line": node.lineno, "end_line": getattr(node, "end_lineno", node.lineno), "type": "import"}
    return None


def insert_import(filepath: str, import_line: str) -> ASTEditResult:
    """Insert an import statement at the correct position in a file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        return ASTEditResult(False, f"Error leyendo archivo: {e}")

    source = "".join(lines)
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return ASTEditResult(False, f"Syntax error en el archivo: {e}")

    # Find last import line
    last_import_line = 0
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            last_import_line = getattr(node, "end_lineno", node.lineno)

    # Check if import already exists
    import_name = import_line.strip().split(" import ")[0].replace("from ", "").strip()
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == import_name:
                    return ASTEditResult(True, f"Import '{import_name}' ya existe (línea {node.lineno})")
        elif isinstance(node, ast.ImportFrom):
            if node.module == import_name:
                return ASTEditResult(True, f"Import '{import_name}' ya existe (línea {node.lineno})")

    # Insert after last import (or at top if no imports)
    insert_at = last_import_line if last_import_line > 0 else 0
    import_text = import_line.strip() + "\n"

    # Add blank line after imports if inserting at end of imports
    if last_import_line > 0 and insert_at < len(lines):
        if lines[insert_at].strip() != "":
            import_text += "\n"

    lines.insert(insert_at, import_text)

    with open(filepath, "w", encoding="utf-8") as f:
        f.writelines(lines)

    return ASTEditResult(True, f"Import insertado en línea {insert_at + 1}")


def remove_import(filepath: str, module_name: str) -> ASTEditResult:
    """Remove an import statement by module name."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        return ASTEditResult(False, f"Error leyendo archivo: {e}")

    source = "".join(lines)
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return ASTEditResult(False, f"Syntax error: {e}")

    removed = False
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == module_name:
                    start = node.lineno - 1
                    end = getattr(node, "end_lineno", node.lineno)
                    del lines[start:end]
                    removed = True
                    break
        elif isinstance(node, ast.ImportFrom):
            if node.module == module_name:
                start = node.lineno - 1
                end = getattr(node, "end_lineno", node.lineno)
                del lines[start:end]
                removed = True

    if removed:
        with open(filepath, "w", encoding="utf-8") as f:
            f.writelines(lines)
        return ASTEditResult(True, f"Import '{module_name}' eliminado")
    return ASTEditResult(False, f"Import '{module_name}' no encontrado")


def safe_edit(filepath: str, old_text: str, new_text: str) -> ASTEditResult:
    """Edit with AST validation — verifies the result parses correctly."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
    except Exception as e:
        return ASTEditResult(False, f"Error leyendo archivo: {e}")

    if old_text not in source:
        return ASTEditResult(False, f"Texto no encontrado en el archivo")

    count = source.count(old_text)
    if count > 1:
        return ASTEditResult(False, f"El texto aparece {count} veces — no puedo hacer edit seguro")

    new_source = source.replace(old_text, new_text, 1)

    # Validate AST
    try:
        ast.parse(new_source)
    except SyntaxError as e:
        return ASTEditResult(False, f"El edit genera syntax error: {e}")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_source)

    return ASTEditResult(True, "Edit aplicado y validado con AST")


def get_source_segment(filepath: str, start_line: int, end_line: int) -> str:
    """Get source code lines from a file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
        return "".join(lines[start_line - 1:end_line])
    except Exception as e:
        return f"Error: {e}"


def _unparse(node) -> str:
    try:
        return ast.unparse(node)
    except Exception:
        return "..."
