# -*- coding: utf-8 -*-
"""
daily_health_report.py — Reporte diario de salud de ERIS.

Unifica las tres validaciones integrales en un solo reporte:
  1. self_regression  — compila todos los .py + pytest + auditoría A/B
  2. tool_benchmark   — tiempos de respuesta de las tools principales
  3. git_daily        — estado del repo y trabajo pendiente

Acciones:
  run    — ejecuta las tres y guarda el reporte en memory/daily_health.json
  status — muestra el último reporte guardado
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
HEALTH_FILE = PROJECT_DIR / "memory" / "daily_health.json"


def daily_health_report(parameters: dict = None, player=None) -> str:
    """Reporte diario de salud. Acciones: run (ejecuta self_regression + benchmark + git_daily y guarda),
    status (último reporte). 'git' es el path del repo (default: ERIS)."""
    action = str(parameters.get("action") or "run").lower()
    git_repo = parameters.get("git") or str(PROJECT_DIR)

    if action == "status":
        if not HEALTH_FILE.exists():
            return "No hay reporte de salud todavía. Usá action='run'."
        try:
            data = json.loads(HEALTH_FILE.read_text("utf-8"))
        except Exception:
            return "Reporte corrupto. Usá action='run' para regenerarlo."
        lines = [
            f"═══ REPORTE DE SALUD ({data.get('timestamp', '')}) ═══",
            f"Compilación:   {'OK' if data.get('compile_ok') else 'FALLO'}",
            f"pytest:        {'OK' if data.get('pytest_ok') else 'FALLO'}",
            f"Auditoría A/B: A={data.get('audit_a')} B={data.get('audit_b')}",
            f"Commits pendientes: {data.get('pending_commits')}",
        ]
        bench = data.get("benchmark", {})
        if bench:
            lines.append("Tools más lentas:")
            for name, secs in list(bench.items())[:3]:
                lines.append(f"  {name}: {secs:.2f}s")
        return "\n".join(lines)

    if action == "run":
        if player:
            try:
                player.write_log("[salud] self_regression...")
            except Exception:
                pass
        try:
            from actions.self_regression import self_regression
            reg = self_regression({"action": "run"})
        except Exception as e:
            reg = f"error: {e}"

        try:
            from actions.tool_benchmark import tool_benchmark
            bench = tool_benchmark({"action": "run", "tools": [
                "system_reader", "calculator", "file_editor", "web_search"]})
        except Exception as e:
            bench = f"error: {e}"

        try:
            from actions.git_daily import git_daily
            git_status = git_daily({"action": "status", "path": git_repo})
        except Exception as e:
            git_status = f"error: {e}"

        compile_ok = "py_compile: OK" in reg
        pytest_ok = "pytest: OK" in reg
        import re
        m_a = re.search(r"A=(\d+)", reg)
        m_b = re.search(r"B=(\d+)", reg)
        audit_a = int(m_a.group(1)) if m_a else -1
        audit_b = int(m_b.group(1)) if m_b else -1
        pending = 1 if ("M " in git_status or "A " in git_status or "D " in git_status) else 0

        bench_dict = {}
        for line in bench.splitlines():
            mm = re.match(r"\s+([\w_]+): ([\d.]+)s", line)
            if mm:
                bench_dict[mm.group(1)] = float(mm.group(2))

        report = {
            "timestamp": datetime.now().isoformat(),
            "compile_ok": compile_ok,
            "pytest_ok": pytest_ok,
            "audit_a": audit_a,
            "audit_b": audit_b,
            "pending_commits": pending,
            "benchmark": bench_dict,
        }
        try:
            HEALTH_FILE.parent.mkdir(exist_ok=True)
            HEALTH_FILE.write_text(json.dumps(report, indent=2, ensure_ascii=False), "utf-8")
        except Exception:
            pass

        lines = ["═══ REPORTE DE SALUD ═══"]
        lines.append(f"py_compile: {'OK' if compile_ok else 'FALLO'} | pytest: {'OK' if pytest_ok else 'FALLO'}")
        lines.append(f"Auditoría A/B: A={audit_a} B={audit_b}")
        lines.append(f"Repo: {'hay cambios sin commitear' if pending else 'limpio'}")
        lines.append("Benchmark (s): " + (", ".join(f"{k}={v:.2f}" for k, v in sorted(bench_dict.items(), key=lambda kv: kv[1], reverse=True)) or "n/a"))
        lines.append("Reporte guardado en memory/daily_health.json")
        return "\n".join(lines)

    return "Acción no válida. Disponibles: run, status."
