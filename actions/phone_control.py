# -*- coding: utf-8 -*-
"""actions/phone_control.py — Controla el celular Android desde la PC.

Requiere: adb + scrcpy (D:\\Scrcpy\\scrcpy-win64-v3.3.4) y el celular con
depuracion USB autorizada. Via adb se puede tocar/deslizar/escribir en la
pantalla del celu SIN root.

Guia completa del proyecto movil: D:\\Eris_Source\\mobile\\README.md
"""
import os
import re
import subprocess
import urllib.parse
from datetime import datetime

SCRCPY_DIR = r"D:\Scrcpy\scrcpy-win64-v3.3.4"
ADB = os.path.join(SCRCPY_DIR, "adb.exe")
SCRCPY = os.path.join(SCRCPY_DIR, "scrcpy.exe")
SHOT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                        "data", "screenshots")

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
    "playstore": "com.android.vending",
    "play store": "com.android.vending",
    "tienda": "com.android.vending",
    "reloj": "com.google.android.deskclock",
    "clima": "com.google.android.apps.weather",
    "flash": "com.android.flashlight",
    "linterna": "com.android.flashlight",
    "traductor": "com.google.android.apps.translate",
    "drive": "com.google.android.apps.docs",
    "photos": "com.google.android.apps.photos",
    "facebook": "com.facebook.katana",
    "tiktok": "com.zhiliaoapp.musically",
    "netflix": "com.netflix.mediaclient",
    "prime video": "com.amazon.avod.thirdpartyclient",
    "twitter": "com.twitter.android",
    "x": "com.twitter.android",
    "firefox": "org.mozilla.firefox",
    "duckduckgo": "com.duckduckgo.mobile.android",
    "telegram x": "org.thunderdog.challegram",
    "signal": "org.thoughtcrime.securesms",
    "discord": "com.discord",
}

KEYEVENTS = {
    "back": "4",
    "home": "3",
    "recent": "187",
    "enter": "66",
    "unlock": "82",
    "volup": "24",
    "voldown": "25",
    "power": "26",
    "menu": "82",
    "search": "84",
}


def _run(cmd, timeout=20):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace",
                           timeout=timeout, check=False)
        return (p.stdout + (" " + p.stderr if p.stderr else "")).strip()
    except Exception as e:
        return "ERROR: {}".format(e)


def _connected():
    out = _run([ADB, "devices"])
    devs = []
    for line in out.splitlines()[1:]:
        line = line.strip()
        if line and "daemon" not in line.lower() and line.split()[-1] == "device":
            devs.append(line.split()[0])
    return devs, out


def _require_device():
    devs, raw = _connected()
    if not devs:
        return None, "No hay celular conectado. Conectalo por USB y autoriza la depuracion."
    return devs[0], None


def _status():
    devs, raw = _connected()
    lines = ["Celular conectado: {}".format("Sí" if devs else "NO")]
    if not devs:
        lines.append("Conectá el celular por USB con depuración USB activada, "
                     "y autorizá el aviso.")
        lines.append("Detalle: {}".format(raw[:200]))
        return "\n".join(lines)
    for d in devs:
        size = _run([ADB, "-s", d, "shell", "wm", "size"]).strip()
        model = _run([ADB, "-s", d, "shell", "getprop", "ro.product.model"]).strip()
        bat = _run([ADB, "-s", d, "shell", "dumpsys", "battery"])
        level = "?"
        for line in bat.splitlines():
            line = line.strip()
            if line.startswith("level:"):
                level = line.split(":", 1)[1].strip()
        lines.append("  {} | {} | {} | Bateria {}%".format(d, model, size, level))
    return "\n".join(lines)


def _find_pkg(dev, query):
    q = query.strip().lower()
    if q in APPS:
        return APPS[q], q
    cand = [k for k in APPS if q in k or k in q]
    if len(cand) == 1:
        return APPS[cand[0]], cand[0]
    out = _run([ADB, "-s", dev, "shell", "pm", "list", "packages"])
    pkgs = [l[len("package:"):].strip() for l in out.splitlines()
            if l.startswith("package:")]
    hits = sorted([p for p in pkgs if q in p.lower()], key=len)
    if hits:
        return hits[0], hits[0]
    return None, None


def _launch_pkg(dev, pkg):
    comp = _run([ADB, "-s", dev, "shell", "cmd", "package", "resolve-activity",
                 "--brief", "-a", "android.intent.action.MAIN",
                 "-c", "android.intent.category.LAUNCHER", pkg])
    comp = comp.strip().strip("/").split()[-1] if comp.strip() else ""
    if comp and "/" in comp:
        return _run([ADB, "-s", dev, "shell", "am", "start", "-n", comp])
    return _run([ADB, "-s", dev, "shell", "am", "start",
                 "-a", "android.intent.action.MAIN",
                 "-c", "android.intent.category.LAUNCHER", "-p", pkg])


def _open_app(dev, query):
    pkg, shown = _find_pkg(dev, query)
    if not pkg:
        return "No encontré una app que se llame '{}' en el celular.".format(query)
    out = _launch_pkg(dev, pkg)
    low = out.lower()
    if "error" in low or "exception" in low or not out:
        return "No pude abrir {}: {}".format(shown, out[:200] or "sin respuesta")
    return "Abriendo {}...".format(shown)


def _ui_elements(dev):
    _run([ADB, "-s", dev, "shell", "uiautomator", "dump",
          "/sdcard/window_dump.xml"])
    out = _run([ADB, "-s", dev, "shell", "cat", "/sdcard/window_dump.xml"])
    items = []
    for tag in re.findall(r"<node[^>]*?/?>", out or ""):
        tm = re.search(r'text="([^"]*)"', tag)
        bm = re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', tag)
        if not tm or not bm:
            continue
        text = tm.group(1)
        if not text.strip():
            continue
        x1, y1, x2, y2 = map(int, bm.groups())
        items.append((text, (x1 + x2) // 2, (y1 + y2) // 2))
    return items


def _tap_text(dev, text):
    items = _ui_elements(dev)
    q = text.strip().lower()
    if not items:
        return "No pude leer la pantalla del celular."
    for label, x, y in items:
        if q in label.lower():
            _run([ADB, "-s", dev, "shell", "input", "tap", str(x), str(y)])
            return "Toqué '{}' en ({}, {}).".format(label, x, y)
    sample = "; ".join(label[:30] for label, _, _ in items[:12])
    return ("No encontré '{}' en pantalla. Elementos visibles: {}".format(
        text, sample[:200]))


def _screenshot(dev):
    os.makedirs(SHOT_DIR, exist_ok=True)
    name = "phone_{}.png".format(datetime.now().strftime("%Y%m%d_%H%M%S"))
    path = os.path.join(SHOT_DIR, name)
    with open(path, "wb") as f:
        p = subprocess.run([ADB, "-s", dev, "exec-out", "screencap", "-p"],
                           stdout=f, timeout=30)
    if p.returncode == 0 and os.path.getsize(path) > 0:
        return "Captura guardada: {}".format(path)
    return "No pude capturar la pantalla."


def phone_control(parameters, player=None):
    action = (parameters.get("action") or "").lower().strip()
    if not action:
        return ("Acciones: status, mirror, open_app, apps, open_url, search, "
                "tap, tap_text, swipe, scroll, text, ui, screenshot, battery, "
                "home, back, recent, unlock")

    if action == "status":
        return _status()

    dev, err = _require_device()
    if err:
        return err

    if action == "mirror":
        try:
            subprocess.Popen([SCRCPY])
            return "Scrcpy lanzado: la pantalla del celular se abrió en la PC."
        except Exception as e:
            return "No pude lanzar Scrcpy: {}".format(e)

    if action == "open_app":
        name = (parameters.get("app") or parameters.get("name") or "").strip()
        if not name:
            return "Indicame la app: open_app app=youtube (o el nombre de cualquier app instalada)"
        return _open_app(dev, name)

    if action == "apps":
        return ("Apps conocidas: " + ", ".join(sorted(set(APPS))) +
                ". Tambien puedo abrir CUALQUIER app instalada por nombre.")

    if action == "open_url":
        url = (parameters.get("url") or parameters.get("text") or "").strip()
        if not url:
            return "Uso: open_url url=https://..."
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        out = _run([ADB, "-s", dev, "shell", "am", "start",
                    "-a", "android.intent.action.VIEW", "-d", url])
        return "Abriendo {} en el celular...".format(url)

    if action == "search":
        query = (parameters.get("query") or parameters.get("q")
                 or parameters.get("text") or "").strip()
        if not query:
            return "Uso: search query=recetas de pasta"
        url = "https://www.google.com/search?q=" + urllib.parse.quote(query)
        out = _run([ADB, "-s", dev, "shell", "am", "start",
                    "-a", "android.intent.action.VIEW", "-d", url])
        return "Buscando '{}' en el celular...".format(query)

    if action == "tap":
        x = parameters.get("x", parameters.get("coord_x"))
        y = parameters.get("y", parameters.get("coord_y"))
        if x is None or y is None:
            return "Uso: tap x=540 y=1200"
        out = _run([ADB, "-s", dev, "shell", "input", "tap", str(x), str(y)])
        return "Toque en ({}, {}). {}".format(x, y, out) if out else "Toque realizado."

    if action == "tap_text":
        text = (parameters.get("text") or parameters.get("label") or "").strip()
        if not text:
            return "Uso: tap_text text=Buscar (toca el elemento que dice ese texto)"
        return _tap_text(dev, text)

    if action == "swipe":
        x1 = parameters.get("x1", 540)
        y1 = parameters.get("y1", 800)
        x2 = parameters.get("x2", 540)
        y2 = parameters.get("y2", 400)
        ms = parameters.get("ms", 300)
        out = _run([ADB, "-s", dev, "shell", "input", "swipe",
                    str(x1), str(y1), str(x2), str(y2), str(ms)])
        return "Deslizamiento hecho. {}".format(out) if out else "Swipe realizado."

    if action == "scroll":
        direction = (parameters.get("direction") or parameters.get("text")
                     or "down").lower()
        if direction in ("down", "abajo", "bajar"):
            out = _run([ADB, "-s", dev, "shell", "input", "swipe",
                        "540", "1700", "540", "500", "400"])
        else:
            out = _run([ADB, "-s", dev, "shell", "input", "swipe",
                        "540", "500", "540", "1700", "400"])
        return "Scroll {}. {}".format(direction, out) if out else "Scroll hecho."

    if action in ("text", "type", "write"):
        text = parameters.get("text") or parameters.get("message") or ""
        if not text:
            return "Uso: text text=hola mundo"
        esc = text.replace(" ", "%s")
        out = _run([ADB, "-s", dev, "shell", "input", "text", esc])
        return "Texto escrito. {}".format(out) if out else "Texto escrito."

    if action in ("ui", "see", "screen"):
        items = _ui_elements(dev)
        if not items:
            return "No pude leer la pantalla del celular."
        return "Elementos en pantalla:\n" + "\n".join(
            "  - {} ({},{})".format(label, x, y) for label, x, y in items[:25])

    if action == "screenshot":
        return _screenshot(dev)

    if action == "battery":
        out = _run([ADB, "-s", dev, "shell", "dumpsys", "battery"])
        vals = {}
        for line in out.splitlines():
            line = line.strip()
            for k in ("level", "status", "temperature"):
                if line.startswith(k + ":"):
                    vals[k] = line.split(":", 1)[1].strip()
        return "Bateria: {}% | Estado: {} | Temp: {} C".format(
            vals.get("level", "?"), vals.get("status", "?"),
            vals.get("temperature", "?"))

    if action in KEYEVENTS:
        _run([ADB, "-s", dev, "shell", "input", "keyevent", KEYEVENTS[action]])
        if action == "home":
            return "Volví al inicio del celular."
        if action == "back":
            return "Fui para atrás."
        if action == "recent":
            return "Mostrando apps recientes."
        if action == "unlock":
            return "Intente desbloquear el celular."
        return "Key {} enviada.".format(action)

    return ("Acciones: status, mirror, open_app (app=...), apps, "
            "open_url (url=...), search (query=...), tap (x,y), "
            "tap_text (text=...), swipe (x1,y1,x2,y2,ms), scroll (direction=down|up), "
            "text (text=...), ui, screenshot, battery, home, back, recent, unlock")
