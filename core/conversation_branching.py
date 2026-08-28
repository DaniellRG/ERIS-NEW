"""
conversation_branching.py — Exploración de múltiples caminos de solución.

Cuando hay varias formas de resolver un problema, el agente puede
explorarlas simultáneamente y quedarse con la mejor.

Flujo:
  1. Recibir objetivo con ambigüedad (varias soluciones posibles)
  2. Generar N caminos alternativos
  3. Evaluar cada uno (riesgo, complejidad, tiempo)
  4. Ejecutar el mejor o los mejores
  5. Comparar resultados y quedarse con la mejor
"""
from __future__ import annotations

import json
import re
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from core.agent_architecture import _chat, _execute_step
except ImportError:
    _chat = None
    _execute_step = None


_BRANCH_SYS = (
    "Dado un objetivo del usuario, generá 2-3 caminos alternativos para "
    "resolverlo. Para cada camino, evaluá riesgo (1-5), complejidad (1-5), "
    "y tiempo estimado.\n\n"
    "Respondé SOLO con un JSON válido: "
    '[{"name": "nombre", "description": "qué hace", "approach": "cómo", '
    '"risk": 1-5, "complexity": 1-5, "estimated_time": "rápido/medio/lento"}]'
)


def generate_branches(goal: str, context: str = "") -> list[dict]:
    """Genera caminos alternativos para un objetivo.

    Args:
        goal: Objetivo del usuario
        context: Contexto adicional

    Returns:
        Lista de [{name, description, approach, risk, complexity, estimated_time}]
    """
    if _chat is None:
        return _generate_branches_heuristic(goal)

    try:
        resp = _chat([
            {"role": "system", "content": _BRANCH_SYS},
            {"role": "user", "content": f"Objetivo: {goal}\nContexto: {context}"},
        ], max_tokens=800)
        text = resp.get("content", "")
    except Exception:
        return _generate_branches_heuristic(goal)

    m = re.search(r"\[[\s\S]*\]", text)
    if m:
        try:
            branches = json.loads(m.group(0))
            if isinstance(branches, list) and len(branches) >= 2:
                return branches[:4]
        except Exception:
            pass
    return _generate_branches_heuristic(goal)


def _generate_branches_heuristic(goal: str) -> list[dict]:
    """Generación heurística sin LLM."""
    branches = [
        {
            "name": "directo",
            "description": "Implementar directamente la solución",
            "approach": "Hacer lo que el usuario pide literalmente",
            "risk": 2,
            "complexity": 2,
            "estimated_time": "rápido",
        },
        {
            "name": "robusto",
            "description": "Solución con validación y manejo de errores",
            "approach": "Implementar con verificación completa",
            "risk": 1,
            "complexity": 4,
            "estimated_time": "medio",
        },
    ]
    if "bug" in goal.lower() or "error" in goal.lower():
        branches.append({
            "name": "diagnóstico",
            "description": "Diagnosticar primero, luego arreglar",
            "approach": "Reproducir → diagnosticar → fix mínimo",
            "risk": 1,
            "complexity": 3,
            "estimated_time": "medio",
        })
    return branches


def evaluate_branch(branch: dict) -> float:
    """Evalúa un camino y devuelve un score (menor = mejor).

    Score = risk * 2 + complexity * 1.5 + time_penalty
    """
    time_penalties = {"rápido": 0, "medio": 1, "lento": 3}
    risk = branch.get("risk", 3)
    complexity = branch.get("complexity", 3)
    time_pen = time_penalties.get(branch.get("estimated_time", "medio"), 1)
    return risk * 2 + complexity * 1.5 + time_pen


def select_best_branch(branches: list[dict]) -> dict:
    """Selecciona el mejor camino."""
    if not branches:
        return {}
    scored = [(evaluate_branch(b), b) for b in branches]
    scored.sort(key=lambda x: x[0])
    return scored[0][1]


def execute_branch(branch: dict, goal: str, player=None) -> dict:
    """Ejecuta un camino y devuelve el resultado.

    Returns:
        dict con: branch, result, status, elapsed
    """
    if _execute_step is None:
        return {"branch": branch, "result": "Agente no disponible", "status": "error", "elapsed": 0}

    t0 = time.time()
    step = {
        "step": 1,
        "description": f"{goal} (camino: {branch.get('name', 'directo')})",
        "tools": [],
        "status": "running",
    }

    result = _execute_step(goal, step, f"  1. [running] {branch.get('name', '')}", [], player, max_attempts=3)

    return {
        "branch": branch,
        "result": result.get("result", ""),
        "status": result.get("status", "failed"),
        "elapsed": round(time.time() - t0, 3),
    }


def explore_and_select(
    goal: str,
    context: str = "",
    player=None,
    max_branches: int = 2,
) -> dict:
    """Explora múltiples caminos y selecciona el mejor.

    Args:
        goal: Objetivo del usuario
        context: Contexto
        player: Player instance
        max_branches: Máximo de caminos a explorar en paralelo

    Returns:
        dict con: branches, selected, results, winner
    """
    # Generar caminos
    branches = generate_branches(goal, context)
    if not branches:
        return {"branches": [], "selected": None, "results": [], "winner": None}

    # Ordenar por score y tomar los mejores N
    scored = sorted(branches, key=evaluate_branch)
    to_explore = scored[:max_branches]

    # Ejecutar en paralelo
    results = []
    with ThreadPoolExecutor(max_workers=max_branches) as executor:
        futures = {
            executor.submit(execute_branch, b, goal, player): b
            for b in to_explore
        }
        for future in as_completed(futures, timeout=120):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                b = futures[future]
                results.append({"branch": b, "result": str(e), "status": "error", "elapsed": 0})

    # Seleccionar ganador
    successful = [r for r in results if r["status"] == "completed"]
    if successful:
        winner = min(successful, key=lambda r: len(r["result"]))
    else:
        winner = results[0] if results else None

    return {
        "branches": branches,
        "selected": winner["branch"] if winner else None,
        "results": results,
        "winner": winner,
    }
