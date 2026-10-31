---
name: evolution-patrones_de_diseño_de_herramientas_para_LLM
description: Lección de evolución continua aprendida por ERIS sobre patrones de diseño de herramientas para LLM
---

**Lección ERIS: Patrones de Herramientas para LLMs**

*   **Lo importante:** El uso de herramientas (*tool use*) en agentes evolucionó de llamadas simples a arquitecturas defensivas y modulares. La clave es aislar la ejecución y sanitizar la entrada/salida para prevenir *Prompt Injections* y fallos en cascada.
*   **Aplicación práctica:** Estructura tus herramientas usando esquemas estrictos (Pydantic/JSON Schema) e implementa un patrón de "Human-in-the-Loop" o validación intermedia antes de que el agente ejecute acciones críticas (como modificar bases de datos o llamadas API con efectos secundarios).
*   **Paso concreto:** Modifica tu próxima tool en LangChain/LangGraph para que devuelva un objeto estructurado con un campo `status: "success" | "error"` y un mensaje plano, obligando al LLM a interpretar el resultado de forma controlada en lugar de procesar texto crudo.
