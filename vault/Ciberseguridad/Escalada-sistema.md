# Escalada — sistema

Nivel: 3/8

- Auditoria completa de Eris: verifique codigo+estado+runtime y detecte 5 fallas ALTAS (2 agentes muertos deploy/system_monitor, 2 imports rotos session_search/project_manager, 2 tools fantasma screen_vision/calc_test, docs desactualizadas) + 8 MEDIAS (huerfanos, imports rotos, Hermes a medio terminar, opencode_bridge duplicado, features off, eris_workspace abandonado, loop de key, conteo None) + bajas
- Arregle las 5 fallas ALTAS de la auditoria de Eris (con OK del dueno): (A1) quite los agentes muertos deploy/system_monitor; (A2) cree core/session_search.py; (A3) cree actions/project_manager.py; (A4) guarde el import de mss en screen_vision y borre la tool fantasma calc_test; (A5) actualice AGENTS.md con los numeros reales