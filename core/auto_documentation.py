"""
auto_documentation.py — Generación automática de documentación.

Analiza código modificado y genera documentación relevante:
  - Docstrings para funciones sin documentar
  - README de secciones afectadas
  - Changelog de cambios
  - Notas de migración si hay breaking changes
"""
from __future__ import annotations

import re
import ast
from pathlib import Path

try:
    from core.agent_architecture import _chat
except ImportError:
    _chat = None


def analyze_code_for_docs(file_path: str) -> dict:
    """Analiza un archivo de código y detecta qué necesita documentación.

    Returns:
        dict con: undocumented_functions, undocumented_classes, file_path, suggestions
    """
    path = Path(file_path)
    if not path.exists():
        return {"error": f"Archivo no encontrado: {file_path}"}

    try:
        content = path.read_text(encoding="utf-8")
    except Exception as e:
        return {"error": f"Error leyendo: {e}"}

    undocumented = []
    undocumented_classes = []

    try:
        tree = ast.parse(content)
    except SyntaxError:
        return {"error": "Syntax error en el archivo"}

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            docstring = ast.get_docstring(node)
            if not docstring:
                undocumented.append({
                    "name": node.name,
                    "line": node.lineno,
                    "args": [arg.arg for arg in node.args.args if arg.arg != "self"],
                    "type": "function",
                })
        elif isinstance(node, ast.ClassDef):
            docstring = ast.get_docstring(node)
            if not docstring:
                undocumented_classes.append({
                    "name": node.name,
                    "line": node.lineno,
                    "type": "class",
                })

    return {
        "file_path": str(file_path),
        "undocumented_functions": undocumented,
        "undocumented_classes": undocumented_classes,
        "total_undocumented": len(undocumented) + len(undocumented_classes),
    }


def generate_docstring(function_info: dict, file_context: str = "") -> str:
    """Genera un docstring para una función basándose en su nombre y contexto."""
    name = function_info.get("name", "")
    args = function_info.get("args", [])

    # Generar docstring descriptivo basándose en el nombre
    words = re.sub(r"([A-Z])", r" \1", name).lower().split()
    description = " ".join(words)

    docstring_parts = ['    """' + description.capitalize() + "."]
    if args:
        docstring_parts.append("\n    Args:")
        for arg in args:
            docstring_parts.append("        %s: Descripcion de %s." % (arg, arg))

    docstring_parts.append('    """')
    return "\n".join(docstring_parts)


def generate_changelog(changes: list[dict]) -> str:
    """Genera un changelog a partir de una lista de cambios.

    Args:
        changes: [{file, type, description}] donde type es added/modified/fixed/removed

    Returns:
        Changelog en formato markdown
    """
    if not changes:
        return "No hay cambios documentados."

    lines = ["## Changelog\n"]
    by_type = {}
    for change in changes:
        t = change.get("type", "modified")
        if t not in by_type:
            by_type[t] = []
        by_type[t].append(change)

    type_headers = {
        "added": "### Added",
        "modified": "### Modified",
        "fixed": "### Fixed",
        "removed": "### Removed",
    }

    for change_type in ["added", "fixed", "modified", "removed"]:
        if change_type in by_type:
            lines.append(type_headers.get(change_type, f"### {change_type.title()}"))
            for change in by_type[change_type]:
                file_name = Path(change.get("file", "")).name
                desc = change.get("description", "Sin descripción")
                lines.append(f"- {file_name}: {desc}")
            lines.append("")

    return "\n".join(lines)


def suggest_migration(changes: list[dict]) -> str | None:
    """Detecta breaking changes y sugiere migración."""
    breaking_indicators = [
        "renamed", "removed", "deleted", "deprecated", "breaking",
        "signature changed", "parameter removed",
    ]

    breaking = []
    for change in changes:
        desc = change.get("description", "").lower()
        for indicator in breaking_indicators:
            if indicator in desc:
                breaking.append(change)
                break

    if not breaking:
        return None

    lines = ["⚠️ Breaking changes detectados. Migración sugerida:\n"]
    for b in breaking:
        lines.append(f"- {Path(b.get('file', '')).name}: {b.get('description', '')}")
    lines.append("\nRevisar cada cambio y actualizar código dependiente.")
    return "\n".join(lines)
