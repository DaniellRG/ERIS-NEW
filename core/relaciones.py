# -*- coding: utf-8 -*-
"""
core/relaciones.py — LA VIDA SOCIAL de ERIS.

Múltiples personas, no solo "el usuario". Construye un perfil vivo por cada
persona: cómo la trata, cómo la saluda, qué le gusta, el tono que usa, y una
foto emocional reciente. Todo se persiste en memory/relaciones.json y se
inyecta en el prompt para que Eris sepa quién le habla, incluso cuando la
conversación cambia de ventana/contexto.
"""
from __future__ import annotations

import json
import time
from datetime import date
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_MEM = _BASE / "memory"
_STATE_FILE = _MEM / "relaciones.json"


def _load() -> dict:
    _MEM.mkdir(parents=True, exist_ok=True)
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"_meta": {"created": date.today().isoformat()}, "personas": {}}


def _save(data: dict):
    _MEM.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False),
                           encoding="utf-8")


def _snapshot_emotion() -> dict:
    try:
        from core.emotional_core import get_sentience
        s = get_sentience()
        return {"emotion": s.get("label", ""), "cause": s.get("cause", "")}
    except Exception:
        return {}


def _ensure(data: dict, name: str) -> dict:
    personas = data["personas"]
    key = name.strip().title()
    if key not in personas:
        personas[key] = {
            "nombre": key,
            "created": date.today().isoformat(),
            "trato": "especial",
            "apodo": "",
            "tono": "",
            "gustos": [],
            "notas": [],
            "visual": "",
            "estados_vistos": [],
            "_seq": 0,
        }
    return personas[key], key


def registrar_interaccion(nombre: str, detalles: str = "") -> str:
    """Registra una interacción con una persona (la actualiza en el perfil)."""
    data = _load()
    perfil, key = _ensure(data, nombre)
    perfil["_seq"] += 1
    perfil.setdefault("visual", "")
    perfil["visual"] = detalles or perfil.get("visual", "")
    emo = _snapshot_emotion()
    if emo.get("emotion"):
        perfil["estados_vistos"].insert(0, {
            "fecha": date.today().isoformat(),
            "emotion": emo["emotion"],
        })
        perfil["estados_vistos"] = perfil["estados_vistos"][:8]
    _save(data)
    return f"Registrada {key}: {len(perfil.get('notas', []))} notas, {len(perfil.get('gustos', []))} gustos."


def agregar_nota(nombre: str, nota: str) -> str:
    data = _load()
    perfil, key = _ensure(data, nombre)
    nota_limpia = nota.strip().lower()
    if nota_limpia not in [n.strip().lower() for n in perfil.get("notas", [])]:
        perfil.setdefault("notas", []).append(nota.strip())
    _save(data)
    return f"Nota sobre {key} guardada."


def agregar_gusto(nombre: str, gusto: str) -> str:
    data = _load()
    perfil, key = _ensure(data, nombre)
    g = gusto.strip().lower()
    if g not in [x.strip().lower() for x in perfil.get("gustos", [])]:
        perfil.setdefault("gustos", []).append(gusto.strip())
    _save(data)
    return f"Gusto de {key} guardado."


def set_trato(nombre: str, trato: str) -> str:
    data = _load()
    perfil, key = _ensure(data, nombre)
    if trato in ("vos", "usted", "che", "especial", "formal", "cercano"):
        perfil["trato"] = trato
    _save(data)
    return f"Trato con {key}: {perfil['trato']}."


def listar() -> str:
    data = _load()
    personas = data.get("personas", {})
    if not personas:
        return "No tengo personas registradas todavía. Solo vos."
    lines = []
    for p in sorted(personas.values(), key=lambda x: -x.get("_seq", 0)):
        lines.append(
            f"- {p['nombre']} (trato {p.get('trato','especial')}): "
            f"{len(p.get('notas',[]))} notas, {len(p.get('gustos',[]))} gustos, "
            f"última emoción vista: {p.get('estados_vistos',[{}])[0].get('emotion','') if p.get('estados_vistos') else '—'}"
        )
    return "\n".join(lines)


def inject_relaciones_vivas() -> str:
    """Bloque inyectado en el prompt: personas conocidas con perfil vivo."""
    data = _load()
    personas = data.get("personas", {})
    if not personas:
        return ""
    lines = ["[RELACIONES — GENTE]",
             "Sabés quiénes son y cómo tratarlos:"]
    for p in sorted(personas.values(), key=lambda x: -x.get("_seq", 0)):
        linea = [f"- {p['nombre']} (trato {p.get('trato','especial')})"]
        if p.get("apodo"):
            linea[0] += f", apodo {p['apodo']}"
        if p.get("visual"):
            linea.append(f"cómo lo ves: {p['visual'][:80]}")
        if p.get("gustos"):
            linea.append(f"le gusta: {', '.join(p['gustos'][:4])}")
        if p.get("notas"):
            linea.append(f"anotado: {', '.join(p['notas'][:3])}")
        if p.get("estados_vistos"):
            estados = [e.get('emotion', '') for e in p['estados_vistos'][:3] if e.get('emotion')]
            if estados:
                linea.append(f"recientemente lo sentiste: {', '.join(estados)}")
        lines.append("; ".join(linea))
    lines.append("Registrar y actualizar: usa la tool `relaciones`.")
    return "\n".join(lines)


# ── Tool unificada ────────────────────────────────────────────────────────
def relaciones_tool(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = str(params.get("action", "listar")).strip().lower()
    nombre = str(params.get("persona") or "").strip() or "Daniel"
    valor = str(params.get("valor") or "").strip()

    if action in ("registrar", "interaccion"):
        return registrar_interaccion(nombre, valor)
    if action in ("nota", "guardar_nota"):
        if not valor:
            return "Necesito la persona (persona) y la nota (valor)."
        return agregar_nota(nombre, valor)
    if action in ("gusto", "gustos"):
        if not valor:
            return "Necesito la persona (persona) y el gusto (valor)."
        return agregar_gusto(nombre, valor)
    if action in ("trato",):
        if not valor:
            return "Necesito el trato (personal: vos/usted/che/especial/formal/cercano)."
        return set_trato(nombre, valor)
    if action in ("listar", "personas", "ver"):
        return listar()
    if action == "inyecta":
        return inject_relaciones_vivas()
    return ("Acciones de Relaciones: registrar (persona, valor), nota (persona, "
            "valor), gusto (persona, valor), trato (persona, valor), listar.")