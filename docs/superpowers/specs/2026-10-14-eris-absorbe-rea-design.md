# ERIS absorbe REA — diseño

Fecha: 2026-10-14
Repo fuente: https://github.com/morluto/rea (MIT), paquete npm `rea-agents`
Versión verificada: **6.5.0**

## Qué pidió el dueño

"Que Eris aprenda a realizar esto… colocale todo lo que tenga este repositorio
a Eris, que pueda Eris manejarlo". En la charla se aclaró el porqué: Eris es una
IA agéntica que **absorbe conocimiento y lo aplica**; cuando al dueño se le
ocurre un proyecto, ella ya sabe encararlo y ejecutarlo. REA es la **primera
capacidad concreta** que Eris absorbe, reutilizando el andamiaje que ya existe
(motor de barreras de P1, tablas de crecimiento de P2, sub-agentes, fábrica).

## Qué es REA (hechos verificados, no marketing)

- CLI + **servidor MCP stdio** (`npx -y rea-agents@6.5.0 mcp`).
- **207 tools + 6 prompts** (lo confirma `rea mcp doctor`: `healthy: true`,
  `expected/observed = 207/207`, protocolo 2025-11-25).
- Cubre: binarios nativos (Ghidra/Hopper/IDA/rizin/gdb), apps JS/Electron,
  .NET/managed, APKs, firmware (binwalk), webs/capturas (Playwright, pcap,
  tshark), WASM, EVM, Go/Rust/SQLite (estos últimos **target-free**, sin motor
  nativo).
- Trae un **skill de agente** (`skills/reverse-engineer-anything/`: `SKILL.md` +
  6 `references/*.md`) que enseña el enrutado por tipo de objetivo.
- Sin motor nativo, REA **igual funciona** en: JS/Electron estático, .NET
  managed, paquetes/archivos, Go/Rust/SQLite, layout ELF (pwntools), etc.

## Restricciones del entorno (relevo)

- Node v26.11.1 / npm 11.20.0 (mise, prefix **escribible**, sin sudo).
- **No hay** Ghidra, Hopper, IDA, rizin, JADX, adb, tshark, binwalk. Solo
  `objdump`. → El análisis **nativo pesado** queda como paso aparte que pide OK
  (instalar Ghidra es una incorporación grande).
- Eris ya tiene cliente MCP stdio (`actions/mcp_standard.py`) + puente
  (`core/mcp_bridge.py`) + tool MCP declarada (`mcp_tool`, con
  `call_standard`/`list_standard`).

## Diseño (3 capas, todo reusado)

### 1. Capa de acceso: tool propia `rea` (CLI)

`core/rea_engine.py` expone **una** tool `rea` que corre el CLI de REA con
`--json`. Un único punto de entrada (cabe en el tope de 128 de Gemini y queda
siempre visible) con **passthrough total**: la acción `comando` corre **cualquiera
de los 207 comandos**. Acciones amables: `estado`, `doctor`, `capacidades`,
`comandos`, `analizar`, `js`, `go`, `layout`, `decompilar`, `comando`,
`evidencia`, `mcp`.

Diseño "evidencia dura": **cada corrida guarda el JSON completo** en
`data/rea_evidence/<ts>_<cmd>.json` (archivo que el dueño puede abrir) y devuelve
a Eris un **resumen** compacto + el `evidence_id` de REA + la ruta del archivo.
Así el grafo enorme nunca revienta el contexto, pero la evidencia full queda
persistida.

### 2. Capa MCP: servidor `rea` registrado en Eris

`memory/mcp_config.json` registra `rea` como server estándar estándar
(`npx -y rea-agents@6.5.0 mcp`). El puente existente
(`core/mcp_bridge.bridge_standard_tools`) expone las 207 tools como
`mcp_rea_*` para Eris (dispatcher/sub-agentes) y vía `mcp_tool
action=list_standard|call_standard`. La acción `mcp` de la tool `rea`
**re-crea el registro si falta** (memory/ es runtime y puede borrarse).
stdio puro: **no abre puertos** (nada que exponer; sin riesgo de red).

### 3. Capa de comprensión/registro: skill + memoria

- Skill `reverse-engineer-anything` instalada en
  `skills/user_created/reverse-engineer-anything/` (**SKILL.md + references/**),
  para que Eris sepa enrutar y trabajar "summary-first".
- `data/knowledge/ingenieria_inversa.md` (espejo de conocimiento, como
  `escalada_vivo.md`).
- Registro en `escalada` + `crecimiento` (dominio **fabrica** = crear sus
  propias capacidades) con **evidencia real** (doctor 207/207 + análisis JS con
  `evidence_id`), y novedad en `todo_yo`.

## Evidencia de aceptación (lo que el dueño puede abrir)

1. `rea mcp doctor` → `healthy: true`, 207/207 (lo corre Eris vía la tool).
2. Un análisis JS real de un objetivo propio → `evidence_id` + JSON guardado en
   `data/rea_evidence/`.
3. La fila en `…/BaseObsiEris/Crecimiento/Tabla-fabrica.md` con la evidencia y
   la ruta del archivo.

## Fuera de alcance (pide OK aparte)

- Instalar **Ghidra** (o usar Hopper/IDA) para desensamblar binarios nativos.
  Sin eso, REA funciona en todo lo target-free y en JS/.NET/paquetes. No se
  instala nada pesado sin aprobación explícita.
