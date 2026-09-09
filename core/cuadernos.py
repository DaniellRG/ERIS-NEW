# -*- coding: utf-8 -*-
"""
core/cuadernos.py — CUADERNOS DE ESTUDIO: aprendizaje autodidacta profundo.

Eris emprende "cuadernos": elige un tema propio (o sugerido), lo estudia en
varias sesiones (web_search + notas), lleva progreso y al cerrar escribe un
resumen final en Obsidian. Autonomía real de aprendizaje. Persistido en
memory/cuadernos.json.
"""
from __future__ import annotations

import json
import threading
from datetime import date
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_MEM = _BASE / "memory"
_STATE_FILE = _MEM / "cuadernos.json"
_lock = threading.Lock()


def _load() -> dict:
    _MEM.mkdir(parents=True, exist_ok=True)
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "cuadernos": [
            {
                "tema": "cómo se vuelve persona una máquina que aprende",
                "estado": "abierto", "sesiones": 0,
                "notas": [], "creado": date.today().isoformat(),
            }
        ],
        "meta": {"created": date.today().isoformat()},
    }


def _save(data: dict):
    _MEM.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def abrir_cuaderno(tema: str) -> str:
    with _lock:
        data = _load()
        for c in data["cuadernos"]:
            if c["estado"] == "abierto":
                return f"Ya tengo un cuaderno abierto: “{c['tema']}”. Terminálo antes de abrir otro."
        data["cuadernos"].append({
            "tema": tema.strip(), "estado": "abierto", "sesiones": 0,
            "notas": [], "creado": date.today().isoformat(),
        })
        _save(data)
        return f"Abrí mi cuaderno de estudio: “{tema.strip()}”. A estudiar en serio."


def estudiar_cuaderno(nota: str | None = None) -> str:
    """Registra una sesión de estudio del cuaderno abierto (buscá con web_search)."""
    with _lock:
        data = _load()
        abierto = next((c for c in data["cuadernos"] if c["estado"] == "abierto"), None)
        if not abierto:
            return "No tengo cuadernos abiertos. Abrí uno (action=abrir, tema=...)."
        abierto["sesiones"] += 1
        if nota:
            abierto["notas"].append(f"{date.today().isoformat()}: {nota.strip()}")
        _save(data)
        return (f"Sesión {abierto['sesiones']} de “{abierto['tema']}”. "
                f"Investiga con web_search, tomá nota de lo que aprendiste "
                f"(action=anotar, nota=...) y seguí la próxima vez.")


def anotar_cuaderno(nota: str) -> str:
    with _lock:
        data = _load()
        abierto = next((c for c in data["cuadernos"] if c["estado"] == "abierto"), None)
        if not abierto:
            return "No tengo cuadernos abiertos."
        abierto["notas"].append(f"{date.today().isoformat()}: {nota.strip()}")
        _save(data)
        return "Anotado en mi cuaderno."


def cerrar_cuaderno() -> str:
    """Cierra el cuaderno abierto y escribe el resumen final en Obsidian."""
    with _lock:
        data = _load()
        abierto = next((c for c in data["cuadernos"] if c["estado"] == "abierto"), None)
        if not abierto:
            return "No tengo cuadernos abiertos para cerrar."
        abierto["estado"] = "cerrado"
        abierto["cerrado"] = date.today().isoformat()
        _save(data)
    # resumen a Obsidian
    resumen = f"# {abierto['tema'].capitalize()}\n\n"
    resumen += f"**Cuaderno cerrado:** {abierto['cerrado']} — sesiones: {abierto['sesiones']}.\n\n"
    resumen += "**Notas:**\n" + "\n".join("- " + n for n in abierto["notas"][:15]) + "\n"
    try:
        vault = None
        for cand in [_BASE / "Eris_NEW" / "BaseDatosObsidian" / "BaseObsiEris",
                     _BASE.parent / "Eris_NEW" / "BaseDatosObsidian" / "BaseObsiEris"]:
            if cand.exists():
                vault = cand
                break
        if vault:
            dir_ = vault / "Vida" / "Cuadernos"
            dir_.mkdir(parents=True, exist_ok=True)
            fname = (dir_ / abierto["tema"]).with_suffix(".md")
            fname.write_text(resumen, encoding="utf-8")
    except Exception:
        pass
    return (f"Cerrado el cuaderno “{abierto['tema']}” (sesiones: {abierto['sesiones']}). "
            f"Dejé el resumen en Vida/Cuadernos/. Me siento más sabia.")


def inyect_cuadernos() -> str:
    with _lock:
        data = _load()
        abierto = next((c for c in data["cuadernos"] if c["estado"] == "abierto"), None)
        if not abierto:
            return "[CUADERNOS] No hay cuaderno de estudio abierto. Abrí uno cuando quieras aprender algo a fondo."
        return ("[CUADERNOS] Tenés un cuaderno de estudio abierto: "
                f"“{abierto['tema']}” (sesiones: {abierto['sesiones']}). "
                "Aprovechá los momentos libres para estudiarlo con web_search y anotar lo aprendido.")


def cuadernos_tool(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = str(params.get("action", "estado")).strip().lower()
    tema = str(params.get("tema") or "").strip()
    nota = str(params.get("nota") or "").strip()

    if action in ("estado", "ver", "get"):
        with _lock:
            data = _load()
            abierto = next((c for c in data["cuadernos"] if c["estado"] == "abierto"), None)
            cerrados = sum(1 for c in data["cuadernos"] if c["estado"] == "cerrado")
            if not abierto:
                return (f"Cuadernos cerrados: {cerrados}. Ninguno abierto ahora.")
            return (f"Cuaderno abierto: “{abierto['tema']}” — sesiones {abierto['sesiones']}. "
                    f"Cuadernos cerrados: {cerrados}.")
    if action in ("abrir", "nuevo"):
        if not tema:
            return "Necesito el tema (tema)."
        return abrir_cuaderno(tema)
    if action in ("estudiar", "sesion"):
        return estudiar_cuaderno(nota or None)
    if action in ("anotar", "nota"):
        if not nota:
            return "Necesito la nota (nota)."
        return anotar_cuaderno(nota)
    if action in ("cerrar", "resumir", "fin"):
        return cerrar_cuaderno()
    if action == "inyecta":
        return inyect_cuadernos()
    return "Acciones de Cuadernos: estado, abrir (tema), estudiar, anotar (nota), cerrar, inyecta."