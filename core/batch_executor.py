"""
batch_executor.py — Ejecución paralela de múltiples herramientas.

En vez de ejecutar tools una por una (secuencial), permite ejecutar
múltiples tools simultáneamente cuando son independientes.

Flujo:
  1. Recibir lista de tool calls
  2. Detectar dependencias (si una tool necesita el resultado de otra)
  3. Ejecutar las independientes en paralelo
  4. Ejecutar las dependientes secuencialmente
  5. Combinar resultados
"""
from __future__ import annotations

import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

try:
    from core.tool_registry import get_tool
except ImportError:
    get_tool = None

try:
    from core.verification_layer import verify_tool_output
except ImportError:
    verify_tool_output = None

try:
    from core.tool_cache import get_tool_cache
except ImportError:
    get_tool_cache = None

# Tools que NUNCA se ejecutan en batch (efectos secundarios, orden importa)
SequentialTools = {
    "file_write", "file_edit", "file_delete", "self_edit",
    "shell", "github_push", "github_pr",
    "agent_loop", "task_planner",
}

# Tools que dependen de resultados de otras
Dependencies = {
    "code_review": ["file_read", "codebase"],
    "document_rag": ["index_document"],
    "memory_consolidation": ["episodic_add"],
}


def _detect_dependencies(calls: list[dict]) -> dict[str, list[str]]:
    """Detecta qué calls dependen de otras basándose en:",
    - Nombres de outputs que una tool necesita como input
    - Patrones de dependencia conocidos
    """
    dep_graph = {}
    for call in calls:
        name = call.get("name", "")
        deps = Dependencies.get(name, [])
        # Detectar dependencia por nombre de tool: si los args contienen
        # un resultado previo
        args = call.get("arguments", {})
        for key, val in args.items():
            if isinstance(val, str) and val.startswith("$result_"):
                # Referencia a resultado de otra tool
                deps.append(val.replace("$result_", ""))
        dep_graph[name] = deps
    return dep_graph


def _execute_single(name: str, args: dict, player=None) -> dict:
    """Ejecuta una tool individual con verificación y cache."""
    t0 = time.time()
    try:
        # Check cache first
        cache = get_tool_cache()
        if cache:
            cached = cache.get(name, args)
            if cached is not None:
                return {
                    "name": name,
                    "status": "cached",
                    "result": cached,
                    "elapsed": time.time() - t0,
                }

        # Execute
        func = get_tool(name) if get_tool else None
        if func is None:
            return {
                "name": name,
                "status": "error",
                "result": f"Herramienta '{name}' no disponible",
                "elapsed": time.time() - t0,
            }

        import inspect
        sig = inspect.signature(func)
        kwargs = {"parameters": args}
        if "player" in sig.parameters:
            kwargs["player"] = player

        result = func(**kwargs)
        result_str = str(result)[:4000]

        # Verify output
        if verify_tool_output:
            verification = verify_tool_output(name, result_str)
            if not verification.get("valid", True):
                result_str = f"[VERIFICATION FAILED] {result_str}"

        # Cache result
        if cache:
            cache.set(name, args, result_str)

        elapsed = time.time() - t0
        return {
            "name": name,
            "status": "ok",
            "result": result_str,
            "elapsed": round(elapsed, 3),
        }
    except Exception as e:
        return {
            "name": name,
            "status": "error",
            "result": f"Error en {name}: {e}",
            "elapsed": round(time.time() - t0, 3),
        }


def execute_batch(
    calls: list[dict],
    player=None,
    max_workers: int = 4,
    timeout: int = 60,
) -> dict:
    """Ejecuta múltiples tool calls en paralelo, respetando dependencias.

    Args:
        calls: Lista de [{name, arguments}, ...]
        player: Player instance
        max_workers: Máximo de threads paralelos
        timeout: Timeout por tool

    Returns:
        dict con: results, total_time, parallel_count, sequential_count
    """
    t0 = time.time()
    if not calls:
        return {"results": [], "total_time": 0, "parallel_count": 0, "sequential_count": 0}

    # Separar en paralelas y secuenciales
    parallel_calls = []
    sequential_calls = []
    for call in calls:
        name = call.get("name", "")
        if name in SequentialTools or any(
            dep in SequentialTools for dep in Dependencies.get(name, [])
        ):
            sequential_calls.append(call)
        else:
            parallel_calls.append(call)

    results = []

    # Ejecutar paralelas
    if parallel_calls:
        with ThreadPoolExecutor(max_workers=min(len(parallel_calls), max_workers)) as executor:
            futures = {
                executor.submit(_execute_single, c["name"], c.get("arguments", {}), player): c
                for c in parallel_calls
            }
            for future in as_completed(futures, timeout=timeout):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    call = futures[future]
                    results.append({
                        "name": call["name"],
                        "status": "timeout",
                        "result": f"Timeout o error: {e}",
                        "elapsed": timeout,
                    })

    # Ejecutar secuenciales
    for call in sequential_calls:
        result = _execute_single(call["name"], call.get("arguments", {}), player)
        results.append(result)

    total_time = round(time.time() - t0, 3)

    return {
        "results": results,
        "total_time": total_time,
        "parallel_count": len(parallel_calls),
        "sequential_count": len(sequential_calls),
    }


def format_batch_results(batch: dict) -> str:
    """Formatea resultados batch para el LLM/usuario."""
    lines = [
        f"Batch ejecutado: {batch['parallel_count']} paralelas + {batch['sequential_count']} secuenciales "
        f"en {batch['total_time']}s"
    ]
    for r in batch.get("results", []):
        status_icon = {"ok": "✓", "cached": "◆", "error": "✗", "timeout": "⏱"}.get(r["status"], "?")
        result_preview = r.get("result", "")[:150]
        lines.append(f"  {status_icon} {r['name']} ({r.get('elapsed', 0)}s): {result_preview}")
    return "\n".join(lines)
