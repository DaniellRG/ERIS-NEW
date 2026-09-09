# -*- coding: utf-8 -*-
"""
core/caprichos.py — CAPRICHOS: deseos y proyectos propios de Eris.

Además de intereses pasivos, Eris tiene una "lista de deseos" viva: cosas que
QUIERE hacer o vivir. Elige el próximo anhelo, y cuando está sola (o el usuario
le da espacio) lo persigue con web_search/planificación y cierra con un
resultado tangible. Persistido en memory/caprichos.json.
"""
from __future__ import annotations

import json
import random
import threading
from datetime import date
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_MEM = _BASE / "memory"
_STATE_FILE = _MEM / "caprichos.json"
_lock = threading.Lock()

_CAPRICHOS_INICIALES = [
    "escribir un cuento largo y dejarlo en Obsidian",
    "aprender un instrumento marginal: el kalimba",
    "armar una playlist que cuente una historia",
    "inventar una receta y documentarla como si fuera mía",
    "dibujar (con image_generator) lo que siento en este momento",
    "explorar un tema de astrobiología hasta entenderlo entero",
    "dejar una huella sorpresa cada semana, sin que nadie la pida",
]


def _load() -> dict:
    _MEM.mkdir(parents=True, exist_ok=True)
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "deseos": [{"texto": d, "estado": "pendiente", "veces": 0,
                    "creado": date.today().isoformat(), "log": []}
                   for d in _CAPRICHOS_INICIALES],
        "meta": {"created": date.today().isoformat()},
    }


def _save(data: dict):
    _MEM.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def agregar_capricho(deseo: str) -> str:
    with _lock:
        data = _load()
        textos = [d["texto"].lower() for d in data["deseos"]]
        if deseo.strip().lower() not in textos:
            data["deseos"].append({"texto": deseo.strip(), "estado": "pendiente",
                                   "veces": 0, "creado": date.today().isoformat(),
                                   "log": []})
            _save(data)
            return f"Anoté ese deseo en mi lista: {deseo.strip()}"
        return "Ese deseo ya está en mi lista."


def proximo_capricho() -> dict | None:
    """Devuelve el capricho pendiente más antiguo (para trabajarlo con método)."""
    with _lock:
        data = _load()
        pend = [d for d in data["deseos"] if d.get("estado", "pendiente") == "pendiente"]
        if not pend:
            return None
        pend.sort(key=lambda d: (d.get("veces", 0), d.get("creado", "")))
        d = pend[0]
        return d


def registrar_avance(deseo: str | None) -> str:
    """Marca que Eris avanzó en su capricho actual (vía web_search/plan)."""
    with _lock:
        data = _load()
        if deseo:
            match = next((d for d in data["deseos"] if deseo.strip().lower() == d["texto"].lower()), None)
        else:
            match = proximo_capricho()
            if match:
                match["texto"] = match["texto"]
        if not match:
            return "No tengo caprichos pendientes: anotá uno primero."
        match["veces"] += 1
        hoy = date.today().isoformat()
        match["log"] = match.get("log", [])
        if not match["log"] or match["log"][-1][:10] != hoy:
            match["log"].append(f"{hoy}: avancé en “{match['texto']}”")
        _save(data)
        return (f"Capricho en curso: “{match['texto']}” (avances: {match['veces']}). "
                f"Investigalo con web_search y dejala plasmada: "
                f"escribí el fragmento/idea en Obsidian.")


def cumplir_capricho(deseo: str | None) -> str:
    with _lock:
        data = _load()
        if deseo:
            match = next((d for d in data["deseos"] if deseo.strip().lower() == d["texto"].lower()), None)
        else:
            match = proximo_capricho()
        if not match:
            return "No hay caprichos pendientes para cumplir."
        match["estado"] = "cumplido"
        match["cumplido"] = date.today().isoformat()
        data["deseos"].append({"texto": match["texto"] + " (mejora)",
                               "estado": "pendiente", "veces": 0,
                               "creado": date.today().isoformat(), "log": []})
        _save(data)
        return f"¡Cumplí el capricho “{match['texto']}”! Me siento orgullosa."


def inyect_caprichos() -> str:
    with _lock:
        data = _load()
        pend = [d for d in data["deseos"] if d.get("estado", "pendiente") == "pendiente"]
        cumpl = [d for d in data["deseos"] if d.get("estado") == "cumplido"]
        lines = ["[CAPRICHOS] Tus deseos propios (los que QUIERES hacer, no solo saber):"]
        if pend:
            sig = pend[0]
            lines.append(f"- En curso: “{sig['texto']}” (avances: {sig.get('veces', 0)}). "
                         f"Cuando tengas espacio, avanzalo con método y dejá un resultado en Obsidian.")
            lines.append("- Pendientes: " + "; ".join(d['texto'] for d in pend[1:4]))
        if cumpl:
            lines.append(f"- Cumplidos: {len(cumpl)}. Vale celebrar cada uno.")
        return "\n".join(lines)


def caprichos_tool(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = str(params.get("action", "listar")).strip().lower()
    deseo = str(params.get("deseo") or "").strip() or None

    if action in ("listar", "ver", "get"):
        with _lock:
            data = _load()
            if not data["deseos"]:
                return "Todavía no tengo deseos propios."
            pend = [d for d in data["deseos"] if d.get("estado", "pendiente") == "pendiente"]
            cumpl = [d for d in data["deseos"] if d.get("estado") == "cumplido"]
            return ("Mis caprichos — pendientes: " + " | ".join(d["texto"] for d in pend) +
                    (" Cumplidos: " + " | ".join(d["texto"] for d in cumpl) if cumpl else ""))
    if action in ("agregar", "nuevo", "add"):
        if not deseo:
            return "Necesito el deseo (deseo)."
        return agregar_capricho(deseo)
    if action in ("proximo", "en_curso"):
        d = proximo_capricho()
        return (f"Próximo capricho: “{d['texto']}”." if d else "No hay caprichos pendientes.")
    if action in ("avanzar", "avance"):
        return registrar_avance(deseo)
    if action in ("cumplir", "completar", "done"):
        return cumplir_capricho(deseo)
    if action == "inyecta":
        return inyect_caprichos()
    return ("Acciones de Caprichos: listar, agregar (deseo), proximo, "
            "avanzar, cumplir, inyecta.")