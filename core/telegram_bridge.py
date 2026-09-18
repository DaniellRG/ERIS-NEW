"""telegram_bridge.py — PUENTE TELEGRAM para ERIS.

Conecta a ERIS con un chat de Telegram vía Bot API usando solo `requests`
(ya en requirements-linux.txt; sin deps nuevas). Long-poll de getUpdates que
inyecta los mensajes en la sesión viva y reenvía la respuesta de ERIS.

Config en config/api_keys.json (se relee en cada ciclo):
  telegram_enabled: true/false (default false → bridge inactivo, sin ruido)
  telegram_bot_token: token del bot creado con @BotFather
  telegram_chat_id: chat permitido (opcional; si falta, acepta cualquier chat)

Uso observable:
  bridge = TelegramBridge()
  bridge.on_message(cb)   # cb(texto_del_usuario)
  bridge.is_pending_chat()  # True si el último turno vino de Telegram
  bridge.send(texto)     # responde al chat pendiente
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Callable

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "api_keys.json"
_POLL_TIMEOUT = 30      # long-poll: no spamear getUpdates
_RETRY_SLEEP = 5.0      # ante error de red, no martillar la API
_ENABLED_DEFAULT = False


def _read_cfg() -> dict:
    try:
        return json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


class TelegramBridge:
    def __init__(self, on_message: Callable[[str], None] | None = None):
        self._cb = on_message
        self._offset = 0
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._pending_chat = False
        self._last_chat_id: str | int | None = None

    # ── API ────────────────────────────────────────────────────────────────
    def on_message(self, cb: Callable[[str], None]):
        self._cb = cb

    def is_pending_chat(self) -> bool:
        return self._pending_chat

    @property
    def chat_id(self) -> str | int | None:
        return self._last_chat_id

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True,
                                        name="telegram-bridge")
        self._thread.start()

    def stop(self):
        self._stop.set()

    def send(self, text: str):
        if not text:
            return
        cfg = _read_cfg()
        token = cfg.get("telegram_bot_token", "")
        chat_id = self._last_chat_id or cfg.get("telegram_chat_id", "")
        if not token or not chat_id or not cfg.get("telegram_enabled", _ENABLED_DEFAULT):
            return
        try:
            import requests
            requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": text[:4000]},
                timeout=10,
            )
            self._pending_chat = False
        except Exception as e:
            print(f"[TELEGRAM] send error: {e}")

    # ── Bucle interno ──────────────────────────────────────────────────────
    def _loop(self):
        import requests
        while not self._stop.is_set():
            cfg = _read_cfg()
            if not cfg.get("telegram_enabled", _ENABLED_DEFAULT):
                self._pending_chat = False
                self._stop.wait(_POLL_TIMEOUT)
                continue
            token = cfg.get("telegram_bot_token", "")
            allowed = str(cfg.get("telegram_chat_id", "") or "")
            if not token:
                self._stop.wait(_POLL_TIMEOUT)
                continue
            try:
                resp = requests.get(
                    f"https://api.telegram.org/bot{token}/getUpdates",
                    params={"timeout": _POLL_TIMEOUT - 5, "offset": self._offset},
                    timeout=_POLL_TIMEOUT,
                )
                data = resp.json()
                for update in data.get("result", []):
                    self._offset = max(self._offset, int(update["update_id"]) + 1)
                    msg = update.get("message") or update.get("edited_message") or {}
                    text = (msg.get("text") or "").strip()
                    chat_id = msg.get("chat", {}).get("id")
                    if not text or chat_id is None:
                        continue
                    if allowed and str(chat_id) != str(allowed):
                        continue
                    self._last_chat_id = chat_id
                    self._pending_chat = True
                    try:
                        print(f"[TELEGRAM] << {text[:80]}")
                        if self._cb:
                            self._cb(text)
                    except Exception as e:
                        print(f"[TELEGRAM] cb error: {e}")
            except Exception as e:
                print(f"[TELEGRAM] poll error: {e}")
                self._stop.wait(_RETRY_SLEEP)


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from core.telegram_bridge import TelegramBridge
    br = TelegramBridge()
    print("[TELEGRAM] snapshot:", json.dumps({
        "enabled": _read_cfg().get("telegram_enabled", _ENABLED_DEFAULT),
        "has_token": bool(_read_cfg().get("telegram_bot_token", "")),
        "chat_id": _read_cfg().get("telegram_chat_id", ""),
    }))