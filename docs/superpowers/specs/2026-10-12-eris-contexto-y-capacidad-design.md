# Eris: contexto compartido, herramientas vivas y acción autónoma

- **Fecha:** 2026-10-12
- **Proyecto:** `/home/soul/ERIS-NEW`
- **Estado:** aprobado por el dueño. Las 4 decisiones abiertas de la Revisión 2
  fueron respondidas el 2026-10-12 y están incorporadas en §8.

> **Revisión 2.** Un constructor revisor leyó este documento contra el código y
> encontró que 3 afirmaciones mías eran falsas y que la Fase 0.1 tenía un
> problema de arquitectura. Corregido. Las correcciones están marcadas
> `[CORREGIDO]`.
>
> **Revisión 3.** Respuestas del dueño incorporadas. La más importante cambia el
> eje del proyecto: **Eris debe funcionar en Windows y en Linux**, no solo en
> Linux. Marcado `[REV.3]`.

---

## 1. Intención y por qué

Eris tiene 503 herramientas registradas, 26 subagentes, un system prompt de 170 KB
y 185.000 líneas de Python. Y a pesar de eso, en el uso cotidiano falla de forma
predecible: pierde el hilo de la conversación, dice que hizo algo que no hizo,
ignora el programa que el usuario tiene abierto, y devuelve respuestas truncadas
o de eco.

El motivo no es que falte capacidad. Es que **el diseño actual garantiza el
fracaso**:

1. Los 26 subagentes son decorativos. 27 de las 32 llamadas a herramientas que
   hacen dentro fallan siempre; las 5 restantes apuntan a herramientas que no
   existen.
2. El contexto de conversación nunca se les pasa. Reciben solo tu última frase.
3. El router por palabras clave secuestra la conversación antes de que el LLM
   pueda usar sus herramientas.
4. El sistema de "sentidos" está escrito únicamente para Windows, y el usuario
   trabaja en Linux/Wayland.

Este diseño arregla esas cuatro fallas de estructura. No agrega features nuevas:
**reactiva capacidades que ya existen pero están desconectadas**, y después sí,
construye lo que falta.

---

## 2. Diagnóstico verificado

Los bugs de la Fase 0 fueron verificados leyendo el código directamente, y
re-verificados por un segundo revisor independiente.

| # | Archivo:línea | Bug |
|---|---|---|
| B1 | `core/sub_agent_crew.py:47` | Importa `dispatch_tool` de `core.tool_dispatcher`. Ese módulo **solo define** `_should_learn` (línea 71) y `_result_status` (línea 105) a nivel de módulo. **La función no existe.** |
| B2 | `core/sub_agent_crew.py:1490` | `agent.execute(task, task_params)` — solo `task_params`. Nunca recibe `_convo_ctx`, ni el resumen de sesión, ni el system prompt. `ResearchAnalyst.execute()` (línea 524) hace `context = context or {}` y nunca lo lee. |
| B3 | `actions/code_analyzer.py:29,39,45,59` | `creationflags=0x08000000` sin guard `os.name` → `ValueError` en Linux. |
| B4 | `agent/task_queue.py:42` | `os.environ["USERPROFILE"]` → KeyError en Linux. Backend del `@tool agent_task`. |
| B5 | `core/observer.py:24` y `:58-61` | Rama Windows: `_WIN32 = __WIN32` → **NameError, el módulo no importa en Windows**. Rama Linux: `_U32 = None` → `get_foreground()` vacío. Los sentidos no funcionan en ninguna plataforma. |
| B6 | `core/logging_setup.py` | **`[CORREGIDO]`** Mi versión anterior decía que un `dup2(/dev/null)` descartaba todos los tracebacks. **Falso.** Ese `dup2` solo silencia ruido de ALSA durante el setup y se **restaura** en el `finally` de `:115-122`. Lo real: hay un `_TeeStream` (`:109-110`) que escribe a `eris.log`, pero **`eris.log` no existe en la raíz** pese a que `setup_logging()` se llama en `main.py:78` y `eris_cli.py:27`. Y `_TeeStream.fileno()` (`:106-107`) lanza `io.UnsupportedOperation`, lo que rompe cualquier cosa que pida un descriptor de los streams. |
| B7 | `main.py:1598` | Resultado de subagente truncado a 300 caracteres + instrucción de "decile en 1 frase corta". |
| B8 | `main.py:1471-1567` | `classify_intent()` secuestra la conversación salvo que el texto empiece con uno de ~130 verbos de `_EXEC_STEMS`. |
| B9 | `core/gemini_text_chat.py:27-38` | De las 87 tools prioritarias, **19 no existen** en `_TOOLS`: `hermes_web_search`, `hermes_web_scraper`, `hermes_page_summarizer`, `hermes_data_analyzer`, `hermes_csv_processor`, `hermes_writer_articles`, `hermes_email_writer`, `hermes_code_review`, `hermes_test_generator`, `hermes_security_audit`, `hermes_feed_monitor`, `hermes_github_sync`, `lab_pulse`, `paper_search`, `repo_discovery`, `evolution_campaigns`, `learning_engine`, `aprendizaje_videos`, `auto_defensa`. |
| B10 | `core/action_imports.py:1209-1265` | 13 `try: from core.hermes_tools import ...`. **`core/hermes_tools.py` no existe.** |
| B11 | `core/tool_dispatcher.py:124` | `_result_status` clasifica `{"ok": false, "msg": "..."}` como `"ok"`. Eris aprende la lección equivocada. |
| B12 | `core/agent_definitions.py:142-152` | **`[CORREGIDO]`** Mi versión anterior culpaba a `main.py:_build_agent_router()`. **Falso:** ese archivo nunca menciona esos agentes. Lo muerto son las declaraciones `"handler": 'agents.system_monitor_agent.system_monitor_agent'` y `'agents.deploy_agent.deploy_agent'` (esos módulos no existen) más los imports en `core/action_imports.py:297-303`. `core/agent_router.py:57-74` las registra `"enabled": True` sin comprobar handler. Peor de lo que parecía: las keywords de `deploy` incluyen `limpiar`, `optimizar`, `backup`, `disco`, `estado`, `pip`, y las de `system_monitor` incluyen `estado`, `chequeo`, `procesos`, `cpu`, `ram`, `limpiar` — con el umbral `best_score < 3` de `agent_router.py:141`, frases como "limpia el disco" puntúan alto a agentes que **nunca pueden correr**. |
| B13 | pyautogui / pygetwindow | **`[CORREGIDO]`** Mi versión anterior decía 28 archivos con guards `except ImportError` que no atrapan. **Falso:** ya están arreglados — `actions/browser_control.py:4-8` y `actions/computer_control.py:11-15` usan `except Exception:`, y `core/action_imports.py` tiene **0** `except ImportError` contra 538 `except Exception`. Lo que queda son tools **degradadas**, no crasheantes. |
| B14 | `core/sub_agent_crew.py:110-116` | Código inalcanzable, comentado después de un `return`. |
| B15 | varios | Números desactualizados: `main.py:807` dice 19 subagentes (26), `eris_cli.py:202` dice 507 tools (503), `core/prompt.txt:29` dice 12 agentes (16). |
| B16 | `core/sub_agent_crew.py` | **`[NUEVO]`** De las 32 tools que llama `_dispatch_tool`, **5 no están en `_TOOLS` ni en `actions/`**: `api_invoke`, `paper_search`, `repo_discovery`, `sqlite_query`, `webhook_sender`. El fallback dinámico de `_generic_dispatch` (`tool_dispatcher.py:828`) no puede salvarlas: no hay módulo. Dos son load-bearing (`InvestigadorExterno` se construye sobre `api_invoke` y `paper_search`). |

---

## 3. Decisiones tomadas con el usuario

Estas son del dueño del proyecto. No se revisan.

| Decisión | Elección | Razón |
|---|---|---|
| **Plataformas objetivo** | **Windows Y Linux** `[REV.3]` | El dueño lo dijo al final: *"quiero que Eris pueda utilizarse en los 2 sistemas operativos"*. **Esto corrige la Revisión 2**, donde solo decía Linux. Ninguna corrección puede romper Windows. |
| **Cómo actúa sobre código** | **Editando archivos directamente** | Elegido explícitamente sobre controlar el mouse. Es exacto y no se rompe. |
| **Los ojos** | **Sí, ahora** | No es riesgoso y es lo que más falta. |
| **Control de mouse/teclado** | **Diferido** | `ydotool` no está instalado; Wayland es frágil. |
| **Autonomía** | **Las dos: propone y ejecuta** | Que lea el pedido y actúe sola, sin interruptor. |

**Consecuencia de `[REV.3]` que hay que respetar en cada fase:**

- El arreglo de `creationflags` (0.2a) **no es "quitarlo"**: es poner un guard que
  devuelva el flag en Windows y `{}` en el resto. Borrarlo rompería Windows.
- El observer (0.4) necesita **los dos backends vivos**, no solo Hyprland.
- `src_clean/` **se conserva** (§8.4): es el artefacto de distribución de
  Windows. Nota honesta: los `.pyd` solo cargan en Windows, así que **el
  desarrollo en Linux jamás debe depender de ellos**.
- Toda verificación debe correr en Linux (lo que hay) **y** declarar qué queda
  sin probar en Windows, si no hay forma de probarlo desde aquí.

### `[REV.3]` ⚠️ Restricción nueva y permanente

Todo el trabajo pasa a ser **cross-platform**. No es "arreglar Linux". Es
"arreglar lo que está roto, sin romper la otra plataforma". Una corrección que
funciona en Linux y rompe Windows es un error, no un éxito parcial.

### Entorno verificado de la máquina destino

```
XDG_SESSION_TYPE=wayland   WAYLAND_DISPLAY=wayland-1   XDG_CURRENT_DESKTOP=Hyprland
Python 3.15.0 (mise)       GPU: /dev/dri/card1         Ollama: apagado
hyprctl OK   wtype OK   grim OK   slurp OK   wl-copy OK   ffmpeg OK
xdotool FALTA   ydotool FALTA
```

**`[CORREGIDO]`** Mi versión anterior daba este bloque por el entorno completo.
Falta lo más importante y es un bloque entero:

- **No existe `.venv-linux/`**, pese a que lo referencian `run_linux.sh:29-33` y `HANDOFF_OPENCODE.md:2`.
- El único intérprete es el Python 3.15 de `mise`, sin `PyQt6`, `requests`, `psutil`, `numpy`, `PIL`, `bs4`, `yaml` ni `google-genai`.
- **`pytest` no está instalado.** `requirements-linux.txt` está sin pinear.
- `core.tool_registry` **sí** importa (503 keys), así que la verificación estática/AST funciona. **Nada de nivel runtime funciona hoy.**

Esto es una precondición de todo el proyecto (§7.6).

---

## 4. Objetivos

1. Que todo lo que Eris **ya sabe hacer** deje de estar roto.
2. Que deje de perder el contexto de la conversación, en cualquier ruta de ejecución.
3. Que sepa qué ventana y qué archivo estás usando, sin que se lo pidas.
4. Que lea tu pedido y decida sola si investigar, proponer o actuar.
5. Que nunca destruya trabajo: todo cambio reversible.
6. Que la terminal tenga la misma capacidad que la app, no menos.

## 5. No-objetivos

- **No** agregar features nuevas hasta terminar la Fase 3.
- **No** rediseñar la voz, la GUI PyQt6 ni el avatar VRM.
- **No** migrar de proveedor de LLM sin confirmación explícita.
- **No** reescribir `main.py`. Es un orquestador delgado de 5.349 líneas; el problema no es su tamaño, es que las piezas que llama no funcionan.
- **No** borrar `src_clean/` ni artefactos de Windows sin hablarlo.

## 6. Anti-objetivos

Lo que también sería un fracaso, aunque "funcione":

- Que Eris diga que hizo algo sin haberlo hecho.
- Que el sistema silencie errores para que la salida se vea limpia.
- Que "arreglar" signifique silenciar excepciones con `except Exception: pass`.
- Que Eris edite archivos sin copia de seguridad previa.

---

## 7. Restricciones

### 7.1 Archivos protegidos

`HANDOFF_OPENCODE.md` §3 declara 6 archivos con WIP del dueño, "no tocar":
`core/gemini_text_chat.py`, `data/cli_sessions/default.json`,
`data/knowledge/eris_inventario_vivo.md`, `eris_cli.py`,
`memory/self_care_apuntes.md`, `vault/Capacidades/Estado de Evolución.md`.

**`[REV.3]` Autorizados para edición.** El dueño respondió *"sí, tocarlos si hace
falta"*. Esto desbloquea dos sub-fases que antes quedaban abiertas:

- **B9**: los 19 tools priorizados de Gemini que no existen (0.5).
- **Fase 1.2**: que la CLI deje de ser una isla (`eris_cli.py`).

**Restricción que se mantiene igual:** nada de esto autoriza a borrar trabajo
inacabado. Si al abrir cualquiera de los 6 hay WIP a medio hacer que no se puede
integrar con el cambio, se para esa línea, se avisa, y se sigue por el resto del
plan. El trabajo del dueño no se pisa.

### 7.2 Límite de Gemini

Máximo **128 `function_declarations`**. Con 503 tools el chat crashea con
`400 INVALID_ARGUMENT`. Cualquier trabajo en B9 respeta este techo.

### 7.3 `[REV.3]` Gemini vuelve a ser el modelo principal

Antes: `gemini_api_key` estaba vacío a propósito (`HANDOFF_OPENCODE.md:126`,
"las declarations de Eris rompen el schema de Gemini") y **OpenRouter quedaba
como punto único de falla** de todo el sistema.

**Decisión del dueño:** *"te dejo la api de Gemini, y que OpenRouter funcione de
respaldo"*. Es decir: **Gemini primero, OpenRouter como failover**.

Consecuencias concretas:

1. La clave va en `config/api_keys.json → gemini_api_key`. Ese archivo está en
   `.gitignore` (líneas 12 y 49) y **nunca** se escribe en un documento, un
   commit o un log.
2. **B9 cambia de remedio.** Con Gemini como principal, las 19 tools inexistentes
   **no se eliminan: se tienen que volver reales**, porque son parte de lo que el
   modelo ve.
3. **El techo de 128 `function_declarations` (§7.2) pasa a ser la restricción
   dominante.** No es "arreglar 19 tools": es elegir, de las 503, un subconjunto
   de ≤128 que sea coherente y que no contenga referencias rotas.
4. La cadena de failover queda `Gemini → OpenRouter → xKiro → Groq → Ollama`.
   **xKiro no está integrado y Ollama está apagado**: hay que hacerlos reales o
  sacarlos de la cadena, para no prometer un respaldo que no existe.

### 7.4 Python 3.15

Ambiente muy reciente; varias dependencias pueden no tener wheel.

### 7.5 Permisos y seguridad

- `DANGEROUS_COMMANDS` y el permission gate deben seguir **fail-closed** (P3 de
  `HANDOFF_OPENCODE.md` ya lo arregló; no revertir).
- Lectura de portapapeles o captura de pantalla queda en log observable, no silenciosa.

### 7.6 `[NUEVO]` Precondición: el entorno de Python no existe

Nada del §12 es verificable hasta que exista un intérprete con las
dependencias. Esta es la **primera** tarea del proyecto, antes de la Fase 0.

---

## 8. `[REV.3]` Decisiones del dueño — respondidas

Las cuatro preguntas de la Revisión 2. Todas respondidas el 2026-10-12.

### 8.1 Seguridad → **Conectar el guardián primero**

> *"Conectar el guardián primero."*

Convierte la seguridad en **precondición**, no en algo posterior. Se agrega
una **Fase 0.0**, que va **antes** de arreglar B1:

1. Conectar `ActionGuard` (`core/sub_agent_crew.py:1194`) al camino de
   `dispatch_tool` para toda tool que escriba.
2. `core/permission_gate.py` se consulta en `dispatch_tool` y es **fail-closed**.
3. Grabar en log toda invocación de tool de escritura con su resultado.
4. **Recién después** se arregla B1 y prenden las 27 tools.

Efecto colateral favorable: con el permiso gate ya en el camino, activarlas pasa
de ser "27 herramientas sueltas" a ser "27 herramientas supervisadas".

### 8.2 Modelo → **Gemini principal, OpenRouter de respaldo**

> *"te dejo la api de Gemini […] y que OpenRouter funcione de respaldo."*

Ver §7.3. Gemini primero, failover a OpenRouter. B9 pasa de "eliminar 19 tools" a
"hacerlas reales dentro del techo de 128".

### 8.3 Archivos protegidos → **Autorizados**

> *"Sí, tocarlos si hace falta."*

Ver §7.1. Con la salvedad de no pisar WIP del dueño.

### 8.4 `src_clean/` y `eris_workspace/` → **Se conservan**

> *"déjalo como está porque quiero que Eris pueda utilizarse en los 2 sistemas
> operativos como Windows y Linux."*

Se conservan, y esto es lo que dispara el cambio de eje `[REV.3]`: la plataforma
objetivo son **las dos**. `src_clean/` es el artefacto de distribución de Windows.
Nota honesta: los `.pyd` **solo cargan en Windows**, así que en Linux son peso
muerto — pero no se tocan, y el desarrollo en Linux no debe depender de ellos.

---

## 9. Diseño

### Fase -1 — Que exista un Python que corra (precondición)

Crear `.venv-linux/`, instalar `requirements-linux.txt` pineado, instalar `pytest`,
verificar que `import core.tool_registry` sigue devolviendo 503 keys y que
`ui.py` levanta. Sin esto, ninguna otra fase se puede verificar.

**Definición de hecho:** `./run_linux.sh` arranca la GUI y `pytest` corre.

---

### Fase 0.0 — `[NUEVO, REV.3]` Conectar el guardián ANTES de tocar nada

Esta fase es la respuesta a §8.1 y **va primera**. Sin ella, la Fase 0.1 le da
vida a 27 herramientas sin supervisión.

El estado actual, verificado:

- `ActionGuard` existe en `core/sub_agent_crew.py:1194`, es un `SubAgentBase`
  corriente que se invoca a mano. `_dispatch_tool` (`:44-51`) **nunca lo consulta**.
- `core/permission_gate.py` lista `shell_session`, `terminal_agent`, `file_api`,
  `git_control` en `DANGEROUS_TOOLS`, y ya es **fail-closed** desde el P3 de
  `HANDOFF_OPENCODE.md`. Ese trabajo está hecho y no hay que revertirlo.
- `_subagents_loop` (`main.py:790`) despacha cada **30 segundos**, sin supervisión.

Trabajo:

1. **`dispatch_tool` consulta el permission gate antes de ejecutar.** Fail-closed:
   cualquier excepción al evaluar → denegar.
2. **`dispatch_tool` consulta `ActionGuard`** para toda tool de escritura. El
   guardián se registra como `SubAgentBase` real en el registro de la tripulación,
   no como invocación manual.
3. **Log de auditoría.** Toda tool de escritura se registra con: subagente que la
   pidió, tool, params, decisión del guardián, resultado. Va a archivo **y** es
   consultable desde el chat.
4. **Prueba de humo:** con el gate activo, un subagente que intente
   `git_control push` debe ser **denegado y registrado**. Se verifica antes de
   tocar B1.

**Definición de hecho:** hay un test que demuestra que una tool de escritura es
denegada sin confirmación, y que la denegación queda registrada.

---

### Fase 0 — Que nada esté roto

#### 0.1 Exponer el despachador de herramientas a los subagentes (arregla B1, B16)

**`[CORREGIDO]` — el diseño anterior era imposible de implementar.** Decía
"resolver el singleton `ToolDispatcher` y ejecutar sincrónicamente propagando la
excepción". Los tres puntos fallan:

1. **No hay singleton.** `ToolDispatcher.__init__(self, eris)` se construye
   ad-hoc en exactamente 3 lugares: `main.py:619`, `agents/tool_executor.py:68`,
   `eris_cli.py:331`. No existe `get_tool_dispatcher()`.
2. **`execute(fc)` no tiene esa firma.** Toma un `types.FunctionCall`, necesita
   un event loop vivo (`:156`, `:293`), y desreferencia `self._eris.ui`,
   `self._eris.speak`, `self._eris._session_id`.
3. **Traga las excepciones que el diseño quiere propagar.** `:460-461` devuelve
   `f"Tool '{name}' failed: {e}"` y `_generic_dispatch` devuelve
   `f"Error en {name}: {e}"`. **Ningún wrapper puede recuperar la excepción.**

**Mi decisión: ir por debajo de `ToolDispatcher.execute()`.** Ya existe el
precedente funcionando: `agents/tool_executor.py:88-101` hace
`get_tool(name)` → `self._dispatcher._build_kwargs(tool, params)` → `tool(**kwargs)`,
y **propaga**. Son ~30 líneas.

Nuevo `core/tool_dispatch_api.py`:

```python
def get_dispatcher() -> ToolDispatcher
def get_host() -> Host                  # módulo-nivel, resuelve el ErisLive vivo
class HeadlessHost: ...                 # para CLI: ui.ask/speak/muted/_session_id
def dispatch_tool(tool_name, params, *, host=None, context=None) -> Any
```

Reglas no negociables:
- **Nunca** devuelve un string de error disfrazado de resultado. Si una tool
  falla, la excepción sube. Si la tool no existe, `KeyError` con la lista de
  nombres válidos.
- Pasa por `core/permission_gate.py` **antes** de ejecutar (ver 0.2b).
- Pasa por `core/sub_agent_crew.py:1194` `ActionGuard` para tools que escriben.

**Las 5 tools inexistentes (B16)**: crear o eliminar, una por una. Por defecto
**eliminar** (`api_invoke`, `paper_search`, `repo_discovery`, `sqlite_query`,
`webhook_sender`) y reconstruir lo que dependía de ellas. Si el dueño prefiere
mantener alguna, se implementa.

#### 0.2 Reparar lo que está roto en Linux

**a) `creationflags`.** **`[CORREGIDO]`** Mi versión anterior decía "~18 call-sites
en 9 archivos". **Real: 62 ocurrencias en 26 archivos.** Muchos ya están
branch-eados (`core/tts_engine.py` tiene 6 sitios y 6 guards).

**`[REV.3]` Y el arreglo NO es quitarlo.** Windows depende de ese flag. El guard
devuelve el flag en Windows y `{}` en el resto:

```python
# core/platform_compat.py
def run_flags() -> dict:
    return {"creationflags": 0x08000000} if os.name == "nt" else {}
```

Definición de hecho: **ningún `creationflags` sin guard queda en el repo**,
verificado con un script, **y el test suite pasa en Windows** (o, si no hay forma
de correrlo desde aquí, el cambio se limita a sustituir la llamada por
`run_flags()` y no se toca ninguna otra línea del call-site).

Nuevo `core/platform_compat.py` con `run_flags() -> dict`, aplicado en
`actions/code_analyzer.py`, `actions/terminal_agent.py`, `actions/system_monitor.py`,
`actions/vscode_controller.py`, `actions/clipboard_manager.py`,
`actions/screen_context.py`, `actions/self_healing_loop.py`,
`actions/eris_guardian.py`, `actions/cancion_generator.py`, `core/shell_session.py`,
`core/crash_recovery.py`, `core/ollama_autostart.py`.

**b) Permission gate en el camino.** `core/permission_gate.py` ya lista
`shell_session`, `terminal_agent`, `file_api`, `git_control` en
`DANGEROUS_TOOLS`. `dispatch_tool` debe consultarlo y ser **fail-closed**.

**c) `agent/task_queue.py:42`.** `USERPROFILE` → `Path.home()/"Desktop"` con
fallback a `xdg-user-dir DESKTOP`.

#### 0.3 Los errores tienen que verse (arregla B6, corregido)

**No** sacar el `dup2` de ALSA — re-explicaría el spam de sonido y no arregla
nada. Lo correcto:

- Verificar por qué `eris.log` no existe pese a los dos call-sites de
  `setup_logging()`. Que exista y rote.
- Arreglar `_TeeStream.fileno()` (`:106-107`), que hoy lanza
  `io.UnsupportedOperation` y rompe a quien pida un descriptor.
- Un buffer de errores visible en la UI.

**Antes de tocar nada**, reproducir el escenario que motivó el bug original
(agente que devuelve `"[Tool X no disponible]"`) y confirmar **dónde** queda
registrado hoy. La premisa de mi versión anterior puede tener otro origen real.

#### 0.5 Cerrar los holes del registro (B9, B10, B12)

- **B12**: quitar de `AGENT_DEFINITIONS` los dos handlers muertos, **o** poner una
  regla en `classify_intent` de "saltar agentes sin handler". Por defecto **la
  regla**, porque no rompe el test. Ojo: `tests/test_agent_router.py:12` asserta
  el conjunto de definiciones, y `core/self_evolution.py:164` hardcodea "25
  sub-agentes" en un prompt.
- **B9 `[REV.3]` — cambió el remedio.** Con Gemini como principal (§7.3), las 19
  tools no se eliminan en bloque: **las importantes se vuelven reales**, y el techo
  de 128 `function_declarations` manda sobre el resto. Hay que construir de verdad:
  `hermes_web_search`, `hermes_web_scraper`, `hermes_code_review`,
  `hermes_security_audit`, `hermes_csv_processor`, `hermes_data_analyzer`,
  `hermes_page_summarizer`. Las demás salen de `_GEMINI_PRIORITY_TOOLS` hasta que
  se necesiten. `gemini_text_chat.py` está autorizado para edición (§7.1), pero
  **no** se revierte `_gemini_tools()` a `TOOL_DECLARATIONS` completo (AGENTS.md).
  Recordar el sync sagrado: registry **y** declarations, `len == len`, 0 dupes.
- **B10**: crear `core/hermes_tools.py` con las tools que sí se construyen, o
  borrar los 13 imports muertos.

**0.7 `[NUEVO, REV.3]` La cadena de failover tiene que ser real (§7.3)**

`Gemini → OpenRouter → xKiro → Groq → Ollama`. Hoy **xKiro no está integrado y
Ollama está apagado**. Prometer un respaldo que no existe es peor que no prometerlo:
integrar xKiro o sacarlo de la cadena, y decidir qué hacer con Ollama. Verificarlo
con un test que **caiga** el backend primario y compruebe que el secundario
responde.

#### 0.6 Corregir el estado (B7, B8, B11, B14, B15)

- Truncado 300 chars: subir el límite y **no** instruir al LLM a resumir el
  resultado de una herramienta.
- B8: `_EXEC_STEMS` pasa a ser una señal más, no la única puerta. Si el pedido no
  matchea un verbo conocido, **dejar que el LLM decida** con sus 503 tools.
- B11: `_result_status` mira la clave booleana `ok`/`success` antes de la
  heurística de strings. **Decisión mía: eso invalida lo aprendido a la
  inversa** — `procedimientos.registrar_paso`, `skill_auto_creator`,
  `proactive_context`, `training_pipeline` y `truth_audit` aprendieron de los
  estados equivocados. Purgar ese estado aprendido junto con el fix.
- B14: eliminar código inalcanzable.
- B15: derivar los números de `len(registry.get_all_agents())` y `len(_TOOLS)`.

---

### Fase 1 — Un solo cerebro

**1.1 `SharedContext`.** Nuevo `core/shared_context.py`, singleton por proceso:
`convo_ctx`, `session_summary`, `project_root`, `active_file`, `foreground_app`,
`identity`, `read_only`.

**1.2 Pasarlo a todos lados.**
- `dispatch_to_sub_agent(..., shared_context)` → `execute(task, params, context)`.
  Cada agente declara qué campos usa.
- La CLI deja de ser una isla (requiere `eris_cli.py` — ver §8.3).
- Extraer la lógica de `_build_config()` (`main.py:2924-3720`, ~25 bloques de
  contexto) a un módulo reutilizable, llamado desde GUI, CLI y subagentes.

**1.3 Fin del eco.** `main.py:1607-1616` inyecta el resultado **y** lo anuncia
por voz. Una sola vez.

---

### Fase 2 — Los ojos

**2.1** `core/window_detect.py` con `get_foreground`, `list_windows`,
`get_active_class`. **`[REV.3]` Los DOS backends tienen que quedar vivos:**

| Backend | Plataforma | Estado |
|---|---|---|
| `ctypes`/user32 | Windows | Funciona; hoy tieñe por el bug B5 |
| `hyprctl` | Linux/Hyprland | **A construir** — el patrón ya existe en `actions/computer_control.py:191` y `actions/ide_integration.py:192`; se extrae a un módulo común y ambos lo consumen |
| genérico | otros | Devuelve vacío honestamente |

AGENTS.md documenta que en Hyprland ≥0.55 `dispatch` es Lua y la sintaxis legacy
`focuswindow address:...` crashea con rc 7. Respetarlo.

**2.2** El observer ya tiene los conjuntos de clasificación (`_CODE_PROCS` con 28
editores, `_TERMINAL_PROCS`, `_BROWSER_PROCS`, `_SENSITIVE_PAT` con 27
patrones). Con el backend vivo, `get_foreground()` alimenta la clasificación solo.

**2.3** En CLI, `project_root` = cwd, más una tool de mapeo que devuelve el árbol
con una línea de qué hace cada archivo. Verificar que `codebase_explorer` funciona
y que Eris la usa sola al detectar un proyecto.

**2.4** Los 27 patrones de `_SENSITIVE_PAT` **silencian la observación** y
registran el evento sin reportar contenido.

---

### Fase 3 — Que actúe sola

**3.1 Lectura de intención.** `core/intent_reader.py` clasifica el pedido en
`INVESTIGAR` / `EDITAR` / `AUTONOMO`, combinando **texto + `SharedContext`**, no
solo palabras.

| Modo | Cuándo | Qué hace |
|---|---|---|
| `INVESTIGAR` | "investiga", "qué está pasando" | Lee, ejecuta, **no toca archivos**. Diagnóstico + parche propuesto. |
| `EDITAR` | "está en la línea N", "cambiá esto" | Edita directo, con backup. |
| `AUTONOMO` | "arreglalo", "hacelo funcionar" | Leer → hipótesis → probar → verificar → reintentar. Tope de intentos. Con backup. |

"Hay un error que no logro solucionar" con VS Code abierto es `AUTONOMO`; en un
chat vacío es `INVESTIGAR`. El contexto, no el verbo, decide.

**3.2 Nada se rompe.** Toda escritura pasa por `core/file_api.py`, que ya tiene
backups y `validate_ast`. Backup previo en `memory/undo_backups/`. El resultado dice
**exactamente** qué líneas cambiaron. `TAREA COMPLETA` y un `deshacer` por chat.

**3.3 Autonomía desenredada.** `_run_self_improvement`, auto-continuación (10
pushes), `core/autonomia.py` (idle > 420 s), observer proactivo (idle > 60 s) ya
existen. El trabajo es **enchufarlos al `SharedContext`** y bajar cooldowns que hoy
los hacen inaudibles.

**3.4 Verificación antes de "listo".** Al mandato de "nunca digas no puedo sin
intentar 3 formas" se le suma el simétrico: **no digas "listo" sin verificar** —
correr el código, correr los tests, releer el archivo. El anti-objetivo §6 lo exige.

---

## 10. Fuera de alcance en esta pasada

| Ítem | Por qué no ahora |
|---|---|
| `nul` — 40 bytes, salida de un `cmd.exe` fallido | Basura. Preguntar antes de borrar. |
| `src_clean/` — 55 `.pyd`, 30 MB, versionado | **`[REV.3]` Se conservan** (§8.4): es el artefacto de distribución de Windows. No se tocan, pero **el desarrollo en Linux jamás debe depender de ellos**. |
| `eris_workspace/` — proyecto paralelo, 0 imports | **`[REV.3]` Se conserva** (§8.4). |
| `memory/sub_agent_plans/` — 118 JSON, ~250 KB, nunca purgados | Mantenimiento. |
| `memory/tool_sync_backups/` — 519 KB + 45 KB | Mantenimiento. |
| 13 módulos duplicados `actions/` vs `core/` | Solo 2 con shadowing real. Analizar cuál gana. |
| `bios/` (4 archivos, 0 imports), `context/*.md` (0 imports) | Stale. `context/AGENTS.md` habla de Windows y de una identidad "Nyx". |
| Rutas hardcodeadas `D:\...` en 6 archivos | Limpieza posterior. |
| Avatar VRM no visible en Linux | Bug conocido y documentado. |

---

## 11. Deuda que se hereda

No la arregla este diseño:

- `os_system: "windows"` desactualizado en la config.
- `visual_expressions` necesita `libtk8.6.so`, ausente.
- **xKiro no integrado al failover** — pasa a ser trabajo de Fase 0.7.
- Puerto 6789 compartido entre `core/vrm_server.py` y el bridge de opencode.
- GUI-automation (`browser_control`, `computer_control`, `native_ui`,
  `desktop_control`, `screen_vision`) degradada en Wayland. Con `[REV.3]` ya no es
  deuda: es el comportamiento correcto en Linux, y funciona en Windows.
- 3 WARN permanentes del test suite (neuro nodes, chromadb, `ctypes.windll`).
- Hermes rota su `agent_key` aproximadamente cada hora.

---

## 12. Verificación

| Fase | Cómo se verifica |
|---|---|
| **-1** | `./run_linux.sh` levanta la GUI. `pytest` corre. `import core.tool_registry` → 503. |
| **0.0 `[REV.3]`** | Un test demuestra que una tool de escritura es **denegada** sin confirmación y que la denegación queda registrada. Debe existir **antes** de tocar B1. |
| **0** | Script que invoca cada tool y reporta estado real. Las 32 llamadas de subagente devuelven resultado, no placeholder. `pytest` en verde. Cero `creationflags` sin guard. Sync registry/declarations sigue 503/503 con 0 dupes. Failover probado **cayendo** el backend primario. |
| **1** | Un subagente responde con conocimiento del historial. CLI y GUI producen el mismo contexto. |
| **2** | Eris nombra la ventana activa sin que se lo pidan. En CLI mapea el árbol del proyecto. |
| **3** | "Hay un error que no logro solucionar" produce diagnóstico o fix sin intervención. Un archivo editado se deshace. |

**Sobre Windows:** desde esta máquina no se puede ejecutar el suite en Windows.
Cada corrección `[REV.3]` se limita a sustituir el call-site por `run_flags()` (o
equivalente) sin tocar la línea vecina, y se declara explícitamente qué quedó sin
probar en Windows. No se afirma que algo "funciona en ambos" sin haberlo visto.

---

## 13. Para el constructor

**Decidido por el dueño, no lo revises:**

- **Windows Y Linux.** Ningún arreglo puede romper la otra plataforma.
- Edición directa de archivos como vía de acción; control de mouse diferido.
- Ojos: los dos backends (ctypes + hyprctl).
- Autonomía de ambas clases: propone y ejecuta.
- **Conectar `ActionGuard` y el permission gate ANTES de arreglar B1** (§8.1).
- **Gemini principal, OpenRouter de respaldo** (§8.2).
- Los 6 archivos de §7.1 **están autorizados** para edición.
- `src_clean/` y `eris_workspace/` **se conservan**.

**Decisiones mías, para que las revises al leer** (puedo cambiarlas): ir por debajo
de `ToolDispatcher.execute()` (0.1); eliminar las 5 tools inexistentes de B16;
sweep de los 62 `creationflags` con `run_flags()` y definición de hecho por script;
no sacar el `dup2` de ALSA; purgar el estado aprendido al arreglar B11; regla
"saltar agentes sin handler" en vez de borrar definiciones; construir las 7 tools
hermes de B9 y sacar las otras 12 de la lista priorizada.

**Tu trabajo:** arrancar por **Fase -1**. Sin un Python que corra, todo lo demás
es a ciegas. Después **Fase 0.0** (el guardián), que es la condición que puso el
dueño. Después 0.1, el cambio de mayor impacto. Commiteá y reportá qué funciona
**medido, no supuesto**.

**Baseline con el que comparar:** `test_all.py` está en **176 PASS / 1 FAIL
ambiental / 3 WARN**. No puede bajar de ahí sin que se justifique cada diferencia.