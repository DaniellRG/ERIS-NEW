# B3 — Puente Hermes: unificar y helper ausente

## 1. Puertos y módulos
- `core/hermes_bridge.py`: 6790 (activo, usado por Eris)
- `core/opencode_bridge.py`: 6789 (separado, arranque comentado en main). Diferentes puertos → conviven. No conflicto.

## 2. Endpoints vs consumo de Eris
Eris consume: `/api/task` (POST), `/api/response/{id}` (GET/poll), `/api/ask` (POST), `/api/learn` (POST), `/api/status` (GET). `/api/query` **no aparece** en código ni llamadas. El contrato actual es suficiente.

## 3. Unificación
`hermes_bridge.py` implementa API completa y herramientas cliente (`consultar_a_hermes`, `enviar_a_hermes`, `herramienta_eris`). `opencode_bridge.py` es puente separado (otro propósito). No es necesario fusionar: puertos distintos, propósitos distintos. Mantener ambos con responsabilidades claras (no crear alias confusos que rompan registro). Canónico: **hermes_bridge.py** en 6790 para Hermes↔Eris.

## 4. Helper ausente
Creado `tools/hermes_helper.py` con interfaz documentada por AGENTS.md: flags `--status`, `--task`, `--pregunta` (posicional), compatibles con descripción. Compila OK.

## 5. Verificación
- py_compile: core/hermes_bridge.py, core/opencode_bridge.py, tools/hermes_poll.py, tools/hermes_helper.py → OK
- Prueba end-to-end (puente 6790):
  - start_bridge OK, bridge_up True
  - POST /api/task → task_id devuelto
  - cola real (sin eco), respuesta vía send_response_to_eris + respuesta_{id}.json
- API existente cubre contrato; `/api/query` no requerido.

## Conclusión
Puente único canónico en 6790 (hermes_bridge). Helper CLI creado. Ambos bridges conviven sin conflicto. No se tocan firmas públicas ni registro (507/507).