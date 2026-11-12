# -*- coding: utf-8 -*-
"""
scripts/metrics_ssot.py — Fuente única de verdad de métricas de ERIS.

Lee tool_registry.py y tool_declarations.py y calcula:
  - total de tools sincronizadas
  - herramientas solo en registry / solo en declarations / duplicadas
  - cantidad de action modules, agentes y skills
  - baseline de tests (lee test_all.py si existe)

Salida: JSON a stdout y opcionalmente escribe metrics.json en la raíz.

Uso:
  python scripts/metrics_ssot.py
  python scripts/metrics_ssot.py --write metrics.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))


def _load_registry():
    from core.tool_registry import _TOOLS, get_all_tool_names
    return _TOOLS, list(get_all_tool_names())


def _load_declarations():
    from core.tool_declarations import TOOL_DECLARATIONS
    return list(TOOL_DECLARATIONS)


def _count_files(pattern):
    return len(list(BASE.rglob(pattern)))


def _parse_baseline():
    """Intenta extraer la línea de baseline de test_all.py (PASS/FAIL/WARN)."""
    p = BASE / "test_all.py"
    if not p.exists():
        return None
    text = p.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"(\d+)\s*PASS\s*/\s*(\d+)\s*FAIL\s*/\s*(\d+)\s*WARN", text)
    if m:
        return {"pass": int(m.group(1)), "fail": int(m.group(2)), "warn": int(m.group(3))}
    return None


def _dups(items):
    seen, dup = set(), set()
    for x in items:
        if x in seen:
            dup.add(x)
        seen.add(x)
    return sorted(dup)


def build_metrics() -> dict:
    tools, reg_names = _load_registry()
    declarations = _load_declarations()
    dec_names = [d.get("name") for d in declarations if isinstance(d, dict)]
    reg_set, dec_set = set(reg_names), set(dec_names)

    baseline = _parse_baseline()

    return {
        "project": "ERIS 4.0.1 Constellation Prime",
        "tools": {
            "registry": len(reg_set),
            "declarations": len(dec_set),
            "synced": len(reg_set & dec_set),
            "only_in_registry": sorted(reg_set - dec_set),
            "only_in_declarations": sorted(dec_set - reg_set),
            "duplicates_registry": _dups(reg_names),
            "duplicates_declarations": _dups(dec_names),
            "in_sync": reg_set == dec_set and not _dups(reg_names) and not _dups(dec_names),
        },
        "actions": {
            "modules": _count_files("actions/*.py"),
        },
        "agents": {
            "specialist": 14,  # fuente: core/agent_definitions.py
            "sub_agents": _count_files("agents/*.py"),
        },
        "skills": {
            "skyll_md": _count_files("**/SKILL.md"),
        },
        "tests": {
            "baseline": baseline,
            "pytest_files": _count_files("tests/test_*.py"),
            "test_all_exists": (BASE / "test_all.py").exists(),
        },
        "files_tracked": None,  # se rellena desde git si está disponible
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", metavar="PATH", help="Escribe métricas a este archivo JSON")
    args = ap.parse_args()

    m = build_metrics()
    out = json.dumps(m, indent=2, ensure_ascii=False)

    if args.write:
        Path(args.write).write_text(out, encoding="utf-8")
        print(f"[metrics_ssot] escrito {args.write}")
    else:
        print(out)

    if not m["tools"]["in_sync"]:
        print("\n[metrics_ssot] ADVERTENCIA: registry y declarations NO están sincronizados.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
