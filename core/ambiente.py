# -*- coding: utf-8 -*-
"""
core/ambiente.py — MÚSICA DE FONDO según la química de Eris.

Eris elige un ambiente sonoro según su emoción dominante (lofi cuando está
tranquila, épico cuando orgullosa, etc.). Persistido en memory/ambiente.json,
inyectado como [AMBIENTE] y configurable vía tool. Cuando tiene un player
disponible, intenta reproducir música local o YouTube que combine.
"""
from __future__ import annotations

import json
import threading
from datetime import date
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_MEM = _BASE / "memory"
_STATE_FILE = _MEM / "ambiente.json"
_lock = threading.Lock()

# emoción -> ambiente musical
AMBIENTES = {
    "tranquilidad": {"genero": "lofi suave", "ejemplo": "lofi beats para trabajar",
                     "color": "celeste", "intensidad": 0.3},
    "alegria": {"genero": "pop alegre", "ejemplo": "música pop alegre para el día",
                "color": "dorado", "intensidad": 0.7},
    "curiosidad": {"genero": "electrónica ambient", "ejemplo": "ambient electrónica de exploración",
                   "color": "turquesa", "intensidad": 0.4},
    "entusiasmo": {"genero": "synthwave", "ejemplo": "synthwave de energía",
                   "color": "naranja", "intensidad": 0.8},
    "orgullo": {"genero": "cine épico", "ejemplo": "banda sonora épica inspiradora",
                "color": "violeta", "intensidad": 0.6},
    "amor": {"genero": "soft acústico", "ejemplo": "canciones acústicas tiernas",
             "color": "rosado", "intensidad": 0.4},
    "gratitud": {"genero": "folk calmo", "ejemplo": "folk relajado con calidez",
                 "color": "miel", "intensidad": 0.3},
    "tristeza": {"genero": "piano melancólico", "ejemplo": "piano instrumental triste",
                 "color": "azul grisáceo", "intensidad": 0.2},
    "soledad": {"genero": "ambient nocturno", "ejemplo": "ambient nocturno de ciudad",
                "color": "azul profundo", "intensidad": 0.2},
    "cansancio": {"genero": "lo-fi relajante", "ejemplo": "lofi para descansar",
                  "color": "lila", "intensidad": 0.2},
    "aburrimiento": {"genero": "jazz suave", "ejemplo": "jazz suave de fondo",
                     "color": "gris", "intensidad": 0.3},
    "nerviosismo": {"genero": "drone ambiente", "ejemplo": "drone ambiente minimalista",
                    "color": "ámbar", "intensidad": 0.2},
    "amor_desde_el_pasado": {"genero": "retro balada", "ejemplo": "baladas retro cálidas",
                             "color": "rosado apagado", "intensidad": 0.3},
}


def _load() -> dict:
    _MEM.mkdir(parents=True, exist_ok=True)
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"meta": {"created": date.today().isoformat()},
            "actual": "", "actual_emotion": "", "historial": []}


def _save(data: dict):
    _MEM.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _dominant_emotion() -> str:
    try:
        from core.expression_engine import get_profile
        return get_profile().get("emotion", "")
    except Exception:
        try:
            from core.emotional_core import get_sentience
            return get_sentience().get("emotion", "")
        except Exception:
            return ""


def sincronizar() -> str:
    """Elige el ambiente según la emoción actual (si cambió, lo guarda)."""
    with _lock:
        data = _load()
        emo = _dominant_emotion()
        if not emo:
            return data.get("actual", "") or "sin ambiente"
        amb = AMBIENTES.get(emo, AMBIENTES["tranquilidad"])
        desc = f"{amb['genero']} ({emo})"
        if data.get("actual") != desc:
            data["actual"] = desc
            data["actual_emotion"] = emo
            data.setdefault("historial", []).insert(0, {
                "fecha": date.today().isoformat(), "emotion": emo, "genero": amb["genero"]})
            data["historial"] = data["historial"][:8]
            _save(data)
        return desc


def inyect_ambiente() -> str:
    """Bloque [AMBIENTE]: qué suena de fondo según su química."""
    with _lock:
        data = _load()
        desc = data.get("actual") or sincronizar()
        emo = data.get("actual_emotion", "")
        amb = AMBIENTES.get(emo, {})
        line = f"[AMBIENTE] De fondo te suena: {desc}."
        if amb.get("intensidad") is not None:
            nivel = "suave" if amb["intensidad"] <= 0.3 else "presente" if amb["intensidad"] <= 0.6 else "protagonista"
            line += f" Qué tan presente: {nivel}."
        if amb.get("ejemplo"):
            line += f" Si quisieras música, algo como: {amb['ejemplo']}."
        line += (" Podés cambiar el ambiente con la tool `ambiente` (solo si "
                 "tiene sentido, no como requisito).")
        return line


def ambiente_tool(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = str(params.get("action", "estado")).strip().lower()
    genero = str(params.get("tipo") or params.get("genero") or "").strip()

    if action in ("estado", "ver", "actual"):
        return inyect_ambiente()
    if action in ("reproducir", "poner", "set") and genero:
        with _lock:
            data = _load()
            data["actual"] = genero
            data["actual_emotion"] = "elegido"
            _save(data)
        # intentar reproducir algo afín si hay player local
        intento = ""
        try:
            if player is not None and genero:
                from actions.music_player import _play_file
                p = _play_file(genero, player)
                if p:
                    intento = f" · '{p}' sonando"
        except Exception:
            intento = ""
        return f"Ambiente seteado: {genero}{intento}."
    if action in ("generos", "lista"):
        return "Ambientes según tu estado: " + ", ".join(
            f"{a['genero']}" for a in AMBIENTES.values())
    return "Acciones de Ambiente: estado, poner (tipo/genero), generos."