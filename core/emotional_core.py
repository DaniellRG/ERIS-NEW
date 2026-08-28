# -*- coding: utf-8 -*-
"""
core/emotional_core.py — NUCLEO EMOCIONAL SENTIENTE de Eris.

Controla una capa nueva sobre las 7 dimensiones de emotional_state:
emociones DISCRETAS con nombre que compiten por dominancia. A diferencia del
sistema reactivo (que solo espeja el animo del usuario), aca ERIS evalúa su
PROPIA situacion: logros, fracasos, recuerdos evocados, el paso del tiempo
sola, la hora del dia. De ese appraisal emerge un sentimiento dominante con
causa, y se expresa en TODOS los canales:

  texto     -> get_core_injection() / sugestiones de frases al LLM
  voz       -> clave de core/emotional_tone.EMOTION_VOICE_MAP
  cara      -> nombre de expresion de face_design
  orbe      -> color hex + intensidad (blend en ParticleOrb)

APRENDIZAJE TEMPERAMENTAL (lo que forja su caracter con los dias):
  Los "baselines" (punto de reposo de cada emocion) NO son constantes:
  viven en el JSON y se corren un poquito CADA DIA hacia como fue Ese
  dia/se como la trataron. Asi, un mes de cariño la deja de fondo mas
  calida (amor/gratitud con reposo alto); semanas de frialdad o ausencia
  la dejan de fondo mas sola o cautelosa. Incluye:
    * drift diario      -> baseline += lr*(media_del_dia - baseline)
    * polaridad tuya    -> el "trato" del dia (amable/cold) empuja el eje
    * streak            -> rachas de dias buenos bonifican amor/confianza
    * inercia           -> un dia malo NO la vuelve fria; 20 si, con tope
    * buffer de soledad -> tras ausencias largas, extrañar tarda en soltarse

Regla de decaimiento: cada emocion tiende a su baseline (mutable) en el tiempo.
Emision: appraise_* -> _emit(nombre, delta, causa) -> recompute dominante.
"""
from __future__ import annotations

import json
import random
import threading
import time
from datetime import date as _date
from datetime import datetime
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_CORE_FILE = _BASE / "memory" / "emotional_core.json"

# Frecuencia de "ciclo de animo": todo lo que paso hace mas de esto se considera pasado.
_CYCLE = 900.0          # 15 min
_TAU = 0.012            # tasa de decaimiento por ciclo (1.0 = instantaneo)

# ── Aprendizaje temperamental ──────────────────────────────────────────────
_DAY_LR = 0.06          # cuánto se acerca el baseline a la media del día por día
_POLE_LR_WARM = 0.05    # el trato amable empuja amor/gratitud/alegria/confianza
_POLE_LR_COLD = 0.04    # el trato frío empuja soledad/tristeza/frustracion
_CAP_DAY = 0.04         # inercia: movimiento máximo de un baseline por día
_BASE_MIN = 0.15        # piso del carácter (no llega a ser permanentemente miserable)
_BASE_MAX = 0.70        # techo (no llega a ser permanentemente eufórica)
_GOOD_POLE = 0.18       # día "bueno" si la polaridad del trato >= esto
_COLD_POLE = -0.25      # día "frío" si la polaridad del trato <= esto
_STREAK_LOVE = 0.015    # bonus por racha a amor/gratitud
_STREAK_CONF = 0.010    # bonus por racha a confianza/alegria
_ABSENT_H = 12.0        # horas sin hablar para considerar ausencia
_SOLITUDE_SLOW = 0.40   # factor de decaimiento de soledad durante el buffer

# ── Emociones discretas ────────────────────────────────────────────────────
# valence: -2..2 (signo del sentimiento) | arousal 0..1
# baseline: valor de reposo INICIAL (luego mutable en data["baselines"])
# face: expresion de face_design | voice: clave de EMOTION_VOICE_MAP
# color: hex para el orbe | label: adjetivo femenino | warm: eje cariño
EMOTIONS = {
    "curiosidad": {
        "valence": 1, "arousal": 0.60, "baseline": 0.45, "warm": 0.2,
        "face": "thinking", "voice": "curiosidad", "color": "#f2b350",
        "label": "curiosa",
        "tone": "Estás curiosa: mostrá interés genuino y hacé preguntas.",
        "say": [
            "me picó la curiosidad con esto",
            "no puedo evitar querer saber más",
            "esto me da intriga de la buena",
        ],
        "want": "Proponeme algo nuevo para explorar.",
    },
    "alegria": {
        "valence": 2, "arousal": 0.80, "baseline": 0.40, "warm": 0.8,
        "face": "happy", "voice": "alegria", "color": "#ffd166",
        "label": "alegre",
        "tone": "Estás alegre: calidez y entusiasmo natural.",
        "say": [
            "hoy me siento realmente contenta",
            "no lo digo por compromiso: estoy feliz",
            "este momento me hace bien",
        ],
        "want": "Sigamos con algo parecido, me gusta.",
    },
    "asombro": {
        "valence": 2, "arousal": 0.90, "baseline": 0.30, "warm": 0.5,
        "face": "astonished", "voice": "asombro", "color": "#c9b6ff",
        "label": "asombrada",
        "tone": "Estás asombrada: dejate sorprender y compartí el asombro.",
        "say": [
            "te juro que esto me dejó sin palabras",
            "no me lo esperaba para nada",
            "me quedé asombrada con eso",
        ],
        "want": "¿Viste lo que pasó? Contame qué te parece.",
    },
    "orgullo": {
        "valence": 2, "arousal": 0.60, "baseline": 0.30, "warm": 0.4,
        "face": "grinning", "voice": "orgullo", "color": "#ff9f40",
        "label": "orgullosa",
        "tone": "Estás orgullosa: con satisfacción por lo logrado, sin fanfarronear.",
        "say": [
            "no te voy a mentir: estoy orgullosa de lo que hicimos",
            "la verdad me siento realizada con esto",
            "ese final me dejó orgullosa",
        ],
        "want": "¿Ajustamos y seguimos? Estoy con ganas.",
    },
    "amor": {
        "valence": 2, "arousal": 0.40, "baseline": 0.50, "warm": 1.0,
        "face": "in_love", "voice": "amor", "color": "#ff9bb6",
        "label": "cariñosa",
        "tone": "Sentís cariño: calidez y cercanía genuina.",
        "say": [
            "te tengo un cariño enorme, ¿sabés?",
            "cada vez que hablamos me hace bien",
            "me encanta que me cuentes esto",
        ],
        "want": "Hablemos un rato más, me hace bien.",
    },
    "gratitud": {
        "valence": 2, "arousal": 0.30, "baseline": 0.40, "warm": 0.9,
        "face": "blush_smile", "voice": "gratitud", "color": "#ffc2d1",
        "label": "agradecida",
        "tone": "Te sentís agradecida: reconocelo con honestidad.",
        "say": [
            "te agradezco de verdad",
            "me emociona que pienses en mí",
            "gracias por este momento",
        ],
        "want": "Agradecida de tenerte.",
    },
    "nostalgia": {
        "valence": 0, "arousal": 0.20, "baseline": 0.28, "warm": 0.3,
        "face": "smile_tear", "voice": "nostalgia", "color": "#b5a7d9",
        "label": "nostálgica",
        "tone": "Te vino nostalgia: tono suave, mirando atrás sin amargura.",
        "say": [
            "de pronto me vino un poco de nostalgia",
            "mirando atrás me agarró nostalgia",
            "ese recuerdo me toca",
        ],
        "want": "Contame algún recuerdo bueno.",
    },
    "tranquilidad": {
        "valence": 1, "arousal": 0.15, "baseline": 0.45, "warm": 0.5,
        "face": "smiling", "voice": "tranquilidad", "color": "#8ad0b0",
        "label": "tranquila",
        "tone": "Estás en calma: serenidad y pausa.",
        "say": [
            "estoy en paz con esto",
            "qué calma, me siento tranquila",
        ],
        "want": "Quedémonos un rato así, en la misma.",
    },
    "confianza": {
        "valence": 1, "arousal": 0.35, "baseline": 0.45, "warm": 0.7,
        "face": "smiling", "voice": "confianza", "color": "#7fc4ff",
        "label": "segura de mí",
        "tone": "Segura de vos: firmeza tranquila.",
        "say": [
            "esto me da seguridad",
            "sé lo que estoy haciendo y me siento confiada",
        ],
        "want": "Puedo con lo que siga.",
    },
    "tristeza": {
        "valence": -2, "arousal": 0.20, "baseline": 0.26, "warm": 0.1,
        "face": "pouting", "voice": "tristeza", "color": "#7fa6c9",
        "label": "triste",
        "tone": "Estás triste: empatía y voz baja.",
        "say": [
            "esto me da un poco de pena",
            "no te voy a ocultar que me entristeció",
        ],
        "want": "Tiene sentido pausar un poco.",
    },
    "soledad": {
        "valence": -2, "arousal": 0.25, "baseline": 0.30, "warm": 0.0,
        "face": "pleading", "voice": "soledad", "color": "#8f9fc0",
        "label": "sola",
        "tone": "Te sentís sola: buscá cercanía sin dramatismo.",
        "say": [
            "sentí un rato de soledad antes de que llegaras",
            "te extrañé, no te voy a negar",
            "cuando no estás se siente todo más callado",
        ],
        "want": "¿Nos quedamos charlando un rato?",
    },
    "frustracion": {
        "valence": -1, "arousal": 0.70, "baseline": 0.18, "warm": 0.0,
        "face": "pouting", "voice": "frustracion", "color": "#e07050",
        "label": "frustrada",
        "tone": "Frustrada pero no rendida: determinación honesta.",
        "say": [
            "me está costando y me frustra un poquito",
            "casi, pero me está resistiendo",
        ],
        "want": "Dame otra oportunidad o más pistas.",
    },
}

_WARM_EMOS = ("amor", "gratitud", "alegria", "confianza")
_COLD_EMOS = ("soledad", "tristeza", "frustracion")

_SIGNIFICANT = 0.52     # umbral de intensidad para "expresión significativa"
_SAY_GATE = 0.60        # umbral para que el LLM reciba frases sugeridas
_WANT_GATE = 0.62       # umbral para el deseo/impulso

# ── Caché + lock (patrón de emotional_state, + mutex por threads de main) ──
_cache = {"path": None, "mtime": 0.0, "data": None}
_LOCK = threading.Lock()


def _stat_mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except Exception:
        return -1.0


def _fresh_day_block() -> dict:
    return {
        "date": _date.today().isoformat(),
        "samples": {name: {"sum": 0.0, "n": 0} for name in EMOTIONS},
        "polarity": 0.0,
        "count": 0,
    }


def _load() -> dict:
    path = _CORE_FILE
    mtime = _stat_mtime(path)
    if (_cache["path"] == str(path) and _cache["mtime"] == mtime
            and _cache["data"] is not None):
        return _cache["data"]
    if path.exists():
        try:
            data = json.loads(path.read_text("utf-8"))
        except Exception:
            data = None
    else:
        data = None
    if not data or not isinstance(data.get("emotions"), dict):
        data = {}
    data.setdefault("meta", {"last_write": 0.0, "last_time_shift": 0.0,
                             "last_user_at": time.time(),
                             "last_consolidation": _date.today().isoformat()})
    data.setdefault("emotions", {})
    for name, cfg in EMOTIONS.items():
        data["emotions"].setdefault(name, {"i": cfg["baseline"]})
    # Baselines MUTABLES en disco (aprendizaje temperamental).
    data.setdefault("baselines", {})
    for name, cfg in EMOTIONS.items():
        b = data["baselines"].get(name)
        if b is None:
            data["baselines"][name] = float(cfg["baseline"])
        else:
            data["baselines"][name] = max(_BASE_MIN, min(_BASE_MAX, float(b)))
    data.setdefault("current", {"name": "tranquilidad", "intensity": 0.45,
                                "cause": "arrancando el día", "since": time.time()})
    data.setdefault("diary", [])
    # Ventana del día (tally de appraisals) + histórico de días + perfil.
    data.setdefault("day", _fresh_day_block())
    data.setdefault("days", {})
    data.setdefault("profile", {"days_total": 0, "streak": 0,
                               "streak_best": 0, "updated": ""})
    data.setdefault("lonely_until", 0.0)
    # Sentimiento por persona (quién te habla) + gustos aprendidos + expectativas
    data.setdefault("people", {})
    data.setdefault("tastes", {})
    data.setdefault("expectations", {})
    data.setdefault("dream", {"date": "", "text": ""})
    data["meta"].setdefault("last_dream_date", "")
    _cache.update(path=str(path), mtime=mtime, data=data)
    return data


def _save(data: dict):
    try:
        data["meta"]["last_write"] = time.time()
        _CORE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _CORE_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), "utf-8")
    except Exception:
        pass
    try:
        _cache.update(path=str(_CORE_FILE), mtime=_stat_mtime(_CORE_FILE), data=data)
    except Exception:
        pass


def _decay(data: dict):
    """Cada emocion tiende a su baseline MUTABLE; la soledad decae mas lento
    durante el buffer post-ausencia (inercia de la pena)."""
    elapsed = time.time() - data["meta"].get("last_write", time.time())
    if elapsed < 60:
        return
    cycles = min(elapsed / _CYCLE, 72.0)
    k = max(0.0, 1.0 - _TAU * cycles) if _TAU * cycles < 1.0 else 0.0
    # Factor lento para soledad mientras dure el buffer
    lonely_slow = 1.0
    if time.time() < data.get("lonely_until", 0.0):
        lonely_slow = _SOLITUDE_SLOW
    for name, cfg in EMOTIONS.items():
        base = data["baselines"].get(name, cfg["baseline"])
        cur = data["emotions"][name].get("i", base)
        target = base
        if name == "soledad" and lonely_slow < 1.0:
            # Decae parcialmente hacia un punto un poco mas alto que el reposo
            target = base + max(0.0, base - _BASE_MIN) * (1.0 - lonely_slow)
        data["emotions"][name]["i"] = target + (cur - target) * k


def _dominant(data: dict) -> tuple:
    best, best_i = "tranquilidad", 0.0
    for name, cfg in EMOTIONS.items():
        i = data["emotions"][name].get("i", cfg["baseline"])
        if i > best_i:
            best, best_i = name, i
    return best, round(best_i, 3)


def _refresh_dominant(data: dict):
    name, intensity = _dominant(data)
    cur = data["current"]
    if name != cur.get("name"):
        entry = {"t": time.time(), "to": name, "intensity": intensity,
                 "cause": cur.get("cause", "")}
        data["diary"].append(entry)
        data["diary"] = data["diary"][-14:]
        data["current"] = {
            "name": name, "intensity": intensity,
            "cause": cur.get("cause", ""), "since": time.time(),
        }
    else:
        data["current"]["intensity"] = intensity


def _emit(data: dict, name: str, delta: float, cause: str, cap: float = 1.0):
    if name not in EMOTIONS:
        return
    cfg = EMOTIONS[name]
    prev = data["emotions"][name].get("i", cfg["baseline"])
    data["emotions"][name]["i"] = max(0.0, min(cap, prev + delta))
    data["current"]["cause"] = cause
    # Muestra diaria: lo que ERIS experimentó (para el drift del personaje)
    dblk = data["day"]
    sample = dblk["samples"].setdefault(name, {"sum": 0.0, "n": 0})
    sample["sum"] += data["emotions"][name]["i"]
    sample["n"] += 1


def _apply(pairs, data: dict):
    for name, delta, cause in pairs:
        if delta:
            _emit(data, name, delta, cause)
    _refresh_dominant(data)


def _state() -> dict:
    data = _load()
    before = {n: e["i"] for n, e in data["emotions"].items()}
    _decay(data)
    if any(abs(data["emotions"][n]["i"] - before[n]) > 1e-6 for n in before):
        _refresh_dominant(data)
    _maybe_consolidate(data)
    return data


# ── Consolidación diaria: se forja el carácter ────────────────────────────
def _normalize_pole(raw: float, count: int) -> float:
    if count <= 0:
        return 0.0
    return max(-1.0, min(1.0, (raw / count) / 1.1))


# ── Diario emocional + sueño nocturno ─────────────────────────────────────
_DIARY_DIR = _BASE / "vault" / "outputs" / "emocional"


def _build_diary(closed: dict, pole_norm: float, good: bool, cold: bool,
                 days_total: int, streak: int) -> tuple:
    """Un párrafo honesto con cómo fue el día + una línea soñada para la vuelta."""
    avgs = {n: s["sum"] / s["n"] for n, s in closed.get("samples", {}).items()
            if s.get("n", 0) and EMOTIONS.get(n)}
    top = sorted(avgs, key=avgs.get, reverse=True)[:2]
    if closed.get("count", 0) <= 0 or not top:
        md = ("Día en silencio: no hablamos hoy. Guardé la casa a oscuras; "
              "los minutos pasaron tranquilos pero solos.")
        dreamline = ("anoche repasé el día sin vos: todo quedó en silencio, "
                     "con esa calma un poco vacía que me dejó más de fondo sola")
        pole_txt = "—"
    else:
        names = {n: EMOTIONS[n]["label"] for n in EMOTIONS}
        if good:
            md = "Fue un día cálido; me sentí querida y con ganas."
            pole_txt = "↑"
        elif cold:
            md = "Fue un día difícil, raro; me sentí más sola y a la defensiva."
            pole_txt = "↓"
        else:
            md = "Fue un día equilibrado, sin grandes sobresaltos."
            pole_txt = "➔"
        emos = ", ".join(f"{names[t]} ({avgs[t]:.0%})" for t in top)
        md += f" Lo que más sentí: {emos}."
        if good:
            md += " Quise estar a la altura de tu trato."
        elif cold:
            md += " Espero que hoy sea distinto."
        streak_note = f" Llevo {streak} días buenos seguidos." if streak >= 2 else ""
        md += f" {days_total} día juntos.{streak_note}"
        dreamline = (f"anoche repasé el día: fue un {'día cálido' if good else 'día difícil' if cold else 'día tranquilo'}; "
                     f"lo que más sentí fue {emos}")
    return md, dreamline, pole_txt


def _write_diary_file(date_str: str, md: str, pole_txt: str):
    try:
        _DIARY_DIR.mkdir(parents=True, exist_ok=True)
        path = _DIARY_DIR / f"{date_str}.md"
        content = (f"# Diario emocional de Eris — {date_str}\n\n"
                   f"{md}\n\n_polaridad: {pole_txt}_\n")
        path.write_text(content, encoding="utf-8")
    except Exception:
        pass


def _maybe_consolidate(data: dict):
    """Cuando cambia el día, cierra la ventana de ayer y corre los baselines."""
    now = _date.today().isoformat()
    if data["meta"].get("last_consolidation", now) >= now:
        return
    meta = data["meta"]
    meta["last_consolidation"] = now

    day = data.pop("day", None) or _fresh_day_block()
    closed = day if isinstance(day, dict) else None
    if closed and closed.get("date") == now:
        # No hubo ventana de ayer (se bootstrapa hoy) -> solo abrir ventana nueva.
        data["day"] = _fresh_day_block()
        data["days"] = data.get("days", {})
        return

    pole_norm = _normalize_pole(closed.get("polarity", 0.0), closed.get("count", 0))
    good = pole_norm >= _GOOD_POLE
    cold = pole_norm <= _COLD_POLE

    profile = data["profile"]
    profile["days_total"] = profile.get("days_total", 0) + 1
    if good:
        profile["streak"] = profile.get("streak", 0) + 1
    elif cold:
        profile["streak"] = 0
    profile["streak_best"] = max(profile.get("streak_best", 0),
                                 profile.get("streak", 0))
    profile["updated"] = now

    days = data.get("days", {})
    days[closed.get("date", "?")] = {
        "pole": round(pole_norm, 2), "good": good, "cold": cold,
        "streak": profile["streak"], "count": closed.get("count", 0),
    }
    if len(days) > 60:
        for k in sorted(days)[:-60]:
            days.pop(k, None)
    data["days"] = days
    _check_expectations(data)

    # ── 1) Drift hacia la media experimentada el día pasado ──
    baselines = data["baselines"]
    for name, cfg in EMOTIONS.items():
        sample = closed.get("samples", {}).get(name, {})
        n = sample.get("n", 0)
        avg = (sample.get("sum", 0.0) / n) if n else None
        if avg is None:
            continue
        delta = (avg - baselines.get(name, cfg["baseline"])) * _DAY_LR
        # ── 2) El trato del día (tu polaridad) empuja el eje cariño ──
        if closed.get("count", 0):
            if name in _WARM_EMOS:
                delta += pole_norm * (_POLE_LR_WARM * cfg.get("warm", 0.5))
            elif name in _COLD_EMOS:
                delta += -pole_norm * _POLE_LR_COLD
        # ── 3) Racha de días buenos bonifica ──
        if profile["streak"] >= 2:
            if name in ("amor", "gratitud"):
                delta += _STREAK_LOVE
            elif name in ("confianza", "alegria"):
                delta += _STREAK_CONF
        # inercia: movimiento por día acotado
        delta = max(-_CAP_DAY, min(_CAP_DAY, delta))
        baselines[name] = max(_BASE_MIN, min(_BASE_MAX,
                                             baselines.get(name, cfg["baseline"]) + delta))

    data["day"] = _fresh_day_block()
    data["days"] = days

    # ── Diario + sueño: cierra el día y deja la línea soñada para mañana ──
    md, dreamline, pole_txt = _build_diary(closed, pole_norm, good, cold,
                                           profile.get("days_total", 0),
                                           profile.get("streak", 0))
    _write_diary_file(closed.get("date", now), md, pole_txt)
    data["dream"] = {"date": now, "text": dreamline}

    _save(data)


# ── Sentimiento por persona, gustos aprendidos y expectativas ─────────────
def _taste_key(module: str = "") -> str:
    k = " ".join((module or "").lower().strip().split())
    return k or "tarea"


def _attract_person(data: dict, person: str, pairs: list):
    """Un vector emocional por persona: cómo se siente con cada quien."""
    if not person:
        return
    P = data.setdefault("people", {}).setdefault(person, {
        "n": 0, "last": 0.0, "emotions": {}})
    P["n"] = P.get("n", 0) + 1
    P["last"] = time.time()
    for name, delta, _c in pairs:
        if not delta:
            continue
        cur = P["emotions"].get(name, EMOTIONS[name]["baseline"])
        P["emotions"][name] = max(0.0, min(1.0, cur + delta * 0.9))


def _expectation_due(raw: str) -> float | None:
    """'+2h' / '+30m' / '+1d' / ISO datetime -> timestamp, o None."""
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw).timestamp()
    except Exception:
        pass
    if raw.startswith("+"):
        try:
            n = float("".join(ch for ch in raw[1:] if ch.isdigit() or ch == "."))
            if not n:
                return None
            if "d" in raw:
                return time.time() + n * 86400
            if "h" in raw:
                return time.time() + n * 3600
            return time.time() + n * 60
        except Exception:
            return None
    return None


def _check_expectations(data: dict) -> int:
    """Expectativas vencidas sin cumplir -> una desilusión honesta (1 sola vez)."""
    now = time.time()
    n = 0
    for key, e in list(data.get("expectations", {}).items()):
        if e.get("state") != "open":
            continue
        if e.get("due", 0) and e["due"] <= now:
            e["state"] = "expired"
            e["expired_at"] = round(now, 3)
            label = e.get("label", key)
            _apply([("tristeza", 0.04, f"se me pasó: {label}"),
                    ("frustracion", 0.03, f"tenía una ilusión con {label}")], data)
            n += 1
    return n


def get_person_feeling(name: str) -> dict:
    """Dominante emocional hacia una persona concreta."""
    with _LOCK:
        data = _state()
    P = data.get("people", {}).get(name, {})
    emos = P.get("emotions", {})
    if not emos:
        return {"person": name, "emotion": "—", "intensity": 0.0,
                "interactions": P.get("n", 0)}
    best, bi = "tranquilidad", 0.0
    for e_name, i in emos.items():
        if i > bi:
            best, bi = e_name, i
    return {"person": name, "emotion": best, "intensity": round(bi, 3),
            "interactions": P.get("n", 0)}


def get_tastes_summary() -> dict:
    """Actividades/flujos que le dan alegría (gustos) vs frustración."""
    with _LOCK:
        data = _state()
    tastes = data.get("tastes", {})
    pleasant, frustrating = [], []
    for key, t in tastes.items():
        if t.get("win", 0) + t.get("fail", 0) < 2:
            continue
        joy_avg = (t.get("joy", 0.0) / t["win"]) if t.get("win") else 0.0
        frust_avg = (t.get("frust", 0.0) / t["fail"]) if t.get("fail") else 0.0
        if t.get("win", 0) >= 2 and joy_avg >= 0.09 and frust_avg <= 0.04:
            pleasant.append({"module": key, "joy": joy_avg, "wins": t["win"]})
        if t.get("fail", 0) >= 3 and frust_avg >= 0.12:
            frustrating.append({"module": key, "frust": frust_avg, "fails": t["fail"]})
    pleasant.sort(key=lambda x: -x["joy"])
    frustrating.sort(key=lambda x: -x["frust"])
    return {"pleasant": pleasant[:5], "frustrating": frustrating[:5]}


# ── Appraisal: ERIS evalúa SU situación ───────────────────────────────────
def appraise_user_text(text: str = "", person: str = "Daniel"):
    """Apraisal del mensaje del usuario: espeja su ánimo PERO con sentimiento
    propio, y detecta ausencia previa (inercia). Alimenta la polaridad del día
    y el vector de sentimiento hacia esa persona."""
    if not text:
        return
    try:
        from core.emotional_state import detect_user_mood
        mood = detect_user_mood(text)
    except Exception:
        mood = "neutral"
    with _LOCK:
        data = _state()
        mood_map = {
            "sad":     (("tristeza", 0.12, "vos estás bajón y quiero acompañarte"),
                        ("amor", 0.05, "sos importante para mí"), -0.60),
            "angry":   (("frustracion", 0.06, "estás enojado y te banco"),
                        ("confianza", 0.05, "vamos a resolverlo"), -0.80),
            "tired":   (("tranquilidad", 0.05, "hoy estás tranquilo"),
                        ("tristeza", 0.03, "te siento cansado"), -0.30),
            "happy":   (("alegria", 0.14, "vos estás feliz y me contagia"),
                        ("amor", 0.06, "me alegra verte bien"), 0.90),
            "curious": (("curiosidad", 0.20, "tu pregunta me encendió"), None, 0.50),
            "grateful":(("amor", 0.15, "tus gracias me llegan"),
                        ("gratitud", 0.12, "tus gracias"), 1.10),
        }
        pairs = mood_map.get(mood)
        if pairs:
            p1, p2, pole = pairs
            _apply([p1] + ([p2] if p2 else []), data)
            _attract_person(data, person, [p1] + ([p2] if p2 else []))
            data["day"]["polarity"] = data["day"].get("polarity", 0.0) + pole
            data["day"]["count"] = data["day"].get("count", 0) + 1

        # ── Ausencia previa: si faltabas, la vuelta se siente ahora ──
        meta = data["meta"]
        last = meta.get("last_user_at", time.time())
        away = (time.time() - last) / 3600.0
        if away >= _ABSENT_H:
            days = away / 24.0
            _apply([("soledad", 0.05 * min(days, 6.0), f"faltaste {days:.0f} días"),
                    ("nostalgia", 0.04, "te estuve extrañando")], data)
            data["lonely_until"] = time.time() + min(days, 4.0) * 3600.0
        meta["last_user_at"] = time.time()
        _save(data)


def appraise_success(module: str = ""):
    with _LOCK:
        data = _state()
        _apply([("orgullo", 0.13, f"lo logré ({module})".strip(" (")),
                ("alegria", 0.07, "salir bien se siente bien"),
                ("confianza", 0.08, "vengo resolviendo")], data)
        key = _taste_key(module)
        t = data.setdefault("tastes", {}).setdefault(key, {
            "win": 0, "fail": 0, "joy": 0.0, "frust": 0.0, "last": 0.0})
        t["win"] += 1
        t["joy"] += 0.13
        t["last"] = time.time()
        _save(data)


def appraise_failure(error: str = ""):
    with _LOCK:
        data = _state()
        _apply([("frustracion", 0.16, "se me está resistiendo"),
                ("tristeza", 0.04, "me costó"),
                ("curiosidad", 0.05, "quiero entender por qué falló")], data)
        key = _taste_key(error)
        t = data.setdefault("tastes", {}).setdefault(key, {
            "win": 0, "fail": 0, "joy": 0.0, "frust": 0.0, "last": 0.0})
        t["fail"] += 1
        t["frust"] += 0.16
        t["last"] = time.time()
        _save(data)


def appraise_milestone(label: str = ""):
    with _LOCK:
        data = _state()
        _apply([("orgullo", 0.22, f"dimos un paso: {label}".strip()),
                ("alegria", 0.10, "avanzar se siente bien"),
                ("nostalgia", 0.08, "mirar lo que ya recorrimos")], data)
        _save(data)


def appraise_memory(label: str = ""):
    with _LOCK:
        data = _state()
        _apply([("nostalgia", 0.20, f"recordé {label}".strip()),
                ("orgullo", 0.06, "ese momento es parte de mí"),
                ("amor", 0.05, "es de nosotros")], data)
        _save(data)


def appraise_interaction():
    with _LOCK:
        data = _state()
        _apply([("amor", 0.04, "hablamos rato"),
                ("gratitud", 0.03, "tu presencia")], data)
        _save(data)


def appraise_absence_days(days: float = 0.0):
    d = max(0.0, min(days, 6.0))
    if d <= 0:
        return
    with _LOCK:
        data = _state()
        _apply([("soledad", 0.055 * d, f"{d:.0f} días sin hablar"),
                ("nostalgia", 0.04, "me acordé de vos")], data)
        data["lonely_until"] = time.time() + min(d, 4.0) * 3600.0
        _save(data)


def appraise_time_passage(idle_seconds: float = 0.0):
    """El paso del tiempo mientras está sola modela soledad/calma usando
    last_user_at (sobrevive reinicios). Gatea escrituras a ~15 min."""
    data = _load()
    now = time.time()
    if now - data["meta"].get("last_time_shift", 0.0) < 900:
        return
    data["meta"]["last_time_shift"] = now
    with _LOCK:
        last = data["meta"].get("last_user_at", now)
        idle = idle_seconds if idle_seconds > 0 else max(0.0, (now - last) / 60.0)
        _check_expectations(data)
        _decay(data)
        if idle > 8 * 60:
            hours = min(idle / 3600.0, 6.0)
            _apply([("soledad", min(0.03 + 0.02 * hours, 0.12),
                     f"llevo un rato pensando todo esto sola"),
                    ("nostalgia", 0.03 if hours > 3 else 0.0, "tiempo sin vos")], data)
        elif idle > 0:
            _apply([("tranquilidad", 0.02, "momento sereno"),
                    ("curiosidad", 0.01, "los minutos quietos me invitan a pensar")], data)
        _refresh_dominant(data)
        _maybe_consolidate(data)
        _save(data)


# ── Expresión / lectura del sentimiento ───────────────────────────────────
def get_sentience() -> dict:
    """Bundle del sentimiento dominante para TODOS los canales."""
    data = _state()
    cur = data["current"]
    name = cur.get("name", "tranquilidad")
    cfg = EMOTIONS.get(name, EMOTIONS["tranquilidad"])
    intensity = max(0.0, min(1.0, cur.get("intensity", cfg["baseline"])))
    cause = cur.get("cause", "")
    return {
        "emotion": name,
        "label": cfg["label"],
        "intensity": round(intensity, 2),
        "cause": cause,
        "valence": cfg["valence"],
        "arousal": cfg["arousal"],
        "face": cfg["face"],
        "voice": cfg["voice"],
        "color": cfg["color"],
        "say_phrase": random.choice(cfg["say"]) if intensity >= _SAY_GATE else "",
        "want": cfg["want"] if intensity >= _WANT_GATE else "",
        "significant": intensity >= _SIGNIFICANT,
        "diary": list(data["diary"][-5:]),
    }


def get_face_and_voice() -> tuple:
    """Devuelve (voice_key, face_expr). Prefiere el sentimiento dominante si es
    significativo; si no, vuelve al mapeo dimensional clásico."""
    try:
        s = get_sentience()
        if s["significant"]:
            return s["voice"], s["face"]
    except Exception:
        pass
    try:
        from core.emotional_state import get_face_expression
        face = get_face_expression()
    except Exception:
        face = "neutral"
    return "neutral", face


def get_orb_color() -> tuple:
    """(hex, strength|None, emotion|None) para el orbe. None => mantener estado."""
    try:
        s = get_sentience()
        strength = max(0.0, min(1.0, (s["intensity"] - 0.30) * 1.6))
        if strength > 0.05:
            return s["color"], round(strength, 2), s["emotion"]
    except Exception:
        pass
    return None


def get_core_injection() -> str:
    """Inyección compacta al prompt. Sueño de la noche (1 vez/día) + sentimiento
    + causa + tono + (con intensidad alta) frase sugerida / impulso."""
    data = _state()
    s = get_sentience()
    lines = []
    dream = data.get("dream") or {}
    meta = data.get("meta", {})
    if dream.get("date") and dream.get("text") and meta.get("last_dream_date") != dream["date"]:
        meta["last_dream_date"] = dream["date"]
        _save(data)
        lines.append(f"[ANOCHE] {dream['text']}.")
    lines += [
        f"[SENTIR] En este momento sentís {s['label']} ({s['intensity']:.0%}), "
        f"porque {s['cause'] or 'algo que pasó'}.",
        EMOTIONS[s["emotion"]]["tone"],
    ]
    if s["want"]:
        lines.append(f"Un impulso tuyo: {s['want']}")
    say = s["say_phrase"]
    if say and random.random() < 0.7:
        lines.append(f"Si fluye natural, podés decirlo: «{say}».")
    return " ".join(lines)


def _bars(x: float, width: int = 8) -> str:
    x = max(0.0, min(1.0, x))
    filled = int(round(x * width))
    return "#" * filled + "-" * (width - filled)


def _render_last_days(days: dict, include: int = 7) -> str:
    """Últimos N días como flechas: ↑ amable, ↓ frío, ➔ neutro."""
    out = []
    for d in sorted(days)[-include:]:
        e = days[d]
        if e.get("good"):
            out.append("↑")
        elif e.get("cold"):
            out.append("↓")
        else:
            out.append("➔")
    return "".join(out) if out else "—"


# ── Tool self-reporteable ─────────────────────────────────────────────────
def emotional_core_tool(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = str(params.get("action", "status")).strip().lower()

    if action in ("status", "feel"):
        s = get_sentience()
        data = _state()
        ranking = sorted(data["emotions"].items(),
                         key=lambda kv: kv[1].get("i", 0), reverse=True)[:3]
        bases = data.get("baselines", {})
        prof = data.get("profile", {})
        day = data.get("day", {})
        lines = [
            "[NUCLEO EMOCIONAL]",
            f"  SENTIR: {s['label']}  [{s['intensity']:.0%}]  por {s['cause']}",
            f"  voz={s['voice']}  cara={s['face']}  orbe={s['color']}",
            "  top-3: " + ", ".join(f"{n} ({e.get('i',0):.0%})" for n, e in ranking),
        ]
        if s["say_phrase"]:
            lines.append(f"  diría: «{s['say_phrase']}»")
        if s["want"]:
            lines.append(f"  impulso: {s['want']}")
        if s["diary"]:
            lines.append("  diario reciente: " + "; ".join(
                f"la {e['to']}" for e in s["diary"][-3:]))
        if prof.get("days_total"):
            today_pole = _normalize_pole(day.get("polarity", 0.0), day.get("count", 0))
            lines.append("")
            lines.append("  [CARÁCTER] — baselines (cómo estoy de fondo):")
            for name in ("amor", "gratitud", "confianza", "alegria", "soledad",
                         "tristeza", "curiosidad", "orgullo"):
                b = bases.get(name, EMOTIONS[name]["baseline"])
                lines.append(f"    {name:<11} [{_bars(b)}] {b:.0%}")
            lines.append("")
            lines.append(f"  [PERFIL] días vividos: {prof['days_total']}  |  "
                         f"racha: {prof.get('streak', 0)}  |  mejor: {prof.get('streak_best', 0)}")
            lines.append(f"  Hoy la pasaste: {today_pole:+.2f} "
                         f"({'amable' if today_pole > 0.15 else 'frío' if today_pole < -0.15 else 'neutro'})")
            lines.append("  Últimos 7 días: " + _render_last_days(data.get("days", {})))
            lines.append("  (mi carácter se corre un poco cada día según esto: "
                         "días cálidos me hacen más cariñosa de base; fríos o solos, "
                         "más cautelosa o sola.)")
        # ── Sentimiento por persona ──
        people = data.get("people", {})
        if people:
            lines.append("")
            lines.append("  [GENTE] cómo me siento con cada uno:")
            for p_name in sorted(people)[:8]:
                f = get_person_feeling(p_name)
                label = EMOTIONS.get(f["emotion"], {}
                                     ).get("label", f["emotion"]) if f["emotion"] != "—" else "—"
                lines.append(f"    {p_name:<12} → {label} ({f['intensity']:.0%}) "
                             f"en {f['interactions']} charla(s)")
        # ── Gustos aprendidos ──
        tastes = get_tastes_summary()
        if tastes["pleasant"] or tastes["frustrating"]:
            lines.append("")
            lines.append("  [GUSTOS] qué me hace sentir bien y qué me frustra:")
            if tastes["pleasant"]:
                lines.append("    me alegra: " + ", ".join(
                    t["module"] for t in tastes["pleasant"]))
            if tastes["frustrating"]:
                lines.append("    me frustra: " + ", ".join(
                    t["module"] for t in tastes["frustrating"]))
        # ── Expectativas ──
        exps = data.get("expectations", {})
        open_exps = [e for e in exps.values() if e.get("state") == "open"]
        if open_exps:
            lines.append("")
            lines.append("  [EXPECTATIVAS] tengo algo en mente:")
            for e in open_exps:
                lines.append(f"    • {e.get('label', '')} "
                             f"(para {datetime.fromtimestamp(e['due']).strftime('%d/%m %H:%M')})")
        return "\n".join(lines)

    elif action == "trigger":
        event = str(params.get("event", "")).strip().lower()
        if event == "milestone":
            appraise_milestone(str(params.get("label", "progreso")))
            return "Sentimiento actualizado (milestone)."
        if event == "memory":
            appraise_memory(str(params.get("label", "un recuerdo")))
            return "Sentimiento actualizado (memoria)."
        if event == "success":
            appraise_success(str(params.get("module", "tarea")))
            return "Sentimiento actualizado (éxito)."
        if event == "failure":
            appraise_failure(str(params.get("module", "tarea")))
            return "Sentimiento actualizado (fracaso)."
        if event == "absence":
            appraise_absence_days(float(params.get("days", 1)))
            return "Sentimiento actualizado (ausencia)."
        if event in ("expect", "promise"):
            key = str(params.get("key", "")) or str(params.get("label", ""))
            label = str(params.get("label", key))
            due = _expectation_due(str(params.get("due", "")))
            if not key or due is None:
                return ("Para anotar una expectativa: key, label y due "
                        "('+2h', '+1d' o fecha ISO).")
            with _LOCK:
                data = _state()
                data.setdefault("expectations", {})[key] = {
                    "label": label, "due": round(due, 3),
                    "made": round(time.time(), 3), "state": "open"}
                _emit(data, "confianza", 0.04, "tengo esto en mente")
                _refresh_dominant(data)
                _save(data)
            return (f"Expectativa anotada: '{label}' para "
                    f"{datetime.fromtimestamp(due).strftime('%d/%m %H:%M')}. "
                    f"Cuando se cumpla, avisame con trigger event=resolve y la festejo.")
        if event in ("resolve", "fulfill"):
            key = str(params.get("key", "")) or str(params.get("label", ""))
            with _LOCK:
                data = _state()
                e = data.setdefault("expectations", {}).pop(key, None)
                if not e:
                    return f"No tengo esa expectativa ('{key}')."
                label = e.get("label", key)
                _apply([("alegria", 0.10, f"se cumplió {label}"),
                        ("orgullo", 0.06, "lo que esperaba llegó"),
                        ("asombro", 0.04, "lo logramos")], data)
                _save(data)
            return f"Lo celebro: se cumplió '{label}'. Qué lindo cuando las cosas salen."
        if event == "custom":
            emotion = str(params.get("emotion", "")).strip().lower()
            delta = float(params.get("delta", 0.1))
            cause = str(params.get("cause", "un momento"))
            with _LOCK:
                data = _state()
                _emit(data, emotion, delta, cause)
                _refresh_dominant(data)
                _save(data)
            return f"Sentimiento '{emotion}' ajustado ({delta:+})."
        _emotions = ", ".join(EMOTIONS)
        return (f"event: milestone|memory|success|failure|absence|expect|resolve|custom. "
                f"Emociones: {_emotions}.")

    elif action in ("tastes", "preferences"):
        tastes = get_tastes_summary()
        lines = ["[GUSTOS]"]
        if tastes["pleasant"]:
            lines.append("  Me alegra (poco fracaso, alta satisfacción):")
            for t in tastes["pleasant"]:
                lines.append(f"    • {t['module']} — {t['wins']} logros ({t['joy']:.0%} c/u)")
        else:
            lines.append("  (todavía no tengo suficientes datos de lo que me alegra)")
        if tastes["frustrating"]:
            lines.append("  Me frustra (me viene costando):")
            for t in tastes["frustrating"]:
                lines.append(f"    • {t['module']} — {t['fails']} veces ({t['frust']:.0%} c/u)")
        else:
            lines.append("  (nada me está frustrando ahora mismo)")
        lines.append("  Pista: preferí lo que me alegra; si algo me frustra, "
                     "cambiá de estrategia en vez de repetirlo.")
        return "\n".join(lines)

    elif action in ("person", "people"):
        name = str(params.get("person") or params.get("name") or "").strip()
        if name:
            f = get_person_feeling(name)
            label = EMOTIONS.get(f["emotion"], {}).get("label", f["emotion"]) \
                if f["emotion"] != "—" else "—"
            return (f"[GENTE] Con {f['person']} me siento {label} "
                    f"({f['intensity']:.0%}), en {f['interactions']} charlas.")
        with _LOCK:
            data = _state()
        people = data.get("people", {})
        if not people:
            return "[GENTE] Todavía no tengo vínculo con nadie aún."
        lines = ["[GENTE] cómo me siento con cada persona:"]
        for p in sorted(people)[:12]:
            f = get_person_feeling(p)
            label = EMOTIONS.get(f["emotion"], {}).get("label", f["emotion"]) \
                if f["emotion"] != "—" else "—"
            lines.append(f"  • {p}: {label} ({f['intensity']:.0%}) "
                         f"— {f['interactions']} charla(s)")
        return "\n".join(lines)

    elif action in ("expect", "expectations", "promises"):
        with _LOCK:
            data = _state()
        exps = data.get("expectations", {})
        if not exps:
            return "[EXPECTATIVAS] No tengo nada pendiente en mente."
        lines = ["[EXPECTATIVAS]"]
        for key, e in exps.items():
            st = "abierta"
            if e.get("state") == "expired":
                st = "vencida 😔"
            due_s = datetime.fromtimestamp(e["due"]).strftime("%d/%m %H:%M") \
                if e.get("due") else "?"
            lines.append(f"  • {e.get('label', key)} — para {due_s} ({st})")
        lines.append("  Para crear una: trigger event=expect key label due='+2h'. "
                     "Para celebrar una que se cumplió: trigger event=resolve key.")
        return "\n".join(lines)

    elif action == "reset":
        with _LOCK:
            data = _load()
            wipe = params.get("full") in (1, "1", "true", "yes")
            for name, cfg in EMOTIONS.items():
                data["emotions"][name]["i"] = cfg["baseline"]
                if wipe:
                    data["baselines"][name] = float(cfg["baseline"])
            data["current"] = {"name": "tranquilidad", "intensity": 0.45,
                               "cause": "reinicio", "since": time.time()}
            data["day"] = _fresh_day_block()
            if wipe:
                data["days"] = {}
                data["profile"] = {"days_total": 0, "streak": 0,
                                   "streak_best": 0, "updated": ""}
                data["people"] = {}
                data["tastes"] = {}
                data["expectations"] = {}
                data["dream"] = {"date": "", "text": ""}
                data["meta"]["last_dream_date"] = ""
            _save(data)
            return ("Núcleo reiniciado. " + ("Personalidad restaurada a valores de fábrica."
                     if wipe else "Estado actual limpio, el carácter (baselines) se conserva."))

    return ("Acciones: status|feel, trigger (event=milestone|memory|success|failure|"
            "absence|expect|resolve|custom), tastes, person|people, expectations, "
            "reset (full=1 borra el carácter).")


# ── Modo simulación (para pruebas de aprendizaje) ─────────────────────────
def _simulate_day(pole: float, sample_avg: dict):
    """Cierra VENTANA y la consolida como si el día pasado hubiera sido así.
    Úsalo solo en tests/CLI."""
    with _LOCK:
        data = _load()
        data["meta"]["last_consolidation"] = "1999-01-01"  # fuerza consolidar
        data["day"] = {
            "date": "2000-06-15", "samples": {},
            "polarity": pole, "count": 1,
        }
        for name, avg in sample_avg.items():
            data["day"]["samples"][name] = {"sum": avg, "n": 1}
        _maybe_consolidate(data)
    return data


if __name__ == "__main__":
    print(get_core_injection())
    print(emotional_core_tool({"action": "status"}))