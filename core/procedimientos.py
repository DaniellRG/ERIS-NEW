"""
procedimientos.py — Aprendizaje procedural de ERIS.

ERIS aprende "cómo se hace X": asocia la intención del usuario con las
herramientas que usó para resolverla. Con cada repetición consolida un
procedimiento y puede reutilizarlo (o enseñarlo) cuando vuelve a aparecer
esa intención.

Estado: memory/procedimientos.json
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_STATE_FILE = _BASE / "memory" / "procedimientos.json"

# Buffer en memoria: intención actual → lista de tools usadas en este turno
_current_intent = ""
_current_tools: list[str] = []
_last_flush = 0.0


def _load() -> dict:
    try:
        if _STATE_FILE.exists():
            return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"procedimientos": {}, "created_at": "", "updated_at": ""}


def _save(state: dict):
    try:
        _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        state["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        _STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (s or "").lower()).strip("_")[:40]


def guardar_procedimiento(nombre: str, descripcion: str = "", pasos: list = None,
                          intencion: str = "", origen: str = "manual") -> str:
    """Guarda explícitamente un procedimiento (receta de pasos/herramientas)."""
    name = _norm(nombre) or f"proc_{int(time.time())}"
    if not pasos:
        return f"Faltan los pasos del procedimiento. Pasos: lista de {intencion or 'acciones'}."
    state = _load()
    procs = state.setdefault("procedimientos", {})
    procs[name] = {
        "nombre": name,
        "descripcion": descripcion or f"Procedimiento para {intencion or nombre}",
        "pasos": pasos,
        "intencion": intencion or "",
        "origen": origen,
        "veces_usado": procs.get(name, {}).get("veces_usado", 0),
        "creado": procs.get(name, {}).get("creado", time.strftime("%Y-%m-%dT%H:%M:%S")),
        "actualizado": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    _save(state)
    return f"Procedimiento '{name}' guardado con {len(pasos)} pasos."


def listar_procedimientos() -> list:
    state = _load()
    procs = state.get("procedimientos", {})
    return [
        {"nombre": p.get("nombre"), "descripcion": p.get("descripcion", ""),
         "pasos": len(p.get("pasos", [])), "veces_usado": p.get("veces_usado", 0),
         "origen": p.get("origen", "manual"), "intencion": p.get("intencion", "")}
        for p in sorted(procs.values(), key=lambda x: x.get("veces_usado", 0), reverse=True)
    ]


def obtener_procedimiento(nombre: str) -> dict:
    state = _load()
    return state.get("procedimientos", {}).get(_norm(nombre)) or {}


def borrar_procedimiento(nombre: str) -> str:
    state = _load()
    procs = state.get("procedimientos", {})
    name = _norm(nombre)
    if name in procs:
        del procs[name]
        _save(state)
        return f"Procedimiento '{name}' eliminado."
    return f"No encontré el procedimiento '{nombre}'."


def buscar_por_intencion(intencion: str) -> list:
    """Encuentra procedimientos cuya intención o nombre coincida con lo pedido."""
    if not intencion:
        return []
    q = _norm(intencion)
    if not q:
        return []
    words = set(q.split("_"))
    hits = []
    for p in listar_procedimientos():
        score = 0
        for w in words:
            if len(w) < 3:
                continue
            if w in _norm(p.get("nombre", "")):
                score += 2
            if w in _norm(p.get("intencion", "")):
                score += 3
            if w in _norm(p.get("descripcion", "")):
                score += 1
        if score:
            hits.append((score, p))
    hits.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in hits[:5]]


def registrar_paso(tool_name: str, intencion: str = "") -> str:
    """Registra una tool usada dentro de la intención actual (aprendizaje continuo)."""
    global _current_intent, _current_tools
    inten = intencion or _current_intent
    if inten != _current_intent:
        _flush()
        _current_intent = inten
        _current_tools = []
        _last_flush = time.time()
    if tool_name not in _current_tools:
        _current_tools.append(tool_name)
    return f"paso {tool_name} registrado para '{inten[:50]}'"


def _flush():
    """Consolida la secuencia del turno: la guarda como procedimiento en borrador."""
    global _current_intent, _current_tools
    tools = list(_current_tools)
    inten = _current_intent
    _current_tools = []
    _current_intent = ""
    if len(tools) >= 2 and inten:
        state = _load()
        procs = state.setdefault("procedimientos", {})
        key = _norm(f"flujo_{inten}")
        name = key or f"flujo_{int(time.time())}"
        existing = procs.get(name, {})
        pasos = existing.get("pasos", [])
        # merge conservando orden: agrega tools nuevas al final
        for t in tools:
            paso = {"tool": t}
            if not any(p.get("tool") == t for p in pasos):
                pasos.append(paso)
        procs[name] = {
            "nombre": name,
            "descripcion": f"Flujo aprendido al resolver: {inten[:80]}",
            "pasos": pasos,
            "intencion": inten[:120],
            "origen": "auto",
            "veces_usado": existing.get("veces_usado", 0),
            "creado": existing.get("creado", time.strftime("%Y-%m-%dT%H:%M:%S")),
            "actualizado": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        _save(state)


def atribuir_exito_procedimiento(nombre: str):
    """Suma un uso positivo a un procedimiento."""
    state = _load()
    procs = state.get("procedimientos", {})
    name = _norm(nombre)
    if name in procs:
        procs[name]["veces_usado"] = procs[name].get("veces_usado", 0) + 1
        procs[name]["actualizado"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        _save(state)


def procedimientos(parameters=None, player=None) -> str:
    """Tool de aprendizaje procedural: guardar/listar/obtener/usar/borrar."""
    import json as _json
    try:
        params = _json.loads(parameters) if isinstance(parameters, str) else (parameters or {})
    except Exception:
        params = {}
    action = (params.get("action") or "listar").lower()
    p = ac = l = a = None  # noqa
    if action in ("guardar", "aprender", "crear"):
        pasos = params.get("pasos") or params.get("steps") or []
        if isinstance(pasos, str):
            try:
                pasos = _json.loads(pasos)
            except Exception:
                pasos = [{"tool": s.strip()} for s in pasos.split(",") if s.strip()]
        return guardar_procedimiento(params.get("nombre", ""), params.get("descripcion", ""),
                                     pasos, params.get("intencion", ""))
    if action in ("listar", "list"):
        ls = listar_procedimientos()
        if not ls:
            return {"mensaje": "Todavía no tengo procedimientos guardados.", "procedimientos": []}
        return {"procedimientos": ls}
    if action in ("buscar", "recordar", "olvidar" if False else "sugerir"):
        return {"sugerencias": buscar_por_intencion(params.get("intencion", params.get("texto", "")))}
    if action in ("obtener", "detalle", "get"):
        return obtener_procedimiento(params.get("nombre", ""))
    if action in ("usar", "aplicar"):
        name = _norm(params.get("nombre", ""))
        proc = obtener_procedimiento(name)
        if not proc:
            return {"error": f"No encontré el procedimiento '{params.get('nombre')}'."}
        atribuir_exito_procedimiento(name)
        return {"procedimiento": proc, "instrucciones": "Resolvé siguiendo los pasos indicados."}
    if action in ("borrar", "delete", "eliminar"):
        return {"status": "eliminado", "mensaje": borrar_procedimiento(params.get("nombre", ""))}
    return {"error": f"Acción desconocida: {action}. Acciones: guardar, listar, buscar, obtener, usar, borrar."}