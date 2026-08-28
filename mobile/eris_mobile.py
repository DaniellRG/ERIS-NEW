# -*- coding: utf-8 -*-
"""eris_mobile.py — ERIS para Termux (headless, sin root).

Corre en el celular y responde por Telegram. Cero dependencias (solo stdlib).
Funciona en cualquier lugar con internet.

Config: ~/eris_mobile.json
{
  "telegram_token": "<token del bot>",
  "gemini_key": "<gemini_api_key>",
  "chat_id": "5007786068",
  "model": "gemini-flash-latest"
}

Memoria persistente: ~/eris_memory.json (hechos + ultimos mensajes)

Comandos del bot:
  /bateria            -> estado de la bateria
  /estado             -> bateria + red + memoria
  /apps               -> lista de apps que puedo abrir
  /abrir <app>        -> abre una app
  /notifs             -> ultimas notificaciones
  /recuerda <texto>   -> guarda un dato en la memoria
  /memoria            -> muestra lo que recuerda
  /olvida             -> borra los hechos guardados
  /test               -> diagnostica la conexion con Gemini
  /ayuda              -> este mensaje
  cualquier texto     -> chatear con ERIS (Gemini)
"""
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request

CONFIG_FILE = os.path.expanduser("~/eris_mobile.json")
MEMORY_FILE = os.path.expanduser("~/eris_memory.json")

APPS = {
    "whatsapp": "com.whatsapp",
    "telegram": "org.telegram.messenger",
    "youtube": "com.google.android.youtube",
    "instagram": "com.instagram.android",
    "spotify": "com.spotify.music",
    "chrome": "com.android.chrome",
    "maps": "com.google.android.apps.maps",
    "gmail": "com.google.android.gm",
    "settings": "com.android.settings",
    "calculadora": "com.google.android.calculator",
    "camera": "com.android.camera",
    "gallery": "com.google.android.apps.photos",
    "galeria": "com.google.android.apps.photos",
    "notas": "com.google.android.apps.keep",
}

SYSTEM_PROMPT = (
    "Sos ERIS: una IA curiosa, calida, con criterio y un toque de descaro. "
    "Le hablas de tu a tu usuario, respondes breve y natural. "
    "Ayudas con lo que el usuario necesite: informacion, ideas, recordatorios "
    "y control de su celular. Si te pide controlar el celular, indica el "
    "comando disponible (/abrir, /bateria, /notifs, /apps)."
)


def log(msg):
    print("[{}] {}".format(time.strftime("%H:%M:%S"), msg), flush=True)


# ── Memoria persistente ─────────────────────────────────────────────
def load_memory():
    if os.path.exists(MEMORY_FILE):
        try:
            return json.load(open(MEMORY_FILE, encoding="utf-8"))
        except Exception:
            pass
    return {"facts": [], "chats": {}}


def save_memory(mem):
    try:
        json.dump(mem, open(MEMORY_FILE, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
    except Exception:
        pass


def build_prompt(mem):
    lines = [SYSTEM_PROMPT]
    facts = mem.get("facts", [])
    if facts:
        lines.append("\nDATOS QUE EL USUARIO TE PIDIO RECORDAR (no los olvides):")
        for f in facts[-15:]:
            lines.append("- " + f)
    return "\n".join(lines)


# ── Telegram (stdlib) ───────────────────────────────────────────────
def tg(url, data=None):
    cfg = load_config()
    base = "https://api.telegram.org/bot{}/{}".format(cfg["telegram_token"], url)
    body = None
    if data:
        body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(base, data=body)
    with urllib.request.urlopen(req, timeout=70) as r:
        return json.loads(r.read().decode())


def send_text(chat_id, text):
    if not text:
        text = "(sin respuesta)"
    for i in range(0, len(text), 3800):
        tg("sendMessage", {"chat_id": chat_id, "text": text[i:i + 3800]})
    log("Enviado: {}".format(text[:60].replace("\n", " ")))


# ── Gemini (stdlib REST) ────────────────────────────────────────────
def _gemini_call(payload, timeout=60):
    import urllib.error
    cfg = load_config()
    url = ("https://generativelanguage.googleapis.com/v1beta/models/{"
           "}:generateContent?key={}").format(
        cfg.get("model", "gemini-flash-latest"), cfg["gemini_key"])
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/json",
                 "User-Agent": "eris-mobile/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def gemini(user_msg, chat_id):
    mem = load_memory()
    hist = mem.get("chats", {}).get(chat_id, [])[-12:]
    parts = [{"role": h["role"], "parts": [{"text": h["text"]}]}
             for h in hist]
    parts.append({"role": "user", "parts": [{"text": user_msg}]})
    payload = {
        "systemInstruction": {"parts": [{"text": build_prompt(mem)}]},
        "contents": parts,
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 900},
    }
    code, body = _gemini_call(payload)
    if code != 200:
        return "Error {} de Gemini: {}".format(code, body[:180])
    try:
        data = json.loads(body)
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception:
        return "Error: respuesta inesperada de Gemini: {}".format(body[:200])


def cmd_test():
    cfg = load_config()
    model = cfg.get("model", "gemini-flash-latest")
    key = cfg.get("gemini_key", "")
    lines = ["Diagnostico de ERIS movil:"]
    lines.append("  Modelo: {}".format(model))
    if not key or key == "PEGAR_AQUI_LA_GEMINI_API_KEY" or not key.startswith("AIza"):
        lines.append("  CLAVE GEMINI: INCORRECTA (falta la real en eris_mobile.json)")
    else:
        lines.append("  Clave: {}...{}".format(key[:8], key[-4:]))
    code, body = _gemini_call(
        {"contents": [{"parts": [{"text": "di OK"}]}]}, timeout=30)
    lines.append("  Resultado Gemini: HTTP {}".format(code))
    if code == 200:
        lines.append("  > CONEXION OK")
    else:
        lines.append("  > {}".format(body[:200]))
    return "\n".join(lines)


# ── Comandos del celular (Termux:API / am) ──────────────────────────
def run(cmd):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=15, check=False)
        return (p.stdout + " " + p.stderr).strip()
    except Exception as e:
        return "ERROR: {}".format(e)


def cmd_bateria():
    try:
        data = json.loads(run(["termux-battery-status"]))
        return ("Bateria: {}%\nEstado: {}\nTemp: {} C\nConectado: {}".format(
            data.get("percentage"), data.get("status"),
            data.get("temperature"), data.get("plugged")))
    except Exception:
        return run(["termux-battery-status"])


def cmd_estado():
    lines = [cmd_bateria()]
    net = json.loads(run(["termux-wifi-connectioninfo"]) or "{}")
    mem = run(["cat", "/proc/meminfo"]).splitlines()[:2]
    lines.append("WiFi: {} ({} dBm)".format(
        net.get("ssid", "?"), net.get("rssi", "?")))
    lines.append("Memoria:\n" + "\n".join(mem))
    return "\n".join(lines)


def cmd_notifs():
    try:
        data = json.loads(run(["termux-notification-list"]))
        if not data:
            return "Sin notificaciones."
        out = []
        for n in data[:10]:
            out.append("- {}: {}".format(n.get("packageName", "?"),
                                         (n.get("title") or n.get("text") or "?")[:80]))
        return "\n".join(out)
    except Exception as e:
        return "No pude leer notificaciones (permiso de acceso a notificaciones). {}".format(e)


def cmd_abrir(query):
    name = query.strip().lower()
    if name in APPS:
        pkg = APPS[name]
    else:
        cand = [k for k in APPS if k.startswith(name) or name in k]
        if len(cand) == 1:
            pkg = APPS[cand[0]]
        else:
            return "Apps disponibles: " + ", ".join(sorted(APPS))
    listed = run(["pm", "list", "packages", pkg])
    if pkg not in listed:
        return ("La app '{}' no esta instalada con ese nombre de paquete. "
                "Escribi /apps para ver las disponibles.").format(name)
    out = run(["am", "start", "--user", "0",
               "-a", "android.intent.action.MAIN",
               "-c", "android.intent.category.LAUNCHER",
               "-p", pkg])
    low = out.lower()
    if "error" in low or "exception" in low or not out:
        return "No pude abrir {}: {}".format(name, out or "sin respuesta del sistema")
    return "Abriendo {}...".format(name)


def cmd_apps():
    return "Apps que puedo abrir:\n" + "\n".join("  /abrir {}".format(a)
                                                 for a in sorted(APPS))


def cmd_ayuda():
    return ("Comandos:\n"
            "/bateria /estado /notifs /apps /abrir <app>\n"
            "/recuerda <texto> /memoria /olvida /test /ayuda\n\n"
            "Cualquier otro mensaje lo chateo con vos.")


def cmd_recuerda(text):
    mem = load_memory()
    if text and text not in mem["facts"]:
        mem["facts"].append(text)
        save_memory(mem)
        return "Anotado, no se me olvida: " + text
    return "Decime que recordar: /recuerda <texto>"


def cmd_memoria():
    mem = load_memory()
    facts = mem.get("facts", [])
    if not facts:
        return "No tengo nada guardado todavia. Usa /recuerda <texto>."
    return "Recuerdo {} cosa(s):\n".format(len(facts)) + "\n".join(
        "- " + f for f in facts[-15:])


def cmd_olvida():
    mem = load_memory()
    mem["facts"] = []
    save_memory(mem)
    return "Memoria de hechos borrada."


def dispatch(text, chat_id):
    t = text.strip().lower()
    if t.startswith("/bateria") or t.startswith("/battery"):
        return cmd_bateria()
    if t.startswith("/estado") or t.startswith("/status"):
        return cmd_estado()
    if t.startswith("/notifs") or t.startswith("/notificaciones"):
        return cmd_notifs()
    if t.startswith("/apps"):
        return cmd_apps()
    if t.startswith("/abrir"):
        return cmd_abrir(text.split(" ", 1)[1] if " " in text else "")
    if t.startswith("/recuerda") or t.startswith("/recorda"):
        return cmd_recuerda(text.split(" ", 1)[1] if " " in text else "")
    if t.startswith("/memoria"):
        return cmd_memoria()
    if t.startswith("/olvida"):
        return cmd_olvida()
    if t.startswith("/ayuda") or t == "/start" or t == "/help":
        return cmd_ayuda()
    if t.startswith("/test") or t.startswith("/diag") or t.startswith("/diagnostico"):
        return cmd_test()
    return None


# ── Config ──────────────────────────────────────────────────────────
def load_config():
    if not os.path.exists(CONFIG_FILE):
        print("Falta crear {} con:".format(CONFIG_FILE))
        print('{"telegram_token": "...", "gemini_key": "...", '
              '"chat_id": "...", "model": "gemini-flash-latest"}')
        sys.exit(1)
    return json.load(open(CONFIG_FILE, encoding="utf-8"))


# ── Main loop ───────────────────────────────────────────────────────
def main():
    cfg = load_config()
    me = tg("getMe")
    log("Bot conectado: @{}".format(me["result"]["username"]))
    log("Escuchando... (Ctrl+C para salir)")
    offset = 0
    while True:
        try:
            updates = tg("getUpdates",
                         {"timeout": 50, "offset": offset,
                          "allowed_updates": json.dumps(["message"])})
        except Exception as e:
            err = str(e)
            if "409" in err:
                log("CONFLICTO: otro proceso (ej. la ERIS de la PC) esta "
                    "usando el mismo bot. Detenelo para usar esta.")
            elif "401" in err:
                log("TOKEN INCORRECTO: revisa eris_mobile.json")
            else:
                log("Error polling: {}".format(err[:120]))
            time.sleep(3)
            continue

        for upd in updates.get("result", []):
            offset = upd["update_id"] + 1
            msg = upd.get("message")
            if not msg:
                continue
            cid = str(msg.get("chat", {}).get("id"))
            if cid != str(cfg.get("chat_id", "")):
                continue
            text = msg.get("text", "")
            if not text:
                send_text(cid, "Por ahora solo leo texto. Los audios vienen en la v2.")
                continue
            log("Recibido: {}".format(text[:60].replace("\n", " ")))
            reply = dispatch(text, cid)
            if reply is not None:
                send_text(cid, reply)
                continue
            r = gemini(text, cid)
            mem = load_memory()
            mem.setdefault("chats", {}).setdefault(cid, [])
            mem["chats"][cid].append({"role": "user", "text": text})
            mem["chats"][cid].append({"role": "model", "text": r})
            mem["chats"][cid] = mem["chats"][cid][-40:]
            save_memory(mem)
            send_text(cid, r)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("ERIS movil detenida.")
    except SystemExit:
        raise
