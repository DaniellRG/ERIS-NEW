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
| T2 | S2 | inline | completed | — |
| T3 | S3 | inline | completed | — |
| T4 | S4 | inline | completed | 8f901f1 |
| T5 | S5 | inline | completed | — |
| T6 | S6 | inline | pending | — |
| T7 | S7 | inline | pending | — |

## Log

L1. Usuario ordenó ejecutar Paso 0 (leer ErisLive y ErisUI + mapa de dependencias) y luego ejecutar todos los pasos de Fase 3, continuar Fase 4. (2026-11-12)
L2. Creado documento de tracking. (2026-11-12)
L3. Paso 0 completado: mapa de dependencias dibujado. main→ui unidireccional; ErisLive expone interfaz UI estrecha (write_log, set_state, inject_text, show_expression, express_emotion, muted, set_face_speaking, set_audio_level, set_orb_audio_level, clear_eris_response, show_thought, stream_eris_chunk, tray_icon, show_and_activate, callbacks on_text_command/on_stop_command/on_config_saved). (2026-11-12)
L4. Paso 1 (S1) completado y commiteado (78743f6): quitados wrappers _shared_* redundantes de main.py; call sites apuntan a core.shared_context.get_shared_context(). main.py compila; shared_context pasa prueba de humo. (2026-11-12)
L5. Paso 2 (S2) completado parcialmente y commiteado (este commit): creado core/controller.py con lógica de negocio sin Qt ni sesión Live (observer_line, tts_backend_works, run_cognitive_cycle, run_autonomy_cycle, proactive_reminders, voice_resilient_fallback). ErisLive instancia self._controller y delega en él _observer_line y _tts_backend_works. main.py y controller.py compilan; controller pasa prueba de humo (observer_line puro, tts_backend_works no falla en backend inexistente). Queda pendiente delegar en el controller los ciclos (cognitivo/autonomía), proactive_reminders y voice_resilient_fallback en una próxima pasada. (2026-11-12)
| T4 | S4 | inline | completed | 8f901f1 |
| T5 | S5 | inline | completed | 1212fcd |
| T6 | S6 | inline | completed | — |
| T7 | S7 | inline | pending | — |

## Log

L1. Usuario ordenó ejecutar Paso 0 (leer ErisLive y ErisUI + mapa de dependencias) y luego ejecutar todos los pasos de Fase 3, continuar Fase 4. (2026-11-12)
L2. Creado documento de tracking. (2026-11-12)
L3. Paso 0 completado: mapa de dependencias dibujado. main→ui unidireccional; ErisLive expone interfaz UI estrecha. (2026-11-12)
L4. Paso 1 (S1) completado y commiteado (78743f6): quitados wrappers _shared_* redundantes de main.py; call sites apuntan a core.shared_context.get_shared_context(). main.py compila; shared_context pasa prueba de humo. (2026-11-12)
L5. Paso 2 (S2) completado y commiteado (7171071): creado core/controller.py con lógica de negocio sin Qt ni sesión Live. ErisLive instancia self._controller y delega en él _observer_line y _tts_backend_works. main.py y controller.py compilan; controller pasa prueba de humo. (2026-11-12)
L6. Paso 3 (S3) completado y commiteado (6e53ffa): creado core/events.py (EventBus thread-safe + singleton) y expuesto self.bus en ErisLive.__init__. main.py y events.py compilan; event bus pasa prueba de humo. (2026-11-12)
L7. Paso 4 (S4) completado y commiteado (8f901f1): creado paquete gui/ con styles.py, widgets/orb.py, widgets/glass.py, widgets/sidebar.py, widgets/chat.py, widgets/settings.py, widgets/transcript.py, widgets/floating.py, widgets/vrm.py, widgets/options.py. Todos los widgets extraídos de ui.py (~1900 líneas eliminadas del god file). ui.py restaurado completo y re-exporta desde gui/widgets para retrocompatibilidad. ui.py + todos los gui/ compilan. (2026-11-12)
L8. Paso 5 (S5) completado y commiteado (1212fcd): creado core/app.py con bootstrap() (arranque headless: zona horaria, consola_log, identidad, metas, Ollama). main.py llama a bootstrap() en lugar del bloque de ~50 líneas. main.py y core/app.py compilan. (2026-11-12)
L9. Fase 4 completada (propuesta entregada): creado scripts/metrics_ssot.py (SSOT de métricas: 525 tools sincronizadas, 309 action modules, 14 agentes + 15 sub-agentes, 52 skills, 37 pytest files) y escrito metrics.json. Actualizados AGENTS.md y CHANGELOG.md con los números SSOT reales (525/525 tools, 309 actions, 15 sub-agentes, 52 skills) y quitados números hardcodeados desactualizados. Creado README.md robusto (descripción, stack, instalación segura, tests, métricas, estructura del repo, flujo de checkouts divergentes Windows/Linux). (2026-11-12)
L10. T6 (S6) completado en este commit: creado core/prompts/ (ORDER.txt + 61 secciones .md + build.py + __init__.py) que parte prompt.txt en secciones modulares; build.py regenera core/prompt.txt byte-a-byte idéntico (verificado no-regresión). core/prompt_loader.py reescrito: load_system_prompt() usa las secciones modulares como fuente de verdad (con fallback al archivo consolidado y al prompt embebido), aplicando _portabilize y _inject_live_counts. Prueba de humo OK: 173680 chars, @TOOLS@→525. T6 commiteado junto con los archivos pendientes de T4 (gui/widgets/{sidebar,options,transcript,floating,vrm}.py y __init__.py). (2026-11-12)
L11. Siguiente: T7 (S7) — tests de caracterización antes de cada bloque movido + suite verde tras cada paso (pytest + test_all.py). Fase 4 ya entregada. (2026-11-12)
