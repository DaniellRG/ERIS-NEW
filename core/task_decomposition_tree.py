"""
task_decomposition_tree.py — Árbol de descomposición de tareas con dependencias.

Para objetivos muy complejos, crea un árbol jerárquico de sub-tareas
con dependencias y las ejecuta en orden óptimo (topological sort).

Mejora el plan lineal actual al:
  - Manejar dependencias explícitas
  - Ejecutar tareas independientes en paralelo
  - Re-planificar dinámicamente cuando algo falla
"""
from __future__ import annotations

import json
import re
from collections import defaultdict, deque

try:
    from core.agent_architecture import _chat
except ImportError:
    _chat = None


_DECOMPOSE_SYS = (
    "Descompón este objetivo en un árbol de sub-tareas con dependencias.\n"
    "Cada sub-tarea tiene: id, description, depends_on (lista de ids de los que "
    "deben completarse primero), tools (herramientas sugeridas), priority (1=alta).\n\n"
    "Respondé SOLO con JSON válido:\n"
    '{"tasks": [{"id": "t1", "description": "...", "depends_on": [], '
    '"tools": ["tool1"], "priority": 1}]}\n\n'
    "Reglas:\n"
    "- Mínimo 3 tareas, máximo 15\n"
    "- Las raíces (depends_on=[]) son las que se ejecutan primero\n"
    "- No crear dependencias circulares\n"
    "- Prioridad 1=crítica, 2=importante, 3=normal"
)


class TaskNode:
    """Nodo en el árbol de tareas."""

    def __init__(self, task_id: str, description: str, depends_on: list[str] = None,
                 tools: list[str] = None, priority: int = 2):
        self.id = task_id
        self.description = description
        self.depends_on = depends_on or []
        self.tools = tools or []
        self.priority = priority
        self.status = "pending"  # pending, running, completed, failed
        self.result = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "description": self.description,
            "depends_on": self.depends_on,
            "tools": self.tools,
            "priority": self.priority,
            "status": self.status,
            "result": self.result,
        }


class TaskTree:
    """Árbol de tareas con topological sort."""

    def __init__(self):
        self.nodes: dict[str, TaskNode] = {}

    def add_task(self, task: TaskNode):
        self.nodes[task.id] = task

    def _build_graph(self) -> dict[str, list[str]]:
        """Construye grafo de dependencias."""
        graph = defaultdict(list)
        in_degree = {nid: 0 for nid in self.nodes}

        for nid, node in self.nodes.items():
            for dep in node.depends_on:
                if dep in self.nodes:
                    graph[dep].append(nid)
                    in_degree[nid] += 1

        return graph, in_degree

    def topological_sort(self) -> list[list[str]]:
        """Devuelve listas de tareas que pueden ejecutarse en paralelo.

        Returns:
            Lista de niveles. Cada nivel tiene tareas independientes.
            Ej: [["t1", "t2"], ["t3"], ["t4", "t5"]]
            (t1 y t2 van en paralelo, luego t3, luego t4 y t5 en paralelo)
        """
        graph, in_degree = self._build_graph()
        levels = []

        # BFS con Kahn's algorithm
        queue = deque([nid for nid, deg in in_degree.items() if deg == 0])
        visited = 0

        while queue:
            level = []
            next_queue = deque()

            while queue:
                nid = queue.popleft()
                level.append(nid)
                visited += 1

                for neighbor in graph[nid]:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        next_queue.append(neighbor)

            if level:
                # Ordenar por prioridad dentro del nivel
                level.sort(key=lambda nid: self.nodes[nid].priority)
                levels.append(level)
            queue = next_queue

        if visited != len(self.nodes):
            # Hay dependencias circulares — detectar y reportar
            remaining = [nid for nid in self.nodes if self.nodes[nid].status == "pending"]
            if remaining:
                levels.append(remaining)  # Ejecutar lo que se pueda

        return levels

    def get_next_batch(self) -> list[str]:
        """Devuelve las tareas listas para ejecutar (dependencias satisfechas)."""
        ready = []
        for nid, node in self.nodes.items():
            if node.status != "pending":
                continue
            deps_ok = all(
                self.nodes.get(dep, TaskNode(dep, "")).status == "completed"
                for dep in node.depends_on
                if dep in self.nodes
            )
            if deps_ok:
                ready.append(nid)
        # Ordenar por prioridad
        ready.sort(key=lambda nid: self.nodes[nid].priority)
        return ready

    def mark_completed(self, task_id: str, result: str = ""):
        if task_id in self.nodes:
            self.nodes[task_id].status = "completed"
            self.nodes[task_id].result = result

    def mark_failed(self, task_id: str, error: str = ""):
        if task_id in self.nodes:
            self.nodes[task_id].status = "failed"
            self.nodes[task_id].result = error

    def is_complete(self) -> bool:
        return all(n.status in ("completed", "failed") for n in self.nodes.values())

    def get_summary(self) -> dict:
        completed = sum(1 for n in self.nodes.values() if n.status == "completed")
        failed = sum(1 for n in self.nodes.values() if n.status == "failed")
        return {
            "total": len(self.nodes),
            "completed": completed,
            "failed": failed,
            "pending": len(self.nodes) - completed - failed,
            "is_complete": self.is_complete(),
        }

    def format_tree(self) -> str:
        """Formato legible del árbol."""
        levels = self.topological_sort()
        lines = ["Árbol de tareas:"]
        for i, level in enumerate(levels):
            icons = []
            for nid in level:
                node = self.nodes[nid]
                status_icon = {"pending": "○", "running": "●", "completed": "✓", "failed": "✗"}.get(node.status, "?")
                icons.append(f"{status_icon} {nid}: {node.description[:50]}")
            lines.append(f"  Nivel {i + 1}: {' | '.join(icons)}")
        return "\n".join(lines)


def decompose_goal(goal: str, context: str = "") -> TaskTree:
    """Descompone un objetivo en un árbol de tareas.

    Args:
        goal: Objetivo del usuario
        context: Contexto adicional

    Returns:
        TaskTree con las tareas descompuestas
    """
    tree = TaskTree()

    if _chat is None:
        return _decompose_heuristic(goal, tree)

    try:
        resp = _chat([
            {"role": "system", "content": _DECOMPOSE_SYS},
            {"role": "user", "content": f"Objetivo: {goal}\nContexto: {context}"},
        ], max_tokens=1500)
        text = resp.get("content", "")
    except Exception:
        return _decompose_heuristic(goal, tree)

    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        try:
            data = json.loads(m.group(0))
            for t in data.get("tasks", []):
                node = TaskNode(
                    task_id=t["id"],
                    description=t["description"],
                    depends_on=t.get("depends_on", []),
                    tools=t.get("tools", []),
                    priority=t.get("priority", 2),
                )
                tree.add_task(node)
            if tree.nodes:
                return tree
        except Exception:
            pass

    return _decompose_heuristic(goal, tree)


def _decompose_heuristic(goal: str, tree: TaskTree) -> TaskTree:
    """Descomposición heurística sin LLM."""
    tree.add_task(TaskNode("t1", "Diagnosticar y mapear el objetivo", [], ["codebase", "file_read"], 1))
    tree.add_task(TaskNode("t2", "Implementar la solución", ["t1"], ["file_write", "file_edit", "shell"], 1))
    tree.add_task(TaskNode("t3", "Verificar y documentar", ["t2"], ["shell", "file_write"], 2))
    return tree
