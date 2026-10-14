# Eris: skills vivos, sensores del equipo, dos capacidades nuevas y alineación de metas

- **Fecha:** 2026-10-13
- **Proyecto:** `/home/soul/ERIS-NEW`
- **Origen:** revisión de 4 repos pedidos por el dueño — `open-jarvis/OpenJarvis`,
  `paperclipai/paperclip`, `THU-MAIC/OpenMAIC`, `yihui-dev/awesome-opus5-5-videos`.
- **Estado:** borrador para aprobación. Nada se construye hasta que el dueño
  apruebe.

> **Recon (hecho).** Antes de escribir esto se exploró el código real (registro de
> tools, `skill_registry.py`, `equipo.py`, `permission_gate.py`,
> `tool_dispatcher.py`, `goal_tracker.py`, schedulers, UI) y se verificó el
> ecosistema remoto (layouts de skills y sensores de hardware). Los hallazgos que
> cambian el diseño están marcados `[RECON]`.

> **Revisión 2.** Un constructor revisor leyó esta versión contra el código y
> encontró 7 problemas reales; 3 de mis afirmaciones eran falsas. Corregido y
> marcado `[REV.2]`. Resumen de lo que cambió:
> 1. `_validate_skill_content` **rechaza toda skill real** con PyYAML presente →
>    arreglar el validador entra en el alcance de F1.
> 2. `[METAS]` no puede leer solo `goal_tracker`: el store autónomo es
>    `goal_setting` (`memory/goals.json`) → se federa.
> 3. El gate **ya** cubre la ruta de subagentes; el bypass real es
>    `agents/tool_executor.py` → entra en el alcance de F5b (antes no estaba).
> 4. `file_manager action=open` es **Windows-only** (`os.startfile`) → no sirve en
>    Linux/Wayland; hay que abrir distinto.
> 5. El planner de subagentes **no ve** `[METAS]` y `SubAgentTask` no tiene
>    `goal_id` → el id se pasa como parámetro al crear la tarea.
> 6. Precedencia de las reglas de riesgo y no degradar los hard-block de
>    `guard_check` → definida explícitamente.
> 7. `eris_cli.ask` **no** es fail-closed (es `input()`) → se corrige el criterio.

---

## 1. Intención y por qué

El dueño eligió **las 5 mejoras** que salieron de revisar los 4 repos. Al mirarlas
de cerca, dos son *arreglos de algo que ya existe y está roto o incompleto*, y tres
son *capacidades nuevas*. El eje común: **que Eris sepa más de su entorno y de sus
propios límites, y que pueda hacer dos cosas nuevas por sí misma (animar y
enseñar), sin tocar la sagrada sync 510/510 de tools.**

Contexto que gobierna todo: Eris **ya convergió** con lo mejor de esos repos.
`[RECON]` Ya tiene:
- skills estilo Hermes/agentskills.io con *progressive disclosure* (`skills_list` /
  `skill_view`) — la idea la tomó de `NousResearch/hermes-agent`;
- RAG híbrido BM25+semántico con cross-encoder (`core/advanced_rag.py`) — igual a
  la memoria de OpenJarvis;
- rastreador de costos/tokens (`core/cost_tracker.py`) y schedulers
  (`scheduler.py`, `maintenance_scheduler.py`, `cron_scheduler.py`);
- **dos capas de permiso** (`core/permission_gate.py` + `tool_dispatch_api.guard_check`)
  y un set fail-closed `_RISKY_TOOLS` en el dispatcher.

Por eso el diseño **no reescribe**: arregla lo roto, suma lo que falta y evita
duplicar.

---

## 2. Objetivos / No-objetivos / Anti-objetivos

### Objetivos
1. **F1 — Sync de skills que funcione de verdad** (hoy apunta a un repo 404) y que
   pueda traer skills de fuentes reales (openclaw / Hermes) con validación.
2. **F2 — Sensores en el pulso del equipo**: sumar temperatura de CPU/GPU/NVMe (y
   batería, ya está) al `[EQUIPO]` que se inyecta cada turno.
3. **F3 — Skill de animación HTML**: que Eris genere animaciones/explicadores
   autocontenidos a partir de un pedido, sembrada con los patrones de
   `awesome-opus5-5-videos`.
4. **F4 — Skill "armar clase"**: que Eris genere una lección HTML interactiva
   (slides + quiz) de un tema o documento, al estilo OpenMAIC pero liviano.
5. **F5 — Alineación de metas + aprobaciones unificadas**: que las tareas arrastren
   el "por qué" (meta activa) y que exista **un solo** árbitro de riesgo con
   metadatos por tool.

### No-objetivos
- No se adopta ni se embebe ninguno de los 4 proyectos como dependencia.
- No se refactoriza la fragmentación de stores de metas/tareas (es grande y
  riesgosa). F5 federará lectura, no unificará escritura.
- No se agregan tools nuevas si puede evitarse (para no tocar la sync 510/510).
- No se portan GPU utilities de Rust, ni DSPy/GEPA, ni ColBERT.

### Anti-objetivos (harían fallar esto aunque "funcione")
- Que el sync baje basura o skills rotas al catálogo.
- Que el sync instale 0 y reporte "éxito".
- Que el pulso crezca tanto que coma presupuesto de prompt o sea spam.
- Que la animación/clase salga vacía, en blanco o dependa de un CDN caído.
- Que las aprobaciones bloqueen a Eris en bucle o la dejen muda/inoperante.
- Romper la baseline `test_all.py` (177 PASS / 0 FAIL / 3 WARN) o la sync 510/510.

---

## 3. Restricciones (de `AGENTS.md`)

- **Tool sync sagrada**: si se agrega/quita una tool, editar **ambos**
  `core/tool_registry.py` y `core/tool_declarations.py`, verificar
  `len(registry)==len(declarations)` y 0 duplicados, y reiniciar Eris. → este
  diseño **reutiliza tools existentes** siempre que puede.
- `config/api_keys.json` **UTF-8 sin BOM**, o Eris crashea al arrancar.
- Portable: usar `Path(__file__).resolve().parent.parent`, env vars con fallback;
  nada de rutas `C:\Users\...` ni `ctypes.windll` fuera de guard.
- Linux/Wayland: `pyautogui`/`pygetwindow` **no** funcionan; abrir cosas va por
  un opener portable (`xdg-open`), no por GUI-automation.
- Gemini: límite de 128 `function_declarations` (ya resuelto con subconjunto
  priorizado) — no inflar el set live.
- Tests: `test_all.py` con `--ignore` de ide/neurospheres cuando aplique.

---

## 4. Recon: estado actual relevante

- **F1 sync** — `skills/skill_registry.py:150 sync_remote_skills()` lee
  `REMOTE_INDEX_URL` (JSON `[{name,description,category,tags}]`) y baja
  `{REMOTE_SKILLS_BASE}/{name}/SKILL.md`. Los defaults (líneas 31-38) apuntan a
  `https://raw.githubusercontent.com/open-jarvis/skills/main/...` → **404**.
  `[RECON]` `open-jarvis/skills` no existe. Layouts reales:
  - `openclaw/openclaw` → `skills/<skill>/SKILL.md` (plano, miles de skills).
  - `NousResearch/hermes-agent` → `skills/<categoría>/<skill>/SKILL.md` (212).
  Ninguno publica el `index.json` plano que el código espera.
  Se expone por `skill_manage action=sync` (`skills/skill_registry.py:282`).
  `[REV.2]` `_validate_skill_content` (`:455`) corre `yaml.safe_load(content)`
  sobre **todo el archivo** (`:470`): con PyYAML presente (está en `.venv-linux`)
  **rechaza toda skill con frontmatter + cuerpo** (openclaw da `ComposerError`;
  las builtin de Eris dan `ScannerError` por `description` con `:` sin comillas).
  `[REV.2]` El repo `openclaw` es enorme y su `SKILL.md` es solo índice de
  workflows (docs, no tool-calls); su primera parte alfabética es macOS-céntrica.
- **F2 pulso** — `core/equipo.py` (nuevo, commit `1b70cc6`) ya inyecta
  `[EQUIPO] CPU · RAM · Disco · Batería`, `[PANTALLA]` y emite eventos con
  cooldown. `[RECON]` hardware: CPU `k10temp` Tctl, GPU integrada **Radeon 680M**
  (`amdgpu` edge), NVMe, `acpitz`, `spd5118`. Sin fans. Sin potencia en watts
  (no hay RAPL en esta APU).
- **F3/F4 salida HTML** — `actions/web_designer.py:40` usa
  `Path.home()/Desktop/ERIS_web` como carpeta por defecto.
  `[REV.2]` **`file_manager action=open` NO sirve en Linux**: `_open_file`/
  `_open_folder` llaman `os.startfile()` sin rama Linux (`actions/file_manager.py:240`
  y `:255`). Sí tienen rama `xdg-open`: `actions/terminal_agent.py:138-150` y
  `actions/open_app.py:185`.
- **F5 metas** — `core/goal_tracker.py` (`data/goals.json`, rico: subtasks/
  milestones) **pero** `[REV.2]` el store que Eris **auto-puebla** al arrancar es
  `core/goal_setting.py` (`memory/goals.json`, llamado por `main.py:2991` y
  `main.py:4839` con `auto_generate`), y `actions/goals.py` usa
  `config/goals.json` (que **sí** está en el subset prioritario de Gemini,
  `core/gemini_text_chat.py:82`; `goal_tracker` no). `[RECON]` hay **≥10 stores**;
  no unificar ahora.
- **F5 aprobaciones** — `core/permission_gate.py` (policy
  `data/permission_rules.json` allow/ask/deny + `ALWAYS_CONFIRM` + `assess_risk` +
  `check`, log `data/permission_log.json`) y `core/tool_dispatch_api.py`
  `guard_check` (`GuardVerdict`, `RISKY_API`, `BLOCKED_PARAMS`, `PARAM_RULES`).
  `[REV.2]` La ruta de subagentes **ya** pasa por el gate
  (`core/sub_agent_crew.py:44 _dispatch_tool` → `tool_dispatch_api.dispatch_tool`
  → `guard_check` + `permission_gate.check`). El **bypass real** es
  `agents/tool_executor.py`: arma su propio `ToolDispatcher` con `MockUI.ask`
  que devuelve **True** (`:59`) y llama la tool cruda (`:88-101`), y `main.py:1580`
  lo usa en cada acierto del ActionDetector. `[REV.2]` `eris_cli.ask` es
  `input("[s/n]")` (`eris_cli.py:276`), no fail-closed; `HeadlessUI.ask` sí
  devuelve False (`tool_dispatch_api.py:268`). `[REV.2]` con riesgo `medium` y sin
  UI, `permission_gate` **permite** (`:305-310`).

---

## 5. Diseño por pieza

### F1 — Sync de skills (arreglo + fuentes reales)

**Qué cambia** (`skills/skill_registry.py`):

0. **`[REV.2]` Arreglar el validador (bloqueante).** `_validate_skill_content`
   debe parsear **solo el frontmatter** (usar `_parse_frontmatter`, que ya existe)
   en vez de `yaml.safe_load` sobre todo el archivo, y no fallar por un `:` sin
   comillas en `description` (normalizar/entrecomillar). Sin esto, F1 instala 0 y
   miente "éxito". Afecta también `skill_manage import/validate` (mejora, no
   regresión: hoy rechaza de más).
1. **Fuentes declarativas**. Reemplazar los dos defaults rotos por una lista de
   fuentes, configurable por env/`config`:
   ```python
   SKILL_SOURCES = [
     # layout "flat": <base>/<name>/SKILL.md
     {"id": "openclaw", "owner": "openclaw", "repo": "openclaw",
      "branch": "main", "root": "skills", "layout": "flat"},
     # layout "categorized": <root>/<cat>/<name>/SKILL.md
     {"id": "hermes", "owner": "NousResearch", "repo": "hermes-agent",
      "branch": "main", "root": "skills", "layout": "categorized"},
   ]
   ```
   Override por env `ERIS_SKILL_SOURCES` (JSON) para no tocar código.
2. **Descubrimiento** con dos caminos:
   - *GitHub tree* (default): `GET /repos/{owner}/{repo}/git/trees/{branch}?recursive=1`,
     filtrar `*/SKILL.md`, derivar el nombre del directorio padre, reconstruir la
     URL raw (`https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}`).
   - *Index legacy* (compat): si la fuente trae `index_url`, usar el camino viejo
     (`[{name,...}]` + `{base}/{name}/SKILL.md`).
3. **Traer + validar** (con el validador ya arreglado en el paso 0): descargar el
   `SKILL.md`, validar, instalar en `SYNCED_DIR/<name>/`. Si es inválido → borrar y
   contar error (comportamiento actual, se conserva).
4. **Límites y seguridad**: `limit` por sync (default **50**, `limit=0` = todas,
   exponer vía `skill_manage action=sync all=true`), timeout 15s, dedup por nombre,
   y **token opcional** `github_token` en `config/api_keys.json` (env
   `ERIS_GITHUB_TOKEN`).
5. **Reporte claro**: `Traídas N, salteadas M (ya existían), rechazadas K, errores E`.

**Decisiones mías (llamadas del constructor):** default = `openclaw` con `limit=50`;
`all=true` opt-in. `[REV.2]` **Semilla curada alternativa:** como `openclaw` está en
inglés y su `SKILL.md` no son tool-calls de Eris, `hermes-agent` (~212, espejo
Hermes, del que Eris ya copió el formato) es probablemente mejor semilla inicial;
dejo la elección como pregunta al dueño (§8-Q1).

**No cambia:** `skills_list`, `skill_view`, ni la sync de tools.

---

### F2 — Sensores en el pulso del equipo

**Qué cambia** (`core/equipo.py`):

1. Nueva función `temperaturas() -> dict` que lee `psutil.sensors_temperatures()` y
   devuelve, si existen, `{"cpu": °C, "gpu": °C, "nvme": °C}` (k10temp→cpu,
   amdgpu→gpu, nvme→nvme). Nunca lanza.
2. `pulso()` suma, **solo si hay sensores**, una cola compacta:
   `[EQUIPO] CPU 13% · RAM 55% (…GB) · CPU 54° · GPU 52° · NVMe 49° · Bat 73%`.
   Se mantiene cacheado ~20s y bajo ~200 chars.
3. `eventos()` suma dos umbrales nuevos (con el mismo cooldown de 30 min):
   `temp_alta` (cpu o gpu ≥ 85 °C) y, opcional, `nvme_caliente` (≥ 70 °C).
   `linea_evento()` les da frase natural es-AR.

**Decisiones mías:** mostrar solo lo disponible; no mostrar potencia en W; umbral
de temp 85 °C.

---

### F3 — Skill de animación HTML (awesome-opus)

**Qué se agrega:** `skills/user_created/animacion-html/SKILL.md` (una skill, **no**
una tool). Contrato:

- **Entrada:** un pedido en lenguaje natural (\"una animación de un agujero negro
  devorando estrellas\", \"un explicador de cómo funciona una neurona\").
- **Salida:** **un único archivo HTML autocontenido** en
  `~/Desktop/ERIS_web/animaciones/<slug>-<ts>.html` (env `ERIS_WEB_OUT` override),
  con el código de la animación adentro (Canvas/SVG/GSAP/Three.js vía CDN).
- **Apertura:** `[REV.2]` con un **opener portable** (en Linux `xdg-open`), **no**
  `file_manager action=open` (es Windows-only). Decisión: **arreglar
  `file_manager._open_file`/`_open_folder`** agregando la rama Linux `xdg-open`
  (arreglo chico, local, y cierra un bug latente que `AGENTS.md` ya daba por
  bueno); si se prefiere no tocarlo, usar `terminal_agent action=open`.
- **Cuerpo de la skill:** pasos (estilo `diseno-web-estilos`): (1) elegir el tipo
  (motion graphics / explicador / escena 3D / juego interactivo); (2) escribir el
  HTML completo con el código de la animación; (3) verificar que no quede en blanco
  (abrir y, si hay vision, mirar; si no, validar que el HTML tenga `<canvas>`/JS y
  cierre bien); (4) informar dónde quedó.
- **Semilla:** 4-6 patrones de prompt destilados de `awesome-opus5-5-videos`
  (motion graphics con GSAP; explicador con SVG; escena 3D con Three.js;
  juego/partículas con Canvas), como ejemplos dentro del `.md`.

**No cambia:** ninguna tool de la sync. El implementador confirma el nombre exacto
de la tool de escritura (`file_api` vs `web_designer`) en `core/tool_registry.py`.

---

### F4 — Skill \"armar clase\" (OpenMAIC liviano)

**Qué se agrega:** `skills/user_created/armar-clase/SKILL.md`. Contrato:

- **Entrada:** un tema o la **ruta de un documento** (usa las tools de lectura
  existentes).
- **Salida:** **un único HTML autocontenido** en
  `~/Desktop/ERIS_web/clases/<slug>-<ts>.html` con: portada, **slides navegables**
  (←/→), un **quiz** con corrección al final, y opcionalmente una **simulación
  interactiva** simple. Sin build, sin servidor.
- **Apertura:** `[REV.2]` mismo opener portable que F3.
- **Cuerpo de la skill:** tipos de escena tomados de OpenMAIC (slides, quiz,
  simulación interactiva, PBL) reducidos a HTML/JS puro; pasos de armado; chequeo
  de \"no vacío\".

**Decisión mía:** no portar OpenMAIC (Next.js+Postgres); solo el concepto, resuelto
como HTML estático. Reutiliza el mismo contrato de salida que F3.

---

### F5 — Alineación de metas + aprobaciones unificadas

Se parte en dos sub-fases (cada una un commit).

#### F5a — Alineación de metas (\"el por qué\")

- `[REV.2]` **Federación de lectura, no unificación.** El helper `linea_meta()`
  (en `goal_tracker.py` o un `core/goal_context.py` fino) lee **ambos** stores
  activos: `goal_setting` (`memory/goals.json`, el autónomo que Eris auto-puebla)
  **y** `goal_tracker` (`data/goals.json`, el rico con subtasks). Devuelve la meta
  activa + su próximo paso:
  `[METAS] Objetivo activo: \"…\" (progreso 40%) · Próximo paso: …`.
  Si ninguno tiene meta activa, no se inyecta nada.
- **Inyección:** en `core/context_builder.py`, junto a `[EQUIPO]`, se inyecta
  `[METAS]` (barato, sobrevive el trim).
- `[REV.2]` **Herencia por parámetro, no por prompt.** El planner de subagentes
  **no** ve el prompt de chat (`MissionPlanner._build_plan` usa su propio system
  prompt, `core/sub_agent_crew.py:97-119`), y `SubAgentTask` no tiene `goal_id`
  (`core/sub_agents.py:46-60`). Entonces: el modelo principal (que sí ve `[METAS]`)
  pasa `goal_id` como **parámetro** a `agente_sub`/`proyectar`, y `proyectar`
  (`:146-169`) lo adjunta a las tareas creadas. Mínimo: **no** se toca el esquema
  de persistencia ni el planner; si en el futuro hace falta, se inyecta `[METAS]`
  también en los prompts de subagente.

#### F5b — Un solo árbitro de riesgo con metadatos por tool

- **`core/permission_gate.py`** pasa a ser el árbitro único. Se le agrega carga de
  un mapa declarativo **`config/tool_risk.json`** (`{\"<tool>\": \"safe|ask|deny\"}`,
  por tool y por `tool.action`), cacheado por mtime. Así se marca riesgo **sin tocar
  las 510 declaraciones**.
- `[REV.2]` **Precedencia explícita** (de mayor a menor):
  1. `config/tool_risk.json` (override del dueño),
  2. `data/permission_rules.json` (reglas del usuario, ya existen),
  3. heurística hardcodeada (`DANGEROUS_TOOLS`/`ALWAYS_CONFIRM`/`_RISKY_TOOLS`).
  `[REV.2]` **No degradar los hard-block de `guard_check`**: los patrones de
  `RISKY_API`/`BLOCKED_PARAMS`/`PARAM_RULES` (p.ej. `git_control force=true`,
  `file_api delete`, `process_manager kill`) **se preservan tal cual**; no se
  convierten en `ask` (si no, en la ruta headless un `ask` sin UI se **permite**,
  `permission_gate.py:305-310`, y un bloqueo se volvería un allow).
- `[REV.2]` **El bypass real: `agents/tool_executor.py`** entra en el alcance. Hoy
  crea su propio `ToolDispatcher` con `MockUI` (`ask→True`, `:59`) y llama la tool
  cruda (`:88-101`), y `main.py:1580` lo usa en cada acierto del ActionDetector. Se
  hace que use la **UI real** y pase por el gate unificado (o que delegue en el
  dispatcher de main). La ruta de subagentes **ya** está cubierta, no se toca.
- `[REV.2]` **`ask` en contexto no-interactivo = fail-closed.** `eris_cli.ask` es
  `input()` (`eris_cli.py:276`); si se llega desde un hilo de fondo/cron/subagente
  sin TTY, bloquearía esperando stdin (Eris \"trabada\"). Criterio: usar `ask`
  interactivo solo en el CLI en primer plano con TTY; en cualquier otro contexto,
  fail-closed (como `HeadlessUI.ask`, `tool_dispatch_api.py:268`).
- **UI:** el modal ya existe (`ui.ask`). El resultado de cada aprobación se registra
  en `data/permission_log.json` (ya lo hace el gate).

**Decisión mía:** F5b **no cambia qué tools son riesgosas** de entrada; `tool_risk.json`
arranca **vacío** (hereda el comportamiento actual) y solo unifica el criterio.

**Riesgo/anti-objetivo:** fail-closed de más traba a Eris. Por eso el default de
`tool_risk.json` es vacío y los hard-block se preservan.

---

## 6. Orden y fases (un commit por fase)

| # | Fase | Entrega | Toca tools 510? |
|---|------|---------|-----------------|
| F1 | Sync de skills (+ validador + opener portable) | `skill_registry.py`, `file_manager.py`, config | No |
| F2 | Sensores en el pulso | `core/equipo.py` | No |
| F3 | Skill animación HTML | `skills/user_created/animacion-html/` | No |
| F4 | Skill armar clase | `skills/user_created/armar-clase/` | No |
| F5a | Alineación de metas | `goal_context` + `context_builder` + param en `proyectar` | No |
| F5b | Aprobaciones unificadas | `permission_gate`, `tool_executor`, `tool_dispatch_api` | No |

Cada fase: implementar → `test_all.py` (baseline 177/0/3) → commit. Nunca push.

`[REV.2]` El arreglo del opener portable (`file_manager.py`) puede ir con F1 (es
infra de las skills) o con F3; lo pongo en F1 para que F3/F4 lo encuentren listo.

---

## 7. Qué queda a cargo del constructor

- Elegir la tool exacta de escritura de archivos para F3/F4 (confirmar en
  `core/tool_registry.py`: candidatas `file_api`, `web_designer`).
- Definir el `slug`/timestamp del nombre de archivo y el `ERIS_WEB_OUT` por defecto.
- Decidir si `linea_meta()` vive en `goal_tracker.py` o en un `goal_context.py` nuevo.
- Escribir los tests: F1 (validador con frontmatter+body; resolver con fixture),
  F2 (pulso con/sin sensores), F5a (federación de stores), F5b (gate consultado en
  la ruta `tool_executor`; `ask` fail-closed sin TTY).

---

## 8. Preguntas abiertas para el dueño

1. **F1 — fuentes y tope.** ¿Traigo por defecto de `openclaw/openclaw` (miles de
   skills, en inglés, no son tool-calls; tope 50) o preferís solo `hermes-agent`
   (~212, espejo del formato que Eris ya usa)? ¿Registrás un `github_token` en
   config para evitar el rate limit?
2. **F3/F4 — salida.** ¿Te sirve `~/Desktop/ERIS_web/animaciones` y
   `.../clases`? ¿Aceptás CDNs (necesita internet al abrir) o querés libs locales
   embebidas para que funcione offline?
3. **F5b — alcance.** ¿Solo unifico el criterio de riesgo (mi recomendación), o
   querés que además *cambiemos* qué se considera riesgoso? ¿Confirmás que
   `tool_executor.py` entre en esta fase?

---

## 9. Anexo — más cosas analizadas (potenciales, no en estas 5)

- **Versionado/restore de skills** (estilo Skill Studio de Paperclip): historial de
  `SKILL.md` con restore.
- **Fact-store de memoria**: extraer hechos estables y consultarlos, además del RAG
  por similitud (OpenJarvis `memory/extractor.py`).
- **Loop guard dedicado** para loops de agentes (OpenJarvis `loop_guard.rs`).
- **Routing por \"slot\" de modelos** (un modelo por capacidad: chat/visión/tts),
  patrón de OpenMAIC.
- **Telemetría de GPU más rica** (uso/temp) si se logra sin deps nuevas.
