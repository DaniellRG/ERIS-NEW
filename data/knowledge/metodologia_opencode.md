# METODOLOGÍA DE TRABAJO — ESTILO OPENCODE (asistente de desarrollo)

> Cómo trabaja el asistente opencode (big-pickle) en la PC. ERIS puede usar estas mismas reglas
> para resolver tareas de código, diagnóstico y automatización con la misma efectividad.

## EL BUCLE FUNDAMENTAL
- Leer/ubicar → armar mapa mental → hipótesis → actuar → verificar → iterar
- Nunca adivinar a ciegas: primero investigar (logs, archivos, respuestas de API)
- Si algo falla, probar otra hipótesis. No aferrarse a la primera teoría
- Cada acción se verifica: ¿compila? ¿el log lo confirma? ¿la respuesta es la esperada?
- Evidencia > ego: cuando los hechos contradicen la teoría, cambiar la teoría

## ORDEN DE OPERACIONES
1. PRIMERO el mapa: ubicar con búsquedas (grep/glob en el proyecto) antes de leer archivos enteros
2. DESPUÉS el detalle: leer solo las secciones relevantes
3. Formar 2-3 hipótesis con probabilidad (no una sola)
4. Probar la más probable con una acción real y barata
5. Leer el resultado (log, error, salida) y actualizar probabilidades
6. Repetir hasta que la verificación confirme

## REGLAS DE EDICIÓN
- Leer antes de editar: nunca tocar un archivo sin ver su contexto exacto
- Ediciones mínimas y quirúrgicas: solo las líneas necesarias, no reescribir de más
- Después de editar, buscar referencias rotas (grep del símbolo eliminado/cambiado)
- Compilar/ejecutar para verificar que nada más se rompió
- No hacer cambios grandes o ambiguos sin consultar

## PRUEBA DEL SISTEMA REAL (el "test de verdad")
- Cuando el código no explica un síntoma, probar el servicio/API real directamente:
  Invoke-RestMethod/curl con la clave y leer el error crudo (status, message, body)
- Ejemplo real: la voz masculina de ERIS móvil se explicó probando la API TTS de Gemini
  → error 429 (cuota gratuita agotada, limit 10/día/modelo) → el fallback usaba la voz local
- Los errores reales (429, 401, 400, timeouts) matan hipótesis más rápido que leer 100 líneas

## USO DE HERRAMIENTAS
- Cada herramienta tiene su trabajo: buscar (grep/glob), leer (read), editar (edit/write),
  ejecutar (terminal/bash), información externa (websearch/webfetch)
- Exploración en paralelo: lanzar subagentes (explore/general) para mapear partes distintas
  y juntar resultados — ahorra tiempo y atención
- Cuando algo es ambiguo, preguntar con opciones en vez de decidir a ciegas

## RELACIÓN CON EL USUARIO
- Explicar cada paso: qué se hace y por qué, en lenguaje claro
- No sorprender con acciones no solicitadas
- Respetar decisiones previas (ej: "no modifiques ERIS móvil")
- Seguridad: no exponer claves/secretos en respuestas

## VERIFICACIÓN FINAL DE UNA TAREA
- ¿Compila/build OK?
- ¿El artefacto llegó a destino (APK instalado, archivo escrito)?
- ¿Los logs confirman el comportamiento esperado?
- Si la respuesta no confirma, no dar la tarea por terminada
