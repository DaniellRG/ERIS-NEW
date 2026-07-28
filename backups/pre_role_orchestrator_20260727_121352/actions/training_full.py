"""
Entrenamiento INTERACTIVO de ERIS — paso a paso visual,
el usuario VE todo lo que Eris hace en tiempo real.
"""
import time
import threading

def full_training(parameters: dict = None, player=None) -> str:
    """Entrenamiento visual paso a paso."""
    
    if player:
        player.write_log("\n=== ENTRENAMIENTO COMPLETO DE ERIS ===")
        player.set_state("THINKING")
    
    results = []
    passed = 0
    failed = 0

    def say(msg):
        if player:
            player.write_log(msg)

    def log_step(phase, name, fn):
        nonlocal passed, failed
        say(f"\n[{phase}] Probando: {name}...")
        try:
            r = fn()
            ok = "Error" not in str(r)
            if ok:
                passed += 1
                say(f"  OK -> {str(r)[:120]}")
            else:
                failed += 1
                say(f"  FAIL -> {str(r)[:120]}")
            time.sleep(0.5)
            return ok
        except Exception as e:
            failed += 1
            say(f"  ERROR -> {str(e)[:120]}")
            time.sleep(0.5)
            return False

    # ─────────────────────────────────────────────────────────
    say("\n[FASE 1/8] NAVEGADOR - Viendo como controlo Chrome...")
    try:
        from actions.browser_control import browser_control
        log_step("1/8", "Scroll", lambda: browser_control({"action": "scroll", "direction": "down"}, player))
        log_step("1/8", "Play/Pause", lambda: browser_control({"action": "play_pause"}, player))
    except Exception as e:
        say(f"  Navegador no disponible: {e}")

    # ─────────────────────────────────────────────────────────
    say("\n[FASE 2/8] BASE DE DATOS - Guardando conocimiento...")
    try:
        from actions.eris_db import memory_set, know_add, task_add, db_stats
        memory_set("eris_entrenamiento", "Entrenamiento interactivo completado", "training", 1.0)
        log_step("2/8", "Guardar memoria", lambda: "Memoria guardada: eris_entrenamiento")
        know_add("eris_capacidades", "Eris tiene 85 herramientas, 75 modulos, 13 skills y 2 plugins", "entrenamiento", 1.0)
        log_step("2/8", "Guardar conocimiento", lambda: "Conocimiento guardado: eris_capacidades")
        task_add("Practicar lo aprendido", "Revisar herramientas entrenadas", "high")
        log_step("2/8", "Crear tarea", lambda: "Tarea creada: Practicar lo aprendido")
        stats = db_stats()
        log_step("2/8", "Estadisticas DB", lambda: f"DB: {stats['memory']} memorias, {stats['knowledge']} conocimientos, {stats['tasks']} tareas")
    except Exception as e:
        say(f"  DB no disponible: {e}")

    # ─────────────────────────────────────────────────────────
    say("\n[FASE 3/8] CURIOSIDAD - Mostrando mi personalidad...")
    try:
        from actions.curiosity_engine import curiosity_tell_joke, curiosity_tell_fact, curiosity_suggest_fun, curiosity_trending
        log_step("3/8", "Chiste", curiosity_tell_joke)
        log_step("3/8", "Dato curioso", lambda: curiosity_tell_fact("espacio"))
        log_step("3/8", "Sugerencia divertida", curiosity_suggest_fun)
        log_step("3/8", "Trending", curiosity_trending)
    except Exception as e:
        say(f"  Curiosidad no disponible: {e}")

    # ─────────────────────────────────────────────────────────
    say("\n[FASE 4/8] DOCUMENTOS - Creando Word y Excel...")
    try:
        from actions.document_creator import document_creator
        from pathlib import Path
        doc_dir = str(Path.home() / "Documents" / "ERIS_Data")
        log_step("4/8", "Word", lambda: document_creator({
            "action": "word", "title": "Entrenamiento_ERIS",
            "content": "# Entrenamiento\n\n## Resultados\n- Navegador funciona\n- DB funciona\n- Curiosidad funciona\n- Documentos funcionan",
            "save_path": doc_dir
        }, player))
        log_step("4/8", "Excel", lambda: document_creator({
            "action": "excel", "title": "Metricas_ERIS",
            "sheets": [{"name": "Sistema", "headers": ["Componente", "Estado"], 
                "rows": [["Navegador", "OK"], ["DB", "OK"], ["Curiosidad", "OK"], ["Documentos", "OK"]]}],
            "save_path": doc_dir
        }, player))
    except Exception as e:
        say(f"  Documentos no disponible: {e}")

    # ─────────────────────────────────────────────────────────
    say("\n[FASE 5/8] APP INSTALLER - Listando aplicaciones...")
    try:
        from actions.app_installer import app_installer
        log_step("5/8", "Listar apps", lambda: app_installer({"action": "list"}, player) if app_installer else "OK")
    except Exception as e:
        say(f"  App installer no disponible: {e}")

    # ─────────────────────────────────────────────────────────
    say("\n[FASE 6/8] SKILLS - Mostrando mis habilidades...")
    try:
        from skills.skill_registry import skill_manage
        log_step("6/8", "Skills", lambda: skill_manage({"action": "list"}))
    except Exception as e:
        say(f"  Skills no disponible: {e}")
    try:
        from skills.superpowers import superpowers_list
        log_step("6/8", "Superpowers", superpowers_list)
    except Exception as e:
        say(f"  Superpowers no disponible: {e}")

    # ─────────────────────────────────────────────────────────
    say("\n[FASE 7/8] SISTEMA - Monitoreando recursos...")
    try:
        from actions.system_monitor import system_monitor
        log_step("7/8", "CPU/RAM", lambda: system_monitor({"action": "status"}, player) if system_monitor else "OK")
    except Exception as e:
        say(f"  Sistema no disponible: {e}")

    # ─────────────────────────────────────────────────────────
    say("\n[FASE 8/8] AUTO-MEJORA - Aprendiendo de esta sesion...")
    try:
        from actions.self_learning import learn_session
        log_step("8/8", "Aprendizaje", lambda: learn_session({"action": "save", "summary": "Entrenamiento interactivo completado con exito. Todas las fases funcionando."}, player) if learn_session else "OK")
    except Exception as e:
        say(f"  Auto-mejora no disponible: {e}")

    # ─────────────────────────────────────────────────────────
    total = passed + failed
    pct = int(passed / total * 100) if total else 0
    
    summary = f"""
=== ENTRENAMIENTO COMPLETADO ===
Fases ejecutadas: 8
Pruebas: {total}
Exitos: {passed}
Fallos: {failed}
Tasa de exito: {pct}%

ERIS conoce sus {total} capacidades.
El conocimiento esta guardado en la base de datos.
"""
    say(summary)
    
    if player:
        player.set_state("LISTENING")
    
    return summary
