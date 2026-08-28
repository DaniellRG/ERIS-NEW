---
name: review
description: Code review como Staff Engineer (metodología gstack). Encontrar bugs que pasan CI, auto-corregir los obvios, marcar gaps de completitud, no tocar el estilo del autor salvo que sea bloqueante. Usar ante CUALQUIER diff/cambio de código propio o ajeno antes de darlo por terminado.
version: 1.0.0
category: development
tags: [review, code, bugs, diff, ci, gstack]
---
# Code Review — Staff Engineer

## When to Use
Sobre cualquier diff/PR/cambio de código (propio o ajeno) ANTES de considerar la tarea terminada. También como revisor de un plan ya implementado.

## Procedure

### 1. LEER EL DIFF COMPLETO
- Revisar TODOS los archivos cambiados (no solo el archivo principal): config, tests, imports, recursos.
- Prestar atención a lo que se ELIMINÓ, no solo a lo que se agregó.
- Verificar que cada archivo modificado es coherente: sin código muerto, imports sin uso, `print`/debug left-over.

### 2. BUSCAR BUGS QUE PASAN CI (foco principal)
Lo que CI no detecta:
- Cambios de lógica sutiles: `>=` vs `>`, retornos tempranos que cortan el flujo, manejo de None/vacío.
- Estado compartido mutado por error (lists/dicts como defaults, globals, variables reutilizadas).
- Caminos de error que no retornan/continúan mal.
- Race conditions y reentrada en herramientas del agente (dos llamadas simultáneas).
- Timezones y locales (fechas sin tz, formato de hora).

### 3. AUTO-CORREGIR LO OBVIO
- Typos, off-by-one, formato, comparaciones invertidas, nombres confusos: corregirlos directamente.
- Regla: NO reescribir el estilo del autor. Cambiar solo si es bug o es bloqueante para leer.
- Cada auto-fix: mínimo, con justificación de una línea.

### 4. MARCAR GAPS DE COMPLETITUD
- Tests faltantes para la lógica cambiada.
- Manejo de errores ausente (tool calls que pueden fallar y no tienen fallback).
- Documentación/declaración de herramientas sin actualizar (tool_declarations, prompt.txt, inventario de skills).
- Entrada/salida de funciones sin validar.

### 5. VERIFICACIÓN (no fingir)
- Si el cambio tiene tests: correrlos (`ci_cd`, pytest). Si NO los tiene, decirlo explícito.
- Smoke test del símbolo tocado: `get_tool('nombre')` + llamada real con el parámetro declarado.
- Buscar referencias rotas: grep del símbolo renombrado/eliminado en TODO el proyecto.

### 6. VEREDICTO
- APROBADO / APROBADO CON CAMBIOS / RECHAZADO (con la lista exacta de archivos y líneas).
- Bugs corregidos: listados uno por uno con `archivo:línea`.
- Gaps pendientes: listados como "seguimiento necesario".
- Lenguaje claro, sin humillaciones: es el código del equipo, el objetivo es que funcione.

## Pitfalls
- Revisar solo "lo que se ve": saltar config/tests/imports.
- Confundir preferencia de estilo con bug.
- Aprobar con "parece que funciona" sin correr nada.
- Ignorar lo eliminado: a veces el bug está en lo que se quitó.
- No marcar referencias rotas del símbolo renombrado (grep obligatorio).
