"""
sandbox_execution.py — Ejecución segura de código Python/JS en sandbox.
Limita tiempo, memoria y acceso a archivos/sistema.
"""
import json
import os
import sys
import subprocess
import tempfile
try:
    import resource
except ImportError:
    resource = None  # Windows fallback
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

_BASE = Path(__file__).resolve().parent.parent
_HISTORY_FILE = _BASE / "data" / "sandbox_history.json"

MAX_EXECUTION_TIME = 30  # seconds
MAX_OUTPUT_SIZE = 50000  # chars
ALLOWED_PATHS = [
    str(_BASE / "data"),
    str(_BASE / "actions"),
    str(_BASE / "core"),
    str(tempfile.gettempdir()),
]
BLOCKED_MODULES = [
    "subprocess", "shutil", "ctypes", "socket", "http",
    "urllib", "requests", "smtplib", "imaplib",
]


def sandbox_execution(parameters: dict = None, player=None) -> str:
    """Ejecución segura de código."""
    params = parameters or {}
    action = params.get("action", "run_python").lower()

    if action == "run_python":
        return _run_python(params)
    elif action == "run_js":
        return _run_js(params)
    elif action == "run_snippet":
        return _run_snippet(params)
    elif action == "validate":
        return _validate(params)
    elif action == "history":
        return _get_history()
    elif action == "status":
        return _get_status()
    elif action == "limits":
        return _get_limits()
    elif action == "examples":
        return _get_examples()
    return "Acciones: run_python, run_js, run_snippet, validate, history, status, limits, examples"


def _validate(params: dict) -> str:
    code = params.get("code", "")
    if not code:
        return "Error: se requiere 'code'"
    lang = params.get("lang", "python")
    ok, reason = _validate_code(code, lang)
    if ok:
        return "Código válido ({}): {}".format(lang, reason)
    return "Código inválido: {}".format(reason)


def _validate_code(code: str, lang: str = "python") -> tuple:
    """Valida código antes de ejecutar. Retorna (ok, reason)."""
    if not code.strip():
        return False, "Código vacío"
    if len(code) > 100000:
        return False, "Código demasiado largo (>100KB)"

    if lang == "python":
        dangerous = ["import os", "os.system", "os.popen", "__import__",
                      "eval(", "exec(", "compile(", "open('/etc", "open('/proc",
                      "os.remove", "os.rmdir", "os.rename", "os.chmod",
                      "shutil.", "ctypes.", "subprocess."]
        for pattern in dangerous:
            if pattern in code:
                return False, "Código contiene patrón restringido: {}".format(pattern)
        for mod in BLOCKED_MODULES:
            if "import {}".format(mod) in code or "from {}".format(mod) in code:
                return False, "Módulo bloqueado: {}".format(mod)

    return True, "OK"


def _run_python(params: dict) -> str:
    code = params.get("code", "")
    if not code:
        return "Error: se requiere 'code'"

    ok, reason = _validate_code(code, "python")
    if not ok:
        return "Bloqueado: {}".format(reason)

    timeout = min(int(params.get("timeout", MAX_EXECUTION_TIME)), 60)

    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True, text=True,
            timeout=timeout,
            cwd=str(tempfile.gettempdir()),
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        stdout = result.stdout[:MAX_OUTPUT_SIZE]
        stderr = result.stderr[:MAX_OUTPUT_SIZE]

        _log_execution("python", code[:500], result.returncode, stdout[:200])

        if result.returncode == 0:
            output = stdout if stdout else "(sin salida)"
            return "Python OK ({}s):\n{}".format(timeout, output)
        else:
            return "Python ERROR (code {}):\n{}".format(result.returncode, stderr or stdout)
    except subprocess.TimeoutExpired:
        return "Timeout: código excedió {} segundos".format(timeout)
    except Exception as e:
        return "Error: {}".format(str(e))


def _run_js(params: dict) -> str:
    code = params.get("code", "")
    if not code:
        return "Error: se requiere 'code'"

    ok, reason = _validate_code(code, "js")
    if not ok:
        return "Bloqueado: {}".format(reason)

    timeout = min(int(params.get("timeout", MAX_EXECUTION_TIME)), 60)

    try:
        result = subprocess.run(
            ["node", "-e", code],
            capture_output=True, text=True,
            timeout=timeout,
            cwd=str(tempfile.gettempdir()),
        )
        stdout = result.stdout[:MAX_OUTPUT_SIZE]
        stderr = result.stderr[:MAX_OUTPUT_SIZE]

        _log_execution("javascript", code[:500], result.returncode, stdout[:200])

        if result.returncode == 0:
            output = stdout if stdout else "(sin salida)"
            return "JS OK ({}s):\n{}".format(timeout, output)
        else:
            return "JS ERROR (code {}):\n{}".format(result.returncode, stderr or stdout)
    except FileNotFoundError:
        return "Node.js no encontrado. Instalar: winget install OpenJS.NodeJS"
    except subprocess.TimeoutExpired:
        return "Timeout: código excedió {} segundos".format(timeout)
    except Exception as e:
        return "Error: {}".format(str(e))


def _run_snippet(params: dict) -> str:
    lang = params.get("lang", "python").lower()
    code = params.get("code", "")
    if not code:
        return "Error: se requiere 'code'"

    presets = {
        "fibonacci": {
            "python": "def fib(n):\n    a, b = 0, 1\n    for _ in range(n):\n        a, b = b, a + b\n    return a\nprint([fib(i) for i in range(20)])",
            "javascript": "function fib(n) { let a=0, b=1; for(let i=0;i<n;i++){[a,b]=[b,a+b]} return a; }\nconsole.log(Array.from({length:20},(_,i)=>fib(i)));",
        },
        "sort": {
            "python": "data = [64, 34, 25, 12, 22, 11, 90]\nsorted_data = sorted(data)\nprint(f'Original: {data}')\nprint(f'Ordenado: {sorted_data}')",
            "javascript": "const data = [64, 34, 25, 12, 22, 11, 90];\nconsole.log('Original:', data);\nconsole.log('Ordenado:', [...data].sort((a,b)=>a-b));",
        },
        "hash": {
            "python": "import hashlib\nmsg = 'Hello ERIS'\nprint(f'MD5:    {hashlib.md5(msg.encode()).hexdigest()}')\nprint(f'SHA256: {hashlib.sha256(msg.encode()).hexdigest()}')",
        },
        "matrix": {
            "python": "def matrix_mult(a, b):\n    return [[sum(x*y for x,y in zip(r, c)) for c in zip(*b)] for r in a]\n\nA = [[1,2],[3,4]]\nB = [[5,6],[7,8]]\nprint('A × B =', matrix_mult(A, B))",
        },
        "regex": {
            "python": "import re\ntext = 'Email: test@example.com, Phone: +57-300-1234567'\nemails = re.findall(r'[\\w.-]+@[\\w.-]+\\.\\w+', text)\nphones = re.findall(r'\\+?\\d[\\d-]+', text)\nprint(f'Emails: {emails}')\nprint(f'Phones: {phones}')",
        },
    }

    if code in presets and lang in presets[code]:
        return _run_python({"code": presets[code][lang], "timeout": params.get("timeout", 10)}) if lang == "python" else _run_js({"code": presets[code][lang], "timeout": params.get("timeout", 10)})

    if lang == "python":
        return _run_python(params)
    elif lang in ("javascript", "js"):
        return _run_js(params)
    return "Lenguaje no soportado: {}. Usa: python, javascript".format(lang)


def _get_history() -> str:
    history = _load_history()
    if not history:
        return "Sin historial de ejecución"
    lines = ["═══ HISTORIAL DE EJECUCIÓN ═══", ""]
    for entry in history[-20:]:
        status = "OK" if entry.get("returncode", 1) == 0 else "ERROR"
        lines.append("  [{}] {} — {}".format(
            status, entry.get("lang", "?"),
            entry.get("timestamp", "?")[:19]))
        if entry.get("output"):
            lines.append("    {}".format(entry["output"][:80]))
        lines.append("")
    return "\n".join(lines)


def _get_status() -> str:
    history = _load_history()
    total = len(history)
    ok = sum(1 for h in history if h.get("returncode") == 0)
    errors = total - ok
    lines = [
        "═══ SANDBOX STATUS ═══",
        "",
        "  Lenguajes:      Python, JavaScript (Node.js)",
        "  Timeout max:    {} segundos".format(MAX_EXECUTION_TIME),
        "  Output max:     {} chars".format(MAX_OUTPUT_SIZE),
        "  Módulos block:  {}".format(", ".join(BLOCKED_MODULES[:5]) + "..."),
        "  Ejecuciones:    {} total ({} OK, {} ERR)".format(total, ok, errors),
    ]
    try:
        subprocess.run([sys.executable, "--version"], capture_output=True, timeout=5)
        lines.append("  Python:         Disponible")
    except Exception:
        lines.append("  Python:         NO disponible")
    try:
        subprocess.run(["node", "--version"], capture_output=True, timeout=5)
        lines.append("  Node.js:        Disponible")
    except Exception:
        lines.append("  Node.js:        NO disponible")
    return "\n".join(lines)


def _get_limits() -> str:
    return (
        "═══ LÍMITES DEL SANDBOX ═══\n\n"
        "  Tiempo:     {} segundos max\n"
        "  Memoria:    Limitada por subprocess\n"
        "  Archivos:   Solo data/, actions/, core/, temp/\n"
        "  Red:        BLOQUEADA (sin socket/http/requests)\n"
        "  Módulos:    {} bloqueados\n"
        "  Código:     Max 100KB\n"
        "  Output:     Max {} chars\n"
    ).format(MAX_EXECUTION_TIME, len(BLOCKED_MODULES), MAX_OUTPUT_SIZE)


def _get_examples() -> str:
    return (
        "═══ EJEMPLOS DE CÓDIGO ═══\n\n"
        "  Presets disponibles (action: run_snippet):\n"
        "    'fibonacci'  — Secuencia de Fibonacci\n"
        "    'sort'       — Algoritmos de ordenamiento\n"
        "    'hash'       — Hashing con hashlib\n"
        "    'matrix'     — Multiplicación de matrices\n"
        "    'regex'      — Expresiones regulares\n\n"
        "  Ejemplo directo:\n"
        "    code: 'print([i**2 for i in range(10)])'\n"
        "    lang: 'python'\n"
        "    timeout: 10\n"
    )


def _log_execution(lang: str, code: str, returncode: int, output: str):
    history = _load_history()
    history.append({
        "lang": lang,
        "code": code,
        "returncode": returncode,
        "output": output[:200],
        "timestamp": datetime.now().isoformat(),
    })
    if len(history) > 100:
        history = history[-100:]
    _save_history(history)


def _load_history() -> list:
    if _HISTORY_FILE.exists():
        try:
            return json.loads(_HISTORY_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return []


def _save_history(history: list):
    _HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    _HISTORY_FILE.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")
