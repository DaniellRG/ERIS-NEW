# Auditoría completa de Eris (2026-10-15)

Auditoría verificada de `/home/soul/ERIS-NEW`. Informe completo visible en
`BaseDatosObsidian/BaseObsiEris/Logs/Auditoria-completa-2026-10-15.md`.

## Sano (verificado)
Sync de tools **514/514, 0 duplicados**; salud `evolucion action=health` = 514/514
resuelven; `test_all.py` **177 PASS / 0 FAIL / 3 WARN**; `auto_salud` OK; 44 skills
válidas (21 builtin + 23 user_created); RAG 205 notas. Eris no crasheó: la PC se apagó a
las 17:34:51 (journalctl `poweroff.target`), sin coredump de Python.

## Hallazgos verificados

### ALTA
- Agentes `deploy` y `system_monitor`: definidos en `core/agent_definitions.py` (16 keys)
  pero sin handler en `main.py:_build_agent_router` (14); sus módulos
  `agents/deploy_agent.py` / `agents/system_monitor_agent.py` no existen.
  `core/agent_router.py:101-113` los salta explícitamente.
- `agents/search_agent.py:21` importa `core.session_search` (no existe) → búsqueda de
  sesiones rota.
- `agents/productivity_agent.py:56` importa `actions.project_manager` (no existe) → rama
  proyectos/tareas/kanban rota.
- Tools fantasma: `screen_vision` (declarada, `get_tool`→None; único caso en la base 514)
  y `calc_test` (`actions/custom_tools.json` sin módulo; sube las declaraciones a 517).
- AGENTS.md desactualizado: 510→514 tools, 16→14 agentes, 302→303 actions, 40→44 skills,
  72→86 knowledge; cita `actions/aprendizaje_videos.py` que no existe.

### MEDIA
- Módulos huérfanos: `actions/res_manager.py` (duplica res_monitor),
  `actions/training_full.py` (duplica full_training), `actions/orb_overlay.py`,
  `actions/_chrome_launch.py`, `core/test_win_audio.py`, `watchdog.py`
  (hardcodea `D:\Eris_Source`).
- Imports rotos: `paper_search`, `repo_discovery`, `aprendizaje_videos` (aún usados por
  `core/learning_engine.py` y `core/sub_agent_crew.py` pese a `core/research_channels.py`),
  `core/config_loader` (compaction), `core/skill_registry` (eris_fabrica → el re-scan de
  skills nuevas nunca ocurre), `google_drive`, `emotional_steering`.
- `core/hermes_tools.py`: 6 imports a funciones inexistentes → siempre None.
- `opencode_bridge` duplicado: `agents/opencode_bridge.py` y `core/opencode_bridge.py`.
- Desactivados: puente opencode comentado (`main.py:4531`), `telegram_enabled=false`,
  `ollama_enabled=false` (contradice el doc), `offline_voice=false`.
- `eris_workspace/` abandonado (imports rotos a core.data_loader/state/graph_engine).
- Loop de ruido pidiendo API key de OpenRouter (`core/key_manager.py:276` vía
  `core/gemini_text_chat.py:330`).
- `core/action_imports.py` tiene 18 `None` reales (no 23 como dice el doc).

### BAJA
- Residuos Windows: `ERIS.exe`, `nul`, `watchdog_start.vbs.disabled`.
- `pass # silenciado (owner WIP)` en `core/tool_dispatcher.py:222,804`;
  `actions/self_heal.py:444` genera `if False:`; `faulthandler` "debug temporal"
  (`main.py:36`); conteos viejos en `core/self_evolution.py:4` ("447 tools").

Plan de arreglo propuesto en el informe del vault, por severidad.

## ✅ EJECUTADO — 5 ALTAS arregladas (2026-10-15)

Decisión del dueño: solo las ALTAS; los agentes muertos, quitarlos.

- **A1**: quitados `deploy` + `system_monitor` de `core/agent_definitions.py` (quedan 14),
  borrados sus imports muertos en `core/action_imports.py`. El router purga solo.
- **A2**: creado `core/session_search.py` (búsqueda en sesiones: índice + RAG). Antes el
  import apuntaba a un módulo inexistente.
- **A3**: creado `actions/project_manager.py` (delega en `task_manager`).
- **A4**: `actions/screen_vision.py` con el import opcional `mss` guardado (en Wayland usa
  grim) → ya resuelve; borrada la tool fantasma `calc_test` de `actions/custom_tools.json`.
- **A5**: AGENTS.md con números reales (514 tools, 14 agentes, 304 actions, 44 skills,
  87 knowledge, 15 None).

Verificado: py_compile OK; sync **514/514, 0 duplicados**; **0 declaradas sin
implementación**; `test_all.py` **177 PASS / 0 FAIL / 3 WARN**; las 2 ramas rotas ya
responden.

## ✅ EJECUTADO — MEDIAS + bajas arregladas (2026-10-15, OK del dueño)

- **M1** huérfanos (`res_manager`, `training_full`, `orb_overlay`, `_chrome_launch`,
  `core/test_win_audio.py`, `watchdog.py`) → **cuarentena** en `_quarantine_2026-10-15/`
  (0 referencias verificadas; nada se borró).
- **M2** imports rotos → enrutados a **`core/research_channels.py`** en `learning_engine`,
  `sub_agent_crew` (InvestigadorExterno), `autonomia`, `evolution_campaigns`; `compaction`
  lee `config/api_keys.json` directo; `eris_fabrica` usa `skills.skill_registry`.
- **M3** los **6** imports Hermes a funciones inexistentes → eliminados de `action_imports`.
- **M4** `opencode_bridge`: NO era duplicado (`agents/…` da `opencode_task`/`recall_lessons`
  usados; `core/…` es el puente MCP) → se conserva.
- **M5** features off (telegram/ollama/offline_voice/opencode) → sin cambios (decisión de config).
- **M6** `eris_workspace/` → cuarentena.
- **M7** loop de key → `key_manager.should_announce()` (1 aviso/6 h); en un arranque aparece 1 vez.
- **M8** `action_imports` 15 → **7 `None`**; AGENTS.md corregido.
- **Bajas**: residuos Windows (`ERIS.exe`/`nul`/`watchdog_start.vbs.disabled`) → cuarentena;
  `self_evolution.py` “447→514 tools”. Lo intencional del dueño (faulthandler, `pass` WIP, `if False:`)
  queda igual.
- **Hallazgo nuevo**: Eris tiene **auto-commit** (`git_autonomo auto` = `git add -A`), corrió durante
  la sesión (`3b9c181`). No filtra la key (`api_keys.json` gitignoreado), pero versiona estado runtime.

Verificado: py_compile OK; sync **514/514, 0 duplicados**, 514/514 resuelven; funcional con red real
(papers+repos); `test_all.py` **177 PASS / 0 FAIL / 3 WARN**; Eris relanzada sin tracebacks.
