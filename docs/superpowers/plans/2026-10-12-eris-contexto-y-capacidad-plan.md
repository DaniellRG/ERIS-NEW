# Plan de ejecución — Eris: contexto, herramientas y autonomía

- **Fecha:** 2026-10-12
- **Diseño:** `docs/superpowers/specs/2026-10-12-eris-contexto-y-capacidad-design.md`
- **Estado:** aprobado por el dueño. Commits solo locales, **nunca push** (regla de `HANDOFF_OPENCODE.md` §3).

Cada fase termina en un commit. Ninguna fase se da por hecha sin la verificación
escrita en su definición de hecho.

---

## Fase -1 — Que exista un Python que corra

**Por qué primero:** hoy no hay `.venv-linux/`, no hay `pytest`, y a `PyQt6`,
`PIL` y `bs4` les falta. Nada de lo demás es verificable.

**Hallazgo de esta sesión:** existe `/usr/bin/python3.14` (3.14.7), que es la
versión que documenta `AGENTS.md`. El 3.15.0 es el de `mise`. **Se usa el 3.14
del sistema**, no el de mise: coincide con lo documentado y tiene más chances de
wheels para PyQt6/opencv.

Pasos:

1. `python3.14 -m venv .venv-linux` en la raíz del repo.
2. Pinear `requirements-linux.txt` (hoy está sin pinear) en un lockfile.
3. Núcleo primero: `pytest requests psutil pyyaml beautifulsoup4 pillow`.
   Las pesadas (`opencv-python`, `vosk`, `pyqt6-webengine`) van aparte, no
   bloquean el test suite.
4. Guardar la clave de Gemini en `config/api_keys.json` → `gemini_api_key`.
   **UTF-8 sin BOM** (AGENTS.md: BOM rompe la carga). Ese archivo está en
   `.gitignore` (líneas 12 y 49). No va a ningún commit, documento ni log.
5. Verificar: `import core.tool_registry` → 503 keys, 0 duplicados.

**Definición de hecho:** `test_all.py` corre y no baja del baseline
**176 PASS / 1 FAIL ambiental / 3 WARN**. Cada diferencia se justifica.

---

## Fase 0.0 — Conectar el guardián

**Por qué antes de todo lo demás:** al arreglar B1 prenden 27 herramientas, y
`_subagents_loop` las despacha cada 30 segundos sin supervisión.

Pasos:

1. `core/tool_dispatch_api.py` con `get_dispatcher()`, `get_host()`,
   `HeadlessHost`, `dispatch_tool(tool_name, params, *, host, context)`.
2. **`dispatch_tool` consulta `core/permission_gate.py` antes de ejecutar.**
   Fail-closed: cualquier excepción al evaluar → denegar.
3. **`dispatch_tool` consulta `ActionGuard`** (`core/sub_agent_crew.py:1194`)
   para toda tool de escritura. El guardián pasa a ser un `SubAgentBase`
   registrado, no una invocación manual.
4. Log de auditoría: subagente, tool, params, decisión, resultado. A archivo y
   consultable desde el chat.
5. Test de humo: un subagente que intente `git_control push` es **denegado y
   registrado**.

**Definición de hecho:** ese test pasa. La denegación es visible en el log.

---

## Fase 0.1 — Revivir la tripulación (27 tools)

**Por qué es el cambio de mayor impacto:** hoy las 32 llamadas a herramientas
dentro de los subagentes fallan siempre.

Pasos:

1. Implementar `dispatch_tool` **por debajo** de `ToolDispatcher.execute()`,
   reusando el patrón que ya funciona en `agents/tool_executor.py:88-101`
   (`get_tool` → `_build_kwargs` → `tool(**kwargs)`), que **propaga** excepciones.
   `execute()` no sirve: toma un `types.FunctionCall`, necesita event loop vivo y
   traga los errores en strings.
2. `core/sub_agent_crew.py:44-51` importa de ahí. Nunca más un string de error
   disfrazado de resultado.
3. **Las 5 tools que no existen** (`api_invoke`, `paper_search`, `repo_discovery`,
   `sqlite_query`, `webhook_sender`): eliminar de la lista de la tripulación.
   `InvestigadorExterno` se reconstruye sin las dos que le cargaban.

**Definición de hecho:** las 32 llamadas devuelven resultado real. Cero
`"[Tool X no disponible]"` en los logs.

---

## Fase 0.2 — Lo que está roto en Linux, sin romper Windows

1. `core/platform_compat.py` con `run_flags()`. **No se borra el
   `creationflags`** — Windows depende de él.
2. Barrido de los **62 sitios en 26 archivos**. Se sustituye **solo** la llamada,
   sin tocar la línea vecina.
3. `agent/task_queue.py:42`: `USERPROFILE` → `Path.home()/"Desktop"` con fallback
   a `xdg-user-dir DESKTOP`.

**Definición de hecho:** script que confirma **cero** `creationflags` sin guard.

---

## Fase 0.3 — Los errores tienen que verse

**No** sacar el `dup2` de ALSA: re-explicaría el spam de sonido y no arregla nada.

1. Reproducir el fallo real y confirmar **dónde** queda registrado hoy.
2. Hacer que `eris.log` exista y rote.
3. Arreglar `_TeeStream.fileno()`, que lanza `io.UnsupportedOperation`.
4. Buffer de errores visible en la UI.

---

## Fase 0.5 / 0.6 — Registro y estado

- **B12**: regla "saltar agentes sin handler" en `classify_intent`.
- **B9**: construir 7 tools hermes reales (`hermes_web_search`,
  `hermes_web_scraper`, `hermes_code_review`, `hermes_security_audit`,
  `hermes_csv_processor`, `hermes_data_analyzer`, `hermes_page_summarizer`);
  sacar las otras 12 de `_GEMINI_PRIORITY_TOOLS`. **Sync sagrado**: registry +
  declarations, `len == len`, 0 dupes. No revertir `_gemini_tools()` a
  `TOOL_DECLARATIONS` completo.
- **0.7**: integrar xKiro o sacarlo de la cadena. Test que **cae** el backend
  primario y comprueba que el secundario responde.
- **B7**: subir el truncado y quitar el "resumí en 1 frase".
- **B8**: `_EXEC_STEMS` pasa a ser una señal más, no la única puerta.
- **B11**: `_result_status` mira la clave booleana antes que la heurística de
  strings, **y purga el estado aprendido** a la inversa.
- **B14/B15**: código inalcanzable, números derivados del registro real.

---

## Fase 1 — Un solo cerebro

1. `core/shared_context.py`: `convo_ctx`, `session_summary`, `project_root`,
   `active_file`, `foreground_app`, `identity`, `read_only`. Singleton por proceso.
2. Pasarlo a los subagentes (`execute(task, params, context)`), a la CLI, y al
   dispatcher.
3. Extraer la lógica de `_build_config()` (main.py:2924-3720) a un módulo
   reutilizable, llamado desde GUI, CLI y subagentes.
4. Fin del eco: `main.py:1607-1616` anuncia una sola vez.

**Definición de hecho:** un subagente responde con conocimiento del historial. CLI
y GUI producen el mismo contexto.

---

## Fase 2 — Los ojos (los dos backends)

`core/window_detect.py`: `ctypes`/user32 para Windows, `hyprctl` para
Linux/Hyprland, genérico que devuelve vacío honestamente. En CLI, `project_root` =
cwd + mapeo del árbol del proyecto. Los 27 patrones de `_SENSITIVE_PAT` silencian
la observación y registran el evento.

---

## Fase 3 — Que actúe sola

`core/intent_reader.py` clasifica en `INVESTIGAR` / `EDITAR` / `AUTONOMO`
combinando texto **y** `SharedContext`. Toda escritura por `core/file_api.py` con
backup, resultado que dice exactamente qué líneas cambiaron, y `deshacer`.
Y: **no decir "listo" sin verificar**.

---

## Orden de commit

Una fase = un commit. Identidad local `opencode (agente)` — los 117 commits
previos son tuyos y no se tocan. **Nunca push.**

---

## Estado de ejecución (actualizado 2026-10-12)

| Fase | Commit | Estado |
|---|---|---|
| -1 | `29f6b66` | hecho |
| 0.0 + 0.1 | `c553d91` | hecho |
| 0.2 | `8410453` | hecho |
| 0.3 | `9f733d9` | hecho |
| 0.6 | `0c4c784` | hecho |
| 0.5 | `ea9d1a7` | hecho |
| 0.7 | `7958d4b` | hecho (failover real + test que cae el primario) |
| 1.1 | `da5af25` | hecho (`core/shared_context.py` + 13 tests) |
| 1.2 | `9478677` | hecho, con alcance reducido (ver nota) |
| 1.3 | `9c1e98c` | hecho (fin del eco + 2 tests) |
| **1 (resto)** | — | **pendiente**: extracción completa de `_build_config` |
| 2.1–2.4 | `103303e` | hecho (los ojos: `core/window_detect.py`, observer ve en Linux, `codebase_explorer action=map`, evento `privado` sin contenido) |
| 3.1 | `8a693f1` | hecho (módulo `core/intent_reader.py` + 9 tests) |
| 3.1b | `13c4591` | hecho en CLI (`_turn_intent` + `_intent_system` inyecta el modo por turno y lo restaura; 9 tests). GUI: pendiente |
| 3.2 | `f1e4382` | hecho (escrituras por `file_api` con backup en `memory/undo_backups`, líneas exactas, action `deshacer` + `/deshacer` en CLI; 14 tests) |
| 3.3–3.4 | — | pendiente (autonomía al SharedContext / verificar antes de "listo") |

**Nota Fase 1.2:** la extracción **completa** de `_build_config()` (~370 líneas,
`main.py:2992-3370`) a un módulo reutilizable **quedó pendiente**. Ese bloque
está enredado con estado vivo de PyQt/Gemini Live y no es testeable desde este
box Linux; un corte a ciegas arriesga la GUI. Lo que hoy es reutilizable y común
a GUI, CLI y subagentes es el **SharedContext** (lo que de verdad decide "qué
veníamos haciendo"): la GUI lo espeja y lo inyecta, la CLI lo fija y lo espeja,
y los subagentes lo reciben en `execute(task, context)`. Retomar la extracción
en una pasada con la GUI a la vista.

**Baseline vigente:** `test_all.py` 177 PASS / 0 FAIL / 3 WARN · sync tools
510/510 · `pytest tests/` 197 passed (3 fallos pre-existentes en archivos no
tocados: `generated/test_weather_report.py` y `tests/test_tool_declarations.py`).