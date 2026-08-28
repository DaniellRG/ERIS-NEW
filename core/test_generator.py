# -*- coding: utf-8 -*-
from __future__ import annotations

import ast
import re
import subprocess
import sys
from pathlib import Path

_DATA_DIR = Path(r"D:\Eris_Source\data")
_TESTS_DIR = Path(r"D:\Eris_Source\tests\generated")
_PROJECT = Path(r"D:\Eris_Source")


def test_generator(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = params.get("action", "scan").lower()

    if action == "scan":
        return _scan(params)
    elif action == "generate":
        return _generate(params)
    elif action == "run":
        return _run(params)
    elif action == "coverage":
        return _coverage(params)
    elif action == "suggestions":
        return _suggestions(params)

    return (
        "Acciones disponibles: scan, generate, run, coverage, suggestions"
    )


def _resolve_file(params: dict) -> Path | None:
    file_path = params.get("file_path", "").strip()
    module_name = params.get("module_name", "").strip()

    if file_path:
        p = Path(file_path)
        if p.exists():
            return p.resolve()
        alt = _PROJECT / file_path
        if alt.exists():
            return alt.resolve()

    if module_name:
        parts = module_name.split(".")
        if len(parts) >= 2:
            mod_path = _PROJECT / Path(*parts[:-1]) / (parts[-1] + ".py")
            if mod_path.exists():
                return mod_path.resolve()
            act_path = _PROJECT / "actions" / (parts[-1] + ".py")
            if act_path.exists():
                return act_path.resolve()

    return None


def _parse_file(file_path: Path) -> dict | None:
    try:
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content)
    except Exception:
        return None

    functions = []
    classes = []

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("_"):
                continue
            info = _analyze_function(node)
            functions.append(info)
        elif isinstance(node, ast.ClassDef):
            cls_info = {"name": node.name, "line": node.lineno, "methods": []}
            for item in ast.iter_child_nodes(node):
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if item.name.startswith("_") and item.name != "__init__":
                        continue
                    info = _analyze_function(item)
                    info["class"] = node.name
                    cls_info["methods"].append(info)
                    functions.append(info)
            classes.append(cls_info)

    return {
        "functions": functions,
        "classes": classes,
        "source": content,
        "tree": tree,
    }


def _analyze_function(node) -> dict:
    args_list = []
    defaults = {}
    has_player = False

    for arg in node.args.args:
        if arg.arg in ("self", "cls"):
            continue
        if arg.arg == "player":
            has_player = True
            continue
        args_list.append(arg.arg)

    num_defaults = len(node.args.defaults)
    if num_defaults > 0:
        arg_names = [a.arg for a in node.args.args if a.arg not in ("self", "cls", "player")]
        offset = len(arg_names) - num_defaults
        for i, default in enumerate(node.args.defaults):
            idx = offset + i
            if 0 <= idx < len(arg_names):
                defaults[arg_names[idx]] = ast.dump(default)

    return_annotation = None
    if node.returns:
        try:
            return_annotation = ast.unparse(node.returns)
        except Exception:
            return_annotation = str(ast.dump(node.returns))

    param_types = {}
    for arg in node.args.args:
        if arg.arg in ("self", "cls", "player"):
            continue
        if arg.annotation:
            try:
                param_types[arg.arg] = ast.unparse(arg.annotation)
            except Exception:
                param_types[arg.arg] = str(ast.dump(arg.annotation))

    docstring = ast.get_docstring(node) or ""
    raises = False
    for child in ast.walk(node):
        if isinstance(child, ast.Raise):
            raises = True
            break

    has_dict_param = any(
        param_types.get(a, "") in ("dict", "Dict", "dict | None", "Optional[dict]")
        for a in args_list
    )

    return {
        "name": node.name,
        "line": node.lineno,
        "args": args_list,
        "defaults": defaults,
        "param_types": param_types,
        "return_type": return_annotation,
        "has_player": has_player,
        "docstring": docstring,
        "raises": raises,
        "has_dict_param": has_dict_param,
        "is_async": isinstance(node, ast.AsyncFunctionDef),
        "class": None,
    }


def _scan(params: dict) -> str:
    file_path = _resolve_file(params)
    if not file_path:
        return "Archivo no encontrado. Usa 'file_path' o 'module_name'"

    parsed = _parse_file(file_path)
    if not parsed:
        return "Error al parsear: {}".format(file_path)

    functions = parsed["functions"]
    classes = parsed["classes"]

    test_dir = _PROJECT / "tests"
    existing_tests = set()
    if test_dir.exists():
        for tf in test_dir.glob("**/test_*.py"):
            try:
                content = tf.read_text(encoding="utf-8")
                for fn in functions:
                    if fn["name"] in content:
                        existing_tests.add(fn["name"])
            except Exception:
                pass

    lines = [
        "═══ ANÁLISIS DE: {} ═══".format(file_path.name),
        "",
        "  Funciones públicas: {}".format(len(functions)),
        "  Clases: {}".format(len(classes)),
        "  Ya testeadas: {}".format(len(existing_tests)),
        "  Sin tests: {}".format(len(functions) - len(existing_tests)),
        "",
    ]

    if functions:
        lines.append("  Funciones:")
        for fn in functions:
            has_test = "✓" if fn["name"] in existing_tests else "✗"
            args_str = ", ".join(fn["args"]) if fn["args"] else "(sin params)"
            ret = " → {}".format(fn["return_type"]) if fn["return_type"] else ""
            lines.append("    {} {} {}{}  [línea {}]".format(
                has_test, fn["name"], args_str, ret, fn["line"]
            ))
            if fn["raises"]:
                lines.append("      ⚠ Puede lanzar excepciones")
            if fn["has_dict_param"]:
                lines.append("      ⚠ Parámetro dict detectado (action pattern)")

    if classes:
        lines.append("")
        lines.append("  Clases:")
        for cls in classes:
            lines.append("    {} [línea {}] — {} métodos".format(
                cls["name"], cls["line"], len(cls["methods"])
            ))
            for m in cls["methods"][:5]:
                lines.append("      - {}".format(m["name"]))

    tests_to_gen = [f for f in functions if f["name"] not in existing_tests]
    if tests_to_gen:
        lines.append("")
        lines.append("  Tests a generar: {}".format(", ".join(f["name"] for f in tests_to_gen)))

    return "\n".join(lines)


def _generate_test_code(func_info: dict, module_name: str) -> list:
    name = func_info["name"]
    args = func_info["args"]
    param_types = func_info.get("param_types", {})
    defaults = func_info.get("defaults", {})
    has_dict = func_info.get("has_dict_param", False)
    raises = func_info.get("raises", False)
    return_type = func_info.get("return_type")
    cls_name = func_info.get("class")

    tests = []

    if has_dict:
        tests.extend(_gen_dict_tests(name, args, param_types, module_name, cls_name))
    else:
        tests.extend(_gen_basic_tests(name, args, param_types, defaults, module_name, cls_name))

    if raises:
        tests.append(_gen_exception_test(name, args, param_types, module_name, cls_name))

    if return_type and "None" in return_type:
        tests.append(_gen_none_return_test(name, args, param_types, module_name, cls_name))

    return tests


def _gen_dict_tests(name, args, param_types, module_name, cls_name):
    tests = []

    if cls_name:
        call_prefix = cls_name + "."
    else:
        call_prefix = ""

    tests.append(
        "def test_{name}_basic():\n"
        '    """Test básico para {call}{name}."""\n'
        "    result = {call}{name}(parameters={{}}, player=None)\n"
        "    assert result is not None\n"
        '    assert isinstance(result, str)\n'.format(
            name=name, call=call_prefix,
        )
    )

    tests.append(
        "def test_{name}_action_list():\n"
        '    """Test acción list/status."""\n'
        "    result = {call}{name}(parameters={{\"action\": \"list\"}}, player=None)\n"
        "    assert result is not None\n"
        '    assert isinstance(result, str)\n'.format(
            name=name, call=call_prefix,
        )
    )

    tests.append(
        "def test_{name}_empty_params():\n"
        '    """Test con parámetros vacíos."""\n'
        "    result = {call}{name}(parameters=None, player=None)\n"
        "    assert result is not None\n".format(
            name=name, call=call_prefix,
        )
    )

    return tests


def _gen_basic_tests(name, args, param_types, defaults, module_name, cls_name):
    tests = []

    if cls_name:
        call_prefix = cls_name + "."
    else:
        call_prefix = ""

    if not args:
        tests.append(
            "def test_{name}_basic():\n"
            '    """Test básico para {call}{name}."""\n'
            "    result = {call}{name}()\n"
            "    assert result is not None\n".format(
                name=name, call=call_prefix,
            )
        )
        return tests

    test_values = _generate_test_values(args, param_types, defaults)
    for tv_name, tv_args in test_values:
        args_str = ", ".join(tv_args) if tv_args else ""
        tests.append(
            "def test_{name}_{tv}():\n"
            '    """Test {tv} para {call}{name}."""\n'
            "    result = {call}{name}({args})\n"
            "    assert result is not None\n".format(
                name=name, tv=tv_name, call=call_prefix,
                args=args_str,
            )
        )

    return tests


def _generate_test_values(args, param_types, defaults):
    values = []

    str_args = []
    for a in args:
        ptype = param_types.get(a, "")
        if "str" in ptype.lower():
            str_args.append(("\"{}\"", a))
        elif "int" in ptype.lower() or "float" in ptype.lower():
            str_args.append(("0", a))
        elif "dict" in ptype.lower() or "list" in ptype.lower():
            str_args.append(("{{}}" if "dict" in ptype.lower() else "[]", a))
        elif "bool" in ptype.lower():
            str_args.append(("True", a))
        elif "path" in a.lower() or "file" in a.lower():
            str_args.append(("\"test.txt\"", a))
        elif "name" in a.lower():
            str_args.append(("\"test_name\"", a))
        elif "query" in a.lower() or "text" in a.lower() or "content" in a.lower():
            str_args.append(("\"test input\"", a))
        else:
            str_args.append(("\"default\"", a))

    base_args = [val.format() for val, _ in str_args]
    values.append(("basic", base_args))

    str_idx = [i for i, a in enumerate(args) if "str" in param_types.get(a, "").lower()]
    if str_idx:
        empty_args = list(base_args)
        for idx in str_idx:
            empty_args[idx] = "\"\""
        values.append(("empty", empty_args))

    int_idx = [i for i, a in enumerate(args) if "int" in param_types.get(a, "").lower()]
    if int_idx:
        neg_args = list(base_args)
        for idx in int_idx:
            neg_args[idx] = "-1"
        values.append(("negative", neg_args))

    large_args = list(base_args)
    for i, a in enumerate(args):
        if "str" in param_types.get(a, "").lower():
            large_args[i] = "\"{}\"".format("x" * 1000)
    if large_args != base_args:
        values.append(("large", large_args))

    return values


def _gen_exception_test(name, args, param_types, module_name, cls_name):
    call_prefix = cls_name + "." if cls_name else ""
    return (
        "def test_{name}_exception_handling():\n"
        '    """Test que {name} maneja excepciones correctamente."""\n'
        "    try:\n"
        "        {call}{name}(parameters={{\"invalid_key\": True}}, player=None)\n"
        "    except (TypeError, ValueError, KeyError, Exception):\n"
        "        pass\n".format(
            name=name, call=call_prefix,
        )
    )


def _gen_none_return_test(name, args, param_types, module_name, cls_name):
    call_prefix = cls_name + "." if cls_name else ""
    return (
        "def test_{name}_returns_none():\n"
        '    """Test que {name} retorna None."""\n'
        "    result = {call}{name}(parameters={{}}, player=None)\n"
        "    assert result is None\n".format(
            name=name, call=call_prefix,
        )
    )


def _generate(params: dict) -> str:
    file_path = _resolve_file(params)
    if not file_path:
        return "Archivo no encontrado. Usa 'file_path' o 'module_name'"

    parsed = _parse_file(file_path)
    if not parsed:
        return "Error al parsear: {}".format(file_path)

    functions = parsed["functions"]
    if not functions:
        return "No hay funciones públicas para generar tests en {}".format(file_path.name)

    module_name = file_path.stem
    rel_path = str(file_path.relative_to(_PROJECT)) if _PROJECT in file_path.parents else file_path.name

    test_lines = [
        "# -*- coding: utf-8 -*-",
        '"""Tests automáticos para {}"""'.format(rel_path),
        "import pytest",
        "",
    ]

    imports = set()
    for fn in functions:
        cls_name = fn.get("class")
        if cls_name:
            imports.add("from {} import {}".format(
                rel_path.replace("\\", ".").replace("/", ".").replace(".py", ""),
                cls_name
            ))
        else:
            imports.add("from {} import {}".format(
                rel_path.replace("\\", ".").replace("/", ".").replace(".py", ""),
                fn["name"]
            ))

    for imp in sorted(imports):
        test_lines.append(imp)
    test_lines.append("")

    total_tests = 0
    for fn in functions:
        gen_tests = _generate_test_code(fn, rel_path.replace("\\", ".").replace("/", ".").replace(".py", ""))
        total_tests += len(gen_tests)
        for test_code in gen_tests:
            test_lines.append(test_code)
            test_lines.append("")

    output = params.get("output", "")
    if output:
        out_path = Path(output)
    else:
        out_path = _TESTS_DIR / "test_{}.py".format(module_name)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    test_content = "\n".join(test_lines)
    out_path.write_text(test_content, encoding="utf-8")

    lines = [
        "═══ TESTS GENERADOS ═══",
        "",
        "  Módulo: {}".format(rel_path),
        "  Funciones: {}".format(len(functions)),
        "  Tests generados: {}".format(total_tests),
        "  Archivo: {}".format(out_path),
        "",
        "  Para ejecutar:",
        "    python -m pytest {} -v".format(out_path),
    ]
    return "\n".join(lines)


def _run(params: dict) -> str:
    file_path = _resolve_file(params)
    if not file_path:
        return "Archivo no encontrado. Usa 'file_path' o 'module_name'"

    gen_result = _generate(params)
    if "Error" in gen_result or "no encontrado" in gen_result:
        return gen_result

    module_name = file_path.stem
    test_file = _TESTS_DIR / "test_{}.py".format(module_name)

    if not test_file.exists():
        return "Error: archivo de test no generado: {}".format(test_file)

    lines = [
        "═══ EJECUTANDO TESTS ═══",
        "",
    ]

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(test_file), "-v", "--tb=short", "-q"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(_PROJECT),
        )

        output = result.stdout or ""
        stderr = result.stderr or ""

        if output:
            lines.append(output.strip())

        passed = len(re.findall(r"PASSED", output))
        failed = len(re.findall(r"FAILED", output))
        skipped = len(re.findall(r"SKIPPED", output))
        errors = len(re.findall(r"ERROR", output))

        lines.append("")
        lines.append("  Resumen:")
        lines.append("    ✓ Pasaron:  {}".format(passed))
        lines.append("    ✗ Fallaron: {}".format(failed))
        lines.append("    ○ Saltados: {}".format(skipped))
        lines.append("    ! Errores:  {}".format(errors))

        if stderr and failed:
            lines.append("")
            lines.append("  Errores:")
            for line in stderr.strip().split("\n")[:10]:
                lines.append("    {}".format(line))

    except subprocess.TimeoutExpired:
        lines.append("  Timeout: tests tardaron más de 120 segundos")
    except Exception as e:
        lines.append("  Error ejecutando tests: {}".format(str(e)))

    return "\n".join(lines)


def _coverage(params: dict) -> str:
    lines = [
        "═══ COBERTURA DE TESTS ═══",
        "",
    ]

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--tb=short", "-q", "--co", "-q"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(_PROJECT),
        )
        output = result.stdout or ""
        collected = len(re.findall(r"::", output))
        lines.append("  Tests colectados: {}".format(collected))
    except Exception:
        lines.append("  No se pudieron colectar tests")

    modules_with_tests = set()
    modules_without_tests = set()

    test_dir = _PROJECT / "tests"
    if test_dir.exists():
        for tf in test_dir.glob("**/test_*.py"):
            try:
                content = tf.read_text(encoding="utf-8")
                for match in re.findall(r"from\s+(\S+)\s+import", content):
                    modules_with_tests.add(match)
            except Exception:
                pass

    gen_dir = _TESTS_DIR
    if gen_dir.exists():
        for tf in gen_dir.glob("test_*.py"):
            try:
                content = tf.read_text(encoding="utf-8")
                for match in re.findall(r"from\s+(\S+)\s+import", content):
                    modules_with_tests.add(match)
            except Exception:
                pass

    core_dir = _PROJECT / "core"
    actions_dir = _PROJECT / "actions"

    for d in [core_dir, actions_dir]:
        if not d.exists():
            continue
        for py_file in d.glob("*.py"):
            if py_file.name.startswith("_"):
                continue
            parts = []
            if d.name == "core":
                parts.append("core")
            elif d.name == "actions":
                parts.append("actions")
            parts.append(py_file.stem)
            module_path = ".".join(parts)
            if module_path not in modules_with_tests:
                modules_without_tests.add(module_path)

    lines.append("")
    lines.append("  Módulos sin tests: {}".format(len(modules_without_tests)))

    if modules_without_tests:
        lines.append("")
        top_untested = sorted(modules_without_tests)[:20]
        for m in top_untested:
            lines.append("    ✗ {}".format(m))
        if len(modules_without_tests) > 20:
            lines.append("    ... y {} más".format(len(modules_without_tests) - 20))

    total = len(modules_with_tests) + len(modules_without_tests)
    coverage_pct = (len(modules_with_tests) / max(total, 1)) * 100
    lines.append("")
    lines.append("  Cobertura: {:.1f}% ({}/{})".format(
        coverage_pct, len(modules_with_tests), total
    ))

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "--tb=short", "-q"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(_PROJECT),
        )
        output = result.stdout or ""
        passed = len(re.findall(r"PASSED", output))
        failed = len(re.findall(r"FAILED", output))
        skipped = len(re.findall(r"SKIPPED", output))

        lines.append("")
        lines.append("  Última ejecución:")
        lines.append("    ✓ Pasaron:  {}".format(passed))
        lines.append("    ✗ Fallaron: {}".format(failed))
        lines.append("    ○ Saltados: {}".format(skipped))
    except Exception:
        pass

    return "\n".join(lines)


def _suggestions(params: dict) -> str:
    lines = [
        "═══ SUGERENCIAS DE TESTING ═══",
        "",
    ]

    targets = []

    core_dir = _PROJECT / "core"
    actions_dir = _PROJECT / "actions"

    test_dir = _PROJECT / "tests"
    modules_with_tests = set()
    if test_dir.exists():
        for tf in test_dir.glob("**/test_*.py"):
            try:
                content = tf.read_text(encoding="utf-8")
                for match in re.findall(r"from\s+(\S+)\s+import", content):
                    modules_with_tests.add(match)
            except Exception:
                pass

    for d in [core_dir, actions_dir]:
        if not d.exists():
            continue
        for py_file in d.glob("*.py"):
            if py_file.name.startswith("_"):
                continue
            prefix = "core" if d.name == "core" else "actions"
            module_path = "{}.{}".format(prefix, py_file.stem)
            if module_path in modules_with_tests:
                continue

            try:
                content = py_file.read_text(encoding="utf-8")
                tree = ast.parse(content)
                pub_funcs = [
                    n.name for n in ast.iter_child_nodes(tree)
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and not n.name.startswith("_")
                ]
                if pub_funcs:
                    targets.append({
                        "file": py_file,
                        "module": module_path,
                        "functions": pub_funcs,
                    })
            except Exception:
                pass

    if not targets:
        lines.append("  ¡Todos los módulos tienen tests! No hay sugerencias.")
        return "\n".join(lines)

    targets.sort(key=lambda t: len(t["functions"]), reverse=True)

    lines.append("  Prioridad ALTA (muchas funciones sin tests):")
    for t in targets[:10]:
        lines.append("    {} — {} funciones públicas".format(
            t["module"], len(t["functions"])
        ))
        for fn in t["functions"][:3]:
            lines.append("      - {}".format(fn))
        if len(t["functions"]) > 3:
            lines.append("      ... y {} más".format(len(t["functions"]) - 3))

    lines.append("")
    lines.append("  Para generar tests para un módulo:")
    lines.append("    test_generator(action='generate', file_path='actions/foo.py')")
    lines.append("    test_generator(action='run', file_path='core/bar.py')")

    high_priority = [t for t in targets if len(t["functions"]) >= 5]
    if high_priority:
        lines.append("")
        lines.append("  Recomendación: {} módulos tienen 5+ funciones sin tests.".format(
            len(high_priority)
        ))
        lines.append("  Prioriza: {}".format(", ".join(
            t["module"] for t in high_priority[:5]
        )))

    return "\n".join(lines)
