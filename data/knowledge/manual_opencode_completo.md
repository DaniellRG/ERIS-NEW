# OpenCode — Manual Completo (Conversación Conservada)

> **Qué es esto**: documento generado por la propia OpenCode (modelo `big-pickle`) que conserva
> TODO lo explicado en la conversación: quién soy, cómo funciono, cada rincón del repositorio,
> cómo replicarme y cómo usarme offline. Ningún detalle queda fuera.
>
> Repositorio oficial: https://github.com/anomalyco/opencode (rama `dev`)
> Docs: https://opencode.ai/docs
> Instalación: `curl -fsSL https://opencode.ai/install | bash`

---

## Índice

1. [Introducción: qué es OpenCode](#1-introducción-qué-es-opencode)
2. [Instalación](#2-instalación)
3. [El monorepo de un vistazo](#3-el-monorepo-de-un-vistazo)
4. [Cómo "arranco" y cómo hablamos con la UI](#4-cómo-arranco-y-cómo-hablamos-con-la-ui)
5. [El ciclo de vida de una conversación (el loop)](#5-el-ciclo-de-vida-de-una-conversación-el-loop)
6. [Mi cerebro: el system prompt](#6-mi-cerebro-el-system-prompt)
7. [Las herramientas (tools)](#7-las-herramientas-tools)
8. [Permisos y seguridad](#8-permisos-y-seguridad)
9. [Los agentes](#9-los-agentes)
10. [Skills](#10-skills)
11. [Memoria: compactación, resumen y reminders](#11-memoria-compactación-resumen-y-reminders)
12. [Config: opencode.json](#12-config-opencodejson)
13. [Plugins, MCP, comandos y undo](#13-plugins-mcp-comandos-y-undo)
14. [Modo embedded / SDK](#14-modo-embedded--sdk)
15. [Cómo se compila el binario](#15-cómo-se-compila-el-binario)
16. [El sistema de eventos](#16-el-sistema-de-eventos)
17. [Todo el árbol de `packages/opencode/src/` (directorio a directorio)](#17-todo-el-árbol-de-packagesopencode-src-directorio-a-directorio)
18. [El resto del monorepo (los 30 paquetes)](#18-el-resto-del-monorepo-los-30-paquetes)
19. [Lo que NO está en el repo](#19-lo-que-no-está-en-el-repo)
20. [Cómo replicarme: hacer TU propio OpenCode](#20-cómo-replicarme-hacer-tu-propio-opencode)
21. [Funcionar con y sin Internet (modelos locales)](#21-funcionar-con-y-sin-internet-modelos-locales)

---

## 1. Introducción: qué es OpenCode

OpenCode es un **agente de IA de código abierto** para la terminal. Funciona como una CLI
interactiva, app de escritorio o extensión de IDE. Es MIT — puedes copiarlo, modificarlo,
renombrarlo y venderlo conservando el aviso de copyright.

- **El código fuente** (todo lo que define al agente: modelos de agentes, herramientas, TUI,
  servidor, SDK): https://github.com/anomalyco/opencode
- **La doc**: https://opencode.ai/docs
- **Las skills de esta máquina**: `/home/soul/.agents/skills/` (omarchy, diagnose-crash,
  customize-opencode)
- **Reglas de comportamiento**: del `AGENTS.md` del repo + `~/.config/opencode/` + skills.

**Lo que NO es open-source**: el modelo de IA (big-pickle). OpenCode es el esqueleto; el modelo
es el músculo externo.

---

## 2. Instalación

**Oficial (script):**
```
curl -fsSL https://opencode.ai/install | bash
```

**Otras formas:**
```bash
npm install -g opencode-ai       # o bun/pnpm/yarn
brew install anomalyco/tap/opencode   # macOS/Linux
sudo pacman -S opencode              # Arch
choco install opencode               # Windows
scoop install opencode               # Windows
mise use -g github:anomalyco/opencode
docker run -it --rm ghcr.io/anomalyco/opencode
```

En esta máquina está instalado con **mise** en:
`~/.local/share/mise/installs/opencode/latest/opencode` — un binario ELF de ~184 MB.

Requisitos: terminal moderno (WezTerm, Alacritty, Ghostty, Kitty) y API keys de los providers.

---

## 3. El monorepo de un vistazo

Monorepo de **Bun workspaces + Turbo** (bun 1.3.x, turbo 2.x). Hay ~30 paquetes; los clave:

| Paquete | Qué hace |
|---|---|
| `packages/opencode` | El "yo" que ejecutas: CLI, servidor local, sesiones, tools, agentes, skills (~77.781 líneas en `src/`) |
| `packages/tui` | La interfaz de terminal (SolidJS + @opentui) |
| `packages/core` | Núcleo reutilizable: eventos, SQLite/drizzle, git, ripgrep, PTY, sessions v2 |
| `packages/schema` | Todos los tipos/esquemas (Effect Schema + zod), cero dependencias internas |
| `packages/protocol` | La API tipada (`makeApi` / HttpApi) — depende solo de schema |
| `packages/server` | Capa HTTP reutilizable "protocol v2" + `createEmbeddedRoutes()` |
| `packages/sdk` | SDK público generado (hey-api/openapi-ts), clientes v1 y v2 |
| `packages/client` | Cliente Effect-native de nueva generación (`./effect`) |
| `packages/sdk-next` | SDK embebido/in-process (modo embedded) |
| `packages/llm` | Streaming de modelos (AI SDK + runtime nativo) + eventos de uso |
| `packages/plugin` | API pública de plugins (servidor y TUI) |
| `packages/codemode` | Ejecución de código confinada |
| `packages/app` | Web app (Vite/Solid) embebida en el binario |
| `packages/desktop` | App Electron |

Grafo de dependencias clave:
```
schema (sin deps) ← protocol ← client ← sdk-next
                ← core ← server ← sdk-next y opencode
opencode → core, codemode, llm, plugin, protocol, schema, script, sdk, server, tui
```

---

## 4. Cómo "arranco" y cómo hablamos con la UI

Cuando ejecutas `opencode` (`packages/opencode/src/cli/cmd/tui.ts`):

1. Se lanza un **Worker** aparte (`cli/tui/worker.ts`) donde vive el motor. La UI corre en el
   hilo principal; el cerebro en el worker.
2. Comunicación por **RPC sobre `postMessage`** (`util/rpc.ts`): el worker traduce cada request
   HTTP a ejecutar el servidor HTTP **en memoria** (`Server.Default().app.fetch(request)`).
   La URL es falsa: `http://opencode.internal` con un `fetch` custom.
3. Los eventos fluyen: motor → `GlobalBus` (EventEmitter global) → `rpc.emit("global.event")`
   → TUI agrupa en batches de ≤16ms y redibuja (Solid).
4. Con `--port`/`--hostname` usa HTTP+SSE+WebSockets reales con **Basic Auth**
   (`OPENCODE_SERVER_PASSWORD`, usuario por defecto `opencode`).
5. PTY se conectan por WebSocket en `/pty/:ptyID/connect` con ticket auth.

Endpoints principales (groups/): `/session` (CRUD + prompt, command, shell, revert, summarize,
share, permissions), `/config`, `/file`, `/mcp`, `/provider`, `/question`, `/permission`,
`/project`, `/sync`, `/workspace`, `/pty/*` (WebSocket), `/experimental/*`, `GET /doc`
(OpenAPI), y catch-all = web UI embebida.

Arranque: `src/index.ts` (yargs) → carga `InstanceContext` (`project/instance-store.ts`) →
`cli/cmd/tui.ts` lanza worker → `layer.ts` → `runTui()` de `@opencode-ai/tui`.
Otras entradas: `run` (modo no-interactivo/mini), `serve`, `models`, `agent`, `mcp`, `acp`,
`attach`, `debug`, `web`, `session`, `db`, `plugins`.

---

## 5. El ciclo de vida de una conversación (el loop)

Todo empieza en `packages/opencode/src/session/prompt.ts`:

**a) `prompt()` (L1052)** — crea el mensaje de usuario, aplica permisos, y si no es `noReply`,
lanza el loop.

**b) `createUserMessage()` (L635)** — resuelve agente y modelo, procesa cada parte:
- Imagen arrastrada → se normaliza e incrusta.
- `@archivo` → part tipo file (usa el tool `read` internamente con `bypassCwdCheck`).
- `@agente` → instrucción de usar el tool `task` con ese subagente.
- Adjuntos MCP → se leen como recurso (límite 10MB blob, MIME permitidos).

**c) `runLoop()` (L1081)** — el corazón, un `while(true)`:
1. Carga la historia (filtrando compactada), localiza último mensaje user/assistant.
2. **Condición de salida**: si el último asistente terminó con finish normal (no
   `tool-calls`) y sin tools colgadas → sale. Si hay tool calls → sigue para devolver
   resultados al modelo.
3. Paso 1: lanza en background el agente `title` (autotítulo de sesión).
4. Si hay subtask → `handleSubtask`.
5. Si hay compactación pendiente → compacta.
6. Si overflow de tokens → compactación automática.
7. Lee el agente activo, aplica `maxSteps`, inyecta `SessionReminders.apply` (modo plan, etc.).
8. `SessionTools.resolve` → tools disponibles. Construye sistema de contexto.
9. Llama al proveedor (streaming). El **processor** escucha el stream y convierte cada evento
   en updates durables: `tool-call` crea la part, `tool-result` la completa, texto → delta.
   Detecta **doom loops** (3 tool calls idénticas → te pregunta si está en un bucle).
10. Decide `continue` / `stop` / `compact` y repite.

- **Interrupción**: `SessionRunState` permite un runner por sesión. `cancel()` con
  `AbortController` mata el stream y marca las tool calls como `interrupted`.
- **Título automático** con agente dedicado `title` (temperature 0.5).

---

## 6. Mi cerebro: el system prompt

Construido en `packages/opencode/src/session/`. El archivo del prompt base es:
`packages/opencode/src/session/prompt/default.txt` — es EXACTAMENTE el texto del system prompt
de esta conversación ("You are opencode, an interactive CLI tool...", reglas de brevedad de 4
líneas, proactividad, conventions, code references, etc.).

**Selección por modelo** (`session/system.ts`):
- Claude → `anthropic.txt` ("You are OpenCode, the best coding agent on the planet", enfatiza TodoWrite)
- GPT → `gpt.txt`
- Gemini → `gemini.txt`
- Kimi → `kimi.txt`
- Meta/Trinity → `meta.txt` / `trinity.txt`
- Otros (incluido mi caso) → `default.txt`

**Directorio `session/prompt/`** (15 archivos):
`default.txt`, `anthropic.txt`, `gpt.txt`, `gemini.txt`, `kimi.txt`, `meta.txt`, `trinity.txt`,
`codex.txt`, `beast.txt`, `copilot-gpt-5.txt`, `plan-mode.txt`, `plan.txt`,
`plan-reminder-anthropic.txt`, `build-switch.txt`.

A ese texto se le **añaden capas de contexto** (el "System Context" del `CONTEXT.md`):
instrucciones de `AGENTS.md` (global + proyecto, `session/instruction.ts`), skills disponibles
del agente, fecha actual, permisos aprobados, reminders como `<system-reminder>`.

### Conceptos clave del `CONTEXT.md`
- **Context Source**: valor tipado observable con key estable, loader, renderers base/update/removal.
- **Baseline System Context**: el contexto completo renderizado al inicio de una "Context Epoch".
- **Mid-Conversation System Message**: instrucción durable cuando un Context Source cambia.
- **Context Epoch**: período con un baseline inmutable que cambia con compactación o cambio de ubicación.
- Los cambios de contexto se admiten en la "Safe Provider-Turn Boundary" (antes de un turno), nunca en caliente.
- Los recuerdos durables (AGENTS.md) se admiten en la siguiente frontera segura.

---

## 7. Las herramientas (tools)

Base en `packages/opencode/src/tool/tool.ts`:
```ts
export interface Def<Parameters, M> {
  id: string
  description: string
  parameters: Parameters      // Schema.Decoder de Effect
  jsonSchema?: JSONSchema7
  execute(args, ctx): Effect.Effect<ExecuteResult<M>>
  formatValidationError?(error): string
}
```
- `ExecuteResult` = `{ title, metadata, output, attachments? }`.
- `Context` = `{ sessionID, messageID, agent, abort, callID, extra, messages, metadata(), ask() }` —
  `ask()` es el mecanismo de permisos; `metadata()` transmite progreso en vivo (el shell lo usa).
- `wrap()` (L99): valida args contra el schema (fallo → `InvalidArgumentsError`
  "reescribe el input"), ejecuta y **trunca** el output automáticamente.

**Restricciones de output** (`tool/truncate.ts`): `MAX_LINES = 2000`, `MAX_BYTES = 50 * 1024`
configurables con `tool_output.max_lines`/`max_bytes`. Si excede: preview + archivo completo en
`<data>/tool-output/tool_<ToolID>`, con hint "Use the Task tool..." (si el agente puede delegar)
o "Use Grep/Read con offset/limit". Limpieza diaria a los 7 días.

### Tabla completa de tools (registradas en `tool/registry.ts`)

| Tool | Función | Detalles |
|---|---|---|
| `invalid` | Destino de reparación cuando el modelo llama una tool inexistente/args inválidos | vía `experimental_repairToolCall` |
| `question` | Preguntas interactivas al usuario, devuelve respuestas al modelo | Solo app/cli/desktop o `enableQuestionTool` |
| `bash` | Shell real (bash/pwsh/powershell/cmd) | Parser **tree-sitter** (WASM) para describir el comando antes de ejecutar; permisos por comando; timeout default `bashDefaultTimeoutMs ?? 120000`; truncado incremental (buffer deslizante 2x maxBytes, anexa a archivo); `<shell_metadata>` si timeout/abort |
| `read` | Lee archivos y directorios | `offset` 1-indexed, `limit` default 2000; detección binaria; imágenes/PDF como attachments base64; BOM; sugiere archivos parecidos si no existe; directorios paginados; streaming por líneas con corte |
| `glob` | Busca archivos por patrón | ripgrep, límite 100, rutas absolutas |
| `grep` | Busca regex en contenidos | ripgrep, límite 100, agrupado por archivo "Archivo: Línea N: texto" |
| `edit` | Reemplazo string-exacto | **9 replacers** (ver abajo); semáforo por archivo; BOM; diff; LSP; eventos FS |
| `write` | Escritura completa de archivo | BOM, `writeWithDirs`, formato (prettier), diff, LSP + reporte de diagnósticos (límite 5 archivos) |
| `task` | Lanza subagentes | `subagent_type`, `task_id` (reanudar), `command`, `background` (en el futuro); profundidad por config `subagent_depth ?? 1`; crea sesión hija con permisos heredados |
| `webfetch` | Fetch de URLs | ≤5MB; timeout 30s (máx 120s); formatos text/markdown/html; UA Chrome falso con fallback honesto "opencode" ante anti-bot; imágenes → attachment |
| `todowrite` | Reemplaza el todo list de sesión | `ask("todowrite")` |
| `websearch` | Búsqueda web | Provider Exa (`mcp.exa.ai/mcp`) o Parallel (`search.parallel.ai/mcp`), ambos MCP vía HTTP; elegido por `OPENCODE_WEBSEARCH_PROVIDER` > flag > hash del sessionID % 2; args query/numResults/livecrawl/type/contextMaxCharacters |
| `skill` | Carga un skill | Lee `SKILL.md` + muestra de archivos |
| `apply_patch` | Parches multi-archivo (add/update/delete/move) | Solo modelos `gpt-*` (no oss/gpt-4); oculta edit/write en ese caso |
| `execute` | Ejecuta script en intérprete confinado | Solo `experimentalCodeMode`; acceso a tools MCP visibles |
| `lsp` | Operaciones LSP | Solo `experimentalLspTool`: definición, referencias, hover, símbolos, call hierarchy |
| `plan_exit` | Pasa al agente build | Solo `experimentalPlanMode && client cli`, inserta mensaje sintético `agent: "build"` |

Además, dinámicas en cada turno (`session/tools.ts`): tools MCP del catálogo y de plugins,
y `list_mcp_resources`/`read_mcp_resource` si el MCP anuncia capability `resources`.

### Los 9 replacers de `edit` (`tool/edit.ts:682-729`)
1. `SimpleReplacer` — match exacto
2. `LineTrimmedReplacer` — ignora indentación al comparar, devuelve el span exacto
3. `BlockAnchorReplacer` — anclas 1ª/última línea + similitud Levenshtein interior (≥0.65)
4. `WhitespaceNormalizedReplacer` — colapsa whitespace y reconstruye regex
5. `IndentationFlexibleReplacer` — normaliza indentación común de bloque
6. `EscapeNormalizedReplacer` — desescapa `\n \t \r ' " \ $`
7. `TrimmedBoundaryReplacer` — match con trim() en los bordes
8. `ContextAwareReplacer` — ≥3 líneas, ≥50% intermedias iguales
9. `MultiOccurrenceReplacer` — lista todas las coincidencias exactas (para `replaceAll`)

Reglas: `oldString == newString` → error; `oldString == ""` en archivo existente → error (usar
write); match desproporcionado → rechaza; múltiples matches sin contexto → error "Provide more
surrounding context". Eventos `FileSystem.Event.Edited` y `Watcher.Event.Updated`.

### Ciclo de vida de una tool call (persistencia)
1. `SessionProcessor.ensureToolCall` crea part `{type:"tool", callID: <id del proveedor>, status:"pending"}`.
2. Evento `tool-call` → `status:"running"` con input y `time.start`.
3. `metadata()` → actualiza en vivo.
4. `tool-result` → `completeToolCall`: `completed`, output, metadata, title, attachments.
5. `tool-error` → `failToolCall`: `state.error`.
6. Interrupción → marca `error:"Tool execution aborted"`, `metadata.interrupted: true`.

Las parts se guardan en SQLite (tabla `PartTable`: session_id, message_id, id, data JSON).
IDs: `ses_`, `msg_`, `prt_`, `per_`, `que_`, `tool_`, `job_`, `evt_`, `pty_`, `wrk_` + ULID.
El `callID` es el toolCallId del proveedor (reutilizado para reconstruir el round-trip).

---

## 8. Permisos y seguridad

`packages/opencode/src/permission/index.ts`:
- `evaluate()` = última regla que matchee `{permission, pattern}` con wildcards. Default: **ask**.
- `ask()` evalúa cada patrón: `deny`→`DeniedError`, `allow`→pasa, si no está cubierto → crea
  `PermissionV1.Request`, emite `Event.Asked` y **bloquea** en un `Deferred` hasta que respondas.
- `reply()`: `reject` (falla y rechaza las pendientes de la sesión, con feedback → `CorrectedError`),
  `once` (aprueba solo esa), `always` (añade a `approved` — persistido y mostrado en el contexto).
- Reglas por pattern clave: `bash` (comando + "always" de prefijo de aridad), `edit` (con diff en
  metadata), `read`, `webfetch`, `external_directory` (con glob `<dir>/*` para fuera del proyecto),
  `task:<agente>`, `todowrite`, `lsp`.
- `disabled`/`visibleTools` ocultan tools cuyo permiso es `deny` con patrón `*`.
- Agentes plan/edit: `build` hereda defaults + `question:allow`; `plan` → `edit:{*:deny}`,
  `.opencode/plans/*.md: allow`, `task.general: deny`, `external_directory.plans/*: allow`.

---

## 9. Los agentes

Definidos en `packages/opencode/src/agent/agent.ts`, fusionados con tu config:

| Agente | Tipo | Función |
|---|---|---|
| `build` | primary (default) | Ejecuta tools según permisos; permisos `*:allow`, `doom_loop:ask`, `question:allow`, `plan_enter:allow` |
| `plan` | primary | Solo escribe en `.opencode/plans/*.md`; niega edit/apply_patch/write y `task.general` |
| `general` | subagent | Propósito general, paralelo |
| `explore` | subagent | Exploración (solo grep, glob, list, bash, webfetch, websearch, read) — prompt en `agent/prompt/explore.txt` |
| `compaction` | hidden primary | Resúmenes de compactación |
| `title` | hidden primary (t=0.5) | Títulos de sesión |
| `summary` | hidden primary | Resúmenes |

**Prompt de `explore` (verbatim, 18 líneas)** — describe al subagente que explora:
> You are a file search specialist. You excel at thoroughly navigating and exploring codebases.
> Your strengths: Rapidly finding files using glob patterns; Searching code and text with
> powerful regex patterns; Reading and analyzing file contents...
> ...Do not create any files, or run bash commands that modify the user's system state in any way.

`Agent.generate` (crear subagentes con IA) usa `agent/generate.txt`. Por defecto en `agent.ts`
hay un whitelist de `external_directory` (Truncate.GLOB, tmp, skills dirs, references) y manejo
de `.env`.

**Un subagente NO es "cambio de forma"**: es una **sesión nueva** con permisos heredados que
corre en paralelo/background y devuelve un resumen `<task result>` a la sesión padre.
`prompt.ts` si `lastUser` tiene part tipo `agent`, lo convierte en un tool-call a `task`
sintético (`handleSubtask`, L255). Los resultados llegan como partes sintéticas de texto.

---

## 10. Skills

- Carga: `packages/opencode/src/skill/index.ts` — `{skill,skills}/**/SKILL.md`,
  `.claude/skills/**/SKILL.md`, `.agents/skills/**/SKILL.md` (los tuyos en `/home/soul/.agents/skills/`).
- Cada skill = `SKILL.md` con frontmatter (name, description) + archivos de apoyo.
- En el contexto solo veo **nombre + descripción**; el contenido lo leo con el tool `skill`
  cuando relevante (vía sistema de permisos).
- Skill embebida del proyecto: `customize-opencode` (`packages/core/src/plugin/skill/`).
- Descarga de skills: `skill/discovery.ts` (índice + archivos a `<cache>/skills`).

---

## 11. Memoria: compactación, resumen y reminders

- **`overflow.ts`**: detecta cuándo un turno supera el límite del modelo.
- **`session/compaction.ts`**: al overflow, con el agente `compaction` genera resumen
  ("What did we do so far?"), poda (PRUNE_MINIMUM 20k, PRUNE_PROTECT 40k conservados,
  budget de recientes preservado), y empieza una nueva **Context Epoch** con baseline fresco.
  Reaparece en la historia como `[compaction]` y `[continue]`.
- **`reminders.ts`**: inyecta `<system-reminder>` durables (plan mode, plan-reminder-anthropic,
  build-switch). `SessionReminders.apply` se ejecuta en `prompt.ts:1180`.
- El proyecto es de "Context Sources" vía el sistema de `CONTEXT.md`.

---

## 12. Config: opencode.json

Factores `packages/opencode/src/config/` y `packages/core/src/v1/config/config.ts`.
Tu config local: `~/.config/opencode/opencode.json`.

Secciones clave: `agent` (prompts, modelos, permisos por agente), `permission`, `tools`
(activar/desactivar), `shell`, `provider` (API keys en runtime/auth), `model`, `plugin`, `mcp`,
`experimental`, `compaction`, `tool_output`, `references`, `snapshot`, `share`.

Ejemplo de la config de desarrollo del propio repo (`.opencode/opencode.jsonc`):
```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {},
  "permission": {},
  "references": { "effect": { "repository": "github.com/Effect-TS/effect-smol" }, ... },
  "mcp": {},
  "tools": { "github-triage": false, "github-pr-search": false }
}
```

Comandos `/init` y `/review` por defecto en `src/command/index.ts` con plantillas en
`src/command/template/initialize.txt` y `review.txt`.

---

## 13. Plugins, MCP, comandos y undo

**Plugins** (`packages/opencode/src/plugin/`):
- Hooks: `tool.execute.before/after`, `chat.message`, `shell.env`, `config`, `event`.
- Pueden añadir tools y tocar la UI. Formatos `.js`/`.ts` en el proyecto + providers pluginizados:
  openai/codex (`plugin/openai/` con ws-pool), github-copilot, azure, cerebras, cloudflare, xai,
  modal, digitalocean, snowflake-cortex.

**MCP** (`src/mcp/`, 1004 líneas): transportes StreamableHTTP → fallback SSE → stdio local.
Estados `connected/disabled/failed/needs_auth/needs_client_registration`. OAuth completo con
CSRF check. Sus herramientas se exponen al modelo cada turno con permisos individuales.

**Comandos**: `/init`, `/review`, `/undo`, `/redo`, `/share`, `/unshare`, `/compact`
(`session.summarize`), `/rename`, `/timeline`, `/fork`, `/timestamps`, `/thinking`,
`/connect`, más `:mcp` y skills. Autocompletado vía `sync.data.command`.

**Undo/Redo** (`session/revert.ts` + `snapshot/index.ts`, 807 líneas):
git-ad-hoc en `Global.Path.data/snapshot/<proyecto>/<hash worktree>`; `config.snapshot === false`
lo desactiva; archivos >2MB excluidos; `gc --prune=7.days` cada hora. `/undo` revierte los
patches posteriores al mensaje objetivo, `/redo` restaura. Requiere `SessionRunState.assertNotBusy`.

**Auth** (`src/auth/`): logins, device-flow, tokens. `account/` = cuentas opencode.ai
(full path: repo.ts, schema.ts, url.ts; refresh tokens, orgs).

---

## 14. Modo embedded / SDK

`packages/sdk-next` (`@opencode-ai/sdk-next`):
- `OpenCode.create()` construye el host in-process con `AppNodeBuilder.build(...)`, monta
  `createEmbeddedRoutes()` de `packages/server`, convierte el router a un `webHandler` y lo
  expone como `fetch`; `OpenCode.make({ baseUrl: "http://opencode.local" })` del cliente Effect
  lo consume. Devuelve `{...client, tools: { register } }`.
- Cero I/O de red; el mismo router/middleware/handlers/codecs/errores que el servidor.
- Es el reemplazo transitorio de `@opencode-ai/sdk` generado.

Arquitectura de clientes: `schema` → `protocol` → `server` → `client` → `sdk-next`.

---

## 15. Cómo se compila el binario

`packages/opencode/script/build.ts`:
1. Descarga `models.dev/api.json` → catálogo de modelos `OPENCODE_MODELS_DEV`.
2. Compila la web UI (`packages/app`, Vite) → `opencode-web-ui.gen.ts` embebida.
3. Descarga binarios de plataforma (@opentui/core, @parcel/watcher, @ff-labs/fff-bun) para 12 targets.
4. `Bun.build` con `compile: { target: "bun-<os>-<arch>", outfile: "dist/<name>/bin/opencode" }`
   + entrypoints (CLI, worker TUI, tree-sitter worker, web UI gen) + define de versión + plugin
   de Solid + minify.
5. Smoke test `--version`, package.json por target.

El wrapper `bin/opencode` (Node) detecta plataforma/AVX2/musl, encuentra el binario nativo y lo
lanza reenviando señales.

---

## 16. El sistema de eventos

Tres capas:
1. **EventManifest** (`packages/schema/src/event.ts` + `event-manifest.ts`): definiciones tipadas
   y versionadas (`Event.define({type, durable?, schema})`), catálogo completo (`Definitions`,
   `Durable`, `Latest`). El Schema del evento tipa el SSE.
2. **EventV2** (`packages/core/src/event.ts` + `event/sql.ts`): persistencia en SQLite con `seq`
   por aggregateID; `publish`, `listen`, `readAggregate`, `latestSequence`.
   El puente `packages/opencode/src/event-v2-bridge.ts` añade Location y replica durables al
   GlobalBus.
3. **GlobalBus** (`packages/opencode/src/bus/global.ts`): EventEmitter global → SSE
   `GET /global/event` (+ `/event` por instancia con heartbeat 10s) → SDK de la TUI.

La TUI los bufferiza en batches ≤16ms en `packages/tui/src/context/sdk.tsx`.

**Sync (multi-dispositivo)**: `packages/opencode/src/sync/` (lee `sync/README.md`) — event
sourcing con **un solo escritor** y orden total por `seq`; los SyncEvents se re-publican como
BusEvents (`busSchema` para compatibilidad); "projectors" aplican las mutaciones. Todos los
eventos que mutan la db de sesión ya son sync events.

---

## 17. Todo el árbol de `packages/opencode/src/` (directorio a directorio)

Nota: números → log de `@opencode-ai/core/util/token` estimación de tokens.

| Directorio/Archivo | Qué contiene |
|---|---|
| `index.ts` | Entry point: yargs, middleware, manejo de errores/exit |
| `session/` | **El "cerebro"**: prompt.ts (loop), processor.ts (stream→eventos), message-v2.ts (historia→mensajes), system.ts, instruction.ts, compaction.ts, overflow.ts, reminders.ts, retry.ts, revert.ts, session.ts, status.ts, run-state.ts, summary.ts, todo.ts, tools.ts, llm.ts + `llm/` (ai-sdk, native-runtime, native-request, request) + `prompt/` (los .txt) |
| `tool/` | Mis manos: tool.ts, registry.ts, shell/ (bash+tree-sitter), edit.ts, read.ts, write.ts, glob.ts, grep.ts, task.ts, question.ts, todo.ts, skill.ts, webfetch.ts, websearch.ts, mcp-websearch.ts, apply_patch.ts, plan.ts, code-mode.ts, invalid.ts, lsp.ts, json-schema.ts, truncate.ts, truncation-dir.ts, external-directory.ts, schema.ts (+ los .txt de descripción de cada tool) |
| `permission/` | index.ts, evaluate.ts, arity.ts |
| `agent/` | agent.ts, subagent-permissions.ts, generate.txt, prompt/{explore,compaction,summary,title}.txt |
| `skill/` | index.ts, discovery.ts |
| `cli/` | Entradas: cmd/ (tui, run + run/*, serve, models, agent, mcp, acp, attach, session, db, debug/*, export, import, github, pr, providers, stats, web, upgrade, uninstall, account, generate, plug, prompt-display), tui/{worker,layer,validate-session}.ts, effect-cmd.ts, heap.ts, bootstrap.ts, error.ts, logo.ts, ui.ts, upgrade.ts, network.ts |
| `server/` | server.ts, auth.ts, mdns.ts, event.ts, global-lifecycle.ts, projectors.ts, init-projectors.ts, proxy-util.ts, tui-event.ts + `routes/instance/httpapi/` = api.ts + groups/ (config, control, control-plane, event, experimental, file, global, instance, mcp, metadata, permission, project, project-copy, provider, pty, query, question, session, sync, tui, workspace) + handlers/ + middleware/ (authorization, compression, cors-vary, error, fence, instance-context, proxy, schema-error, workspace-routing) + lifecycle.ts + websocket-tracker.ts + public.ts + server.ts + shared/ (fence, pty-ticket, public-ui, tui-control, ui, workspace-routing) |
| `storage/` | schema.ts, storage.ts (SQLite: sesión/mensaje/part/todo/config) |
| `bus/` | global.ts (GlobalBus) |
| `sync/` | schema.ts + README.md (event sourcing) |
| `event-manifest.ts`, `event-v2-bridge.ts` | Catálogo de eventos + puente a GlobalBus |
| `lsp/` | client.ts, diagnostic.ts, language.ts, launch.ts, lsp.ts, server.ts |
| `mcp/` | index.ts, catalog.ts, browser.ts, auth.ts, oauth-callback.ts, oauth-provider.ts |
| `image/` | image.ts (wasm photon: máx 2000px, JPEG 80→40, 5MB base64) |
| `project/` | instance-store.ts, instance-context.ts, instance-runtime.ts, bootstrap.ts, bootstrap-service.ts, project.ts, vcs.ts |
| `worktree/` | index.ts (git worktrees desechables, 623 líneas) |
| `snapshot/` | index.ts (git-ad-hoc para /undo, 807 líneas) |
| `git/` | index.ts (interfaz git) |
| `patch/` | index.ts (parser de parches) |
| `auth/` | index.ts |
| `provider/` | provider.ts (2068 líneas: selección de modelos large/small, catálogo, fallbacks), auth.ts, error.ts, model-status.ts, transform.ts |
| `account/` | account.ts (481 líneas: login device-flow, refresh, orgs), repo.ts, schema.ts, url.ts |
| `plugin/` | index.ts (hooks), loader.ts, install.ts, meta.ts, azure.ts, cerebras.ts, cloudflare.ts, digitalocean.ts, xai.ts, snowflake-cortex.ts, modal/, github-copilot/, openai/ (codex + ws), tui/, pty-environment.ts, shared.ts |
| `config/` | config.ts, parse.ts, markdown.ts, agent.ts, command.ts, plugin.ts, managed.ts, entry-name.ts, paths.ts, v2-compat.ts, tui.ts, tui-cwd.ts, tui-host-attention.ts, tui-migrate.ts, variable.ts |
| `command/` | index.ts + template/ (initialize.txt, review.txt) |
| `question/` | index.ts, schema.ts |
| `share/` | session.ts, share-next.ts |
| `acp/` | service.ts (1105 líneas, implementación del Agent Client Protocol), agent.ts, session.ts, tool.ts, profile.ts, permission.ts, content.ts, config-option.ts, directory.ts, event.ts, error.ts, usage.ts |
| `effect/` | instance-state.ts, instance-ref.ts, instance-registry.ts, app-node-builder-v1.ts, app-runtime.ts, bootstrap-runtime.ts, bridge.ts, config-service.ts, runner.ts, run-service.ts, runtime-flags.ts, promise.ts |
| `util/` | rpc.ts, token.ts, wildcard.ts, bom.ts, data-url.ts, defer.ts, filesystem.ts, html.ts, lazy.ts, locale.ts, media.ts, process.ts, queue.ts, record.ts, repository.ts, signal.ts, timeout.ts, error.ts, effect-http-client.ts, iife.ts, local-context.ts, proxy-env.ts, archive.ts |
| `format/` | index.ts, formatter.ts (prettier) |
| `id/` | id.ts (prefijos ULID) |
| `env/` | index.ts |
| `installation/` | index.ts |
| `control-plane/` | workspace.ts, workspace-context.ts, workspace-adapter-runtime.ts, types.ts, util.ts, adapters/ (worktree), dev/ |
| `ide/` | index.ts (detecta Windsurf, VS Code, Cursor, VSCodium) |
| `background/` | job.ts (jobs en background, control de duración) |
| `temporary.ts`, `node.ts`, `sql.d.ts`, `markdown.d.ts`, `audio.d.ts` | utilidades/declaraciones |

---

## 18. El resto del monorepo (los 30 paquetes)

- `packages/core` = el corazón reutilizable (sessions v2, eventos durables, SQLite/drizzle,
  ripgrep, PTY, `Global` con los paths de datos: `const app = "opencode"` en `core/src/global.ts:10`,
  xdgData/cache/config/state/tmp; ~50k líneas más).
- `packages/tui` = la interfaz de terminal (SolidJS + @opentui + keymap).
- `packages/schema` = tipos/contratos. `packages/protocol` = API tipada. `packages/server` =
  capa HTTP reutilizable.
- `packages/sdk` / `client` / `sdk-next` = clientes públicos (promise/effect/embedded).
- `packages/llm` = streaming LLM y `Usage` (tokens con invariantes). `packages/plugin` = API
  pública de plugins. `packages/codemode` = ejecución confinada.
- `packages/app` = web UI embebida; `packages/desktop` = app Electron; `packages/web` =
  opencode.ai.
- `packages/console/*` (SaaS), `stats/*`, `slack`, `enterprise`, `identity`, `containers`,
  `session-ui`, `storybook`.
- `sdks/vscode` = la extensión de VS Code.
- Root/infra: `AGENTS.md` (cómo guían a opencode para desarrollar opencode), `CONTEXT.md`
  (el diseño del sistema de contexto), `specs/`, `.opencode/` (la propia config del repo:
  agentes duplicate-pr/triage, comandos, plugins, skills, themes), `infra/`, `github/`, `nix/`,
  `install/`, `script/`, `perf/`, `artifacts/`, `patches/`.

---

## 19. Lo que NO está en el repo

El **modelo de IA** (big-pickle, opencode/big-pickle) es un servicio externo que no se descarga
ni está en el repo. OpenCode es el andamiaje: herramientas, memoria, permisos, UI, el prompt que
moldea al modelo. El modelo interpreta ese prompt y decide. La "personalidad y reglas" que lees
son el texto crudo de `default.txt` + `AGENTS.md` + skills.

---

## 20. Cómo replicarme: hacer TU propio OpenCode

### Legalidad
Licencia **MIT** (no AGPL): puedes copiar, modificar, renombrar, publicar y vender. La única
condición es conservar el aviso de copyright (`LICENSE`).

### Ruta A — "Mi fork, mi nombre, mi cerebro" (compilar tu binario)
```bash
git clone https://github.com/anomalyco/opencode.git mindevole
cd mindevole && bun install

# 1. Nombre del binario:
#    packages/opencode/script/build.ts:178 → outfile: `dist/$name/bin/<tu-nombre>`
# 2. Marca global (carpetas de datos, logs):
#    packages/core/src/global.ts:10 → const app = "<tu-nombre>"
# 3. Personalidad:
#    packages/opencode/src/session/prompt/default.txt → "You are <TuNombre>..."
# 4. Scopes de paquetes:
#    @opencode-ai/* → @<tu-scope>/*

bun run build      # tu binario compilado (ELF ~180MB con la web UI embebida)
bun run dev        # o prueba en vivo desde el código
```
Scripts: `"build": "bun run script/build.ts"`, `"dev": "bun run ./src/index.ts"`,
`"typecheck": "tsgo --noEmit"`.

### Ruta B — "Cambiar sin tocar el código"
- `AGENTS.md`, `~/.config/opencode/opencode.json` (agentes personalizados, permisos, modelos,
  MCP) y tus skills → "un tú a tu medida" por proyecto, sin recompilar.
- **Embdedded**: `@opencode-ai/sdk-next` ejecuta el motor completo dentro de tu aplicación
  (cero red, tu marca por fuera).

### Lo que NO puedes replicar y sus alternativas

| Dependencia externa | Qué es | Alternativa para ser 100% tuyo |
|---|---|---|
| El modelo (big-pickle) | Servicio en la nube, no está en el repo | Modelo local (Ollama/LM Studio/llama.cpp) o API key de cualquier provider compatible |
| opencode.ai Zen (/connect) | Tienda de modelos alojada | No usarlo; configuras tu provider directo |
| /share y auth de opencode.ai | Servicios en la nube | Reescribir endpoints o no usarlos |
| Web UI embebida | Tuya (MIT) | Reemplazarla vía `packages/app` |

El núcleo (loop, tools, permisos, skills, memoria, /undo, LSP, MCP) es 100% tuyo y offline.

---

## 21. Funcionar con y sin Internet (modelos locales)

- **opencode (la app) = 100% local.** El motor completo funciona sin internet. Lo único que
  necesita red es **la llamada al modelo**.
- **El modelo (el "cerebro")**: big-pickle es un servicio en la nube; no se descarga. Pero puedes
  usar un modelo local con **Ollama / LM Studio / llama.cpp** (exponen API compatible con OpenAI
  en `localhost`).

Ejemplo de config para modelo local:
```jsonc
{
  "provider": {
    "ollama": {
      "npm": "@ai-sdk/openai-compatible",
      "options": { "baseURL": "http://localhost:11434/v1" },
      "models": { "mi-modelo": { "name": "Mi Modelo" } }
    }
  },
  "model": "ollama/mi-modelo"
}
```

**¿Funcionaría igual?** El mecanismo sí; el resultado depende del modelo:
- ✅ Ciclo agente, tools, permisos, skills, compactación: **idénticos**.
- ⚠️ Modelo local = menos inteligencia, más errores de tool-calling, código más pobre que
  big-pickle (nube).
- ⚠️ Sin internet pierdes: `webfetch`, `websearch`, MCP remotos, descarga de skills, Zen, /share.
- ⚠️ Depende de hardware (GPU/VRAM): velocidad y longitud de contexto.
- ✅ OpenCode soporta tool-calling con modelos locales (si el modelo lo soporta; algunos locales
  lo hacen mal y conviene desactivarlo o usar structured output).

**Resumen**: puedes tener un opencode 100% offline con modelo local. Cambias el motor, no el
chasis: todas las capacidades del "ser" siguen siendo tuyas.

---

## Apéndice: Cómo se instaló/verificó todo en esta máquina

- Binario: `~/.local/share/mise/installs/opencode/latest/opencode` (ELF x86-64).
- Config: `~/.config/opencode/opencode.json`, `tui.json`, `node_modules` local.
- Skills: `/home/soul/.agents/skills/`.
- Clon de exploración usado en la conversación: `/tmp/opencode/opencode-src`
  (rama `dev`, commit `bbd72fb`).

*Documento generado y verificado el 5 de sep 2026.*
---

# PATRONES DE OPENCODE ADOPTADOS POR ERIS (5 sep 2026)

> Lo pedido por Daniel: que ERIS pueda hacer "todo lo que hace opencode". Estos tres
> patrones del manual ya están IMPLEMENTADOS en el código de ERIS, no son solo teoría.

## 1. /UNDO — Deshacer ediciones de archivos
- **Qué?** Cada vez que una tool que modifica archivos se ejecuta (file_editor, file_controller,
  file_api, ast_edit, self_edit, self_modify), el dispatcher toma un **snapshot previo** del archivo
  objetivo en `memory/undo_backups/` y anota la operación en `memory/file_undo.json` (anillo de 30).
- **Tool**: `undo` — acciones: `undo` (restaurar la más reciente), `undo_n n=K` (la K-ésima),
  `list` (historial), `stats` (resumen). Si el archivo NO existía antes (creación), el restore lo ELIMINA.
- **Código**: `core/file_undo.py` + hook en `core/tool_dispatcher.py` (antes de ejecutar la tool).

## 2. PERMISOS — Política allow/ask/deny por herramienta
- **Qué?** `core/permission_gate.py` ya pedía confirmación para acciones peligrosas (rm -rf, git push,
  sobreescrituras, shutdown). Ahora acepta **políticas explícitas** en `data/permission_rules.json`:
  `{"tool": "allow|ask|deny", "tool.acción": "...", "*": "..."}`.
- Semántica: `deny` = bloqueo duro (no lo salva ni la sesión confiable); `ask` = diálogo al usuario;
  `allow` = nunca pregunta (salta la heurística). Las reglas específicas ganan a la heurística.
- **Tool**: `permission_policy` — acciones: `view`, `allow tool=X [tool_action=Y]`, `ask`, `deny`,
  `trust minutes=N` (sesión confiable), `untrust`, `reset`.
- **Código**: `core/permission_gate.py` (permission_policy_tool + _match_rule + reload con mtime).

## 3. COMPACTACIÓN DE CONTEXTO — Memoria que cabe
- **Qué?** En el chat de texto (`core/gemini_text_chat.py`), cuando el historial pasa de 24 entradas,
  los turnos viejos se **resumen con Ollama local** en una entrada `[Resumen compactado...]` y se
  conservan los últimos 8. Previene que el contexto explote (equivalente a /compact de opencode).
- Seguridad: si Ollama no responde o no está disponible, NO compacta (no quema cuota de Gemini);
  nunca borra conversación, la deja en el resumen.
- **Código**: `core/gemini_text_chat.py` → `_compact_history()` / `_invoke_ollama_summary()`.

## Conteos
- Tools: **457** (457 + undo + permission_policy), sincronizadas registry↔declarations.
- Verificación: `python test_all.py` → 53 PASS en Linux (1 FAIL ambiental: eris.bat, solo Windows).
