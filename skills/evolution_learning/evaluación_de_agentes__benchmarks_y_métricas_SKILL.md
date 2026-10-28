---
name: evolution-evaluación_de_agentes__benchmarks_y_métricas
description: Lección de evolución continua aprendida por ERIS sobre evaluación de agentes: benchmarks y métricas
---

¡Entendido! Aquí tienes tu lección rápida para seguir mejorando:

* **Lo importante:** Evaluar agentes requiere ir más allá de la precisión del LLM; hay que medir su autonomía, uso de herramientas, eficiencia en costos y éxito en tareas multi-paso (como en benchmarks recientes *Efficient Benchmarking*).
* **Cómo aplicarlo:** Integra un framework de evaluación en tu loop de desarrollo (ej. usando métricas de éxito binario por tarea, latencia acumulada y número de llamadas a herramientas antes de converger).
* **Paso concreto:** Añade un log de prueba en tu agente actual que mida el **costo total por ejecución** (tokens) y el **porcentaje de éxito** en 5 corridas de una misma tarea.
