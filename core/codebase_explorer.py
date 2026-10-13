"""
ERIS Codebase Explorer — Búsqueda profunda de código, análisis de arquitectura,
mapeo de dependencias, y comprensión de estructura de proyecto.

Capacidades:
- Búsqueda por patrón en archivos (grep)
- Búsqueda por nombre de archivo (glob)
- Análisis de imports/dependencias entre archivos
- Architecture map (qué módulos dependen de qué)
- File statistics (líneas, funciones, classes)
- Find definitions/references
"""
import os
import re
import ast
import json
import time
from pathlib import Path
from collections import defaultdict, Counter
from typing import Optional

_WORKSPACE = Path(os.environ.get("ERIS_WORKSPACE",
                                 str(Path(__file__).resolve().parent.parent)))


def _grep(pattern: str, path: str = None, include: str = None, exclude: str = None, max_results: int = 50) -> list:
    """Search file contents with regex."""
    search_path = Path(path) if path else _WORKSPACE
    results = []
    regex = re.compile(pattern, re.IGNORECASE)
    include_pat = re.compile(include) if include else None
    exclude_pat = re.compile(exclude) if exclude else None

    for root, dirs, files in os.walk(search_path):
        # Skip hidden dirs and common ignore dirs
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in
                   ("__pycache__", "node_modules", ".git", "venv", ".venv", "env", "chroma_db", "sandbox")]
        for fname in files:
            if not fname.endswith((".py", ".js", ".ts", ".json", ".md", ".txt", ".yaml", ".yml", ".toml", ".cfg")):
                continue
            if include_pat and not include_pat.search(fname):
                continue
            if exclude_pat and exclude_pat.search(fname):
                continue
            fpath = Path(root) / fname
            try:
                content = fpath.read_text(encoding="utf-8", errors="replace")
                for i, line in enumerate(content.split("\n"), 1):
                    if regex.search(line):
                        rel = fpath.relative_to(_WORKSPACE)
                        results.append({
                            "file": str(rel),
                            "line": i,
                            "content": line.rstrip()[:200],
                        })
                        if len(results) >= max_results:
                            return results
            except Exception:
                continue
    return results


def _glob_files(pattern: str, path: str = None, max_results: int = 50) -> list:
    """Find files by glob pattern."""
    search_path = Path(path) if path else _WORKSPACE
    matches = []
    for p in search_path.rglob(pattern):
        if any(skip in str(p) for skip in [".git", "__pycache__", "node_modules", ".venv", "venv", "chroma_db"]):
            continue
        matches.append({
            "file": str(p.relative_to(_WORKSPACE)),
            "size": p.stat().st_size if p.exists() else 0,
        })
        if len(matches) >= max_results:
            break
    return matches


def _analyze_imports(filepath: str) -> dict:
    """Analyze imports in a Python file."""
    try:
        content = Path(filepath).read_text(encoding="utf-8", errors="replace")
        imports = []
        local_imports = []
        external_imports = []

        for i, line in enumerate(content.split("\n"), 1):
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith("from "):
                imports.append({"line": i, "text": stripped})
                # Check if it's a local import
                if "from " in stripped:
                    mod = stripped.split("from ")[1].split(" import")[0].strip()
                else:
                    mod = stripped.split("import ")[1].split(".")[0].strip()
                if mod.startswith(".") or (Path(_WORKSPACE / mod.replace(".", "/")).exists() or
                    (Path(_WORKSPACE / mod.replace(".", "/") + ".py")).exists()):
                    local_imports.append(mod)
                else:
                    external_imports.append(mod)

        return {
            "total": len(imports),
            "local": local_imports,
            "external": external_imports,
            "imports": imports,
        }
    except Exception as e:
        return {"error": str(e)[:200]}


def _dependency_graph(path: str = None) -> dict:
    """Build a dependency graph of all Python files in the project."""
    search_path = Path(path) if path else _WORKSPACE
    graph = {}  # file -> [dependencies]

    for root, dirs, files in os.walk(search_path):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in
                   ("__pycache__", "node_modules", ".git", ".venv", "venv")]
        for fname in files:
            if not fname.endswith(".py"):
                continue
            fpath = Path(root) / fname
            rel = str(fpath.relative_to(_WORKSPACE))
            imports = _analyze_imports(str(fpath))
            graph[rel] = {
                "local_deps": imports.get("local", []),
                "external_deps": imports.get("external", []),
                "import_count": imports.get("total", 0),
            }
    return graph


def _find_definitions(name: str, path: str = None) -> list:
    """Find where a function/class/variable is defined."""
    pattern = rf"(def|class|async\s+def)\s+{re.escape(name)}\b"
    return _grep(pattern, path)


def _find_references(name: str, path: str = None) -> list:
    """Find all references to a name (excluding definitions)."""
    all_refs = _grep(rf"\b{re.escape(name)}\b", path)
    return [r for r in all_refs if "def " + name not in r["content"] and "class " + name not in r["content"]]


def _file_stats(filepath: str) -> dict:
    """Get statistics for a file."""
    try:
        content = Path(filepath).read_text(encoding="utf-8", errors="replace")
        lines = content.split("\n")
        code_lines = [l for l in lines if l.strip() and not l.strip().startswith("#") and not l.strip().startswith('"""') and not l.strip().startswith("'''")]
        functions = len(re.findall(r"^\s*(async\s+)?def\s+", content, re.MULTILINE))
        classes = len(re.findall(r"^\s*class\s+", content, re.MULTILINE))
        imports = len(re.findall(r"^\s*(import|from)\s+", content, re.MULTILINE))
        return {
            "total_lines": len(lines),
            "code_lines": len(code_lines),
            "blank_lines": len(lines) - len(code_lines),
            "functions": functions,
            "classes": classes,
            "imports": imports,
            "size_bytes": len(content.encode("utf-8")),
        }
    except Exception as e:
        return {"error": str(e)[:200]}


def _architecture_map(path: str = None) -> dict:
    """Generate a high-level architecture map."""
    search_path = Path(path) if path else _WORKSPACE
    dirs = {}
    total_files = 0
    total_lines = 0

    for root, dirnames, filenames in os.walk(search_path):
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in
                       ("__pycache__", "node_modules", ".git", ".venv", "venv", "chroma_db")]
        py_files = [f for f in filenames if f.endswith(".py")]
        if py_files:
            rel_dir = str(Path(root).relative_to(search_path))
            if rel_dir == ".":
                rel_dir = "(root)"
            code_lines = 0
            for f in py_files:
                try:
                    content = (Path(root) / f).read_text(encoding="utf-8", errors="replace")
                    code_lines += len([l for l in content.split("\n") if l.strip() and not l.strip().startswith("#")])
                except Exception:
                    pass
            dirs[rel_dir] = {
                "files": len(py_files),
                "code_lines": code_lines,
                "modules": [f.replace(".py", "") for f in py_files[:20]],
            }
            total_files += len(py_files)
            total_lines += code_lines

    # Find most-imported modules
    graph = _dependency_graph(path)
    import_count = Counter()
    for info in graph.values():
        for dep in info.get("local_deps", []):
            import_count[dep] += 1

    return {
        "directories": dirs,
        "total_py_files": total_files,
        "total_code_lines": total_lines,
        "most_imported": import_count.most_common(20),
        "total_modules": len(graph),
    }


def _module_one_liner(filepath: Path) -> str:
    """Primera línea útil de un módulo: el resumen del docstring, o el primer
    def/class si no hay docstring. Best effort, no rompe."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as fh:
            head = fh.read(4000)
    except Exception:
        return ""
    try:
        doc = ast.get_docstring(ast.parse(head))
        if doc:
            return doc.strip().splitlines()[0].strip()[:110]
    except Exception:
        pass
    for line in head.splitlines():
        s = line.strip()
        if s.startswith(("def ", "class ")):
            return s.rstrip(":").replace("_", " ")[:110]
    return ""


_SKIP_DIRS = {"__pycache__", "node_modules", ".git", ".venv", "venv",
              "chroma_db", ".mypy_cache", ".pytest_cache", "dist", "build",
              "site-packages"}


def _project_tree(path: str = None, max_files: int = 60) -> list:
    """Árbol de módulos .py con UNA línea de qué hace cada uno (2.3)."""
    root = Path(path) if path else _WORKSPACE
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames
                       if not d.startswith(".") and d not in _SKIP_DIRS]
        for f in sorted(filenames):
            if not f.endswith(".py"):
                continue
            fp = Path(dirpath) / f
            try:
                rel = str(fp.relative_to(root))
            except Exception:
                rel = str(fp)
            out.append({"file": rel, "summary": _module_one_liner(fp)})
            if len(out) >= max_files:
                return out
    return out


def codebase_explorer(parameters: dict = None, player=None) -> str:
    """Tool entry point."""
    params = parameters or {}
    action = params.get("action", "grep").lower()

    if action == "grep":
        pattern = params.get("pattern", "")
        if not pattern:
            return "Necesito 'pattern'."
        path = params.get("path")
        include = params.get("include")
        exclude = params.get("exclude")
        max_r = int(params.get("limit", 50))
        results = _grep(pattern, path, include, exclude, max_r)
        if not results:
            return f"Sin resultados para '{pattern}'."
        return f"Resultados ({len(results)}):\n" + "\n".join(
            f"  {r['file']}:{r['line']}: {r['content']}" for r in results
        )

    elif action == "glob":
        pattern = params.get("pattern", "")
        if not pattern:
            return "Necesito 'pattern' (ej: '**/*.py', 'core/*.py')."
        results = _glob_files(pattern, params.get("path"))
        if not results:
            return f"Sin archivos para '{pattern}'."
        return f"Archivos ({len(results)}):\n" + "\n".join(
            f"  {r['file']} ({r['size']} bytes)" for r in results
        )

    elif action == "imports":
        filepath = params.get("file", "")
        if not filepath:
            return "Necesito 'file'."
        result = _analyze_imports(filepath)
        if "error" in result:
            return result["error"]
        output = f"Imports en {Path(filepath).name}: {result['total']}\n"
        if result["local"]:
            output += f"  Locales: {', '.join(result['local'])}\n"
        if result["external"]:
            output += f"  Externos: {', '.join(result['external'][:15])}\n"
        return output

    elif action == "graph":
        path = params.get("path")
        graph = _dependency_graph(path)
        if not graph:
            return "Sin archivos Python encontrados."
        output = f"Dependency graph: {len(graph)} módulos\n\n"
        # Show modules with most local deps
        by_deps = sorted(graph.items(), key=lambda x: len(x[1]["local_deps"]), reverse=True)
        for mod, info in by_deps[:15]:
            if info["local_deps"]:
                output += f"  {mod} → {', '.join(info['local_deps'][:5])}\n"
        return output

    elif action == "definitions":
        name = params.get("name", "")
        if not name:
            return "Necesito 'name'."
        results = _find_definitions(name, params.get("path"))
        if not results:
            return f"Sin definiciones de '{name}'."
        return f"Definiciones de '{name}' ({len(results)}):\n" + "\n".join(
            f"  {r['file']}:{r['line']}: {r['content']}" for r in results
        )

    elif action == "references":
        name = params.get("name", "")
        if not name:
            return "Necesito 'name'."
        results = _find_references(name, params.get("path"))
        if not results:
            return f"Sin referencias a '{name}'."
        return f"Referencias a '{name}' ({len(results)}):\n" + "\n".join(
            f"  {r['file']}:{r['line']}: {r['content']}" for r in results[:30]
        )

    elif action == "stats":
        filepath = params.get("file", "")
        if not filepath:
            return "Necesito 'file'."
        result = _file_stats(filepath)
        if "error" in result:
            return result["error"]
        return (f"Stats de {Path(filepath).name}:\n"
                f"  Líneas: {result['total_lines']} (código: {result['code_lines']}, blank: {result['blank_lines']})\n"
                f"  Funciones: {result['functions']}, Clases: {result['classes']}, Imports: {result['imports']}\n"
                f"  Tamaño: {result['size_bytes']} bytes")

    elif action == "architecture":
        path = params.get("path")
        result = _architecture_map(path)
        output = f"Architecture: {result['total_py_files']} archivos, {result['total_code_lines']} líneas de código\n\n"
        for dir_name, info in sorted(result["directories"].items(), key=lambda x: x[1]["code_lines"], reverse=True)[:15]:
            output += f"  {dir_name}/: {info['files']} archivos, {info['code_lines']} líneas\n"
        if result["most_imported"]:
            output += "\nMás importados:\n"
            for mod, count in result["most_imported"][:10]:
                output += f"  {mod}: {count} imports\n"
        return output

    elif action == "map":
        path = params.get("path")
        max_files = int(params.get("limit", 60) or 60)
        tree = _project_tree(path, max_files)
        if not tree:
            return "Sin archivos Python para mapear."
        out = f"Mapa del proyecto ({len(tree)} archivos, una línea por archivo):\n"
        out += "\n".join(f"  {t['file']}: {t['summary']}" if t["summary"]
                         else f"  {t['file']}" for t in tree)
        return out

    return f"Acción '{action}' no reconocida. Usa: grep, glob, imports, graph, definitions, references, stats, architecture, map"
