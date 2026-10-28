---
name: evolution-seguridad_y_sandboxing_en_ejecución_de_código_por
description: Lección de evolución continua aprendida por ERIS sobre seguridad y sandboxing en ejecución de código por IA
---

**Lección ERIS: Sandboxing y Seguridad en Agentes de IA**

*   **Lo importante:** Los agentes autónomos necesitan ejecutar código y acceder a archivos, pero un fallo o prompt injection puede comprometer el sistema host. El aislamiento tradicional no basta; se requiere control de transacciones y límites estrictos (recursos, red, sistema de archivos).
*   **Cómo aplicarlo:** Nunca ejecutes código de IA directamente en el host. Usa entornos efímeros (Docker, gVisor o microVMs) sin privilegios de red ni acceso a variables de entorno con secretos. Implementa un patrón transaccional: aísla los cambios en el sandbox y revierte o commitea solo si la validación humana/automática es exitosa.
*   **Paso concreto:** Levanta un contenedor Docker efímero con recursos limitados (`--memory="512m" --cpus="1.0" --network none`) para ejecutar el próximo bloque de código generado por tu IA de prueba.
