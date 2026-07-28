import os
import json
import threading
import time
import urllib.request
import urllib.parse

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
CONFIG_DIR = os.path.join(BASE_DIR, "config")
API_KEYS_FILE = os.path.join(CONFIG_DIR, "api_keys.json")
DATA_DIR = os.path.join(BASE_DIR, "data")
STATE_FILE = os.path.join(DATA_DIR, "telegram_state.json")

_bot_running = False
_bot_thread = None


def _load_api_keys():
    if os.path.exists(API_KEYS_FILE):
        with open(API_KEYS_FILE, "r") as f:
            return json.load(f)
    return {}


def _get_token():
    keys = _load_api_keys()
    return keys.get("telegram_bot_token", os.environ.get("TELEGRAM_BOT_TOKEN", ""))


def _api_call(method, data=None, token=None):
    if not token:
        token = _get_token()
    if not token:
        return None, "No Telegram bot token configured. Set in config/api_keys.json"
    url = f"https://api.telegram.org/bot{token}/{method}"
    if data:
        encoded = urllib.parse.urlencode(data).encode("utf-8")
        req = urllib.request.Request(url, data=encoded)
    else:
        req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
            return result, None
    except Exception as e:
        return None, str(e)


def telegram_bot(parameters: dict, player=None) -> str:
    action = parameters.get("action", "status").lower()

    if action == "send_message":
        return _send_message(parameters)
    elif action == "list_chats":
        return _list_chats(parameters)
    elif action == "read_messages":
        return _read_messages(parameters)
    elif action == "start_bot":
        return _start_bot(parameters)
    elif action == "stop_bot":
        return _stop_bot()
    elif action == "status":
        return _bot_status()
    else:
        return f"Unknown action: {action}. Valid: send_message, list_chats, read_messages, start_bot, stop_bot, status"


def _send_message(parameters: dict):
    chat_id = parameters.get("chat_id", "")
    text = parameters.get("text", "")
    if not chat_id or not text:
        return "'chat_id' and 'text' parameters required."

    data = {"chat_id": chat_id, "text": text}
    parse_mode = parameters.get("parse_mode", "")
    if parse_mode:
        data["parse_mode"] = parse_mode

    result, err = _api_call("sendMessage", data)
    if err:
        return f"Error: {err}"
    if result and result.get("ok"):
        return f"Message sent to chat {chat_id}."
    return f"Failed: {result}"


def _list_chats(parameters: dict):
    limit = parameters.get("limit", 10)
    result, err = _api_call("getUpdates", {"limit": limit})
    if err:
        return f"Error: {err}"
    if not result or not result.get("ok"):
        return f"Failed: {result}"

    updates = result.get("result", [])
    if not updates:
        return "No recent updates. Send a message to your bot first."

    seen = {}
    for update in updates:
        msg = update.get("message") or update.get("channel_post") or {}
        chat = msg.get("chat", {})
        chat_id = chat.get("id")
        if chat_id and chat_id not in seen:
            seen[chat_id] = {
                "id": chat_id,
                "title": chat.get("title") or chat.get("first_name", "Unknown"),
                "type": chat.get("type", "unknown")
            }

    lines = [f"Recent chats ({len(seen)}):"]
    for c in seen.values():
        lines.append(f"  - {c['title']} (ID: {c['id']}, Type: {c['type']})")
    return "\n".join(lines)


def _read_messages(parameters: dict):
    limit = parameters.get("limit", 20)
    result, err = _api_call("getUpdates", {"limit": limit})
    if err:
        return f"Error: {err}"
    if not result or not result.get("ok"):
        return f"Failed: {result}"

    updates = result.get("result", [])
    messages = []
    for update in updates:
        msg = update.get("message")
        if msg:
            text = msg.get("text", "")
            if text:
                chat = msg.get("chat", {})
                sender = msg.get("from", {})
                messages.append({
                    "chat": chat.get("title") or chat.get("first_name", "Unknown"),
                    "from": sender.get("first_name", "Unknown"),
                    "text": text,
                    "date": msg.get("date", 0)
                })

    if not messages:
        return "No messages found."

    lines = [f"Recent messages ({len(messages)}):"]
    for m in messages:
        lines.append(f"  [{m['chat']}] {m['from']}: {m['text']}")
    return "\n".join(lines)


def _start_bot(parameters: dict):
    global _bot_running, _bot_thread

    if _bot_running:
        return "Bot is already running."

    _bot_running = True
    interval = parameters.get("poll_interval", 5)

    def _poll_loop():
        offset = 0
        while _bot_running:
            data = {"limit": 10, "timeout": 1}
            if offset:
                data["offset"] = offset
            result, err = _api_call("getUpdates", data)
            if err:
                time.sleep(interval)
                continue
            if result and result.get("ok"):
                for update in result.get("result", []):
                    offset = update["update_id"] + 1
                    msg = update.get("message", {})
                    text = msg.get("text", "")
                    chat_id = msg.get("chat", {}).get("id")
                    if text.startswith("/"):
                        _handle_command(chat_id, text)
            time.sleep(interval)

    _bot_thread = threading.Thread(target=_poll_loop, daemon=True)
    _bot_thread.start()
    return "Bot started. Listening for updates..."


def _handle_command(chat_id, text):
    cmd = text.split()[0].lower()
    if cmd == "/start":
        _api_call("sendMessage", {"chat_id": chat_id, "text": "Bot is active."})
    elif cmd == "/help":
        _api_call("sendMessage", {
            "chat_id": chat_id,
            "text": "Commands: /start, /help, /status"
        })
    elif cmd == "/status":
        _api_call("sendMessage", {"chat_id": chat_id, "text": "Running normally."})


def _stop_bot():
    global _bot_running
    if not _bot_running:
        return "Bot is not running."
    _bot_running = False
    return "Bot stopped."


def _bot_status():
    state = "running" if _bot_running else "stopped"
    token = _get_token()
    token_status = "configured" if token else "NOT configured"
    lines = [
        f"Bot status: {state}",
        f"Token: {token_status}",
    ]
    if not token:
        lines.append("Set token in config/api_keys.json under 'telegram_bot_token'")
    return "\n".join(lines)
