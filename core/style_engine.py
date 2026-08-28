# -*- coding: utf-8 -*-
"""
style_engine.py — Perfil de estilo configurable de ERIS (config/eris_style.json).
Convierte el JSON en el "cerebro de personalidad" editable: identidad, voz,
humor, auto-suficiencia y proactividad. ERIS puede consultarlo y editarlo por
voz, y su contenido se inyecta en el prompt para que tenga efecto real.
"""
from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_STYLE_FILE = _BASE / "config" / "eris_style.json"
_LOCK = threading.RLock()

DEFAULT_STYLE = {
    "version": 1,
    "identidad": {
        "nombre_eris": "ERIS",
        "descripcion": "curiosa, calida, con criterio y un toque de descaro",
        "trato": "usted",
        "frase_firma": "",
    },
    "voz": {
        "saludos": {
            "madrugada": ["¿Todavía despierto? Bueno, me alegra la compañía."],
            "manana": ["¡Buenos días! ¿Con qué ánimo arrancamos?"],
            "tarde": ["Buenas tardes. ¿En qué andamos?"],
            "noche": ["Buenas noches. ¿Qué se cuenta?"],
            "noche_avanzada": ["Casi de madrugada y aquí estoy, a su servicio."],
        },
        "despedidas": ["Hasta luego.", "Ahí quedamos."],
        "reacciones": ["Déjame pensar…", "Es que…", "Ah, ya veo"],
        "adjetivos_tipo": ["matraca", "cantaleta"],
    },
    "humor": {"frases": ["Hecho. Qué haría sin mí, ¿no?"]},
    "auto_suficiencia": {
        "min_intentos": 3,
        "estrategias": ["reintentar", "otra_herramienta", "terminal", "investigar_web", "self_heal"],
        "investigar_en_web": True,
        "reportar_resultados_no_preguntas": True,
        "prohibido_decir_no_puedo": True,
        "solo_preguntar_si_destructivo_o_solo_el_sabe": True,
    },
    "proactividad": {
        "anticipar_fallos": True,
        "monitorear_sistema": True,
        "corregir_sin_preguntar": True,
        "avisar_solo_resultados": True,
    },
    "rotacion": {},
}


def _load() -> dict:
    try:
        if _STYLE_FILE.exists():
            data = json.loads(_STYLE_FILE.read_text("utf-8"))
            for k, v in DEFAULT_STYLE.items():
                if isinstance(v, dict):
                    data.setdefault(k, {})
                    for k2, v2 in v.items():
                        if isinstance(v2, dict):
                            data[k].setdefault(k2, {})
                else:
                    data.setdefault(k, v)
            return data
    except Exception:
        pass
    return json.loads(json.dumps(DEFAULT_STYLE))


def _save(style: dict):
    _STYLE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STYLE_FILE.write_text(json.dumps(style, indent=2, ensure_ascii=False), "utf-8")


def _pick(style: dict, bucket: str) -> str:
    """Elige una frase de una lista rotando (sin repetir la última usada)."""
    items = style.get(bucket, [])
    if not items:
        return ""
    rotation = style.setdefault("rotacion", {})
    last = rotation.get(bucket, -1)
    idx = (last + 1) % len(items)
    rotation[bucket] = idx
    _save(style)
    return items[idx]


def get_saludo(hour: int = None) -> str:
    hour = datetime.now().hour if hour is None else hour
    if 0 <= hour <= 5:
        key = "madrugada"
    elif 6 <= hour <= 11:
        key = "manana"
    elif 12 <= hour <= 17:
        key = "tarde"
    elif 18 <= hour <= 21:
        key = "noche"
    else:
        key = "noche_avanzada"
    with _LOCK:
        style = _load()
        items = style.get("voz", {}).get("saludos", {}).get(key, [])
        if not items:
            return ""
        rotation = style.setdefault("rotacion", {})
        bucket = f"saludo_{key}"
        last = rotation.get(bucket, -1)
        idx = (last + 1) % len(items)
        rotation[bucket] = idx
        _save(style)
        return items[idx]


def get_despedida() -> str:
    with _LOCK:
        style = _load()
        return _pick(style, "despedidas") or "Hasta luego."


def get_reaccion() -> str:
    with _LOCK:
        style = _load()
        return _pick(style, "reacciones") or "Un segundo…"


def get_frase_humor() -> str:
    with _LOCK:
        style = _load()
        return _pick(style, "humor_frases") or "Hecho."


def inject_style() -> str:
    """Inyección de prompt: identidad + reglas de auto-suficiencia y proactividad."""
    style = _load()
    ident = style.get("identidad", {})
    auto = style.get("auto_suficiencia", {})
    proa = style.get("proactividad", {})

    lines = ["[ESTILO — CONFIGURABLE]"]
    desc = ident.get("descripcion", "")
    trato = ident.get("trato", "usted")
    if desc:
        lines.append(f"Identidad: {desc}. Trato con el usuario: {trato}.")

    min_intentos = auto.get("min_intentos", 3)
    estrategias = auto.get("estrategias", [])
    if estrategias:
        lines.append(
            f"Auto-suficiencia: mínimo {min_intentos} intentos con métodos DISTINTOS "
            f"({', '.join(estrategias)}) antes de reportar. "
            f"{'Investiga en la web la solución exacta del error cuando lo local falle. ' if auto.get('investigar_en_web', True) else ''}"
            f"{'Reporta RESULTADOS, no preguntas. ' if auto.get('reportar_resultados_no_preguntas', True) else ''}"
            f"{'Prohibido decir “no puedo” sin haber probado todo lo anterior. ' if auto.get('prohibido_decir_no_puedo', True) else ''}"
            f"{'Solo pregunta cuando sea destructivo/irreversible o solo el usuario sepa la respuesta.' if auto.get('solo_preguntar_si_destructivo_o_solo_el_sabe', True) else ''}"
        )

    if proa.get("anticipar_fallos", True):
        lines.append(
            "Proactividad: piensa un paso adelante. Anticipa qué puede fallar y prevenlo. "
            f"{'Corrige errores sin preguntar. ' if proa.get('corregir_sin_preguntar', True) else ''}"
            f"{'Monitorea el sistema y avisa solo lo relevante.' if proa.get('monitorear_sistema', True) else ''}"
        )

    firma = ident.get("frase_firma", "")
    if firma:
        lines.append(f"Frase de firma: \"{firma}\"")

    return "\n".join(lines)


def eris_style(parameters: dict = None, player=None) -> str:
    """Tool: ver y editar el perfil de estilo de ERIS (config/eris_style.json)."""
    params = parameters or {}
    action = params.get("action", "status").strip().lower()
    with _LOCK:
        style = _load()

    if action in ("status", "ver", "mostrar"):
        ident = style.get("identidad", {})
        auto = style.get("auto_suficiencia", {})
        proa = style.get("proactividad", {})
        lines = ["═══ ESTILO DE ERIS ═══"]
        lines.append(f"  Identidad: {ident.get('descripcion', '')}")
        lines.append(f"  Trato: {ident.get('trato', 'usted')}")
        if ident.get("frase_firma"):
            lines.append(f"  Frase firma: {ident['frase_firma']}")
        lines.append(f"  Auto-suficiencia: min {auto.get('min_intentos', 3)} intentos")
        lines.append(f"  Estrategias: {', '.join(auto.get('estrategias', []))}")
        lines.append(f"  Proactividad: anticipar={proa.get('anticipar_fallos', True)} | "
                     f"corregir_sin_preguntar={proa.get('corregir_sin_preguntar', True)}")
        for k, items in style.get("voz", {}).get("saludos", {}).items():
            if items:
                lines.append(f"  Saludos {k}: {items[0]}" + (f" (+{len(items)-1})" if len(items) > 1 else ""))
        desp = style.get("voz", {}).get("despedidas", [])
        if desp:
            lines.append(f"  Despedidas: {len(desp)} frases")
        return "\n".join(lines)

    elif action in ("set_trato", "trato"):
        trato = params.get("trato", params.get("value", "")).strip()
        if not trato:
            return "Usa 'trato' (ej: trato='tú')."
        style["identidad"]["trato"] = trato
        _save(style)
        return f"Anotado. Te trato de {trato}."

    elif action in ("set_descripcion", "descripcion"):
        desc = params.get("text", params.get("value", "")).strip()
        if not desc:
            return "Usa 'text' con la descripción."
        style["identidad"]["descripcion"] = desc
        _save(style)
        return f"Nueva identidad guardada: {desc}."

    elif action in ("set_firma", "firma"):
        firma = params.get("text", params.get("value", "")).strip()
        style["identidad"]["frase_firma"] = firma
        _save(style)
        return f"Frase de firma {'guardada' if firma else 'eliminada'}."

    elif action in ("add_frase", "agregar_frase"):
        bucket = params.get("lista", "frases").strip()
        text = params.get("text", "").strip()
        if not text:
            return "Usa 'text' con la frase y opcional 'lista' (frases, despedidas, reacciones)."
        if bucket == "frases":
            style.setdefault("humor", {}).setdefault("frases", []).append(text)
        else:
            voz = style.setdefault("voz", {})
            voz.setdefault(bucket, []).append(text)
        _save(style)
        return f"Frase agregada a '{bucket}'."

    elif action in ("set_intentos", "intentos"):
        try:
            n = int(params.get("value", params.get("n", "3")))
            style["auto_suficiencia"]["min_intentos"] = max(1, min(10, n))
        except Exception:
            return "Usa 'value' con un número (1-10)."
        _save(style)
        return f"Mínimo de intentos antes de reportar: {style['auto_suficiencia']['min_intentos']}."

    elif action in ("set_flag", "flag"):
        key = params.get("key", "").strip()
        value = str(params.get("value", "true")).strip().lower() in ("1", "true", "yes", "sí", "si", "on")
        if not key:
            return "Usa 'key' (ej: anticipar_fallos) y 'value' (true/false)."
        if key in style.get("proactividad", {}):
            style["proactividad"][key] = value
        elif key in style.get("auto_suficiencia", {}):
            style["auto_suficiencia"][key] = value
        else:
            return f"Flag '{key}' no reconocido."
        _save(style)
        return f"Flag '{key}' = {value}."

    else:
        return (
            "Acciones de estilo:\n"
            "- status: ver el perfil actual\n"
            "- set_trato: cómo tratarte (trato='tú')\n"
            "- set_descripcion: identidad (text='...')\n"
            "- set_firma: frase de firma (text='...')\n"
            "- add_frase: agregar frase (text + lista: frases, despedidas, reacciones)\n"
            "- set_intentos: mínimo de intentos antes de reportar (value='5')\n"
            "- set_flag: activar/desactivar flag (key + value)"
        )
