# optimización de contexto y ventana de tokens

Aprendido: 2026-10-31 07:07:09

**Lección ERIS: Optimización de Contexto y Ventana de Tokens**

*   **Lo importante:** La ventana de contexto es finita y costosa. Las técnicas modernas (como *LongRoPE* para expandir tokens y *MemoSight* para compresión) evitan el desbordamiento en agentes mediante la gestión inteligente del historial y la poda de información irrelevante.
*   **Aplicación en código:** Implementa un sistema de memoria deslizante (*sliding window*) o compresión de contexto en tus agentes. En lugar de pasar todo el historial de chat, resume los turnos anteriores y conserva solo los artefactos críticos y las instrucciones recientes.
*   **Paso concreto:** Configura un límite estricto de tokens de entrada en tu agente actual e integra un middleware básico que detecte cuando el prompt supere el 70% de la capacidad, recortando automáticamente los mensajes intermedios más antiguos.