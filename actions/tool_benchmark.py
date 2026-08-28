# -*- coding: utf-8 -*-
"""
tool_benchmark.py — Benchmark de herramientas de ERIS.

Mide el tiempo de respuesta de las tools registradas (todas o las de una lista)
y guarda un ranking en memory/benchmarks.json. Ayuda a detectar las lentas.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
BENCH_FILE = PROJECT_DIR / "memory" / "benchmarks.json"

# params de ejemplo por tool (sin efectos destructivos)
_SAMPLE = {
    "system_reader": {"action": "status"},
    "webfetch": {"url": "https://example.com", "timeout": 5},
    "file_controller": {"action": "list", "path": "desktop", "count": 5},
    "file_editor": {"action": "glob", "glob_pattern": "**/*.py", "base_path": str(PROJECT_DIR)},
    "calculator": {"action": "calculate", "expression": "2+2"},
    "task_queue": {"action": "status"},
    "web_search": {"query": "python", "num_results": 2},
    "agent_loop": {"action": "status"},
    "code_validator": {"action": "status"},
    "dependency_manager": {"action": "scan"},
    "multi_search": {"action": "sources", "query": "python", "num_results": 1},
    "parallel_agents": {"action": "status"},
    "search_background": {"query": "python"},
    "reminder": {"action": "status"},
    "notifications": {"action": "status"},
}


def _load() -> dict:
    try:
        if BENCH_FILE.exists():
            return json.loads(BENCH_FILE.read_text("utf-8"))
    except Exception:
        pass
    return {}


def tool_benchmark(parameters: dict = None, player=None) -> str:
    """Benchmark de herramientas. Acciones: run (mide 'tools', lista de nombres, o 'all'; 'iterations'
    repeticiones default 1), status (ranking guardado). Devuelve tiempos por tool y las 3 más lentas."""
    action = str(parameters.get("action") or "run").lower()
    tools = parameters.get("tools")
    iterations = int(parameters.get("iterations") or 1)
    if iterations < 1:
        iterations = 1

    if action == "status":
        data = _load()
        if not data:
            return "No hay benchmarks todavía. Usá action='run'."
        rows = sorted(data.items(), key=lambda kv: kv[1].get("avg", 9e9))
        lines = ["Ranking de herramientas (promedio s):"]
        for name, info in rows[:20]:
            lines.append(f"  {name}: {info.get('avg', 0):.2f}s (n={info.get('n', 0)})")
        return "\n".join(lines)

    if action == "run":
        from core.tool_registry import get_tool
        if isinstance(tools, str):
            names = [t.strip() for t in tools.replace(",", " ").split() if t.strip()]
        elif isinstance(tools, list):
            names = [str(t) for t in tools]
        else:
            names = list(_SAMPLE.keys())
        names = [n for n in names if get_tool(n) is not None][:40]
        if player:
            try:
                player.write_log(f"[benchmark] midiendo {len(names)} tools x{iterations}")
            except Exception:
                pass
        results = {}
        for name in names:
            args = _SAMPLE.get(name, {})
            fn = get_tool(name)
            times = []
            for _ in range(iterations):
                t0 = time.time()
                try:
                    fn(parameters=args)
                except Exception:
                    pass
                times.append(time.time() - t0)
            results[name] = {"avg": sum(times) / len(times), "n": iterations}
        try:
            data = _load()
            data.update(results)
            BENCH_FILE.parent.mkdir(exist_ok=True)
            BENCH_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), "utf-8")
        except Exception:
            pass
        ranked = sorted(results.items(), key=lambda kv: kv[1]["avg"], reverse=True)
        lines = [f"Benchmark ({len(results)} tools, {iterations} iteración/es):"]
        for name, info in ranked:
            lines.append(f"  {name}: {info['avg']:.2f}s")
        slowest = ranked[:3]
        if slowest:
            lines.append("Más lentas: " + ", ".join(f"{n} ({v['avg']:.2f}s)" for n, v in slowest))
        return "\n".join(lines)

    return "Accion no valida. Disponibles: run, status."
