# Ingeniería inversa (REA) — conocimiento vivo de Eris

**Qué es.** REA (morluto/rea, MIT) es una caja de herramientas de ingeniería
inversa: un CLI + un servidor MCP con **207 tools** para analizar binarios
nativos, apps JS/Electron, .NET/managed, APKs, firmware, webs/capturas de red,
WASM, EVM, y artefactos Go/Rust/SQLite. No ejecuta por sí solo: **reconstruye**
con evidencia y distingue observación / inferencia / incógnita.

**Cómo lo usa Eris.**
- Tool propia `rea` (passthrough total): `estado`, `doctor`, `capacidades`,
  `comandos`, `evidencia`, `mcp`, y atajos sobre `path`: `analizar`, `js`, `go`,
  `rust`, `sqlite`, `layout`, `web`, `decompilar`, `abrir`. Cualquier otro
  comando: `action=comando, comando=…, arg=…, opciones=…`.
- Cada corrida **guarda el JSON completo** en `data/rea_evidence/` (abrible por
  el dueño) y devuelve a Eris un **resumen** + el `evidence_id` de REA.
- Servidor MCP `rea` registrado en `memory/mcp_config.json`; el puente expone
  las 207 como `mcp_rea_*` (llamables directo / por sub-agentes).
- Skill `reverse-engineer-anything` instalado (skills/user_created) con su
  `SKILL.md` + `references/`: enseña el enrutado por tipo de objetivo y el
  método "summary-first".

**Comando base.** `npx -y rea-agents@6.5.0 mcp` (o el CLI `npx -y rea-agents@6.5.0 <comando>`).
Override por env: `ERIS_REA_SPEC`, `ERIS_REA_CMD`.

**Qué falta (pide OK aparte).** El análisis **nativo pesado** (desensamblar/
decompilar binarios) requiere un motor: **Ghidra** (no configurado —
`GHIDRA_INSTALL_DIR`), Hopper o IDA. Sin motor, REA igual funciona en: JS/Electron
estático, .NET managed, paquetes/archivos, Go/Rust/SQLite, layout ELF, etc.

**Evidencia de absorción.**
- `rea mcp doctor` → `healthy: true`, tools `expected/observed = 207/207`.
- Análisis JS real → `evidence_id ev_28e9c03360cd5fe2b743329fe01a56d9f096841433be365cb934d59fec660bb3`,
  evidencia en `data/rea_evidence/20261014-225142_analyze-javascript-application.json`.

Diseño: `docs/superpowers/specs/2026-10-14-eris-absorbe-rea-design.md`
