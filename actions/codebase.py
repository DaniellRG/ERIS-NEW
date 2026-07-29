"""
actions/codebase.py — Full codebase analysis for ERIS.
Understands project structure, provides statistics, search and navigation.
"""
import ast
import os
from pathlib import Path
from collections import defaultdict

_PROJECT_DIR = Path(__file__).resolve().parent.parent

def codebase(parameters: dict, player=None) -> str:
    action = (parameters.get("action") or "").lower()
    target = parameters.get("target") or parameters.get("archivo") or ""
    pattern = parameters.get("pattern") or parameters.get("patron") or ""
    detail = parameters.get("detail") or parameters.get("detalle") or "summary"

    if player:
        player.write_log(f"📊 Codebase: {action}")

    if action in ("stats", "estadisticas"):
        return _stats(target, player)

    elif action in ("tree", "arbol"):
        return _tree(target, player)

    elif action in ("functions", "funciones"):
        return _list_functions(target, player)

    elif action in ("classes", "clases"):
        return _list_classes(target, player)

    elif action in ("imports", "importaciones"):
        return _list_imports(target, player)

    elif action in ("search", "buscar"):
        return _search(pattern, target, player)

    elif action in ("deps", "dependencias"):
        return _dependency_graph(target, player)

    elif action in ("duplicates", "duplicados"):
        return _find_duplicates(target, player)

    elif action in ("structure", "estructura"):
        return _structure(target, player)

    elif action in ("unused", "no_usados"):
        return _find_unused(target, player)

    elif action in ("glob"):
        return _glob(pattern, player)

    elif action in ("grep", "buscar"):
        return _search(pattern, target, player)

    elif action == "summary":
        return _summary(player)

    else:
        actions = [
            "stats (target=)", "tree (target=)", "functions (target=)", "classes (target=)",
            "imports (target=)", "search (pattern=, target=)", "deps (target=)",
            "duplicates (target=)", "structure (target=)", "unused (target=)", "summary",
            "glob (pattern=)", "grep (pattern=)"
        ]
        return f"Acciones codebase: {', '.join(actions)}"


def _stats(target: str, player=None) -> str:
    """Statistics for a file or the whole project."""
    try:
        all_py = _get_files(target)
        total_files = len(all_py)
        total_lines = 0
        total_functions = 0
        total_classes = 0
        sizes = []

        for f in all_py:
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    content = fh.read()
                lines = content.splitlines()
                total_lines += len(lines)
                sizes.append(len(content))
                tree = ast.parse(content)
                total_functions += sum(1 for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
                total_classes += sum(1 for n in ast.walk(tree) if isinstance(n, ast.ClassDef))
            except Exception:
                pass

        if target:
            return (
                f"📊 {Path(target).name if '/' not in target else target}\n"
                f"  Lineas: {total_lines:,}\n"
                f"  Funciones: {total_functions}\n"
                f"  Clases: {total_classes}"
            )

        avg_size = int(sum(sizes) / len(sizes)) if sizes else 0
        max_size = max(sizes) if sizes else 0

        return (
            f"📊 Codebase Stats\n"
            f"  Archivos .py: {total_files}\n"
            f"  Lineas totales: {total_lines:,}\n"
            f"  Funciones totales: {total_functions}\n"
            f"  Clases totales: {total_classes}\n"
            f"  Tamano promedio: {avg_size:,} bytes\n"
            f"  Archivo mas grande: {max_size:,} bytes"
        )
    except Exception as e:
        return f"Error: {str(e)[:200]}"


def _tree(target: str, player=None) -> str:
    """Directory tree of the project."""
    try:
        base = _PROJECT_DIR
        if target:
            base = _PROJECT_DIR / target
            if not base.exists():
                return f"No existe: {target}"

        lines = []
        _build_tree(base, "", lines, max_depth=3)
        return "\n".join(lines) if lines else "Vacio"
    except Exception as e:
        return f"Error: {str(e)[:200]}"


def _build_tree(path: Path, prefix: str, lines: list, max_depth: int = 3):
    if max_depth < 0:
        return
    try:
        items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
    except PermissionError:
        return

    for i, item in enumerate(items):
        is_last = i == len(items) - 1
        if item.name.startswith(".") or item.name == "__pycache__":
            continue
        if item.is_dir():
            lines.append(f"{prefix}{'└── ' if is_last else '├── '}{item.name}/")
            _build_tree(item, f"{prefix}{'    ' if is_last else '│   '}", lines, max_depth - 1)
        elif item.suffix == ".py" or item.suffix == ".json" or item.suffix == ".md":
            lines.append(f"{prefix}{'└── ' if is_last else '├── '}{item.name}")


def _list_functions(target: str, player=None) -> str:
    """List all functions in a file or project."""
    try:
        all_py = _get_files(target)
        results = []
        for f in all_py:
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    tree = ast.parse(fh.read())
                funcs = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
                if funcs:
                    rel = f.relative_to(_PROJECT_DIR)
                    results.append(f"{rel}: {', '.join(funcs[:20])}")
            except Exception:
                pass
        return "\n".join(results[:50]) if results else "No se encontraron funciones"
    except Exception as e:
        return f"Error: {str(e)[:200]}"


def _list_classes(target: str, player=None) -> str:
    """List all classes in a file or project."""
    try:
        all_py = _get_files(target)
        results = []
        for f in all_py:
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    tree = ast.parse(fh.read())
                classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
                if classes:
                    rel = f.relative_to(_PROJECT_DIR)
                    results.append(f"{rel}: {', '.join(classes)}")
            except Exception:
                pass
        return "\n".join(results[:30]) if results else "No se encontraron clases"
    except Exception as e:
        return f"Error: {str(e)[:200]}"


def _list_imports(target: str, player=None) -> str:
    """List all imports in a file or project."""
    try:
        all_py = _get_files(target)
        import_map = defaultdict(list)
        for f in all_py:
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    tree = ast.parse(fh.read())
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            import_map[alias.name].append(f.name)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            import_map[node.module].append(f.name)
            except Exception:
                pass

        results = []
        for mod, files in sorted(import_map.items()):
            results.append(f"{mod} -> {', '.join(Path(ff).name for ff in files[:5])}")
        return "\n".join(results[:50]) if results else "No se encontraron imports"
    except Exception as e:
        return f"Error: {str(e)[:200]}"


def _search(pattern: str, target: str, player=None) -> str:
    """Search for a pattern in codebase."""
    try:
        if not pattern:
            return "Necesito 'pattern' para buscar"
        all_py = _get_files(target)
        results = []
        for f in all_py:
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    for i, line in enumerate(fh, 1):
                        if pattern.lower() in line.lower():
                            rel = f.relative_to(_PROJECT_DIR)
                            results.append(f"{rel}:{i}  {line.strip()[:80]}")
            except Exception:
                pass

        if not results:
            return f"'{pattern}' no encontrado"
        lines = results[:40]
        if len(results) > 40:
            lines.append(f"... y {len(results) - 40} resultados mas")
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {str(e)[:200]}"


def _dependency_graph(target: str, player=None) -> str:
    """Show file dependencies (who imports what)."""
    try:
        all_py = _get_files(target)
        deps = {}
        for f in all_py:
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    tree = ast.parse(fh.read())
                imports = []
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.append(alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            imports.append(node.module)
                deps[f.name] = imports
            except Exception:
                deps[f.name] = ["(error parsing)"]

        results = []
        for fname, imports in sorted(deps.items()):
            if imports:
                results.append(f"{fname}: {', '.join(imports[:8])}")
        return "\n".join(results[:40]) if results else "No dependencies found"
    except Exception as e:
        return f"Error: {str(e)[:200]}"


def _find_duplicates(target: str, player=None) -> str:
    """Find potential duplicate functions."""
    try:
        all_py = _get_files(target)
        func_map = defaultdict(list)
        for f in all_py:
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    tree = ast.parse(fh.read())
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        func_map[node.name].append(f.name)
            except Exception:
                pass

        duplicates = {k: v for k, v in func_map.items() if len(v) > 1}
        if not duplicates:
            return "No se encontraron funciones duplicadas"
        results = []
        for name, files in sorted(duplicates.items()):
            results.append(f"{name}: {', '.join(Path(ff).name for ff in files)}")
        return "\n".join(results[:30])
    except Exception as e:
        return f"Error: {str(e)[:200]}"


def _structure(target: str, player=None) -> str:
    """Show directory structure with file sizes."""
    try:
        base = _PROJECT_DIR
        if target:
            base = _PROJECT_DIR / target
            if not base.exists():
                return f"No existe: {target}"

        lines = [f"📁 {base.name}"]
        total_size = 0
        total_files = 0

        for f in sorted(base.rglob("*.py")):
            try:
                size = f.stat().st_size
                total_size += size
                total_files += 1
                rel = f.relative_to(base)
                lines.append(f"  {rel.parent / f.name}  ({size:,} bytes)")
            except Exception:
                pass

        lines.append(f"\nTotal: {total_files} archivos, {total_size:,} bytes")
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {str(e)[:200]}"


def _find_unused(target: str, player=None) -> str:
    """Very basic unused code detection (functions defined but never called)."""
    try:
        all_py = _get_files(target)
        defined = set()
        called = set()
        for f in all_py:
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    tree = ast.parse(fh.read())
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        defined.add(node.name)
                    elif isinstance(node, ast.Call):
                        if isinstance(node.func, ast.Name):
                            called.add(node.func.id)
                        elif isinstance(node.func, ast.Attribute):
                            called.add(node.func.attr)
            except Exception:
                pass

        unused = defined - called
        unused = {u for u in unused if not u.startswith("_")}
        if not unused:
            return "No se encontraron funciones no utilizadas (revision basica)"
        return f"Posibles funciones no utilizadas: {', '.join(sorted(unused)[:30])}"
    except Exception as e:
        return f"Error: {str(e)[:200]}"


def _glob(pattern: str, player=None) -> str:
    """Find files matching a glob pattern."""
    try:
        if not pattern:
            return "Necesito 'pattern' (ej: **/*.py, **/*.html, actions/*.py)"
        from pathlib import Path
        base = _PROJECT_DIR
        matches = list(base.glob(pattern))
        if not matches:
            return f"No se encontraron archivos: {pattern}"
        lines = [f"Encontrados {len(matches)} archivos:"]
        for m in matches[:50]:
            lines.append(f"  {m.relative_to(base)}")
        if len(matches) > 50:
            lines.append(f"  ... y {len(matches) - 50} mas")
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {str(e)[:200]}"


def _summary(player=None) -> str:
    """Quick summary of the codebase."""
    try:
        all_py = list(_PROJECT_DIR.rglob("*.py"))
        total = len(all_py)
        total_lines = 0
        total_funcs = 0
        total_classes = 0
        dirs = set()

        for f in all_py:
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    content = fh.read()
                total_lines += len(content.splitlines())
                tree = ast.parse(content)
                total_funcs += sum(1 for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
                total_classes += sum(1 for n in ast.walk(tree) if isinstance(n, ast.ClassDef))
                dirs.add(f.parent)
            except Exception:
                pass

        return (
            f"📋 Codebase Summary\n"
            f"  Directorios: {len(dirs)}\n"
            f"  Archivos .py: {total}\n"
            f"  Lineas totales: {total_lines:,}\n"
            f"  Funciones: {total_funcs}\n"
            f"  Clases: {total_classes}\n"
            f"  Ruta: {_PROJECT_DIR}"
        )
    except Exception as e:
        return f"Error: {str(e)[:200]}"


def _get_files(target: str = "") -> list:
    """Get list of .py files, optionally filtered by target."""
    if target:
        path = _PROJECT_DIR / target
        if path.is_file() and path.suffix == ".py":
            return [path]
        elif path.is_dir():
            return list(path.rglob("*.py"))
        else:
            all_py = list(_PROJECT_DIR.rglob("*.py"))
            # Try fuzzy match
            target_lower = target.lower()
            return [f for f in all_py if target_lower in f.name.lower()]
    return list(_PROJECT_DIR.rglob("*.py"))
