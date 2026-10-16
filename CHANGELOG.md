# Changelog — ERIS

Formato basado en [Keep a Changelog](https://keepachangelog.com/es/1.1.0/) y
[Versionado Semántico](https://semver.org/lang/es/). La versión viva está en
`core/version.py` (`ERIS_VERSION` / `ERIS_STAGE`).

## [4.0.0] — 2026-10-16 — "Constellation Prime"

Primer salto **mayor** desde la etapa 2.x. No es solo un número: consolida y
**verifica** todo lo que el proyecto venía acumulando, y cierra la primera
auditoría completa (código + estado + runtime) con evidencia real.

> Numerado **4.0.0** (y no 3.x) porque el repo ya tenía los tags `v3.0` y `v3.1`
> del 2026-06-06 sobre el mismo commit antiguo ("Add files via upload", sin
> `version.py`); empezar en 4.0.0 evita ambigüedad y deja una versión limpia.

### Agregado
- **Auditoría completa de Eris** con evidencia verificable (informe en
  `BaseDatosObsidian/BaseObsiEris/Logs/Auditoria-completa-2026-10-15.md` +
  espejo indexado en `data/knowledge/`).
- **Cuarentena reversible** `_quarantine_2026-10-15/` con README (huérfanos y
  residuos Windows apartados **sin borrar**).
- `CHANGELOG.md` (este archivo).

### Arreglado
- **ALTAS**: agentes muertos `deploy`/`system_monitor` fuera; creados
  `core/session_search.py` y `actions/project_manager.py` (imports rotos);
  tools fantasma `screen_vision` (guard de `mss`, usa grim en Wayland) y
  `calc_test` resueltas; `AGENTS.md` con los números reales.
- **MEDIAS**: imports rotos enrutados a `core/research_channels.py`
  (`learning_engine`, `sub_agent_crew`, `autonomia`, `evolution_campaigns`);
  `compaction` lee `config/api_keys.json`; `eris_fabrica` usa
  `skills.skill_registry`; fuera los 6 imports Hermes a funciones inexistentes;
  `paper_search`/`repo_discovery` eliminados de `action_imports` (de 15 → 7 `None`).
- **Ruido**: el pedido de API key ya no se repite cada turno
  (`key_manager.should_announce`, 1 aviso por proveedor cada 6 h).

### Estado verificado en esta versión
- **514 tools** con sync `514/514` y **0 duplicados**; **514/514** resuelven.
- `test_all.py` → **177 PASS / 0 FAIL / 3 WARN**.
- **14 agentes** especializados · **26 sub-agentes** en 4 capas · **304** módulos de
  acción · **44 skills** (21 builtin + 23 creadas por Eris).
- Memoria total RAG multi-fuente, evolución/auto-salud/auto-defensa propias,
  laboratorio de pentest aislado, NeuroSpheres.

## [2.7.6] — "Constellation Core"
Etapa previa (punto de partida de esta versión). Núcleo consolidado: chat dual
Ollama/Gemini, TTS local Kokoro, memoria Obsidian, evolución continua.
