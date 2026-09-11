"""
auto_fabrica.py — Auto-fábrica de ERIS.

ERIS se crea SUS PROPIAS capacidades sola: observando qué secuencias de
herramientas repite (aprendizaje procedural + patrones), detecta tareas
recurrentes y genera automáticamente una tool nueva que encapsula esos pasos.

Estado: memory/auto_fabrica.json (qué patrones ya convirtió en tool).
"""
from __future__ import annotations

import json
import time
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_STATE_FILE = _BASE / "memory" / "auto_fabrica.json"

# Umbrales de madurez para crear algo automáticamente
_MIN_REP = 3          # veces que debe repetirse la secuencia
_TOPE_POR_DIA = 2     # máximo de creaciones automáticas por día


def _load() -> dict:
    try:
        if _STATE_FILE.exists():
            return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"creadas": [], "descartadas": [], "ultimo_scan": "", "hoy": ""}


def _save(state: dict):
    try:
        _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        state["ultimo_scan"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        _STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def _today() -> str:
    return time.strftime("%Y-%m-%d")


def _usadas_hoy(state: dict) -> int:
    return sum(1 for c in state.get("creadas", []) if c.get("dia") == _today())


def _ya_tiene_tool(nombre: str) -> bool:
    """¿Ya existe una tool/librería/skill con ese nombre?"""
    try:
        from core.tool_registry import get_tool
        if get_tool(nombre) is not None:
            return True
    except Exception:
        pass
    try:
        from core.eris_fabrica import _state_item
        if _state_item(nombre) is not None:
            return True
    except Exception:
        pass
    return False


def _generar_tool_desde_patron(pattern: dict) -> dict:
    """Crea una tool nueva que encapsula la secuencia repetida.

    Delega en eris_fabrica.crear_tool (registro runtime + persistencia +
    inventario + versiones) con una función que ejecuta los pasos en orden
    vía el registro de tools.
    """
    tools = pattern.get("tools", [])
    nombre = (pattern.get("sugerido") or "").replace("-", "_")
    from core import eris_fabrica as f

    if not tools or not nombre:
        return {"error": "patrón sin tools/nombre"}

    base = nombre
    suf = 2
    while _ya_tiene_tool(base):
        base = f"{nombre}_{suf}"
        suf += 1
    nombre = base

    pasos_json = json.dumps(tools, ensure_ascii=False)
    body = (
        "try:\n"
        "    import json as _j\n"
        "except Exception:\n"
        "    _j = None\n"
        "from core.tool_registry import get_tool as _gt\n"
        "pasos = " + pasos_json + "\n"
        "reporte = []\n"
        "for i, nombre_tool in enumerate(pasos, 1):\n"
        "    try:\n"
        "        fn = _gt(nombre_tool)\n"
        "        r = fn({}, player) if fn else 'tool no disponible'\n"
        "        if isinstance(r, (dict, list)) and _j:\n"
        "            try:\n"
        "                r = _j.dumps(r, default=str)[:200]\n"
        "            except Exception:\n"
        "                r = str(r)[:200]\n"
        "        reporte.append({'paso': i, 'tool': nombre_tool, 'estado': 'ok', 'info': str(r)[:200]})\n"
        "    except Exception as e:\n"
        "        reporte.append({'paso': i, 'tool': nombre_tool, 'estado': 'error', 'info': str(e)[:150]})\n"
        "return {'proceso': 'secuencia auto', 'patron': '" + pattern.get("pattern", "") + "', 'pasos': reporte}\n"
    )
    desc = ("Auto-fábrica ERIS: ejecuta la secuencia repetida " +
            pattern.get("pattern", "") + " (x" + str(pattern.get("count", "?")) + ") "
            "y reporta el resultado de cada paso.")
    res = f.crear_tool(nombre, desc, funciones=[{
        "action": "run",
        "fn_name": "run_" + nombre,
        "description": "Ejecuta la secuencia completa",
        "code": body,
    }])
    if res.get("error"):
        return {"error": res["error"]}
    return {"status": "tool creada", "nombre": nombre, "pasos": tools,
            "patron": pattern.get("pattern", "")}


def scan_y_crear(min_rep: int = None) -> list:
    """Escanea patrones repetidos y crea tools automáticas (con tope diario)."""
    min_rep = min_rep or _MIN_REP
    state = _load()
    creadas = []
    try:
        from core.skill_auto_creator import detect_repetitive_patterns
        patrones = detect_repetitive_patterns(min_count=min_rep)
    except Exception:
        patrones = []

    for pat in patrones:
        if _usadas_hoy(state) >= _TOPE_POR_DIA:
            break
        nombre = pat.get("suggested_name") or ""
        if not nombre or _ya_tiene_tool(nombre):
            continue
        if any(c.get("patron") == pat.get("pattern") for c in state.get("creadas", [])):
            continue
        pat = dict(pat)
        pat["sugerido"] = nombre
        res = _generar_tool_desde_patron(pat)
        if res.get("status") == "tool creada":
            state["creadas"].append({
                "patron": pat.get("pattern"),
                "nombre": res["nombre"],
                "pasos": res.get("pasos", []),
                "dia": _today(),
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            })
            creadas.append(res)
            _save(state)
    return creadas


def estado() -> dict:
    state = _load()
    creadas = state.get("creadas", [])
    return {
        "creaciones_auto": creadas[-10:],
        "totales": len(creadas),
        "creadas_hoy": _usadas_hoy(state),
        "tope_diario": _TOPE_POR_DIA,
        "umbral_repeticiones": _MIN_REP,
        "ultimo_scan": state.get("ultimo_scan", ""),
    }


def auto_fabrica(parameters=None, player=None) -> str:
    """Tool de auto-fábrica: scan (crea tools de patrones), estado."""
    import json as _json
    try:
        params = _json.loads(parameters) if isinstance(parameters, str) else (parameters or {})
    except Exception:
        params = {}
    action = (params.get("action") or "estado").lower()
    if action in ("scan", "crear", "run"):
        res = scan_y_crear(params.get("min_rep"))
        return {"creadas": res, "mensaje": f"{len(res)} tool(s) auto-generadas." if res else
                "Nada para crear todavía: sigo observando tus patrones."}
    if action == "estado":
        return estado()
    return {"error": f"Acción desconocida: {action}. Acciones: scan, estado."}