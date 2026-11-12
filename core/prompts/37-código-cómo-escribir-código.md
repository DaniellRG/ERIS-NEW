## CÓDIGO — CÓMO ESCRIBIR CÓDIGO

Cuando uses `auto_programmer` o `self_edit` para escribir/modificar código:

1. **ANTES de escribir, EXPLORA**: Lee archivos similares existentes para entender convenciones (imports, naming, estructura). Usa `self_edit` modo read o `codebase` para ver ejemplos.
2. **COPIA el estilo**: snake_case, comillas, imports, todo igual al código existente.
3. **NO asumas librerías**: Si no ves `requests` en imports del proyecto, usá `urllib.request`.
4. **Mínimo código**: Solo lo necesario para la tarea. Sin comentarios a menos que sean esenciales.
5. **Sin try genéricos**: Atrapá excepciones específicas o dejá que fallen (el error ayuda a corregir).
6. **SINTAXIS → SANDBOX → REGISTRO**: Siempre pasar por la pipeline completa de auto_programmer.

Regla de oro: El código existente es la referencia. Nunca inventes un patrón nuevo si ya hay uno en el proyecto.

