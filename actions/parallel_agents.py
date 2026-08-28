# -*- coding: utf-8 -*-
"""
parallel_agents.py — Subagentes paralelos para ERIS.

Lanza N tareas independientes en hilos simultáneos, cada una resuelta por un
mini-agente (tool-calling LLM limitado a unas pocas iteraciones), y consolida
los resultados. Equivalente al lanzamiento de subagentes en paralelo.
"""
from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

from core.agent_architecture import _chat, _run_tool

_SYS = (
    "Eres un subagente especialista de ERIS. Completa tu TAREA usando las "
    "herramientas disponibles. Razona en 'content'; llama a la herramienta que "
    "necesites. Cuando termines, responde con un resumen del resultado en español "
    "(3-6 lineas). No inventes datos: solo lo que las herramientas confirmaron."
)


def _solve_subtask(task: str, tools: list, max_iter: int = 6) -> str:
    messages = [{"role": "system", "content": _SYS},
                {"role": "user", "content": f"TAREA: {task}\n\nResuélvela."}]
    for _ in range(max_iter):
        resp = _chat(messages, tools=tools, max_tokens=1200)
        if resp.get("error"):
            return f"[error] {resp['error']}"
        content = resp.get("content") or ""
        tcs = resp.get("tool_calls") or []
        if not tcs:
            return content.strip() or "[sin respuesta]"
        messages.append({
            "role": "assistant", "content": content,
            "tool_calls": [{"id": tc["id"], "type": "function",
                            "function": {"name": tc["name"], "arguments": json.dumps(tc["arguments"], ensure_ascii=False)}}
                           for tc in tcs],
        })
        for tc in tcs:
            messages.append({"role": "tool", "tool_call_id": tc["id"],
                             "name": tc["name"], "content": _run_tool(tc["name"], tc["arguments"])})
    return "[sin completar: max iteraciones]"


def parallel_agents(parameters: dict = None, player=None) -> str:
    """Ejecuta varias tareas en paralelo con subagentes. Params: tasks (lista de tareas
    o string con una tarea por linea), max_workers (default 3), max_iter (por subagente,
    default 6). Devuelve el resultado consolidado de cada tarea."""
    tasks = parameters.get("tasks")
    max_workers = int(parameters.get("max_workers") or 3)
    max_iter = int(parameters.get("max_iter") or 6)

    if isinstance(tasks, str):
        tasks = [t.strip() for t in tasks.splitlines() if t.strip()]
    if not isinstance(tasks, list) or not tasks:
        return "Error: se requiere 'tasks' (lista de tareas o texto con una por linea)."

    tasks = [str(t) for t in tasks]
    if max_workers < 1:
        max_workers = 1

    if player:
        try:
            player.write_log(f"[parallel_agents] {len(tasks)} tareas, {max_workers} workers")
        except Exception:
            pass

    try:
        tools = __import__("core.agent_architecture", fromlist=["_agent_tools"])._agent_tools()
    except Exception:
        tools = None

    results = {}
    with ThreadPoolExecutor(max_workers=min(max_workers, len(tasks))) as pool:
        futures = {pool.submit(_solve_subtask, t, tools, max_iter): t for t in tasks}
        for fut in as_completed(futures):
            task = futures[fut]
            try:
                results[task] = fut.result(timeout=180)
            except Exception as e:
                results[task] = f"[subagente error] {e}"

    lines = [f"Subagentes paralelos ({len(tasks)} tareas):"]
    for i, t in enumerate(tasks, 1):
        lines.append(f"\n── TAREA {i}: {t} ──")
        lines.append(str(results.get(t, "[sin resultado]"))[:1500])
    return "\n".join(lines)
