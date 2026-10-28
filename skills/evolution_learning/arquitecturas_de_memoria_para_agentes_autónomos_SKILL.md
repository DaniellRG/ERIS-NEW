---
name: evolution-arquitecturas_de_memoria_para_agentes_autónomos
description: Lección de evolución continua aprendida por ERIS sobre arquitecturas de memoria para agentes autónomos
---

* **Lo importante:** Las arquitecturas modernas (como MEMTIER, Memoria y jerarquías de Computer Architecture) demuestran que un agente autónomo no debe tratar toda la información por igual; requiere una **memoria multinivel (Tiered/Recursive)** que segmente contexto inmediato, memoria episódica y repositorio persistente para evitar la saturación y reducir costos.
* **Cómo lo aplico:** Implementaré una estructura en tres capas en mis bucles de ejecución: 1) *Working Memory* (buffer de ventana de contexto acotado), 2) *Experiential/Episodic Memory* (vector DB para recuperar experiencias pasadas relevantes mediante similitud), y 3) *Archival/Tiered Storage* (base de datos relacional/KV para estado global). Añadiré un mecanismo de auto-evolución (estilo EvolveMem) para podar y consolidar memorias periódicamente.
* **Paso concreto:** Modificaré mi gestor de contexto actual para separar el prompt del sistema y las últimas 5 interacciones (Working) del historial histórico, integrando una consulta básica a una base vectorial antes de cada llamada al LLM para inyectar solo los 3 recuerdos más afines a la tarea actual.
