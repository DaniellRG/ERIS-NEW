---
name: evolution-técnicas_de_razonamiento_en_cadena__chain-of-thoug
description: Lección de evolución continua aprendida por ERIS sobre técnicas de razonamiento en cadena (chain-of-thought) modernas
---

**LECCIÓN ERIS: Razonamiento en Cadena (CoT) Moderno**

*   **Lo importante:** El CoT moderno ya no es solo pedir "piensa paso a paso", sino guiar estratégicamente al LLM mediante la descomposición dinámica de problemas, validación intermedia y *Self-Consistency* (generar múltiples rutas y votar la mejor).
*   **Aplicación en código/agentes:** En tus pipelines, estructura las llamadas en dos fases: 
    1. Forzar al agente a generar un bloque `<scratchpad>` con los pasos lógicos y suposiciones antes de la respuesta final.
    2. Implementar un nodo de validación o reintentos si la cadena detecta inconsistencias matemáticas o lógicas.
*   **Paso para probarlo hoy:** Modifica el prompt de tu agente principal añadiendo: *"Antes de dar la respuesta final, genera una cadena de razonamiento estructurada en 3 hipótesis alternativas y selecciona la más coherente"*.
