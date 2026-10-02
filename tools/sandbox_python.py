"""sandbox_python — Entorno de ejecución aislada para código Python.
Wraper que delega a sandbox_execution, code_sandbox."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def tool_handler(parameters: dict = None, player=None) -> str:
    """Maneja sandbox_python: delega a sandbox_execution o code_sandbox según acción."""
    if parameters is None:
        parameters = {}

    from actions.sandbox_execution import sandbox_execution as _execution
    from actions.code_sandbox import code_sandbox as _sandbox

    accion = parameters.get("action", "").lower()

    if accion and accion.startswith("execution_") or accion in ("run_python", "run_js", "run_snippet", "validate", "history", "limits", "examples", "status", "sandbox_status"):
        return _execution(parameters, player)
    elif accion and accion.startswith("sandbox_") or accion in ("run", "execute", "clear", "sandbox_run", "sandbox_clear", "sandbox_history"):
        return _sandbox(parameters, player)
    else:
        return _execution(parameters, player)


def info() -> dict:
    return {
        "name": "sandbox_python",
        "description": "Entorno de ejecución aislada para código Python. Integra sandbox_execution y code_sandbox.",
        "version": "1.0.0",
    }


if __name__ == "__main__":
    import json
    print(json.dumps(info(), indent=2))
