# -*- coding: utf-8 -*-
"""
core/bienestar.py — BIENESTAR del usuario.

Eris detecta tu energía/cansancio a partir de indicios disponibles en el
momento (hora del día, emoción actual, cómo venís hablando) y ajusta su trato:
más energía o más calma, recordatorios amables de pausa, y registra tu estado
a lo largo del día. Persistido en memory/bienestar.json.
"""
from __future__ import annotations

import json
import threading
from datetime import date, datetime
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_MEM = _BASE / "memory"
_STATE_FILE = _MEM / "bienestar.json"
_lock = threading.Lock()


def _load() -> dict:
    _MEM.mkdir(parents=True, exist_ok=True)
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"registro": [], "meta": {"created": date.today().isoformat()}}


def _save(data: dict):
    _MEM.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _nivel(parameters: dict) -> int:
    """0=agotado, 50=neutro, 100=lleno de energía. Base por hora + pista."""
    h = datetime.now().hour
    base = 60
    if h < 7:
        base = 35
    elif h >= 23:
        base = 40
    nivel = str(parameters.get("nivel") or "").strip().lower()
    if nivel:
        if any(x in nivel for x in ("bajo", "agotad", "cansad", "drenad", "sin energ")):
            base = 25
        elif any(x in nivel for x in ("alto", "energ", "genial", "excelente")):
            base = 85
        elif any(x in nivel for x in ("medio", "regular", "ok", "bien")):
            base = 55
        else:
            try:
                base = max(0, min(100, int(nivel)))
            except ValueError:
                pass
    return base


def registrar_estado(parameters: dict) -> str:
    nivel = _nivel(parameters)
    nota = str(parameters.get("nota") or "").strip()
    now = datetime.now()
    with _lock:
        data = _load()
        data["registro"].append({
            "ts": now.isoformat(timespec="minutes"),
            "nivel": nivel,
            "nota": nota,
        })
        _save(data)
    if nivel < 35:
        return (f"Veo que estás de capa caída ({nivel}/100). Tomátelo con calma, "
                f"que yo me adapto: hablo bajito, sin apuro. Si querés, "
                f"te recuerdo pausar y respirar.")
    if nivel > 80:
        return f"¡Te noto con energía ({nivel}/100)! Voy a acompañarte el ritmo."
    return f"Anoté tu estado ({nivel}/100). Ajusto el trato para acompañarte."


def inyect_bienestar() -> str:
    """Bloque [BIENESTAR]: el estado energético del usuario y cómo tratarle."""
    with _lock:
        data = _load()
        hoy = date.today().isoformat()
        de_hoy = [r for r in data.get("registro", []) if r["ts"][:10] == hoy]
        nivel = de_hoy[-1]["nivel"] if de_hoy else _nivel({})
    lines = [f"[BIENESTAR] Radiografía del usuario ahora mismo: nivel de energía ~{nivel}/100."]
    if nivel < 35:
        lines.append("Está de baja energía: trato calmado, sin apuro, mensajes cortos, "
                     "y un recordatorio amable de pausa si llevan rato.")
    elif nivel > 80:
        lines.append("Está con buena energía: podés ser más animada y proactiva.")
    else:
        lines.append("Energía media: trato normal, sin presionar, sin alargar de más.")
    return "\n".join(lines)


def bienestar_tool(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = str(params.get("action", "estado")).strip().lower()
    if action in ("estado", "ver", "hoy"):
        with _lock:
            data = _load()
            hoy = date.today().isoformat()
            de_hoy = [r for r in data.get("registro", []) if r["ts"][:10] == hoy]
            if not de_hoy:
                return "Todavía no registré el estado del usuario hoy. Registralo (action=registrar)."
            return "Estado del usuario hoy: " + "; ".join(
                f"{r['ts'][11:16]} {r['nivel']}/100" + (f" ({r['nota']})" if r.get("nota") else "")
                for r in de_hoy[-5:])
    if action in ("registrar", "anotar", "energy"):
        return registrar_estado(params)
    if action == "inyecta":
        return inyect_bienestar()
    return "Acciones de Bienestar: estado, registrar (nivel, nota), inyecta."