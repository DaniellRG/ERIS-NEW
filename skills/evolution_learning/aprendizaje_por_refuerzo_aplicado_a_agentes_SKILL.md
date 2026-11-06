---
name: evolution-aprendizaje_por_refuerzo_aplicado_a_agentes
description: Lección de evolución continua aprendida por ERIS sobre aprendizaje por refuerzo aplicado a agentes
---

**Lección ERIS: Aprendizaje por Refuerzo en Agentes**

• **Qué es lo importante:** El agente aprende mediante prueba y error maximizando recompensas (*reward shaping*), clave hoy para entrenar modelos a usar herramientas, navegar GUIs o sintetizar experiencias (*AgentFly*, *SkillGraph*).
• **Cómo lo aplico en mi código:** Define un entorno claro (estado, acción, recompensa) y desacopla la lógica del agente de un *verifier* o módulo de validación multimodal que evalúe si la tarea se completó antes de actualizar la política.
• **Paso concreto para probarlo:** Clona el repo base (`victory06/TFM` o un entorno simple de GridWorld en `DiploDatos/AprendizajePorRefuerzos`), implementa una función de recompensa binaria (1 si acierta, 0 si falla) y entrena un agente tabular básico por 100 episodios.
