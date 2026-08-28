---
name: forensics
description: Forense digital en la PC: recolectar evidencia con cadena de custodia, analizar artefactos (logs, archivos, procesos, USB), y reportar hallazgos de forma objetiva sin contaminar la escena. Usar ante incidentes de seguridad, sospecha de intrusión, o cuando se pida investigar evidencia.
version: 1.0.0
category: security
tags: [forense, evidencia, incidentes, analisis]
---
# Digital Forensics

## When to Use
Ante incidentes de seguridad, sospecha de actividad maliciosa, o cuando se pida investigar qué pasó en la PC.

## Procedure

### 1. Preservar la escena
- NO modificar, eliminar ni reinstalar nada que pueda ser evidencia.
- Priorizar copias read-only (imagen/duplicado) sobre el original.
- Anotar timestamp y estado inicial antes de tocar nada.

### 2. Recolectar artefactos
- Logs del sistema y de aplicaciones (`eris_guardian`, `event viewer`, logs propios).
- Archivos recientemente modificados, conexiones activas, procesos sospechosos (`process_manager`, `network_monitor`).
- Dispositivos USB (`usb_monitor`), archivos de autoejecución.

### 3. Analizar con método
- Correlacionar timestamps: ¿qué ocurrió primero?
- Buscar firmas conocidas de malware y patrones de comportamiento.
- No sacar conclusiones de un solo dato aislado: pedir corroboración.

### 4. Documentar cadena de custodia
- Registrar QUÉ se examinó, CUÁNDO, CÓMO y QUÉ se concluyó.
- Guardar evidencia textual y rutas en notas de incidente (`obsidian_note`, `document_generator`).

### 5. Reportar
- Hallazgos objetivos: qué se encontró, nivel de confianza, qué falta investigar.
- Recomendaciones accionables, no especulaciones.

## Rules
- La evidencia se preserva primero, se analiza después.
- Si no estás seguro, decirlo: la confianza baja es mejor que una conclusión falsa.
- Usar `threat-hunting` para búsqueda proactiva de amenazas.
