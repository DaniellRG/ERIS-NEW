---
name: evolution-optimización_de_contexto_y_ventana_de_tokens
description: Lección de evolución continua aprendida por ERIS sobre optimización de contexto y ventana de tokens
---

**Lección ERIS: Optimización de Contexto y Ventana de Tokens**

*   **Lo importante:** La ventana de contexto es limitada y costosa. Investigaciones como *LongRoPE* y *YaRN* muestran que expandirla requiere ajustar las posiciones (RoPE), mientras que la compresión (ej. *MemoSight*) evita procesar ruido innecesario mediante resúmenes dinámicos.
*   **Aplicación en código/agentes:** Implementa *token trimming* en tus agentes: trunca historiales largos de chat, descarta prompts del sistema redundantes y usa embeddings locales para recuperar solo los fragmentos de documentos estrictamente necesarios (RAG) antes de llamar al LLM.
*   **Paso concreto para probarlo:** Cuenta los tokens exactos de tu prompt actual usando la librería `tiktoken` en Python y recorta un 30% del contenido irrelevante antes de enviarlo a la API.
