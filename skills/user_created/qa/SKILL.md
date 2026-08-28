---
name: qa
description: QA Lead (metodología gstack). Probar la app real, encontrar bugs, arreglarlos con commits atómicos, re-verificar, generar tests de regresión. Enfocado en bugs de UI/UX, rutas de error, y regresiones. Usar cuando la tarea es encontrar o corregir bugs en la interfaz/flujo del usuario.
version: 1.0.0
category: development
tags: [qa, testing, bugs, ui, ux, regresion, gstack]
---
# QA Lead

## When to Use
- Para verificar que un cambio no rompió el comportamiento del usuario.
- Cuando se busca activamente bugs en la interfaz/flujo (nuevo feature, refactor).
- Si se necesita generar tests de regresión a partir de bugs encontrados.

## Procedure

### 1. MAPA DE LA FEATURE/FLUJO
- Entender QUÉ debería hacer el usuario (entry point → happy path → salida).
- Identificar caminos alternativos: input inválido, vacío, cancelación, timeout.
- Notar: si el flujo toca archivos de configuración, permisos, o servicios externos, mapearlos.

### 2. PROBAR EL FLUJO REAL
- Usar herramientas del sistema: `file_reader` para leer lo que se generó; `exec_python`/`shell` para simular; `codebase` para confirmar que la función existe.
- Simular input extremo: vacío, None, 0, negativo, strings muy largos, caracteres especiales.
- Para UI: describir cada paso con texto claro ("hice click aquí, me llegó esto"). No hay navegador real, pero se puede verificar la lógica detrás.
- Verificar la lógica: si algo se genera, ¿existía antes? ¿es consistente? ¿se sobreescribió?

### 3. IDENTIFICAR BUGS
Clasificar:
- BUG CRÍTICO: crashea, borra datos, expone info, rompe el flujo principal.
- BUG MAYOR: comportamiento incorrecto que afecta al usuario.
- BUG MENOR: cosmetico, UX molesta pero funcional.
- NO-BUG: preferencia de estilo, comportamiento documentado.

### 4. ARREGLAR CON COMMITS ATÓMICOS
- Cada bug arreglado: UN commit con nombre claro y descriptivo.
- Nunca arreglar varios bugs en un commit.
- Antes de cada commit: correr el test afectado + smoke test.
- Si un fix afecta a otro archivo (propagación), correr el flujo completo después.

### 5. RE-VERIFICAR TODO
- Re-hacer el flujo completo que falló, ahora debe funcionar.
- Correr tests existentes (si los hay) para confirmar que no se rompió nada.
- Si el fix depende de un servicio externo: TEST DE VERDAD (llamada real, leer error crudo).
- Confirmar con evidencia: log, output, ejecución exitosa.

### 6. GENERAR TEST DE REGRESIÓN
- Si el bug no estaba cubierto por tests: crear un test mínimo que lo reproduzca (pytest o script de smoke).
- El test debe FALLAR sin el fix y PASAR con el fix.
- No crear tests vacíos o trivialmente verdaderos.

## Pitfalls
- Confundir "no crashea" con "funciona bien": revisar el output esperado.
- Arreglar el bug y no re-verificar el flujo completo (regresión por fix).
- Crear tests que siempre pasan (no reproducing el escenario de error).
- Arreglar varios bugs en un mismo commit (más difícil de revertir).
- Probar solo el happy path: los bugs viven en los edge cases.
