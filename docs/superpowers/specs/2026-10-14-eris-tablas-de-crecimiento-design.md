# Diseño — Proyecto 2: Tablas de Crecimiento de ERIS

Fecha: 2026-10-14
Estado: aprobado por el dueño ("sigue")
Proyecto 1 (motor de barreras): `docs/superpowers/specs/2026-10-14-eris-superacion-de-barreras-design.md`

---

## 1. Intención y por qué

El dueño quiere **abrir y ver con sus propios ojos** cómo creció Eris: qué
aprendió, en qué dominio, en qué nivel, **cuándo** y con **qué evidencia**.

Hoy `escalada` ya registra logros (12 dominios × 8 niveles) pero:

- no hay una **tabla** legible; son listas sueltas;
- la espeja en `Ciberseguridad/Escalada-<dominio>.md` (carpeta equivocada);
- **no guarda evidencia** por logro (no se puede comprobar);
- no se alimenta sola del motor de barreras (Proyecto 1), que sí produce
  evidencia dura (archivo, test, `/health`, ejecución real).

**Resultado:** un módulo `core/crecimiento.py` que arma y mantiene **tablas de
crecimiento** por dominio (y una **tabla maestra**), en Obsidian, con evidencia
y fecha por fila, actualizadas automáticamente. Reutiliza lo que existe (no crea
un sistema paralelo a `escalada`).

## 2. Éxito / no-éxito

- **Éxito:** el dueño abre `Crecimiento/Tabla-Maestra.md` (o `Tabla-<dominio>.md`)
  y ve una tabla real con nivel, logros, fechas y **rutas de evidencia que puede
  abrir**. Cada fila nace de un hecho verificable, no de la palabra de Eris.
- **No-éxito:** una fila sin evidencia ni fecha; una tabla que se desincroniza
  de `escalada`/barreras; otro store que duplique la verdad.

## 3. Fuentes de verdad (no se duplican)

| Fuente | Qué aporta | Evidencia |
|---|---|---|
| `escalada` (`memory/escalada.json`) | el logro y el **nivel** en un dominio | su nota `Escalada-<dominio>.md` |
| `barrier_engine` (`data/barreras.json`) | capacidad creada por una barrera resuelta | **evidencia dura** de la barrera + ruta del artefacto |
| `festejos` (opcional) | primicias/hitos | su entrada |

`crecimiento` es una **vista** (tabla) + un caché estructurado de filas; la
verdad de los logros sigue en `escalada`/barreras.

## 4. Modelo (`memory/crecimiento.json`, runtime)

```json
{
  "created": "ISO",
  "dominios": {
    "codigo": {
      "nivel": 3,
      "actualizado": "ISO",
      "filas": [
        {"fecha":"ISO","nivel":3,"logro":"...","evidencia":"test verde ...",
         "fuente":"barrier|escalada|manual","ruta":"/abs/path","estado":"verificada"}
      ]
    }
  },
  "stats": {"dominios_activos":0,"filas_totales":0,"con_evidencia":0}
}
```

Regla: una fila **sin evidencia y sin ruta** se marca `estado:"sin_evidencia"`
(visible, no oculta) — nunca se disfraza de logro comprobado.

## 5. Las 4 capas (mismo patrón que `pentest_learning`/`recetario`)

1. `memory/crecimiento.json` (estructurado).
2. Obsidian: `Crecimiento/Tabla-<dominio>.md` (una por dominio) +
   `Crecimiento/Tabla-Maestra.md` (12 filas: dominio, nivel, logros, última
   evidencia, ruta).
3. índice en `rag_engine` (`reindexar`, best-effort).
4. novedad en `todo_yo`.

Nada fuera del vault del dueño se toca (zona protegida intacta).

## 6. Tool `crecimiento`

| action | params | hace |
|---|---|---|
| `estado` (default) | — | resumen de la tabla maestra + ruta para abrir |
| `maestra` | — | (re)genera y devuelve la ruta de `Tabla-Maestra.md` |
| `tabla` | `dominio` | (re)genera y devuelve la ruta de `Tabla-<dominio>.md` |
| `dominio` | `dominio` | tabla en texto (para el chat) |
| `registrar` | `dominio`, `logro`, `evidencia`, `ruta`, `dificultad` | agrega una fila (y espeja el nivel en `escalada` si corresponde) |
| `actualizar` | — | reconstruye las filas desde `escalada` + barreras resueltas |
| `ruta` | `dominio` (opcional) | devuelve la ruta concreta a abrir |

Alta de tool: `core/tool_registry.py` **y** `core/tool_declarations.py`
(sync sagrada; pasará de 512 a 513).

## 7. Wiring

- `barrier_engine.cerrar("resuelta")` → `crecimiento.registrar(...)` con la
  evidencia y la ruta del artefacto (la fila más fuerte: evidencia dura).
- `escalada.registrar_logro` sigue siendo la fuente de nivel; `crecimiento`
  la lee en `actualizar` (sin acoplarse rígido).
- `main.py`: hilo diario que llama `crecimiento.actualizar()` + `reindexar`.

## 8. Fases

1. **P2-F1** — `core/crecimiento.py`: modelo, `registrar`, render de tablas,
   4 capas, `estado`/`dominio`/`ruta`.
2. **P2-F2** — `actualizar()` (desde `escalada` + barreras) + `Tabla-Maestra`.
3. **P2-F3** — tool `crecimiento` (registry + declarations + sync) + wiring con
   `barrier_engine.cerrar`.
4. **P2-F4** — tick diario en `main.py` + reindex + tests + `test_all` + commit.

## 9. Lo que decide el builder

- Formato fino de la tabla y de la maestra.
- Cadencia del tick (propuesta: 1 vez por día, diferido).
- Cómo deduplicar filas repetidas (por `logro`+`dominio`).
