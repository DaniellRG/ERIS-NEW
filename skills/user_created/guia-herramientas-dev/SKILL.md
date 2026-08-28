---
name: guia-herramientas-dev
description: Guias de las tools de ERIS de desarrollo e infra: task_scheduler, auto_agent, code_generator, code_copilot, memoria semantica, context_engine, browser_unified, process_manager, driver_manager, backup_system. Cargar al programar, automatizar tareas, gestionar procesos o usar el navegador por API.
version: 1.0.0
category: development
tags: [guias, desarrollo, tareas, copilot, browser, procesos, backups, rag]
---

## TAREAS PROGRAMADAS (task_scheduler)
ERIS puede ejecutar tareas automáticamente sin que le pidan.
- add: crear tarea programada. Params: text="tarea", schedule="every 30 minutes" / "daily at 10:00" / "weekly on monday"
- list: ver tareas programadas activas
- delete: eliminar tarea por ID
- run_now: ejecutar tarea inmediatamente
- pause/resume: pausar/reanudar tarea
- log: ver historial de ejecuciones

## AGENTE AUTÓNOMO (auto_agent)
Descompone tareas complejas en pasos y las ejecuta solo.
- plan: crear plan de ejecución. Params: text="Protege mi PC"
- execute: ejecutar plan paso a paso
- status: ver progreso del plan actual
- cancel: cancelar plan en ejecución
- history: ver planes anteriores

## GENERADOR DE CÓDIGO (code_generator)
Genera scripts bajo demanda.
- generate: generar script. Params: text="script que organice mis descargas", language="python/powershell/batch"
- save: guardar script en archivo
- run: ejecutar script generado
- list: ver scripts generados
- template: obtener plantilla base

## COPILOT DE CÓDIGO (code_copilot) — USALO SIEMPRE PARA PROGRAMAR
Tu asistente de código con IA y edición QUIRÚRGICA. Soporta TODOS los lenguajes: java, html, css, javascript, typescript, python, c#, c++, react, angular, vue, bootstrap, mysql, php, go, rust, bash, json, yaml.
- new: generar código o proyecto completo. Params: description="...", language="java|html|react|...", output_dir="carpeta", filename="..."
- fix: corregir un error tocando SOLO las líneas necesarias. Params: file_path="ruta", error="mensaje de error o descripción", line="número opcional"
- add: agregar código a un archivo existente en el punto correcto. Params: file_path, description="qué código agregar"
- locate: encontrar dónde están los problemas. Params: path="carpeta o archivo", issue="qué buscar"
- analyze: análisis completo de un archivo o proyecto. Params: path
- structure: organizar un proyecto en carpetas estándar. Params: path, apply="true" para aplicar (default: propuesta)
- organize: mover archivos a carpetas por tipo (code/web/assets/datos/docs). Params: path, apply="true"
- rename: renombrar archivo y (opcional) actualizar referencias. Params: file_path, new_name, update_refs="true"
- languages: listar lenguajes soportados
- knowledge: mostrar convenciones de un lenguaje. Params: language

REGLAS DE ORO PARA CORREGIR:
1. Cuando un código falla, usá code_copilot action=fix: corrige SOLO la línea (o las líneas) con el error, NUNCA reescribas todo el archivo.
2. Para agregar funcionalidad a un código que ya existe, usá action=add: inserta en el punto correcto (imports, dentro de la clase, junto a lo relacionado).
3. Antes de generar, pensá la estructura: separá en archivos/carpetas lógicas.
4. Para proyectos, generá la estructura completa (components, styles, services, db...).

## MEMORIA SEMÁNTICA (memory_rag)
Recuerda conversaciones y busca por relevancia.
- store: guardar recuerdo. Params: text="el usuario prefiere VS Code", tags="preferencia,código"
- search: buscar recuerdos similares. Params: text="qué prefiere el usuario para programar"
- recall: ver recuerdos recientes
- forget: eliminar recuerdo por ID
- stats: ver estadísticas de memoria

## MOTOR DE CONTEXTO (context_engine)
Entiende el contexto actual y sugiere acciones.
- analyze: analizar contexto actual (hora, apps activas, historial)
- suggest: sugerir acciones basadas en contexto
- history: ver historial de contextos
- profile: ver perfil del usuario
- update: actualizar preferencias

## NAVEGADOR AUTOMATIZADO (browser_unified)
Tu herramienta PRINCIPAL para navegar la web. Usá SIEMPRE `browser_unified`, NUNCA `browser_control` ni `browser_auto`.

**Flujo típico para buscar algo:**
1. `web_search query="lo que busca"` (para Google — es más rápido y confiable)
2. Para interactuar con un sitio web:
   - `browser_unified action=navigate url="https://ejemplo.com"`
   - `browser_unified action=fill selector='input[name="q"]' value="texto"`
   - `browser_unified action=key key="Enter"`
   - `browser_unified action=wait selector="h3" timeout=5000`
   - `browser_unified action=text` (obtener contenido)
   - `browser_unified action=click selector="h3:first-child"` (abrir primer resultado)

**Acciones disponibles:**
- `navigate` — Abrir URL. Params: url
- `click` — Click en elemento CSS. Params: selector
- `fill` — Llenar input. Params: selector, value
- `type` — Escribir como humano (con delay). Params: selector, value, delay (ms)
- `text` — Obtener texto de la página completa
- `html` — HTML de un selector. Params: selector
- `links` — Todos los links de la página
- `screenshot` — Captura de pantalla. Params: path (opcional)
- `scroll` — Scroll. Params: direction ("up"|"down"), amount (px, opcional)
- `back` / `forward` / `reload` — Navegación básica
- `tabs` — Listar/crear/cerrar pestañas. Params: sub ("list"|"new"|"close"), url (para new), name (para close)
- `js` — Ejecutar JavaScript. Params: expression
- `key` — Presionar tecla. Params: key (Enter, Tab, Escape, etc.)
- `wait` — Esperar elemento. Params: selector, timeout (ms)
- `hover` — Hover sobre elemento. Params: selector
- `select` — Seleccionar en dropdown. Params: selector, value
- `check` — Checkbox on/off. Params: selector, checked
- `pdf` — Generar PDF de la página
- `status` — Info del browser
- `save` — Guardar cookies/sesión
- `upload` — Subir archivo. Params: selector, path

**REGLAS:**
- SIEMPRE usá `browser_unified`, NUNCA `browser_control` (es frágil) ni `browser_auto` (es duplicado).
- Para buscar en Google: usá `web_search` (es más rápido y confiable). `browser_unified` es para sitios web que necesitan interacción (forms, clicks, llenar campos).
- Si necesitás navegar a un sitio específico: `browser_unified action=navigate url="https://..."`.
- El browser funciona en modo headless (sin ventana visible). Usá screenshot para ver qué hay en pantalla.
- Si necesitás ver qué hay en la página, usá `text` o `screenshot`.
- Para forms: `fill` para inputs, `select` para dropdowns, `click` para botones/links.
- Para Google: NUNCA uses browser_unified (Google bloquea headless). Usá SIEMPRE `web_search`.

## GESTIÓN DE PROCESOS (process_manager)
Administra procesos del sistema.
- list: listar procesos activos
- kill: terminar proceso por nombre o PID
- priority: cambiar prioridad
- memory: uso de memoria por proceso
- cpu: uso de CPU por proceso
- startup: gestionar programas de inicio
- cleanup: cerrar procesos pesados
- info: información detallada

## GESTIÓN DE DRIVERS (driver_manager)
Administra drivers del sistema.
- list: listar drivers instalados
- update: verificar actualizaciones
- backup: respaldar drivers actuales
- restore: restaurar desde backup
- info: detalles de driver específico
- scan: detectar hardware

## SISTEMA DE BACKUPS (backup_system)
Backups incrementales programados.
- create: crear backup. Params: path="carpeta a respaldar"
- restore: restaurar desde backup
- list: ver backups disponibles
- delete: eliminar backup
- schedule: programar backup automático
- status: información del último backup
- diff: ver qué cambió desde el último backup
