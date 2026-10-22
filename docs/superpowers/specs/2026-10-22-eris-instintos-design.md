# Eris: instintos con confianza (Fase B)

- **Fecha:** 2026-10-22
- **Proyecto:** `/home/soul/ERIS-NEW`
- **Origen:** pieza `continuous-learning-v2` de ECC (MIT), adaptada — no copiada.
- **Estado:** propuesto. No se implementa hasta que el dueño apruebe este documento.

> **Recon (hecho, no supuesto).**
> - Eris **no** tiene concepto de instinto: 0 ocurrencias en el código.
> - `memory/auto_corrections.json` **no existe**; `lessons_learned.json` solo
>   guarda errores de tools (`module`, `error`, `solution`), no correcciones
>   del usuario.
> - `main.py:_remember()` recibe **todo** el texto de la conversación, con el
>   prefijo `Usuario: ` para lo que escribe/habla el dueño. Es el punto natural
>   para observar correcciones, tanto en texto como en Live.
> - `core/context_builder.py:build_system_prompt(host)` **intenta** inyectar
>   lecciones y correcciones, pero hoy ese bloque está muerto: lee
>   `memory/learned_lessons.json` y `memory/auto_corrections.json`, mientras el
>   archivo poblado es `memory/lessons_learned.json` (nombre invertido). El
>   bloque de instintos va ahí, independiente, sin depender de ese bug.
> - `data/command_deck.json`: 60 items con `tool, args, status, result, ts,
>   ts_end`. Hay fallos reales seguidos de éxitos reales (ej. dotnet build).
> - `test_all.py` es un script propio (no pytest); los tests nuevos van en
>   `tests/test_instincts.py` y se corren aparte. El baseline 177/0/3 no se toca.

---

## 1. Intención y por qué

Eris aprende lecciones sueltas, pero no tiene **reglas atómicas que suban de
confianza al repetirse**. El objetivo es que una corrección del dueño
("no declares listo sin build/test/curl") se grabe como instinto con confianza
baja, se refuerce cada vez que la situación se repite, y termine inyectándose
en el prompt como una regla estable. Lo mismo con los patrones que se pueden
minar del deck (fallo → arreglo → éxito).

Esto ataca su vicio principal: **declarar sin verificar**. Un instinto no es
una lección narrativa: es un par trigger→acción con evidencia y un número.

## 2. Qué es un instinto

Un archivo YAML con una lista de instintos. Esquema de cada uno:

```yaml
id: inst_20261022_a1b2c3
trigger: "cuando se termine una misión de código"
action: "correr build + tests y pegar la salida real antes de decir listo"
confidence: 0.7          # 0.1 .. 0.9
hits: 4                  # confirmaciones independientes
misses: 0                # contradicciones
mature: false            # true si conf >= 0.8 y hits >= 5
scope: project           # global | project
project: api_vuelos_cs-a1b2c3  # slug; null si scope=global
status: active           # active | retired
source: correction       # correction | deck | manual
created: "2026-10-22T10:30:00"
updated: "2026-10-22T11:02:00"
last_seen: "2026-10-22T11:02:00"
evidence:                # máximo 10, con secretos redactados
  - ts: "2026-10-22T10:30:00"
    kind: correction
    ref: "chat"
    note: "no declares listo sin probar"
```

- `confidence` se muestra siempre con un decimal (`0.7`).
- `trigger` y `action` se recortan a 240 caracteres.
- La evidencia **no** se inyecta en el prompt (solo se guarda para auditoría).

## 3. Dónde vive

```
memory/instincts/
├── global.yaml                 # instintos globales
├── projects/
│   └── api_vuelos_cs-a1b2c3.yaml
├── instincts.log               # errores y minados (nunca rompe un turno)
└── .mine_stamp                 # última vez que corrió el minado
```

- `ERIS_INSTINCTS_DIR` permite redirigir todo a un `tmp_path` en tests.
- Escritura **atómica**: `.tmp` + `os.replace`, con lock de archivo y
  `threading.RLock`. El lock es **portable**: `fcntl.flock` en Linux/macOS;
  `msvcrt.locking` en Windows; si ninguno está disponible, queda el lock de
  proceso (suficiente para Eris, que corre en un solo proceso). El módulo
  **importa en Windows y Linux** sin `ImportError`.
- Si un YAML está corrupto: se renombra a `.corrupt-<ts>` y se arranca vacío.
  Nunca se pierde el archivo original sin backup.
- **Slug de proyecto**: `<basename del git root>-<sha1(abs_path)[:6]>`; si no
  hay git, `<basename del cwd>-<sha1>`. Ejemplo: `api_vuelos_cs-a1b2c3`.
- **Normalización de `project`** (una sola función, usada por la API y el CLI):
  - `None` → global.
  - un **path existente** → se calcula su slug;
  - un string con forma de slug (`nombre-6hex`) → se usa tal cual;
  - un nombre suelto que existe como carpeta bajo el cwd → se calcula su slug;
  - cualquier otra cosa → error explícito (no se inventa un slug).
- Detección del proyecto actual, en orden: argumento explícito → último `cd`
  del deck → `host._shared` (si expone proyecto) → `None` (solo global).

## 4. Ciclo de confianza

| Evento | Efecto |
|---|---|
| Corrección del usuario | crea con `0.3` (o refuerza si es similar) |
| Patrón minado del deck (≥2 casos) | crea con `0.4` |
| Alta manual | crea con `0.5` |
| Confirmación independiente | `+0.10`, tope `0.9`, `hits += 1` |
| Evidencia duplicada exacta | no suma (mismo `kind + ref`) |
| Contradicción | `-0.15`, piso `0.1`, `misses += 1` |
| `confidence < 0.2` o `misses >= 2` | `status: retired` (no se inyecta) |
| `confidence >= 0.8` y `hits >= 5` | `mature: true` (sigue inyectándose) |

**Qué es una confirmación independiente.** En v1 hay tres fuentes:

1. **Otra corrección similar** del usuario (Jaccard o contención ≥ 0.6;
   para correcciones vale contra trigger+acción o solo la acción, porque el
   trigger embebe la última respuesta).
   Cada turno distinto cuenta: el `ref` es `chat:<timestamp>`, así que repetir
   la misma frase en otro turno **sí** refuerza; repetirla en el mismo turno no.
2. **Otro caso del deck** que matchea un instinto ya minado (misma familia,
   otra entrada): `ref` es `deck:<ts>`, y solo cuenta si ese `ts` es nuevo.
3. **`reinforce` manual** por CLI.

Con esto, una corrección nace en `0.3`, con dos repeticiones más llega a `0.5`
y empieza a inyectarse. No se sube por “una vez que salió bien”: eso sería
evidencia débil y no es observable sin ambigüedad en v1.

Sin decaimiento por tiempo en v1: un instinto solo baja por contradicción
explícita. Se guarda `last_seen` para poder agregarlo después sin migrar datos.

**Deduplicación:** si el nuevo trigger+acción tiene Jaccard (o contención)
≥ 0.6 contra uno existente del mismo scope, no se crea otro: se refuerza el
existente. Los patrones minados del deck llevan además una `dedup_key` exacta
(`deck:<proyecto>:<tool>:<familia>`) para no fusionar familias distintas que
comparten path y plantilla de acción (p. ej. `dotnet` vs `pytest`).

## 5. Alimentación

### 5.1 Correcciones del usuario (automático)

En `main.py:_remember()`, si el texto empieza con `Usuario: `, se llama a
`core.instincts.observe_user_message(texto, last_response=<última línea ERIS>,
project=<detectado>)`, dentro de `try/except`.

Se considera corrección solo si pasa **todas** estas reglas (para no convertir
charla normal en instintos):

1. El texto (sin `Usuario: `) tiene **≥ 12 caracteres**.
2. No está en la lista de cortesías: `no, gracias`, `no, está bien`,
   `no hace falta`, `no te preocupes`, `no, tranquila`, `no pasa nada`.
3. Y cumple **una** de estas:
   - contiene una señal fuerte: `no es así`, `está mal`, `esta mal`,
     `te equivocaste`, `no era eso`, `no declares`, `sin probar`,
     `no inventes`, `corregí`, `corregi`, `mal ahí`, `no funciona así`; o
   - empieza con `no,` **y** contiene `sino`, `tenés que`, `debes`, `deberías`,
     `en vez de`, `lo que pedí`, `en realidad`.

La comparación normaliza mayúsculas y acentos (para que `está`/`esta` y
`corregí`/`corregi` matcheen), pero no usa substring suelto de `no` ni de
`en realidad`: siempre hay contexto de corrección.

- `trigger`: si hay una frase después de "sino"/"en vez de"/"tenés que", se usa
  esa; si no, `"cuando el usuario corrija algo como: <última respuesta ERIS>"`.
  La última respuesta ERIS se obtiene recorriendo `_convo_ctx` hacia atrás
  hasta la primera entrada que empiece con `ERIS: `.
- `action`: el texto de la corrección (máx. 240 chars), sin el saludo.
- `evidence`: `{kind: correction, note: "<texto>"}`.
- Si el mensaje no es corrección, no hace nada.
- Costo: lectura/escritura de un YAML chico; sin red, sin LLM, sin bloquear.

### 5.2 Deck (automático 1 vez/día + manual)

`mine_from_deck()` lee `data/command_deck.json` y detecta:

1. **Fallo → éxito**: un item `status=error` seguido (≤10 min, mismo tool,
   misma **familia de comando** y mismo proyecto) de un `status=done`.
2. **Familia de comandos repetida**: mismo (proyecto, tool, familia) aparece
   ≥3 veces con `status=done`.

**Cómo se extrae la familia.** `args` no es una línea de comandos: es
`_short_args()` (`k=v`, cada valor ≤60 chars, total ≤160). El algoritmo es:

1. Parsear `args` como pares `k=v` (separados por `, `); quedarse con `command`
   si existe; si no, usar el `tool` como familia.
2. Del comando, extraer el primer token reconocible de una lista blanca:
   `dotnet, npm, npx, pytest, python, pip, ruff, mypy, go, cargo, make, git,
   curl, bash, sh, node, docker`. Si no hay ninguno, usar el primer token no
   vacío después de `&&`/`;`.
3. Proyecto: buscar `cd <path>` en el comando; normalizar ese path a slug. Si
   no hay `cd`, el item es **global**. Cada patrón se atribuye al proyecto de
   **su propia entrada**, nunca al proyecto “actual” del minado.
4. Snippet para la acción: el valor de `command` (redactado, ≤160 chars). Si
   está truncado (`...`), se guarda igual: sirve como pista, no como comando
   ejecutable.

- Trigger del fallo→éxito: `"cuando <tool> <familia> falle en <proyecto>"`
  (o sin `en <proyecto>` si es global).
- Acción: `"revisar el error y reintentar con el comando que funcionó: <snippet>"`.
- Trigger de familia repetida: `"para <tool> <familia> en <proyecto>"`;
  acción: `"usar el comando que ya funcionó: <snippet>"`.
- Confianza inicial `0.4`; si ya existe un instinto equivalente, se refuerza
  con `ref=deck:<ts>` (solo una vez por entrada).

Reglas duras:

- Solo items de los últimos **30 días**.
- **Redacción de secretos** antes de guardar: `sk-…`, `AIza…`, `Bearer …`,
  `password=…`, `token=…` → `[REDACTED]`.
- Se guardan snippets de ≤160 chars; nada de volcar un comando entero.
- Dedup por Jaccard/contención (correcciones) o `dedup_key` exacta (deck); un
  patrón ya existente se refuerza, no se duplica.
- `--dry-run` no escribe nada y muestra los candidatos.

**Cuándo corre.** `mine_if_due()` se llama desde `_proactive_loop` (hilo que ya
duerme 60 s y corre durante toda la sesión), con un stamp de 24 h. **No** se
engancha al digest diario: ese solo se genera si falta el archivo del día y
puede no ejecutarse nunca con Eris abierta. `mine_if_due()` primero mira el
stamp (una lectura de archivo) y solo entonces lee el deck.

### 5.3 Manual (CLI)

```bash
.venv-linux/bin/python -m core.instincts add \
  --trigger "cuando se termine una misión de código" \
  --action "correr build + tests y pegar la salida real" \
  --scope project --project /home/soul/Documents/PYTHON/api_vuelos_cs \
  --confidence 0.5

.venv-linux/bin/python -m core.instincts list [--scope global|project] [--project X]
.venv-linux/bin/python -m core.instincts show <id>
.venv-linux/bin/python -m core.instincts reinforce <id> --note "se repitió"
.venv-linux/bin/python -m core.instincts contradict <id> --note "no aplica"
.venv-linux/bin/python -m core.instincts retire <id>
.venv-linux/bin/python -m core.instincts mine [--dry-run]
```

## 6. Inyección en el prompt

`instinct_block(project=None, user_text="", limit=5) -> str`:

- Filtra `status=active`, `confidence >= 0.5`, y scope global o proyecto actual.
- Score: `confidence + 0.2 * match_de_palabras + 0.1 * recencia`. El match de
  palabras es **best-effort**: si el texto actual no está disponible (en el
  arranque, `_convo_ctx[-1]` suele ser una línea `ERIS:`), simplemente no suma
  y se ordena por confianza/recencia.
- Devuelve como máximo **5** líneas y **700 caracteres** en total:

```
[INSTINTOS APRENDIDOS]
- (0.8) Cuando se termine una misión de código → correr build + tests y pegar la salida real.
- (0.6) Para shell_session dotnet → usar el comando que ya funcionó.
```

- Si no hay nada, devuelve `""`.
- `user_text` sale de `host._convo_ctx[-1]` **solo si** empieza con `Usuario: `;
  si no, se pasa `""`.
- Se inyecta en `core/context_builder.py` **después** del bloque de lecciones y
  correcciones, dentro de `try/except`: si el módulo falla, el prompt sigue
  exactamente igual que hoy.
- No se inyecta evidencia ni IDs: solo trigger→acción y confianza.

**Limitación conocida (v1).** El system prompt se arma al conectar la sesión
Live (`_build_config`), no en cada turno. Un instinto aprendido durante una
sesión se aplica en la **próxima conexión/arranque**, igual que hoy pasa con
las lecciones. No se agrega un refresh por turno para no tocar el pipeline Live.

## 7. API del módulo (`core/instincts.py`)

```python
add_instinct(trigger, action, scope="global", project=None,
             confidence=0.5, evidence=None, source="manual") -> dict
observe_user_message(text, last_response="", project=None) -> dict | None
reinforce(instinct_id, note="", kind="manual", ref="") -> dict
contradict(instinct_id, note="", kind="manual", ref="") -> dict
retire(instinct_id, reason="") -> dict
list_instincts(scope=None, project=None, include_retired=False) -> list[dict]
instinct_block(project=None, user_text="", limit=5) -> str
mine_from_deck(deck_path=None, dry_run=False, now=None) -> list[dict]
mine_if_due(now=None) -> int
project_slug(path) -> str
set_store_dir(path) -> None        # solo tests
```

Todas las funciones públicas: nunca lanzan hacia afuera; devuelven `None`/`""`/
`[]` y loguean en `instincts.log`.

## 8. Integración exacta

| Archivo | Cambio | Riesgo |
|---|---|---|
| `core/instincts.py` | módulo nuevo (~350 líneas) | nulo (no se importa hasta el paso 2) |
| `tests/test_instincts.py` | tests nuevos, herméticos | nulo |
| `core/context_builder.py` | +8 líneas: bloque `[INSTINTOS]` con `try/except` | bajo, aislado |
| `main.py:_remember()` | +5 líneas: observar `Usuario: ` con `try/except` | bajo, no bloquea |
| `main.py:_proactive_loop` | +3 líneas: `mine_if_due()` (stamp 24 h) | bajo, hilo existente |

No se toca: personalidad, prompts de identidad, pipeline de audio, tools (no se
agrega una tool nueva), `command_deck`, `learning_engine.py`, `skills/`.

Aclaración: `_remember()` es un método de la clase `ErisLive`, así que el hook
**vive dentro del archivo de Live**, pero no toca la personalidad ni el audio:
solo observa el texto que ya se estaba guardando. Es una línea guarded.

**Hallazgo del revisor (pre-existente, fuera de alcance).** `context_builder`
intenta leer `memory/learned_lessons.json` y `memory/auto_corrections.json`,
pero el archivo poblado se llama `memory/lessons_learned.json` (nombre
invertido) y tiene otro esquema. Ese bloque hoy está efectivamente muerto. No
se arregla en esta fase; el bloque de instintos es independiente y no depende
de él. Se deja anotado para una fase posterior.

## 9. Tests (`tests/test_instincts.py`)

Herméticos, con `tmp_path` + `ERIS_INSTINCTS_DIR`; sin red ni subprocess.

1. `add` valida trigger/acción, clampea confianza, genera ID único y crea YAML.
2. `reinforce` suma 0.1, tope 0.9, `hits += 1`; evidencia con el mismo
   `kind+ref` no suma; con otro `ref` (otro turno) sí.
3. `contradict` resta 0.15, piso 0.1; retira con `<0.2` o `misses >= 2`.
4. Scope: global se ve en todos lados; proyecto solo en su slug.
5. `project_slug` + normalización: path existente → slug estable; slug → igual;
   nombre suelto inexistente → error; `None` → global.
6. `instinct_block`: filtra por confianza/scope, ordena, limita a 5, cap 700;
   sin datos devuelve `""`; no repite trigger/acción; sin `user_text` igual
   funciona.
7. `observe_user_message`: crea con una corrección real ("no declares listo sin
   probar"), **ignora** "no, gracias" y charla normal, refuerza una corrección
   similar en otro turno, no crea desde una línea `ERIS:`.
8. `mine_from_deck`: parsea `args` con `command=`, extrae familia (`dotnet`,
   `pytest`, etc.), detecta fallo→éxito y familia repetida, atribuye el scope
   al proyecto del `cd`, deduplica, redacta `sk-...`/`AIza...`; `dry_run` no
   escribe.
9. YAML corrupto: backup `.corrupt-*`, arranque vacío, sin excepción.
10. `mine_if_due`: respeta 24 h; la segunda llamada devuelve 0; no lee el deck
    si el stamp está vigente.
11. `context_builder`: con `instinct_block` monkeypatcheado, el bloque aparece;
    si lanza, el prompt se arma igual (no rompe el turno).
12. Import y lock: el módulo importa sin `fcntl` (simulando Windows con
    `monkeypatch`), y la escritura funciona con el fallback de proceso.
13. Sin efectos colaterales: `add` no toca `lessons_learned.json` ni el deck.

## 10. No-goals

- No agregar una tool nueva (hoy el registry está en 514/514; no se toca).
- No tocar la personalidad, el pipeline de audio ni la estética.
- No hacer inyección por turno en v1: se aplica al conectar/reconectar.
- No instalar Ollama ni dependencias nuevas (PyYAML ya está, 6.0.3).
- No reemplazar `learning_engine`, `lessons_learned` ni `auto_corrections`.
- No sincronizar instintos a la nube ni entre máquinas.
- No usar embeddings en v1: matching por tokens/Jaccard.
- No UI nueva.

## 11. Anti-goals (qué haría fracasar esto aunque "funcione")

- Inflar el prompt con 20 instintos → tope duro 5 / 700 chars.
- Crear instintos con un solo evento → confianza inicial baja y evidencia.
- Guardar secretos del deck en YAML → redacción obligatoria.
- Romper un turno si el módulo falla → todo `try/except`, nunca lanza.
- Instintos que contradicen la evidencia → la evidencia se guarda y se puede
  auditar; el usuario puede retirarlos con el CLI.

## 12. Decisiones que tomé yo (revisables)

1. **Inyección siempre activa**, cap 5 y conf ≥ 0.5, al conectar/reconectar
   (no por turno). Es lo que cambia el comportamiento; si no, el motor no sirve.
2. **Captura automática de correcciones** en `_remember`, con reglas estrictas
   para no convertir "no, gracias" en instinto.
3. **Minado del deck 1 vez/día** desde `_proactive_loop` (stamp de 24 h), no en
   el digest (que puede no correr) ni en cada arranque.
4. **Confianza 0.3–0.9**, sin decaimiento por tiempo en v1; una corrección
   repetida en turnos distintos refuerza.
5. **YAML por scope** (`global.yaml` + un archivo por proyecto), no un JSON
   monolítico: se revisa y se borra fácil.
6. **Slug de proyecto** con hash corto del path absoluto; el CLI acepta path o
   slug, y rechaza nombres ambiguos en vez de inventar.
7. **Los patrones minados se atribuyen al proyecto de su propia entrada del
   deck** (por el `cd`), no al proyecto actual; si no hay `cd`, son globales.

## 13. Verificación (evidencia que se va a mostrar)

```bash
# 1. Tests nuevos
.venv-linux/bin/python -m pytest -q tests/test_instincts.py

# 2. Suite completa intacta
.venv-linux/bin/python test_all.py | tail -8     # 177 PASS / 0 FAIL / 3 WARN

# 3. Demo real con store temporal (no contamina memoria/)
ERIS_INSTINCTS_DIR=/tmp/opencode/instincts-demo \
  .venv-linux/bin/python -m core.instincts add ... && ... list && ... reinforce

# 4. Minado real del deck, primero en seco
.venv-linux/bin/python -m core.instincts mine --dry-run

# 5. Inyección real
ERIS_INSTINCTS_DIR=/tmp/opencode/instincts-demo \
  .venv-linux/bin/python -c "from core.instincts import instinct_block; print(instinct_block())"
```

## 14. Plan de implementación

1. `core/instincts.py` + `tests/test_instincts.py`; correr pytest.
2. Inyección en `context_builder`; test de aislamiento.
3. Hook de correcciones en `_remember`; test con texto real.
4. Minado + `mine_if_due` + hook en `_proactive_loop`; `--dry-run` sobre el
   deck real.
5. Verificación completa y reporte con salidas exactas.

Cada paso es aditivo y reversible; si algo no gusta, se borra el módulo, los
tests y las 3 líneas de integración.

## 15. Limitaciones conocidas de v1 (explícitas)

- Los instintos nuevos se aplican en la **próxima conexión/arranque**, no en el
  turno siguiente.
- La detección de correcciones es heurística (reglas, no un LLM): puede dejar
  pasar una corrección muy indirecta y, si eso pasa, se corrige con el CLI o en
  una v2.
- El minado del deck no reconstruye comandos truncados: guarda la pista tal
  cual vino.
- Sin decaimiento temporal, sin embeddings y sin UI.
- Si el dueño corrige un instinto, se usa `contradict`/`retire`; no hay edición
  interactiva todavía.
