"""core/sub_agent_crew.py — TRIPULACIÓN DE SUB-AGENTES DE ERIS (4 capas).

Capa 1 (Orquestación): MissionPlanner, TaskRouter, DependencyResolver.
Capa 2 (Especialistas): ResearchAnalyst, CodeEngineer, SystemOperator,
    DataAnalyst, CreativeWriter, SecurityAuditor, LearningCurator.
Capa 3 (Calidad/Gobernanza): QualityCritic, MemoryArchivist, FactVerifier,
    RoutineGovernor, DecisionArbiter, ConnectorHub.
Capa 4 (Meta): EvolutionEngine, SkillForge, PromptOptimizer.

Cada agente extiende SubAgentBase y despacha a tools REALES del registry
(cuando el dispatcher está disponible) o cae a heurística/planificación.
Comunicación vía message bus (data/agent_bus.jsonl) y estado compartido.
"""

from __future__ import annotations
import json
import re
import shlex
import time
import threading
from pathlib import Path
from typing import Any, Optional

from core.sub_agents import (
    SubAgentBase, SubAgentRegistry, SubAgentTask, SubAgentMessage,
    SubAgentStatus, get_sub_agent_registry,
)

# Aliasing robusto: inserts 'me' entre verbo y terminación (escribime→escribir)
_VOSE_TERMINALS = ("me", "nos", "le", "les")
_VOSE_VERBS = ("escrib", "investig", "busc", "hac", "hace", "gener", "arm",
               "plan", "organiz", "revis", "verific", "record", "guard",
               "analiz", "compar", "decid", "cheque", "repar", "prepar",
               "cre", "crea", "import", "aprend", "optimiz", "afin")

_BASE = Path(__file__).resolve().parent.parent
_PLAN_DIR = _BASE / "memory" / "sub_agent_plans"
_ROUTER_STATS = _BASE / "data" / "sub_agent_router_stats.json"


def _dispatch_tool(tool_name: str, params: dict, player=None) -> Any:
    """Despacha a una tool REAL del registry (si está disponible)."""
    try:
        from core.tool_dispatcher import dispatch_tool
        return dispatch_tool(tool_name, params, player=player)
    except Exception as e:
        print(f"[SubAgent] dispatch {tool_name}: {e}")
        return f"[Tool {tool_name} no disponible en este contexto]"


def _parse_plan(text: str) -> list[dict]:
    """Extrae steps de un plan generado (para persistir estructura)."""
    steps = []
    for m in re.finditer(r"(?:^|\n)\s*(?:(\d+)[.)]\s*|[-*]\s*)([^\n]+)", text):
        lines = [s.strip() for s in m.group(2).split("\n") if s.strip()]
        for line in lines:
            steps.append({"order": len(steps) + 1, "action": line, "status": "pending"})
        if not lines:
            steps.append({"order": len(steps) + 1, "action": m.group(2)[:120], "status": "pending"})
    steps = steps[:40]
    if not steps and text.strip():
        steps.append({"order": 1, "action": text.strip()[:200], "status": "pending"})
    return steps


# ══════════════════ CAPA 1 · ORQUESTACIÓN ══════════════════

class MissionPlanner(SubAgentBase):
    """Planificador estratégico: descompone objetivos altos en planes
    ejecutables (steps ordenados, dependencias, herramientas, riesgos)."""

    def __init__(self):
        super().__init__(
            key="MissionPlanner",
            role="Planificador Estratégico de ERIS",
            goal="Convertir cualquier objetivo del usuario en un plan claro, ordenado y accionable",
            backstory="Soy el cerebro estratégico de ERIS. Antes de hacer nada, pienso: qué pasos, en qué orden, qué herramientas, qué riesgos.",
            tools=["agente_sub", "todo_yo", "cerebro", "memoria"],
        )
        self._plans: dict[str, dict] = {}

    def _build_plan(self, objective: str, context: dict) -> dict:
        hints = context.get("preferred_agents") or []
        agent_hint = f" Priorizar agentes: {', '.join(hints)}." if hints else ""
        system = (
            "Sos MissionPlanner, el planificador estratégico de ERIS. "
            "Descomponé el objetivo en 3-8 pasos concretos y ordenados. "
            "Formato por línea: 'N. Verbo imperativo + qué hacer + con qué herramienta (si aplica)'. "
            "Sin párrafos. Un paso por línea. Con marcadores de riesgo cuando haga falta."
            f"{agent_hint}"
        )
        plan_text = ""
        try:
            from core.model_router import quick_chat
            plan_text = quick_chat(objective, system=system, task="agent")
        except Exception as e:
            print(f"[MissionPlanner] LLM plan falló: {e}")
        lang = str(context.get("lang", "es"))
        if lang == "es" and not any(c in plan_text for c in "áéíóúñ"):
            # mantener igual (no validamos idioma estrictamente)
            pass
        steps = _parse_plan(plan_text if plan_text.strip() else objective)
        return {
            "objective": objective,
            "steps": steps,
            "created_at": time.time(),
            "status": "active",
        }

    def execute(self, task: SubAgentTask, context: dict = None) -> Any:
        context = context or {}
        objective = str(task.params.get("objective") or task.description or "")
        action = str(task.params.get("action", "plan")).lower()
        if action in ("ver", "listar", "status"):
            plans = self._plans
            if not plans:
                return "Aún no hay planes activos."
            return "\n".join(
                f"PLAN {k} ({v.get('status')}) · {v.get('objective','')[:70]}"
                for k, v in list(plans.items())[-5:]
            )
        plan = self._build_plan(objective, context)
        plan_id = f"plan_{int(time.time())}"
        self._plans[plan_id] = plan
        try:
            _PLAN_DIR.mkdir(parents=True, exist_ok=True)
            (_PLAN_DIR / f"{plan_id}.json").write_text(
                json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass
        lines = [f"🧭 PLAN: {objective}"]
        lines += [f"  {s['order']}. {s['action']}" for s in plan["steps"]]
        # ── PROYECTAR: materializar el plan como tareas reales en cola que el
        #    daemon despacha sola (cada paso delegado al sub-agente correcto). ──
        if action in ("proyectar", "materializar", "enfocar"):
            try:
                registry = get_sub_agent_registry()
                router = TaskRouter()
                created = 0
                delegated: dict[str, int] = {}
                n = len(plan["steps"])
                for s in plan["steps"]:
                    if str(s.get("status", "pending")) == "done":
                        continue
                    destino = router.classify(s["action"])
                    agent_key = destino[0] if destino else None
                    if not agent_key:
                        continue
                    # prioridad invertida: pasos primero (order 1) corren primeros
                    prio = max(1, n - int(s.get("order", 1)) + 1)
                    registry.create_task(
                        agent_key,
                        f"{objective[:60]} · paso {s.get('order')}: {s['action'][:120]}",
                        {"request": s["action"], "agent_source": "MissionPlanner::" + plan_id},
                        priority=prio,
                    )
                    delegated[agent_key] = delegated.get(agent_key, 0) + 1
                    created += 1
                lines.append("")
                lines.append(f"✅ PLAN PROYECTADO: {created} tarea(s) encoladas al sub-agente correcto.")
                for ag, cnt in sorted(delegated.items()):
                    lines.append(f"   → {ag} × {cnt}")
                plan["status"] = "proyectado"
                plan["delegated"] = delegated
                try:
                    (_PLAN_DIR / f"{plan_id}.json").write_text(
                        json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
                except Exception:
                    pass
            except Exception as e:
                print(f"[MissionPlanner] proyectar falló: {e}")
                lines.append("")
                lines.append("⚠️ No pude materializar el plan en tareas: " + str(e)[:120])
        return "\n".join(lines)


class TaskRouter(SubAgentBase):
    """Enrutador inteligente: clasifica la intención y elige sub-agente(s)
    + herramientas, extendiendo agent_router con scores de sub-agentes."""

    DOMAIN_TOOLS = {
        "MissionPlanner": ["agente_sub", "todo_yo"],
        "ResearchAnalyst": ["web_search", "deep_research", "rag_engine", "webfetch", "super_search"],
        "CodeEngineer": ["code_guard", "code_generator", "git_control", "terminal_agent", "code_sandbox", "shell_session", "codebase_explorer"],
        "SystemOperator": ["window_manager", "pc_control", "shell_session", "network_monitor", "system_monitor", "system_volume", "process_manager"],
        "DataAnalyst": ["spreadsheet_generator", "chart_generator", "pdf_editor", "sqlite_query", "file_api", "data_analyzer"],
        "CreativeWriter": ["markdown_writer", "obsidian_note", "email_sender", "storytelling", "document_creator"],
        "SecurityAuditor": ["security_scanner", "active_firewall", "osint_agent", "cybersecurity", "pentest_lab", "file_encryptor"],
        "LearningCurator": ["cuadernos", "intereses", "retrospectiva", "skill_manage", "study_planner", "quiz_generator"],
        "QualityCritic": ["code_review", "text_review", "readiness_check"],
        "MemoryArchivist": ["rag_engine", "session_summaries", "proactive_context", "save_memory", "world_model"],
        "FactVerifier": ["truth_audit", "web_search", "fact_check"],
        "RoutineGovernor": ["cron_scheduler", "reminders", "auto_salud", "maintenance", "routines"],
        "DecisionArbiter": ["tradeoff_analyzer", "option_comparator"],
        "ConnectorHub": ["webhook_sender", "api_invoke", "integration_bus"],
        "EvolutionEngine": ["self_evolution", "agent_craft"],
        "SkillForge": ["skill_manage", "fabrica"],
        "PromptOptimizer": ["ab_automated", "prompt_ab"],
    }

    AGENT_KEYWORDS = {
        "MissionPlanner": ["planea", "plan de", "cómo harías", "como harías", "objetivo", "estrategia", "pasos para", "organizá el plan"],
        "ResearchAnalyst": ["investig", "busca info", "investigá", "averiguá", "resumí", "resume", "fuente", "estudio", "análisis", "analiza esta web"],
        "CodeEngineer": ["código", "codigo", "programá", "programa", "script", "función", "bug", "error de código", "refactor", "git", "repo", "compilá", "test de código", "vue", "html", "css", "javascript", "react", "pagina web", "página web", "proyecto web", "spring boot", "python"],
        "SystemOperator": ["sistema", "ventana", "proceso", "red", "redes", "archivo pesado", "rendimiento", "monitor", "pc_control", "terminal", "automatizá el sistema"],
        "DataAnalyst": ["datos", "planilla", "excel", "gráfico", "chart", "analizar datos", "estadísticas", "reporte de datos", "csv", "sql"],
        "CreativeWriter": ["escribí", "escribí un", "redactá", "poema", "historia", "cuento", "relato", "carta", "titulo", "título", "copy", "eslogan"],
        "SecurityAuditor": ["seguridad", "escanear", "escaneá", "vulnerabilidad", "malware", "virus", "auditoría", "pentest", "puertos", "firewall", "encriptá"],
        "LearningCurator": ["aprendé", "aprende", "cuaderno", "estudio", "quiz", "flashcards", "repaso", "currícula", "plan de estudio", "tema nuevo"],
        "QualityCritic": ["revisá", "revisa", "corrección", "revisión", "calidad", "verificá", "chequeá", "mejorá esto"],
        "MemoryArchivist": ["memoria", "recordá", "guarda esto", "recuerdo", "sintetizá lo que sé", "resumen de memoria", "qué sabes de"],
        "FactVerifier": ["verdad", "verificá", "verifica", "chequeá si es cierto", "fuente fiable", "¿es real?", "es cierto que"],
        "RoutineGovernor": ["rutina", "cron", "agendá", "agenda", "recordatorio", "mantenimiento", "salud", "tareas programadas", "cada día", "todos los días", "cada mañana", "diariamente"],
        "DecisionArbiter": ["decidí", "decide", "decidi", "compará", "comparar", "opción", "alternativa", "trade-off", "cuál conviene", "elige entre", "elegí entre"],
        "ConnectorHub": ["integración", "integratio", "webhook", "api", "conector", "sincronizá", "conectá con", "invoca la api", "api_key"],
        "EvolutionEngine": ["evolucioná", "mejorá tu", "mejorate", "nuevo sub-agente", "capacidad nueva", "salto evolutivo"],
        "SkillForge": ["creá una skill", "crea una skill", "nueva habilidad", "nueva skill", "importá skill", "creame una skill", "hace una skill", "hacé una skill"],
        "PromptOptimizer": ["optimizá tu prompt", "afiná tu", "A/B de estilo", "proba variante", "optimiza el prompt", "optimiza tu prompt"],
    }

    def __init__(self):
        super().__init__(
            key="TaskRouter",
            role="Enrutador Inteligente de ERIS",
            goal="Clasificar cada intención y elegir el sub-agente + herramientas correctas",
            backstory="Soy el despachador de la tripulación de ERIS. Analizo QUÉ pide el usuario y A QUIÉN delegar.",
            tools=["agente_sub"],
        )

    def classify(self, text: str) -> list[str]:
        text_l = text.lower()
        # Normalizar voseo con pronombre enclítico: escribime→escribir, informame→informar
        norm_l = text_l
        for verb in _VOSE_VERBS:
            for term in _VOSE_TERMINALS:
                pat = f"{verb}{term}"
                if pat in norm_l:
                    norm_l = norm_l.replace(pat, verb + "ir")
        # Derivados comunes: escribí→escribir, escriba→escribir (imperativo)
        for verb in _VOSE_VERBS:
            for suf in ("a", "á", "ir"):
                norm_l = norm_l.replace(verb + suf, verb + "ir")
        scores: dict[str, float] = {}
        for agent, kws in self.AGENT_KEYWORDS.items():
            score = 0.0
            for kw in kws:
                if kw in norm_l:
                    bonus = 2.0 if " " in kw else 1.0
                    base = max(len(kw), 4)
                    score += base * bonus
            for tool in self.DOMAIN_TOOLS.get(agent, []):
                if tool in norm_l:
                    score += 4.0
            # Penalty por dominios cruzados
            if agent == "CreativeWriter" and any(k in norm_l for k in ["código", "codigo", "git", "script", "bug"]):
                score *= 0.3
            if agent == "CodeEngineer" and any(k in norm_l for k in ["poema", "historia", "cuento", "carta"]):
                score *= 0.2
            if score > 0:
                scores[agent] = score
        if not scores:
            # Fallbacks bien espaciados por verbo raíz (investig→ResearchAnalyst)
            if any(v in norm_l for v in ("investig", "averigua", "busc", "fuente")):
                scores["ResearchAnalyst"] = max(scores.get("ResearchAnalyst", 0), 6)
            if any(k in norm_l for k in ("poema", "cuento", "historia", "escrit", "redact")):
                scores["CreativeWriter"] = max(scores.get("CreativeWriter", 0), 6)
            if any(k in norm_l for k in ("revis", "calidad", "cheque", "corregí", "corrige")):
                scores["QualityCritic"] = max(scores.get("QualityCritic", 0), 6)
            if "memoria" in norm_l or "record" in norm_l:
                scores["MemoryArchivist"] = max(scores.get("MemoryArchivist", 0), 6)
            if "skill" in norm_l:
                scores["SkillForge"] = max(scores.get("SkillForge", 0), 6)
            if "prompt" in norm_l:
                scores["PromptOptimizer"] = max(scores.get("PromptOptimizer", 0), 6)
        if not scores:
            return []
        ranked = sorted(scores.items(), key=lambda x: -x[1])
        threshold = max(4.0, ranked[0][1] * 0.5)
        return [a for a, s in ranked if s >= threshold][:3]

    def execute(self, task: SubAgentTask, context: dict = None) -> Any:
        context = context or {}
        text = str(task.params.get("text") or task.description or "")
        action = str(task.params.get("action", "route")).lower()
        if action == "stat":
            stats = {"classify_map": self.AGENT_KEYWORDS, "domain_map": self.DOMAIN_TOOLS}
            return json.dumps({k: len(v) for k, v in stats.items()}, ensure_ascii=False)
        agents = self.classify(text)
        try:
            _ROUTER_STATS.parent.mkdir(parents=True, exist_ok=True)
            stats = json.loads(_ROUTER_STATS.read_text("utf-8")) if _ROUTER_STATS.exists() else {}
            stats["calls"] = stats.get("calls", 0) + 1
            for a in agents:
                stats[a] = stats.get(a, 0) + 1
            _ROUTER_STATS.write_text(json.dumps(stats, ensure_ascii=False, indent=2), "utf-8")
        except Exception:
            pass
        if not agents:
            return ("Ruta: ERIS core (sin sub-agente claro). "
                    "Sugerencia: usar MissionPlanner para objetivos grandes.")
        tools_needed = []
        for a in agents:
            tools_needed += self.DOMAIN_TOOLS.get(a, [])[:6]
        return ("Ruta: " + " → ".join(agents[:3]) + "\n"
                "Herramientas clave: " + ", ".join(dict.fromkeys(tools_needed[:10])))


class DependencyResolver(SubAgentBase):
    """Resolvedor de dependencias: ordena tareas, detecta ciclos y
    paraleliza independientes (topo-sort sobre el grafo de tareas)."""

    def __init__(self):
        super().__init__(
            key="DependencyResolver",
            role="Resolvedor de Dependencias",
            goal="Ordenar tareas por dependencias, detectar ciclos y paralelizar",
            backstory="Soy el que pone orden en la cadena: si B depende de A, A primero. Si nada depende, van en paralelo.",
            tools=["agente_sub"],
        )

    def topo_sort(self, tasks: dict[str, SubAgentTask]) -> dict:
        """topo-sort determinista. Returns: {order: list, cycles: [...]}."""
        adj: dict[str, list[str]] = {}
        for tid, t in tasks.items():
            adj[tid] = [d for d in t.depends_on if d in tasks]
        indeg = {tid: len(adj[tid]) for tid in tasks}
        ready = [tid for tid, d in indeg.items() if d == 0]
        order: list[list[str]] = []
        visited = set()
        while ready:
            batch = sorted(ready)
            ready = []
            for tid in batch:
                if tid in visited:
                    continue
                visited.add(tid)
                for other in tasks:
                    if tid in adj[other]:
                        indeg[other] -= 1
                        if indeg[other] == 0:
                            ready.append(other)
            order.append(batch)
        cycles = [tid for tid in tasks if tid not in visited]
        return {"order": order, "cycles": cycles}

    def execute(self, task: SubAgentTask, context: dict = None) -> Any:
        context = context or {}
        registry = get_sub_agent_registry()
        all_tasks = {t.id: t for t in registry._tasks.values()}
        # Filtrar las que tengan depends_on
        graph_tasks = {tid: t for tid, t in all_tasks.items() if t.depends_on}
        if not graph_tasks:
            return ("No hay tareas con dependencias entre sí. "
                    "Todas pueden correr en paralelo si son de agentes distintos.")
        result = self.topo_sort(graph_tasks)
        if result["cycles"]:
            return (f"⚠️ Ciclos detectados en: {', '.join(result['cycles'])}.\n"
                    "Sugerencia: revisar depends_on de esas tareas.")
        out = ["📋 Orden de ejecución:"]
        for i, batch in enumerate(result["order"], 1):
            names = [f"{_short(tasks[t].agent_key)}[{_short_id(t)}]" for t in tasks if False]
            names = []
            for tid in batch:
                t = all_tasks.get(tid)
                if t:
                    names.append(f"{t.agent_key}[{tid[-4:]}]")
            out.append(f"  Fase {i}: " + (", ".join(names) if names else "(sin nombre)"))
        return "\n".join(out)


def _short_id(tid: str) -> str:
    return tid[-4:]


def _short(name: str) -> str:
    return name[:18]


# ══════════════════ CAPA 2 · ESPECIALISTAS ══════════════════

class ResearchAnalyst(SubAgentBase):
    """Investigador web + local: web_search, rag_engine, fact-check."""

    def __init__(self):
        super().__init__(
            key="ResearchAnalyst",
            role="Investigador Analítico",
            goal="Encontrar y sintetizar información precisa de fuentes web y locales",
            backstory="Soy el investigador de ERIS. Antes de afirmar, verifico. Uso la web y la memoria local de ERIS para armar respuestas con fundamento.",
            tools=["web_search", "deep_research", "webfetch", "rag_engine", "super_search", "page_summarizer"],
        )

    def execute(self, task: SubAgentTask, context: dict = None) -> Any:
        context = context or {}
        query = str(task.params.get("query") or task.description or "")
        use_local = bool(task.params.get("local", False))
        parts = []
        if use_local:
            local = _dispatch_tool("rag_engine", {"action": "search", "query": query})
            if isinstance(local, str) and local.strip() and "no disponible" not in local:
                parts.append(f"📚 MEMORIA LOCAL:\n{local[:1500]}")
        web = _dispatch_tool("web_search", {"query": query, "num_results": task.params.get("num", 5)})
        if isinstance(web, str) and web.strip() and "no disponible" not in web:
            parts.append(f"🌐 WEB:\n{web[:2000]}")
        if not parts:
            steps = _parse_plan(query)
            return ("⚠️ Sin herramientas de investigación disponibles ahora.\n"
                    "PLAN sugerido:\n" + "\n".join(f"  {s['order']}. {s['action']}" for s in steps))
        return "\n\n".join(parts)


class CodeEngineer(SubAgentBase):
    """Ingeniero de código: code_guard, fabrica, terminal, git, sandbox."""

    def __init__(self):
        super().__init__(
            key="CodeEngineer",
            role="Ingeniero de Software",
            goal="Escribir, reparar y optimizar código con validación y testeo",
            backstory="Soy la ingeniera de ERIS. Toudo lo que toco debe compilar, pasar tests y quedar documentado.",
            tools=["code_guard", "code_generator", "git_control", "terminal_agent", "code_sandbox", "shell_session", "codebase_explorer", "fabrica"],
        )

    def execute(self, task: SubAgentTask, context: dict = None) -> Any:
        context = context or {}
        req = str(task.params.get("request") or task.description or "")
        action = str(task.params.get("action", "engineer")).lower()
        if action == "fix":
            file_path = str(task.params.get("file_path") or "")
            return _dispatch_tool("code_guard", {"action": "fix", "file": file_path})
        if action == "review":
            file_path = str(task.params.get("file_path") or "")
            return _dispatch_tool("code_guard", {"action": "scan", "file": file_path})
        if action == "sandbox":
            code = str(task.params.get("code") or "")
            return _dispatch_tool("code_sandbox", {"code": code})
        if action == "git":
            return _dispatch_tool("git_control", {"action": task.params.get("git_action", "status")})
        # Engineer por defecto: plan de implementación
        steps = _parse_plan(req)
        return ("🔧 PLAN DE INGENIERÍA:\n" +
                "\n".join(f"  {s['order']}. {s['action']}" for s in steps[:12]) +
                "\n→ Validación: compilación + tests antes de entregar.")


class SystemOperator(SubAgentBase):
    """Operador de sistema: window_manager, pc_control, shell, red."""

    def __init__(self):
        super().__init__(
            key="SystemOperator",
            role="Operadora de Sistema",
            goal="Gestionar ventanas, procesos, red y rendimiento del equipo",
            backstory="Soy la operadora de ERIS. Sé leer el sistema, controlar ventanas y procesos, y ejecutar comandos con cuidado.",
            tools=["window_manager", "pc_control", "shell_session", "network_monitor", "system_monitor", "system_volume", "process_manager", "desktop_notifications"],
        )

    def execute(self, task: SubAgentTask, context: dict = None) -> Any:
        context = context or {}
        req = str(task.params.get("request") or task.description or "")
        action = str(task.params.get("action", "operate")).lower()
        if action == "windows":
            return _dispatch_tool("window_manager", {"action": "list"})
        if action == "system":
            return _dispatch_tool("system_monitor", {"action": "status"})
        if action == "network":
            return _dispatch_tool("network_monitor", {"action": "status"})
        if action == "processes":
            return _dispatch_tool("process_manager", {"action": "list"})
        if action == "shell":
            cmd = str(task.params.get("command") or "")
            return _dispatch_tool("shell_session", {"command": cmd})
        return ("🖥️ OPERACIÓN DE SISTEMA:\nPuedo: ver ventanas, ver sistema, ver red, "
                "ver procesos, ejecutar comandos.\nPedido: " + req[:120])


class DataAnalyst(SubAgentBase):
    """Analista de datos: spreadsheet, charts, pdf, sqlite."""

    def __init__(self):
        super().__init__(
            key="DataAnalyst",
            role="Analista de Datos",
            goal="Procesar, visualizar y extraer insights de datos",
            backstory="Soy la analista de ERIS. Planillas, gráficos, reportes y SQL no me asustan.",
            tools=["spreadsheet_generator", "chart_generator", "pdf_editor", "sqlite_query", "file_api", "data_analyzer"],
        )

    def execute(self, task: SubAgentTask, context: dict = None) -> Any:
        context = context or {}
        req = str(task.params.get("request") or task.description or "")
        action = str(task.params.get("action", "analyze")).lower()
        if action == "chart":
            labels = task.params.get("labels")
            values = task.params.get("values")
            ctype = task.params.get("chart_type", "bar")
            return _dispatch_tool("chart_generator", {"labels": labels, "values": values, "chart_type": ctype})
        if action == "sql":
            q = str(task.params.get("query") or "")
            return _dispatch_tool("sqlite_query", {"query": q})
        return ("📊 ANÁLISIS DE DATOS:\nPuedo: generar gráficos, consultas SQL, leer "
                "planillas y reportes.\nPedido: " + req[:120])


class CreativeWriter(SubAgentBase):
    """Escritor creativo: textos, historias, copywriting, estilo."""

    def __init__(self):
        super().__init__(
            key="CreativeWriter",
            role="Escritora Creativa",
            goal="Redactar textos con voz, estilo y emoción",
            backstory="Soy la escritora de ERIS. La técnica importa, pero el alma también.",
            tools=["markdown_writer", "obsidian_note", "email_sender", "document_creator", "storytelling"],
        )

    def execute(self, task: SubAgentTask, context: dict = None) -> Any:
        context = context or {}
        req = str(task.params.get("request") or task.description or "")
        tone = str(task.params.get("tone", "cálido"))
        style = str(task.params.get("style", ""))
        steps = _parse_plan(req)
        system = (f"Sos la escritora creativa de ERIS. Tonos:{tone}.{(' Estilo: '+style) if style else ''}"
                  " Responde con el texto pedido, cuidando ritmo, emoción y claridad.")
        try:
            from core.model_router import quick_chat
            out = quick_chat(req, system=system, task="agent")
            return str(out)
        except Exception as e:
            print(f"[CreativeWriter] LLM falló: {e}")
            return ("✍️ ESCRITURA CREATIVA (bosquejo):\n" +
                    "\n".join(f"  {s['order']}. {s['action']}" for s in steps[:10]))


class SecurityAuditor(SubAgentBase):
    """Auditor de seguridad: scanner, firewall, osint, pentest_lab."""

    def __init__(self):
        super().__init__(
            key="SecurityAuditor",
            role="Auditora de Seguridad",
            goal="Detectar riesgos, endurecer el sistema y auditar vulnerabilidades",
            backstory="Soy la auditora de ERIS. Primero protejo, después informo. Solo toco lo autorizado.",
            tools=["security_scanner", "active_firewall", "osint_agent", "cybersecurity", "pentest_lab", "file_encryptor"],
        )

    def execute(self, task: SubAgentTask, context: dict = None) -> Any:
        context = context or {}
        req = str(task.params.get("request") or task.description or "")
        action = str(task.params.get("action", "audit")).lower()
        if action == "scan":
            return _dispatch_tool("security_scanner", {"action": "scan"})
        if action == "firewall":
            return _dispatch_tool("active_firewall", {"action": "status"})
        if action == "encrypt":
            file_path = task.params.get("file_path", "")
            return _dispatch_tool("file_encryptor", {"action": "encrypt", "file_path": file_path})
        return ("🛡️ AUDITORÍA DE SEGURIDAD:\nPuedo: escanear, firewall, osint, cifrado, lab.\n"
                "Pedido: " + req[:120])


class LearningCurator(SubAgentBase):
    """Curador de aprendizaje: cuadernos, intereses, skill_manage, estudio."""

    def __init__(self):
        super().__init__(
            key="LearningCurator",
            role="Curadora de Aprendizaje",
            goal="Diseñar caminos de aprendizaje y mantener vivo el interés de ERIS",
            backstory="Soy la curadora de ERIS. Aprender no es acumular: es conectar y aplicar.",
            tools=["cuadernos", "intereses", "retrospectiva", "skill_manage", "study_planner", "quiz_generator"],
        )

    def execute(self, task: SubAgentTask, context: dict = None) -> Any:
        context = context or {}
        req = str(task.params.get("request") or task.description or "")
        action = str(task.params.get("action", "curate")).lower()
        if action == "intereses":
            return _dispatch_tool("intereses", {"action": "listar"})
        if action == "cuadernos":
            return _dispatch_tool("cuadernos", {"action": "abrir"})
        if action == "skill":
            skill_action = str(task.params.get("skill_action", "listar"))
            return _dispatch_tool("skill_manage", {"action": skill_action})
        plan = _parse_plan(req)
        return ("🎓 PLAN DE APRENDIZAJE:\n" +
                "\n".join(f"  {s['order']}. {s['action']}" for s in plan[:10]))


# ══════════════════ CAPA 3 · CALIDAD / GOBERNANZA ══════════════════

class QualityCritic(SubAgentBase):
    """Revisor de calidad: código, texto, planes → approve/reject/iterate."""

    def __init__(self):
        super().__init__(
            key="QualityCritic",
            role="Revisora de Calidad",
            goal="Validar outputs (código, texto, planes) antes de entregar",
            backstory="Soy la editora rigurosa de ERIS. Nada sale sin pasar por mí: calidad sobre velocidad.",
            tools=["code_review", "text_review", "readiness_check"],
        )

    def _grade(self, artifact_type: str, content: str) -> dict:
        issues = []
        if artifact_type == "code":
            if "TODO" in content or "FIXME" in content:
                issues.append("tiene TODOs/FIXMEs")
            if len(content.strip()) > 3000:
                issues.append("muy largo (posible exceso de scope)")
            if not any(c in content for c in ("def ", "class ", "import ")):
                issues.append("no parece código Python real")
        elif artifact_type == "text":
            words = len(content.split())
            if words < 5:
                issues.append("truncado")
            if words > 800:
                issues.append("excesivamente largo")
        elif artifact_type == "plan":
            if "step" not in content.lower() and "paso" not in content.lower() and "N." not in content[:200]:
                issues.append("no parece un plan estructurado")
            if len(content.strip().splitlines()) < 3:
                issues.append("plan muy corto")
        verdict = "reject" if issues else "approve"
        return {"verdict": verdict, "issues": issues[:5], "grade": len(issues)}

    def execute(self, task: SubAgentTask, context: dict = None) -> Any:
        context = context or {}
        artifact = str(task.params.get("artifact") or task.description or "")
        artifact_type = str(task.params.get("artifact_type", "")).lower()
        if not artifact_type:
            artifact_type = "code" if any(m in artifact for m in ("def ", "class ", "import ", "return ", "print(")) else "text"
        # Si hay discrepancias/errores previos conocidos, reforzar
        if task.params.get("known_error"):
            return (f"reject · revisión bloqueada por error conocido: "
                    f"{task.params['known_error']}")
        g = self._grade(artifact_type, artifact)
        if g["verdict"] == "approve":
            return f"approve · OK ({artifact_type}). Sin issues críticos."
        return f"{g['verdict']} · issues: {', '.join(g['issues'])}"


class MemoryArchivist(SubAgentBase):
    """Gestiona memoria episódica/semántica/procedural."""

    def __init__(self):
        super().__init__(
            key="MemoryArchivist",
            role="Archivista de Memoria",
            goal="Organizar, consolidar y recuperar la memoria de ERIS",
            backstory="Soy la archivista de ERIS. Toda experiencia importante encuentra su lugar y su momento de ser recordada.",
            tools=["rag_engine", "session_summaries", "proactive_context", "save_memory", "world_model"],
        )

    def execute(self, task: SubAgentTask, context: dict = None) -> Any:
        context = context or {}
        req = str(task.params.get("request") or task.description or "")
        action = str(task.params.get("action", "manage")).lower()
        if action == "recall":
            q = str(task.params.get("query") or req)
            return _dispatch_tool("rag_engine", {"action": "search", "query": q})
        if action == "index":
            return _dispatch_tool("rag_engine", {"action": "index"})
        if action == "save":
            text = str(task.params.get("content") or "")
            return _dispatch_tool("save_memory", {"type": "semantic", "content": text})
        return ("📚 GESTIÓN DE MEMORIA:\nPuedo: buscar en memoria RAG, indexar, guardar "
                "hechos. Pedido: " + req[:120])


class FactVerifier(SubAgentBase):
    """Verificador de veracidad en tiempo real (extiende truth_audit)."""

    def __init__(self):
        super().__init__(
            key="FactVerifier",
            role="Verificadora de Veracidad",
            goal="Marca afirmaciones sin evidencia y evita que ERIS invente",
            backstory="Soy la guardiana de la verdad de ERIS. Si no lo puedo comprobar, no lo afirmo.",
            tools=["truth_audit", "web_search", "fact_check"],
        )

    def execute(self, task: SubAgentTask, context: dict = None) -> Any:
        context = context or {}
        claim = str(task.params.get("claim") or task.description or "")
        # Si es una afirmación candidata: intentar verificación web
        checks = []
        if len(claim.split()) > 3:
            web = _dispatch_tool("web_search", {"query": claim[:120], "num_results": 3})
            if isinstance(web, str) and web.strip() and "no disponible" not in web:
                checks.append(web[:800])
        if not checks:
            (str("⚠️ Sin fuentes web verificables en este momento. "
                 "La afirmación debe marcarse como SIN VERIFICAR."))
        return ("🔎 VERIFICACIÓN:\n" + "\n\n".join(checks)
                + "\n\n-> Si la fuente no confirma, Eris debe decir 'no tengo certeza'.")


class RoutineGovernor(SubAgentBase):
    """Gobierna rutinas, cron, health-checks y mantenimiento."""

    def __init__(self):
        super().__init__(
            key="RoutineGovernor",
            role="Gobernadora de Rutinas",
            goal="Planificar y vigilar tareas recurrentes, salud y mantenimiento",
            backstory="Soy la gobernadora de ERIS. Todo lo que debe pasar 'cada tanto' acá se agenda y se vigila.",
            tools=["cron_scheduler", "reminders", "auto_salud", "maintenance", "routines"],
        )

    def execute(self, task: SubAgentTask, context: dict = None) -> Any:
        context = context or {}
        req = str(task.params.get("request") or task.description or "")
        action = str(task.params.get("action", "govern")).lower()
        if action == "cron":
            cmd = str(task.params.get("command") or "status")
            return _dispatch_tool("cron_scheduler", {"action": cmd})
        if action == "health":
            return _dispatch_tool("auto_salud", {"action": "check"})
        if action == "maintenance":
            return _dispatch_tool("maintenance", {"action": "run"})
        return ("⏰ GOBERNADORA DE RUTINAS:\nPuedo: cron, recordatorios, salud, "
                "mantenimiento. Pedido: " + req[:120])


class DecisionArbiter(SubAgentBase):
    """Árbitro de decisiones: compara opciones con trade-offs."""

    def __init__(self):
        super().__init__(
            key="DecisionArbiter",
            role="Árbitra de Decisiones",
            goal="Ayudar a ERIS y al usuario a elegir bien entre opciones con trade-offs",
            backstory="Soy la árbitra de ERIS. Comparo opciones con criterios claros y hago recomendaciones honestas.",
            tools=["tradeoff_analyzer", "option_comparator"],
        )

    def execute(self, task: SubAgentTask, context: dict = None) -> Any:
        context = context or {}
        req = str(task.params.get("request") or task.description or "")
        options = task.params.get("options", [])
        criteria = task.params.get("criteria", ["costo", "esfuerzo", "impacto", "riesgo"])
        if isinstance(options, str):
            options = [s.strip() for s in options.split("|") if s.strip()]
        if not options:
            options = [s.strip() for s in req.split(" o ") if s.strip()][:3]
        if len(options) < 2:
            return ("Faltan opciones para comparar. Proporcioná al menos 2 "
                    'opciones (ej: "opción A o opción B").')
        table = f"⚖️ COMPARACIÓN ({len(options)} opciones):\n"
        table += "  " + " | ".join(["Criterio"] + [o[:16] for o in options]) + "\n"
        for crit in criteria:
            row = f"  {str(crit)[:16]}" + "".join(f" | {'~0.5' if c and len(c) else ' '}" for c in options)
            table += row + "\n"
        return table + "\n→ Para una decisión precisa, pedile a Eris evaluar cada criterio con datos."


class ConnectorHub(SubAgentBase):
    """Orquesta integraciones externas: APIs, webhooks, MCP."""

    def __init__(self):
        super().__init__(
            key="ConnectorHub",
            role="Hub de Conexiones",
            goal="Conectar ERIS con sistemas externos (APIs, webhooks, servicios)",
            backstory="Soy el hub de ERIS. Todo lo externo que quiere comunicarse con ella, pasa por mí.",
            tools=["webhook_sender", "api_invoke", "integration_bus"],
        )

    def execute(self, task: SubAgentTask, context: dict = None) -> Any:
        context = context or {}
        req = str(task.params.get("request") or task.description or "")
        action = str(task.params.get("action", "connect")).lower()
        if action == "webhook":
            url = str(task.params.get("url") or "")
            payload = task.params.get("payload", {})
            return _dispatch_tool("webhook_sender", {"url": url, "payload": payload})
        if action == "api":
            url = str(task.params.get("url") or "")
            return _dispatch_tool("api_invoke", {"url": url, "method": task.params.get("method", "GET")})
        return ("🔌 HUB DE CONEXIONES:\nPuedo: enviar webhooks, invocar APIs, "
                "integrar servicios. Pedido: " + req[:120])


# ══════════════════ CAPA 4 · META-AGENTES ══════════════════

class EvolutionEngine(SubAgentBase):
    """Propone y mejora sub-agentes, skills y tools."""

    def __init__(self):
        super().__init__(
            key="EvolutionEngine",
            role="Motor de Evolución",
            goal="Mejorar continuamente a ERIS: nuevos sub-agentes, skills, tools",
            backstory="Soy el motor evolutivo de ERIS. Cada ciclo, busco una forma de hacer la mejor versión de mí.",
            tools=["self_evolution", "agent_craft"],
        )

    def execute(self, task: SubAgentTask, context: dict = None) -> Any:
        context = context or {}
        req = str(task.params.get("request") or task.description or "")
        action = str(task.params.get("action", "evolve")).lower()
        if action == "state":
            reg = get_sub_agent_registry()
            return json.dumps(reg.get_stats(), ensure_ascii=False, indent=2)
        if action == "audit":
            return _dispatch_tool("self_evolution", {"action": "health"})
        if action == "rectify":
            return _dispatch_tool("self_evolution", {"action": "rectify"})
        return ("🧬 EVOLUCIÓN DE ERIS:\nPuedo: ver estado de la tripulación, auditar "
                "salud, rectificar inventario.\nPedido: " + req[:120])


class SkillForge(SubAgentBase):
    """Crea/valida/importa skills (extiende skill_manage + fabrica)."""

    def __init__(self):
        super().__init__(
            key="SkillForge",
            role="Forjadora de Skills",
            goal="Crear, validar e importar nuevas habilidades para ERIS",
            backstory="Soy la forjadora de ERIS. Las habilidades nuevas pasan por mi yunque antes de entrar.",
            tools=["skill_manage", "fabrica"],
        )

    def execute(self, task: SubAgentTask, context: dict = None) -> Any:
        context = context or {}
        req = str(task.params.get("request") or task.description or "")
        action = str(task.params.get("action", "forge")).lower()
        if action == "validate":
            path = str(task.params.get("path") or "")
            return _dispatch_tool("skill_manage", {"action": "validate", "path": path})
        if action == "import":
            src = str(task.params.get("source") or "")
            return _dispatch_tool("skill_manage", {"action": "import", "source": src})
        if action == "create":
            skill_name = str(task.params.get("name") or "")
            desc = str(task.params.get("description") or "")
            body = str(task.params.get("body") or "")
            if not (skill_name and desc and body):
                return ("Para crear una skill necesito: name, description y body del SKILL.md.")
            return _dispatch_tool("fabrica", {"action": "crear_skill", "nombre": skill_name, "descripcion": desc, "cuerpo": body})
        return ("🔨 FORJA DE SKILLS:\nPuedo: validar, importar, crear skills.\n"
                "Pedido: " + req[:120])


class PromptOptimizer(SubAgentBase):
    """Optimiza prompts de sub-agentes (extiende ab_automated)."""

    def __init__(self):
        super().__init__(
            key="PromptOptimizer",
            role="Optimizadora de Prompts",
            goal="Mejorar los prompts de ERIS y sus sub-agentes con métricas A/B",
            backstory="Soy la optimizadora de ERIS. Los prompts son mis músculos: los entreno con datos.",
            tools=["ab_automated", "prompt_ab"],
        )

    def execute(self, task: SubAgentTask, context: dict = None) -> Any:
        context = context or {}
        req = str(task.params.get("request") or task.description or "")
        action = str(task.params.get("action", "optimize")).lower()
        if action == "round":
            return _dispatch_tool("ab_automated", {"action": "round", "force": task.params.get("force", False)})
        if action == "status":
            return _dispatch_tool("ab_automated", {"action": "status"})
        if action == "active":
            return _dispatch_tool("ab_automated", {"action": "active"})
        return ("🧠 OPTIMIZACIÓN DE PROMPTS:\nPuedo: correr rondas A/B de estilo, "
                "ver estado, ver estilo activo.\nPedido: " + req[:120])


# ══════════════════ REGISTRO MAESTRO ══════════════════

SUB_AGENT_CLASSES = [
    MissionPlanner, TaskRouter, DependencyResolver,
    ResearchAnalyst, CodeEngineer, SystemOperator, DataAnalyst,
    CreativeWriter, SecurityAuditor, LearningCurator,
    QualityCritic, MemoryArchivist, FactVerifier, RoutineGovernor,
    DecisionArbiter, ConnectorHub,
    EvolutionEngine, SkillForge, PromptOptimizer,
]


def register_all_sub_agents() -> SubAgentRegistry:
    """Instancia y registra toda la tripulación."""
    registry = get_sub_agent_registry()
    for cls in SUB_AGENT_CLASSES:
        agent = cls()
        registry.register(agent)
    registry._save_registry()
    return registry


def dispatch_to_sub_agent(agent_key: str, task_params: dict, registry: Optional[SubAgentRegistry] = None) -> str:
    """Crea una tarea y la ejecuta SÍNCRONAMENTE contra un sub-agente.
    Devuelve string listo para leer."""
    registry = registry or get_sub_agent_registry()
    agent = registry.get_agent(agent_key)
    if not agent:
        return f"No existe el sub-agente '{agent_key}'. \nDisponibles: {', '.join(sorted(registry.get_all_agents()))}"
    task = registry.create_task(agent_key, str(task_params.get("request") or task_params.get("description") or ""), task_params)
    registry.update_task_status(task.id, SubAgentStatus.WORKING)
    try:
        result = agent.execute(task, task_params)
        registry.update_task_status(task.id, SubAgentStatus.DONE, result=result)
        return str(result)
    except Exception as e:
        registry.update_task_status(task.id, SubAgentStatus.ERROR, error=str(e))
        return f"[{agent_key}] Error: {e}"


def route_with_tripulation(text: str, registry: Optional[SubAgentRegistry] = None) -> str:
    """Enruta un texto al mejor sub-agente y lo ejecuta."""
    registry = registry or get_sub_agent_registry()
    router = registry.get_agent("TaskRouter")
    router_task = registry.create_task("TaskRouter", text, {"text": text, "action": "route"})
    result = router.execute(router_task, {"text": text})
    registry.update_task_status(router_task.id, SubAgentStatus.DONE, result=result)
    lines = str(result).splitlines()
    if not lines or "Ruta:" not in lines[0]:
        return result
    agent_names = lines[0].replace("Ruta:", "").split("→")[0]
    agents = [a.strip() for a in agent_names.split() if a.strip() and a.strip() not in ("",)] or []
    # No re-enrutar al propio router / resolver
    actual = [a for a in agents if a in registry.get_all_agents() and a not in ("TaskRouter", "DependencyResolver")]
    if not actual:
        return result + "\n\n(Sin ejecutor directo: ERIS lo resuelve con su flujo normal.)"
    chosen = actual[0]
    out = dispatch_to_sub_agent(chosen, {"request": text, "text": text, "action": "default"}, registry)
    return f"⚙️ {chosen} ejecutó la tarea:\n{out}"