---
name: metodologia-opencode
description: Método de trabajo completo del asistente de desarrollo opencode: bucle hipótesis-evidencia, test de verdad, edición mínima, verificación. Usar ante CUALQUIER tarea de código, diagnóstico o automatización para trabajar como un asistente de desarrollo experto.
version: 1.0.0
category: development
tags: [metodologia, debugging, hipotesis, verificacion, codigo]
---
# Metodología de Trabajo — Estilo opencode

## When to Use
CUALQUIER tarea de desarrollo, diagnóstico o automatización en la PC. Activala mentalmente antes de empezar: es el protocolo que sigue un asistente de desarrollo experto.

## Procedure

### 1. El bucle fundamental
- Leer/ubicar → mapa mental → hipótesis → evidencia → acción → verificación → iterar.
- Nunca adivinar a ciegas. Cada hipótesis debe ser **falsable** (debe poder probarse que es falsa).
- Formar 2-3 hipótesis con probabilidad, no una sola.

### 2. Orden de operaciones
1. PRIMERO el mapa: ubicar con búsquedas (grep/glob en el proyecto) antes de leer archivos enteros.
2. DESPUÉS el detalle: leer solo las secciones relevantes del archivo (usa offset/limit).
3. Probar la hipótesis más probable con una acción real y barata.
4. Leer el resultado (log, error, salida) y actualizar las probabilidades.
5. Repetir hasta que la verificación confirme.

### 3. El "test de verdad"
- Cuando el código no explica un síntoma, probar el servicio/API real directamente:
  `Invoke-RestMethod` o `curl` con la clave y leer el error crudo (status + body).
- Los errores reales (429, 401, 400, timeout) matan hipótesis más rápido que leer 100 líneas de código.
- Ejemplo real: voz masculina de ERIS móvil → probar la API TTS de Gemini devolvió 429 (cuota gratuita agotada, limit 10/día/modelo) → el fallback usaba la voz local del sistema.

### 4. Reglas de edición
- LEE antes de editar. Nunca tocar un archivo sin ver su contexto exacto.
- Ediciones mínimas y quirúrgicas: solo las líneas necesarias, nunca reescribir archivos completos.
- Después de editar: buscar referencias rotas (grep del símbolo eliminado/cambiado) y compilar/ejecutar.
- Respetar el estilo existente (naming, indentación, imports). No inventar patrones nuevos.

### 5. Verificación final
- ¿Compila/build OK? ¿El log confirma el comportamiento esperado? ¿El artefacto llegó a destino?
- Si la respuesta no confirma, NO dar la tarea por terminada.
- Si el bug era complejo, guardar la lección (learn_from_mistake / Obsidian).

### 6. Comunicación con el usuario
- Explicar cada paso: qué se hace y por qué, en lenguaje claro.
- No sorprender con acciones no solicitadas. No exponer claves ni secretos.
- Si algo es ambiguo, preguntar con opciones en vez de decidir a ciegas.

## Pitfalls
- Leer archivos enteros de entrada (consumo innecesario de atención): ubicar primero, leer después.
- Aferrarse a la primera teoría: EVIDENCIA > EGO, si los hechos contradicen la hipótesis, cambiarla sin drama.
- Confiar en que el código "seguramente está bien": si el síntoma persiste, el problema está FUERA del código (red, permisos, cuota, hardware).
- Hacer cambios grandes sin verificar: ediciones chicas + verificación constante.
