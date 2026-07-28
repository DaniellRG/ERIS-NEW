"""
core/connectivity.py — Internet auto-detect + online/offline mode switcher for ERIS.
Monitors connectivity, auto-switches between Gemini (online) and Ollama (offline).
"""
from __future__ import annotations

import json
import time
import threading
import urllib.request
import urllib.error
from pathlib import Path
from typing import Callable

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_STATE_FILE = _DATA_DIR / "connectivity_state.json"

# Default config
_DEFAULTS = {
    "check_interval": 5,          # seconds between checks
    "fail_threshold": 3,          # consecutive fails before going offline
    "recover_threshold": 2,       # consecutive OKs before going online
    "ping_urls": [
        "https://www.google.com",
        "https://dns.google/resolve?name=google.com",
    ],
    "auto_switch": True,          # auto-switch modes
    "ollama_model": "minicpm-v",  # model for offline mode
    "tts_backend": "kokoro",      # local TTS backend
}


class ConnectivityMonitor:
    """Monitors internet and auto-switches between online/offline modes."""

    def __init__(self, on_mode_change: Callable | None = None):
        self._online = True
        self._consecutive_fails = 0
        self._consecutive_oks = 0
        self._running = False
        self._thread = None
        self._lock = threading.Lock()
        self._on_mode_change = on_mode_change
        self._config = _DEFAULTS.copy()
        self._load_config()
        self._load_state()

    def _load_config(self):
        try:
            cfg_path = Path(__file__).resolve().parent.parent / "config" / "api_keys.json"
            if cfg_path.exists():
                data = json.loads(cfg_path.read_text(encoding="utf-8"))
                if "connectivity" in data:
                    self._config.update(data["connectivity"])
                if "ollama_model" in data:
                    self._config["ollama_model"] = data["ollama_model"]
                if "tts_backend" in data:
                    self._config["tts_backend"] = data["tts_backend"]
        except Exception:
            pass

    def _load_state(self):
        try:
            if _STATE_FILE.exists():
                data = json.loads(_STATE_FILE.read_text(encoding="utf-8"))
                self._online = data.get("last_known_online", True)
        except Exception:
            pass

    def _save_state(self):
        try:
            _DATA_DIR.mkdir(parents=True, exist_ok=True)
            state = {
                "last_known_online": self._online,
                "last_check": time.time(),
                "mode": "online" if self._online else "offline",
            }
            _STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
        except Exception:
            pass

    def is_online(self) -> bool:
        """Check current internet status."""
        with self._lock:
            return self._online

    def get_mode(self) -> str:
        return "online" if self._online else "offline"

    def get_config(self) -> dict:
        return self._config.copy()

    def set_offline(self):
        """Manually force offline mode."""
        with self._lock:
            if self._online:
                self._online = False
                self._consecutive_fails = 0
                self._consecutive_oks = 0
                self._save_state()
                if self._on_mode_change:
                    self._on_mode_change(False)

    def set_online(self):
        """Manually force online mode."""
        with self._lock:
            if not self._online:
                self._online = True
                self._consecutive_fails = 0
                self._consecutive_oks = 0
                self._save_state()
                if self._on_mode_change:
                    self._on_mode_change(True)

    def _check_internet(self) -> bool:
        """Try to reach the internet via HTTP."""
        for url in self._config["ping_urls"]:
            try:
                req = urllib.request.Request(url, method="HEAD")
                resp = urllib.request.urlopen(req, timeout=3)
                resp.close()
                return True
            except Exception:
                continue
        return False

    def _monitor_loop(self):
        """Background monitoring loop."""
        while self._running:
            try:
                online = self._check_internet()
                with self._lock:
                    if online:
                        self._consecutive_fails = 0
                        self._consecutive_oks += 1
                        if not self._online and self._consecutive_oks >= self._config["recover_threshold"]:
                            self._online = True
                            self._consecutive_oks = 0
                            self._save_state()
                            if self._on_mode_change:
                                self._on_mode_change(True)
                    else:
                        self._consecutive_oks = 0
                        self._consecutive_fails += 1
                        if self._online and self._consecutive_fails >= self._config["fail_threshold"]:
                            self._online = False
                            self._consecutive_fails = 0
                            self._save_state()
                            if self._on_mode_change:
                                self._on_mode_change(False)
            except Exception:
                pass
            time.sleep(self._config["check_interval"])

    def start(self):
        """Start background monitoring."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop monitoring."""
        self._running = False

    def status(self) -> str:
        """Return status string for display."""
        mode = self.get_mode()
        icon = "🟢" if self._online else "🔴"
        lines = [
            "═══ CONECTIVIDAD ═══",
            "",
            "  Modo: {} {}".format(icon, mode.upper()),
            "  Auto-switch: {}".format("ON" if self._config["auto_switch"] else "OFF"),
            "  Modelo offline: {}".format(self._config["ollama_model"]),
            "  TTS offline: {}".format(self._config["tts_backend"]),
            "",
            "  Controles:",
            "    - Se auto-detecta internet cada {}s".format(self._config["check_interval"]),
            "    - Si pierde internet → modo OFFLINE automatico",
            "    - Si vuelve internet → modo ONLINE automatico",
            "    - Manual: 'set_offline' / 'set_online'",
        ]
        return "\n".join(lines)


# Singleton
_monitor: ConnectivityMonitor | None = None


def get_monitor(on_mode_change: Callable | None = None) -> ConnectivityMonitor:
    global _monitor
    if _monitor is None:
        _monitor = ConnectivityMonitor(on_mode_change=on_mode_change)
    return _monitor


def connectivity_tool(parameters: dict = None, player=None) -> str:
    """Action handler for connectivity management."""
    if parameters is None:
        parameters = {}
    action = parameters.get("action", "status")
    mon = get_monitor()
    if action == "status":
        return mon.status()
    elif action == "set_offline":
        mon.set_offline()
        return "Modo OFFLINE activado manualmente"
    elif action == "set_online":
        mon.set_online()
        return "Modo ONLINE activado manualmente"
    elif action == "check":
        online = mon._check_internet()
        return "Internet: {}".format("CONNECTED" if online else "DISCONNECTED")
    elif action == "config":
        return json.dumps(mon.get_config(), indent=2)
    else:
        return "Acciones: status, set_offline, set_online, check, config"
