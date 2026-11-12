# ERIS — Refactor de god files + Seguridad (Fase 3 + Fase 4 + Seguridad)

**Objetivo:** Fragmentar los god files de ERIS 4.0.1 siguiendo SOLID, aplicar parches de seguridad críticos y establecer CI/CD, sin romper el comportamiento existente.

**Rama:** main (commiteado directamente)
**Runner:** python -m pytest tests/ -q + python test_all.py

## Specs

S1. Extraer estado compartido de main.py a core/state.py (clase AppState, inyección de dependencias, sin globales).
S2. Extraer lógica de negocio de ErisLive a core/controller.py (router, episodios, auto-mejora).
S3. Crear core/events.py (event bus pub/sub) para desacoplar GUI ↔ núcleo.
S4. Partir ui.py en gui/ (un módulo por grupo de widgets: orb, glass, chat, sidebar, settings, floating, vrm, options).
S5. Delgadir main.py a punto de entrada que llama a core/app.main().
S6. prompt.txt como artefacto generado desde core/prompts/ (secciones por agente) vía core/prompts/build.py.
S7. Tests de caracterización antes de cada bloque movido; suite completa verde tras cada paso.

S8. Seguridad F-01: mobile_server bind 127.0.0.1 + Bearer auth en /chat.
S9. Seguridad F-02: api_server bind 127.0.0.1 (era 0.0.0.0).
S10. Seguridad F-03: WebSocket bind 127.0.0.1 (era 0.0.0.0).
S11. Seguridad F-04: permission_gate no auto-aprueba riesgo medio sin UI.
S12. Seguridad F-05: shell_session lista blanca de comandos seguros.
S13. Seguridad F-06: code_sandbox y calculator sin eval crudo (AST restringido).
S14. CI/CD: .github/workflows/ci.yml + scripts/ci_seed.py.

## Tasks

| ID | Spec | Route | Status | Commit |
|---|---|---|---|---|
| T1 | S1 | inline | completed | 78743f6 |
| T2 | S2 | inline | completed | 7171071 |
| T3 | S3 | inline | completed | 6e53ffa |
| T4 | S4 | inline | completed | 8f901f1 |
| T5 | S5 | inline | completed | 1212fcd |
| T6 | S6 | inline | completed | 6c70349 |
| T7 | S7 | inline | completed | 99ee991 |
| T8 | S8-S10 | inline | completed | a05cb2e |
| T9 | S11-S13 | inline | completed | — |
| T10 | S14 | inline | completed | — |

## Log

L1. Usuario ordenó ejecutar Paso 0 (leer ErisLive y ErisUI + mapa de dependencias) y luego ejecutar todos los pasos de Fase 3, continuar Fase 4. (2026-11-12)
L2. Paso 0 completado: mapa de dependencias dibujado. main→ui unidireccional. (2026-11-12)
L3. Paso 1 (S1) completado y commiteado (78743f6): quitados wrappers _shared_* redundantes de main.py. (2026-11-12)
L4. Paso 2 (S2) completado y commiteado (7171071): creado core/controller.py con lógica de negocio sin Qt ni sesión Live. (2026-11-12)
L5. Paso 3 (S3) completado y commiteado (6e53ffa): creado core/events.py (EventBus) y expuesto self.bus en ErisLive.__init__. (2026-11-12)
L6. Paso 4 (S4) completado y commiteado (8f901f1): creado paquete gui/ con styles.py y widgets (orb, glass, sidebar, chat, settings, transcript, floating, vrm, options). ui.py restaurado y re-exporta desde gui/widgets. (2026-11-12)
L7. Paso 5 (S5) completado y commiteado (1212fcd): creado core/app.py con bootstrap(). (2026-11-12)
L8. Fase 4 completada y commiteado (e29abff): creado scripts/metrics_ssot.py, metrics.json, README.md. Actualizados AGENTS.md y CHANGELOG.md con números SSOT reales. (2026-11-12)
L9. Paso 6 (S6) completado y commiteado (6c70349): creado core/prompts/ (61 secciones + build.py). core/prompt_loader.py reescrito para usar secciones modulares. (2026-11-12)
L10. Paso 7 (S7) completado y commiteado (99ee991): creado tests/test_fase3_characterization.py (9 tests de caracterización). test_all.py compila. (2026-11-12)
L11. Seguridad F-01 a F-03 completada y commiteada (a05cb2e): mobile_server bind 127.0.0.1 + Bearer auth en /chat; api_server y WebSocket bind 127.0.0.1. (2026-11-12)
L12. Seguridad F-04 a F-06 completada en working tree: permission_gate no auto-aprueba riesgo medio; shell_session lista blanca de comandos; code_sandbox y calculator sin eval crudo (AST restringido). Pendiente de commit. (2026-11-12)
L13. CI/CD completado en working tree: .github/workflows/ci.yml (Windows + Linux, Python 3.14, validate_tools + pytest + test_all) y scripts/ci_seed.py para clon fresco. Pendiente de commit. (2026-11-12)
