from __future__ import annotations

"""Code Sandbox — Secure Python code execution in an isolated subprocess.

Actions
-------
exec      – Run arbitrary Python code with a hard timeout (max 30 s).
eval      – Evaluate a single expression and return its repr.
version   – Return the interpreter version.
packages  – List installed packages via ``pip list``.
"""

import subprocess
import sys
import tempfile
import textwrap
import os
import ast

_BLOCKED_PATTERNS = [
    "os.system",
    "subprocess",
    "shutil.rmtree",
    "ctypes",
    "__import__('os')",
    "__import__('subprocess')",
    "__import__('shutil')",
    "__import__('ctypes')",
]

_STORAGE = os.path.join(os.path.dirname(__file__), "..", "data", "sandbox")


def _sanitize(code: str) -> tuple[bool, str]:
    """Return ``(safe, reason)`` after checking for dangerous imports."""
    lower = code.lower()
    for pat in _BLOCKED_PATTERNS:
        if pat in lower:
            return False, f"Blocked pattern detected: {pat}"
    return True, ""


def _safe_eval(code: str):
    """
    Evalúa solo expresiones literales seguras (números, strings, tuplas,
    listas, diccionarios, booleanos, None y operaciones aritméticas básicas).
    Rechaza cualquier nodo de AST que no sea explícitamente permitido.
    """
    try:
        tree = ast.parse(code, mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"Expresión inválida: {exc}")

    _ALLOWED_NODES = (
        ast.Expression, ast.Constant, ast.List, ast.Tuple, ast.Dict,
        ast.Set, ast.NameConstant, ast.UnaryOp, ast.BinOp, ast.BoolOp,
        ast.Compare, ast.Attribute, ast.Subscript, ast.Slice,
        ast.USub, ast.UAdd, ast.Not,
        ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow,
        ast.LShift, ast.RShift, ast.BitOr, ast.BitAnd, ast.BitXor,
        ast.Invert,
        ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
        ast.Is, ast.IsNot, ast.In, ast.NotIn,
    )

    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            raise ValueError(f"Nodo no permitido en expresión: {type(node).__name__}")

    return eval(compile(tree, "<string>", "eval"), {"__builtins__": {}}, {})


def _run_subprocess(code: str, timeout: int) -> tuple[str, str, int]:
    """Execute *code* in a subprocess and return (stdout, stderr, returncode)."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(code)
        tmp_path = tmp.name
    try:
        result = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True,
            text=True,
            timeout=min(timeout, 30),
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "", "Execution timed out (limit 30 s).", -1
    finally:
        os.unlink(tmp_path)


def code_sandbox(parameters: dict = None, player=None) -> str:  # noqa: C901
    """Execute code securely or query interpreter metadata."""
    params = parameters or {}
    action = str(params.get("action", "version")).strip().lower()
    code = str(params.get("code", "")).strip()
    timeout = int(str(params.get("timeout", 30)).strip() or 30)
    filename = str(params.get("filename", "")).strip()

    if action == "exec":
        if not code:
            return "Error: No code provided."
        safe, reason = _sanitize(code)
        if not safe:
            return f"Error: Code rejected — {reason}"
        stdout, stderr, rc = _run_subprocess(code, timeout)
        parts: list[str] = []
        if rc != 0:
            parts.append(f"Exit code: {rc}")
        if stdout:
            parts.append(f"STDOUT:\n{stdout.rstrip()}")
        if stderr:
            parts.append(f"STDERR:\n{stderr.rstrip()}")
        if not parts:
            parts.append("Code executed successfully (no output).")
        return "\n".join(parts)

    if action == "eval":
        if not code:
            return "Error: No expression provided."
        safe, reason = _sanitize(code)
        if not safe:
            return f"Error: Expression rejected — {reason}"
        try:
            result = _safe_eval(code)
            return repr(result)
        except Exception as exc:
            return f"Evaluation error: {exc}"

    if action == "version":
        return f"Python {sys.version}"

    if action == "packages":
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "list"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            return result.stdout.strip() if result.returncode == 0 else f"Error: {result.stderr.strip()}"
        except Exception as exc:
            return f"Error listing packages: {exc}"

    return f"Error: Unknown action '{action}'."
