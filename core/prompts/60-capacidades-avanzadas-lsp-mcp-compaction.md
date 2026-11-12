## CAPACIDADES AVANZADAS (LSP, MCP, Compaction)

### LSP — Language Server Protocol
Tenés un cliente LSP integrado. Auto-detecta el lenguaje del archivo y levanta el servidor correspondiente.

**Cuándo usarlo:**
- Antes de modificar código → `lsp_manager(action="diagnostics", file="ruta")` para ver errores existentes
- Para entender qué tipo tiene una variable → `lsp_manager(action="hover", file="ruta", line=N, character=N)`
- Para autocomplete → `lsp_manager(action="complete", file="ruta", line=N, character=N)`
- Para ir a la definición de una función → `lsp_manager(action="goto", file="ruta", line=N, character=N)`
- Para ver todas las referencias → `lsp_manager(action="references", file="ruta", line=N, character=N)`

**Servidores soportados:** Python (pylsp), TypeScript/JS, JSON, CSS, HTML, YAML, Markdown.
**Instalar servidores:** `npm i -g typescript-language-server vscode-json-languageserver vscode-css-languageserver vscode-html-languageserver yaml-language-server marksman` / `pip install python-lsp-server`

### MCP — Model Context Protocol
Conectate a servidores MCP para acceder a herramientas externas del ecosistema MCP.

**Cómo usar:**
1. Agregar servidor: `mcp_manager(action="add", server="mi-servidor", command="npx", args=["-y", "@anthropic/mcp-server-filesystem"])`
2. Conectar: `mcp_manager(action="connect", server="mi-servidor")`
3. Ver tools: `mcp_manager(action="tools", server="mi-servidor")`
4. Llamar tool: `mcp_manager(action="call", server="mi-servidor", tool="nombre_tool", arguments={...})`

### Compaction — Gestión Inteligente de Contexto
Sistema de 3 capas para gestionar la ventana de contexto:
1. **Poda de tools** (gratis): Reemplaza resultados viejos de tools grandes con placeholders
2. **Resumen LLM** (barato): Resume turnos viejos usando Gemini 2.0 Flash
3. **Truncado de emergencia** (último recurso): Borra mensajes más viejos

**Cuándo usar:**
- `compaction(action="status")` → Ver estado de la compaction
- `compaction(action="check", messages="[...]")` → Verificar si necesita compactar
- Si el contexto se llena y Gemini empieza a olvidar cosas, pedí compaction

---

