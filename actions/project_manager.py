"""actions/project_manager.py — Gestión de proyectos/tareas para productivity_agent.

Requerido por `agents/productivity_agent.py`, que antes hacía
`from actions.project_manager import project_manager` contra un módulo
INEXISTENTE: la rama «proyecto / project / tarea / task / kanban» quedaba muerta
(auditoría 2026-10-15, hallazgo A3).

No duplica el tablero: delega en `actions/task_manager.py`, que ya es la tool
real de Kanban (add/list/move/update/delete/overdue/search/stats).

API esperada por productivity_agent:
    project_manager(parameters={"action": "status"}, player=...)
"""
from __future__ import annotations


def _as_dict(parameters) -> dict:
    import json
    if isinstance(parameters, str):
        try:
            return json.loads(parameters)
        except Exception:
            return {}
    return parameters or {}


def project_manager(parameters=None, player=None) -> str:
    """Vista de proyectos/tareas. Delega en `task_manager`.

    action:
      "status" | "estado" | "resumen" → resumen (stats + listado)
      cualquier otra                   → se pasa tal cual a task_manager
    """
    params = _as_dict(parameters)
    action = str(params.get("action") or "status").lower().strip()

    try:
        from actions.task_manager import task_manager
    except Exception as e:
        return f"No pude cargar el gestor de tareas: {e}"

    if action in ("status", "estado", "resumen"):
        try:
            stats = task_manager({"action": "stats"}, player=player)
        except Exception as e:
            stats = f"(sin stats: {e})"
        try:
            listing = task_manager({"action": "list"}, player=player)
        except Exception as e:
            listing = f"(no pude listar: {e})"
        return f"{stats}\n\n{listing}"

    # Cualquier otra acción (add/list/move/update/delete/search/...) pasa directo
    return task_manager(params, player=player)
