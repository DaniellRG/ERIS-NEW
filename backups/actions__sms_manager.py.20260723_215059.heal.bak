"""SMS desde la PC via Twilio o API HTTP generica."""
import json
import os
import time
from pathlib import Path


HISTORY_FILE = Path(os.environ.get("APPDATA", "")) / "ERIS" / "config" / "sms_history.json"
_sms_history = []


def _load_history():
    global _sms_history
    if HISTORY_FILE.exists():
        try:
            _sms_history = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            _sms_history = []
    return _sms_history


def _save_history():
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(json.dumps(_sms_history[-100:], indent=2, ensure_ascii=False), encoding="utf-8")


def _get_twilio_creds():
    try:
        from memory.config_manager import load_api_keys
        keys = load_api_keys()
        return keys.get("twilio_account_sid", ""), keys.get("twilio_auth_token", ""), keys.get("twilio_from", "")
    except Exception:
        import config.api_keys as fallback
        return fallback.twilio_account_sid or "", fallback.twilio_auth_token or "", fallback.twilio_from or ""
    return "", "", ""


def _sms_twilio(to: str, message: str) -> str:
    import requests
    sid, token, from_num = _get_twilio_creds()
    if not sid or not token:
        return "Twilio no configurado. Configura twilio_account_sid, twilio_auth_token y twilio_from en api_keys.json"

    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
    resp = requests.post(url, auth=(sid, token), data={"From": from_num, "To": to, "Body": message}, timeout=15)
    if resp.status_code == 201:
        data = resp.json()
        return f"SMS enviado a {to}. SID: {data.get('sid', 'N/A')}"
    return f"Error Twilio: {resp.status_code} - {resp.text[:200]}"


def _sms_http(to: str, message: str, params: dict) -> str:
    import requests
    url = params.get("url", "")
    if not url:
        return "URL de API SMS no configurada."
    payload = params.get("payload", "to={to}&message={msg}")
    payload = payload.replace("{to}", to).replace("{msg}", message)
    method = params.get("method", "POST").upper()
    headers = json.loads(params.get("headers", "{}"))
    try:
        if method == "GET":
            resp = requests.get(url, params=dict(p.split("=", 1) for p in payload.split("&") if "=" in p), headers=headers, timeout=15)
        else:
            resp = requests.post(url, data=payload, headers=headers, timeout=15)
        return f"SMS enviado via HTTP: {resp.status_code}"
    except Exception as e:
        return f"Error HTTP SMS: {e}"


def send_sms(parameters: dict = None, player=None) -> str:
    """Envia un SMS."""
    params = parameters or {}
    to = params.get("to", "").strip()
    message = params.get("message", "").strip()
    if not to or not message:
        return "Uso: to=+56912345678 message='Texto del mensaje'"

    sid, token, from_num = _get_twilio_creds()
    if sid and token:
        result = _sms_twilio(to, message)
    else:
        sms_config = _load_sms_config()
        result = _sms_http(to, message, sms_config)

    _load_history()
    _sms_history.append({"to": to, "message": message, "result": result, "time": time.time()})
    _save_history()
    return result


def _load_sms_config():
    try:
        from memory.config_manager import load_api_keys
        keys = load_api_keys()
        return {
            "url": keys.get("sms_api_url", ""),
            "method": keys.get("sms_api_method", "POST"),
            "payload": keys.get("sms_api_payload", "to={to}&message={msg}"),
            "headers": keys.get("sms_api_headers", "{}"),
        }
    except Exception:
        return {}


def history(parameters: dict = None, player=None) -> str:
    """Muestra historial de SMS enviados."""
    _load_history()
    if not _sms_history:
        return "Sin historial de SMS."
    lines = ["Historial de SMS:"]
    for entry in reversed(_sms_history[-20:]):
        t = time.strftime("%Y-%m-%d %H:%M", time.localtime(entry.get("time", 0)))
        to = entry.get("to", "?")
        msg = entry.get("message", "")[:50]
        lines.append(f"  [{t}] -> {to}: {msg}")
    return "\n".join(lines)


def sms_status(parameters: dict = None, player=None) -> str:
    """Estado del servicio SMS."""
    sid, token, from_num = _get_twilio_creds()
    if sid and token:
        return f"SMS via Twilio activo (desde: {from_num})"
    cfg = _load_sms_config()
    if cfg.get("url"):
        return "SMS via HTTP configurado."
    return "SMS no configurado. Configura Twilio o SMS API en api_keys.json."
