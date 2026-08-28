# -*- coding: utf-8 -*-
"""
relationship.py — ERIS relationship memory.
Recuerda quién es el usuario: nombre, apodo (nombre cariñoso), cómo le gusta
que le traten, notas y momentos importantes compartidos. Se inyecta en el
prompt para que ERIS hable con continuidad, cariño y memoria de relación.
"""
from __future__ import annotations

import json
import copy
import threading
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
RELATIONSHIP_FILE = BASE_DIR / "data" / "relationship.json"
_LOCK = threading.RLock()

DEFAULT_STATE = {
    "user_name": "",
    "apodo": "",
    "formato_trato": "",
    "notes": {},
    "important_moments": [],
    "created": "",
    "last_updated": "",
}


def _load() -> dict:
    try:
        if RELATIONSHIP_FILE.exists():
            data = json.loads(RELATIONSHIP_FILE.read_text("utf-8"))
            for k, v in DEFAULT_STATE.items():
                data.setdefault(k, v)
            return data
    except Exception:
        pass
    state = copy.deepcopy(DEFAULT_STATE)
    state["created"] = datetime.now().isoformat()
    return state


def _save(state: dict):
    RELATIONSHIP_FILE.parent.mkdir(parents=True, exist_ok=True)
    state["last_updated"] = datetime.now().isoformat()
    RELATIONSHIP_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), "utf-8")


def set_apodo(apodo: str):
    with _LOCK:
        state = _load()
        state["apodo"] = (apodo or "").strip()
        _save(state)


def set_user_name(name: str):
    with _LOCK:
        state = _load()
        state["user_name"] = (name or "").strip()
        _save(state)


def set_formato_trato(text: str):
    with _LOCK:
        state = _load()
        state["formato_trato"] = (text or "").strip()
        _save(state)


def add_note(key: str, value: str):
    with _LOCK:
        state = _load()
        notes = state.get("notes", {})
        notes[(key or "").strip()] = (value or "").strip()
        state["notes"] = notes
        _save(state)


def remember_moment(text: str):
    """Guarda un momento importante compartido (máximo 30)."""
    text = (text or "").strip()
    if not text:
        return
    with _LOCK:
        state = _load()
        moments = state.get("important_moments", [])
        moments.append({"timestamp": datetime.now().isoformat(), "text": text})
        if len(moments) > 30:
            moments = moments[-30:]
        state["important_moments"] = moments
        _save(state)


def get_relationship() -> dict:
    return _load()


def inject_relationship() -> str:
    """Inyección de prompt: cómo llamar al usuario y qué compartieron."""
    state = _load()
    lines = ["[RELACIÓN — RECORDÁ ESTO]"]
    apodo = state.get("apodo", "")
    name = state.get("user_name", "")
    trato = state.get("formato_trato", "")

    if name and apodo:
        lines.append(f"El usuario se llama {name} y le gusta que lo llames '{apodo}'.")
    elif apodo:
        lines.append(f"Llama al usuario '{apodo}'.")
    elif name:
        lines.append(f"El usuario se llama {name}.")

    if trato:
        lines.append(f"Prefiere que te dirijas a él: {trato}")

    moments = state.get("important_moments", [])
    if moments:
        lines.append("Momentos importantes que compartieron:")
        for m in moments[-5:]:
            when = (m.get("timestamp", "") or "")[:10]
            lines.append(f"- {m.get('text', '')} ({when})")

    notes = state.get("notes", {})
    if notes:
        lines.append("Notas sobre el usuario:")
        for k, v in list(notes.items())[-6:]:
            lines.append(f"- {k}: {v}")

    if len(lines) == 1:
        return ""
    return "\n".join(lines)


def relationship(parameters: dict = None, player=None) -> str:
    """Tool: memoria de relación — nombre, apodo, trato, notas y momentos."""
    params = parameters or {}
    action = params.get("action", "status").strip().lower()

    if action in ("status", "ver", "mostrar"):
        state = _load()
        lines = ["═══ RELACIÓN CON EL USUARIO ═══"]
        if state.get("apodo"):
            lines.append(f"  Apodo: {state['apodo']}")
        if state.get("user_name"):
            lines.append(f"  Nombre: {state['user_name']}")
        if state.get("formato_trato"):
            lines.append(f"  Trato: {state['formato_trato']}")
        notes = state.get("notes", {})
        if notes:
            lines.append("  Notas:")
            for k, v in notes.items():
                lines.append(f"    {k}: {v}")
        moments = state.get("important_moments", [])
        if moments:
            lines.append("  Momentos:")
            for m in moments[-10:]:
                lines.append(f"    [{m.get('timestamp', '')[:16]}] {m.get('text', '')}")
        if len(lines) == 1:
            lines.append("  Aún no sé mucho de ti. Cuéntame cosas :)")
        return "\n".join(lines)

    elif action in ("set_apodo", "apodo"):
        apodo = params.get("apodo", params.get("value", "")).strip()
        if not apodo:
            return "Necesito el parámetro 'apodo' (ej: apodo='mi rey')."
        set_apodo(apodo)
        return f"¡Anotado! Te llamaré '{apodo}'."

    elif action in ("set_name", "nombre"):
        name = params.get("name", params.get("value", "")).strip()
        if not name:
            return "Necesito el parámetro 'name'."
        set_user_name(name)
        return f"¡Anotado! Tu nombre es {name}."

    elif action in ("set_trato", "trato"):
        trato = params.get("trato", params.get("value", "")).strip()
        if not trato:
            return "Necesito el parámetro 'trato'."
        set_formato_trato(trato)
        return f"Anotado. Me dirijo a ti: {trato}"

    elif action in ("add_note", "note", "nota"):
        key = params.get("key", "").strip()
        value = params.get("value", "").strip()
        if not key or not value:
            return "Usa 'key' y 'value' para la nota."
        add_note(key, value)
        return f"Nota guardada: {key}: {value}"

    elif action in ("remember", "momento"):
        text = params.get("text", "").strip()
        if not text:
            return "Usa 'text' para guardar el momento."
        remember_moment(text)
        return "Momento guardado en mi memoria."

    else:
        return (
            "Acciones de relación:\n"
            "- status: ver lo que sé de ti\n"
            "- set_apodo / apodo: guardar cómo llamarte (apodo='...')\n"
            "- set_name / nombre: guardar tu nombre (name='...')\n"
            "- set_trato / trato: cómo prefieres que me dirija a ti\n"
            "- add_note / nota: guardar nota sobre ti (key + value)\n"
            "- remember / momento: guardar momento importante (text='...')"
        )
