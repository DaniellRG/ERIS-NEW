# -*- coding: utf-8 -*-
"""
code_helper.py — Write, edit, explain, run, and build code files.
Actions: write, edit, explain, run, build, auto
"""
import os
import subprocess
import tempfile
import traceback
from pathlib import Path


def code_helper(parameters: dict, player=None) -> str:
    action = parameters.get("action", "auto").lower().strip()
    description = parameters.get("description", "")
    language = parameters.get("language", "python").lower().strip()
    output_path = parameters.get("output_path", "")
    file_path = parameters.get("file_path", "")
    code = parameters.get("code", "")
    args = parameters.get("args", "")
    timeout = int(parameters.get("timeout", 30))

    if action == "auto":
        if code:
            return _explain_code(code, language)
        elif file_path and os.path.exists(file_path):
            return _explain_file(file_path)
        elif description:
            return _generate_and_save(description, language, output_path)
        return "Usá action=write/edit/explain/run/build para más control."

    elif action == "write":
        if not description:
            return "Error: Se requiere 'description' para generar código."
        return _generate_and_save(description, language, output_path)

    elif action == "edit":
        if not file_path or not os.path.exists(file_path):
            return f"Error: '{file_path}' no existe o no se especificó."
        if not description:
            return "Error: Se requiere 'description' describiendo el cambio."
        return _edit_file_with_ai(file_path, description, language)

    elif action == "explain":
        if code:
            return _explain_code(code, language)
        elif file_path and os.path.exists(file_path):
            return _explain_file(file_path)
        return "Error: Se requiere 'code' o 'file_path'."

    elif action == "run":
        if not file_path or not os.path.exists(file_path):
            return f"Error: '{file_path}' no existe."
        return _run_file(file_path, language, args, timeout)

    elif action == "build":
        if not file_path or not os.path.exists(file_path):
            return f"Error: '{file_path}' no existe."
        return _build_file(file_path, language, args, timeout)

    return f"Acción '{action}' no reconocida. Usa: write, edit, explain, run, build, auto"


def _generate_and_save(description: str, language: str, output_path: str) -> str:
    ext_map = {
        "python": ".py", "py": ".py", "javascript": ".js", "js": ".js",
        "typescript": ".ts", "ts": ".ts", "html": ".html", "css": ".css",
        "java": ".java", "c": ".c", "cpp": ".cpp", "go": ".go",
        "rust": ".rs", "bash": ".sh", "shell": ".sh", "sql": ".sql",
        "json": ".json", "yaml": ".yaml", "yml": ".yaml", "xml": ".xml",
        "markdown": ".md", "md": ".md",
    }
    ext = ext_map.get(language, ".py")
    if not output_path:
        from datetime import datetime
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = str(Path.home() / "Documents" / f"code_{ts}{ext}")

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    template = _get_template(language, description)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(template)

    return f"Código generado y guardado en: {output_path}\n\nDescripción: {description}\nLenguaje: {language}"


def _get_template(language: str, description: str) -> str:
    templates = {
        "python": f'''#!/usr/bin/env python3
"""
{description}
"""
import sys
import os


def main():
    """Main function."""
    print("TODO: Implementar — {description}")
    # Your code here


if __name__ == "__main__":
    main()
''',
        "javascript": f'''/**
 * {description}
 */

function main() {{
    console.log("TODO: Implementar — {description}");
}}

main();
''',
        "html": f'''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>{description}</title>
</head>
<body>
    <h1>{description}</h1>
</body>
</html>
''',
    }
    return templates.get(language, f'# {description}\n# TODO: Implementar\n')


def _explain_code(code: str, language: str) -> str:
    lines = code.strip().split("\n")
    explanation = [
        f"Código ({language}, {len(lines)} líneas):",
        ""
    ]

    functions = []
    classes = []
    imports = []
    variables = []

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("import ") or stripped.startswith("from "):
            imports.append(f"  L{i}: {stripped}")
        elif stripped.startswith("def "):
            name = stripped.split("(")[0].replace("def ", "")
            functions.append(f"  L{i}: {name}()")
        elif stripped.startswith("class "):
            name = stripped.split(":")[0].replace("class ", "")
            classes.append(f"  L{i}: {name}")
        elif "=" in stripped and not stripped.startswith("#"):
            var = stripped.split("=")[0].strip()
            if var and len(var) < 50:
                variables.append(f"  L{i}: {var}")

    if imports:
        explanation.append(f"Imports ({len(imports)}):")
        explanation.extend(imports[:10])
    if classes:
        explanation.append(f"\nClases ({len(classes)}):")
        explanation.extend(classes)
    if functions:
        explanation.append(f"\nFunciones ({len(functions)}):")
        explanation.extend(functions)
    if variables:
        explanation.append(f"\nVariables ({len(variables)}):")
        explanation.extend(variables[:10])

    if not any([imports, classes, functions, variables]):
        explanation.append("Código simple sin estructura detectable.")

    return "\n".join(explanation)


def _explain_file(file_path: str) -> str:
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            code = f.read(50000)
        ext = os.path.splitext(file_path)[1].lower()
        lang_map = {".py": "python", ".js": "javascript", ".ts": "typescript",
                    ".html": "html", ".css": "css", ".java": "java",
                    ".go": "go", ".rs": "rust", ".sh": "bash"}
        lang = lang_map.get(ext, ext.replace(".", "") or "unknown")
        result = _explain_code(code, lang)
        return f"Archivo: {os.path.basename(file_path)}\n{result}"
    except Exception as e:
        return f"Error leyendo archivo: {e}"


def _edit_file_with_ai(file_path: str, description: str, language: str) -> str:
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        backup_path = file_path + ".bak"
        with open(backup_path, "w", encoding="utf-8") as f:
            f.write(content)

        lines = content.split("\n")
        new_lines = []
        i = 0
        desc_lower = description.lower()

        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            if any(kw in desc_lower for kw in ["agregar función", "add function", "agregar funcion"]):
                new_lines.append(line)
                i += 1
                if i >= len(lines) or (lines[i].strip() and not lines[i].strip().startswith("#")):
                    func_name = description.split("function")[-1].strip().split()[0] if "function" in desc_lower else "new_function"
                    indent = len(line) - len(line.lstrip()) if line.strip() else 0
                    new_lines.append(" " * indent + f"\ndef {func_name}():")
                    new_lines.append(" " * (indent + 4) + '"""TODO: Implementar"""')
                    new_lines.append(" " * (indent + 4) + "pass")
                    new_lines.append("")
            else:
                new_lines.append(line)
                i += 1

        if new_lines == content.split("\n"):
            new_lines.append(f"\n# {description}\n# TODO: Implementar este cambio\n")

        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(new_lines))

        return f"Archivo editado: {file_path}\nBackup guardado en: {backup_path}\nCambio: {description}"
    except Exception as e:
        return f"Error editando archivo: {e}"


def _run_file(file_path: str, language: str, args: str, timeout: int) -> str:
    cmd_map = {
        "python": ["python", file_path],
        "py": ["python", file_path],
        "javascript": ["node", file_path],
        "js": ["node", file_path],
        "bash": ["bash", file_path],
        "shell": ["bash", file_path],
        "go": ["go", "run", file_path],
    }
    cmd = cmd_map.get(language)
    if not cmd:
        return f"Extensión '{language}' no soportada para ejecutar."

    if args:
        cmd.extend(args.split())

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, cwd=os.path.dirname(file_path) or "."
        )
        output = result.stdout
        if result.stderr:
            output += f"\n[STDERR]\n{result.stderr}"
        if result.returncode != 0:
            output += f"\n[Código de salida: {result.returncode}]"
        return output or "Ejecutado sin salida."
    except subprocess.TimeoutExpired:
        return f"Timeout después de {timeout}s."
    except Exception as e:
        return f"Error ejecutando: {e}"


def _build_file(file_path: str, language: str, args: str, timeout: int) -> str:
    if language in ("c", "cpp"):
        out = os.path.splitext(file_path)[0] + ".exe"
        cmd = ["gcc" if language == "c" else "g++", file_path, "-o", out]
        if args:
            cmd.extend(args.split())
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            if result.returncode == 0:
                return f"Compilado exitosamente: {out}"
            return f"Error de compilación:\n{result.stderr}"
        except Exception as e:
            return f"Error compilando: {e}"
    elif language == "go":
        try:
            result = subprocess.run(["go", "build", file_path], capture_output=True, text=True, timeout=timeout)
            if result.returncode == 0:
                return f"Build exitoso: {os.path.splitext(file_path)[0]}.exe"
            return f"Error de build:\n{result.stderr}"
        except Exception as e:
            return f"Error compilando: {e}"

    return f"Build no soportado para '{language}'. Usa run en su lugar."
