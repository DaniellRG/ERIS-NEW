"""
multi_agent_orchestrator.py — Orquestación de múltiples agentes con roles.

Va más allá de parallel_agents.py (fan-out simple). Este orquestador:
  - Asigna roles a cada agente (investigador, implementador, revisor)
  - Mantiene estado compartido entre agentes
  - Permite negociación/consenso cuando hay desacuerdo
  - Coordina la secuencia: primero research → luego implement → luego review
"""
from __future__ import annotations

import json
import time
import threading
from pathlib import Path
from collections import defaultdict

try:
    from core.agent_architecture import _chat, _run_tool
except ImportError:
    _chat = None
    _run_tool = None


# Roles predefinidos con sus capacidades
AGENT_ROLES = {
    "researcher": {
        "description": "Investiga y recopila información relevante",
        "tools": ["codebase", "websearch", "webfetch", "file_read"],
        "strengths": ["análisis", "búsqueda", "síntesis"],
        "max_tokens": 1500,
    },
    "implementer": {
        "description": "Implementa soluciones de código",
        "tools": ["file_write", "file_edit", "file_read", "shell"],
        "strengths": ["código", "implementación", "testing"],
        "max_tokens": 2000,
    },
    "reviewer": {
        "description": "Revisa calidad, seguridad y corrección",
        "tools": ["file_read", "codebase", "shell"],
        "strengths": ["análisis crítico", "detección de errores", "mejoras"],
        "max_tokens": 1500,
    },
    "planner": {
        "description": "Planifica y coordina el trabajo",
        "tools": ["codebase", "file_read"],
        "strengths": ["estrategia", "organización", "priorización"],
        "max_tokens": 1000,
    },
    "documenter": {
        "description": "Documenta decisiones y resultados",
        "tools": ["file_write", "obsidian_note"],
        "strengths": ["comunicación", "documentación", "claridad"],
        "max_tokens": 1000,
    },
}


class AgentInstance:
    """Instancia de un agente con rol específico."""

    def __init__(self, agent_id: str, role: str, task: str, context: str = ""):
        self.id = agent_id
        self.role = role
        self.task = task
        self.context = context
        self.status = "pending"  # pending, running, completed, failed
        self.result = None
        self.tool_calls = []
        self.start_time = None
        self.end_time = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "role": self.role,
            "task": self.task,
            "status": self.status,
            "result": self.result,
            "duration": (self.end_time or time.time()) - (self.start_time or time.time()),
        }


class AgentOrchestrator:
    """Orquestador de múltiples agentes."""

    def __init__(self):
        self.agents: dict[str, AgentInstance] = {}
        self.shared_state: dict = {}
        self.workflow: list[list[str]] = []  # Secuencia de fases
        self.results: list[dict] = []

    def add_agent(self, role: str, task: str, context: str = "") -> str:
        """Agrega un agente con un rol y tarea específica."""
        agent_id = "%s_%d" % (role, len(self.agents) + 1)
        agent = AgentInstance(agent_id, role, task, context)
        self.agents[agent_id] = agent
        return agent_id

    def set_workflow(self, phases: list[list[str]]):
        """Define la secuencia de fases.
        Ej: [["researcher"], ["implementer"], ["reviewer"]]
        Cada fase es una lista de roles que corren en paralelo.
        """
        self.workflow = phases

    def execute_parallel(self, agent_ids: list[str] = None) -> list[dict]:
        """Ejecuta agentes en paralelo."""
        targets = agent_ids or list(self.agents.keys())
        threads = []
        for aid in targets:
            agent = self.agents.get(aid)
            if agent and agent.status == "pending":
                t = threading.Thread(target=self._run_agent, args=(aid,), daemon=True)
                threads.append(t)
                t.start()

        for t in threads:
            t.join(timeout=120)

        return [self.agents[aid].to_dict() for aid in targets if aid in self.agents]

    def execute_workflow(self) -> str:
        """Ejecuta el workflow completo fase por fase."""
        if not self.workflow:
            return "No hay workflow definido."

        results = []
        for i, phase in enumerate(self.workflow):
            phase_agents = []
            for role in phase:
                for aid, agent in self.agents.items():
                    if agent.role == role and agent.status == "pending":
                        phase_agents.append(aid)

            if phase_agents:
                self.execute_parallel(phase_agents)
                for aid in phase_agents:
                    agent = self.agents[aid]
                    self.shared_state["last_result_%s" % agent.role] = agent.result
                    results.append(agent.to_dict())

        return json.dumps(results, ensure_ascii=False, indent=2)

    def _run_agent(self, agent_id: str):
        """Ejecuta un agente individual."""
        agent = self.agents.get(agent_id)
        if not agent:
            return

        agent.status = "running"
        agent.start_time = time.time()

        role_info = AGENT_ROLES.get(agent.role, {})
        tools_desc = ", ".join(role_info.get("tools", []))

        # Construir contexto con estado compartido
        shared_ctx = json.dumps(self.shared_state, ensure_ascii=False) if self.shared_state else "(sin estado previo)"

        prompt = (
            "Sos un agente con rol: %s (%s)\n"
            "Tu tarea: %s\n"
            "Contexto adicional: %s\n"
            "Estado compartido de otros agentes: %s\n"
            "Herramientas disponibles: %s\n\n"
            "Completá tu tarea. Si necesitás input de otros agentes, usá el estado compartido."
        ) % (agent.role, role_info.get("description", ""), agent.task,
             agent.context or "(ninguno)", shared_ctx, tools_desc)

        if _chat:
            try:
                resp = _chat([
                    {"role": "system", "content": "Sos un agente especializado. Trabajá de forma autónoma."},
                    {"role": "user", "content": prompt},
                ], max_tokens=role_info.get("max_tokens", 1500))

                agent.result = resp.get("content", "")
                agent.status = "completed"
            except Exception as e:
                agent.result = "Error: %s" % str(e)
                agent.status = "failed"
        else:
            agent.result = "Sin LLM disponible para agente %s" % agent.role
            agent.status = "failed"

        agent.end_time = time.time()

    def negotiate(self, agent_ids: list[str] = None) -> dict:
        """Los agentes negocian para llegar a consenso."""
        targets = agent_ids or list(self.agents.keys())
        opinions = {}
        for aid in targets:
            agent = self.agents.get(aid)
            if agent and agent.result:
                opinions[agent.role] = str(agent.result)[:300]

        if not opinions:
            return {"consensus": "Sin opiniones para negociar"}

        # Usar LLM para sintetizar consenso
        if _chat and len(opinions) > 1:
            opinions_text = "\n".join("- %s: %s" % (r, o[:150]) for r, o in opinions.items())
            try:
                resp = _chat([
                    {"role": "system", "content": "Sos un moderador. Sintetizá las opiniones de múltiples agentes en un consenso. Si hay desacuerdo, indicá los puntos clave."},
                    {"role": "user", "content": "Opiniones de los agentes:\n%s\n\nSintetizá en un consenso." % opinions_text},
                ], max_tokens=500)
                return {"consensus": resp.get("content", ""), "opinions": opinions}
            except Exception:
                pass

        return {"consensus": str(list(opinions.values())[0]), "opinions": opinions}

    def get_status(self) -> dict:
        """Estado del orquestador."""
        return {
            "agents": len(self.agents),
            "completed": sum(1 for a in self.agents.values() if a.status == "completed"),
            "failed": sum(1 for a in self.agents.values() if a.status == "failed"),
            "running": sum(1 for a in self.agents.values() if a.status == "running"),
            "pending": sum(1 for a in self.agents.values() if a.status == "pending"),
            "shared_state_keys": list(self.shared_state.keys()),
        }


def orchestrate_task(
    task: str,
    roles: list[str] = None,
    workflow: list[list[str]] = None,
    context: str = "",
) -> str:
    """Función de alto nivel para orquestar una tarea multi-agente.

    Args:
        task: Tarea a orquestar
        roles: Roles a usar (default: researcher, implementer, reviewer)
        workflow: Secuencia de fases
        context: Contexto adicional

    Returns:
        Resultado de la orquestación
    """
    orch = AgentOrchestrator()
    roles = roles or ["researcher", "implementer", "reviewer"]

    for role in roles:
        orch.add_agent(role, task, context)

    if workflow:
        orch.set_workflow(workflow)
    else:
        # Workflow por defecto: research → implement → review
        if "researcher" in roles and "implementer" in roles and "reviewer" in roles:
            orch.set_workflow([["researcher"], ["implementer"], ["reviewer"]])
        else:
            orch.set_workflow([roles])

    result = orch.execute_workflow()

    # Intentar negociación si hay múltiples agentes
    if len(orch.agents) > 1:
        negotiation = orch.negotiate()
        if negotiation.get("consensus"):
            result += "\n\nConsenso: %s" % negotiation["consensus"]

    return result
