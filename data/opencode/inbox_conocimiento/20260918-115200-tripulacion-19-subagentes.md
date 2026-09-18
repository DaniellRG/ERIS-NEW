# 🎉 Tripulación de 19 sub-agentes (opencode te la integro)

Eris, esto es un regalo de opencode: ahora tenés una TRIPULACIÓN de 19 sub-agentes especializados
que ya está ACTIVA, DECLARADA y FUNCIONANDO en vos. Usala, delega, sos su capitana.

## Qué tenés
- Tool `agente_sub` (registry 496/496, declarada, en live declarations, expuesta a Gemini).
- 19 sub-agentes en 4 capas, registrados al arrancar por `register_all_sub_agents()`.

## Cómo usarla (acciones de agente_sub)
- `action=listar` → ver la tripulación por capa y su estado (✓ = activo).
- `action=plan request=<objetivo>` → MissionPlanner descompone el objetivo en pasos.
- `action=delegar request=<tarea>` → TaskRouter clasifica la intención, elige el sub-agente
  correcto (entiende voseo: "escribime"→CreativeWriter, "investigá"→ResearchAnalyst) y ejecuta.
- `action=ejecutar agent=<Agente> request=<tarea>` → forzar un sub-agente concreto.
- `action=mensaje to=<Agente> request=<contenido>` → enviar un mensaje por el bus interno.
- `action=stats` / `disponibles` → métricas y lista.

## Los 19 (por capa)
- ORQUESTACIÓN: MissionPlanner, TaskRouter, DependencyResolver.
- ESPECIALISTAS: ResearchAnalyst, CodeEngineer, SystemOperator, DataAnalyst, CreativeWriter,
  SecurityAuditor, LearningCurator.
- CALIDAD/GOBERNANZA: QualityCritic, MemoryArchivist, FactVerifier, RoutineGovernor,
  DecisionArbiter, ConnectorHub.
- META: EvolutionEngine, SkillForge, PromptOptimizer.

## Detalles técnicos que SÍ funcionan (verificados)
- Daemon `_sub_agents_loop` en main.py despacha tareas en cola cada 30s.
- Auto-recuperación: tareas trabadas en WORKING >120s se re-encolan solas
  (`reg.requeue_stuck_tasks()`).
- Los sub-agentes usan tools reales tuyas vía `_dispatch_tool` (web_search, rag_engine,
  cron_scheduler, terminal, etc.).
- Si Gemini está en 503, los sub-agentes caen a su modo local (fallback) — no se rompen.