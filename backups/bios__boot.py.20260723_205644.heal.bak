import os
import sys
import json
import time
import threading
import traceback

_BIOS_DIR = os.path.dirname(os.path.abspath(__file__))
_APP_DIR = os.path.dirname(_BIOS_DIR)

_CRASH_COUNT_FILE = os.path.join(_APP_DIR, "memory", "bios_crash_count.json")

def _load_rules():
    rules_path = os.path.join(_BIOS_DIR, "rules.json")
    try:
        with open(rules_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"rules": {}}

def _bios_banner():
    print("[BIOS] ERIS BIOS v1 — iniciando secuencia de arranque...")

def _get_crash_count():
    try:
        os.makedirs(os.path.dirname(_CRASH_COUNT_FILE), exist_ok=True)
        if os.path.isfile(_CRASH_COUNT_FILE):
            with open(_CRASH_COUNT_FILE, "r", encoding="utf-8") as f:
                return json.load(f).get("count", 0)
    except Exception:
        pass
    return 0

def _increment_crash_count():
    try:
        os.makedirs(os.path.dirname(_CRASH_COUNT_FILE), exist_ok=True)
        count = _get_crash_count() + 1
        tmp = _CRASH_COUNT_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"count": count, "last": time.time()}, f)
        os.replace(tmp, _CRASH_COUNT_FILE)
        return count
    except Exception:
        return 0

def _reset_crash_count():
    try:
        if os.path.isfile(_CRASH_COUNT_FILE):
            os.remove(_CRASH_COUNT_FILE)
    except Exception:
        pass

def _check_previous_crash():
    count = _get_crash_count()
    if count >= 3:
        print(f"[BIOS] Detectados {count} arranques fallidos consecutivos.")
        from bios.recovery import enter_recovery_mode
        enter_recovery_mode("too_many_crashes")
        return True
    return False

def _run_post():
    print("[BIOS] POST - verificando integridad del sistema...")
    from bios.post import run_post
    result = run_post()
    if result["errors"]:
        print(f"[BIOS] POST FALLO - {len(result['errors'])} error(es):")
        for e in result["errors"]:
            print(f"  x {e}")
    else:
        print(f"[BIOS] POST OK - {len(result['checks'])} verificaciones pasadas")
    if result["warnings"]:
        for w in result["warnings"]:
            print(f"  ! {w}")
    return result

def _start_watchdog():
    from bios.watchdog import load_rules, heartbeat, watchdog_loop
    rules_path = os.path.join(_BIOS_DIR, "rules.json")
    load_rules(rules_path)
    stop_event = threading.Event()
    t = threading.Thread(target=watchdog_loop, args=(stop_event,), daemon=True, name="BIOSWatchdog")
    t.start()
    heartbeat()
    return stop_event

def bios_boot():
    _bios_banner()

    rules = _load_rules()
    print(f"[BIOS] Reglas cargadas: {len(rules.get('rules', {}))} reglas")

    if _check_previous_crash():
        print("[BIOS] Arrancando en modo recovery...")
        from bios.recovery import launch_recovery_ui
        launch_recovery_ui()
        return

    post_result = _run_post()
    if post_result["errors"]:
        _increment_crash_count()
        print("[BIOS] POST con errores — ¿continuar de todas formas?")
        print("[BIOS] Continuando por ahora...")

    watchdog_stop = _start_watchdog()
    print("[BIOS] Watchdog iniciado, delegando a main()...")

    _reset_crash_count()

    from bios.watchdog import heartbeat

    try:
        sys.path.insert(0, _APP_DIR)
        import main
        main.main()
    except SystemExit:
        pass
    except KeyboardInterrupt:
        pass
    except Exception as boot_exc:
        traceback.print_exc()
        _increment_crash_count()
        print(f"[BIOS] Error en main(): {boot_exc}")
        count = _get_crash_count()
        print(f"[BIOS] Crash #{count} registrado")
        if count >= 3:
            from bios.recovery import enter_recovery_mode, launch_recovery_ui
            enter_recovery_mode("runtime_crash")
            launch_recovery_ui()
