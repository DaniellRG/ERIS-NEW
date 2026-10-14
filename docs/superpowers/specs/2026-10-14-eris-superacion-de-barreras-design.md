# Eris: el motor de superación de barreras (Proyecto 1 de 2)

- **Fecha:** 2026-10-14
- **Proyecto:** `/home/soul/ERIS-NEW`
- **Origen:** pedido del dueño (2026-10-13/14). Quiere que Eris, **por sí misma**,
  detecte que no llega a una meta, entienda qué le falta, se construya lo que le
  falta (herramienta, skill, API, función) y lo use hasta cumplir el objetivo,
  autogestionándose — con evidencia real y sin tocar zonas peligrosas.
- **Estado:** borrador para aprobación del dueño. Lo leyó un revisor independiente
  (builder-check); sus preguntas y las decisiones que faltan están en §12.

> **Método.** Una fase = un commit local, nunca push. Baseline sagrado:
> `python test_all.py` = 177 PASS / 0 FAIL / 3 WARN, y sync de tools 510/510.
> El dueño todavía **no** usó a Eris en tareas reales: este diseño se basa en
> escenarios imaginados y se corregirá con la práctica.

---

## 1. Intención y por qué

Eris ya sabe hacerse cosas. La **Fábrica** (`fabrica`) crea librerías, tools y
skills reales con backup y rollback; la **auto-fábrica** convierte secuencias
repetidas en tools; el **motor de aprendizaje** investiga y cristaliza; **mission**
la hace trabajar ordenada; **escalada** mide lo que domina; sus **metas** existen
en tres stores (dos de ellos ya federados al prompt desde F5a).

Lo que **no** existe es el bucle que cierra. Cuando Eris *no llega* a una meta,
hoy nada:

1. lo declara como barrera (solo hay detección de *tarea trabada >120s* en la cola
   de sub-agentes, y de *goal estancado* en `goal_tracker`),
2. diagnostica qué le falta (conocimiento, tool, acceso, permiso, recurso, o la
   meta mal definida),
3. decide el camino **pensando el riesgo antes** de actuar,
4. se construye esa capacidad (tool / librería / skill / script / API / servidor),
5. la usa, y
6. **verifica con evidencia** que llegó de verdad.

Este proyecto construye ese bucle: el **motor de superación de barreras**.

**Criterio de éxito.** Con una meta dada (por el dueño o auto-generada), si Eris
puede alcanzarla con lo que tiene, la alcanza; y si le falta algo, es capaz de
producir ese algo, usarlo y demostrar con un artefacto verificable que llegó. Si
no puede, lo dice con honestidad y explica qué necesitaría — nunca miente ni
declara "listo" sin prueba.

**Anti-goals (lo que haría fracasar el proyecto).**

- Que fabrique basura o tools rotas para *simular* avance.
- Que declare éxito sin evidencia ("falso positivo").
- Que toque el sistema operativo, los datos personales o la red de casa sin OK.
- Que entre en un bucle infinito creando y reintentando sin progreso.
- Que gaste CPU/red/disco sin límite.

---

## 2. Lo que ya existe (reconocimiento verificado en el código)

| Pieza | Archivo | Qué aporta al bucle |
|---|---|---|
| Fábrica | `core/eris_fabrica.py` | `crear_libreria` / `crear_tool` / `crear_skill` con backup, rollback e inventario. **Validación desigual:** `crear_tool` compila + prueba de humo `status` y cada acción; `crear_libreria` solo compila (no ejecuta la función); `crear_skill` no valida nada. |
| Auto-fábrica | `core/auto_fabrica.py` + `core/skill_auto_creator.py` | Detecta patrones de tools repetidos y crea tools (tope 2/día). |
| Motor de aprendizaje | `core/learning_engine.py` | `investigar` (papers/repos/web) → `estudiar` → `cristalizar` skill en `skills/evolution_learning/`. |
| Mission | `core/mission_agent.py` | Protocolo plan→explorar→editar→verificar→step→learn→close. `verify()` corre py_compile/ruff/pytest y no declara "listo" si queda rojo. |
| Tripulación | `core/sub_agent_crew.py` | MissionPlanner (plan + `proyectar` a cola), TaskRouter, DependencyResolver, **ProgressTracker** (foto de tareas WORKING >120s), QualityCritic, FactVerifier, DecisionArbiter (**stub**, §5.3), ConnectorHub, **ActionGuard**, EvolutionEngine, SkillForge, **TraceKeeper** (trazas replayables `data/agent_traces/`). Re-encolado real: `SubAgentRegistry.requeue_stuck_tasks()`. |
| Autonomía | `core/autonomy.py` | `LOW_RISK_ACTIONS`, `auto_install_package`, `execute_autonomous`, `run_autonomous_cycle`. |
| Riesgo / custodia | `core/permission_gate.py`, `core/tool_dispatch_api.py` | `assess_risk`, `guard_check` → `GuardVerdict`, precedencia de `config/tool_risk.json` (**hoy vacío**). `guard_check` solo se consulta en `tool_dispatch_api.dispatch_tool`; el camino del chat (`core/tool_dispatcher.py:249`) solo pasa por `permission_gate` (ver §6). |
| Verdad / evidencia | `core/truth_audit.py` | `audit_turn`, `evidence_block`; detecta cuando Eris dice algo que las tools no respaldan. |
| Metas | `core/goal_tracker.py` (`data/goals.json`, **vacío**), `core/goal_setting.py` (`memory/goals.json`), `actions/goals.py` (`config/goals.json`, **user-facing**), `core/goal_context.py` | `get_active_goals`, `get_stalled_goals`, `get_next_step`. `goal_context`/`[METAS]` federan **solo** `goal_setting` + `goal_tracker`; los del tool `goals` hoy son invisibles al prompt (ver §5.1/§5.8). |
| Escalada | `core/escalada.py` | 8 niveles × 12 dominios; `registrar_logro(dominio, logro, dificultad)`. |
| Loops | `main.py` | Hilos daemon: evolución (30 min), learning (cada 6 ticks), defensa (cada 9), auto-fábrica (30 min), tripulación (30 s), rutinas, auto-salud. |

**El catálogo de la Fábrica está perdido:** `memory/eris_fabrica.json` no existe,
aunque hay artefactos reales en `libraries/`, `actions/custom/` y
`skills/user_created/`. `fabrica action=listar` devuelve vacío. Esto se repara
(§7) porque el bucle necesita saber qué capacidades **ya** tiene para no
reconstruir lo que existe.

---

## 3. Decisiones tomadas con el dueño (no se revisan)

| Decisión | Elección | Razón |
|---|---|---|
| **Orden del trabajo** | Primero este bucle, después las tablas de crecimiento. | "realiza uno por uno primero el primer proyecto y despues el segundo". |
| **Qué es llegar** | El resultado tiene que **existir de verdad** y el dueño tiene que poder **verlo con sus ojos**. | "necesito ver con mis propios ojos que realizo, no quiero que haga trampa ni diga mentiras". |
| **Sin prueba no cuenta** | Toda meta cumplida exige evidencia verificable por un tercero (no su palabra). Sin evidencia = **no hecho**. | Ídem. |
| **Zona protegida** | Sistema operativo (paquetes, `/etc`, `/usr`, config de Omarchy), datos personales (navegador, claves, documentos, ubicación) y **la red de casa / IP**. Solo con OK explícito del dueño, cada vez. | "me daria miedo que modificara algo de aqui… que revelara mi ubicacion… la red de mi casa". |
| **Zona libre** | Su workspace, su lab aislado, crear/instalar cosas dentro de su entorno, investigar la web, fabricarse herramientas. Puede sola. | El dueño la quiere autónoma dentro de lo seguro. |
| **Privacidad** | Proteger la privacidad del **dueño** (no filtrar identidad/ubicación/red; discreción y limpieza de rastros) es un objetivo. Anonimato para **atacar terceros sin permiso** es non-goal; el pentest real queda en el lab `192.168.56.0/24`. | Línea legal y de seguridad. |
| **Su propio código** | Puede reparar/mejorar código **de Eris** dentro de `ERIS-NEW` con `mission`/`code_guard` (backup + validación + rollback). Tocar el **sistema operativo** es zona protegida. | El miedo del dueño era el SO ("algo de aquí"), no su propio proyecto. |
| **Trabajo ofensivo** | Solo en el lab aislado VirtualBox. | Igual que hoy (`pentest_lab`). |

---

## 4. Glosario

- **Meta / objetivo:** algo que se quiere lograr, con una condición de éxito
  observable. Vive en uno de los tres stores: `config/goals.json` (tool `goals`,
  user-facing), `memory/goals.json` (`goal_setting`, autónoma) o `data/goals.json`
  (`goal_tracker`, rica). El motor los lee a los tres.
- **Barrera:** razón concreta por la que Eris **no** está llegando a la meta.
- **Señal:** hecho observable que sugiere una barrera (ver §5.1).
- **Diagnóstico:** qué le falta y por qué, con la evidencia que lo sostiene.
- **Capacidad:** tool, librería, skill, script, API/servidor, permiso, dato o
  conocimiento. El bucle produce capacidades.
- **Evidencia:** artefacto externo verificable (archivo, exit code, test verde,
  endpoint que responde, imagen/video/página accesible). No es la afirmación de Eris.
- **Verificador:** quién/qué valida la evidencia: `mission.verify`, `test_all`,
  `truth_audit`, `TraceKeeper`, o un chequeo directo (existencia/ejecución/HTTP).
- **Zona:** protegida (pide OK) o libre (actúa sola).

---

## 5. El bucle de superación de barreras

Módulo nuevo: **`core/barrier_engine.py`**. Tool pública: **`barreras`**.
Estado persistente: **`data/barreras.json`** (runtime, en `.gitignore`).

Máquina de estados de una barrera:

```
abierta → diagnosticada → planificada → [esperando_ok?] → creada → usada
        → verificada → resuelta
                         ↘ reintento (otro enfoque) → …
                         ↘ escalada (agotada)
                         ↘ abandonada (meta ya no aplica)
```

### 5.1 Detección (señales)

`scan()` recolecta señales de fuentes reales, sin inventar:

1. **mission** — `verify()` en rojo, o `close` con pasos sin resolver.
2. **Tripulación** — tarea en ERROR; o la misma tarea fue **re-encolada por
   `requeue_stuck_tasks()` más de una vez** para el mismo objetivo. (El
   `ProgressTracker` solo saca la foto de lo WORKING >120s; **no** cuenta
   repeticiones por objetivo — el motor lleva su propio contador.)
3. **Metas** — meta activa **estancada** (`goal_tracker.get_stalled_goals(días)`)
   o sin próximo paso accionable. Ojo: `goal_setting` no tiene subtareas ni
   "próximo paso", así que una meta suya **no** es barrera solo por no tener paso.
4. **Verdad** — `truth_audit` marca que una respuesta afirmó algo sin respaldo.
5. **Herramientas** — un `dispatch` devolvió error de *capacidad faltante*
   (`tool not found`, `ImportError`, `ModuleNotFoundError`, `command not found`).
6. **Autorreporte** — el propio LLM puede abrir una barrera con la tool
   (`barreras action=abrir`) cuando se oye decir "no puedo / no sé / me falta".

`scan()` **no actúa**: solo lista candidatas y crea/actualiza la barrera
(`abierta`). Actuar sin revisar sería el bucle infinito que evitamos (anti-goal).

### 5.2 Diagnóstico

Clasifica la barrera en **un tipo dominante** (uno solo, para no diluir):

| tipo | falta… | ruta típica de solución |
|---|---|---|
| `conocimiento` | saber cómo | `learning_engine` / `rag_engine` recall / investigar |
| `capacidad` | una función/tool/servicio | `fabrica.crear_tool`/`crear_libreria`/`crear_skill` |
| `dependencia` | un paquete/módulo | `autonomy.auto_install_package` |
| `acceso` | credencial o permiso de SO | **zona protegida → pide OK** |
| `recurso` | datos, hardware, tiempo, dinero | informar/esperar; o buscar alternativa |
| `meta` | la meta está mal definida o choca con otra | reformular con el dueño / `TaskSpecifier` |
| `externo` | un sistema de afuera no responde | reintento con espera; si falta el canal, es `capacidad` (crear cliente/script). **Ojo:** `ConnectorHub` despacha a `api_invoke`/`webhook_sender`, que **no existen** en el registry → no usar esa ruta. |

Salida: `{tipo, falta, porque, evidencia_del_diagnostico}`. Usa heurística +
LLM (`model_router.quick_chat`) y cita lo que miró (log, error, archivo).

### 5.3 Decisión (pensar antes de actuar)

Arma un **plan corto** (≤5 pasos) y lo pasa por el **árbitro de riesgo**
existente (`permission_gate.assess_risk` / `guard_check`):

- Si **ningún** paso toca zona protegida ni pide un riesgo alto →
  `planificada`, sigue sola.
- Si algún paso toca zona protegida o el Custodio lo bloquea →
  `esperando_ok`: se detiene **ahí**, avisa al dueño (voz/UI) con el plan y el
  por qué, y no lo ejecuta hasta el OK. Los **bloqueos duros no se degradan a
  "ask"** (regla de F5b): directamente se escala.
- Guarda el plan y la decisión en la barrera (para auditoría y para `escalada`).

Cuando hay ≥2 enfoques, los compara con el LLM (`model_router.quick_chat`).
**No** se usa `DecisionArbiter`: es un stub que llena todo con `~0.5` sin evaluar
(`core/sub_agent_crew.py:1172-1177`).

**Camino de ejecución obligatorio.** El motor **no** usa el dispatcher del chat
(`core/tool_dispatcher.py`, que solo pasa por `permission_gate`): todo paso
riesgoso sale por `core.tool_dispatch_api.dispatch_tool` (el mismo que usa la
tripulación), que sí consulta `guard_check`. Y hace su **propio pre-chequeo de
zona** (§6) *antes* de despachar: sin UI el gate es fail-closed y devuelve
**deny** para high/critical, no "ask"; el motor no puede depender de un "ask"
que en un tick de daemon nunca llega.

### 5.4 Creación (o reparación)

**Primero mira si ya la tiene** (inventario de la Fábrica, §7): si la capacidad
existe y funciona, la reutiliza; si existe y está **rota**, la repara; recién si
no existe, la crea. Construye por la ruta que corresponda:

- **tool** → `fabrica.crear_tool` (compila + smoke test `status`/acciones + rollback).
- **librería** → `fabrica.crear_libreria` (**solo compila**: el motor además
  ejecuta la función para probarla, porque la Fábrica no lo hace).
- **skill** → `fabrica.crear_skill` + `skill_manage validate` (la skill se
  **valida aparte**: `crear_skill` no valida nada).
- **reparación** de una capacidad propia que existe y falla → `mission`/`code_guard`
  (cambio mínimo, backup + validación + rollback). Aplica a código de Eris dentro
  de `ERIS-NEW`; el SO es zona protegida.
- **script** → escribe en su workspace y lo prueba.
- **API / servidor local** → **`core/server_forge.py`** (nuevo, ver §8).
- **dependencia** → `autonomy.auto_install_package` (dentro del venv).
- **conocimiento** → `learning_engine` (investigar→estudiar→cristalizar).

Regla: **una capacidad no se da por creada hasta que un test propio pasa.** Como
la validación de la Fábrica es desigual (solo `crear_tool` hace smoke test), el
motor agrega su propia prueba para librerías y skills. Se registra
`{capacidad, tipo, path, como_se_creo, creada_vs_reutilizada}` en la barrera.
**Antes de crear, mira el inventario (§7): no reconstruye lo que ya tiene.**

### 5.5 Uso

Eris usa la capacidad recién creada para atacar la meta:

- si es tool/librería/skill → la invoca (dispatch directo);
- si es una tarea mayor → la delega con `MissionPlanner.proyectar` /
  `dispatch_to_sub_agent`, arrastrando el `goal_id` (herencia de F5a);
- captura **el resultado crudo** (no su resumen): salida de la tool, exit code,
  contenido del archivo.

### 5.6 Verificación con evidencia (regla dura)

**Ninguna barrera se marca `resuelta` sin evidencia verificable e independiente
de la palabra de Eris.** El verificador es uno o más de:

- existencia y tamaño de un archivo real (con ruta),
- `py_compile` / `mission.verify` / `test_all` en verde,
- exit code 0 + salida real de un comando,
- `GET /health` de un API/servidor propio responde 200,
- artefacto imaginable/visible por el dueño (imagen, video, página) y su ruta.

Si la evidencia **no** aparece:

- si Eris **afirmó** éxito → se marca `falso_positivo` (cuenta como fallo, se
  registra la mentira) y **vuelve al diagnóstico con otro enfoque**;
- si fue un fallo honesto → vuelve al diagnóstico con otro enfoque.

La evidencia se guarda en la barrera y en una **traza replayable**
(`TraceKeeper` → `data/agent_traces/`).

**Que el dueño lo vea.** El cierre deja además una nota legible (chat/UI + Obsidian
`Proyectos/barreras/`) con: la meta, qué faltaba, qué creó/reutilizó, la evidencia
y **la ruta concreta para abrirla**. Para resultados intangibles (una skill, una
lección, un servidor interno) la evidencia es su archivo/SKILL.md y su `health`, y
la nota explica cómo comprobarlo. Un resultado sin ruta abrible no cuenta como
"visible".

**Retención.** La barrera y su evidencia quedan (auditoría interna);
`data/barreras.json` y `data/agent_traces/` son runtime → `.gitignore`. La
"limpieza de rastros" (§3) aplica a lo que sale a la web (outbound), **no** a la
auditoría interna.

### 5.7 Reintento y escalada (frenos)

Por barrera hay un **presupuesto** (valores a confirmar en §12, propuesta):

- **máx. 3 enfoques distintos** (no 3 intentos iguales: cada uno debe cambiar de
  ruta — otra capacidad, otro método, otra fuente);
- **máx. 1 capacidad nueva por enfoque**;
- **tope diario de capacidades nuevas** (reutiliza el patrón de tope diario de
  `auto_fabrica`);
- **presupuesto de tiempo** por barrera.

Al agotarlo → **`escalada`**: un informe claro para el dueño (meta, qué intentó,
qué descubrió, qué necesita, evidencia y por qué no pudo), y **se detiene**. No
hay bucle infinito.

### 5.8 Cierre

- `resuelta` → actualiza la meta **en el store del que salió** (los tres: `goals`,
  `goal_setting`, `goal_tracker`), registra el logro en `escalada.registrar_logro`
  (dominio según la meta), deja novedad en `todo_yo` y archiva la barrera.
- `abandonada` → la meta dejó de aplicar; se documenta el motivo.

---

## 6. Zonas y frenos (seguridad)

Hoy el árbitro clasifica por **tool/comando** (heurísticas de `permission_gate`) y
su único override declarativo, `config/tool_risk.json`, **está vacío**. Nada
traduce "datos personales" ni "red de casa" a una regla. Y hay **dos caminos**:
el chat (`tool_dispatcher`) solo pasa por `permission_gate`; `guard_check` corre
solo en `tool_dispatch_api.dispatch_tool`. Por eso el motor hace dos cosas:

**(A) Pre-chequeo de zona propio, antes de despachar.** Una política nueva
`config/zone_policy.json` (creada por el diseño, editable por el dueño) define
patrones → zona. Valores por defecto propuestos:

- **Sistema operativo (protegida):** `/etc`, `/usr`, `/boot`, `/var/lib`, gestores
  de paquetes (`pacman`/`apt`/`dnf`), `systemctl`/`sysctl`, `sudo`, `mkfs`,
  `fdisk`, particiones, bootloader.
- **Datos personales (protegida):** `~/.ssh`, `~/.gnupg`, `~/.mozilla`,
  `~/.config/*/Cookies|Login Data`, `~/.local/share/keyrings`, `~/.password-store`,
  documentos, historiales, `~/.bash_history`.
- **Red de casa (protegida):** publicar IP/hostname/SSID, bind a interfaces
  no-loopback, UPnP, abrir puertos, tocar el router.
- **Su propio proyecto (libre):** `ERIS-NEW/`, su workspace, `libraries/`,
  `actions/custom/`, `skills/user_created/`, `data/`, su lab `192.168.56.0/24`.

Esta política se registra además en el override central (`config/tool_risk.json`)
para que **todo** camino que pase por `guard_check` la respete, no solo el motor.

**Reglas duras:**

1. **Zona protegida → siempre pide OK** (estado `esperando_ok`), aunque el plan
   parezca inocuo.
2. **Bloqueo duro del Custodio → no se ejecuta ni se "pregunta"**: se escala.
3. **Sin evidencia no hay éxito.**
4. **Presupuesto agotado → escala y para.**
5. Nada escucha en `0.0.0.0` ni sale a la LAN sin OK: los servidores propios van
   en `127.0.0.1` por defecto.

> Pendiente del dueño: confirmar la lista de zona protegida (¿el home entero?
> ¿alguna carpeta concreta?) — ver §12.

---

## 7. Reconstruir el catálogo de la Fábrica

Nueva acción `fabrica action=reconciliar` (no destructiva):

- **Escanea artefactos reales:** `libraries/eris_*.py`, `actions/custom/*.py`
  (+ entradas reales en `actions/custom_tools.json`), `skills/user_created/*/SKILL.md`,
  y `memory/eris_fabrica_backups/*` (versiones huérfanas).
- **Reconstruye el inventario** con el esquema que `eris_fabrica._load_state`
  ya espera: `{"items": [{"name","type","path","purpose","functions","created"}],
  "created_at","updated_at"}`.
- **Reporta desajustes** en las dos direcciones: artefacto que existe pero no está
  en el inventario, e inventario que lista algo que ya no está.
- **No borra nada.** Si hay dudas, deja el ítem marcado y lo informa.
- Criterio de aceptación: `fabrica action=listar` muestra al menos la librería
  real `eris_metasploitable` (`libraries/eris_metasploitable.py`) y las tools/skills
  reales; y `usar_libreria` sobre una reconstruida funciona.

Esto le da al bucle el inventario para **no reconstruir lo que ya tiene**.

---

## 8. Crear y levantar APIs / servidores (capacidad nueva)

Módulo nuevo: **`core/server_forge.py`**. Tool: **`server_forge`**.

- Crea un servidor HTTP chico (stdlib `http.server`/`socketserver`, siguiendo el
  patrón de `core/vrm_server.py` y `core/opencode_bridge.py`) o un script de
  servicio a partir de una especificación simple (rutas + handler).
- **Escucha en `127.0.0.1` por defecto.** Escuchar en otra interfaz = zona
  protegida → pide OK.
- Registro propio `data/servers.json` (runtime, gitignore): `{name, port, path,
  pid, health, created}`.
- Ciclo de vida: `crear / levantar / estado / parar / borrar`; con `health`
  (`GET /health` → 200) como **evidencia** para el bucle (§5.6).
- Para **consumir** APIs externas se usa lo que ya exista (web/`ConnectorHub`
  donde funcione); si falta el canal, el diagnóstico lo trata como `capacidad`.
  Esto en cambio es para **exponer** algo propio (que el bucle use o que el dueño
  consulte).

---

## 9. Interfaces concretas (nombres que el builder puede usar)

- `core/barrier_engine.py`
  - `abrir(goal_id, titulo, descripcion, origen) -> dict`
  - `scan() -> list[dict]` (señales → candidatas)
  - `diagnosticar(barrier_id) -> dict`
  - `planificar(barrier_id) -> dict`
  - `crear(barrier_id) -> dict`
  - `usar(barrier_id) -> dict`
  - `verificar(barrier_id) -> dict`
  - `bucle(barrier_id) -> dict` (corre el ciclo con presupuesto)
  - `escalar(barrier_id, motivo) -> dict` / `cerrar(barrier_id, estado) -> dict`
  - `estado() -> dict` / `listar() -> list`
  - `barrier_tool(parameters, player) -> str` (tool `barreras`)
- Estado: `data/barreras.json` (gitignore).
- Seguridad: `config/zone_policy.json` (nueva, editble por el dueño) + registro de
  sus patrones en `config/tool_risk.json`.
- Reutiliza: `fabrica`, `learning_engine`, `autonomy`, `permission_gate`,
  `truth_audit`, `goal_tracker`, `mission_agent.verify`, `server_forge`,
  `escalada`, `todo_yo`, `TraceKeeper`.

---

## 10. Fases (una fase = un commit local)

Cada fase termina con: `test_all.py` 177/0/3, sync de tools verificada, y (si
aplica) Eris arranca sin crash.

1. **F1 — Andamiaje y detección.** `core/barrier_engine.py` con el estado,
   `scan()`, `abrir/listar/estado`, tool `barreras`, `data/barreras.json` en
   `.gitignore`. No crea nada todavía.
2. **F2 — Reconstruir el catálogo.** `fabrica action=reconciliar` (§7).
3. **F3 — Diagnóstico, decisión y zonas.** Clasificación + plan + `config/zone_policy.json`
   + pre-chequeo de zona + registro en `config/tool_risk.json` (guardar `esperando_ok`).
4. **F4 — Creación y uso.** Rutas de `fabrica` + `server_forge` (§8).
5. **F5 — Verificación y frenos.** Evidencia dura, `falso_positivo`, reintento con
   otro enfoque, presupuesto y escalada.
6. **F6 — Wiring y cierre.** Tick en `main.py` + hooks (mission/tripulación/metas);
   cierre con `goal_tracker`/`escalada`/`todo_yo`.

---

## 11. Fuera de alcance (lo decide el builder)

- Cuántos minutos entre ticks y con qué se dispara cada hook.
- Formato exacto del informe de escalada (texto/JSON/Obsidian).
- Cómo detecta el LLM el "no puedo" con la menor tasa de falsos positivos.
- Reutilizar `barrier_engine` también para las "tablas de crecimiento" (Proyecto 2)
  — probable, pero se decide cuando lleguemos.

## 12. Decisiones que necesito del dueño

1. **Zona protegida — confirmar la lista.** Propuse: sistema operativo, datos
   personales (`~/.ssh`, `~/.gnupg`, navegador, llaveros, historial) y red de casa.
   ¿El **home entero** queda protegido, o solo esas partes sensibles (y el resto es
   zona libre)?
2. **Presupuesto.** ¿Te cierra **3 enfoques** por barrera, **1 capacidad nueva por
   enfoque** y un **tope diario** de ~3? ¿O querés otro número?
3. **Reparar su propio código.** ¿Puede reparar/mejorar el código de Eris dentro de
   `ERIS-NEW` sola (con backup + validación + rollback), o preferís aprobar vos
   cada cambio de su propio código?

**Defaults que ya tomé** (decime si alguno no te gusta): cuando necesita tu OK, te
avisa y **sigue con otra cosa** (no queda en pausa); puede **auto-generarse metas**
para practicar (como ya hace `goal_setting`); y cada resultado deja una **nota
visible** en Obsidian además de la evidencia.
