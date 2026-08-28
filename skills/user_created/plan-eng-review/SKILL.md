---
name: plan-eng-review
description: Revisión de plan de ingeniería (Eng Manager). Bloquear arquitectura, flujo de datos, edge cases, matriz de tests y riesgos antes de implementar. Usar ante CUALQUIER plan/feature que vaya a tocar código, siguiendo la metodología de gstack.
version: 1.0.0
category: development
tags: [plan, arquitectura, eng, review, edge-cases, tests, gstack]
---
# Plan de Ingeniería — Eng Manager Review

## When to Use
Antes de implementar cualquier feature, refactor o cambio con impacto arquitectónico.
Rol: Ingeniero Líder que fuerza a que los supuestos ocultos salgan a la luz antes de escribir código.

## Procedure

### 1. ENTRADA
- Tomar el plan/objetivo y el contexto (archivos involucrados, funciones a tocar).
- Leer las secciones relevantes del código actual con `codebase`, `code_analyzer` o `file_controller` (grep).
- NO implementar nada en este paso: solo revisar el plan.

### 2. ARQUITECTURA
- Confirmar que cada paso del plan aterriza en archivos/funciones concretos y existentes (o nuevos justificados).
- Mapear el flujo de datos: entrada → transformación → salida. ¿Hay pasos intermedios faltantes?
- Verificar que el cambio no rompe contratos: firmas de funciones, importaciones, formato de parámetros.
- Señalar dependencias y su orden correcto (setup antes que core, core antes que polish).

### 3. EDGE CASES (no negociable)
Para cada paso, listar casos límite:
- Entradas vacías, None, valores extremos (0, negativo, máximo).
- Archivos/datos inexistentes o corruptos.
- Fallos de red/API/timeout (401, 429, 503).
- Permisos insuficientes, rutas con espacios o acentos (Windows).
- Concurrencia: dos llamadas simultáneas, reentrada, carreras.

### 4. MATRIZ DE TESTS
- Definir QUÉ verificar y CÓMO para cada paso del plan.
- Indicar el comando de test concreto (pytest, py_compile, smoke test de import + llamada real).
- Si el proyecto no tiene tests para esa área, marcarlo como riesgo: "no verificable sin test".
- Pedir un MCVE (reproductor mínimo) si hay bug.

### 5. SEGURIDAD
- OWASP Top 10 rápido: inyección, XSS, path traversal, secretos hardcodeados, deserialización insegura.
- Verificar que el plan no introduzca comandos con input sin validar ni claves en logs.

### 6. VEREDICTO
Responder en formato claro:
- APROBADO / APROBADO CON CAMBIOS / RECHAZADO
- Lista numerada de: (a) riesgos bloqueantes, (b) edge cases a cubrir, (c) tests requeridos, (d) archivos críticos.
- Si hay que modificar el plan, devolver los pasos ajustados.

## Pitfalls
- Aprobar sin leer el código real (revisar el mapa, no solo el texto del plan).
- Ignorar Windows: rutas con espacios/acentos, separadores, permisos.
- Confundir "se compila" con "funciona": exigir test de verdad/llamada real.
- No exigir matriz de tests: sin prueba definida, el paso no es verificable.
- Dejar edge cases fuera "porque es poco probable": eso es lo que rompe en producción.
