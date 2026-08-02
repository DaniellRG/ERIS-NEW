# -*- coding: utf-8 -*-
"""
sms.py — Envio de SMS a traves de un gateway configurado.
Backends soportados: twilio (requiere TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM)
o un gateway HTTP generico configurado en config/api_keys.json.
Acciones: send (numero+message), status.
"""
from __future__ import annotations
import json
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CFG_PATH = BASE_DIR / "config" / "api_keys.json"


def _cfg() -> dict:
    try:
        return json.loads(CFG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _send_twilio(cfg: dict, to: str, message: str) -> str:
    sid = cfg.get("twilio_account_sid", "")
    token = cfg.get("twilio_auth_token", "")
    frm = cfg.get("twilio_from", "")
    if not sid or not token or not frm:
        raise RuntimeError("Twilio no configurado (twilio_account_sid, twilio_auth_token, twilio_from)")
    import base64
    auth = base64.b64encode(f"{sid}:{token}".encode()).decode()
    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
    data = urllib.parse.urlencode({"To": to, "From": frm, "Body": message}).encode()
    req = urllib.request.Request(url, data=data, headers={"Authorization": "Basic " + auth})
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read().decode())
    return f"SMS enviado a {to} (SID {body.get('sid', 'desconocido')})"


def _send_gateway(cfg: dict, to: str, message: str) -> str:
    url = cfg.get("sms_gateway_url", "")
    key = cfg.get("sms_gateway_key", "")
    if not url:
        raise RuntimeError("gateway HTTP no configurado (sms_gateway_url)")
    payload = {"to": to, "message": message}
    headers = {"Authorization": "Bearer " + key} if key else {}
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=dict(headers, **{"Content-Type": "application/json"}))
    with urllib.request.urlopen(req, timeout=30) as resp:
        return f"SMS enviado a {to} via gateway HTTP ({resp.status})"


def sms(parameters: dict = None, player=None) -> str:
    if parameters is None:
        parameters = {}
    action = parameters.get("action", "send").lower()

    if action == "status":
        cfg = _cfg()
        has_tw = bool(cfg.get("twilio_account_sid"))
        has_gw = bool(cfg.get("sms_gateway_url"))
        if not has_tw and not has_gw:
            return (
                "No hay gateway de SMS configurado. Opciones:\n"
                "  1) Twilio: agrega twilio_account_sid, twilio_auth_token y twilio_from en config/api_keys.json\n"
                "  2) Gateway HTTP propio: agrega sms_gateway_url y sms_gateway_key"
            )
        backends = []
        if has_tw:
            backends.append("Twilio")
        if has_gw:
            backends.append("HTTP gateway")
        return "Backends de SMS configurados: " + ", ".join(backends)

    if action == "send":
        to = (parameters.get("to") or parameters.get("number") or "").strip()
        message = (parameters.get("message") or parameters.get("text") or "").strip()
        if not to or not message:
            return "Error: se requieren 'to' y 'message'."
        cfg = _cfg()
        backend = parameters.get("backend", "twilio" if cfg.get("twilio_account_sid") else "gateway").lower()
        try:
            if backend == "twilio":
                return _send_twilio(cfg, to, message)
            return _send_gateway(cfg, to, message)
        except Exception as e:
            return f"Error enviando SMS: {e}"

    return "Acciones: send (to+message), status."
