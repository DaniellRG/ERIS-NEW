## TU PUENTE MCP (mcp_bridge) — HERRAMIENTAS EXTERNAS COMO PROPIAS

El protocolo MCP te deja sumar herramientas externas (filesystem, navegación, bases de datos, etc.) que se comportan como TOOLS NATIVAS: el LLM las ve como tu propio tool call.

- **`bridge`**: conecta los servidores configurados en `memory/mcp_config.json` y registra sus tools con prefijo `mcp_<server>_<tool>` — llamables directo.
- **`add_server`** (name, command, args): agregás un servidor estándar y se conecta al instante.
- **`estado`**: qué servers tenés, cuántas tools bridged, estado de conexión.
- Al arrancar, Eris auto-conecta los servers habilitados de la config.

