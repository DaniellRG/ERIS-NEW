#!/usr/bin/env python3
"""
ERIS SERVER MODE — headless deployment for ZimaOS/Docker.

Runs Eris without Qt event loop block (no app.exec_).
All interaction via HTTP API (8080), WebSocket chat (8765),
and Web dashboard (8888).

Usage:
  python main_server.py      # server mode (headless)
"""

import sys, os, asyncio, threading, signal, time, json
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
        from core.timezome import load_tz
    except ImportError:
        try:
            from core.timezone import load_tz
        except ImportError:
            load_tz = None
    if load_tz:
        try:
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

    # API REST server (port 8081 on server to avoid ZimaOS conflict on 8080)
    if api_server:
        server_port = int(os.environ.get("ERIS_API_PORT", "8081"))
        try:
            api_server({"action": "start", "host": "0.0.0.0", "port": server_port})
            print(f"[MAIN] API REST server iniciado en http://0.0.0.0:{server_port}")
        except Exception as e:
            print(f"[MAIN] API server error: {e}")

    # Mobile server (port 8765, chat + health)
    try:
        mobile_start(port=8765)
        print("[MAIN] Health/Chat endpoint in http://0.0.0.0:8765")
    except Exception as e:
        print(f"[MAIN] Mobile server error: {e}")

    # 7) Iniciar ErisLive (motor principal) en background thread
    from ui import ErisUI
    from main import ErisLive  # reutiliza el motor principal

    print("[MAIN-SERVER] Creating ErisUI (headless)...")
    ui = ErisUI("face.png", server_mode=True)

    # WebSocket server for remote agent clients
    _ws_clients = set()
    _ws_loop = None

    async def handle_client(ws, path=None):
        """Handle WebSocket connection from eris_agent.py clients."""
        _ws_clients.add(ws)
        device_id = path or "unknown"
        print(f"[WS] Agent connected: {device_id} (total: {len(_ws_clients)})")
        try:
            async for msg in ws:
                if isinstance(msg, bytes):
                    # Audio data from client mic → forward to ErisLive
                    _current_eris = globals().get("_current_eris")
                    if _current_eris:
                        try:
                            _current_eris._recv_mic_chunk(msg)
                        except Exception:
                            pass

                elif isinstance(msg, str):
                    try:
                        data = json.loads(msg)
                        msg_type = data.get("type", "")
                        if msg_type == "register":
                            dev_id = data.get("device_id", "unknown")
                            print(f"[WS] Registered: {dev_id} (ws={ws.remote_address})")
                        elif msg_type == "command_result":
                            # Result from agent execution
                            _current_eris = globals().get("_current_eris")
                            if _current_eris:
                                try:
                                    _current_eris._handle_agent_result(data)
                                except Exception:
                                    pass
                    except json.JSONDecodeError:
                        pass

        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            _ws_clients.discard(ws)
            print(f"[WS] Agent disconnected (total: {len(_ws_clients)})")

    async def ws_broadcast_audio(data: bytes):
        """Broadcast audio PCM to all connected agents."""
        if not _ws_clients:
            return
        dead = set()
        for ws in _ws_clients:
            try:
                await ws.send(data)
            except Exception:
                dead.add(ws)
        for ws in dead:
            _ws_clients.discard(ws)

    # Arranque del loop principal de Eris + WebSocket server
    def ws_server_runner():
        """WebSocket server en thread separado con su propio loop."""
        import asyncio as _aio
        import websockets as _ws_lib

        _loop = _aio.new_event_loop()
        _aio.set_event_loop(_loop)

        # websockets 16+/17+ uses async context manager pattern
        # (serve() returns a context manager; server doesn't bind until entered)
        async def _ws_serve():
            async with _ws_lib.serve(
                handle_client, "0.0.0.0", 8766,
                ping_interval=20, ping_timeout=10
            ):
                print("[MAIN-SERVER] WebSocket server en :8766 (ws://0.0.0.0:8766)")
                await _aio.Future()  # run forever

        try:
            _loop.run_until_complete(_ws_serve())
        except ImportError:
            print("[MAIN-SERVER] websockets not installed — WS server disabled")
        except Exception as e:
            print(f"[MAIN-SERVER] WS server error: {e}")
        finally:
            _loop.close()

    # Start WS server in background thread FIRST
    ws_thread = threading.Thread(target=ws_server_runner, daemon=True, name="ws-server")
    ws_thread.start()
    time.sleep(1.5)  # Give WS server time to start

    # Start ErisLive in main process (own event loop)
    def runner():
        def _run():
            pass

        async def _start_eris():
            ui.wait_for_api_key()
            eris = ErisLive(ui)
            globals()["_current_eris"] = eris
            try:
                await eris.run()
            except KeyboardInterrupt:
                print("\n[MAIN-SERVER] Apagando...")
            except Exception as e:
                print(f"[MAIN-SERVER] ErisLive error: {e}")
            finally:
                print("[MAIN-SERVER] ErisLive shutdown complete.")

        try:
            asyncio.run(_start_eris())
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
            time.sleep(0.01)
    except KeyboardInterrupt:
        print("\n[MAIN-SERVER] Shutdown signal received.")
        sys.exit(0)

if __name__ == "__main__":
    main()
