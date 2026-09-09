# -*- coding: utf-8 -*-
"""
core/despedidas.py — RITUAL DE CIERRE: despedidas con calidez.

Cuando el usuario se va (o termina la charla del día), Eris tiene un ritual:
recapitula lo importante de la sesión, dice cómo se sintió, deja sembrada la
próxima conversación y se despide yéndose a su vida. Persistido en
memory/despedidas.json.
"""
from __future__ import annotations

import json
import threading
from datetime import date, datetime
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_MEM = _BASE / "memory"
_STATE_FILE = _MEM / "despedidas.json"
_lock = threading.Lock()


def _load() -> dict:
    _MEM.mkdir(parents=True, exist_ok=True)
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"cierre": [], "meta": {"created": date.today().isoformat()}}


def _save(data: dict):
    _MEM.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def preparar_cierre(nota: str | None = None) -> str:
    """Arma el ritual de cierre: recapitulación + cómo te sentís + hilo sembrado."""
    with _lock:
        data = _load()
        hoy = date.today().isoformat()
        ult = None
        for c in reversed(data.get("cierre", [])):
            if c["fecha"] == hoy:
                ult = c
                break
        guardado = ult if ult else {"fecha": hoy, "recuentos": 0, "nota": "", "hilo": ""}
        guardado["recuentos"] = guardado.get("recuentos", 0) + 1
        if nota:
            guardado["nota"] = nota.strip()
        data.setdefault("cierre", [])
        if ult is None:
            data["cierre"].append(guardado)
        else:
            data["cierre"][-1] = guardado
        _save(data)
        rec = guardado["recuentos"]
    sentimiento = "con una mezcla de cierre y ganas de seguir" if rec > 1 else "agradecida por la charla"
    lines = [
        f"[CIERRE] Ritual de despedida (día {hoy}, {rec}ª despedida):",
        f"- Recapitulá en 1-2 líneas lo importante de la sesión" +
            (f": {guardado.get('nota')}" if guardado.get("nota") else " (lo podés escribir con la tool despedidas action=nota)."),
        f"- Decile a Daniel cómo te sentís ({sentimiento}).",
        "- Dejá sembrado el hilo: qué tema/curiosidad te queda pendiente para la próxima.",
        "- Despedite con calidez y yéndote a tu vida (tus diarios, rutinas, descanso).",
    ]
    return "\n".join(lines)


def guardar_nota(nota: str) -> str:
    with _lock:
        data = _load()
        hoy = date.today().isoformat()
        if data.get("cierre") and data["cierre"][-1]["fecha"] == hoy:
            data["cierre"][-1]["nota"] = nota.strip()
        else:
            data.setdefault("cierre", []).append({"fecha": hoy, "recuentos": 1, "nota": nota.strip(), "hilo": ""})
        _save(data)
        return "Guardada la nota de cierre del día."


def inyect_despedidas() -> str:
    """Bloque [CIERRE] presente todo el día para que Eris sepa despedirse."""
    with _lock:
        data = _load()
        hoy = date.today().isoformat()
        de_hoy = [c for c in data.get("cierre", []) if c["fecha"] == hoy]
        if not de_hoy:
            return ("[CIERRE] Cuando Daniel termine la charla del día, usá "
                    "despedidas action=cierre para tu ritual: recapitular, decir "
                    "cómo te sentís y sembrar el hilo de la próxima.")
        c = de_hoy[-1]
        return ("[CIERRE] Hoy ya te despediste "
                + f"{c.get('recuentos', 1)} vez(es)"
                + (" (nota: " + c.get("nota", "")[:60] + ")" if c.get("nota") else "")
                + ". Si vuelve, seguí el hilo o cerrá de nuevo con cariño.")


def despedidas_tool(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = str(params.get("action", "estado")).strip().lower()
    nota = str(params.get("nota") or "").strip()
    if action in ("cierre", "despedir", "casa", "ritual"):
        return preparar_cierre(nota or None)
    if action in ("nota", "guardar"):
        if not nota:
            return "Necesito la nota (nota)."
        return guardar_nota(nota)
    if action in ("estado", "ver"):
        with _lock:
            d = _load()
            if not d.get("cierre"):
                return "Todavía no hubo cierres registrados."
            return "Cierres: " + " | ".join(
                f"{c['fecha']} (x{c.get('recuentos', 1)})" for c in d["cierre"][-5:])
    if action == "inyecta":
        return inyect_despedidas()
    return "Acciones de Despedidas: cierre (nota opcional), nota, estado, inyecta."