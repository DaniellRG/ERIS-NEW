"""actions/sub_agent_manager.py — Tool oficial 'agente_sub' de ERIS.

Eris administra SU tripulación de sub-agentes especializados desde este tool:
  - listar/status: ver los 19 sub-agentes y su estado
  - delegar: enrutar una tarea al mejor sub-agente (dispatch_to_sub_agent)
  - planificar: MissionPlanner descompone un objetivo
  - ejecutar[agent]: crear tarea para un sub-agente concreto y correrla
  - mensaje: enviar un mensaje por el bus entre sub-agentes
  - resolver: topo-sort de dependencias (DependencyResolver)
  - stats: estadísticas de la tripulación
Registra la tripulación al primer uso (lazy, sin tocar imports de boot).
"""

from __future__ import annotations
import json
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_REGISTRY_FILE = _BASE / "core" / "sub_agent_registry.json"


def _tripulacion_dict() -> dict:
    """Resumen de la tripulación registrada (sin instanciar todo si no hace falta)."""
    try:
        if _REGISTRY_FILE.exists():
            return json.loads(_REGISTRY_FILE.read_text(encoding="utf-8")).get("agents", {})
    except Exception:
        pass
    return {}


def _restore_tripulacion():
    """Asegura que todos los sub-agentes estén registrados en memoria."""
    from core.sub_agent_crew import register_all_sub_agents
    return register_all_sub_agents()


def _agent_list_line(key: str, info: dict) -> str:
    estado = "✓" if _in_memory(key) else "·"
    return f"  {estado} {key}: {info.get('role', '')} — {str(info.get('goal',''))[:70]}"


def _in_memory(key: str) -> bool:
    try:
        from core.sub_agents import get_sub_agent_registry
        return get_sub_agent_registry().get_agent(key) is not None
    except Exception:
        return False


def sub_agent_manager(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = str(params.get("action", "listar")).lower().strip()
    agent = str(params.get("agent", "")).strip()
    request = str(params.get("request") or params.get("text") or params.get("descripcion") or "").strip()

    # Registro lazy de la tripulación (una sola vez por proceso o según faltantes)
    try:
        _restore_tripulacion()
    except Exception as e:
        return f"[agente_sub] Error registrando tripulación: {e}"

    from core.sub_agents import get_sub_agent_registry, SubAgentMessage
    from core.sub_agent_crew import dispatch_to_sub_agent, route_with_tripulation
    reg = get_sub_agent_registry()

    # ── Acciones de administración ───────────────────────────────
    if action in ("listar", "equipo", "list", "status"):
        trip = _tripulacion_dict()
        if not trip:
            return "Tripulación no registrada aún. Usá action=iniciar."
        lines = [f"🤖 TRIPULACIÓN DE ERIS ({len(trip)} sub-agentes):"]
        layers = {
            "Orquestación": ["MissionPlanner", "TaskRouter", "DependencyResolver"],
            "Especialistas": ["ResearchAnalyst", "CodeEngineer", "SystemOperator", "DataAnalyst",
                              "CreativeWriter", "SecurityAuditor", "LearningCurator"],
            "Calidad/Gobernanza": ["QualityCritic", "MemoryArchivist", "FactVerifier",
                                   "RoutineGovernor", "DecisionArbiter", "ConnectorHub"],
            "Meta": ["EvolutionEngine", "SkillForge", "PromptOptimizer"],
        }
        for layer, keys in layers.items():
            lines.append(f"\n  ▸ {layer}:")
            for k in keys:
                info = trip.get(k)
                if info:
                    lines.append(_agent_list_line(k, info))
        stats = reg.get_stats()
        lines.append(f"\n  📊 {stats['tasks_total']} tareas · {stats['tasks_done']} hechas · "
                     f"{stats['tasks_error']} errores · {stats['messages_in_bus']} msgs en bus")
        return "\n".join(lines)

    if action in ("iniciar", "restore", "setup"):
        n = len(reg.get_all_agents())
        return f"Tripulación activa: {n} sub-agentes registrados."

    if action in ("stats", "metricas"):
        return json.dumps(reg.get_stats(), ensure_ascii=False, indent=2)

    if action in ("disponibles", "keys", "agentes"):
        names = sorted(reg.get_all_agents())
        return "Sub-agentes disponibles: " + ", ".join(names)

    # ── Planificación / Routing ──────────────────────────────────
    if action in ("plan", "planificar", "plane"):
        if not request:
            return "Para planificar: agente_sub action=plan request=<objetivo>"
        return dispatch_to_sub_agent("MissionPlanner", {"objective": request, "action": "plan"})

    if action in ("proyectar", "materializar", "enfocar"):
        if not request:
            return "Para proyectar: agente_sub action=proyectar request=<objetivo>"
        return dispatch_to_sub_agent("MissionPlanner", {"objective": request, "action": "proyectar"})

    if action in ("delegar", "route", "enrutar"):
        if not request:
            return "Para delegar: agente_sub action=delegar request=<tarea>"
        return route_with_tripulation(request)

    # ── Ejecución directa en un sub-agente ───────────────────────
    if action in ("ejecutar", "run", "exec"):
        if not agent:
            return ("Falta 'agent'. Usá action=ejecutar agent=<sub-agente> request=<tarea>. "
                    "Disponibles: " + ", ".join(sorted(reg.get_all_agents())))
        if not request:
            return f"Falta 'request' para ejecutar en {agent}."
        extra = {k: v for k, v in params.items() if k not in ("action", "agent", "request")}
        return dispatch_to_sub_agent(agent, {"request": request, **extra})

    # ── Mensajes entre sub-agentes ───────────────────────────────
    if action in ("mensaje", "send", "message"):
        to_agent = str(params.get("to", "")).strip()
        if not to_agent or not request:
            return "Para enviar: agente_sub action=mensaje to=<agente> request=<contenido>"
        msg = SubAgentMessage(
            id=f"msg_{int(__import__('time').time()*1000)}",
            from_agent=str(params.get("from", "ERIS")),
            to_agent=to_agent,
            type=str(params.get("type", "request")),
            payload={"text": request},
        )
        reg.send_message(msg)
        stats = reg.get_stats()
        return f"Mensaje enviado a {to_agent}. Mensajes en bus: {stats['messages_in_bus']}."

    # ── DependencyResolver (topo-sort) ───────────────────────────
    if action in ("resolver", "dependencias"):
        res = dispatch_to_sub_agent("DependencyResolver", {"request": request or "resolver"})
        return res

    # ── Ayuda ────────────────────────────────────────────────────
    return (
        "AGENTE_SUB — administrá la tripulación de ERIS.\n"
        "  · listar — ver los sub-agentes por capa y su estado\n"
        "  · iniciar — registrar todos los sub-agentes\n"
        "  · plan action=plan request=<objetivo> — MissionPlanner\n"
        "  · proyectar action=proyectar request=<objetivo> — MissionPlanner ARMA EL PLAN Y LO PROYECTA como tareas en cola (el daemon las despacha sola)\n"
        "  · delegar request=<tarea> — TaskRouter elige y ejecuta\n"
        "  · ejecutar agent=<sub-agente> request=<tarea> [params]\n"
        "  · mensaje to=<agente> request=<contenido> — bus interno\n"
        "  · stats / disponibles / resolver — utilidades"
    )