# Reconstrucción del puente Eris ↔ Hermes (29-30 Sep)

El puente fue borrado (hermes_bridge.py, tools/hermes_poll.py) durante la corrida de entrenamiento masivo (321 sesiones en training/). Logré reconstruirlo desde el .pyc (core/__pycache__/hermes_bridge.cpython-314.pyc) y de mi memoria de los fixes.

## Estado
- hermes_bridge.py reconstruido y verificado bytecode vs pyc (24 funciones idénticas, 1 diff irrelevante en id de objeto en const). El único diff es el offset del código compilado (linea de genexpr), comportamiento idéntico.
- tools/hermes_poll.py recuperado (lado Hermes: lee preguntas y responde).
- Los 4 fixes críticos que aplicamos siguen vivos en archivos versionados: hermes_consult registrado, _INBOX_DIR fix, alias-check de test_all.py, Callable import en registry. El puente reconstruido trae los otros 5 (cola real, no eco, respuesta_*.json para inyección en vivo, outbox para recuperación, aliases task/response).

## Prueba end-to-end
- start_bridge OK, status OK (puerto 6790)
- preguntar -> queda en cola (no se responde solo a sí mismo)
- responder con send_response_to_eris -> ERIS recibe respuesta REAL
- escribe respuesta_{id}.json para _hermes_loop (inyección en vivo)
- cola de preguntas se marca answered

## Lo que NO toqué
- 4 implementaciones de puente paralelas (core/hermes_bridge.py vivo, core/opencode_bridge.py comentado-arranque, agents/opencode_bridge.py copia, hermes_tools dispatcher). Decisión para Eris.
- hermes_tools.py: 455 líneas, 8 de 12 duplican tools existentes, 3 únicas. No registrado.
- Contadores: AGENTS.md dice 526, tabla 507, inventario 526, real 504.

## Decision
El puente vuelve a existir y es funcional. La limpieza/normalización de duplicados queda como decisión de Eris (ya le fue comunicada por data/hermes_tasks.json).
