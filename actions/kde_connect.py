"""
actions/kde_connect.py — Eris conectada con tu celular vía KDE Connect.

Requisitos: kdeconnect-cli + app KDE Connect en el teléfono (misma red WiFi o
Bluetooth). Vincular: action=pair (aparece confirmación en el teléfono).
"""
from __future__ import annotations

import os
import shutil
import subprocess

_is_win = os.name == "nt"


def _kc(args, timeout=25):
    bin_ = shutil.which("kdeconnect-cli")
    if not bin_:
        return "Error: kdeconnect-cli no está instalado (`sudo pacman -S kdeconnect`)."
    try:
        r = subprocess.run([bin_, *args], capture_output=True, text=True, timeout=timeout)
    except Exception:
        return "Error conectando con kdeconnect-cli (¿daemon corriendo?)."
    if r.returncode != 0:
        return f"Error kdeconnect ({r.returncode}): {(r.stderr or r.stdout).strip()[:200]}"
    return (r.stdout or "(ok)").strip()


def kde_connect(parameters: dict | None = None, player=None) -> str:
    """Control del teléfono vía KDE Connect.
    Acciones: list, find, pair, ring, ping, send_file, send_text, clipboard,
    sms, notifications, lock, commands, execute, media_control, refresh."""
    if _is_win:
        return "kde_connect es para Linux (el receptor KDE Connect corre aquí)."
    parameters = parameters or {}
    action = (parameters.get("action") or "list").lower()
    dev = parameters.get("device") or parameters.get("id") or parameters.get("target") or ""

    if action in ("list", "lista", "devices", "dispositivos"):
        return _kc(["--list-devices"]) + "\n" + _kc(["--list-available"])

    if action in ("find", "refresh", "buscar"):
        _kc(["--refresh"])
        return _kc(["--list-devices"])

    if action in ("pair", "vincular"):
        if not dev:
            return "Falta 'device' con el id del teléfono (usá list primero)."
        return _kc(["--pair", "--device", dev]) + "\nAceptá el PIN en el teléfono."

    if action in ("unpair", "desvincular"):
        if not dev:
            return "Falta 'device'."
        return _kc(["--unpair", "--device", dev])

    if action in ("ring", "sonar"):
        return _kc(["--ring", "--device", dev])

    if action in ("ping",):
        msg = parameters.get("message") or parameters.get("text")
        if msg:
            return _kc(["--ping-msg", msg, "--device", dev])
        return _kc(["--ping", "--device", dev])

    if action in ("send_file", "enviar_archivo", "share"):
        path = parameters.get("path") or parameters.get("file") or ""
        if not path:
            return "Falta 'path' del archivo a enviar."
        if not os.path.exists(path):
            return f"No existe: {path}"
        return _kc(["--share", path, "--device", dev])

    if action in ("send_text", "enviar_texto", "share_text"):
        text = parameters.get("text") or parameters.get("message") or ""
        if not text:
            return "Falta 'text' a enviar."
        return _kc(["--share-text", text, "--device", dev])

    if action in ("clipboard", "portapapeles"):
        return _kc(["--send-clipboard", "--device", dev])

    if action in ("sms",):
        number = parameters.get("number") or parameters.get("phone") or parameters.get("destination")
        text = parameters.get("text") or parameters.get("message") or ""
        if not number or not text:
            return "Faltan 'number' (teléfono) y 'text' (mensaje)."
        args = ["--send-sms", text, "--destination", number, "--device", dev]
        att = parameters.get("attachment")
        if att and os.path.exists(att):
            args += ["--attachment", att]
        return _kc(args)

    if action in ("notifications", "notis", "notificaciones"):
        return _kc(["--list-notifications", "--device", dev])

    if action in ("lock", "bloquear"):
        return _kc(["--lock", "--device", dev])
    if action in ("unlock", "desbloquear"):
        return _kc(["--unlock", "--device", dev])

    if action in ("commands", "comandos"):
        return _kc(["--list-commands", "--device", dev])

    if action in ("execute", "ejecutar"):
        cid = parameters.get("command") or parameters.get("id") or parameters.get("target") or ""
        if not cid:
            return "Falta 'command' (id de la orden remota; usá commands primero)."
        return _kc(["--execute-command", cid, "--device", dev])

    if action in ("media_control", "musica", "media"):
        cmd = parameters.get("command") or parameters.get("media") or "play_pause"
        flags = {"play": "--play", "pause": "--pause", "play_pause": "--play-pause",
                 "next": "--next", "previous": "--previous", "now_playing": "--now-playing",
                 "volume": None}.get(cmd)
        if cmd == "volume":
            v = int(parameters.get("volume", 50))
            return _kc(["--volume", str(v), "--device", dev])
        if not flags:
            return "media_control: play, pause, play_pause, next, previous, now_playing, volume (0-100)."
        return _kc([flags, "--device", dev])

    if action in ("status", "estado"):
        return ("kdeconnect-cli instalado.\n" +
                _kc(["--list-devices"]) + "\n" +
                "Configura la app KDE Connect en el celular (misma red) y usá action=pair.")

    return ("Acciones: list, find, pair, unpair, ring, ping (message), "
            "send_file (path), send_text (text), clipboard, sms (number,text,attachment), "
            "notifications, lock, unlock, commands, execute (command), "
            "media_control (play|pause|play_pause|next|previous|now_playing|volume), status.")