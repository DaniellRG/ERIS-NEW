"""
agent_as_tool.py — Agente delegador inteligente para ERIS.

Permite que un agente delegue sub-tareas a otro agente con:
  - Supervisión: monitorear progreso
  - Retry: reintentar si falla
  - Merge: combinar resultados de múltiples sub-agentes
  - Timeout: límite de tiempo por sub-tarea

Flujo:
  1. Recibir sub-tarea con objetivo y restricciones
  2. Evaluar si es delegable (complejidad, riesgo)
  3. Delegar a sub-agente con contexto mínimo necesario
  4. Monitorear y reintentar si falla
  5. Merge de resultados
"""
from __future__ import annotations

import json
import time
import threading
from typing import Any

try:
    from core.agent_architecture import _chat, _execute_step
except ImportError:
    _chat = None
    _execute_step = None


class SubAgentTask:
    """Representa una sub-tarea delegada a un agente."""

    def __init__(
        self,
        task_id: str,
        goal: str,
        context: str = "",
        tools: list[str] = None,
        timeout: int = 120,
        max_retries: int = 2,
    ):
        self.task_id = task_id
        self.goal = goal
        self.context = context
        self.tools = tools or []
        self.timeout = timeout
        self.max_retries = max_retries
        self.status = "pending"
        self.result = None
        self.error = None
        self.retries = 0
        self.started_at = None
        self.completed_at = None

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "goal": self.goal,
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "retries": self.retries,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


def evaluate_delegability(goal: str, context: str = "") -> dict:
    """Evalúa si una tarea es delegable a un sub-agente.

    Returns:
        dict con: delegable, risk_level, reasoning, suggested_tools
    """
    goal_lower = goal.lower()

    # Tareas NO delegables
    non_delegable = [
        "borrar", "eliminar", "reset", "deploy", "publicar",
        "commit", "push", "merge", "enviar email", "pagar",
    ]
    for marker in non_delegable:
        if marker in goal_lower:
            return {
                "delegable": False,
                "risk_level": "high",
                "reasoning": f"Tarea contiene acción de riesgo: '{marker}'",
                "suggested_tools": [],
            }

    # Tareas delegables con alto valor
    delegable_high = [
        "buscar", "search", "analizar", "comparar", "resumir",
        "documentar", "verificar", "test", "revisar", "review",
    ]
    for marker in delegable_high:
        if marker in goal_lower:
            return {
                "delegable": True,
                "risk_level": "low",
                "reasoning": f"Tarea de '{marker}' ideal para delegar",
                "suggested_tools": ["codebase", "file_reader", "web_search"],
            }

    # Default: delegable con riesgo medio
    return {
        "delegable": True,
        "risk_level": "medium",
        "reasoning": "Tarea genérica, delegable con supervisión",
        "suggested_tools": [],
    }


def create_sub_agent(
    goal: str,
    context: str = "",
    tools: list[str] = None,
    timeout: int = 120,
    max_retries: int = 2,
) -> SubAgentTask:
    """Crea una sub-tarea para delegar."""
    task_id = f"sub_{int(time.time() * 1000)}"
    return SubAgentTask(
        task_id=task_id,
        goal=goal,
        context=context,
        tools=tools,
        timeout=timeout,
        max_retries=max_retries,
    )


def execute_sub_agent(task: SubAgentTask, player=None) -> SubAgentTask:
    """Ejecuta una sub-tarea con supervisión y retry.

    Returns:
        La misma task con status y resultado actualizados.
    """
    task.status = "running"
    task.started_at = time.time()

    while task.retries <= task.max_retries:
        try:
            if _execute_step is None:
                task.status = "failed"
                task.error = "Agente no disponible"
                break

            # Ejecutar el paso
            step = {
                "step": 1,
                "description": task.goal,
                "tools": task.tools,
                "status": "running",
            }
            plan_summary = f"  1. [running] {task.goal}"

            result = _execute_step(
                task.goal, step, plan_summary, [], player,
                max_attempts=3
            )

            if result.get("status") == "completed":
                task.status = "completed"
                task.result = result.get("result", "")
                break
            else:
                task.error = result.get("result", "Error desconocido")
                task.retries += 1
                if task.retries <= task.max_retries:
                    time.sleep(1)  # Brief pause before retry

        except Exception as e:
            task.error = str(e)
            task.retries += 1
            if task.retries > task.max_retries:
                break

    if task.status == "running":
        task.status = "failed"

    task.completed_at = time.time()
    return task


def merge_results(tasks: list[SubAgentTask]) -> str:
    """Combina los resultados de múltiples sub-tareas.

    Args:
        tasks: Lista de SubAgentTask completadas.

    Returns:
        Resultado mergeado como string.
    """
    if not tasks:
        return "No hay resultados de sub-tareas."

    parts = []
    completed = [t for t in tasks if t.status == "completed"]
    failed = [t for t in tasks if t.status == "failed"]

    if completed:
        parts.append(f"Sub-tareas completadas ({len(completed)}):")
        for t in completed:
            parts.append(f"  ✓ {t.goal}: {str(t.result)[:200]}")

    if failed:
        parts.append(f"\nSub-tareas fallidas ({len(failed)}):")
        for t in failed:
            parts.append(f"  ✗ {t.goal}: {t.error}")

    return "\n".join(parts)


def delegate_smart(
    goals: list[str],
    context: str = "",
    timeout: int = 120,
    player=None,
) -> str:
    """API de alto nivel: evalúa, delega y mergea múltiples sub-tareas.

    Args:
        goals: Lista de objetivos a delegar.
        context: Contexto compartido.
        timeout: Timeout por sub-tarea.
        player: Player instance.

    Returns:
        Resultado mergeado de todas las sub-tareas.
    """
    tasks = []
    delegable_goals = []

    for goal in goals:
        eval_result = evaluate_delegability(goal, context)
        if eval_result["delegable"]:
            delegable_goals.append(goal)
        else:
            tasks.append(None)  # Placeholder para no delegable

    if not delegable_goals:
        return "Ninguna de las tareas es segura para delegar."

    # Ejecutar sub-tareas en paralelo (máximo 3)
    active_tasks = []
    for goal in delegable_goals[:3]:
        task = create_sub_agent(goal, context, timeout=timeout)
        active_tasks.append(task)

    # Ejecutar en threads
    threads = []
    for task in active_tasks:
        t = threading.Thread(target=execute_sub_agent, args=(task, player))
        threads.append(t)
        t.start()

    # Esperar con timeout
    for t in threads:
        t.join(timeout=timeout + 10)

    return merge_results(active_tasks)
