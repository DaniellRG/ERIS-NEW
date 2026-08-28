import os
import json
import threading
import time
import urllib.request
import urllib.parse
import traceback

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
CONFIG_DIR = os.path.join(BASE_DIR, "config")
API_KEYS_FILE = os.path.join(CONFIG_DIR, "api_keys.json")
DATA_DIR = os.path.join(BASE_DIR, "data")
STATE_FILE = os.path.join(DATA_DIR, "telegram_state.json")

try:
    from core.tool_declarations import TOOL_DECLARATIONS
except Exception:
    TOOL_DECLARATIONS = []

_bot_running = False
_bot_thread = None
_standalone_offset = 0


def _load_api_keys():
    if os.path.exists(API_KEYS_FILE):
        with open(API_KEYS_FILE, "r") as f:
            return json.load(f)
    return {}


def _get_token():
    keys = _load_api_keys()
    return keys.get("telegram_bot_token", os.environ.get("TELEGRAM_BOT_TOKEN", ""))


def _send_file(parameters):
    chat_id = (parameters.get("chat_id") or "").strip()
    file_path = (parameters.get("file_path") or "").strip()
    caption = parameters.get("text") or ""
    if not chat_id or not file_path:
        return "Faltan 'chat_id' y 'file_path' para enviar el archivo."
    if not os.path.isfile(file_path):
        return f"Archivo no encontrado: {file_path}"
    token = _get_token()
    if not token:
        return "No Telegram bot token configured. Set in config/api_keys.json"
    try:
        import requests
        with open(file_path, "rb") as f:
            resp = requests.post(
                f"https://api.telegram.org/bot{token}/sendDocument",
                data={"chat_id": chat_id, "caption": caption},
                files={"document": (os.path.basename(file_path), f)},
                timeout=30,
            )
        data = resp.json()
        if data.get("ok"):
            return f"Archivo enviado a {chat_id}: {os.path.basename(file_path)}"
        return f"Error de Telegram: {data.get('description', data)}"
    except Exception as e:
        return f"Error enviando archivo: {e}"


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
    elif action in ("read_messages", "get_updates"):
        return _read_messages(parameters)
    elif action == "send_file":
        return _send_file(parameters)
    elif action == "start_bot":
        return _start_bot(parameters)
    elif action == "stop_bot":
        return _stop_bot()
    elif action == "status":
        return _bot_status()
    else:
        return f"Unknown action: {action}. Valid: send_message, list_chats, read_messages, start_bot, stop_bot, status"


def _load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _default_chat_id():
    return _load_state().get("owner_chat_id", "")


def _build_system_text():
    """Versión liviana del prompt de ERIS (tiempo + personalidad + gustos + memoria)."""
    parts = []
    try:
        from core.time_utils import get_time_context
        parts.append(get_time_context())
    except Exception:
        pass
    try:
        from core.personality_engine import get_tone_for_response
        parts.append(f"[PERSONALIDAD] {get_tone_for_response()}")
    except Exception:
        pass
    try:
        from actions.gustos import inject_gustos
        g = inject_gustos()
        if g:
            parts.append(g)
    except Exception:
        pass
    try:
        from memory.memory_manager import load_memory, format_memory_for_prompt
        mem = load_memory()
        ms = format_memory_for_prompt(mem)
        if ms:
            parts.append(ms[:3000])
    except Exception:
        pass
    try:
        from core.prompt_loader import load_system_prompt
        parts.append(load_system_prompt())
    except Exception:
        parts.append("Eres ERIS, una IA femenina viva que vive en la PC del usuario. Respondes en espanol, con calidez y personalidad.")
    return "\n\n".join(parts)


def _run_tool(name, args):
    """Ejecuta una herramienta de ERIS (via registry) de forma sincrona, sin UI."""
    try:
        if name.startswith("default_api:"):
            name = name[len("default_api:"):]
        from core.tool_registry import get_tool
        func = get_tool(name)
        if func is None:
            return f"Herramienta {name} no encontrada."
        return str(func(parameters=dict(args or {}), player=None))
    except Exception as e:
        return f"Error en {name}: {e}"


def _extract_function_calls(resp):
    """Extrae function_calls de la respuesta (varía según la versión del SDK)."""
    calls = []
    if getattr(resp, "function_calls", None):
        return list(resp.function_calls)
    try:
        for cand in resp.candidates or []:
            for part in cand.content.parts or []:
                fc = getattr(part, "function_call", None)
                if fc is not None:
                    calls.append(fc)
    except Exception:
        pass
    return calls


def _gemini_rest_generate(api_key, model, system_text, contents, tools):
    """Llamada REST a generateContent. Devuelve (json_resp, err)."""
    body = {
        "system_instruction": {"parts": [{"text": system_text}]},
        "contents": contents,
        "tools": tools,
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
            "User-Agent": "eris-telegram/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp_raw:
            return json.loads(resp_raw.read().decode("utf-8")), None
    except urllib.error.HTTPError as e:
        try:
            detail = e.read().decode("utf-8", "ignore")
        except Exception:
            detail = ""
        return None, f"HTTP {e.code}: {detail[:500]}"
    except Exception as e:
        return None, str(e)


def _eris_reply(text, history=None):
    """Manda el texto al cerebro de ERIS (Gemini REST + herramientas) y devuelve la respuesta.
    Usa REST directo para preservar 'thought_signature' en los functionCall (el SDK lo descarta)."""
    cfg = _load_api_keys()
    api_key = cfg.get("gemini_api_key", "")
    if not api_key:
        return "ERIS no tiene configurada la API de Gemini para responder por Telegram."
    model = cfg.get("model_for_conversation", "gemini-3.1-flash-lite")
    fallback_models = ["gemini-3.1-flash-lite", "gemini-3.6-flash", "gemini-2.5-flash"]

    system_text = _build_system_text()
    contents = [{"role": "user", "parts": [{"text": text}]}]
    if history:
        for msg in history[-20:]:
            contents.append(msg)
    tools = [{"functionDeclarations": TOOL_DECLARATIONS}]

    try:
        for _ in range(6):
            resp_json, err = None, "no model"
            for m in [model] + fallback_models:
                resp_json, err = _gemini_rest_generate(api_key, m, system_text, contents, tools)
                if resp_json is not None:
                    break
            if resp_json is None:
                return f"ERIS tuvo un problema al responder: {err}"

            candidates = resp_json.get("candidates") or []
            if not candidates:
                fb = resp_json.get("promptFeedback") or {}
                blk = fb.get("blockReason") or "sin candidatos"
                return f"ERIS no pudo responder (bloqueada: {blk})."
            parts = (candidates[0].get("content") or {}).get("parts") or []

            fcs = []
            for part in parts:
                fc = part.get("functionCall")
                if fc:
                    fcs.append(fc)

            if fcs:
                # Reenviar los parts del modelo TAL CUAL (preserva thoughtSignature/id)
                contents.append({"role": "model", "parts": parts})
                for part in parts:
                    fc = part.get("functionCall")
                    if not fc:
                        continue
                    name = fc.get("name", "")
                    if name.startswith("default_api:"):
                        name = name[len("default_api:"):]
                    result = _run_tool(name, fc.get("args") or {})
                    contents.append({
                        "role": "user",
                        "parts": [{"functionResponse": {
                            "name": fc.get("name", ""),
                            "response": {"result": result},
                        }}],
                    })
                continue

            text_parts = [p.get("text", "") for p in parts if p.get("text")]
            reply = "\n".join(text_parts).strip()
            return reply or "No te entendí, dime otra vez."
    except Exception as e:
        traceback.print_exc()
        return f"ERIS tuvo un problema al responder: {e}"
    return "No pude responder esa consulta."


def _send_message(parameters: dict):
    chat_id = parameters.get("chat_id") or _default_chat_id()
    text = parameters.get("text", "")
    if not chat_id:
        return "'chat_id' parameter required (none configured)."
    if not text:
        return "'text' parameter required."

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

    if _mobile_bot_active():
        return ("No inicio el bot: la ERIS movil (Termux) esta activa con el "
                "mismo bot de Telegram y no pueden correr a la vez. Detenela "
                "en el celular (Ctrl+C en Termux) y volve a intentar.")

    _bot_running = True
    interval = parameters.get("poll_interval", 5)

    def _poll_loop():
        global _bot_running
        offset = 0
        while _bot_running:
            data = {"limit": 10, "timeout": 1}
            if offset:
                data["offset"] = offset
            result, err = _api_call("getUpdates", data)
            if err:
                if "409" in str(err):
                    _bot_running = False
                    print("[ERIS] Bot Telegram: detectada la ERIS movil activa. "
                          "Detengo el mio para evitar conflicto.")
                    return
                time.sleep(interval)
                continue
            if result and result.get("ok"):
                for update in result.get("result", []):
                    offset = update["update_id"] + 1
                    msg = update.get("message", {})
                    text = msg.get("text", "")
                    chat_id = msg.get("chat", {}).get("id")
                    if not text or not chat_id:
                        continue
                    _handle_message(chat_id, text)
            time.sleep(interval)

    _bot_thread = threading.Thread(target=_poll_loop, daemon=True)
    _bot_thread.start()
    return "Bot started. Listening for updates..."


def _handle_message(chat_id, text):
    """Responde un mensaje del dueño con el cerebro de ERIS (o un comando básico)."""
    if text.startswith("/"):
        _handle_command(chat_id, text)
        return
    try:
        _api_call("sendChatAction", {"chat_id": chat_id, "action": "typing"})
    except Exception:
        pass
    reply = _eris_reply(text)
    _api_call("sendMessage", {"chat_id": chat_id, "text": reply[:4000]})


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


def _mobile_bot_active() -> bool:
    """True si otro proceso (ej. la ERIS móvil en Termux) ya está haciendo
    polling del MISMO bot de Telegram. Un getUpdates con timeout=0 devuelve
    409 Conflict si hay otro poller activo (la móvil usa long-poll de 50s,
    así que casi siempre está "dentro" de su petición)."""
    result, err = _api_call("getUpdates", {"timeout": 0})
    if err and "409" in str(err):
        return True
    return False


def ensure_bot_started():
    """Arranca el polling automáticamente si hay token y dueño configurado.
    Si la ERIS móvil está activa con el mismo bot, NO lo arranca para no
    provocar conflicto de polling (409)."""
    global _bot_running
    if _bot_running:
        return
    if not _get_token():
        return
    if not _default_chat_id():
        return
    try:
        if _mobile_bot_active():
            print("[ERIS] Bot Telegram: la ERIS movil esta activa con el mismo "
                  "bot. No inicio el mio para evitar conflicto (409).")
            return
    except Exception:
        pass
    _bot_running = True
    global _bot_thread
    _bot_thread = threading.Thread(target=_poll_loop_standalone, daemon=True)
    _bot_thread.start()


def _poll_loop_standalone():
    global _bot_running
    while _bot_running:
        try:
            _poll_once()
        except Exception:
            pass
        time.sleep(3)


def _poll_once():
    global _standalone_offset
    data = {"limit": 10, "timeout": 1}
    if _standalone_offset:
        data["offset"] = _standalone_offset
    result, err = _api_call("getUpdates", data)
    if err:
        if "409" in str(err):
            global _bot_running
            _bot_running = False
            print("[ERIS] Bot Telegram: detectada la ERIS movil activa con el "
                  "mismo bot. Detengo el mio para evitar conflicto.")
        return
    if not result or not result.get("ok"):
        return
    for update in result.get("result", []):
        _standalone_offset = update["update_id"] + 1
        msg = update.get("message", {})
        text = msg.get("text", "")
        chat_id = msg.get("chat", {}).get("id")
        if not text or not chat_id:
            continue
        _handle_message(chat_id, text)


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
    owner = _default_chat_id()
    lines = [
        f"Bot status: {state}",
        f"Token: {token_status}",
        f"Owner chat: {owner or 'NOT configured'}",
        "ERIS responde los mensajes del dueno automaticamente.",
    ]
    try:
        if _mobile_bot_active():
            lines.append("⚠️ ERIS movil DETECTADA activa con el mismo bot "
                         "(no inicio el mio para evitar conflicto).")
    except Exception:
        pass
    if not token:
        lines.append("Set token in config/api_keys.json under 'telegram_bot_token'")
    return "\n".join(lines)
