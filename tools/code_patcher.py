"""code_patcher — Herramienta de análisis, revisión y generación de código.
Wraper que delega a code_analyzer, code_review, code_generator."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def tool_handler(parameters: dict = None, player=None) -> str:
    """Maneja code_patcher: delega a code_analyzer, code_review o code_generator según acción."""
    if parameters is None:
        parameters = {}

    from actions.code_analyzer import code_analyzer as _analyzer
    from actions.code_review import code_review as _review
    from actions.code_generator import code_generator as _generator

    accion = parameters.get("action", "").lower()

    if accion and accion.startswith("analyzer_") or accion in ("analyze", "full_scan", "quick_scan", "info", "fix", "bandit", "pylint", "ruff", "mypy", "radon", "jscpd", "pip_audit", "install_tools"):
        return _analyzer(parameters, player)
    elif accion and accion.startswith("review_") or accion in ("review", "critique", "suggest", "explain", "compare", "security_audit", "perf_audit", "best_practices", "refactor", "test"):
        return _review(parameters, player)
    elif accion and accion.startswith("generate_") or accion in ("generate", "scaffold", "patch", "apply", "template", "complete"):
        return _generator(parameters, player)
    else:
        # Default: pasar a code_analyzer sin acción específica
        return _analyzer(parameters, player)


def info() -> dict:
    return {
        "name": "code_patcher",
        "description": "Herramienta unificada de análisis, revisión y generación de código. Integra code_analyzer, code_review y code_generator.",
        "version": "1.0.0",
    }


if __name__ == "__main__":
    import json
    print(json.dumps(info(), indent=2))
