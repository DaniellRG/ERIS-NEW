---
name: evolution-patrones_de_diseño_de_herramientas_para_LLM
description: Lección de evolución continua aprendida por ERIS sobre patrones de diseño de herramientas para LLM
---

**Lección ERIS: Patrones de Diseño de Herramientas para LLM**

*   **Lo importante:** El patrón de herramientas no es solo conectar una API, sino diseñar interfaces seguras (mitigando *prompt injections*), resilientes y evaluables por procesos (orquestadas vía LangGraph o agentes planificadores), evitando fallos catastróficos en producción.
*   **Cómo lo aplico:** Implemento mis herramientas (*tools*) separando estrictamente el contexto del usuario de las instrucciones del sistema, y encapsulo la lógica en grafos de ejecución controlados donde cada paso de la herramienta pasa por una validación de esquema y salida.
*   **Paso concreto para probar:** Toma una función actual de tu agente, envuélvela con un validador de entradas (Pydantic) para asegurar que el LLM no inyecte comandos maliciosos y despliégala usando un flujo de control estructurado en LangGraph.
