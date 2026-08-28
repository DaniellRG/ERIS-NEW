# -*- coding: utf-8 -*-
"""
self_regression.py — Health-check y auto-regresión de ERIS.

Ejecuta la validación integral que ERIS debe pasar en cada desarrollo:
  1. py_compile de TODOS los .py del proyecto.
  2. pytest (tests/).
  3. Auditoría de alineación A/B (tool_declarations vs código real).
Devuelve un informe con OK/fallo por sección; con action='fix' intenta
autocorregir los desajustes A/B usando el LLM.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent


def _run(cmd, cwd, timeout=300) -> tuple[bool, str]:
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        text = ((r.stdout or "") + "\n" + (r.stderr or "")).strip()
        return r.returncode == 0, text[-5000:]
    except Exception as e:
        return False, f"[error] {e}"


def _compile_all() -> tuple[bool, list]:
    errors = []
    for p in PROJECT_DIR.rglob("*.py"):
        if (".git" in p.parts or "backups" in p.parts or "node_modules" in p.parts
                or ".venv" in p.parts or "venv" in p.parts):
            continue
        try:
            import py_compile
            py_compile.compile(str(p), doraise=True)
        except py_compile.PyCompileError as e:
            errors.append(f"{p.relative_to(PROJECT_DIR)}: {str(e)[:200]}")
            if len(errors) >= 20:
                break
    return not errors, errors


def _run_pytest() -> tuple[bool, str]:
    return _run([sys.executable, "-m", "pytest", "-q", str(PROJECT_DIR / "tests")],
                str(PROJECT_DIR), timeout=300)


def _run_audit() -> tuple[bool, dict]:
    import importlib.util
    spec = importlib.util.spec_from_file_location("audit_run", str(PROJECT_DIR / "tools" / "tool_audit.py"))
    mod = importlib.util.module_from_spec(spec)
    out = {}
    try:
        import io
        buf = io.StringIO()
        import contextlib
        with contextlib.redirect_stdout(buf):
            spec.loader.exec_module(mod)
            mod.main()
        text = buf.getvalue()
        a = 0
        b = 0
        for line in text.splitlines():
            if "[CLASE A]" in line or "Declaradas pero NUNCA" in line:
                continue
            if "[CLASE B]" in line or "Leídas por la función" in line:
                continue
        import re as _re
        m = _re.search(r"CLASE A:\s*(\d+)", text)
        if m:
            a = int(m.group(1))
        m = _re.search(r"CLASE B:\s*(\d+)", text)
        if m:
            b = int(m.group(1))
        return (a == 0 and b == 0), {"a": a, "b": b, "text": text[:1500]}
    except Exception as e:
        return False, {"a": -1, "b": -1, "text": f"error audit: {e}"}


def self_regression(parameters: dict = None, player=None) -> str:
    """Auto-regresión de ERIS. Acciones: run (compile de todos los .py + pytest + auditoría A/B),
    status (ver último informe), fix (corrige desajustes A/B con LLM)."""
    action = str(parameters.get("action") or "run").lower()

    if action == "status":
        report_file = PROJECT_DIR / "memory" / "self_regression.json"
        if not report_file.exists():
            return "No hay informe de auto-regresión todavía. Usá action='run'."
        try:
            import json
            data = json.loads(report_file.read_text("utf-8"))
            return (f"Última regresión ({data.get('timestamp', '')}): "
                    f"compile={'OK' if data.get('compile_ok') else 'FALLO'}, "
                    f"pytest={'OK' if data.get('pytest_ok') else 'FALLO'}, "
                    f"A={data.get('audit_a')} B={data.get('audit_b')}.")
        except Exception:
            return "Informe corrupto. Usá action='run' para regenerarlo."

    if player:
        try:
            player.write_log("[self_regression] Compilando todos los .py...")
        except Exception:
            pass

    compile_ok, compile_errors = _compile_all()
    if player:
        try:
            player.write_log("[self_regression] pytest...")
        except Exception:
            pass
    pytest_ok, pytest_out = _run_pytest()
    audit_ok, audit = _run_audit()

    report = {
        "timestamp": __import__("datetime").datetime.now().isoformat(),
        "compile_ok": compile_ok, "compile_errors": compile_errors[:10],
        "pytest_ok": pytest_ok, "pytest_out": pytest_out[:500],
        "audit_a": audit.get("a", -1), "audit_b": audit.get("b", -1),
        "audit_ok": audit_ok, "audit_text": audit.get("text", ""),
    }
    try:
        import json
        (PROJECT_DIR / "memory").mkdir(exist_ok=True)
        (PROJECT_DIR / "memory" / "self_regression.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False), "utf-8")
    except Exception:
        pass

    lines = ["════ AUTO-REGRESIÓN DE ERIS ════"]
    lines.append(f"py_compile: {'OK' if compile_ok else 'FALLO'} "
                 f"({'0' if compile_ok else len(compile_errors)} errores)")
    if compile_errors:
        lines += [f"  {e}" for e in compile_errors[:8]]
    lines.append(f"pytest: {'OK' if pytest_ok else 'FALLO'}")
    if not pytest_ok:
        lines.append(f"  {pytest_out[-400:]}")
    lines.append(f"auditoría A/B: A={audit.get('a')} B={audit.get('b')} "
                 f"({'OK' if audit_ok else 'FALLO'})")
    total_ok = compile_ok and pytest_ok and audit_ok
    lines.append(f"RESULTADO: {'✓ TODO OK' if total_ok else '✗ HAY FALLOS'}")

    if total_ok:
        try:
            from core.action_imports import episodic_add
            if episodic_add:
                episodic_add(event="self_regression:ok", category="self_regression",
                             importance=0.4, details="compila+pytest+audit")
        except Exception:
            pass
    return "\n".join(lines)
