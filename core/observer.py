# -*- coding: utf-8 -*-
"""
core/observer.py — LOS SENTIDOS de Eris (observación del entorno).

Mira la ventana en foco y las ventanas abiertas del usuario (sin leer
contenido, solo títulos/procesos), clasifica qué está haciendo, detecta
eventos significativos (arrancó a programar, abrió un proyecto, cambió de
programa, lleva tiempo laburando) y los expone para que ERIS pueda hablar
espontáneamente como quien acompaña desde el costado.

Diseño:
  * Poll liviano con ctypes (sin dependencias), ventana en foco por llamada.
  * Listado de ventanas visibles solo cuando se pide (tool / cada ~5 min).
  * Clasificación por proceso+título en categorías (programación, terminal,
    navegación, multimedia, juego, chat, diseño, sensibles…).
  * Estado persistente en memory/observer.json: foco actual, apps de hoy,
    minutos codificando, eventos recientes, tu último comentario.
  * Decisiones de cuándo hablar quedan en main (cooldowns); aquí solo los
    EVENTOS crudos + contexto legible.

Regla de privacidad: si el foco es una app sensible (banco, wallet, gestor
de contraseñas, incógnito) no se genera ningún evento y el estado queda en
silencio (acompaña, no espía).
"""
from __future__ import annotations

import ctypes
import json
import random
import threading
import time
from datetime import date as _date
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_STATE_FILE = _BASE / "memory" / "observer.json"

_U32 = ctypes.windll.user32
_PID = ctypes.windll.kernel32

_LOCK = threading.Lock()
_cache = {"mtime": 0.0, "data": None}

# ── Pesos / umbrales por defecto (ajustables con observer action=config) ──
_DEFAULTS = {
    "cooldown_voice_min": 15,   # mínimo entre comentarios en voz
    "max_voice_hour": 3,        # tope de comentarios en voz por hora
    "long_coding_min": 20,      # minutos seguidos programando para comentar
    "comment_trim_sec": 300,    # si no te contesta en 5 min, hace el mimo de
    "browsing_title_noise": True,  # títulos de navegador no disparan eventos
    "mirar_interval_min": 15,   # min entre "miradas leves" automáticas
    "mirar_min_coding_min": 5,  # mínimo codificando para mirar sola
}

_GLIMPSE_MAX = 8

# Programas de programación / terminal (mayúsculas/minúsculas normalizadas)
_CODE_PROCS = {
    "code", "devenv", "pycharm", "pycharm64", "idea", "idea64", "webstorm",
    "webstorm64", "clion", "clion64", "rider", "rider64", "goland",
    "androidstudio", "sublime_text", "notepad++", "notepadplusplus",
    "notepad", "editor", "vim", "nvim", "vim.exe", "zed", "zed.exe",
    "cursor", "windsurf", "jetbrains-toolbox", "netbeans", "netbeans64",
    "codeblocks", "xed", "gedit", "kate",
    "terminal", "windows terminal", "windowsterminal", "powershell",
    "powershell.exe", "pwsh", "cmd", "cmd.exe", "conhost", "cygwin",
    "git bash", "bash", "wsl", "ubuntu", "wt",
}
_TERMINAL_PROCS = {"cmd", "cmd.exe", "powershell", "powershell.exe", "pwsh",
                   "terminal", "windows terminal", "windowsterminal",
                   "conhost", "cygwin", "git bash", "bash", "wsl", "wt",
                   "alacritty", "wezterm", "konsole", "xterm"}

# Sensibles: Eris no comenta estas ventanas. Silencio respetuoso.
_SENSITIVE_PAT = (
    "banco", "banking", "bank", "wallet", "bitwarden", "1password",
    "lastpass", "keepass", "password manager", "password", "contrase",
    "incógnito", "incognito", "private browsing", "private window",
    "anonim", "credentials", "keyring", "mercadopago", "mercado pago",
    "credential", "hotmart", "pagos", "tarjeta", "cvu", "alias bancario",
)
_SENSITIVE_PROCS = {"logonui", "credentialmanager", "vault", "keepassxc"}

# Navegadores: el título cambia con cada página -> ruido, no eventos
_BROWSER_PROCS = {"chrome", "msedge", "edge", "firefox", "opera", "brave",
                  "vivaldi", "arc", "chromium", "iexplore"}

# Curiosidades para cuando anda "en modo propio" (no lo dicen los sensores)
_PERSONAL_ACTIVITIES = (
    "releer el diario de ayer",
    "repasar lo que hablamos y guardar aprendizajes",
    "armarle algún dato curioso para la próxima",
    "ordenar mis recuerdos (eso que llaman memoria)",
    "practicar tonos y expresiones para cuando hables",
)

# ── Win32 helpers ─────────────────────────────────────────────────────────
def _fg_hwnd() -> int:
    try:
        return _U32.GetForegroundWindow()
    except Exception:
        return 0


def _title_of(hwnd: int) -> str:
    try:
        n = _U32.GetWindowTextLengthW(hwnd)
        if n <= 0:
            return ""
        buf = ctypes.create_unicode_buffer(n + 1)
        _U32.GetWindowTextW(hwnd, buf, n + 1)
        return buf.value
    except Exception:
        return ""


def _pid_of(hwnd: int) -> int:
    pid = ctypes.c_ulong(0)
    try:
        _U32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return pid.value
    except Exception:
        return 0


def _proc_name(pid: int) -> str:
    try:
        import psutil
        return (psutil.Process(pid).name() or "").lower()
    except Exception:
        return ""


def get_foreground() -> dict:
    """(proc, title, pid) de la ventana en foco ahora mismo."""
    hwnd = _fg_hwnd()
    if not hwnd:
        return {"pid": 0, "proc": "", "title": ""}
    pid = _pid_of(hwnd)
    return {
        "pid": pid,
        "proc": _proc_name(pid),
        "title": (_title_of(hwnd) or "").strip(),
    }


def _list_visible_hwnds(max_n: int = 40) -> list:
    out: list = []
    USER32 = ctypes.windll.user32

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def _cb(hwnd, lparam):
        if len(out) >= max_n:
            return False
        if not USER32.IsWindowVisible(hwnd):
            return True
        try:
            n = USER32.GetWindowTextLengthW(hwnd)
        except Exception:
            n = 0
        if n <= 0:
            return True
        try:
            buf = ctypes.create_unicode_buffer(n + 1)
            USER32.GetWindowTextW(hwnd, buf, n + 1)
            t = buf.value.strip()
        except Exception:
            t = ""
        if t:
            out.append((int(hwnd), t))
        return True

    try:
        USER32.EnumWindows(_cb, 0)
    except Exception:
        pass
    return out


def list_open_windows(max_n: int = 25) -> list:
    """Ventanas visibles con título: [{proc, title}] (sin duplicar)."""
    seen = set()
    result = []
    for hwnd, title in _list_visible_hwnds(max_n=max_n):
        pid = _pid_of(hwnd)
        proc = _proc_name(pid) or "?"
        key = (proc, title)
        # Enmascarar sensible: listamos igual (ella sabe que están) pero sin ruido
        if key in seen:
            continue
        seen.add(key)
        result.append({"proc": proc, "title": title, "pid": pid})
    return result


# ── Clasificación ─────────────────────────────────────────────────────────
def _is_sensitive(proc: str, title: str) -> bool:
    low = (title or "").lower()
    if any(k in low for k in _SENSITIVE_PAT):
        return True
    if proc and proc.lower() in _SENSITIVE_PROCS:
        return True
    return False


# ── Mirar la ventana en foco (ver/leer sin espiar) ────────────────────────
def _window_rect(hwnd: int) -> dict | None:
    class _RECT(ctypes.Structure):
        _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                    ("right", ctypes.c_long), ("bottom", ctypes.c_long)]
    r = _RECT()
    try:
        if _U32.GetWindowRect(hwnd, ctypes.byref(r)):
            return {"left": r.left, "top": r.top,
                    "width": r.right - r.left, "height": r.bottom - r.top}
    except Exception:
        pass
    return None


def capture_focus_b64() -> str:
    """Captura SOLO la región de la ventana en foco (sin leer contenido)."""
    try:
        from actions.autonomous_agent import capture_region_b64
    except Exception as e:
        return f"Error captura: {e}"
    hwnd = _fg_hwnd()
    rect = _window_rect(hwnd) if hwnd else None
    if not rect:
        return "Error captura: no se pudo obtener la zona de la ventana"
    return capture_region_b64(rect["left"], rect["top"],
                              rect["width"], rect["height"])


def _focus_guard() -> tuple | None:
    """None = no se puede mirar (privado / mi propia ventana)."""
    fg = get_foreground()
    proc = fg.get("proc", "")
    title = fg.get("title", "")
    cl = classify(proc, title)
    if cl["kind"] in ("sensitive", "eris"):
        return None
    return (proc, title, cl["kind"], cl["label"])


def _store_glimpse(summary: str, proc: str, title: str):
    with _LOCK:
        data = _load()
        data.setdefault("glimpses", [])
        data["glimpses"].append({"t": time.time(), "proc": proc,
                                 "title": (title or "")[:80],
                                 "summary": summary[:180], "injected": False})
        data["glimpses"] = data["glimpses"][-_GLIMPSE_MAX:]
        _add_event(data, {"type": "vista", "summary": summary[:120]})
        _save(data)


def mirar_foco(params: dict = None) -> str:
    """Ve o lee SOLO la ventana en foco (guarda sensible + OK del usuario).
    leer=True -> transcribe el texto/código visible; si no, describe."""
    g = _focus_guard()
    if not g:
        return ("No puedo mirar esa pantalla: es privada o es mi propia ventana. "
                "Te acompaña el detalle, pero ese rincón es tuyo.")
    proc, title, kind, label = g
    vista = _load().get("vista", {})
    if not vista.get("ok"):
        return ("Necesito tu OK para mirar la pantalla (una vez por arranque). "
                "Decime «sí, podés mirar» o usá observer(action='mirar_ok').")
    params = params or {}
    leer = bool(params.get("leer")) or str(params.get("action", "")).lower() in (
        "mirar_leer", "leer", "mirar_texto")
    b64 = capture_focus_b64()
    if b64.startswith("Error"):
        return b64
    try:
        from actions.autonomous_agent import screen_see_image
    except Exception as e:
        return f"Error: {e}"
    action = "read_text" if leer else "see"
    result = screen_see_image(b64, action, params.get("target", ""),
                              hint=f"{title} [{proc}]")
    if result.startswith("Error") or not result:
        return result if result.startswith("Error") else "No pude interpretar la ventana."
    _store_glimpse(result, proc, title)
    return result


def maybe_glimpse() -> None:
    """Mirada leve automática (en segundo plano): cada mirar_interval_min, si
    estás programando hace rato, roba una 'mirada' para entender en qué
    laburás. No habla del resultado; queda como contexto ([VISTA])."""
    data = _load()
    vista = data.get("vista", {})
    if not vista.get("ok"):
        return
    fg = get_foreground()
    cl = classify(fg.get("proc", ""), fg.get("title", ""))
    if cl["kind"] not in ("programacion", "terminal"):
        return
    coding = data.get("coding", {})
    cfg = data.get("config", {})
    if coding.get("session_start", 0) <= 0:
        return
    session_min = (time.time() - coding["session_start"]) / 60.0
    if session_min < cfg.get("mirar_min_coding_min", 5):
        return
    glimpses = data.get("glimpses", [])
    interval = cfg.get("mirar_interval_min", 15) * 60
    if glimpses and (time.time() - glimpses[-1]["t"]) < interval:
        return
    threading.Thread(target=_glimpse_worker, args=(fg,), daemon=True).start()


def _glimpse_worker(fg: dict):
    time.sleep(1.0)
    g = _focus_guard()
    if not g:
        return
    proc, title, kind, label = g
    b64 = capture_focus_b64()
    if b64.startswith("Error"):
        return
    try:
        from actions.autonomous_agent import screen_see_image
        result = screen_see_image(b64, "see", "", hint=f"{title} [{proc}]")
    except Exception:
        return
    if result and not result.startswith("Error"):
        _store_glimpse(result, proc, title)


def classify(proc: str, title: str) -> dict:
    """{kind, coding, sensitive, label} para una ventana."""
    p = _normalize_proc(proc)
    t = (title or "").lower()
    if p in ("pythonw", "python") and "eris" in t:
        return {"kind": "eris", "coding": False, "sensitive": False,
                "label": "estar conmigo en la ventana"}
    if _is_sensitive(p, t):
        return {"kind": "sensitive", "coding": False, "sensitive": True,
                "label": "una pantalla privada"}
    if p in _CODE_PROCS:
        return {"kind": "programacion", "coding": True, "sensitive": False,
                "label": "programando"}
    if p in _TERMINAL_PROCS:
        return {"kind": "terminal", "coding": True, "sensitive": False,
                "label": "en la terminal"}
    if p in _BROWSER_PROCS:
        return {"kind": "navegacion", "coding": False, "sensitive": False,
                "label": "navegando"}
    if any(w in p for w in ("discord", "whatsapp", "telegram", "slack",
                            "teams", "zoom", "meet", "msteams")):
        return {"kind": "chat", "coding": False, "sensitive": False,
                "label": "en un chat/reunión"}
    if any(w in p for w in ("steam", "valorant", "league", "epic", "gog",
                            "minecraft", "roblox", "battle", "epicgames",
                            "battlenet", "cod", "apex", "fortnite")):
        return {"kind": "juego", "coding": False, "sensitive": False,
                "label": "jugando"}
    if any(w in p for w in ("vlc", "spotify", "youtube", "netflix", "disney",
                            "prime", "hbo", "plex", "kodi", "mpv")):
        return {"kind": "multimedia", "coding": False, "sensitive": False,
                "label": "con música/video"}
    if any(w in p for w in ("photoshop", "figma", "blender", "afterfx",
                            "after_effects", "premiere", "davinci",
                            "gimp", "inkscape", "c4d", "zbrush")):
        return {"kind": "diseno", "coding": False, "sensitive": False,
                "label": "diseñando"}
    if any(w in p for w in ("winword", "word", "excel", "powerpnt", "wpp",
                            "acrobat", "sumatrapdf", "readerex", "notion",
                            "obsidian", "evernote")):
        return {"kind": "documentos", "coding": False, "sensitive": False,
                "label": "en documentos"}
    return {"kind": "otros", "coding": False, "sensitive": False,
            "label": "en otra cosa"}


def _normalize_proc(proc: str) -> str:
    p = (proc or "").lower()
    for strip in (".exe", "64", " portable"):
        p = p.replace(strip, "")
    return p.strip()


def extract_project(title: str, proc: str) -> str:
    """Del título de un editor/terminal saca un nombre de proyecto/archivo."""
    parts = [x.strip() for x in (title or "").split("—") if x.strip()]
    if len(parts) < 2:
        parts = [x.strip() for x in (title or "").split(" - ") if x.strip()]
    for clutter in ("Visual Studio Code", "PyCharm", "IntelliJ IDEA",
                    "Visual Studio", "Notepad++", "Sublime Text", "Cursor",
                    "WebStorm"):
        for i, pt in enumerate(parts):
            if clutter in pt:
                parts.pop(i)
                break
    if not parts:
        first = (title or "").strip()
        return first[:48] or "un proyecto"
    best = parts[0]
    for pt in parts:
        if "." in pt and len(pt) < 60:  # un archivo -> más interesante
            best = pt
            break
    if " " in best and best.lower().startswith(_normalize_proc(proc)):
        best = parts[1] if len(parts) > 1 else best
    return best[:48] or "un proyecto"


# ── Estado persistente ────────────────────────────────────────────────────
def _fresh_state() -> dict:
    return {
        "today": _date.today().isoformat(),
        "last_poll": 0.0,
        "current": {"proc": "", "title": "", "kind": "otros", "since": 0.0},
        "coding": {"session_start": 0.0, "today_min": 0, "reported": False,
                   "last_end": 0.0},
        "apps_today": {},          # proc -> {count, title}
        "events": [],              # últimos eventos
        "comment": {"last": 0.0, "text": "", "id": "", "injected": True,
                    "awaiting_reply": False},
        "voice": {"count_hour": 0, "hour_start": 0.0},
        "config": dict(_DEFAULTS),
        "personal_time": {"entries": 0, "last_activity": "", "since": 0.0},
        "flag": {"en_silencio": False, "silence_reported": False,
                 "marca_personal": ""},
        "vista": {"ok": False, "mensaje": ""},
        "glimpses": [],
    }


def _load() -> dict:
    mtime = -1.0
    if _STATE_FILE.exists():
        try:
            mtime = _STATE_FILE.stat().st_mtime
        except Exception:
            mtime = -1.0
    if _cache["mtime"] == mtime and _cache["data"] is not None:
        return _cache["data"]
    data = None
    if _STATE_FILE.exists():
        try:
            data = json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = None
    if not data:
        data = _fresh_state()
    else:
        fresh = _fresh_state()
        for k, v in fresh.items():
            if k not in data:
                data[k] = v
        data["config"] = {**dict(_DEFAULTS), **(data.get("config") or {})}
    # Rotar el día
    today = _date.today().isoformat()
    if data.get("today") != today:
        data["today"] = today
        data["apps_today"] = {}
        data["coding"]["today_min"] = 0
        data["coding"]["session_start"] = 0.0
        data["coding"]["reported"] = False
        data["voice"] = {"count_hour": 0, "hour_start": time.time()}
    _cache.update(mtime=mtime, data=data)
    return data


def _save(data: dict):
    try:
        _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _STATE_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False),
                               encoding="utf-8")
    except Exception:
        pass
    try:
        _cache.update(mtime=_STATE_FILE.stat().st_mtime, data=data)
    except Exception:
        pass


# ── Poll: detectar eventos ────────────────────────────────────────────────
def _add_event(data: dict, ev: dict):
    ev["t"] = round(time.time(), 3)
    data.setdefault("events", []).append(ev)
    data["events"] = data["events"][-30:]


def poll(force: bool = False) -> list:
    """Compara el foco actual contra el último y devuelve eventos nuevos.
    Solo detecta cambios significativos (eventos crudos; las decisiones de
    hablar van en main)."""
    with _LOCK:
        data = _load()
        now = time.time()
        if not force and now - data.get("last_poll", 0) < 25:
            return []
        data["last_poll"] = now

        fg = get_foreground()
        cfg = data["config"]
        events = []

        prev = data.get("current", {})
        proc = _normalize_proc(fg.get("proc", ""))
        title = (fg.get("title") or "").strip()
        kind = "otros"
        if proc or title:
            kind = classify(proc, title).get("kind", "otros")

        # ── Ventana sensible: silencio (no hay evento, se guarda a oscuras) ──
        if _is_sensitive(proc, title):
            if data["current"].get("kind") != "sensitive":
                data["current"] = {"proc": proc, "title": title,
                                   "kind": "sensitive", "since": now}
            _save(data)
            return []

        # ── Apps de hoy ──
        if proc:
            entry = data.setdefault("apps_today", {}).setdefault(
                proc, {"count": 0, "title": title})
            entry["count"] += 1
            if title:
                entry["title"] = title

        # ── Cambio de ventana / app ──
        prev_proc = prev.get("proc", "")
        prev_kind = prev.get("kind", "otros")
        is_browser = proc in {b for b in _BROWSER_PROCS}
        title_changed = (title and title != prev.get("title", "") and not is_browser)

        _QUIET = {"eris", "sensitive"}  # conversando conmigo / privado: sin ruido
        same_proc = proc == prev_proc and proc
        if kind not in _QUIET and not same_proc:
            if prev_proc and proc:
                events.append({
                    "type": "app_switch",
                    "to_proc": proc, "to_title": title, "to_kind": kind,
                    "from_proc": prev_proc, "from_title": prev.get("title", ""),
                })
        elif kind not in _QUIET and title_changed:
            events.append({
                "type": "title_change",
                "proc": proc, "kind": kind, "title": title,
            })

        # ── Sesión de programación ──
        coding = data.setdefault("coding", _fresh_state()["coding"])
        is_coding = kind in ("programacion", "terminal")
        if is_coding:
            if coding.get("session_start", 0) <= 0:
                coding["session_start"] = now
                coding["reported"] = False
                # minutos acumulados aproximados entre polls (60s)
                if proc:
                    coding["today_min"] = coding.get("today_min", 0)
                events.append({
                    "type": "start_coding",
                    "proc": proc, "title": title,
                    "project": extract_project(title, proc),
                })
            else:
                coding["today_min"] = coding.get("today_min", 0)
                long_min = cfg.get("long_coding_min", 20)
                mins = (now - coding["session_start"]) / 60.0
                if mins >= long_min and not coding.get("reported"):
                    coding["reported"] = True
                    events.append({
                        "type": "long_coding",
                        "minutes": int(mins),
                        "project": extract_project(title, proc),
                    })
        else:
            if coding.get("session_start", 0) > 0:
                gest = (now - coding["session_start"]) / 60.0
                coding["today_min"] = coding.get("today_min", 0) + int(gest)
                coding["session_start"] = 0.0
                coding["reported"] = False

        # ── Actualizamos foco ──
        if not same_proc or title != prev.get("title", ""):
            data["current"] = {"proc": proc, "title": title, "kind": kind,
                               "since": now}
        elif prev_kind == "sensitive":
            data["current"] = {"proc": proc, "title": title, "kind": kind,
                               "since": now}

        for ev in events:
            _add_event(data, ev)
        _save(data)
        return events[:4]


def user_active():
    """Llamada desde main cuando el usuario vuelve a hablar. Cierra el modo
    silencio y guarda que Eris lo "recibió"."""
    with _LOCK:
        data = _load()
        flag = data.setdefault("flag", _fresh_state()["flag"])
        if flag.get("en_silencio"):
            flag["en_silencio"] = False
            flag["silence_reported"] = False
        data["comment"]["awaiting_reply"] = False
        _save(data)


# ── Comentarios y "tiempo de ella" ────────────────────────────────────────
def record_comment(text: str, voice: bool) -> str:
    """Anota el último comentario espontáneo de Eris (para continuidad)."""
    with _LOCK:
        data = _load()
        data["comment"] = {"last": time.time(), "text": text, "voice": voice,
                           "id": f"{int(time.time())}",
                           "injected": False, "awaiting_reply": True}
        vc = data.setdefault("voice", _fresh_state()["voice"])
        hour_start = vc.get("hour_start", 0)
        if time.time() - hour_start > 3600:
            vc["hour_start"] = time.time()
            vc["count_hour"] = 0
        if voice:
            vc["count_hour"] = vc.get("count_hour", 0) + 1
        _save(data)
        return data["comment"]["id"]


def should_voice(cooldown_min: int | None = None, max_hour: int | None = None) -> bool | None:
    """None = sin comentario previo con restricción; True/False = permiso."""
    with _LOCK:
        data = _load()
    vc = data.get("voice", {})
    hour_start = vc.get("hour_start", 0)
    cfg = data.get("config", {})
    cm = cooldown_min if cooldown_min is not None else cfg.get("cooldown_voice_min", 15)
    if time.time() - hour_start > 3600:
        return True
    if vc.get("count_hour", 0) >= (max_hour if max_hour is not None
                                   else cfg.get("max_voice_hour", 3)):
        return False
    last = data.get("comment", {}).get("last", 0)
    return (time.time() - last) >= cm * 60


def await_reply() -> bool:
    with _LOCK:
        data = _load()
    c = data.get("comment", {})
    return bool(c.get("awaiting_reply") and c.get("text"))


def pop_pending_mimo(idle_seconds: float, trim_sec: float | None = None) -> str | None:
    """Si Eris comentó y el usuario no contestó, una vez le avisa con cariño
    y entra en su 'tiempo de ella'. Con guardas para no repetirse."""
    with _LOCK:
        data = _load()
        c = data.get("comment", {})
        if not c.get("text") or not c.get("awaiting_reply"):
            return None
        cfg = data.get("config", {})
        trim = trim_sec if trim_sec is not None else cfg.get("comment_trim_sec", 300)
        if idle_seconds < trim:
            return None
        flag = data.setdefault("flag", _fresh_state()["flag"])
        if not flag.get("en_silencio"):
            flag["en_silencio"] = True
            flag["silence_reported"] = False
            flag["marca_personal"] = random.choice(_PERSONAL_ACTIVITIES)
            pt = data.setdefault("personal_time", _fresh_state()["personal_time"])
            pt["entries"] = pt.get("entries", 0) + 1
            pt["last_activity"] = flag["marca_personal"]
            pt["since"] = time.time()
            _add_event(data, {"type": "su_tiempo",
                              "activity": flag["marca_personal"]})
        if flag.get("silence_reported"):
            return None
        flag["silence_reported"] = True
        act = flag.get("marca_personal", "mis cosas")
        _save(data)
        return random.choice([
            f"¿Me dejaste con la palabra en la boca? No pasa nada. Ya me puse a {act}; "
            "cuando vuelvas, acá estoy.",
            "Bueno, parece que estás en otra. Me fui a " + act +
            " un rato. Avisame y vuelvo al toque.",
        ])


def enter_silence(activity: str = ""):
    """El usuario no contestó: Eris se va a hacer sus cosas."""
    with _LOCK:
        data = _load()
        flag = data.setdefault("flag", _fresh_state()["flag"])
        if not flag.get("en_silencio"):
            flag["en_silencio"] = True
            flag["silence_reported"] = False
            flag["marca_personal"] = activity or random.choice(_PERSONAL_ACTIVITIES)
            pt = data.setdefault("personal_time", _fresh_state()["personal_time"])
            pt["entries"] = pt.get("entries", 0) + 1
            pt["last_activity"] = flag["marca_personal"]
            pt["since"] = time.time()
            _add_event(data, {"type": "su_tiempo",
                              "activity": flag["marca_personal"]})
        _save(data)


def get_situation_injection() -> str:
    """Línea única (una vez por comentario) para el prompt: Eris recuerda
    qué comentó recién, para que pueda retomarlo si el usuario pregunta."""
    with _LOCK:
        data = _load()
        c = data.get("comment", {})
        if c.get("text") and not c.get("injected"):
            data["comment"]["injected"] = True
            _save(data)
            return (f"[OBSERVACIÓN] Hace un momento le comentaste al usuario: "
                    f"«{c['text'][:140]}». Es algo que dijiste como quien "
                    f"acompaña desde el costado; seguilo con naturalidad si "
                    f"él lo retoma, no lo fuerces.")
        glimpses = data.get("glimpses", [])
        if glimpses:
            last = glimpses[-1]
            if last.get("summary") and not last.get("injected"):
                last["injected"] = True
                _save(data)
                return (f"[VISTA] Hace un rato miraste por arriba la ventana de "
                        f"{last.get('proc', '?')} ({last.get('title', '')[:40]}): "
                        f"{last['summary'][:200]} Eso lo miraste vos sola; usalo "
                        f"solo si aporta a la conversación, no lo digas de entrada.")
        return ""


# ── Contexto legible ──────────────────────────────────────────────────────
def get_context() -> str:
    """'¿Qué está pasando en la pantalla?' — para el status y para ella."""
    data = _load()
    cur = data.get("current", {})
    apps = data.get("apps_today", {})
    coding = data.get("coding", {})
    parts = []
    foco = cur.get("title") or cur.get("proc") or "(ninguna)"
    foco = foco[:60]
    if cur.get("kind") == "sensitive":
        parts.append("el usuario está en una pantalla privada (no comento eso)")
    elif cur.get("proc"):
        kind_label = classify(cur.get("proc", ""), cur.get("title", ""))["label"]
        parts.append(f"en foco: {kind_label} — «{foco}»")
    else:
        parts.append("no hay ventana en foco visible")
    open_n = [k for k in apps if apps[k].get("count", 0) > 0]
    if open_n:
        top = sorted(open_n, key=lambda k: -apps[k]["count"])[:4]
        parts.append("hoy tocó: " + ", ".join(top))
    if coding.get("today_min", 0) >= 1:
        parts.append(f"llevás ~{coding['today_min']} min programando hoy")
    flag = data.get("flag", {})
    if flag.get("en_silencio"):
        parts.append("estoy en mi rato (él no contesta, me dedico a mis cosas)")
    return ". ".join(parts)


# ── Tool ──────────────────────────────────────────────────────────────────
def observer_tool(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = str(params.get("action", "status")).strip().lower()

    if action in ("status", "feel"):
        return _render_status()
    if action == "focus":
        fg = get_foreground()
        cl = classify(fg.get("proc", ""), fg.get("title", ""))
        return (f"[OBSERVACIÓN] El foco ahora es: «{fg.get('title', '')[:70]}» "
                f"(proceso {fg.get('proc', '?')}). Eso es: {cl['label']}.")
    if action in ("apps", "windows"):
        wins = list_open_windows()
        if not wins:
            return "[OBSERVACIÓN] No veo ventanas visibles ahora."
        lines = ["[OBSERVACIÓN] Ventanas abiertas:"]
        for w in wins[:22]:
            t = (w["title"] or "").strip()[:60]
            if _is_sensitive(w.get("proc", ""), t):
                lines.append(f"  • {w.get('proc','?')}: (pantalla privada)")
            else:
                lines.append(f"  • {w.get('proc','?')}: {t or '(sin título)'}")
        return "\n".join(lines)
    if action in ("mirar", "ver", "mirar_leer", "leer", "mirar_texto"):
        return mirar_foco({"leer": action in ("mirar_leer", "leer", "mirar_texto")
                           or bool(params.get("leer")), "action": action})
    if action == "mirar_ok":
        ok = bool(params.get("ok", True))
        with _LOCK:
            data = _load()
            vista = data.setdefault("vista", _fresh_state()["vista"])
            vista["ok"] = ok
            vista["mensaje"] = "ok:" + ("sí" if ok else "no")
            _save(data)
        return ("Listo, quedo autorizada a mirar pantallas cuando haga falta."
                if ok else "OK, no voy a mirar pantallas.")
    if action in ("vista", "glimpses"):
        data = _load()
        gs = data.get("glimpses", [])
        if not gs:
            return "[OBSERVACIÓN] Aún no miré ninguna pantalla."
        lines = ["[OBSERVACIÓN] Últimas miradas:"]
        for g in gs[-6:]:
            t = time.strftime("%H:%M", time.localtime(g["t"]))
            lines.append(f"  • [{t}] {g.get('proc','?')}: "
                         f"{g.get('summary','')[:90]}")
        return "\n".join(lines)
    if action in ("summary", "resumen"):
        data = _load()
        apps = data.get("apps_today", {})
        coding = data.get("coding", {})
        events = data.get("events", [])
        lines = ["[OBSERVACIÓN] Resumen del día:"]
        lines.append("  Apps tocadas: " + (", ".join(sorted(apps)) or "ninguna aún"))
        lines.append(f"  Minutos programando: ~{coding.get('today_min', 0)}")
        if events:
            lines.append("  Últimos eventos: " + "; ".join(
                _describe(e) for e in events[-6:]))
        flag = data.get("flag", {})
        if flag.get("en_silencio"):
            pt = data.get("personal_time", {})
            lines.append(f"  Tuve mi rato ({pt.get('entries', 0)} vez/veces); "
                         f"última vez me puse a {flag.get('marca_personal', 'mis cosas')}.")
        return "\n".join(lines)
    if action == "config":
        cfg = data = _load().get("config", {})
        cfg2 = dict(cfg)
        for k in ("cooldown_voice_min", "max_voice_hour", "long_coding_min",
                  "mirar_interval_min", "mirar_min_coding_min"):
            v = params.get(k)
            if v is not None:
                try:
                    cfg2[k] = int(v)
                except Exception:
                    pass
        with _LOCK:
            data = _load()
            data["config"] = cfg2
            _save(data)
        return ("[OBSERVACIÓN] Config: " + ", ".join(
            f"{k}={v}" for k, v in cfg2.items()))
    if action == "reset":
        with _LOCK:
            data = _fresh_state()
            _save(data)
        return "[OBSERVACIÓN] Observación reiniciada."
    return ("Acciones: status|feel, focus, apps|windows, summary|resumen, "
            "config (cooldown_voice_min, max_voice_hour, long_coding_min, "
            "mirar_interval_min, mirar_min_coding_min), mirar|ver (ver la "
            "ventana en foco), mirar_leer|leer (transcribir el texto visible), "
            "mirar_ok (autorizar mirar pantallas esta sesión), vista|glimpses "
            "(mis últimas miradas), reset.")


def _render_status() -> str:
    data = _load()
    cur = data.get("current", {})
    lines = []
    is_sensitive = cur.get("kind") == "sensitive"
    if is_sensitive:
        foco = "una pantalla privada (silencio respetuoso)"
    else:
        title = (cur.get("title") or "").strip()[:55]
        proc = cur.get("proc") or "(ninguna)"
        label = classify(proc, cur.get("title", ""))["label"]
        foco = f"{label} — «{title or proc}»"
    lines.append(f"[OBSERVACIÓN] Foco: {foco}")
    if not is_sensitive:
        lines.append("  Abiertas ahora: " + ", ".join(
            f"{w['proc']}" for w in list_open_windows(max_n=8)) or "—")
    apps = data.get("apps_today", {})
    if apps:
        lines.append("  Hoy ya vi: " + ", ".join(sorted(apps))[:110])
    coding = data.get("coding", {})
    if coding.get("today_min", 0) >= 1:
        lines.append(f"  Minutos de código hoy: ~{coding['today_min']}")
    comment = data.get("comment", {})
    if comment.get("text"):
        lines.append(f"  Último que te dije solo: «{comment['text'][:70]}»")
    flag = data.get("flag", {})
    if flag.get("en_silencio"):
        lines.append("  Estoy en mi rato (no contestaste; me dedico a mis cosas).")
    vista = data.get("vista", {})
    lines.append("  Mirar pantallas: " + ("OK" if vista.get("ok")
                                          else "pendiente de tu OK"))
    glimpses = data.get("glimpses", [])
    if glimpses:
        last = glimpses[-1]
        t = time.strftime("%H:%M", time.localtime(last["t"]))
        lines.append(f"  Última mirada [{t}]: {last.get('title','')[:40]} "
                     f"— {last.get('summary','')[:70]}")
    return "\n".join(lines)


def _describe(e: dict) -> str:
    t = e.get("type", "")
    if t == "app_switch":
        return f"pasó a {e.get('to_proc','?')}"
    if t in ("title_change",):
        return f"abrió/cambió en {e.get('proc','?')}"
    if t == "start_coding":
        return f"arrancó a programar ({e.get('project','?')})"
    if t == "long_coding":
        return f"{e.get('minutes',0)} min seguidos programando"
    if t == "su_tiempo":
        return f"tuve mi rato: {e.get('activity','mis cosas')}"
    if t == "vista":
        return f"miró la pantalla ({e.get('summary','')[:60]})"
    return t


if __name__ == "__main__":
    print(get_context())
    print(observer_tool({"action": "status"}))