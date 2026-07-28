"""
code_analyzer.py — Análisis estático de código completo para ERIS.
Herramientas: Ruff (bugs/style), Radon (complejidad), Mypy (tipos), jscpd (duplicados),
               Bandit (seguridad), Pylint (calidad), pip-audit (dependencias).
Auto-instala herramientas faltantes y genera reportes consolidados.
"""
import subprocess
import os
import sys
import json
import time
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ANALYSIS_DIR = BASE_DIR / "data" / "code_analysis"
PYTHON = sys.executable


def _ensure_tool(name: str, install_cmd: list) -> bool:
    """Verifica si una herramienta está instalada, si no la instala."""
    # Check direct command
    if shutil.which(name):
        return True
    # Check via python -m
    try:
        result = subprocess.run(
            [PYTHON, "-m", name, "--version"],
            capture_output=True, timeout=10, creationflags=0x08000000
        )
        if result.returncode == 0:
            return True
    except Exception:
        pass
    # Try installing
    try:
        subprocess.run(
            install_cmd, capture_output=True, timeout=120,
            creationflags=0x08000000
        )
        # Re-check
        try:
            result = subprocess.run(
                [PYTHON, "-m", name, "--version"],
                capture_output=True, timeout=10, creationflags=0x08000000
            )
            return result.returncode == 0
        except Exception:
            return False
    except Exception:
        return False


def _run_tool(cmd: list, timeout: int = 120) -> tuple:
    """Ejecuta una herramienta y retorna (output, returncode)."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=timeout, creationflags=0x08000000
        )
        output = result.stdout
        if result.stderr:
            output += f"\n[STDERR]\n{result.stderr}" if output else result.stderr
        return output.strip(), result.returncode
    except FileNotFoundError:
        return "Tool not installed", -1
    except subprocess.TimeoutExpired:
        return f"Timeout after {timeout}s", -1
    except Exception as e:
        return f"Error: {e}", -1


def _get_target_path(parameters: dict) -> str:
    """Obtiene la ruta objetivo del análisis."""
    path = parameters.get("path", "") or parameters.get("target", "")
    if not path:
        return str(BASE_DIR)
    if os.path.exists(path):
        return path
    # Intentar relativo a BASE_DIR
    full = BASE_DIR / path
    if full.exists():
        return str(full)
    return path


def _save_report(name: str, content: str):
    """Guarda reporte en data/code_analysis/."""
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    report_path = ANALYSIS_DIR / f"{name}_{ts}.txt"
    report_path.write_text(content, encoding="utf-8")
    return str(report_path)


# ═══════════════════════════════════════════════════════════
# 1. RUFF — Bugs, errores de estilo, linting rápido
# ═══════════════════════════════════════════════════════════
def _analyze_ruff(target: str) -> str:
    """Análisis con Ruff (reemplaza Flake8 + Pylint)."""
    if not _ensure_tool("ruff", [PYTHON, "-m", "pip", "install", "ruff", "-q"]):
        return "Ruff no disponible (pip install ruff)"

    # Contar errores
    output, code = _run_tool([PYTHON, "-m", "ruff", "check", target, "--output-format=concise", "--select=E,W,F,I,B,S,UP"], timeout=180)

    if code == 0 and not output:
        return "Ruff: 0 errores encontrados. Código limpio."

    lines = output.split("\n") if output else []
    errors = [l for l in lines if l.strip() and not l.startswith("[") and "warning" not in l.lower()]

    # Contar por tipo
    counts = {"E": 0, "W": 0, "F": 0, "I": 0, "B": 0, "S": 0, "UP": 0}
    for e in errors:
        parts = e.split()
        if len(parts) >= 2 and parts[1]:
            code_char = parts[1][0] if parts[1][0] in counts else "F"
            counts[code_char] = counts.get(code_char, 0) + 1

    total = len(errors)
    report = f"RUFF — {total} problemas encontrados\n"
    report += f"  Errores (F): {counts['F']}\n"
    report += f"  Estilo (E): {counts['E']}\n"
    report += f"  Warnings (W): {counts['W']}\n"
    report += f"  Import (I): {counts['I']}\n"
    report += f"  Bugbear (B): {counts['B']}\n"
    report += f"  Seguridad (S): {counts['S']}\n"
    report += f"  Python upgrade (UP): {counts['UP']}\n\n"

    # Top 15 errores más relevantes
    report += "Top 15 problemas:\n"
    for e in errors[:15]:
        report += f"  {e}\n"

    if total > 15:
        report += f"  ... y {total - 15} más\n"

    return report


# ═══════════════════════════════════════════════════════════
# 2. RADON — Complejidad ciclomática y métricas
# ═══════════════════════════════════════════════════════════
def _analyze_radon(target: str) -> str:
    """Análisis de complejidad con Radon."""
    if not _ensure_tool("radon", [PYTHON, "-m", "pip", "install", "radon", "-q"]):
        return "Radon no disponible (pip install radon)"

    # Complejidad ciclomática
    output, code = _run_tool([PYTHON, "-m", "radon", "cc", target, "-s", "-a", "-nc"], timeout=120)
    complexity_lines = [l for l in output.split("\n") if l.strip()] if output else []

    # Índice de mantenibilidad
    mi_output, _ = _run_tool([PYTHON, "-m", "radon", "mi", target, "-s", "-nc"], timeout=120)
    mi_lines = [l for l in mi_output.split("\n") if l.strip()] if mi_output else []

    # Halstead
    hal_output, _ = _run_tool([PYTHON, "-m", "radon", "hal", target, "-s", "-nc"], timeout=120)

    report = "RADON — Métricas de Complejidad\n\n"

    # Analizar complejidad
    grades = {"A": 0, "B": 0, "C": 0, "D": 0, "E": 0, "F": 0}
    dangerous = []
    for line in complexity_lines:
        for g in grades:
            if f" - {g} " in line or f" ({g})" in line:
                grades[g] += 1
        if "F (" in line or "E (" in line or "D (" in line:
            dangerous.append(line.strip())

    total_func = sum(grades.values())
    report += f"Funciones/clases analizadas: {total_func}\n"
    report += f"  A (simple):     {grades['A']}\n"
    report += f"  B (bajo):       {grades['B']}\n"
    report += f"  C (medio):      {grades['C']}\n"
    report += f"  D (alto):       {grades['D']}\n"
    report += f"  E (muy alto):   {grades['E']}\n"
    report += f"  F (peligroso):  {grades['F']}\n"

    if dangerous:
        report += f"\nFunciones PELIGROSAS (D/E/F — refactorizar):\n"
        for d in dangerous[:20]:
            report += f"  {d}\n"

    if mi_lines:
        report += f"\nMantenibilidad (MI) — primeras 10 entradas:\n"
        for l in mi_lines[:10]:
            report += f"  {l}\n"

    return report


# ═══════════════════════════════════════════════════════════
# 3. MYPY — Errores de tipos
# ═══════════════════════════════════════════════════════════
def _analyze_mypy(target: str) -> str:
    """Análisis de tipos con Mypy."""
    if not _ensure_tool("mypy", [PYTHON, "-m", "pip", "install", "mypy", "-q"]):
        return "Mypy no disponible (pip install mypy)"

    output, code = _run_tool(
        [PYTHON, "-m", "mypy", target, "--ignore-missing-imports", "--no-error-summary",
         "--hide-error-context", "--colored-output=no"],
        timeout=180
    )

    if code == 0 and not output:
        return "Mypy: 0 errores de tipo encontrados."

    lines = [l for l in output.split("\n") if l.strip() and ": error:" in l]
    total = len(lines)

    report = f"MYPY — {total} errores de tipo\n\n"

    # Agrupar por tipo de error
    error_types = {}
    for l in lines:
        parts = l.split(": error:")
        if len(parts) >= 2:
            err_msg = parts[1].strip()[:80]
            error_types[err_msg] = error_types.get(err_msg, 0) + 1

    report += "Tipos de error más comunes:\n"
    for err, count in sorted(error_types.items(), key=lambda x: -x[1])[:10]:
        report += f"  [{count}x] {err}\n"

    report += f"\nPrimeros 15 errores:\n"
    for l in lines[:15]:
        report += f"  {l}\n"

    return report


# ═══════════════════════════════════════════════════════════
# 4. JSCPD — Código duplicado
# ═══════════════════════════════════════════════════════════
def _analyze_jscpd(target: str) -> str:
    """Detección de código duplicado con jscpd."""
    if not shutil.which("jscpd"):
        # Intentar instalar via npm
        installed = _ensure_tool("jscpd", ["npm", "install", "-g", "jscpd"])
        if not installed:
            return "jscpd no disponible (npm install -g jscpd)\nNecesita Node.js instalado."

    output, code = _run_tool(
        ["jscpd", target, "--min-lines", "5", "--min-tokens", "50",
         "--reporters", "console", "--format", "python"],
        timeout=300
    )

    if not output:
        return "jscpd: No se encontró código duplicado."

    report = "JSCPD — Código Duplicado\n\n"
    # Buscar estadísticas en el output
    for line in output.split("\n"):
        if any(k in line.lower() for k in ["duplicat", "clones", "lines", "%", "tokens", "total"]):
            report += f"  {line.strip()}\n"

    if len(report) < 100:
        report += output[:1000]

    return report


# ═══════════════════════════════════════════════════════════
# 5. BANDIT — Análisis de seguridad (SAST)
# ═══════════════════════════════════════════════════════════
def _analyze_bandit(target: str) -> str:
    """Análisis de seguridad con Bandit (SAST)."""
    if not _ensure_tool("bandit", [PYTHON, "-m", "pip", "install", "bandit", "-q"]):
        return "Bandit no disponible (pip install bandit)"

    output, code = _run_tool(
        [PYTHON, "-m", "bandit", "-r", target, "-f", "txt", "-ll", "--exclude", ".git,node_modules,__pycache__,venv"],
        timeout=180
    )

    lines = [l for l in output.split("\n") if l.strip()] if output else []
    issues = [l for l in lines if "Issue:" in l or "SEVERITY" in l or ">>>" in l]

    report = f"BANDIT — Análisis de Seguridad\n\n"

    # Contar por severidad
    severity_counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for l in lines:
        if "High:" in l: severity_counts["HIGH"] += 1
        elif "Medium:" in l: severity_counts["MEDIUM"] += 1
        elif "Low:" in l: severity_counts["LOW"] += 1

    total = sum(severity_counts.values())
    report += f"Vulnerabilidades encontradas: {total}\n"
    report += f"  HIGH:   {severity_counts['HIGH']}\n"
    report += f"  MEDIUM: {severity_counts['MEDIUM']}\n"
    report += f"  LOW:    {severity_counts['LOW']}\n\n"

    if severity_counts["HIGH"] > 0:
        report += "⚠️ VULNERABILIDADES CRÍTICAS:\n"
        for l in lines:
            if "High:" in l:
                report += f"  {l.strip()}\n"

    # Mostrar issues relevantes
    report += "\nIssues de seguridad:\n"
    for l in lines:
        if ">>>" in l or ("Issue:" in l):
            report += f"  {l.strip()}\n"

    return report


# ═══════════════════════════════════════════════════════════
# 6. PYLINT — Calidad general
# ═══════════════════════════════════════════════════════════
def _analyze_pylint(target: str) -> str:
    """Calidad de código con Pylint."""
    if not _ensure_tool("pylint", [PYTHON, "-m", "pip", "install", "pylint", "-q"]):
        return "Pylint no disponible"

    output, code = _run_tool(
        [PYTHON, "-m", "pylint", target, "--disable=C,R", "--output-format=text",
         "--max-line-length=120", "-j", "0"],
        timeout=180
    )

    # Buscar el score final
    score = "N/A"
    for line in (output or "").split("\n"):
        if "rated at" in line.lower():
            score = line.strip()
            break

    errors = [l for l in (output or "").split("\n") if l.strip() and l.startswith("E")]

    report = f"PYLINT — Calidad de Código\n"
    report += f"Score: {score}\n"
    report += f"Errores (E): {len(errors)}\n\n"

    if errors:
        report += "Primeros 15 errores:\n"
        for e in errors[:15]:
            report += f"  {e}\n"

    return report


# ═══════════════════════════════════════════════════════════
# 7. PIP-AUDIT — Dependencias vulnerables
# ═══════════════════════════════════════════════════════════
def _analyze_pip_audit() -> str:
    """Verifica dependencias con vulnerabilidades conocidas."""
    if not _ensure_tool("pip-audit", [PYTHON, "-m", "pip", "install", "pip-audit", "-q"]):
        return "pip-audit no disponible"

    output, code = _run_tool([PYTHON, "-m", "pip_audit", "--format", "columns"], timeout=120)

    lines = [l for l in (output or "").split("\n") if l.strip()] if output else []
    vulns = [l for l in lines if "vulnerability" in l.lower() or "VULN" in l]

    report = f"PIP-AUDIT — Dependencias Vulnerables\n"
    report += f"Paquetes con vulnerabilidades: {len(vulns)}\n\n"

    if vulns:
        for v in vulns[:10]:
            report += f"  {v}\n"
    else:
        report += "Todas las dependencias están actualizadas.\n"

    return report


# ═══════════════════════════════════════════════════════════
# FUNCIÓN PRINCIPAL
# ═══════════════════════════════════════════════════════════
def code_analyzer(parameters: dict, player=None) -> str:
    """
    Analizador de código completo para ERIS.
    Actions: full_scan, ruff, radon, mypy, jscpd, bandit, pylint, pip_audit,
             quick_scan, fix, report, install_tools, info
    """
    action = parameters.get("action", "full_scan")
    target = _get_target_path(parameters)

    if action == "info":
        return (
            "Code Analyzer — Análisis estático de código.\n\n"
            "Actions:\n"
            "  full_scan    — Escaneo completo (Ruff+Radon+Mypy+Bandit)\n"
            "  quick_scan   — Solo errores críticos (Ruff+Bandid)\n"
            "  ruff         — Bugs, estilo, linting\n"
            "  radon        — Complejidad ciclomática\n"
            "  mypy         — Errores de tipo\n"
            "  jscpd        — Código duplicado\n"
            "  bandit       — Vulnerabilidades de seguridad\n"
            "  pylint       — Calidad general\n"
            "  pip_audit    — Dependencias vulnerables\n"
            "  fix          — Auto-fix con Ruff\n"
            "  install_tools — Instala todas las herramientas\n"
            "  info         — Esta ayuda\n\n"
            "Parámetros:\n"
            "  path/ruta a analizar (default: todo el proyecto ERIS)"
        )

    if action == "install_tools":
        tools = {
            "ruff": [PYTHON, "-m", "pip", "install", "ruff", "-q"],
            "radon": [PYTHON, "-m", "pip", "install", "radon", "-q"],
            "mypy": [PYTHON, "-m", "pip", "install", "mypy", "-q"],
            "bandit": [PYTHON, "-m", "pip", "install", "bandit", "-q"],
            "pylint": [PYTHON, "-m", "pip", "install", "pylint", "-q"],
            "pip-audit": [PYTHON, "-m", "pip", "install", "pip-audit", "-q"],
        }
        results = []
        for name, cmd in tools.items():
            ok = _ensure_tool(name, cmd)
            status = "INSTALADO" if ok else "FALLÓ"
            results.append(f"  {name}: {status}")
        return "Herramientas de análisis:\n" + "\n".join(results)

    if action == "fix":
        if not _ensure_tool("ruff", [PYTHON, "-m", "pip", "install", "ruff", "-q"]):
            return "Ruff no disponible"
        output, code = _run_tool([PYTHON, "-m", "ruff", "check", target, "--fix", "--select=E,W,F,I,B"], timeout=120)
        fixed = sum(1 for l in (output or "").split("\n") if "Fixed" in l or "fixed" in l)
        return f"Auto-fix completado.\n{output[:1000]}" if output else "Sin cambios necesarios."

    if player:
        player.write_log(f"🔍 Analizando código: {action}...")

    # ── Análisis individuales ──
    if action == "ruff":
        return _analyze_ruff(target)
    elif action == "radon":
        return _analyze_radon(target)
    elif action == "mypy":
        return _analyze_mypy(target)
    elif action == "jscpd":
        return _analyze_jscpd(target)
    elif action == "bandit":
        return _analyze_bandit(target)
    elif action == "pylint":
        return _analyze_pylint(target)
    elif action == "pip_audit":
        return _analyze_pip_audit()

    # ── FULL SCAN ──
    if action == "full_scan":
        report_parts = []
        report_parts.append("=" * 60)
        report_parts.append("  REPORTE COMPLETO DE ANÁLISIS DE CÓDIGO")
        report_parts.append(f"  Target: {target}")
        report_parts.append(f"  Fecha: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report_parts.append("=" * 60)

        if player:
            player.write_log("🔍 1/7 Ruff (bugs/estilo)...")
        report_parts.append(f"\n{'─'*40}\n{_analyze_ruff(target)}")

        if player:
            player.write_log("🔍 2/7 Radon (complejidad)...")
        report_parts.append(f"\n{'─'*40}\n{_analyze_radon(target)}")

        if player:
            player.write_log("🔍 3/7 Mypy (tipos)...")
        report_parts.append(f"\n{'─'*40}\n{_analyze_mypy(target)}")

        if player:
            player.write_log("🔍 4/7 Bandit (seguridad)...")
        report_parts.append(f"\n{'─'*40}\n{_analyze_bandit(target)}")

        if player:
            player.write_log("🔍 5/7 Pylint (calidad)...")
        report_parts.append(f"\n{'─'*40}\n{_analyze_pylint(target)}")

        if player:
            player.write_log("🔍 6/7 pip-audit (dependencias)...")
        report_parts.append(f"\n{'─'*40}\n{_analyze_pip_audit()}")

        if player:
            player.write_log("🔍 7/7 jscpd (duplicados)...")
        report_parts.append(f"\n{'─'*40}\n{_analyze_jscpd(target)}")

        full_report = "\n".join(report_parts)

        # Guardar reporte
        report_path = _save_report("full_analysis", full_report)
        full_report += f"\n\nReporte guardado en: {report_path}"

        return full_report[:5000]

    # ── QUICK SCAN ──
    if action == "quick_scan":
        parts = []
        parts.append("QUICK SCAN — Errores críticos\n")
        parts.append(_analyze_ruff(target))
        parts.append("\n" + _analyze_bandit(target))
        return "\n".join(parts)[:3000]

    return f"Acción desconocida: {action}. Usa 'info' para ver opciones."
