"""
Asistente de codigo proactivo para Eris.
Detecta errores automaticamente cuando Daniel esta programando.
"""
import json
import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from actions.ide_integration import ide_integration


BRACKETS = {"(": ")", "[": "]", "{": "}"}
OPEN_BRACKETS = set(BRACKETS.keys())
CLOSE_BRACKETS = set(BRACKETS.values())
CLOSERS = set(CLOSE_BRACKETS) | {";", ",", ":"}


def analyze_code(code, language="csharp"):
    errors = []
    warnings = []
    suggestions = []
    lines = code.split("\n")
    brace_count = 0
    paren_count = 0

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
            continue

        for ch in stripped:
            if ch in OPEN_BRACKETS:
                if ch == "{":
                    brace_count += 1
                elif ch == "(":
                    paren_count += 1
            elif ch in CLOSE_BRACKETS:
                if ch == "}":
                    brace_count = max(0, brace_count - 1)
                elif ch == ")":
                    paren_count = max(0, paren_count - 1)

        if language == "csharp":
            if ("Console.ReadLine()" in stripped
                    and "?.Trim()" not in stripped
                    and "?." not in stripped):
                warnings.append({
                    "line": i,
                    "type": "null_safety",
                    "message": "Console.ReadLine() puede retornar null. Usar ?.Trim()",
                    "code": stripped
                })

            if ".ToString()" in stripped and "?." not in stripped and "? " not in stripped:
                suggestions.append({
                    "line": i,
                    "type": "null_safety",
                    "message": "Posible NullReferenceException. Usar ?.ToString()",
                    "code": stripped
                })

            if "catch (Exception)" in stripped and "ex" not in stripped:
                suggestions.append({
                    "line": i,
                    "type": "best_practice",
                    "message": "catch vacio. Considerar loguear la excepcion: catch (Exception ex)",
                    "code": stripped
                })

            if re.match(r"^\s*new\s+\w+\(", stripped):
                suggestions.append({
                    "line": i,
                    "type": "modern_csharp",
                    "message": "Considerar usar target-typed new: List<int> x = new();",
                    "code": stripped
                })

    if brace_count != 0:
        errors.append({
            "line": len(lines),
            "type": "braces",
            "message": f"Llaves desbalanceadas: {brace_count} sin cerrar" if brace_count > 0 else "Llaves sobrantes",
            "code": ""
        })

    if paren_count != 0:
        errors.append({
            "line": len(lines),
            "type": "parentheses",
            "message": f"Parentesis desbalanceados: {paren_count} sin cerrar",
            "code": ""
        })

    return {
        "errors": errors,
        "warnings": warnings,
        "suggestions": suggestions,
        "total_lines": len(lines),
        "language": language
    }


def full_scan():
    try:
        detect_result = json.loads(ide_integration({"action": "detect"}))

        if not detect_result.get("detected"):
            return {
                "status": "no_ide",
                "message": "No hay ningun IDE abierto con codigo detectable."
            }

        read_result = json.loads(ide_integration({"action": "read"}))
        code = read_result.get("code", "")

        if not code:
            return {
                "status": "no_code",
                "message": f"IDE detectado ({detect_result.get('ide_friendly')}) pero no se pudo leer el codigo."
            }

        language = detect_result.get("language", "unknown")
        analysis = analyze_code(code, language)

        report = {
            "status": "ok",
            "ide": detect_result.get("ide_friendly", "?"),
            "file": detect_result.get("file_name", "?"),
            "file_path": detect_result.get("file_path", "?"),
            "language": language,
            "total_lines": analysis["total_lines"],
            "errors": analysis["errors"],
            "warnings": analysis["warnings"],
            "suggestions": analysis["suggestions"],
        }

        total_issues = len(analysis["errors"]) + len(analysis["warnings"]) + len(analysis["suggestions"])
        if total_issues == 0:
            report["summary"] = f"Codigo limpio. {analysis['total_lines']} lineas, sin problemas detectados."
        else:
            parts = []
            if analysis["errors"]:
                parts.append(f"{len(analysis['errors'])} error(es)")
            if analysis["warnings"]:
                parts.append(f"{len(analysis['warnings'])} advertencia(s)")
            if analysis["suggestions"]:
                parts.append(f"{len(analysis['suggestions'])} sugerencia(s)")
            report["summary"] = f"{report['file']}: {', '.join(parts)} encontrados en {analysis['total_lines']} lineas."

        return report

    except Exception as e:
        return {"status": "error", "message": f"Error en escaneo: {e}"}


def format_report(report):
    if report.get("status") == "no_ide":
        return "No veo ningun IDE abierto. Abrí Visual Studio con tu codigo y decime."
    if report.get("status") == "no_code":
        return report.get("message", "No pude leer el codigo.")
    if report.get("status") == "error":
        return report.get("message", "Error desconocido.")

    parts = []
    parts.append(f"Detecte {report['ide']} con {report['file']} ({report['total_lines']} lineas)")

    for err in report.get("errors", []):
        parts.append(f"  ERROR linea {err['line']}: {err['message']}")
        if err.get("code"):
            parts.append(f"    -> {err['code']}")

    for warn in report.get("warnings", []):
        parts.append(f"  ADVERTENCIA linea {warn['line']}: {warn['message']}")
        if warn.get("code"):
            parts.append(f"    -> {warn['code']}")

    for sug in report.get("suggestions", []):
        parts.append(f"  SUGERENCIA linea {sug['line']}: {sug['message']}")

    if not report.get("errors") and not report.get("warnings") and not report.get("suggestions"):
        parts.append("  Todo se ve bien, no encontre problemas.")

    return "\n".join(parts)
