"""
verification_layer.py — Capa de verificación para outputs de herramientas.

Cada resultado de tool pasa por verificación antes de llegar al LLM:
  1. ¿Es válido? (no es error, no está vacío)
  2. ¿Contiene errores detectables?
  3. ¿Necesita procesamiento adicional?
  4. ¿Es consistente con lo esperado?

Esto evita que el LLM reciba basura y tome decisiones sobre datos inválidos.
"""
from __future__ import annotations

import re
from typing import Any


# ── Patrones de error conocidos ──────────────────────────────────────────────

_ERROR_PATTERNS = [
    (re.compile(r"\[ERROR\]", re.IGNORECASE), "error_marker"),
    (re.compile(r"Traceback \(most recent call last\)", re.IGNORECASE), "python_traceback"),
    (re.compile(r"Error:\s", re.IGNORECASE), "error_label"),
    (re.compile(r"FAILED|CRITICAL|FATAL", re.IGNORECASE), "severity_marker"),
    (re.compile(r"errno\s*=\s*\d+", re.IGNORECASE), "errno"),
    (re.compile(r"exit code [1-9]", re.IGNORECASE), "nonzero_exit"),
    (re.compile(r"Permission denied", re.IGNORECASE), "permission_error"),
    (re.compile(r"No such file or directory", re.IGNORECASE), "file_not_found"),
    (re.compile(r"ModuleNotFoundError|ImportError", re.IGNORECASE), "import_error"),
    (re.compile(r"JSONDecodeError|json\.decoder\.JSONDecodeError", re.IGNORECASE), "json_error"),
]

_WARNING_PATTERNS = [
    (re.compile(r"DeprecationWarning|FutureWarning", re.IGNORECASE), "deprecation"),
    (re.compile(r"WARNING|WARN:", re.IGNORECASE), "warning_label"),
    (re.compile(r"deprecated", re.IGNORECASE), "deprecated_api"),
]

_EMPTY_INDICATORS = [
    "", "None", "null", "undefined", "[]", "{}", "()",
    "Sin resultados", "No results", "Empty", "N/A",
]


def verify_tool_output(
    tool_name: str,
    result: Any,
    expected_type: str = "text",
) -> dict:
    """Verifica el output de una herramienta.

    Args:
        tool_name: Nombre de la herramienta.
        result: Resultado de la herramienta.
        expected_type: Tipo esperado (text, json, list, dict, error).

    Returns:
        dict con: valid, status, errors, warnings, needs_processing, summary
    """
    result_str = str(result) if result is not None else ""
    errors = []
    warnings = []
    needs_processing = False

    # 1. Verificar si está vacío
    if not result_str.strip() or result_str.strip() in _EMPTY_INDICATORS:
        errors.append("Resultado vacío o sin contenido")

    # 2. Detectar errores
    for pattern, error_type in _ERROR_PATTERNS:
        if pattern.search(result_str):
            errors.append(f"Error detectado: {error_type}")
            break  # Un error es suficiente

    # 3. Detectar warnings
    for pattern, warning_type in _WARNING_PATTERNS:
        if pattern.search(result_str):
            warnings.append(f"Warning: {warning_type}")

    # 4. Verificar tipo esperado
    if expected_type == "json":
        try:
            import json
            json.loads(result_str)
        except Exception:
            errors.append("Se esperaba JSON válido pero no se pudo parsear")
            needs_processing = True
    elif expected_type == "list":
        if not result_str.startswith("[") and not result_str.startswith("("):
            warnings.append("Se esperaba lista pero no tiene formato de lista")

    # 5. Verificar longitud
    if len(result_str) > 50000:
        warnings.append(f"Resultado muy largo ({len(result_str)} chars)")
        needs_processing = True
    elif len(result_str) < 5 and result_str.strip():
        warnings.append(f"Resultado sospechosamente corto ({len(result_str)} chars)")

    # 6. Detectar resultados repetitivos (posible loop)
    lines = result_str.splitlines()
    if len(lines) > 10:
        unique_lines = set(lines)
        if len(unique_lines) < len(lines) * 0.3:
            warnings.append("Resultado con alta repetición (posible loop)")

    # Determinar status
    if errors:
        status = "error"
    elif warnings:
        status = "warning"
    else:
        status = "ok"

    # Generar resumen
    summary = _generate_summary(tool_name, result_str, errors, warnings)

    return {
        "valid": len(errors) == 0,
        "status": status,
        "errors": errors,
        "warnings": warnings,
        "needs_processing": needs_processing,
        "summary": summary,
        "length": len(result_str),
    }


def _generate_summary(tool_name: str, result: str, errors: list, warnings: list) -> str:
    """Genera un resumen conciso del resultado."""
    if errors:
        return f"[{tool_name}] ERROR: {'; '.join(errors)}"
    if warnings:
        return f"[{tool_name}] OK con warnings: {'; '.join(warnings)}"

    lines = result.splitlines()
    if len(lines) <= 3:
        return f"[{tool_name}] OK: {result[:100]}"
    return f"[{tool_name}] OK: {len(lines)} líneas, {len(result)} chars"


def maybe_fix_output(tool_name: str, result: str, verification: dict) -> str:
    """Intenta arreglar problemas comunes en el output.

    Returns:
        Resultado arreglado o el original si no se pudo arreglar.
    """
    if verification["valid"]:
        return result

    fixed = result

    # Quitar traceback completo y quedarse con la última línea de error
    if any("traceback" in e.lower() for e in verification["errors"]):
        lines = fixed.splitlines()
        # Buscar la línea del error real
        for i in range(len(lines) - 1, -1, -1):
            if "error" in lines[i].lower() or "exception" in lines[i].lower():
                fixed = lines[i]
                break

    # Quitar markers de error si hay contenido útil después
    if "[ERROR]" in fixed:
        parts = fixed.split("[ERROR]", 1)
        if len(parts) > 1 and len(parts[1].strip()) > 20:
            fixed = parts[1].strip()

    return fixed
