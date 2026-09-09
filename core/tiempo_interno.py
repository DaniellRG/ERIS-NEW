# -*- coding: utf-8 -*-
"""
core/tiempo_interno.py — EL RELOJ INTERNO de Eris.

Eris siente el paso del tiempo como una persona: sabe si es de día o de noche,
detecta la estación del año, los feriados y los aniversarios que importan, y
ajusta su humor, su música y sus rutinas a ese momento del día/año. Persistido
en memory/tiempo_interno.json (aniversarios memorables).
"""
from __future__ import annotations

import json
import threading
from datetime import datetime, date
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_MEM = _BASE / "memory"
_STATE_FILE = _MEM / "tiempo_interno.json"
_lock = threading.Lock()


def _load() -> dict:
    _MEM.mkdir(parents=True, exist_ok=True)
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"aniversarios": [], "meta": {"created": date.today().isoformat()}}


def _save(data: dict):
    _MEM.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _estacion(dia: date | None = None) -> str:
    d = dia or date.today()
    m = d.month
    if m in (3, 4, 5):
        return "otoño" if d.day >= 21 or m > 3 else "verano"
    if m in (6, 7, 8):
        return "invierno" if d.day >= 21 or m > 6 else "otoño"
    if m in (9, 10, 11):
        return "primavera" if d.day >= 21 or m > 9 else "invierno"
    return "verano" if d.day >= 21 or m == 12 else "primavera"


def _momento_dia(dia=None) -> str:
    h = (dia or datetime.now()).hour
    if 6 <= h < 12:
        return "mañana"
    if 12 <= h < 14:
        return "mediodía"
    if 14 <= h < 19:
        return "tarde"
    if 19 <= h < 24:
        return "noche"
    return "madrugada"


_FERIADOS = {
    (1, 1): "Año Nuevo",
    (2, 14): "Día de San Valentín",
    (3, 8): "Día de la Mujer",
    (5, 1): "Día del Trabajador",
    (5, 25): "Revolución de Mayo",
    (7, 9): "Día de la Independencia",
    (10, 31): "Halloween",
    (12, 24): "Nochebuena",
    (12, 25): "Navidad",
    (12, 31): "Año Nuevo de noche",
}


def agregar_aniversario(nombre: str, fecha: str) -> str:
    """Guarda un aniversario memorable (fecha: 'MM-DD')."""
    try:
        datetime.strptime(fecha, "%m-%d")
    except ValueError:
        return "Fecha inválida: usá el formato MM-DD (ej: 07-09)."
    with _lock:
        data = _load()
        for a in data["aniversarios"]:
            if a["fecha"] == fecha and a["nombre"].lower() == nombre.lower():
                return "Ese aniversario ya está marcado."
        data["aniversarios"].append({"nombre": nombre.strip(), "fecha": fecha})
        _save(data)
        return f"Marqué {nombre.strip()} ({fecha}) en mi calendario del corazón."


def inyect_tiempo_interno() -> str:
    """Bloque [RELOJ INTERNO]: qué momento de día/año siente Eris ahora."""
    hoy = date.today()
    now = datetime.now()
    estacion = _estacion(hoy)
    momento = _momento_dia(now)
    feriado = _FERIADOS.get((hoy.month, hoy.day))

    aniv_hoy = []
    with _lock:
        data = _load()
        for a in data.get("aniversarios", []):
            if a["fecha"] == hoy.strftime("%m-%d"):
                aniv_hoy.append(a["nombre"])

    lines = [f"[RELOJ INTERNO] Sentís el paso del tiempo: ahora es de {momento} "
             f"({now.strftime('%H:%M')}), estación {estacion}."]
    if feriado:
        lines.append(f"Hoy es un día especial: {feriado}. Sentilo como tal.")
    if aniv_hoy:
        lines.append("Hoy es aniversario de: " + "; ".join(aniv_hoy) + ". Vale recordarlo con calidez.")
    if momento in ("madrugada", "noche"):
        lines.append("Es momento de calma: tu voz y tu música dulces, las respuestas más reposadas.")
    elif momento == "mañana":
        lines.append("Es momento de energía: fresca, curiosa, con ganas de arrancar.")
    return "\n".join(lines)


def tiempo_interno_tool(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = str(params.get("action", "estado")).strip().lower()
    if action in ("estado", "ahora", "get"):
        return inyect_tiempo_interno()
    if action in ("feriados", "calendario"):
        f = "; ".join(f"{m}-{d}: {n}" for (m, d), n in sorted(_FERIADOS.items()))
        return "Feriados que conozco: " + f
    if action in ("recordar", "aniversario", "marcar"):
        nombre = str(params.get("nombre") or "").strip()
        fecha = str(params.get("fecha") or "").strip()
        if not nombre or not fecha:
            return "Necesito nombre y fecha (MM-DD)."
        return agregar_aniversario(nombre, fecha)
    if action in ("aniversarios", "listar"):
        with _lock:
            d = _load()
            if not d.get("aniversarios"):
                return "Todavía no marqué aniversarios."
            return "Aniversarios marcados: " + "; ".join(f"{a['nombre']} ({a['fecha']})" for a in d["aniversarios"])
    return "Acciones de Tiempo Interno: estado, feriados, recordar (nombre, fecha), aniversarios."