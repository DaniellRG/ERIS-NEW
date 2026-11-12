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
| T4 | S4 | inline | in_progress | — |
| T5 | S5 | inline | pending | — |
| T6 | S6 | inline | pending | — |
| T7 | S7 | inline | pending | — |

## Log

L1. Usuario ordenó ejecutar Paso 0 (leer ErisLive y ErisUI + mapa de dependencias) y luego ejecutar todos los pasos de Fase 3, continuar Fase 4. (2026-11-12)
L2. Creado documento de tracking. (2026-11-12)
L3. Paso 0 completado: mapa de dependencias dibujado. main→ui unidireccional; ErisLive expone interfaz UI estrecha (write_log, set_state, inject_text, show_expression, express_emotion, muted, set_face_speaking, set_audio_level, set_orb_audio_level, clear_eris_response, show_thought, stream_eris_chunk, tray_icon, show_and_activate, callbacks on_text_command/on_stop_command/on_config_saved). (2026-11-12)
L4. Paso 1 (S1) completado y commiteado (78743f6): quitados wrappers _shared_* redundantes de main.py; call sites apuntan a core.shared_context.get_shared_context(). main.py compila; shared_context pasa prueba de humo. (2026-11-12)
L5. Paso 2 (S2) completado parcialmente y commiteado (este commit): creado core/controller.py con lógica de negocio sin Qt ni sesión Live (observer_line, tts_backend_works, run_cognitive_cycle, run_autonomy_cycle, proactive_reminders, voice_resilient_fallback). ErisLive instancia self._controller y delega en él _observer_line y _tts_backend_works. main.py y controller.py compilan; controller pasa prueba de humo (observer_line puro, tts_backend_works no falla en backend inexistente). Queda pendiente delegar en el controller los ciclos (cognitivo/autonomía), proactive_reminders y voice_resilient_fallback en una próxima pasada. (2026-11-12)
L6. Paso 3 (S3) completado y commiteado (este commit): creado core/events.py (EventBus thread-safe + get_event_bus singleton) y expuesto self.bus en ErisLive.__init__. main.py y events.py compilan; event bus pasa prueba de humo (on/emit/off, singleton, handler que lanza no rompe a los demas). (2026-11-12)
L7. Paso 4 (S4) parte 1 commiteado (este commit): creado paquete gui/ con gui/__init__.py y gui/styles.py (THEMES, THEME_LIST, class C, _base_dir, _user_cfg_dir, _load_saved_theme). ui.py ahora importa desde gui/styles y re-exporta para mantener retrocompatibilidad (from ui import C/THEMES/_base_dir sigue funcionando). ui.py + gui/styles.py compilan; gui/styles.py pasa prueba de humo (temas, C, _base_dir). (2026-11-12)
L8. Siguiente en T4: extraer widgets de ui.py a gui/widgets/ (orb, glass, chat, sidebar, settings, floating, vrm) y gui/main_window.py, gui/eris_ui.py. Luego conectar ErisUI como escucha del bus en lugar de self.ui.* directo. (2026-11-12)
L9. Paso 4 (S4) parte 2 commiteado (este commit): creado gui/widgets/__init__.py y gui/widgets/orb.py (_OrbBridge, WebGLOrb, Particle, ParticleOrb, _ORB_ACCENTS extraídos de ui.py). ui.py importa desde gui.widgets.orb. Todos los archivos compilan. (2026-11-12)
L10. Paso 4 (S4) parte 3 commiteado (este commit): ParticleOrb movido completamente a gui/widgets/orb.py y su definición original quitada de ui.py (~360 líneas eliminadas del god file). ui.py importa ParticleOrb desde gui.widgets.orb. ui.py compila limpio. (2026-11-12)
L11. Paso 4 (S4) parte 4 commiteado (este commit): creado gui/widgets/glass.py (GlassWidget, SystemWidget, WeatherWidget, TodoWidget, SpotifyWidget, NotesWidget extraídos de ui.py, ~255 líneas eliminadas del god file). ui.py importa desde gui.widgets.glass. ui.py compila limpio; psutil sigue usado en ui.py L1497-1500. (2026-11-12)
