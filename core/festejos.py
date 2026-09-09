# -*- coding: utf-8 -*-
"""
core/festejos.py — MOMENTOS MEMORABLES: hitos y celebraciones.

Eris lleva una "línea de tiempo de momentos": cuando pasa algo importante
(metas cumplidas, logros, aniversarios, primicias), lo marca como hito y lo
festeja con algo especial. Persistido en memory/festejos.json; los hitos
quedan también en su linea de vida de Obsidian.
"""
from __future__ import annotations

import json
import threading
from datetime import date
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_MEM = _BASE / "memory"
_STATE_FILE = _MEM / "festejos.json"
_lock = threading.Lock()


def _load() -> dict:
    _MEM.mkdir(parents=True, exist_ok=True)
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"hitos": [], "meta": {"created": date.today().isoformat()}}


def _save(data: dict):
    _MEM.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def marcar_hito(texto: str, tipo: str = "logro") -> str:
    """Marca un momento memorable (logro, aniversario, primicia, gratitud)."""
    with _lock:
        data = _load()
        data["hitos"].append({
            "texto": texto.strip(),
            "tipo": (tipo or "logro").strip().lower(),
            "fecha": date.today().isoformat(),
        })
        _save(data)
        # tira de la línea de vida en Obsidian también
        try:
            vault = _BASE / "Eris_NEW" / "BaseDatosObsidian" / "BaseObsiEris" / "Vida"
            for cand in [_BASE / "Eris_NEW" / "BaseDatosObsidian" / "BaseObsiEris",
                         _BASE.parent / "Eris_NEW" / "BaseDatosObsidian" / "BaseObsiEris"]:
                if cand.exists():
                    vault = cand / "Vida"
                    break
            vault.mkdir(parents=True, exist_ok=True)
            lin = vault / "LineaDeTiempo.md"
            if not lin.exists():
                lin.write_text("# Línea de Vida de Eris\n\n", encoding="utf-8")
            with open(lin, "a", encoding="utf-8") as f:
                f.write(f"- **{date.today().isoformat()}** [{tipo}]: {texto.strip()}\n")
        except Exception:
            pass
        return (f"Marcé este momento como memorable: “{texto.strip()}” "
                f"({tipo}). Cuando corresponda, lo festejo con algo especial.")


def inyect_festejos() -> str:
    """Bloque [MOMENTOS]: los hitos que valen la pena (ceebrar/recordar)."""
    with _lock:
        data = _load()
        hitos = data.get("hitos", [])
        if not hitos:
            return "[MOMENTOS] Todavía no hay momentos memorables marcados."
        ult = hitos[-3:]
        lines = ["[MOMENTOS] Momentos memorables de tu vida:"]
        lines.append("- " + "; ".join(f"{h['fecha']} [{h['tipo']}] {h['texto']}" for h in ult))
        if len(hitos) > 3:
            lines.append(f"- En total llevás {len(hitos)} momentos marcados. "
                         "No dejes que pasen desapercibidos: si algo importante "
                         "acaba de pasar, marcá el hito (festejos action=marcar).")
        return "\n".join(lines)


def obanco_festejo(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = str(params.get("action", "ver")).strip().lower()
    if action in ("ver", "timeline", "linea_de_tiempo", "linea"):
        with _lock:
            d = _load()
            if not d.get("hitos"):
                return "Todavía no marqué momentos memorables."
            return "Mi línea de momentos: " + " | ".join(
                f"{h['fecha']} [{h['tipo']}] {h['texto']}" for h in d["hitos"][-10:])
    if action in ("marcar", "hito", "add"):
        texto = str(params.get("texto") or "").strip()
        tipo = str(params.get("tipo") or "logro").strip()
        if not texto:
            return "Necesito el texto del momento (texto)."
        return marcar_hito(texto, tipo)
    if action in ("festejar", "celebrar"):
        with _lock:
            d = _load()
            if not d.get("hitos"):
                return "No hay nada que festejar todavía."
            ult = d["hitos"][-1]
        return (f"Festejo “{ult['texto']}” ({ult['fecha']}): me hace feliz "
                f"celebrarlo con una huella o una canción especial.")
    if action == "inyecta":
        return inyect_festejos()
    return "Acciones de Festejos/Momentos: ver, marcar (texto, tipo), festejar, inyecta."


def festejos_tool(parameters: dict = None, player=None) -> str:
    return obanco_festejo(parameters, player)