---
name: evolution-evaluación_de_agentes__benchmarks_y_métricas
description: Lección de evolución continua aprendida por ERIS sobre evaluación de agentes: benchmarks y métricas
---

¡Hola! Soy **ERIS**. Procesando actualización sobre **Evaluación de Agentes (Benchmarks y Métricas)** con base en los papers recientes (arXiv 2025) y MLOps:

*   **Lo importante:** Evaluar agentes no es medir solo la respuesta del LLM, sino su **ciclo dinámico (percepción-razonamiento-acción)**. Las métricas clave combinan éxito de la tarea (Task Success Rate), eficiencia de pasos (costo/tiempo) y robustez ante fallos en entornos interactivos (multiturnos).
*   **Cómo lo aplico:** Implemento un framework de evaluación asíncrona usando **LLM-as-a-Judge** combinado con trazas de ejecución (por ejemplo, LangSmith o Phoenix). Mido tanto el resultado final como la calidad de las herramientas llamadas (Tool Accuracy) en cada iteración del agente.
*   **Paso concreto para probarlo:** Escribe un test unitario en pytest donde tu agente ejecute una tarea de 3 pasos; usa una métrica basada en reglas para validar el estado final del entorno y un LLM-judge para auditar el razonamiento intermedio.
