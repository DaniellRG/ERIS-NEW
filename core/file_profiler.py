"""
file_profiler.py — Perfil completo de archivos del proyecto.

Analiza archivos y genera perfil detallado:
  - Tech stack usado por archivo
  - Complejidad ciclomática
  - Dependencias (imports, imports propios)
  - Calidad (comentarios, docstrings, type hints)
  - Tamaño y métricas de línea
  - Archivos más complejos / problemáticos
"""
from __future__ import annotations

import ast
import json
import time
import re
from pathlib import Path
from collections import defaultdict

_BASE = Path(__file__).resolve().parent.parent


def profile_file(file_path: str) -> dict:
    """Genera perfil completo de un archivo."""
    p = Path(file_path)
    if not p.exists():
        return {"error": "File not found: %s" % file_path}

    try:
        content = p.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        return {"error": "Cannot read: %s" % str(e)}

    lines = content.split("\n")
    stat = p.stat()

    profile = {
        "file": str(p.relative_to(_BASE)) if _BASE in p.parents else str(p),
        "size_bytes": stat.st_size,
        "size_kb": round(stat.st_size / 1024, 1),
        "total_lines": len(lines),
        "blank_lines": sum(1 for l in lines if not l.strip()),
        "comment_lines": sum(1 for l in lines if l.strip().startswith("#")),
        "code_lines": sum(1 for l in lines if l.strip() and not l.strip().startswith("#")),
        "max_line_length": max((len(l) for l in lines), default=0),
        "avg_line_length": round(sum(len(l) for l in lines) / max(1, len(lines)), 1),
    }

    # Analizar imports
    imports = []
    stdlib_imports = []
    third_party_imports = []
    local_imports = []

    stdlib_modules = {
        "os", "sys", "json", "time", "pathlib", "re", "collections",
        "datetime", "typing", "hashlib", "shutil", "gc", "functools",
        "itertools", "operator", "abc", "enum", "dataclasses", "contextlib",
        "io", "math", "random", "string", "textwrap", "threading", "subprocess",
    }

    for line in lines:
        stripped = line.strip()
        m = re.match(r"^(?:from|import)\s+(\S+)", stripped)
        if m:
            mod = m.group(1).split(".")[0]
            imports.append(mod)
            if mod in stdlib_modules:
                stdlib_imports.append(mod)
            elif mod.startswith(".") or mod in ("core", "actions", "plugins"):
                local_imports.append(mod)
            else:
                third_party_imports.append(mod)

    profile["imports"] = list(set(imports))
    profile["stdlib_count"] = len(set(stdlib_imports))
    profile["third_party_count"] = len(set(third_party_imports))
    profile["local_count"] = len(set(local_imports))

    # Analizar AST si es Python
    if p.suffix == ".py":
        ast_info = _analyze_ast(content, p)
        profile.update(ast_info)

    # Detectar tech stack
    profile["tech_stack"] = _detect_tech_stack(imports, content)

    # Score de calidad
    profile["quality_score"] = _calculate_quality_score(profile, lines)

    return profile


def _analyze_ast(content: str, path: Path) -> dict:
    """Análisis AST del código."""
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return {"parse_error": True}

    classes = []
    functions = []
    has_type_hints = False
    has_docstrings = False
    complexity = 0

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            methods = [n.name for n in ast.iter_child_nodes(node) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            classes.append({
                "name": node.name,
                "methods": len(methods),
                "line": node.lineno,
            })
        elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            # Complejidad ciclomática básica
            func_complexity = 1
            for child in ast.walk(node):
                if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                    func_complexity += 1
                elif isinstance(child, ast.BoolOp):
                    func_complexity += len(child.values) - 1

            functions.append({
                "name": node.name,
                "line": node.lineno,
                "args": len(node.args.args),
                "complexity": func_complexity,
                "has_docstring": bool(ast.get_docstring(node)),
            })
            complexity += func_complexity

            # Type hints
            for arg in node.args.args:
                if arg.annotation:
                    has_type_hints = True
                    break

            # Docstrings
            if ast.get_docstring(node):
                has_docstrings = True

    return {
        "class_count": len(classes),
        "function_count": len(functions),
        "total_complexity": complexity,
        "avg_complexity": round(complexity / max(1, len(functions)), 1),
        "max_function_complexity": max((f["complexity"] for f in functions), default=0),
        "has_type_hints": has_type_hints,
        "has_docstrings": has_docstrings,
        "classes": classes[:10],
        "complex_functions": [
            {"name": f["name"], "complexity": f["complexity"]}
            for f in sorted(functions, key=lambda x: x["complexity"], reverse=True)[:5]
            if f["complexity"] > 5
        ],
    }


def _detect_tech_stack(imports: list[str], content: str) -> list[str]:
    """Detecta tecnologías usadas."""
    stack = []
    tech_map = {
        "flask": "Flask", "django": "Django", "fastapi": "FastAPI",
        "requests": "requests", "aiohttp": "aiohttp",
        "numpy": "NumPy", "pandas": "Pandas", "matplotlib": "Matplotlib",
        "sklearn": "scikit-learn", "tensorflow": "TensorFlow", "torch": "PyTorch",
        "selenium": "Selenium", "playwright": "Playwright",
        "pytest": "pytest", "unittest": "unittest",
        "sqlalchemy": "SQLAlchemy", "sqlite3": "SQLite",
        "redis": "Redis", "celery": "Celery",
        "chromadb": "ChromaDB", "sentence_transformers": "SentenceTransformers",
        "pydantic": "Pydantic", "httpx": "httpx",
        "PIL": "Pillow", "cv2": "OpenCV",
        "pyautogui": "PyAutoGUI", "psutil": "psutil",
        "mutagen": "Mutagen", "pygame": "Pygame",
        "docx": "python-docx", "openpyxl": "openpyxl",
    }
    import_set = set(imports)
    for mod, name in tech_map.items():
        if mod in import_set:
            stack.append(name)

    if "async def" in content or "await " in content:
        stack.append("asyncio")
    if "class " in content and "Model" in content:
        stack.append("OOP")

    return list(set(stack))


def _calculate_quality_score(profile: dict, lines: list[str]) -> int:
    """Calcula score de calidad (0-100)."""
    score = 50  # Base

    # +10 si tiene type hints
    if profile.get("has_type_hints"):
        score += 10

    # +10 si tiene docstrings
    if profile.get("has_docstrings"):
        score += 10

    # +5 si tiene comentarios decentes
    if profile["comment_lines"] > 0:
        score += 5

    # +5 si el promedio de complejidad es bajo
    if profile.get("avg_complexity", 0) <= 3:
        score += 5

    # -10 si hay funciones muy complejas
    if profile.get("max_function_complexity", 0) > 15:
        score -= 10

    # -5 si las líneas son muy largas
    if profile.get("max_line_length", 0) > 120:
        score -= 5

    # +5 si tiene imports locales (bueno = modular)
    if profile.get("local_count", 0) > 0:
        score += 5

    return max(0, min(100, score))


def profile_project(directories: list[str] = None) -> dict:
    """Perfila todo el proyecto."""
    dirs = directories or [str(_BASE / "core"), str(_BASE / "actions")]
    profiles = []

    for d in dirs:
        p = Path(d)
        if not p.exists():
            continue
        for f in p.rglob("*.py"):
            try:
                profiles.append(profile_file(str(f)))
            except Exception:
                continue

    # Resumen
    total_lines = sum(p.get("total_lines", 0) for p in profiles)
    total_functions = sum(p.get("function_count", 0) for p in profiles)
    total_classes = sum(p.get("class_count", 0) for p in profiles)
    total_complexity = sum(p.get("total_complexity", 0) for p in profiles)

    avg_quality = (
        sum(p.get("quality_score", 0) for p in profiles) / max(1, len(profiles))
    )

    # Top archivos problemáticos
    complex_files = sorted(
        [p for p in profiles if p.get("total_complexity", 0) > 10],
        key=lambda x: x.get("total_complexity", 0),
        reverse=True,
    )[:5]

    return {
        "total_files": len(profiles),
        "total_lines": total_lines,
        "total_functions": total_functions,
        "total_classes": total_classes,
        "total_complexity": total_complexity,
        "avg_quality_score": round(avg_quality, 1),
        "complex_files": [
            {"file": f["file"], "complexity": f["total_complexity"], "lines": f["total_lines"]}
            for f in complex_files
        ],
    }


def format_profile(profile: dict) -> str:
    """Formatea perfil de archivo."""
    if "error" in profile:
        return profile["error"]

    lines = [
        "Perfil: %s" % profile.get("file", "?"),
        "  Tamaño: %.1f KB, %d líneas (%d código, %d comentarios, %d blank)" % (
            profile.get("size_kb", 0), profile.get("total_lines", 0),
            profile.get("code_lines", 0), profile.get("comment_lines", 0),
            profile.get("blank_lines", 0)),
        "  Complejidad total: %d, promedio: %.1f" % (
            profile.get("total_complexity", 0), profile.get("avg_complexity", 0)),
        "  Clases: %d, Funciones: %d" % (
            profile.get("class_count", 0), profile.get("function_count", 0)),
        "  Quality score: %d/100" % profile.get("quality_score", 0),
        "  Imports: %d stdlib, %d third-party, %d local" % (
            profile.get("stdlib_count", 0), profile.get("third_party_count", 0),
            profile.get("local_count", 0)),
    ]
    if profile.get("tech_stack"):
        lines.append("  Stack: %s" % ", ".join(profile["tech_stack"]))
    if profile.get("complex_functions"):
        lines.append("  Funciones complejas:")
        for f in profile["complex_functions"]:
            lines.append("    ⚠ %s (complejidad: %d)" % (f["name"], f["complexity"]))
    return "\n".join(lines)
