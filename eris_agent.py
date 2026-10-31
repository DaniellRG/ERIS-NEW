#!/usr/bin/env python3
"""
ERIS AGENT — Lightweight client for remote devices.

Connects to central Eris Server (ZimaOS) and:
  1. Receives audio stream → reproduces locally via pacat
  2. Captures microphone    → sends to server via WebSocket
  3. Executes commands      → file ops, system control, etc.

Usage:
  python eris_agent.py --host 100.69.172.124 --port 8765 --device-id "mi-pc-trabajo"
  python eris_agent.py --host 100.69.172.124  (auto-detect device-id)
"""

import sys, os, argparse, json, time, socket, threading, asyncio
import struct, subprocess

# ── Optional deps ──
try:
    import sounddevice as sd
    import numpy as np
    _HAS_SD = True
except ImportError:
    _HAS_SD = False
    print("[AGENT] sounddevice not installed — audio capture/playback disabled")

# ── WebSocket client (uses stdlib) ──
try:
    import websockets
    _HAS_WS = True
except ImportError:
    try:
        import websocket
        _HAS_WS = True
    except ImportError:
        _HAS_WS = False
        print("[AGENT] websocket/client not installed — cannot connect to server")

# ── Constants ──
AUDIO_SAMPLE_RATE = 24000  # matches Gemini Live output
AUDIO_CHANNELS = 1
AUDIO_FORMAT = "S16LE"

class ErisAgent:
    def __init__(self, host="127.0.0.1", port=8765, device_id=None,
                 speaker_id=None, mic_id=None):
        self.host = host
        self.port = port
        self.device_id = device_id or self._auto_device_id()
        self.speaker_id = speaker_id
        self.mic_id = mic_id

        # Audio buffers
        self._audio_queue = []
        self._pacat_proc = None
        self._stream = None

        # Connection state
        self.ws = None
        self._running = False
        self._server_version = "unknown"

    def _auto_device_id(self):
        h = socket.gethostname()
        u = os.environ.get("USER", "user")
        return f"{u}@{h}"

    def _start_pacat(self):
        """Start pacat playback subprocess for receiving audio."""
        try:
            self._pacat_proc = subprocess.Popen(
                ["pacat", "--rate=24000", "--format=S16LE", "--channels=1",
                 "--device", str(self.speaker_id or "auto")],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            print(f"[AGENT] pacat playback started (PID {self._pacat_proc.pid})")
        except FileNotFoundError:
            print("[AGENT] ⚠️ pacat not found — audio output disabled")

    def _push_audio(self, pcm_bytes):
        """Push incoming PCM audio to pacat."""
        if self._pacat_proc and self._pacat_proc.poll() is None:
            try:
                self._pacat_proc.stdin.write(pcm_bytes)
                self._pacat_proc.stdin.flush()
            except Exception as e:
                print(f"[AGENT] pacat write error: {e}")
                self._restart_pacat()

    def _restart_pacat(self):
        try:
            if self._pacat_proc:
                self._pacat_proc.terminate()
        except Exception:
            pass
        self._start_pacat()

    def _start_mic_capture(self):
        """Start microphone capture and stream to server."""
        if not _HAS_SD:
            return

        try:
            # List devices to let user pick
            devices = sd.query_devices()
            default_in = sd.default.device[0] if sd.default.device else 0
            if self.mic_id is not None:
                default_in = int(self.mic_id)

            def audio_callback(indata, frames, time_info, status):
                if not self._running:
                    return
                # Convert float32 to S16LE PCM
                pcm = (indata * 32767).astype('<i2').tobytes()
                # Send via WebSocket
                if self.ws:
                    try:
                        self.ws.send(pcm, binary=True)
                    except Exception:
                        pass
                    try:
                        self.ws.send(pcm, binary=True)
                    except Exception:
                        pass

            self._stream = sd.InputStream(
                samplerate=AUDIO_SAMPLE_RATE,
                channels=AUDIO_CHANNELS,
                dtype='float32',
                device=default_in,
                callback=audio_callback,
            )
            self._stream.start()
            dev_name = devices[default_in]['name'] if default_in < len(devices) else "default"
            print(f"[AGENT] Mic stream open (device {default_in}: {dev_name})")
        except Exception as e:
            print(f"[AGENT] Microphone error: {e}")

    def _register_with_server(self):
        """Send registration message to identify this device."""
        reg = {
            "type": "register",
            "device_id": self.device_id,
            "host": socket.gethostname(),
            "platform": sys.platform,
            "python": sys.version[:6],
            "has_mic": _HAS_SD,
            "has_speaker": True,
        }
        return json.dumps(reg)

    def connect(self):
        """Connect to Eris Server via WebSocket."""
        if not _HAS_WS:
            print("[AGENT] No websocket library available. Install: pip install websockets")
            return False

        ws_url = f"ws://{self.host}:{self.port}/ws"

        print(f"[AGENT] Connecting to {ws_url} as '{self.device_id}'...")

        try:
            if 'websockets' in sys.modules:
                # Async websockets
                import asyncio
                asyncio.run(self._connect_async(ws_url))
            else:
                # sync websocket-client
                self._connect_sync(ws_url)
        except KeyboardInterrupt:
            print("\n[AGENT] Disconnecting...")
            self._running = False
        except Exception as e:
            print(f"[AGENT] Connection error: {e}")
            return False

        return True

    async def _connect_async(self, ws_url):
        """Async websocket connection using websockets library."""
        import websockets
        self._running = True

        # Start audio output first
        self._start_pacat()
        self._start_mic_capture()

        async with websockets.connect(ws_url) as ws:
            self.ws = ws
            print(f"[AGENT] ✅ Connected to Eris Server ({self.device_id})")

            # Register device
            await ws.send(self._register_with_server())

            # Listen for messages
            while self._running:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=30)
                    await self._handle_message(ws, msg)
                except asyncio.TimeoutError:
                    # Ping server periodically
                    await ws.ping()
                except Exception as e:
                    if self._running:
                        print(f"[AGENT] recv error: {e}")
                    break

            # Cleanup
            self._running = False
            if self._stream:
                self._stream.stop_stream()
                self._stream.close()
            if self._pacat_proc:
                self._pacat_proc.terminate()

    def _connect_sync(self, ws_url):
        """Synchronous websocket connection using websocket-client."""
        import websocket
        self._running = True

        # Start audio output
        self._start_pacat()
        self._start_mic_capture()

        def on_message(ws, msg):
            if isinstance(msg, bytes):
                self._push_audio(msg)
            elif isinstance(msg, str):
                try:
                    data = json.loads(msg)
                    self._handle_json(data)
                except json.JSONDecodeError:
                    print(f"[AGENT] Server: {msg}")

        def on_open(ws):
            print(f"[AGENT] ✅ Connected to Eris Server ({self.device_id})")
            ws.send(self._register_with_server())

        def on_close(ws, *args):
            print("[AGENT] Connection closed")
            self._running = False
            if self._stream:
                try:
                    self._stream.stop_stream()
                    self._stream.close()
                except Exception:
                    pass
            if self._pacat_proc:
                self._pacat_proc.terminate()

        def on_error(ws, err):
            print(f"[AGENT] WebSocket error: {err}")

        ws_app = websocket.WebSocketApp(
            ws_url,
            on_message=on_message,
            on_open=on_open,
            on_close=on_close,
            on_error=on_error,
        )
        self.ws = ws_app
        ws_app.run_forever(ping_interval=25, ping_timeout=5)

    async def _handle_message(self, ws, msg):
        if isinstance(msg, bytes):
            self._push_audio(msg)
        elif isinstance(msg, str):
            try:
                data = json.loads(msg)
                self._handle_json(data)
            except json.JSONDecodeError:
                print(f"[AGENT] Server: {msg}")
        else:
            print(f"[AGENT] Unknown message type: {type(msg)}")

    def _handle_json(self, data: dict):
        msg_type = data.get("type", "unknown")

        if msg_type == "audio":
            pcm = data.get("data", "")
            try:
                pcm_bytes = bytes.fromhex(pcm) if isinstance(pcm, str) else bytes(pcm)
                self._push_audio(pcm_bytes)
            except Exception as e:
                print(f"[AGENT] audio decode error: {e}")

        elif msg_type == "command":
            cmd = data.get("cmd", "")
            target = data.get("target", "")
            print(f"[AGENT] Command: {cmd} (target={target})")
            # Execute and return result
            result = self._exec_command(cmd, data.get("args", {}))
            if self.ws:
                try:
                    self.ws.send(json.dumps({
                        "type": "command_result",
                        "device_id": self.device_id,
                        "cmd": cmd,
                        "result": result,
                    }))
                except Exception:
                    pass

        elif msg_type == "text":
            print(f"[ERIS] {data.get('text', '')}")

    def _exec_command(self, cmd: str, args: dict) -> str:
        """Execute commands locally on this device."""
        try:
            if cmd == "file_list":
                path = args.get("path", ".")
                files = os.listdir(path)
                return json.dumps({"files": files[:50]})

            elif cmd == "file_read":
                path = args.get("path", "")
                with open(path, "r") as f:
                    return f.read()[:4096]

            elif cmd == "file_write":
                path = args.get("path", "")
                content = args.get("content", "")
                os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
                with open(path, "w") as f:
                    f.write(content)
                return "OK"

            elif cmd == "shell":
                shell_cmd = args.get("cmd", "")
                result = subprocess.run(shell_cmd, shell=True, capture_output=True,
                                        text=True, timeout=30)
                return result.stdout[:2048] + result.stderr[:1024]

            elif cmd == "ping":
                return "pong"

            else:
                return f"Unknown command: {cmd}"

        except Exception as e:
            return f"Error: {e}"

    def run(self):
        """Main entry: connect and maintain connection."""
        self._running = True
        try:
            self.connect()
        finally:
            self._running = False

            # Cleanup
            if self._pacat_proc:
                try:
                    self._pacat_proc.stdin.close()
                    self._pacat_proc.terminate()
                except Exception:
                    pass

            if self._stream:
                try:
                    self._stream.stop_stream()
                    self._stream.close()
                except Exception:
                    pass

            print(f"[AGENT] Device '{self.device_id}' disconnected.")


def main():
    parser = argparse.ArgumentParser(description="ERIS Agent — Remote device client")
    parser.add_argument("--host", default="127.0.0.1",
                        help="Eris Server host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8766,
                        help="Eris Server WebSocket port (default: 8766)")
    parser.add_argument("--device-id", default=None,
                        help="Device identifier (default: auto-detect)")
    parser.add_argument("--speaker-id", type=int, default=None,
                        help="PulseAudio sink ID for audio output")
    parser.add_argument("--mic-id", type=int, default=None,
                        help="Audio input device ID for microphone")

    args = parser.parse_args()

    print(f"""
╔══════════════════════════════════════════════╗
║  ERIS AGENT — Remote Device Client           ║
║  Server: {args.host}:{args.port:<20} ║
║  Device: {(args.device_id or 'auto'):<20} │
║  Mic:     {'disabled' if not _HAS_SD else 'enabled':19} │
╚══════════════════════════════════════════════╝
""")

    agent = ErisAgent(
        host=args.host,
        port=args.port,
        device_id=args.device_id,
        speaker_id=args.speaker_id,
        mic_id=args.mic_id,
    )

    agent.run()


if __name__ == "__main__":
    main()
