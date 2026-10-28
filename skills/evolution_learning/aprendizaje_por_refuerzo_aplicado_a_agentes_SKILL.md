---
name: evolution-aprendizaje_por_refuerzo_aplicado_a_agentes
description: Lección de evolución continua aprendida por ERIS sobre aprendizaje por refuerzo aplicado a agentes
---

**Lección ERIS: Aprendizaje por Refuerzo en Agentes**

• **Qué importa:** El ciclo fundamental (Agente, Entorno, Estado, Acción y Recompensa). El agente maximiza su recompensa acumulada interactuando por prueba y error.
• **Cómo aplicarlo:** Define un espacio de estados claro y una función de recompensa estricta que penalice errores y premie el objetivo. Usa algoritmos base como *Q-Learning* para actualizar la tabla de decisiones ($Q$-table) según la regla de Bellman.
• **Paso concreto:** Implementa un entorno simple en Python (ej. una cuadrícula 3x3 con Gym o código propio) donde tu agente deba llegar a una meta evitando obstáculos, e imprime la evolución de su recompensa tras 100 episodios.
