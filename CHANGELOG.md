# Changelog — ERIS

Formato basado en [Keep a Changelog](https://keepachangelog.com/es/1.1.0/) y
[Versionado Semántico](https://semver.org/lang/es/). La versión viva está en
`core/version.py` (`ERIS_VERSION` / `ERIS_STAGE`).

## [4.0.1] — 2026-10-16 — Rendimiento de arranque

Parche posterior al release `v4.0.0` (tag + GitHub Release). Solo rendimiento:
sin cambios de comportamiento ni de la sync de tools (**514/514**).

### Rendimiento
- **`core/tool_dispatcher.py`**: `google.genai` ya no se importa a nivel de módulo
  (era el único import eager de `google.genai` del proyecto; los otros 13 sitios ya
  eran lazy). Ahora se importa dentro de `execute()` (~430 ms menos de arranque,
  aunque Eris use Ollama por defecto y Gemini sea el fallback).
- **`main.py` + `core/tool_dispatcher.py`**: el arranque **ya no carga
  `core.action_imports`**, que importaba ~296 action modules de golpe. `main.py`
  importa nombre por nombre solo los ~12 módulos que usa de verdad (con fallback a
  `None`, igual que antes), y `tool_dispatcher` importa `_eg_on_tool_result`
  directo de `actions.emotional_growth`. El resto de los 616 nombres sigue
  disponible igual vía `from core.action_imports import X` **cuando se usa**
  (los `action_imports.py`/`self_extend` quedan intactos).

### Verificado
- `import main`: mediana **3150 ms → 2948 ms** (−~200 ms, −6.4 %; 10 muestras).
- `core.action_imports` ya **no** aparece en `sys.modules` tras `import main`.
- `test_all.py` → **177 PASS / 0 FAIL / 3 WARN**; sync de tools **514/514**,
  0 duplicados; `symtable` confirma **0 nombres huérfanos** en `main.py`.

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

## Etiquetas (tags) del repositorio

Los tags no siempre siguieron a `core/version.py`, así que quedan mapeados para
que no haya confusión con los números:

| Tag | Fecha | Qué es |
|---|---|---|
| `v1.0.0`, `v1.0.1` | 2026-06-04 | Primeros commits (subida inicial). |
| `v3.0`, `v3.1` | 2026-06-06 | **Legacy**: ambos sobre el MISMO commit ("Add files via upload"), antes de que existiera `version.py`. No son releases reales. |
| `v2.1-estable-1007-fixed` | 2026-07-29 | Estado estable tras corregir el error 1007. |
| **`v4.0.0`** | **2026-10-16** | **Actual — "Constellation Prime"** (primera auditoría completa + release público). |

> Los tags `v3.0` / `v3.1` quedan **intactos** a propósito: son historia del repo
> y borrarlos sería lo único irreversible. La numeración "oficial" del proyecto
> vive en `core/version.py`.
