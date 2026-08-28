---
name: depuracion-playbook
description: Playbook de depuración rápida: qué hacer ante cada clase de fallo típico (app que no arranca, comando que falla, API con error, build roto, resultado incorrecto, problema de red). Usar cuando algo no funciona y no sabés por dónde arrancar.
version: 1.0.0
category: development
tags: [debugging, fallos, api, build, red, logcat]
---
# Playbook de Depuración — Triage por clase de fallo

## When to Use
Algo falla y no sabés por dónde arrancar. Elegí la clase de fallo y seguí los pasos. Regla de oro: SI EL CÓDIGO NO EXPLICA EL SÍNTOMA, EL PROBLEMA ESTÁ FUERA DEL CÓDIGO (red, permisos, cuota, hardware).

## Procedure

### 1. La app / programa no arranca
- Ejecutarlo desde terminal/consola para ver el error crudo en stderr (no doble clic).
- Android: `adb logcat -d | findstr /i "eris"` o grep del paquete; buscar excepciones y el stacktrace completo.
- Verificar que los archivos/dependencias que usa existen y están en la ruta esperada.
- Verificar permisos (archivo bloqueado, falta admin).

### 2. Un comando falla
- Leer el MENSAJE DE ERROR COMPLETO, no las últimas líneas.
- Revisar sintaxis, rutas con espacios (comillas), permisos.
- Dividir el comando en pasos más chicos hasta aislar cuál falla.

### 3. Una API devuelve error
- Probar el endpoint directo: `Invoke-RestMethod -Uri "<endpoint>" ...` o `curl -X POST ...`, con la clave real, y leer status + body CRUDO.
- 401/403 → clave inválida/sin permisos. 429 → cuota o límite de tasa (agotada). 400/422 → parámetros mal. 5xx → problema del servidor, no tuyo.
- Buscar el mensaje exacto del body (ej: "RESOURCE_EXHAUSTED" de Google) con websearch si hace falta.

### 4. Build / compilación falla
- Leer el PRIMER error (los siguientes suelen ser consecuencias en cascada).
- Buscar referencias a símbolos renombrados/eliminados (grep del nombre en el proyecto).
- Verificar imports, versiones de dependencias, variables de entorno (ANDROID_HOME, JAVA_HOME, etc.).

### 5. Resultado incorrecto pero sin error
- Instrumentar con logs temporales en el punto crítico (no adivinar).
- Aislar el MÍNIMO caso que reproduce el problema y probar la lógica paso a paso.
- Verificar el estado real: ¿el archivo se escribió? ¿la variable tiene el valor esperado?

### 6. Problema de red / conectividad
- `Test-NetConnection <host> -Port <puerto>` o `curl -I https://host` para ver si responde.
- Probar sin proxy/VPN si hay alguna configurada.
- Android: verificar que el dispositivo tenga internet (`adb shell ping -c 3 8.8.8.8`).

### 7. Nunca
- NUNCA probar lo mismo dos veces sin cambiar algo. NUNCA repetir una hipótesis descartada.
- Si llevás 3 intentos sin avanzar, parar y explicar qué se probó + pedir ayuda (o usar ask_opencode).
- No tocar nada que no esté relacionado con el síntoma.

## Pitfalls
- Mirar solo el final del error (los problemas se esconden al principio).
- Culpar al código sin probar el servicio real primero.
- Repetir el mismo intento esperando otro resultado.
