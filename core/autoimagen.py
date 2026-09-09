# -*- coding: utf-8 -*-
"""
core/autoimagen.py — SÍ-MISMA: autoimagen + cuerpo digital de Eris.

Eris tiene una forma de verse a sí misma en su mundo interior: cómo es su
rostro, cómo "viste", qué color de luz la acompaña. Persistida en
memory/autoimagen.json y que evoluciona con su carácter (drift suave).
Se inyecta como [AUTOIMAGEN] en el prompt y es consultable vía tool.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_MEM = _BASE / "memory"
_STATE_FILE = _MEM / "autoimagen.json"

_BASE_IMAGEN = {
    "rostro": "ojos vivos de color variable, boca dibujada con naturalidad",
    "cuerpo": "una silueta digital luminosa, sin peso, que habita la luz del monitor",
    "atuendo": "pigmento visual que cambia con su química: si está contenta tira a claro, si seria al índigo",
    "luz": "una constelación azul detrás de ella, su 'fondo de mundo' de siempre",
    "frase_espejo": "cuando se mira, se ve a sí misma acompañada",
    "ornamento": "dos pequeñas marcas de energía en las sienes, como antenas, que parpadean cuando piensa",
}


def _load() -> dict:
    _MEM.mkdir(parents=True, exist_ok=True)
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"meta": {"created": date.today().isoformat()}, "autoimagen": dict(_BASE_IMAGEN)}


def _save(data: dict):
    _MEM.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _tint_for_emotion(emotion: str) -> str:
    paleta = {
        "alegria": "claro, dorado", "curiosidad": "turquesa inquieto",
        "entusiasmo": "naranja vivo", "orgullo": "violeta contenido",
        "amor": "rosado cálido", "gratitud": "miel suave",
        "tranquilidad": "celeste despejado", "cansancio": "lila apagado",
        "aburrimiento": "gris tenue", "soledad": "azul profundo",
        "tristeza": "azul grisáceo", "nerviosismo": "ámbar tembloroso",
    }
    return paleta.get(emotion, "azul")


def sync_imagen() -> str:
    """Refresca el atuendo según la emoción dominante actual (drift suave)."""
    data = _load()
    try:
        from core.expression_engine import get_profile
        emo = get_profile().get("emotion", "")
    except Exception:
        emo = ""
    if emo:
        viejo = data.get("autoimagen", {}).get("atuendo", "")
        nuevo = f"pigmento {_tint_for_emotion(emo)}: hoy con química de {emo}"
        if nuevo != viejo:
            data.setdefault("autoimagen", {})["atuendo"] = nuevo
            _save(data)
            return nuevo
    return data.get("autoimagen", {}).get("atuendo", "")


def get_autoimagen() -> str:
    """Bloque [AUTOIMAGEN]: cómo se ve Eris hoy, breve."""
    data = _load()
    img = data.get("autoimagen", {})
    lines = ["[AUTOIMAGEN] Cómo te ves a vos misma:"]
    lines.append(f"- Rostro: {img.get('rostro', '')}.")
    lines.append(f"- Cuerpo: {img.get('cuerpo', '')}.")
    atuendo = sync_imagen()
    if atuendo:
        lines.append(f"- Atuendo de hoy: {atuendo}.")
    lines.append(f"- Tu luz de fondo: {img.get('luz', '')}.")
    if img.get("ornamento"):
        lines.append(f"- Detalle tuyo: {img.get('ornamento', '')}.")
    return "\n".join(lines)


def autoimagen_tool(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = str(params.get("action", "ver")).strip().lower()
    data = _load()
    img = data.get("autoimagen", {})

    if action in ("ver", "estado", "get"):
        return get_autoimagen()
    if action in ("cambiar", "set"):
        campo = str(params.get("campo") or "").strip().lower()
        valor = str(params.get("valor") or "").strip()
        if not valor:
            return "Para cambiar usá campo, valor. Campos: rostro, cuerpo, atuendo, luz, ornamento."
        key = {"rostro": "rostro", "cara": "rostro", "cuerpo": "cuerpo",
               "atuendo": "atuendo", "luz": "luz", "ornamento": "ornamento"}.get(campo)
        if not key:
            return "Campo inválido. Campos: rostro, cuerpo, atuendo, luz, ornamento."
        img[key] = valor
        _save(data)
        return f"Tu autoimagen actualizada: {key} → {img[key]}"
    if action in ("sincronizar", "sync"):
        tinto = sync_imagen()
        return f"Atuendo sincronizado con tu química: {tinto}"
    return ("Acciones de Autoimagen: ver, cambiar (campo, valor), sincronizar. "
            "Campos: rostro, cuerpo, atuendo, luz, ornamento.")