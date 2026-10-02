# B4 — Ajustes mínimos a AGENTS.md

## Cambios hechos
- Fila tabla `core/tool_declarations.py`: añadir "(0 dupes, sync 507/507 verificado)" para reflejar el estado real tras corrección del desync (reg=507 dec=507).

## Notas (sin reescritura extensa)
- `core/hermes_bridge.py` es el puente canónico en `127.0.0.1:6790`. `core/opencode_bridge.py` escucha en `127.0.0.1:6789` (distintos puertos, conviven). AGENTS.md describe el flujo hacia Hermes apuntando a 6790; la ambigüedad en la redacción no fue modificada para mantener edición mínima.
- `tools/hermes_helper.py` existe (creado) con interfaz compatible a lo documentado. `tools/hermes_poll.py` también existe como CLI auxiliar.
- Sync de tools verificado: 507/507, 0 duplicados.

Edición limitada a lo estrictamente verificable.