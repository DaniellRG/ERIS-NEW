## NUEVAS CAPACIDADES CORE (8 módulos de confiabilidad)

Estos módulos están integrados y listos para usar:

### 1. TERMINAL INTERACTIVA PERSISTENTE
- `terminal_agent` ahora usa un shell PowerShell/CMD persistente entre comandos.
- CWD se mantiene: si hacés `cd D:\proyecto`, los siguientes comandos corren ahí.
- Actions nuevas: `stream` (output en tiempo real), `session_info` (ver estado de sesión), `session_reset` (reiniciar shell).

### 2. EDICIÓN AST-AWARE
- `ast_analyze`: Analiza un archivo .py — funciones, clases, imports, decoradores, líneas.
- `ast_edit`: Edita un archivo con validación AST — si el edit genera syntax error, lo rechaza.
- `file_api` action `edit` con `validate_ast=true`: edita y valida automáticamente.

### 3. MEMORIA UNIFICADA
- Reemplaza los 5 sistemas separados con una sola API.
- `working_add(role, content)` → contexto de conversación actual.
- `long_term_set(category, key, value)` → memoria persistente.
- `episodic_add(event, context)` → qué pasó y cuándo.
- `fact_add(statement, source)` → hechos extraídos.
- `search_all(query)` → busca en todos los tipos de memoria.

### 4. TASK DECOMPOSITION ENGINE
- Crea tareas multi-paso: `TaskEngine.create_task("objetivo", [pasos])`.
- Cada paso tiene: descripción, tool, parámetros, dependencias.
- `execute_task(task)` → ejecuta en orden, respeta dependencias, reintenta fallidos.
- Guarda progreso en disco (sobrevive crashes).

### 5. FILE API UNIFICADA
- `file_api(action, ...)` → reemplaza file_editor + file_controller + code_engineer.
- Actions: read, write, edit, multi_edit, insert, delete, list, mkdir, grep, glob, move, copy, rename, info, backups, restore.
- Backups automáticos antes de cada escritura/edición/borrado.

### 6. AGENT COMMUNICATION BUS
- `agent_bus.set_shared(key, value)` → estado compartido entre agentes.
- `agent_bus.send(receiver, action, payload)` → mensajería entre agentes.
- `agent_bus.subscribe(event, callback)` → pub/sub de eventos.
- `agent_bus.set_scratch(key, value)` → paso temporal de datos entre agentes.

### 7. ERROR AUTO-FIX
- `error_recovery` ahora aplica fixes automáticamente:
  - ModuleNotFoundError → sugiere `pip install`
  - JSON inválido → intenta corregir automáticamente
  - FileNotFoundError → verifica paths
  - PermissionDenied → sugiere admin
- El fix se aplica Y se reintenta la tool original.

### 8. PERMISSION GATE
- Detecta automáticamente acciones riesgosas: rm, del, format, git push, force push, elevated.
- Pide confirmación al usuario antes de ejecutar (ventana flotante).
- Puede confiar por sesión (trust_session) para no preguntar todo el tiempo.
- Log de todas las decisiones de permiso.

### 9. CONSOLE.LOG (Error & Performance Logger)
- Logger centralizado de errores, warnings, tool calls y rendimiento.
- Ubicación: `data/console_logs/console.log`, `errors.log`, `performance.log`
- **Usá `console_log`** para:
  - `action="read"` → Leer las últimas entradas del log
  - `action="errors"` → Ver errores recientes
  - `action="search", query="..."` → Buscar en el log
  - `action="stats"` → Estadísticas de errores y tool calls
  - `action="clear"` → Limpiar el log
- Si ves un error o falla, REGISTRALO con `console_log(action="read")` primero para entender qué pasó.
- El log registra automáticamente: crashes, tool failures, performance metrics, system events.

