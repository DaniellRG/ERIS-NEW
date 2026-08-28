---
name: workflow-codigo
description: Pipeline completo de cambio de código estilo opencode: mapa → plan → edición mínima → REVISAR EL PROPIO DIFF como un reviewer → verificación → documentar/aprender → cerrar. Usar en CUALQUIER modificación de código, propia o de otros proyectos.
version: 1.0.0
category: development
tags: [codigo, edicion, review, verificacion, diff]
---
# Workflow Completo de Cambio de Código

## When to Use
Cualquier modificación de código: arreglar un bug, agregar una función, refactorizar, o editar el propio código de ERIS.

## Procedure

### 1. MAPA
- Ubicar con búsquedas (`codebase` search, `code_copilot` locate, grep): qué archivos/funciones están involucrados.
- Leer SOLO las secciones relevantes (no archivos enteros).
- Entender convenciones: naming, indentación, imports, patrón del proyecto.

### 2. PLAN
- 2-3 hipótesis si es un bug. Definir el cambio MÍNIMO necesario.
- Anotar el plan con `task_planner` o `todowrite` (pasos cortos y verificables).
- Si es un BUG: crear un REPRODUCTOR MÍNIMO (MCVE) — 10-20 líneas o una llamada directa que lo haga fallar — y confirmar que FALLA antes de tocar nada.

### 3. EDICIÓN MÍNIMA
- `code_copilot` (fix/add) o `self_edit`: tocar SOLO las líneas necesarias.
- No reescribir archivos completos. No agregar comentarios salvo que aporten.
- Respetar el estilo existente. No inventar patrones nuevos.

### 4. REVISAR EL PROPIO DIFF (paso que muchos se saltan)
Leer el cambio hecho como si fuera de otro desarrollador:
- ¿Convenciones respetadas? ¿naming/indentación/imports consistentes?
- ¿Quedó código muerto o funciones sin usar?
- ¿Referencias rotas? (grep del símbolo renombrado/eliminado en TODO el proyecto)
- ¿Secretos o claves hardcodeadas? (NUNCA exponer claves)
- ¿El cambio está aislado del síntoma? (no arreglar otra cosa de paso)

### 5. VERIFICACIÓN (no negociable)
- Compilar/ejecutar los tests si el proyecto los tiene (`ci_cd`, `code_analyzer`). Si no hay tests, DECIRLO.
- Si el cambio arregla un bug: re-correr el MISMO reproductor mínimo (MCVE) y confirmar que ya no falla.
- Si depende de un servicio externo: TEST DE VERDAD (probar el endpoint real y leer el error crudo).
- TEST DE HUMO: tras editar tu propio código, importá el módulo y hacé una llamada de prueba real:
  `get_tool('nombre')` y ejecutarla con el parámetro DECLARADO. Si no responde como esperás, el cambio no está listo.
- Confirmar con evidencia: build OK, log sin errores, comando devuelve lo esperado.
- SI NO SE PUEDE VERIFICAR, NO DAR POR TERMINADO: reportar qué falta verificar.

### 6. DOCUMENTAR / APRENDER
- Si fue complejo o repetible: guardar lección (`learn_from_mistake`), nota en Obsidian, y crear/actualizar una skill con `skill_manage(action='create'...)` o `tool_creator`.
- El conocimiento que no se guarda se pierde en la próxima sesión.

### 7. CERRAR
- Reportar al usuario: QUÉ se cambió y CÓMO se verificó. En lenguaje claro.
- Si algo quedó sin verificar, decirlo explícitamente.

## Pitfalls
- Editar sin mapear antes (tocar archivos equivocados).
- No revisar el diff propio (typos, código muerto, referencias rotas).
- Hardcodear claves o secretos en el cambio.
- Dar por terminada una tarea sin verificación real.
- Olvidar documentar: la próxima sesión no recuerda nada.
