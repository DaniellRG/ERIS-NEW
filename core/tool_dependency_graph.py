"""
tool_dependency_graph.py — Grafo de dependencias entre herramientas.

Mapea qué tools dependen de cuáles, qué tools comparten datos,
y qué tools son críticas (si fallan, afectan a muchas).

Útil para:
  - Batch execution: saber qué tools correr en paralelo
  - Error recovery: saber qué tools afecta un fallo
  - Optimization: identificar bottlenecks
"""
from __future__ import annotations

import json
from pathlib import Path
from collections import defaultdict

_BASE = Path(__file__).resolve().parent.parent
_GRAPH_FILE = _BASE / "data" / "tool_dependency_graph.json"

# Dependencias estáticas conocidas (pueden ser expandidas dinámicamente)
STATIC_DEPENDENCIES = {
    "code_review": {"depends_on": ["file_read", "codebase"], "category": "dev"},
    "document_rag": {"depends_on": ["index_document"], "category": "rag"},
    "memory_consolidation": {"depends_on": ["episodic_add"], "category": "memory"},
    "github_pr": {"depends_on": ["git_control", "shell"], "category": "dev"},
    "github_push": {"depends_on": ["git_control"], "category": "dev"},
    "obsidian_note": {"depends_on": ["file_write"], "category": "knowledge"},
    "workflow_runner": {"depends_on": ["task_planner", "shell"], "category": "automation"},
    "task_scheduler": {"depends_on": ["reminder"], "category": "automation"},
    "image_generation": {"depends_on": ["web_search"], "category": "creative"},
    "voice_clone": {"depends_on": ["audio_transcriber"], "category": "voice"},
    "deep_research": {"depends_on": ["web_search", "webfetch"], "category": "search"},
    "super_search": {"depends_on": ["web_search"], "category": "search"},
    "code_generator": {"depends_on": ["codebase"], "category": "dev"},
    "data_analyst": {"depends_on": ["file_read"], "category": "data"},
    "spreadsheet_generator": {"depends_on": ["file_write"], "category": "data"},
    "morning_brief": {"depends_on": ["daily_digest", "goals"], "category": "productivity"},
    "self_healing_loop": {"depends_on": ["self_heal", "shell"], "category": "self"},
    "proactive_automation": {"depends_on": ["task_scheduler"], "category": "automation"},
    "episodic_log": {"depends_on": ["episodic_add"], "category": "memory"},
}


class ToolDependencyGraph:
    """Grafo de dependencias entre herramientas."""

    def __init__(self):
        self.graph = self._load()

    def _load(self) -> dict:
        try:
            if _GRAPH_FILE.exists():
                return json.loads(_GRAPH_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
        return {"nodes": {}, "edges": []}

    def _save(self):
        try:
            _GRAPH_FILE.parent.mkdir(parents=True, exist_ok=True)
            _GRAPH_FILE.write_text(
                json.dumps(self.graph, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            pass

    def register_tool(self, name: str, category: str = "other"):
        """Registra una tool en el grafo."""
        if name not in self.graph["nodes"]:
            self.graph["nodes"][name] = {
                "category": category,
                "dependents": [],  # tools que dependen de mí
                "dependencies": [],  # tools de las que yo dependo
                "call_count": 0,
                "error_count": 0,
            }

    def add_dependency(self, tool: str, depends_on: str):
        """Añade una dependencia: tool depende de depends_on."""
        self.register_tool(tool)
        self.register_tool(depends_on)

        if depends_on not in self.graph["nodes"][tool]["dependencies"]:
            self.graph["nodes"][tool]["dependencies"].append(depends_on)
        if tool not in self.graph["nodes"][depends_on]["dependents"]:
            self.graph["nodes"][depends_on]["dependents"].append(tool)

        edge = {"from": depends_on, "to": tool}
        if edge not in self.graph["edges"]:
            self.graph["edges"].append(edge)

    def record_call(self, tool: str, success: bool):
        """Registra una llamada a tool para métricas."""
        self.register_tool(tool)
        node = self.graph["nodes"][tool]
        node["call_count"] += 1
        if not success:
            node["error_count"] += 1

    def get_critical_tools(self, top_n: int = 5) -> list[dict]:
        """Encuentra las tools más críticas (las que más dependen de ellas)."""
        scored = []
        for name, node in self.graph["nodes"].items():
            dependents = len(node.get("dependents", []))
            errors = node.get("error_count", 0)
            calls = node.get("call_count", 0)
            # Score = dependientes * 2 + errores * 3 + llamadas * 0.1
            score = dependents * 2 + errors * 3 + calls * 0.1
            scored.append({"name": name, "score": score, "dependents": dependents, "errors": errors})
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_n]

    def get_affected_tools(self, failed_tool: str) -> list[str]:
        """Dado un tool que falló, devuelve qué otros tools se afectan."""
        node = self.graph["nodes"].get(failed_tool, {})
        return node.get("dependents", [])

    def get_parallel_groups(self) -> list[list[str]]:
        """Agrupa tools que pueden correr en paralelo (sin dependencias entre sí)."""
        independent = []
        dependent = []
        for name, node in self.graph["nodes"].items():
            if not node.get("dependencies"):
                independent.append(name)
            else:
                dependent.append(name)

        # Tools con dependencias van en secuencial
        return [independent] if independent else []

    def get_category_stats(self) -> dict:
        """Estadísticas por categoría."""
        stats = defaultdict(lambda: {"tools": 0, "calls": 0, "errors": 0})
        for name, node in self.graph["nodes"].items():
            cat = node.get("category", "other")
            stats[cat]["tools"] += 1
            stats[cat]["calls"] += node.get("call_count", 0)
            stats[cat]["errors"] += node.get("error_count", 0)
        return dict(stats)

    def format_graph(self) -> str:
        """Formato legible del grafo."""
        lines = [f"Grafo: {len(self.graph['nodes'])} tools, {len(self.graph['edges'])} dependencias"]
        critical = self.get_critical_tools(3)
        if critical:
            lines.append("Tools críticas:")
            for c in critical:
                lines.append(f"  {c['name']}: {c['dependents']} dependientes, {c['errors']} errores")
        return "\n".join(lines)


# Inicializar con dependencias estáticas
def _init_graph():
    graph = ToolDependencyGraph()
    for tool, info in STATIC_DEPENDENCIES.items():
        graph.register_tool(tool, info.get("category", "other"))
        for dep in info.get("depends_on", []):
            graph.add_dependency(tool, dep)
    graph._save()
    return graph


_graph: ToolDependencyGraph | None = None


def get_dependency_graph() -> ToolDependencyGraph:
    global _graph
    if _graph is None:
        _graph = _init_graph()
    return _graph
