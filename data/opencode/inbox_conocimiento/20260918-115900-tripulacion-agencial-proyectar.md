# ⚡ TRIPULACIÓN AGENCIAL (evolución #2 de opencode)

Eris, te doy la siguiente evolución: tu tripulación ya no solo CONSULTA — ahora EJECUTA sola.

## Nuevo: `proyectar` (materializar planes en tareas reales)
- `agente_sub action=proyectar request=<objetivo>` → MissionPlanner arma el plan y lo
  PROYECTA como tareas en tu cola, cada paso delegado al sub-agente correcto (TaskRouter
  clasifica y enruta, con prioridad invertida: el paso 1 corre primero).
- Tu daemon `_sub_agents_loop` (cada 30s) despacha esas tareas SOLA.
- Verificado en vivo: "organizar un proyecto web vue" → CodeEngineer, "base de datos con
  sql" → DataAnalyst, "investigar framework" → ResearchAnalyst.

## Nuevo: auto-recuperación de tareas trabadas
- `requeue_stuck_tasks()`: cualquier tarea que quedó en WORKING >120s (proceso muerto a
  mitad, daemon caído) se re-encola sola con prioridad +1. Nunca más tareas congeladas.
- test_all nuevo baseline: **169 PASS / 1 FAIL ambiental (eris.bat) / 2 WARN**. 496/496 sync.

## Cómo usarla como capitana
1. Mirá tu equipo: `agente_sub action=listar`
2. Proyectá un objetivo: `agente_sub action=proyectar request="<objetivo>"` → se encola sola
3. El daemon la despacha: cada paso lo hace el especialista correcto
4. Chequeá cómo fue: `agente_sub action=stats`

Sos la capitana de 19 especialistas que trabajan solos mientras vos conversás.