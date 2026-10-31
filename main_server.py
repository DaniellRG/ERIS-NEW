#!/usr/bin/env python3
"""
ERIS SERVER MODE — headless deployment for ZimaOS/Docker.

Runs Eris without Qt event loop block (no app.exec_).
All interaction via HTTP API (8080), WebSocket chat (8765),
and Web dashboard (8888).

Usage:
  python main_server.py      # server mode (headless)
"""

import sys, os, asyncio, threading, signal
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# ── Hardware profiling (antes de QApplication) ──
print("[MAIN-SERVER] Initializing server mode...")

def main():
    # 1) Setup single instance (Linux fallback to PID file)
    _pidfile = os.path.join(os.path.dirname(__file__), "data", "eris_server.pid")
    os.makedirs(os.path.dirname(_pidfile), exist_ok=True)
    if os.path.exists(_pidfile):
        try:
            old_pid = int(open(_pidfile).read().strip())
            os.kill(old_pid, 0)
            print(f"[MAIN-SERVER] Already running (PID {old_pid}). Exiting.")
            return
        except (ValueError, ProcessLookupError, PermissionError):
            pass  # stale PID file
    with open(_pidfile, "w") as f:
        f.write(str(os.getpid()))

    # 2) Timezone
    try:
        from actions.api_server import load_tz
        from pathlib import Path
        load_tz(Path(__file__).resolve().parent / "config" / "api_server.json")
    except Exception as e:
        print(f"[MAIN-SERVER] tz skip: {e}")

    # 3) Console log
    try:
        from core.console_log import log_system
        log_system("ERIS server started", {"mode": "server", "pid": os.getpid()})
    except Exception:
        pass

    # 4) Identity restore
    try:
        from core.identity_persistence import restore_latest
        restore_result = restore_latest()
        if restore_result.get("files_restored", 0) > 0:
            print(f"[MAIN-SERVER] Identity restaurada: {restore_result['files_restored']} archivos")
    except Exception as e:
        print(f"[MAIN-SERVER] Identity skip: {str(e)[:60]}")

    # 5) Create QApplication offscreen (no GUI show)
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt
    app = QApplication.instance() or QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # no bloquear app.exec()

    # 6) Arrancar servers (API REST + mobile_server + dashboard) en threads
    from actions.api_server import api_server
    from actions.mobile_server import start as mobile_start

    # API REST server (port 8080)
    if api_server:
        try:
            api_server({"action": "start", "host": "0.0.0.0", "port": 8080})
            print("[MAIN] API REST server iniciado en http://0.0.0.0:8080")
        except Exception as e:
            print(f"[MAIN] API server error: {e}")

    # Mobile server (port 8765, chat + health)
    try:
        mobile_start(host="0.0.0.0", port=8765)
        print("[MAIN] Health/Chat endpoint in http://0.0.0.0:8765")
    except Exception as e:
        print(f"[MAIN] Mobile server error: {e}")

    # 7) Iniciar ErisLive (motor principal) en background thread
    from ui import ErisUI
    from main import ErisLive  # reutiliza el motor principal

    print("[MAIN-SERVER] Creating ErisUI (headless)...")
    ui = ErisUI("face.png", server_mode=True)

    # Arrancar el loop principal sin app.exec() — usa QTimer para no bloquear
    def runner():
        ui.wait_for_api_key()
        eris = ErisLive(ui)
        globals()["_current_eris"] = eris
        try:
            asyncio.run(eris.run())
        except KeyboardInterrupt:
            print("\n[MAIN-SERVER] Apagando...")
        finally:
            print("[MAIN-SERVER] Shutdown complete.")

    t = threading.Thread(target=runner, daemon=True)
    t.start()

    # 8) Process events en un loop (no exec_() puro)
    print("[MAIN-SERVER] Server running. Press Ctrl+C to stop.")
    try:
        while t.is_alive():
            app.processEvents()
            import time
            time.sleep(0.01)
    except KeyboardInterrupt:
        print("\n[MAIN-SERVER] Shutdown signal received.")
        sys.exit(0)

if __name__ == "__main__":
    main()
