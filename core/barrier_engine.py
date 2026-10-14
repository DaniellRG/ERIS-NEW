"""
barrier_engine.py — Motor de superación de barreras de ERIS (Proyecto 1).

ERIS detecta que NO está llegando a una meta, diagnostica qué le falta,
investiga/reúne material, decide pensando el riesgo, se construye la capacidad,
la usa y **verifica con evidencia** antes de dar algo por hecho. Toda barrera
deja una receta reutilizable (recetario) para resolver al instante lo parecido.

Este archivo es la **Fase 1 (andamiaje y detección)**: la máquina de estados, la
detección de señales y la tool. Todavía **no crea ni usa** capacidades.

Diseño: docs/superpowers/specs/2026-10-14-eris-superacion-de-barreras-design.md
Estado: data/barreras.json (runtime; data/*.json ya está en .gitignore)
"""
from __future__ import annotations

import json
import time
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_STATE_FILE = _BASE / "data" / "barreras.json"

# Estados del ciclo (diseño §5). "reintento" es una transición, no un estado.
_ESTADOS = {
    "abierta", "diagnosticada", "investigando", "planificada", "esperando_ok",
    "creada", "usada", "verificada", "resuelta", "escalada", "abandonada",
    "falso_positivo",
}
# Estados "vivos": una barrera acá sigue en juego.
_EN_CURSO = {"abierta", "diagnosticada", "investigando", "planificada",
             "esperando_ok", "creada", "usada", "verificada"}


# ─────────────────────────── estado ──────────────────────────────────────────

def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _load() -> dict:
    try:
        if _STATE_FILE.exists():
            data = json.loads(_STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("barreras"), list):
                return data
    except Exception:
        pass
    return {"barreras": [], "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "updated_at": ""}


def _save(state: dict) -> None:
    try:
        _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        state["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        _STATE_FILE.write_text(
            json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception:
        # Nunca crashear por no poder escribir el estado.
        pass


def _nueva_id() -> str:
    return "bar_%d" % int(time.time() * 1000)


def _find(state: dict, barrier_id: str) -> dict | None:
    for b in state.get("barreras", []):
        if b.get("id") == barrier_id:
            return b
    return None


def _es_activa(b: dict) -> bool:
    return b.get("estado") not in ("resuelta", "abandonada", "escalada")


def _mismo(b: dict, goal_ref: dict | None, titulo: str) -> bool:
    """¿Esta barrera abierta ya representa la misma barrera que se quiere abrir?"""
    gr = goal_ref or {}
    if gr.get("id"):
        return (b.get("goal_ref") or {}).get("id") == gr.get("id")
    return (b.get("titulo") or "").strip().lower() == (titulo or "").strip().lower()


def _log(b: dict, evento: str, detalle: str = "") -> None:
    b.setdefault("historial", []).append(
        {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "evento": evento, "detalle": detalle}
    )
    b["historial"] = b["historial"][-100:]
    b["actualizada"] = time.strftime("%Y-%m-%dT%H:%M:%S")


# ── API principal ──────────────────────────────────────────────────────────

def abrir(goal_ref: dict = None, titulo: str = "", descripcion: str = "",
          origen: str = "manual", senales: list = None) -> dict:
    """Abre (o reutiliza) una barrera. Devuelve {ok, barrera, reutilizada}."""
    titulo = (titulo or "").strip()
    if not titulo:
        return {"ok": False, "error": "Falta el título de la barrera."}

    state = _load()
    for b in state["barreras"]:
        if b.get("estado") not in ("resuelta", "abandonada", "escalada") \
                and _mismo(b, goal_ref, titulo):
            # Ya hay una barrera abierta para esto: la reutilizamos.
            if senales:
                b.setdefault("senales", [])
                for s in senales:
                    if s not in b["senales"]:
                        b["senales"].append(s)
            _log(b, "reutilizada", origen)
            _save(state)
            return {"ok": True, "barrera": b, "reutilizada": True}

    ahora = time.strftime("%Y-%m-%dT%H:%M:%S")
    b = {
        "id": "bar_%d" % int(time.time() * 1000),
        "goal_ref": goal_ref or {},
        "titulo": titulo,
        "descripcion": descripcion or "",
        "origen": origen or "manual",
        "estado": "abierta",
        "senales": list(senales or []),
        "diagnostico": None,
        "paquete": None,
        "plan": None,
        "capacidad": None,
        "evidencia": [],
        "intentos": [],
        "creada": ahora,
        "actualizada": ahora,
        "historial": [{"ts": ahora, "evento": "abierta", "detalle": origen or "manual"}],
    }
    state["barreras"].append(b)
    _save(state)
    return {"ok": True, "barrera": b, "reutilizada": False}


def scan(dias: int = 3) -> list[dict]:
    """Recolecta señales REALES (no inventa) y crea/actualiza barreras `abierta`.

    Fase 1 cubre dos fuentes con estado legible:
      - metas estancadas (`goal_tracker.get_stalled_goals`);
      - tareas de la tripulación en ERROR (`memory/sub_agent_state.json`).
    Las demás señales del diseño (mission/verdad/tool faltante) se enganchan en
    fases siguientes. `scan()` NO actúa: solo declara la barrera.
    """
    state = _load()
    resultados: list[dict] = []
    creadas = 0
    reutilizadas = 0
    for senal in _recolectar_senales(dias):
        r = _aplicar_senal(state, senal)
        if r.get("reutilizada"):
            reutilizadas += 1
        else:
            creadas += 1
        resultados.append({
            "tipo": senal.get("tipo"),
            "barrera_id": r["barrera"]["id"],
            "reutilizada": bool(r.get("reutilizada")),
        })
    _save(state)
    return resultados


def _recolectar_senales(dias: int = 3) -> list[dict]:
    senales: list[dict] = []
    senales += _senales_metas(dias)
    senales += _senales_tripulacion()
    return senales


def _senales_metas(dias: int = 3) -> list[dict]:
    out: list[dict] = []
    try:
        from core.goal_tracker import get_stalled_goals
        for g in get_stalled_goals(days=dias):
            gid = g.get("id")
            out.append({
                "tipo": "meta_estancada",
                "goal_ref": {"store": "goal_tracker", "id": gid},
                "titulo": f"Meta estancada: {g.get('title') or gid}",
                "descripcion": (
                    f"La meta '{g.get('title')}' (state={g.get('state')}) no se "
                    f"actualizó en {dias}+ días."
                ),
                "evidencia": {"updated_at": g.get("updated_at"), "state": g.get("state")},
            })
    except Exception:
        pass
    return out


def _senales_tripulacion() -> list[dict]:
    out: list[dict] = []
    path = _BASE / "memory" / "sub_agent_state.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        for t in data.get("tasks", []):
            if t.get("status") != "error":
                continue
            tid = t.get("id") or t.get("agent_key")
            out.append({
                "tipo": "tripulacion_error",
                "goal_ref": {},
                "titulo": f"Tarea falló: {t.get('agent_key') or tid}",
                "descripcion": (
                    f"La tarea '{tid}' ({t.get('agent_key')}) terminó en ERROR: "
                    f"{str(t.get('error'))[:200]}"
                ),
                "evidencia": {"task_id": tid, "error": t.get("error")},
            })
    except Exception:
        pass
    return out


def _aplicar_senal(state: dict, senal: dict) -> dict:
    """Crea o reutiliza la barrera para una señal, usando el mismo estado cargado."""
    titulo = (senal.get("titulo") or "").strip()
    for b in state["barreras"]:
        if b.get("estado") in ("resuelta", "abandonada", "escalada"):
            continue
        if _mismo(b, senal.get("goal_ref"), titulo):
            if senal.get("tipo") not in {s.get("tipo") for s in b.get("senales", [])}:
                b.setdefault("senales", []).append(
                    {"tipo": senal.get("tipo"), "evidencia": senal.get("evidencia")}
                )
            _log(b, "senal_repetida", senal.get("tipo", ""))
            return {"barrera": b, "reutilizada": True}

    ahora = time.strftime("%Y-%m-%dT%H:%M:%S")
    b = {
        "id": "bar_%d" % int(time.time() * 1000),
        "goal_ref": senal.get("goal_ref") or {},
        "titulo": titulo,
        "descripcion": senal.get("descripcion") or "",
        "origen": "scan",
        "estado": "abierta",
        "senales": [{"tipo": senal.get("tipo"), "evidencia": senal.get("evidencia")}],
        "diagnostico": None, "paquete": None, "plan": None, "capacidad": None,
        "evidencia": [], "intentos": [],
        "creada": ahora, "actualizada": ahora,
        "historial": [{"ts": ahora, "evento": "abierta", "detalle": f"scan:{senal.get('tipo')}"}],
    }
    state["barreras"].append(b)
    return {"barrera": b, "reutilizada": False}


def listar(estado: str = None, limite: int = 50) -> list[dict]:
    state = _load()
    bs = state["barreras"]
    if estado:
        bs = [b for b in bs if b.get("estado") == estado]
    bs = sorted(bs, key=lambda b: b.get("actualizada", ""), reverse=True)
    return bs[:limite] if limite else bs


def estado() -> dict:
    state = _load()
    bs = state["barreras"]
    por_estado: dict[str, int] = {}
    for b in bs:
        e = b.get("estado", "?")
        por_estado[e] = por_estado.get(e, 0) + 1
    return {
        "total": len(bs),
        "por_estado": por_estado,
        "abiertas": sum(1 for b in bs if b.get("estado") not in
                        ("resuelta", "abandonada", "escalada")),
        "actualizado": state.get("updated_at", ""),
    }


def _buscar(barrier_id: str) -> dict | None:
    state = _load()
    for b in state["barreras"]:
        if b.get("id") == barrier_id:
            return b
    return None


def aprobar(barrier_id: str) -> dict:
    """Aprueba una barrera en `esperando_ok` para que retome (diseño §5.3)."""
    state = _load()
    for b in state["barreras"]:
        if b.get("id") != barrier_id:
            continue
        if b.get("estado") != "esperando_ok":
            return {"ok": False, "error": f"La barrera {barrier_id} no está esperando OK "
                                          f"(estado={b.get('estado')})."}
        b["estado"] = "planificada"
        b["aprobada"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        _log(b, "aprobada", "OK del dueño")
        _save(state)
        return {"ok": True, "barrera": b}
    return {"ok": False, "error": f"No existe la barrera {barrier_id}."}


def rechazar(barrier_id: str, motivo: str = "") -> dict:
    """Rechaza una barrera en `esperando_ok`: vuelve al diagnóstico con otro enfoque."""
    state = _load()
    for b in state["barreras"]:
        if b.get("id") != barrier_id:
            continue
        if b.get("estado") != "esperando_ok":
            return {"ok": False, "error": f"La barrera {barrier_id} no está esperando OK "
                                          f"(estado={b.get('estado')})."}
        b.setdefault("intentos", []).append(
            {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "resultado": "rechazada", "motivo": motivo}
        )
        b["estado"] = "diagnosticada"
        _log(b, "rechazada", motivo)
        _save(state)
        return {"ok": True, "barrera": b}
    return {"ok": False, "error": f"No existe la barrera {barrier_id}."}


# ── Tool `barreras` ───────────────────────────────────────────────────────────

def _fmt_barrera(b: dict) -> str:
    gr = b.get("goal_ref") or {}
    ref = f" [{gr.get('store')}:{gr.get('id')}]" if gr.get("id") else ""
    lineas = [
        f"· {b.get('id')} [{b.get('estado')}] {b.get('titulo')}{ref}",
    ]
    if b.get("descripcion"):
        lineas.append(f"   {b['descripcion']}")
    return "\n".join(lineas)


def barrier_tool(parameters: dict = None, player=None) -> str:
    """Tool `barreras`: abre, escanea, lista, consulta y aprueba/rechaza barreras."""
    params = parameters or {}
    action = str(params.get("action") or "estado").strip().lower()

    if action in ("abrir", "nueva"):
        r = abrir(
            goal_ref=params.get("goal_ref") or {
                "store": params.get("store") or "manual",
                "id": params.get("goal_id") or "",
            },
            titulo=params.get("titulo") or params.get("name") or "",
            descripcion=params.get("descripcion") or params.get("description") or "",
            origen=params.get("origen") or "llm",
        )
        if not r.get("ok"):
            return f"⚠️ No pude abrir la barrera: {r.get('error')}"
        b = r["barrera"]
        cual = "ya existía" if r.get("reutilizada") else "queda abierta"
        return f"🪨 Barrera {b['id']} {cual} [{b['estado']}]: {b['titulo']}"

    if action in ("scan", "escanear", "detectar"):
        try:
            dias = int(params.get("dias") or 3)
        except Exception:
            dias = 3
        state = _load()
        antes = len(state["barreras"])
        senales = _recolectar_senales(dias)
        for s in senales:
            _aplicar_senal(state, s)
        _save(state)
        despues = len(state["barreras"])
        return (f"🔎 Escaneo: {len(senales)} señales reales; "
                f"{despues - antes} barreras nuevas, {antes} previas → {despues} totales.")

    if action in ("listar", "lista"):
        bs = listar(estado=params.get("estado"), limite=int(params.get("limite") or 50))
        if not bs:
            return "No hay barreras registradas."
        return "🪨 Barreras:\n" + "\n".join(_fmt_barrera(b) for b in bs)

    if action in ("aprobar", "ok"):
        r = aprobar(params.get("id") or params.get("barrera_id") or "")
        return (f"✅ Barrera {r['barrera']['id']} aprobada → {r['barrera']['estado']}."
                if r.get("ok") else f"⚠️ {r.get('error')}")

    if action in ("rechazar", "no"):
        r = rechazar(params.get("id") or params.get("barrera_id") or "",
                     params.get("motivo") or "")
        return (f"🚫 Barrera {r['barrera']['id']} rechazada → {r['barrera']['estado']}."
                if r.get("ok") else f"⚠️ {r.get('error')}")

    # default: estado
    e = estado()
    if e["total"] == 0:
        return "No hay barreras registradas todavía."
    detalle = ", ".join(f"{k}={v}" for k, v in sorted(e["por_estado"].items()))
    return f"🪨 Barreras: {e['total']} en total ({e['abiertas']} abiertas). {detalle}"


# Alias para el registro de tools
barreras = barrier_tool
