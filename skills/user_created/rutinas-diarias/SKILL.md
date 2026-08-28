---
name: rutinas-diarias
description: Rutinas diarias de ERIS estilo Jarvis OS. Inbox matutino (repaso de pendientes del vault Obsidian), plan del día (objetivos y agenda), métricas (recursos del sistema), actualizar vault Obsidian y cierre del día. Usar cuando Daniel pida "rutinas", "rutina de la mañana", "plan del día", "inbox", "cierre del día", "métricas del sistema" o arranque/cierre de jornada.
version: 1.0.0
category: routines
tags: [rutinas, inbox, plan, metricas, vault, obsidian, jarvis, cierre]
---

# Rutinas Diarias (Jarvis OS)

Flujo de rutinas que ERIS ejecuta como un verdadero "Jarvis OS", conectando la
memoria del vault Obsidian, las tareas/agenda y los recursos del sistema.

## When to Use
- **Inbox matutino**: al despertar / primer uso del día → repasar pendientes y notas del vault.
- **Plan del día**: cuando pida "plan del día" o "qué tengo hoy".
- **Métricas**: estado de CPU, RAM, disco, red y batería.
- **Vault**: guardar/leer notas en la base Obsidian.
- **Cierre del día**: resumen de lo hecho y cierre de la jornada.

## Procedure

### 1. INBOX MATUTINO ("buenos días" / "inbox")
1. Obtener fecha/hora actual (`eris_time_now`).
2. Leer pendientes y notas del vault Obsidian (`obsidian_note` action `search`/`read` o `obsidian_brain`).
3. Leer tareas pendientes (`db_tasks` action `list`).
4. Saludar a Daniel con: hora, clima si está configurado, N pendientes del vault,
   N tareas pendientes, y la primera prioridad sugerida.
5. Si hay algo urgente, decirlo primero.

### 2. PLAN DEL DÍA ("plan del día" / "qué tengo hoy")
1. Listar tareas del día (`db_tasks` action `list`, filtrar por hoy si es posible).
2. Leer recordatorios programados (`scheduler` / `reminders`).
3. Consultar objetivos activos (`goals`).
4. Entregar: lista priorizada (1..N), cada ítem con su ventana horaria si existe,
   y preguntar si quiere reordenar o agregar algo.

### 3. MÉTRICAS DEL SISTEMA ("métricas" / "cómo está la pc")
1. Ejecutar `res_monitor` action `status` o `dashboard` action `system`.
2. Reportar: CPU %, RAM usada/total, disco, red, batería, procesos top.

### 4. VAULT OBSIDIAN ("guardá esto" / "anotá" / "acordate de")
1. Identificar tipo de nota (idea, tarea, dato, pendiente).
2. Guardar en el vault con `obsidian_note` (action `add`/`create`) o `save_memory`.
3. Confirmar la ruta exacta guardada (carpeta del vault) y confirmar con 1 frase.
4. Si es un pendiente, además agregarlo a `db_tasks` action `add`.

### 5. CIERRE DEL DÍA ("cierre del día" / "buenas noches")
1. Resumir lo hecho: tareas completadas (db_tasks), notas creadas hoy en el vault.
2. Guardar un resumen del día en el vault Obsidian (nota `Resumen-YYYY-MM-DD`).
3. Listar pendientes que quedan para mañana.
4. Despedida breve y cálida con la hora de mañana sugerida.

## Pitfalls
- No inventar datos: si el vault no tiene notas o no hay tareas, decirlo.
- No sobrecargar: inbox y plan máximos 5-7 ítems priorizados.
- El vault vive en `D:\Eris_NEW\BaseDatosObsidian\BaseObsiEris` — verificar existencia antes de escribir.
- Si Ollama/Gemini está caído, seguir con las tools locales (db_tasks, obsidian_note) que no dependen de red.
