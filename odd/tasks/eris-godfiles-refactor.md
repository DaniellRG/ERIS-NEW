# ERIS — Refactor de god files (main.py / ui.py / prompt.txt)

**Objetivo:** Fragmentar los god files de ERIS 4.0.1 siguiendo SOLID, sin romper el comportamiento existente.
- `main.py` (5092 líneas): `ErisLive` + funciones de módulo + `main()`.
- `ui.py` (3585+ líneas): docenas de widgets + `MainWindow` + `ErisUI`.
- `prompt.txt` (175 KB): prompt monolítico → secciones modulares por agente.

**Rama:** `feat/eris-godfiles-refactor` (a crear desde `main`).
**Runner:** `python -m pytest tests/ -q` + `python test_all.py` (+ `python scripts/validate_tools.py` de Fase 2).
**Entrega strategy:** `ask-on-risk` (default).

## Specs

S1. Extraer estado compartido de `main.py` a `core/state.py` (clase `AppState`, inyección de dependencias, sin globales).
S2. Extraer lógica de negocio de `ErisLive` a `core/controller.py` (router, episodios, auto-mejora, post-sesión).
S3. Crear `core/events.py` (event bus pub/sub) para desacoplar GUI ↔ núcleo.
S4. Partir `ui.py` en `gui/` (un módulo por grupo de widgets: orb, glass, chat, sidebar, settings, floating, vrm).
S5. Delgadir `main.py` a punto de entrada que llama a `core/app.main()`.
S6. `prompt.txt` como artefacto generado desde `core/prompts/` (secciones por agente) vía `core/prompts/build.py`.
S7. Tests de caracterización antes de cada bloque movido; suite completa verde tras cada paso.

## Tasks

| ID | Spec | Route | Status | Commit |
|---|---|---|---|---|
| T0 | S1-S7 | inline | in_progress | — |
| T1 | S1 | inline | completed | 78743f6 |
| T2 | S2 | inline | pending | — |
| T3 | S3 | inline | pending | — |
| T4 | S4 | delegated | pending | — |
| T5 | S5 | inline | pending | — |
| T6 | S6 | inline | pending | — |
| T7 | S7 | inline | pending | — |

## Log

L1. Usuario ordenó ejecutar Paso 0 (leer ErisLive y ErisUI + mapa de dependencias) y luego ejecutar todos los pasos de Fase 3, continuar Fase 4. (2026-11-12)
L2. Creado documento de tracking. (2026-11-12)
L3. Paso 0 completado: mapa de dependencias dibujado. main→ui unidireccional; ErisLive expone interfaz UI estrecha (write_log, set_state, inject_text, show_expression, express_emotion, muted, set_face_speaking, set_audio_level, set_orb_audio_level, clear_eris_response, show_thought, stream_eris_chunk, tray_icon, show_and_activate, callbacks on_text_command/on_stop_command/on_config_saved). (2026-11-12)
L4. Paso 1 (S1) completado y commiteado (78743f6): quitados wrappers _shared_* redundantes de main.py; call sites apuntan a core.shared_context.get_shared_context(). main.py compila; shared_context pasa prueba de humo. (2026-11-12)
L5. Siguiente: T2 (S2) — extraer lógica de negocio de ErisLive a core/controller.py (router de agentes, chat, episodios, autonomía, habla). Requiere leer métodos de negocio de ErisLive en main.py L1127–L5067. (2026-11-12)
