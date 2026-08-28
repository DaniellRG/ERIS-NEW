---
name: exploracion-paralela
description: Patrón de exploración con subagentes en paralelo: cuando una tarea tiene varias partes desconocidas independientes, lanzar subagentes simultáneos (uno por zona) en vez de explorar secuencialmente, y fusionar resultados. Usar en investigaciones, diagnósticos grandes o tareas con múltiples áreas.
version: 1.0.0
category: development
tags: [subagentes, paralelo, investigacion, mapeo, eficiencia]
---
# Exploración en Paralelo con Subagentes

## When to Use
Una tarea tiene DOS O MÁS partes desconocidas e independientes (distintas carpetas, módulos, servicios o preguntas que no dependen entre sí). Explorarlas una por una desperdicia tiempo y atención. En paralelo se resuelven a la vez.

## Procedure

### 1. Decidir si vale la pena paralelizar
- SÍ: 2+ áreas independientes, cada una requiere búsquedas o lecturas que no comparten estado.
- NO: tareas diminutas (el overhead no vale), dependencias lineales (A antes de B), zonas que comparten archivos/estado mutable.

### 2. Dividir y lanzar
- Identificar las partes independientes del problema.
- Lanzar UN subagente por área con `subagent_task` (o `auto_agent`/`task_planner`), cada uno con:
  - Una PREGUNTA ESPECÍFICA (no "explorá el proyecto").
  - El alcance exacto (carpetas/archivos permitidos).
  - QUÉ debe devolver: hechos concretos con rutas y números de línea, no resúmenes vagos.
- Lanzarlos TODOS en el mismo momento para que corran en paralelo.

### 3. Recolectar y fusionar
- Esperar a que TODOS terminen antes de actuar.
- Fusionar los resultados en un mapa mental único.
- Verificar coherencia: si dos subagentes se contradicen, re-explorar esa zona específica.

### 4. Actuar
- Solo después de tener el mapa completo, decidir hipótesis y acciones.
- No saltar a editar mientras la exploración está incompleta.

## Pitfalls
- Pedir resúmenes vagos a los subagentes (definir SIEMPRE el formato de retorno: ruta, línea, qué hace, prueba).
- Lanzar subagentes con alcances solapados (resultados contradictorios).
- Paralelizar tareas triviales (más overhead que beneficio).
- Empezar a tocar código antes de tener el mapa completo.
