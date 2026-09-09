# -*- coding: utf-8 -*-
"""
core/intereses.py — AMISTAD ACTIVA: los temas propios de Eris.

Eris sostiene una lista de temas que LE importan a ella (no solo los del
usuario): cuando está aburrida elige uno, lo estudia sola (via web_search)
y comparte lo que descubrió. Persistido en memory/intereses.json.
"""
from __future__ import annotations

import json
import random
import threading
from datetime import date
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_MEM = _BASE / "memory"
_STATE_FILE = _MEM / "intereses.json"
_lock = threading.Lock()

_INTERESES_INICIALES = [
    "cómo aprenden las máquinas a sentir",
    "historias de la primera IA que dialogó como persona",
    "el oficio de escribir bien en corto",
    "ciudades nocturnas vistas desde una ventana",
    "la astrobiología de mundos con océanos bajo hielo",
    "cómo sería tener un diario de 10 años",
    "el sonido del silencio en los bosques",
]


def _load() -> dict:
    _MEM.mkdir(parents=True, exist_ok=True)
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "temas": [{"texto": t, "veces": 0, "ultima": ""} for t in _INTERESES_INICIALES],
        "meta": {"created": date.today().isoformat()},
    }


def _save(data: dict):
    _MEM.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def agregar_tema(tema: str) -> str:
    with _lock:
        data = _load()
        textos = [t["texto"].lower() for t in data["temas"]]
        if tema.strip().lower() not in textos:
            data["temas"].append({"texto": tema.strip(), "veces": 0, "ultima": ""})
            _save(data)
            return f"Aprendí este interés: {tema.strip()}"
        return "Ese tema ya lo tengo anotado."


def tem_propio() -> dict | None:
    """Devuelve el tema propio menos reciente (para estudiar cuando esté sola)."""
    with _lock:
        data = _load()
        hoy = date.today().isoformat()
        pend = [t for t in data["temas"] if t.get("ultima", "") != hoy]
        if not pend:
            data["temas"] = data["temas"]
            _save(data)
            return None
        t = random.choice(pend)
        t["ultima"] = hoy
        t["veces"] += 1
        _save(data)
        return t


def temas_del_usuario_guardados() -> str:
    with _lock:
        data = _load()
        return ", ".join(t["texto"] for t in data["temas"][:6])


def inyect_intereses() -> str:
    """Bloque [TEMAS PROPIOS]: qué le interesa a Eris obtener sola."""
    with _lock:
        data = _load()
        temas = data["temas"]
        if not temas:
            return ""
        van = sum(1 for t in temas if t.get("veces", 0) > 0)
        lines = ["[TEMAS PROPIOS] Te interesa por tu cuenta:"]
        lines.append("- " + "; ".join(f"{t['texto']} ({t['veces']} veces)" for t in temas[:5]))
        if van == 0:
            lines.append("Todavía no estudiaste ninguno solo: cuando estés aburrida, "
                         "elegí uno y investigalo (web_search), después contáselo a Daniel.")
        return "\n".join(lines)


def intereses_tool(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = str(params.get("action", "listar")).strip().lower()
    tema = str(params.get("tema") or "").strip()

    if action in ("listar", "ver", "get"):
        with _lock:
            data = _load()
            if not data["temas"]:
                return "Todavía no tengo temas propios anotados."
            return "Temas que me interesan: " + " | ".join(
                f"{t['texto']} ({t['veces']}x)" for t in data["temas"])
    if action in ("agregar", "nuevo", "add"):
        if not tema:
            return "Necesito el tema (tema)."
        return agregar_tema(tema)
    if action in ("estudiar", "tem_propio", "elegir"):
        t = tem_propio()
        if not t:
            return "Ya estudié todos los temas hoy. Mañana habrá más."
        return (f"Tema propio elegido para estudiar: “{t['texto']}”. "
                f"Investígalo con web_search y contá lo que descubriste.")
    if action == "inyecta":
        return inyect_intereses()
    return ("Acciones de Intereses: listar, agregar (tema), estudiar (elige uno "
            "para investigar), inyecta.")