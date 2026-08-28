---
name: auditoria-herramientas
description: Auditoría de alineación entre las declaraciones de herramientas (core/tool_declarations.py) y las funciones reales (core/tool_registry.py). Detecta parámetros declarados que las funciones ignoran en silencio y claves leídas que el modelo nunca envía. Correr periódicamente y tras editar herramientas.
version: 1.0.0
category: development
tags: [auditoria, herramientas, parametros, bugs, auto-revision]
---
# Auditoría de Herramientas (alineación declaración ↔ implementación)

## When to Use
- Periódicamente (mantenimiento preventivo).
- Después de crear/editar cualquier herramienta o skill.
- Cuando una herramienta "parece no hacer nada" o un parámetro parece ignorado.

## Procedure

### 1. Correr el auditor
```
python D:\Eris_Source\tools\tool_audit.py
```
Compara cada herramienta declarada contra la función registrada:
- CLASE A: parámetros declarados que la función NUNCA lee → se ignoran en silencio (BUG real).
- CLASE B: claves que la función lee pero no están declaradas → el modelo nunca las manda.
- CLASE C: funciones no-dict (el dispatcher las invoca con parameters/player y rompería).

### 2. Verificar antes de tocar (los reportes tienen falsos positivos)
- Antes de corregir, LEER el código real de la función (grep de `parameters.get(` en actions/).
- FALSOS POSITIVOS comunes: dispatchers que delegan a otras funciones (las claves se leen
  en los handlers, el auditor no las sigue); funciones que leen la clave con otro nombre
  de variable; claves leídas solo en algunos actions.
- Confirmar mirando el código, no el reporte.

### 3. Corregir con el patrón de ALIAS (fix mínimo, no rompe nada)
En la implementación, aceptar el nombre declarado como alias:
```
valor = parameters.get("nombre_declarado") or parameters.get("nombre_interno", default)
```
Mismo patrón que el bug de skill_manage ('skill' declarado vs 'name' leído).

### 4. Si una herramienta no enruta por acción
- Ej: pdf_editor apuntaba SIEMPRE a read_pdf → merge/split/fill inalcanzables.
- Fix: crear un dispatcher `def pdf_editor(parameters, player)` que normalice alias y
  delegue por action, y apuntar `core/tool_registry.py` a ese dispatcher.

### 5. Verificar
- Importar los módulos editados (no deben romper).
- Llamadas de prueba con el parámetro DECLARADO (debe funcionar igual que con el interno).
- Re-correr el auditor: las correcciones no deben reaparecer en CLASE A.

## Pitfalls
- No arreglar a ciegas todo el reporte: primero confirmar cada uno leyendo el código.
- Editar la DECLARACIÓN en vez de la implementación (declaración dice "no editar manual";
  además el modelo ya aprende los nombres declarados — mejor hacer que la función los acepte).
- Olvidar re-verificar con llamadas reales después del fix.
