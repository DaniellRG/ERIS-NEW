"""
ERIS Code Sandbox — Ejecución segura de Python/JS con timeout, límites de memoria,
y output capturado. Aísla el código del sistema.
"""
import os
import sys
import json
import time
import tempfile
import subprocess
import threading
from pathlib import Path
from typing import Optional

_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "sandbox"
_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Límites de seguridad
MAX_TIMEOUT = 30  # segundos
MAX_MEMORY_MB = 256
MAX_OUTPUT_CHARS = 10000

# Módulos bloqueados en Python
_BLOCKED_PYTHON_MODULES = {
    "subprocess", "shutil", "ctypes", "socket", "http", "urllib",
    "requests", "smtplib", "ftplib", "telnetlib", "xmlrpc",
    "multiprocessing", "threading", "signal", "os.system",
    "_thread", "winreg",
}


def execute_python(code: str, timeout: int = 15, extra_globals: dict = None) -> str:
    """Ejecuta Python en un subprocess aislado."""
    timeout = min(timeout, MAX_TIMEOUT)

    # Env seguro
    safe_env = os.environ.copy()
    safe_env["PYTHONDONTWRITEBYTECODE"] = "1"
    safe_env["PYTHONIOENCODING"] = "utf-8"

    # Wraper que captura stdout/stderr y limita imports
    wrapper = f'''
import sys, io, builtins

# Redirect stdout/stderr
_stdout_capture = io.StringIO()
_stderr_capture = io.StringIO()
sys.stdout = _stdout_capture
sys.stderr = _stderr_capture

# Block dangerous imports
_original_import = builtins.__import__
_blocked = {repr(list(_BLOCKED_PYTHON_MODULES))}
def _safe_import(name, *args, **kwargs):
    top = name.split('.')[0]
    if top in _blocked:
        raise ImportError(f"Module '{{name}}' is blocked in sandbox")
    return _original_import(name, *args, **kwargs)
builtins.__import__ = _safe_import

# Memory limit (Unix only)
try:
    import resource
    resource.setrlimit(resource.RLIMIT_AS, ({MAX_MEMORY_MB} * 1024 * 1024, {MAX_MEMORY_MB} * 1024 * 1024))
except (ImportError, ValueError, OSError):
    pass

# ── User code ──
try:
    _result = eval(compile({repr(code)}, "<sandbox>", "exec"))
    if _result is not None:
        print(_result)
except Exception as e:
    print(f"Error: {{type(e).__name__}}: {{e}}", file=sys.stderr)

# Restore and output
sys.stdout = sys.__stdout__
sys.stderr = sys.__stderr__
_out = _stdout_capture.getvalue()
_err = _stderr_capture.getvalue()
if _out:
    print("STDOUT:" + _out[:{MAX_OUTPUT_CHARS}])
if _err:
    print("STDERR:" + _err[:{MAX_OUTPUT_CHARS}])
'''

    try:
        result = subprocess.run(
            [sys.executable, "-c", wrapper],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=safe_env,
            cwd=str(_DATA_DIR),
        )
        output = result.stdout
        if result.returncode != 0 and not output:
            output = result.stderr

        # Parse stdout/stderr from wrapper
        stdout_text = ""
        stderr_text = ""
        for line in output.split("\n"):
            if line.startswith("STDOUT:"):
                stdout_text += line[7:] + "\n"
            elif line.startswith("STDERR:"):
                stderr_text += line[7:] + "\n"
            else:
                stdout_text += line + "\n"

        stdout_text = stdout_text.strip()
        stderr_text = stderr_text.strip()

        parts = []
        if stdout_text:
            parts.append(f"Salida:\n{stdout_text[:MAX_OUTPUT_CHARS]}")
        if stderr_text:
            parts.append(f"Error:\n{stderr_text[:MAX_OUTPUT_CHARS]}")
        if not parts:
            parts.append("Ejecutado sin output.")
        return "\n".join(parts)

    except subprocess.TimeoutExpired:
        return f"Timeout después de {timeout}s. El código tardó demasiado."
    except Exception as e:
        return f"Error ejecutando código: {str(e)[:200]}"


def execute_javascript(code: str, timeout: int = 15) -> str:
    """Ejecuta JavaScript usando Node.js (si disponible) o Playwright."""
    timeout = min(timeout, MAX_TIMEOUT)

    # Try Node.js first
    node_path = _find_node()
    if node_path:
        try:
            result = subprocess.run(
                [node_path, "-e", code],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(_DATA_DIR),
            )
            output = result.stdout.strip()
            error = result.stderr.strip()
            if output:
                return f"Salida:\n{output[:MAX_OUTPUT_CHARS]}"
            if error:
                return f"Error:\n{error[:MAX_OUTPUT_CHARS]}"
            return "Ejecutado sin output."
        except subprocess.TimeoutExpired:
            return f"Timeout después de {timeout}s."
        except Exception as e:
            return f"Error: {str(e)[:200]}"

    # Fallback: Playwright evaluate
    try:
        from core.browser_manager import get_browser_manager
        mgr = get_browser_manager()
        if not mgr._ensure():
            return "Error: Ni Node.js ni navegador disponible para JS."
        r = mgr.evaluate(code)
        if r["ok"]:
            return f"Resultado: {r['result']}"
        return f"Error: {r['error']}"
    except Exception as e:
        return f"Error: Ni Node.js ni navegador disponible. ({str(e)[:100]})"


def _find_node() -> Optional[str]:
    """Find node.exe on PATH."""
    for name in ("node", "node.exe"):
        try:
            result = subprocess.run(
                ["where" if os.name == "nt" else "which", name],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                path = result.stdout.strip().split("\n")[0].strip()
                if os.path.isfile(path):
                    return path
        except Exception:
            pass
    return None


def code_sandbox(parameters: dict = None, player=None) -> str:
    """Tool entry point."""
    params = parameters or {}
    language = params.get("language", "python").lower()
    code = params.get("code", "")
    timeout = int(params.get("timeout", 15))

    if not code.strip():
        return "Error: se necesita 'code' para ejecutar."

    if language in ("python", "py"):
        return execute_python(code, timeout)
    elif language in ("javascript", "js", "node"):
        return execute_javascript(code, timeout)
    else:
        return f"Lenguaje '{language}' no soportado. Usa 'python' o 'javascript'."
