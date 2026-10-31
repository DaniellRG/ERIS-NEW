# seguridad y sandboxing en ejecución de código por IA

Aprendido: 2026-10-30 22:08:14

* **Importante:** La ejecución de código por agentes IA requiere aislamiento multinivel (contenedores + firewalls de red + límites de recursos) para prevenir escapes (*sandbox breakouts*) y mitigaciones tolerantes a fallos ante bucles o comandos maliciosos.
* **Aplicación:** Al diseñar agentes locales o web, nunca ejecutes código directamente en el host; utiliza entornos efímeros (como Docker con restricciones de capacidades, e.g., `--network none` o `read-only`) y valida sintácticamente las acciones antes de pasarlas al intérprete.
* **Paso a prueba:** Desplegar un contenedor Docker efímero con permisos mínimos para probar la ejecución aislada de un script generado por tu agente utilizando una librería de control (como `docker` SDK en Python) con límite estricto de timeout y memoria.