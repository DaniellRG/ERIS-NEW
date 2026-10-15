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
import uuid
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
    return "bar_" + uuid.uuid4().hex[:12]


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
        "id": _nueva_id(),
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
        "id": _nueva_id(),
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


# ── F3: diagnóstico + acopio + deliberación ─────────────────────────────────

def _texto_barrera(b: dict) -> str:
    partes = [str(b.get("titulo") or ""), str(b.get("descripcion") or "")]
    for s in b.get("senales", []):
        if isinstance(s, dict) and s.get("evidencia"):
            partes.append(str(s["evidencia"]))
    return "\n".join(p for p in partes if p)


def _clasificar(texto: str) -> tuple[str, str, str]:
    """Heurística: tipo dominante de barrera (§5.2). → (tipo, falta, ruta)."""
    t = (texto or "").lower()
    if any(k in t for k in ("modulenotfounderror", "importerror", "no module named",
                            "command not found", "not installed", "pip install",
                            "no such file", "not found")):
        return "dependencia", "un paquete/módulo", "autonomy.auto_install_package"
    if any(k in t for k in ("permission denied", "permiso denegado", "sudo", "credencial",
                            "password", "contraseña", "401", "403", "unauthorized")):
        return "acceso", "credencial o permiso del SO", "zona protegida → pide OK"
    if any(k in t for k in ("no sé", "no se como", "cómo se hace", "como se hace",
                            "how to", "tutorial", "aprender", "documentación")):
        return "conocimiento", "saber cómo", "learning_engine / investigar"
    if any(k in t for k in ("hardware", "ram", "disco", "disk", "sin espacio",
                            "memoria insuficiente", "sin tiempo", "dinero")):
        return "recurso", "datos / hardware / tiempo", "informar/esperar o buscar alternativa"
    return "capacidad", "una función / tool / servicio", "fabrica.crear_tool|crear_libreria|crear_skill"


_RUTA_POR_TIPO = {
    "conocimiento": ("saber cómo", "learning_engine / investigar"),
    "capacidad": ("una función / tool / servicio", "fabrica.crear_*"),
    "dependencia": ("un paquete/módulo", "autonomy.auto_install_package"),
    "acceso": ("credencial o permiso del SO", "zona protegida → pide OK"),
    "recurso": ("datos / hardware / tiempo", "informar/esperar"),
}


def _clasificar_llm(texto: str) -> tuple[str, str, str] | None:
    """Refina con el LLM (best-effort; si no hay proveedor, devuelve None)."""
    try:
        from core.model_router import quick_chat
        out = quick_chat(
            "Clasificá esta barrera en UN tipo de la lista y respondé solo con la palabra.\n"
            "Tipos: conocimiento, capacidad, dependencia, acceso, recurso\n"
            f"Barrera: {texto[:800]}\nTipo:"
        ).strip().lower()
        for tipo in ("conocimiento", "dependencia", "acceso", "recurso", "capacidad"):
            if tipo in out:
                falta, ruta = _RUTA_POR_TIPO[tipo]
                return tipo, falta, ruta
    except Exception:
        pass
    return None


def diagnosticar(barrier_id: str, usar_llm: bool = False) -> dict:
    """Clasifica la barrera en un tipo dominante y lo guarda (§5.2)."""
    state = _load()
    b = _find(state, barrier_id)
    if not b:
        return {"ok": False, "error": f"No existe la barrera {barrier_id}."}
    texto = _texto_barrera(b)
    tipo, falta, ruta = _clasificar(texto)
    metodo = "heuristica"
    if usar_llm:
        llm = _clasificar_llm(texto)
        if llm:
            tipo, falta, ruta = llm
            metodo = "llm"
    b["diagnostico"] = {"tipo": tipo, "falta": falta, "ruta": ruta,
                        "metodo": metodo, "texto": texto[:600], "ts": _now()}
    b["estado"] = "diagnosticada"
    _log(b, "diagnosticada", f"{tipo} ({metodo})")
    _save(state)
    return {"ok": True, "barrera_id": barrier_id, "diagnostico": b["diagnostico"]}


def investigar(barrier_id: str, limite: int = 5) -> dict:
    """Acopio (§5.2b): recetario local primero; si no hay, investiga afuera."""
    state = _load()
    b = _find(state, barrier_id)
    if not b:
        return {"ok": False, "error": f"No existe la barrera {barrier_id}."}
    diag = b.get("diagnostico") or {}
    query = " ".join(x for x in (b.get("titulo"), diag.get("tipo"), diag.get("falta")) if x)

    paquete = {"query": query, "recetas": [], "fuentes": [], "canales": [], "ts": _now()}
    try:
        from core.recetario import buscar as rec_buscar
        paquete["recetas"] = rec_buscar(query, limite)
    except Exception as e:
        paquete["error_recetario"] = str(e)[:200]
    if paquete["recetas"]:
        paquete["canales"].append("recetario")
        paquete["reutilizable"] = True
    else:
        try:
            from core.research_channels import investigar as rc_investigar
            ext = rc_investigar(query, limite)
            papers, repos, web = ext.get("papers", []), ext.get("repos", []), ext.get("web", [])
            paquete["fuentes"] = papers + repos + web
            paquete["por_canal"] = {"papers": len(papers), "repos": len(repos), "web": len(web)}
            if paquete["fuentes"]:
                paquete["canales"].append("web/ddgs")
        except Exception as e:
            paquete["error_externo"] = str(e)[:200]

    b["paquete"] = paquete
    if b.get("estado") in ("abierta", "diagnosticada"):
        b["estado"] = "investigando"
    _log(b, "acopio", ", ".join(paquete["canales"]) or "sin fuentes")
    _save(state)
    return {"ok": True, "barrera_id": barrier_id, "paquete": paquete}


def _pasos_de_receta(receta: dict) -> list[str]:
    pasos = receta.get("pasos")
    if isinstance(pasos, list) and pasos:
        return [str(p) for p in pasos][:6]
    sol = receta.get("solucion") or receta.get("problema") or ""
    return [str(sol)] if sol else []


def _opciones_plan(paquete: dict, diag: dict) -> list[dict]:
    opciones: list[dict] = []
    recetas = paquete.get("recetas") or []
    fuentes = paquete.get("fuentes") or []
    tipo = diag.get("tipo", "capacidad")

    if recetas:
        opciones.append({
            "id": "A", "enfoque": "reutilizar receta",
            "detalle": f"Ya vivió algo parecido ({len(recetas)} receta/s): aplicarla directo.",
            "pasos": _pasos_de_receta(recetas[0]),
            "impacto": 3, "esfuerzo": 1, "riesgo": "bajo",
        })
    if tipo == "dependencia":
        opciones.append({
            "id": "B", "enfoque": "instalar dependencia",
            "detalle": "autonomy.auto_install_package dentro del venv (fuera de él, pide OK).",
            "pasos": ["identificar el paquete/módulo que falta", "instalarlo en el venv",
                      "reintentar la acción"],
            "impacto": 3, "esfuerzo": 1, "riesgo": "medio",
        })
    elif tipo == "conocimiento":
        opciones.append({
            "id": "B", "enfoque": "estudiar / investigar",
            "detalle": "learning_engine (investigar→estudiar→cristalizar) sobre las fuentes.",
            "pasos": ["investigar las fuentes", "estudiar", "cristalizar skill", "usarla"],
            "impacto": 2, "esfuerzo": 2, "riesgo": "bajo",
        })
    elif tipo == "acceso":
        opciones.append({
            "id": "B", "enfoque": "pedir credencial/permiso",
            "detalle": "Es zona protegida: se corta en `esperando_ok` y se le pide OK al dueño.",
            "pasos": ["explicar qué permiso falta", "esperar OK del dueño", "reanudar"],
            "impacto": 2, "esfuerzo": 1, "riesgo": "alto",
        })
    else:
        opciones.append({
            "id": "B", "enfoque": "crear la capacidad",
            "detalle": "fabrica (tool/librería/skill) y probarla ANTES de usarla.",
            "pasos": ["ver si ya existe (fabrica listar)", "crear la que falte", "probarla"],
            "impacto": 3, "esfuerzo": 3, "riesgo": "medio",
        })
    if fuentes:
        opciones.append({
            "id": "C", "enfoque": "incorporar de fuente externa",
            "detalle": f"{len(fuentes)} fuente/s hallada/s (revisar licencia; probar aislado).",
            "pasos": ["elegir la mejor fuente", "probar en code_sandbox (lógica) / venv (red)",
                      "empaquetar como tool/librería", "usarla"],
            "impacto": 2, "esfuerzo": 3, "riesgo": "alto",
        })
    return opciones


_RIESGO_PENALIZACION = {"bajo": 0, "medio": 1, "alto": 3}


def _score_plan(o: dict) -> int:
    return o.get("impacto", 0) * 2 - o.get("esfuerzo", 0) \
        - _RIESGO_PENALIZACION.get(o.get("riesgo", "medio"), 1)


def _elegir_plan(opciones: list[dict], usar_llm: bool = False) -> tuple[dict, str]:
    """Elige el mejor plan por impacto/esfuerzo/riesgo (LLM best-effort)."""
    if not opciones:
        return {}, "sin opciones"
    if usar_llm:
        try:
            from core.model_router import quick_chat
            detalle = "\n".join(
                f"{o['id']}) {o['enfoque']}: {o.get('detalle', '')} "
                f"(impacto {o.get('impacto')}, esfuerzo {o.get('esfuerzo')}, riesgo {o.get('riesgo')})"
                for o in opciones)
            out = quick_chat(
                "Elegí el mejor plan por impacto/esfuerzo/riesgo. Respondé solo con el id.\n"
                f"{detalle}\nOpción:").strip().upper()
            for o in opciones:
                if o["id"] in out[:6]:
                    return o, "elegido por LLM"
        except Exception:
            pass
    return max(opciones, key=_score_plan), "elegido por heurística (impacto − esfuerzo − riesgo)"


def planificar(barrier_id: str, usar_llm: bool = False) -> dict:
    """Delibera (§5.2b.4 / §5.3): formula 2–3 planes y elige el mejor."""
    state = _load()
    b = _find(state, barrier_id)
    if not b:
        return {"ok": False, "error": f"No existe la barrera {barrier_id}."}
    opciones = _opciones_plan(b.get("paquete") or {}, b.get("diagnostico") or {})
    # Rechazo = "otro enfoque" (§5.3): no volver a proponer lo ya rechazado.
    vetados = {r.get("enfoque") for r in b.get("rechazados", []) if r.get("enfoque")}
    if vetados:
        filtradas = [o for o in opciones if o.get("enfoque") not in vetados]
        if filtradas:
            opciones = filtradas
    elegido, motivo = _elegir_plan(opciones, usar_llm)
    plan = {"opciones": opciones, "elegido": (elegido or {}).get("id"),
            "enfoque": (elegido or {}).get("enfoque", ""), "motivo": motivo,
            "pasos": (elegido or {}).get("pasos", []),
            "riesgo_nominal": (elegido or {}).get("riesgo", ""),
            "metodo": "llm" if "LLM" in motivo else "heuristica", "ts": _now()}
    b["plan"] = plan
    b["estado"] = "planificada"
    _log(b, "planificada", f"{plan.get('elegido')}: {plan.get('enfoque')}")
    _save(state)
    return {"ok": True, "barrera_id": barrier_id, "plan": plan}


def _buscar(barrier_id: str) -> dict | None:
    state = _load()
    for b in state["barreras"]:
        if b.get("id") == barrier_id:
            return b
    return None


# ── F4: zonas y decisión (§5.3, §6) ─────────────────────────────────────────

# Acciones que el motor puede hacer SOLA aunque el riesgo nominal sea medio:
# todo dentro de su propio proyecto / entorno aislado (§5.3 allowlist).
_ALLOWLIST_MEDIA = (
    "libraries/", "actions/custom/", "skills/user_created/", "data/",
    "eris-new", ".venv-linux", "venv", "code_sandbox", "pip install",
    "pip uninstall", "reutilizar receta", "estudiar", "investigar",
)


def _zona_de_paso(paso: str) -> dict:
    """Evalúa un paso del plan con LA MISMA política que usa el árbitro (§6)."""
    try:
        from core.zone_policy import evaluar_zona
        return evaluar_zona(paso)
    except Exception:
        return {"zona": "desconocida", "motivo": "", "regla": "", "match": ""}


def _paso_en_allowlist(paso: str) -> bool:
    p = (paso or "").lower()
    return any(a in p for a in _ALLOWLIST_MEDIA)


# Enfoques del plan que caen enteros en el margen propio del motor (§5.3):
# reutilizar/estudiar/crear capacidad/instalar en el venv. Los otros (incorporar
# de fuente externa, pedir credencial) son riesgo alto → cortan solos.
_ENFOQUES_PROPIOS = {
    "reutilizar receta", "estudiar / investigar", "crear la capacidad",
    "instalar dependencia",
}


def decidir(barrier_id: str) -> dict:
    """Decide si el plan elegido puede seguir sola o corta en `esperando_ok`.

    Pre-chequeo del motor (§5.3/§6): corre el MISMO módulo de zonas que el
    árbitro (`core/zone_policy.py`) sobre cada paso del plan elegido, más el
    riesgo nominal. Si algo cae en zona protegida o el riesgo es alto/crítico —
    o medio fuera del margen propio — deja la barrera en `esperando_ok`, con el
    paso pendiente guardado para reanudar sin reiniciar (`aprobar`/`rechazar`).
    """
    state = _load()
    b = _find(state, barrier_id)
    if not b:
        return {"ok": False, "error": f"No existe la barrera {barrier_id}."}
    plan = b.get("plan") or {}
    opciones = plan.get("opciones") or []
    elegido = next((o for o in opciones if o.get("id") == plan.get("elegido")), None)
    if not elegido:
        return {"ok": False, "error": "Primero `planificar`: todavía no hay plan elegido."}

    pasos = [str(p) for p in (elegido.get("pasos") or [])]
    riesgo = str(elegido.get("riesgo") or plan.get("riesgo_nominal") or "medio").lower()
    enfoque = str(elegido.get("enfoque") or plan.get("enfoque") or "").strip().lower()

    protegidos = []
    for p in pasos:
        z = _zona_de_paso(p)
        if z.get("zona") == "protegida":
            protegidos.append({"paso": p, "motivo": z.get("motivo"), "match": z.get("match")})

    en_allowlist = (enfoque in _ENFOQUES_PROPIOS
                    or (bool(pasos) and all(_paso_en_allowlist(p) for p in pasos)))
    motivo_corte = ""
    if protegidos:
        motivo_corte = (f"toca zona protegida ({protegidos[0]['motivo']}: "
                        f"'{protegidos[0]['match']}')")
    elif riesgo in ("alto", "crítico", "critico", "critical", "high"):
        motivo_corte = f"riesgo {riesgo} según el plan"
    elif riesgo == "medio" and not en_allowlist:
        motivo_corte = ("riesgo medio fuera del margen propio (no todo el plan cae en "
                        "su workspace/venv/sandbox)")

    decision = {
        "pasos": pasos,
        "enfoque": enfoque,
        "riesgo_nominal": riesgo,
        "protegidos": protegidos,
        "en_allowlist": en_allowlist,
        "corte": motivo_corte or None,
        "resultado": "esperando_ok" if motivo_corte else "procede",
        "ts": _now(),
    }
    if motivo_corte:
        b["estado"] = "esperando_ok"
        b["paso_pendiente"] = {"pasos": pasos, "riesgo": riesgo, "motivo": motivo_corte}
    else:
        b["estado"] = "planificada"
        b.pop("paso_pendiente", None)
    b["decision"] = decision
    _log(b, "decidida", decision["resultado"] + (f" — {motivo_corte}" if motivo_corte else ""))
    _save(state)
    return {"ok": True, "barrera_id": barrier_id, "decision": decision, "estado": b["estado"]}


def evaluar_zona_texto(texto: str) -> dict:
    """Consulta aislada de la política de zonas (para la tool `barreras action=zona`)."""
    try:
        from core.zone_policy import evaluar_zona
        return evaluar_zona(texto)
    except Exception as e:
        return {"zona": "desconocida", "error": str(e)[:200]}


# ── F5: creación y uso (§5.4/§5.5) ──────────────────────────────────────────

def _inventario(nombre: str) -> dict | None:
    """Busca una capacidad por nombre en el inventario real (fabrica + servers)."""
    if not nombre:
        return None
    try:
        from core import eris_fabrica as fab
        det = fab.detalle(nombre)
        if isinstance(det, dict) and det.get("name"):
            return {"origen": "fabrica", "item": det}
        for it in fab.listar().get("creadas", []):
            if it.get("name") == nombre:
                return {"origen": "fabrica", "item": it}
    except Exception:
        pass
    try:
        from core import server_forge as sf
        for s in sf.buscar(nombre):
            if s.get("name") == nombre:
                return {"origen": "server_forge", "item": s}
    except Exception:
        pass
    return None


def _cap(capacidad: str, tipo: str, path: str, como: str, prueba: str,
         creada: bool = True) -> dict:
    return {"ok": True, "capacidad": capacidad, "tipo": tipo, "path": path,
            "como_se_creo": como,
            "creada_vs_reutilizada": "creada" if creada else "reutilizada",
            "prueba": prueba}


def _crear_libreria(spec: dict) -> dict:
    from core import eris_fabrica as fab
    nombre = spec.get("name") or spec.get("nombre") or ""
    res = fab.crear_libreria(nombre,
                             purpose=spec.get("purpose") or spec.get("description") or "",
                             functions=spec.get("functions") or spec.get("funciones") or [])
    if not isinstance(res, dict) or res.get("error"):
        return {"ok": False, "error": str((res or {}).get("error", "la fábrica no devolvió resultado"))}
    lib = res["name"]
    fns = res.get("functions") or []
    # La Fábrica SOLO compila; el motor la PRUEBA ejecutando (diseño §5.4).
    pruebas = []
    for fn in fns[:4]:
        params = (spec.get("prueba_params") or {}).get(fn, {})
        if not isinstance(params, dict):
            params = {}
        try:
            out = fab.usar_libreria(lib, fn, params)
            if isinstance(out, dict) and out.get("error"):
                pruebas.append(f"{fn}=error({str(out['error'])[:60]})")
            else:
                pruebas.append(f"{fn}=ok")
        except Exception as e:
            pruebas.append(f"{fn}=exc({type(e).__name__})")
    if not any(p.endswith("=ok") for p in pruebas):
        # Distinguir "falta dato de prueba" de "la función está rota".
        if pruebas and all("argument" in p or "missing" in p for p in pruebas):
            return {"ok": False, "error": ("Hacen falta `prueba_params` para probar la librería "
                                           f"(argumentos requeridos): {pruebas}")}
        return {"ok": False, "error": f"La librería {nombre} no pasó la prueba de sus funciones: {pruebas}"}
    return _cap(lib, "libreria", str(fab._LIB_BASE / (lib + ".py")),
                "fabrica.crear_libreria", "funciones probadas: " + ", ".join(pruebas))


def _crear_tool(spec: dict) -> dict:
    from core import eris_fabrica as fab
    r = fab.crear_tool(spec.get("name") or spec.get("nombre") or "",
                       spec.get("description") or spec.get("descripcion") or "",
                       funciones=spec.get("funciones") or spec.get("functions") or [])
    if r.get("error"):
        return {"ok": False, "error": r["error"]}
    return _cap(r.get("name"), "tool", r.get("file") or "", "fabrica.crear_tool",
                "smoke: " + str(r.get("prueba_smoke", ""))[:80])


def _crear_skill(spec: dict) -> dict:
    from core import eris_fabrica as fab
    r = fab.crear_skill(spec.get("name") or spec.get("nombre") or "",
                        spec.get("description") or spec.get("descripcion") or "",
                        pasos=spec.get("pasos") or "")
    if r.get("error"):
        return {"ok": False, "error": r["error"]}
    # La skill se VALIDA aparte (crear_skill no valida nada, §5.4).
    prueba = "sin_validar"
    try:
        from core.tool_registry import get_tool
        msg = str(get_tool("skill_manage")({"action": "validate", "name": r.get("name")}))
        if "APROBADA" in msg:
            prueba = "skill_manage validate: APROBADA"
        else:
            return {"ok": False, "error": f"La skill no pasó la validación: {msg[:200]}"}
    except Exception as e:
        prueba = f"validate_no_disponible({type(e).__name__})"
    return _cap(r.get("name"), "skill", r.get("path") or "", "fabrica.crear_skill",
                prueba)


def _crear_server(spec: dict) -> dict:
    from core import server_forge as sf
    r = sf.crear(spec.get("name") or spec.get("nombre") or "",
                 rutas=spec.get("rutas") or spec.get("routes") or [],
                 host=spec.get("host") or "127.0.0.1",
                 port=spec.get("port") or 0,
                 descripcion=spec.get("description") or spec.get("descripcion") or "")
    if r.get("error"):
        return {"ok": False, "error": r["error"]}
    lv = sf.levantar(r["name"])
    if lv.get("health") != "ok":
        return {"ok": False, "error": f"El servidor {r['name']} no dio /health 200: {lv.get('health')}"}
    return _cap(r["name"], "server", r.get("path") or "", "server_forge.crear+levantar",
                f"/health 200 en {lv.get('health_url')}")


def _crear_dependencia(spec: dict) -> dict:
    pkg = spec.get("package") or spec.get("paquete") or spec.get("name")
    if not pkg:
        return {"ok": False, "error": "Falta 'package' en la spec."}
    try:
        from core.tool_registry import get_tool
        out = str(get_tool("autonomy")({"action": "install", "package": pkg,
                                        "reason": spec.get("razon") or "barrera"}))
    except Exception as e:
        return {"ok": False, "error": f"autonomy no disponible: {e}"}
    return _cap(pkg, "dependencia", "", "autonomy.auto_install_package (venv)",
                out[:200])


def _crear_conocimiento(spec: dict) -> dict:
    tema = spec.get("tema") or spec.get("name") or ""
    if not tema:
        return {"ok": False, "error": "Falta 'tema' para estudiar."}
    try:
        from core import learning_engine as le
        out = le.study_cycle(tema)
    except Exception as e:
        return {"ok": False, "error": f"learning_engine no disponible: {e}"}
    return _cap(tema, "conocimiento", "", "learning_engine.study_cycle", str(out)[:200])


def _reparar(spec: dict) -> dict:
    """Reparación de código propio: cambio mínimo con backup+validación+rollback."""
    path = spec.get("path") or spec.get("file") or ""
    code = spec.get("code") or spec.get("contenido")
    if not path or code is None:
        return {"ok": False, "error": "Para reparar hacen falta 'path' y el 'code' nuevo."}
    try:
        from core.mission_agent import edit as _mission_edit
        out = str(_mission_edit(path, code, confirm=bool(spec.get("confirm"))))
    except Exception as e:
        return {"ok": False, "error": f"mission.edit no disponible: {e}"}
    ok = "Aplicado" in out
    return {"ok": ok, "capacidad": path.split("/")[-1], "tipo": "reparacion",
            "path": path, "como_se_creo": "mission.edit (backup+validación)",
            "creada_vs_reutilizada": "reparada", "prueba": str(out)[:200]} if ok \
        else {"ok": False, "error": str(out)[:240]}


def _crear_script(spec: dict) -> dict:
    """Escribe un script en su workspace y lo prueba (lógica: code_sandbox)."""
    path = spec.get("path") or spec.get("file") or ""
    code = spec.get("code") or spec.get("contenido") or ""
    if not path or not code:
        return {"ok": False, "error": "Para un script hacen falta 'path' y 'code'."}
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(code, encoding="utf-8")
    except Exception as e:
        return {"ok": False, "error": f"No pude escribir el script: {e}"}
    # Prueba en code_sandbox (lógica pura) antes de darlo por creado.
    prueba = "sin_probar"
    try:
        from core.code_sandbox import execute_python
        out = str(execute_python(code, timeout=int(spec.get("timeout") or 15)))
        prueba = out[:200]
    except Exception as e:
        prueba = f"code_sandbox no disponible: {e}"
    return _cap(spec.get("name") or path.split("/")[-1], "script", path,
                "script en workspace + code_sandbox", prueba)


_ROUTE_CREAR = {
    "libreria": _crear_libreria, "library": _crear_libreria,
    "tool": _crear_tool, "herramienta": _crear_tool,
    "skill": _crear_skill,
    "server": _crear_server, "servidor": _crear_server, "api": _crear_server,
    "dependencia": _crear_dependencia, "paquete": _crear_dependencia,
    "conocimiento": _crear_conocimiento, "knowledge": _crear_conocimiento,
    "reparacion": _reparar, "reparar": _reparar, "fix": _reparar,
    "script": _crear_script,
}


def _tipo_de_enfoque(plan: dict) -> str:
    enf = str(plan.get("enfoque") or "").lower()
    if "reutilizar" in enf:
        return "recetario"
    if "instalar dependencia" in enf:
        return "dependencia"
    if "estudiar" in enf or "investigar" in enf:
        return "conocimiento"
    if "incorporar" in enf:
        return "incorporada"
    if "pedir credencial" in enf or "permiso" in enf:
        return "acceso"
    return "capacidad"


def crear(barrier_id: str, spec: dict = None) -> dict:
    """Ruta de creación (§5.4): mira el inventario, crea/repara y prueba.

    `spec` describe qué crear: {tipo, name, ...}. Si no se pasa, se reusa la
    guardada en la barrera o se infiere del plan. Una capacidad NO se da por
    creada hasta que su test propio pasa.
    """
    state = _load()
    b = _find(state, barrier_id)
    if not b:
        return {"ok": False, "error": f"No existe la barrera {barrier_id}."}
    if spec:
        b["creacion_spec"] = dict(spec)
    spec = dict(b.get("creacion_spec") or {})
    plan = b.get("plan") or {}
    tipo = str(spec.get("tipo") or _tipo_de_enfoque(plan)).lower()
    nombre = spec.get("name") or spec.get("nombre") or ""

    # 1) ¿Ya existe? No reconstruir lo que ya tiene (§7).
    inv = _inventario(nombre) if nombre else None
    if inv:
        item = inv["item"]
        cap = {"capacidad": nombre, "tipo": tipo,
               "path": item.get("path") or item.get("file") or "",
               "como_se_creo": inv["origen"], "creada_vs_reutilizada": "reutilizada",
               "prueba": "ya existía en el inventario", "ts": _now()}
        b["capacidad"] = cap
        b["estado"] = "creada"
        _log(b, "reutilizada_capacidad", f"{nombre} ({inv['origen']})")
        _save(state)
        return {"ok": True, "barrera_id": barrier_id, "capacidad": cap}

    # 2) Frenos de presupuesto (§12.2) — solo al CREAR algo nuevo (reutilizar es gratis).
    enfoque = str(plan.get("enfoque") or "")
    intentados = b.setdefault("enfoques_intentados", [])
    nuevo_enfoque = bool(enfoque) and enfoque not in intentados
    if nuevo_enfoque and len(intentados) >= _MAX_ENFOQUES:
        _save(state)
        esc = escalar(barrier_id, "presupuesto de 3 enfoques agotado")
        return {"ok": False, "barrera_id": barrier_id,
                "error": "Presupuesto de enfoques agotado (3). Escalado al dueño.",
                "escalada": esc.get("escalada")}
    por_enf = b.setdefault("cap_nuevas_por_enfoque", {})
    if enfoque and por_enf.get(enfoque, 0) >= _MAX_CAP_POR_ENFOQUE:
        return {"ok": False, "barrera_id": barrier_id,
                "error": "Ya creaste una capacidad nueva para este enfoque; "
                         "probá OTRO enfoque (usá `rechazar`)."}
    if _capacidades_nuevas_hoy(state) >= _TOPE_DIARIO:
        _save(state)
        esc = escalar(barrier_id, "tope diario de 3 capacidades nuevas alcanzado")
        return {"ok": False, "barrera_id": barrier_id,
                "error": "Tope diario alcanzado (3 capacidades nuevas). Escalado al dueño.",
                "escalada": esc.get("escalada")}
    if nuevo_enfoque:
        intentados.append(enfoque)

    # 3) Crear por la ruta que corresponda.
    fn = _ROUTE_CREAR.get(tipo)
    if fn is None:
        return {"ok": False, "error": f"Tipo de creación '{tipo}' no soportado. "
                                      f"Especificá spec.tipo ∈ {sorted(_ROUTE_CREAR)}."}
    try:
        r = fn(spec)
    except Exception as e:
        r = {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}"}
    if not r.get("ok"):
        b.setdefault("intentos", []).append(
            {"ts": _now(), "resultado": "creacion_fallida", "tipo": tipo,
             "error": r.get("error", "")[:300]})
        _log(b, "creacion_fallida", f"{tipo}: {r.get('error','')[:120]}")
        _save(state)
        return {"ok": False, "error": r.get("error"), "barrera_id": barrier_id}

    cap = {"capacidad": r.get("capacidad") or nombre, "tipo": r.get("tipo") or tipo,
           "path": r.get("path") or "", "como_se_creo": r.get("como_se_creo") or "",
           "creada_vs_reutilizada": r.get("creada_vs_reutilizada") or "creada",
           "prueba": r.get("prueba") or "", "ts": _now()}
    b["capacidad"] = cap
    b["estado"] = "creada"
    if enfoque:
        b.setdefault("cap_nuevas_por_enfoque", {})
        b["cap_nuevas_por_enfoque"][enfoque] = b["cap_nuevas_por_enfoque"].get(enfoque, 0) + 1
    _log(b, "creada", f"{cap['capacidad']} ({cap['tipo']}): {cap['prueba'][:100]}")
    _save(state)
    return {"ok": True, "barrera_id": barrier_id, "capacidad": cap}


def usar(barrier_id: str, invocacion: dict = None) -> dict:
    """Uso (§5.5): invoca la capacidad creada y captura el resultado CRUDO."""
    state = _load()
    b = _find(state, barrier_id)
    if not b:
        return {"ok": False, "error": f"No existe la barrera {barrier_id}."}
    cap = b.get("capacidad")
    if not cap:
        return {"ok": False, "error": "Primero `crear`: la barrera no tiene capacidad."}
    spec = dict(b.get("creacion_spec") or {})
    inv = dict(invocacion or spec.get("uso") or {})
    tipo = str(cap.get("tipo") or "").lower()
    nombre = cap.get("capacidad") or ""
    crudo = ""
    ok = False
    try:
        if tipo in ("tool", "herramienta"):
            from core.tool_registry import get_tool
            t = get_tool(nombre)
            if t is None:
                return {"ok": False, "error": f"La tool '{nombre}' no está registrada."}
            crudo = str(t(inv.get("params") or inv or {"action": "status"}))
            ok = bool(crudo.strip()) and '"error"' not in crudo.lower()[:200]
        elif tipo in ("libreria", "library"):
            from core import eris_fabrica as fab
            fn_name = inv.get("function") or (spec.get("functions") or [{}])[0].get("name") or "probar"
            r = fab.usar_libreria(nombre, fn_name, inv.get("params") or {})
            crudo = json.dumps(r, ensure_ascii=False, default=str)
            ok = not (isinstance(r, dict) and r.get("error"))
        elif tipo in ("skill",):
            p = Path(cap.get("path") or "")
            sk = p / "SKILL.md" if p.is_dir() else p
            crudo = sk.read_text(encoding="utf-8") if sk.exists() else ""
            ok = len(crudo) > 0
        elif tipo in ("server", "servidor"):
            from core import server_forge as sf
            h = sf.health(nombre)
            crudo = json.dumps(h, ensure_ascii=False)
            ok = bool(h.get("ok"))
        elif tipo in ("dependencia", "paquete"):
            import importlib
            mod = nombre.split("[")[0].strip()
            importlib.import_module(mod)
            crudo = f"import {mod} OK"
            ok = True
        elif tipo in ("reparacion", "reparar"):
            from core import mission_agent as ma
            v = ma.verify(cap.get("path") or "")
            crudo = json.dumps(v, ensure_ascii=False, default=str)
            ok = "verde" in crudo.lower() or v.get("ok") is True
        elif tipo in ("script",):
            from core import code_sandbox as cs
            code = Path(cap.get("path")).read_text(encoding="utf-8")
            crudo = cs.execute_python(code, timeout=int(inv.get("timeout") or 15))
            ok = "error" not in crudo.lower()[:200]
        else:
            return {"ok": False, "error": f"No sé usar la capacidad de tipo '{tipo}'."}
    except Exception as e:
        return {"ok": False, "error": f"Fallo al usar '{nombre}': {type(e).__name__}: {str(e)[:200]}"}

    uso = {"ok": ok, "resultado_crudo": str(crudo)[:4000], "ts": _now(),
           "invocacion": inv}
    b["uso"] = uso
    b["estado"] = "usada"
    _log(b, "usada", f"{nombre}: {'ok' if ok else 'error'}")
    _save(state)
    return {"ok": ok, "barrera_id": barrier_id, "uso": uso}


# ── F6: verificación con evidencia + frenos (§5.6/§5.7) ──────────────────────

# Presupuesto aprobado por el dueño (§12.2).
_MAX_ENFOQUES = 3          # enfoques distintos por barrera
_MAX_CAP_POR_ENFOQUE = 1   # capacidad nueva por enfoque
_TOPE_DIARIO = 3           # capacidades nuevas por día (todas las barreras)
_HORAS_PRESUPUESTO = 24    # presupuesto de tiempo por barrera


def _hoy() -> str:
    return time.strftime("%Y-%m-%d")


def _capacidades_nuevas_hoy(state: dict) -> int:
    n = 0
    for x in state.get("barreras", []):
        c = x.get("capacidad")
        if c and c.get("creada_vs_reutilizada") == "creada" \
                and str(c.get("ts", ""))[:10] == _hoy():
            n += 1
    return n


def _traza(accion: str, request: str, result: str, ok: bool) -> str:
    """Traza replayable (mismo formato/dir que TraceKeeper: data/agent_traces/)."""
    try:
        d = Path(_BASE) / "data" / "agent_traces"
        d.mkdir(parents=True, exist_ok=True)
        run = {"ts": time.time(), "agent": "barrier_engine", "action": accion,
               "request": str(request)[:200], "tools": ["barreras"],
               "result": str(result)[:500], "ok": bool(ok)}
        p = d / f"trace_{int(time.time() * 1000)}.json"
        p.write_text(json.dumps(run, ensure_ascii=False, indent=2), encoding="utf-8")
        return str(p)
    except Exception:
        return ""


def _nota_obsidian(b: dict, titulo: str, cuerpo: str) -> str:
    """Deja una nota legible (lo que el dueño puede ABRIR) en Obsidian."""
    try:
        from core.logging_setup import get_obsidian_vault
        vault = get_obsidian_vault()
        carpeta = Path(vault) / "Proyectos" / "barreras"
        carpeta.mkdir(parents=True, exist_ok=True)
        safe = "".join(c for c in (b.get("titulo") or "barrera") if c.isalnum() or c in " -_")[:40].strip() or "barrera"
        fecha = time.strftime("%Y-%m-%d")
        p = carpeta / f"{fecha} {safe}.md"
        p.write_text(cuerpo, encoding="utf-8")
        return str(p)
    except Exception as e:
        return f"(no pude escribir la nota: {e})"


def _registrar_enfoque(b: dict, enfoque: str) -> None:
    if not enfoque:
        return
    lst = b.setdefault("enfoques_intentados", [])
    if enfoque not in lst:
        lst.append(enfoque)


def _evidencia_de(cap: dict, spec: dict, uso: dict | None) -> list[dict]:
    """Chequeos de evidencia dura según el tipo de capacidad (§5.6)."""
    checks: list[dict] = []
    tipo = str(cap.get("tipo") or "").lower()
    path = cap.get("path") or ""
    nombre = cap.get("capacidad") or ""
    try:
        if tipo in ("tool", "herramienta"):
            from core.tool_registry import get_tool
            t = get_tool(nombre)
            checks.append({"nombre": "tool registrada", "ok": callable(t), "detalle": nombre})
            if callable(t):
                out = str(t({"action": "status"}))
                checks.append({"nombre": "tool responde status", "ok": bool(out.strip()),
                               "detalle": out[:200]})
        elif tipo in ("libreria", "library"):
            p = Path(path) if path else None
            checks.append({"nombre": "archivo .py existe", "ok": bool(p and p.is_file() and p.stat().st_size > 0),
                           "detalle": path})
            from core import eris_fabrica as fab
            fn = None
            if spec.get("functions"):
                fn = spec["functions"][0].get("name")
            if fn:
                out = fab.usar_libreria(nombre, fn, (spec.get("prueba_params") or {}).get(fn, {}))
                ok = not (isinstance(out, dict) and out.get("error"))
                checks.append({"nombre": f"función {fn} ejecuta", "ok": ok,
                               "detalle": json.dumps(out, ensure_ascii=False, default=str)[:200]})
        elif tipo == "skill":
            p = Path(path)
            sk = (p / "SKILL.md") if p.is_dir() else p
            checks.append({"nombre": "SKILL.md existe", "ok": bool(sk.is_file() and sk.stat().st_size > 0),
                           "detalle": str(sk)})
        elif tipo in ("server", "servidor"):
            from core import server_forge as sf
            h = sf.health(nombre)
            checks.append({"nombre": "GET /health 200", "ok": bool(h.get("ok")),
                           "detalle": json.dumps(h, ensure_ascii=False)[:200]})
        elif tipo in ("dependencia", "paquete"):
            import importlib
            mod = nombre.split("[")[0].strip()
            try:
                importlib.import_module(mod)
                ok, det = True, f"import {mod} OK"
            except Exception as e:
                ok, det = False, str(e)[:200]
            checks.append({"nombre": f"import {mod}", "ok": ok, "detalle": det})
        elif tipo in ("reparacion", "reparar"):
            import py_compile
            try:
                py_compile.compile(str(path), doraise=True)
                ok, det = True, "py_compile OK"
            except Exception as e:
                ok, det = False, str(e)[:200]
            checks.append({"nombre": "py_compile", "ok": ok, "detalle": det})
        elif tipo == "script":
            p = Path(path) if path else None
            checks.append({"nombre": "archivo del script", "ok": bool(p and p.exists() and p.stat().st_size > 0),
                           "detalle": path})
        else:
            p = Path(path) if path else None
            checks.append({"nombre": "artefacto con ruta", "ok": bool(p and p.exists()),
                           "detalle": path or "(sin ruta)"})
    except Exception as e:
        checks.append({"nombre": "chequeo", "ok": False, "detalle": f"{type(e).__name__}: {e}"})

    if uso and uso.get("resultado_crudo"):
        checks.append({"nombre": "uso previo devolvió salida", "ok": True,
                       "detalle": str(uso["resultado_crudo"])[:200]})
    return checks


def _dejar_receta(b: dict) -> dict:
    """Deja la receta de la barrera en las 4 capas (§5.8b). Best-effort."""
    try:
        from core import recetario as rec
        return rec.guardar(barrera=b)
    except Exception as e:
        return {"error": f"{type(e).__name__}: {str(e)[:150]}"}


def verificar(barrier_id: str) -> dict:
    """Verifica con EVIDENCIA dura (§5.6). Sin evidencia no hay 'resuelta'."""
    state = _load()
    b = _find(state, barrier_id)
    if not b:
        return {"ok": False, "error": f"No existe la barrera {barrier_id}."}
    cap = b.get("capacidad")
    if not cap:
        return {"ok": False, "error": "No hay capacidad que verificar: primero `crear`."}
    spec = dict(b.get("creacion_spec") or {})
    checks = _evidencia_de(cap, spec, b.get("uso"))
    evidencia_ok = bool(checks) and all(c["ok"] for c in checks)
    b["evidencia"] = {"checks": checks, "ok": evidencia_ok, "ts": _now()}

    if evidencia_ok:
        b["estado"] = "verificada"
        b.pop("paso_pendiente", None)
        _log(b, "verificada", "; ".join(c["nombre"] for c in checks))
        _save(state)
        b["receta"] = _dejar_receta(b)
        _save(state)
        _traza("verificar", barrier_id, f"evidencia ok: {[c['nombre'] for c in checks]}", True)
        return {"ok": True, "barrera_id": barrier_id, "evidencia": b["evidencia"],
                "estado": "verificada"}

    # No apareció la evidencia (§5.6): ¿Eris había afirmado éxito?
    afirmo = bool(b.get("uso") and b.get("uso", {}).get("ok"))
    b["estado"] = "diagnosticada"
    enfoque = str((b.get("plan") or {}).get("enfoque") or "")
    if enfoque:
        b.setdefault("rechazados", []).append(
            {"ts": _now(), "motivo": "sin evidencia", "enfoque": enfoque})
    if afirmo:
        b["falso_positivo"] = {"ts": _now(), "motivo": "afirmó éxito sin evidencia dura",
                               "checks": checks}
        _log(b, "falso_positivo", "afirmó éxito y la evidencia no apareció")
    b.pop("paso_pendiente", None)
    _save(state)
    _traza("verificar", barrier_id, f"sin evidencia (falso_positivo={afirmo})", False)

    # Frenos: si ya no quedan enfoques, escalar.
    if len(b.get("enfoques_intentados", [])) >= _MAX_ENFOQUES:
        esc = escalar(barrier_id, "se agotaron los enfoques sin evidencia")
        return {"ok": False, "barrera_id": barrier_id, "evidencia": b["evidencia"],
                "falso_positivo": afirmo, "error": "sin evidencia; escalado", "escalada": esc}
    return {"ok": False, "barrera_id": barrier_id, "evidencia": b["evidencia"],
            "falso_positivo": afirmo,
            "error": "La evidencia no apareció; vuelve al diagnóstico con otro enfoque."}


def escalar(barrier_id: str, motivo: str = "") -> dict:
    """Escalada al dueño (§5.7): informe legible + nota Obsidian, y frena."""
    state = _load()
    b = _find(state, barrier_id)
    if not b:
        return {"ok": False, "error": f"No existe la barrera {barrier_id}."}
    cap = b.get("capacidad") or {}
    ev = b.get("evidencia") or {}
    informe = {
        "meta": b.get("goal_ref") or b.get("titulo"),
        "que_faltaba": (b.get("diagnostico") or {}).get("tipo") or b.get("descripcion"),
        "creado_o_reutilizado": (f"{cap.get('capacidad')} ({cap.get('tipo')}, "
                                 f"{cap.get('creada_vs_reutilizada')})" if cap else "nada"),
        "enfoques_intentados": b.get("enfoques_intentados", []),
        "motivo": motivo or "sin especificar",
        "evidencia": ev.get("checks") if ev else [],
        "falso_positivo": bool(b.get("falso_positivo")),
        "ts": _now(),
    }
    b["escalada"] = informe
    b["estado"] = "escalada"
    b.pop("paso_pendiente", None)

    lineas = [
        f"# 🧗 Barrera escalada — {b.get('titulo') or barrier_id}",
        f"**{informe['ts']}** · id `{barrier_id}`",
        "",
        f"- **Meta:** {informe['meta']}",
        f"- **Qué faltaba:** {informe['que_faltaba']}",
        f"- **Creó o reutilizó:** {informe['creado_o_reutilizado']}",
        f"- **Enfoques intentados:** {', '.join(informe['enfoques_intentados']) or '(ninguno)'}",
        f"- **Motivo de la escalada:** {informe['motivo']}",
        f"- **Falso positivo:** {'sí' if informe['falso_positivo'] else 'no'}",
    ]
    if informe["evidencia"]:
        lineas += ["", "## Evidencia",
                   *[f"- {'✅' if c.get('ok') else '❌'} {c.get('nombre')}: {c.get('detalle')}"
                     for c in informe["evidencia"]]]
    lineas += ["", "## Qué necesito del dueño", b.get("escalada_pregunta")
               or "Decidir si cambio de enfoque, me das acceso/dato faltante, o lo dejamos."]
    ruta = _nota_obsidian(b, b.get("titulo") or "barrera", "\n".join(lineas))
    informe["nota"] = ruta
    b["escalada"] = informe

    _log(b, "escalada", f"{informe['motivo']} → nota {ruta}")
    _save(state)
    b["receta"] = _dejar_receta(b)
    _save(state)
    _traza("escalar", barrier_id, informe["motivo"], False)
    return {"ok": True, "barrera_id": barrier_id, "escalada": informe}


def bucle(barrier_id: str, spec: dict = None) -> dict:
    """Corre el ciclo con presupuesto (§5.7): diag→acopio→plan→decisión→crear→usar→verificar.

    Frena en `esperando_ok` (pide OK) y en el presupuesto (escala). No da nada
    por hecho sin evidencia.
    """
    state = _load()
    b = _find(state, barrier_id)
    if not b:
        return {"ok": False, "error": f"No existe la barrera {barrier_id}."}
    if b.get("estado") in ("escalada",):
        return {"ok": False, "error": "La barrera ya está escalada.", "escalada": b.get("escalada")}

    diario: list[str] = []

    def paso(nombre, fn):
        r = fn()
        diario.append(nombre)
        return r

    if not b.get("diagnostico"):
        paso("diagnosticar", lambda: diagnosticar(barrier_id))
    b = _buscar(barrier_id) or b
    if not b.get("plan"):
        paso("investigar", lambda: investigar(barrier_id))
        b = _buscar(barrier_id) or b
        paso("planificar", lambda: planificar(barrier_id))
        b = _buscar(barrier_id) or b
    paso("decidir", lambda: decidir(barrier_id))
    b = _buscar(barrier_id) or b

    if b.get("estado") == "esperando_ok":
        return {"ok": True, "esperando_ok": True, "barrera_id": barrier_id,
                "corte": (b.get("decision") or {}).get("corte"), "pasos": diario,
                "nota": "Necesita tu OK (aprobar) o cambiar de enfoque (rechazar)."}

    if not b.get("capacidad"):
        r = crear(barrier_id, spec=spec)
        diario.append("crear")
        if not r.get("ok"):
            return {"ok": False, "barrera_id": barrier_id, "pasos": diario,
                    "error": r.get("error"), "escalada": r.get("escalada")}
        b = _buscar(barrier_id) or b

    r = usar(barrier_id)
    diario.append("usar")
    b = _buscar(barrier_id) or b
    v = verificar(barrier_id)
    diario.append("verificar")
    b = _buscar(barrier_id) or b
    return {"ok": bool(v.get("ok")), "barrera_id": barrier_id, "pasos": diario,
            "usar_ok": r.get("ok"), "evidencia": b.get("evidencia"),
            "falso_positivo": v.get("falso_positivo", False),
            "estado": b.get("estado"), "escalada": v.get("escalada")}


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
        plan = b.get("plan") or {}
        if plan.get("enfoque"):
            b.setdefault("rechazados", []).append(
                {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "motivo": motivo,
                 "opcion": plan.get("elegido"), "enfoque": plan.get("enfoque")}
            )
        b["estado"] = "diagnosticada"
        b.pop("paso_pendiente", None)
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

    if action in ("diagnosticar", "diagnostico"):
        r = diagnosticar(params.get("id") or params.get("barrera_id") or "",
                         usar_llm=bool(params.get("usar_llm")))
        if not r.get("ok"):
            return f"⚠️ {r.get('error')}"
        d = r["diagnostico"]
        return (f"🩺 Barrera {r['barrera_id']}: falta **{d['falta']}** "
                f"(tipo `{d['tipo']}`, vía {d['ruta']}; método {d['metodo']}).")

    if action in ("investigar", "acopio", "acopiar"):
        r = investigar(params.get("id") or params.get("barrera_id") or "",
                       int(params.get("limite") or 5))
        if not r.get("ok"):
            return f"⚠️ {r.get('error')}"
        p = r["paquete"]
        if p.get("recetas"):
            return (f"📚 Acopio de {r['barrera_id']}: **{len(p['recetas'])} receta/s del recetario** "
                    f"→ se puede resolver reutilizando.")
        return (f"🔎 Acopio de {r['barrera_id']}: {len(p.get('fuentes', []))} fuente/s externas "
                f"({p.get('por_canal', {})}). Canales: {', '.join(p['canales']) or 'ninguno'}.")

    if action in ("planificar", "plan"):
        r = planificar(params.get("id") or params.get("barrera_id") or "",
                       usar_llm=bool(params.get("usar_llm")))
        if not r.get("ok"):
            return f"⚠️ {r.get('error')}"
        pl = r["plan"]
        return (f"🧭 Plan de {r['barrera_id']}: {len(pl['opciones'])} opción/es; "
                f"elegida **{pl.get('elegido')} · {pl.get('enfoque')}** ({pl.get('motivo')}). "
                f"Pasos: {'; '.join(pl.get('pasos', []))}")

    if action in ("decidir", "decision"):
        r = decidir(params.get("id") or params.get("barrera_id") or "")
        if not r.get("ok"):
            return f"⚠️ {r.get('error')}"
        d = r["decision"]
        if d["resultado"] == "esperando_ok":
            return (f"⏸️ Barrera {r['barrera_id']} corta en **esperando_ok**: {d['corte']}. "
                    f"(aprobá con `action=aprobar` o pedí otro enfoque con `action=rechazar`).")
        return (f"▶️ Barrera {r['barrera_id']} puede seguir (riesgo {d['riesgo_nominal']}, "
                f"en margen propio={d['en_allowlist']}).")

    if action in ("zona", "zona?"):
        texto = params.get("texto") or params.get("text") or params.get("consulta") or ""
        if not texto:
            return "Pasá `texto=...` para consultar la zona (ej: un comando o una ruta)."
        z = evaluar_zona_texto(texto)
        extra = f" ({z.get('motivo')}: '{z.get('match')}')" if z.get("zona") == "protegida" else ""
        return f"🧭 Zona de «{texto[:80]}»: **{z.get('zona')}**{extra}"

    if action in ("crear", "creacion"):
        spec = params.get("spec") or params.get("especificacion")
        if isinstance(spec, str):
            try:
                spec = json.loads(spec)
            except Exception:
                spec = None
        r = crear(params.get("id") or params.get("barrera_id") or "", spec=spec)
        if not r.get("ok"):
            return f"⚠️ No pude crear: {r.get('error')}"
        c = r["capacidad"]
        return (f"🛠️ Capacidad **{c['capacidad']}** ({c['tipo']}) — {c['creada_vs_reutilizada']} "
                f"vía {c['como_se_creo']}. Prueba: {c['prueba'][:120]}. Ruta: {c['path']}")

    if action in ("usar", "uso"):
        inv = params.get("invocacion") or params.get("params_uso")
        if isinstance(inv, str):
            try:
                inv = json.loads(inv)
            except Exception:
                inv = None
        r = usar(params.get("id") or params.get("barrera_id") or "", invocacion=inv)
        if not r.get("ok"):
            err = r.get("error") or (r.get("uso") or {}).get("resultado_crudo", "")[:200]
            return f"⚠️ No se pudo usar: {err}"
        crudo = r["uso"]["resultado_crudo"]
        return f"▶️ Uso de {r['barrera_id']}:\n{crudo[:600]}"

    if action in ("verificar", "verificacion", "verificá"):
        r = verificar(params.get("id") or params.get("barrera_id") or "")
        if r.get("error") and "evidencia" not in r:
            return f"⚠️ {r.get('error')}"
        ev = r.get("evidencia") or {}
        lineas = [f"{'✅' if c.get('ok') else '❌'} {c.get('nombre')}: {c.get('detalle')}"
                  for c in ev.get("checks", [])]
        if r.get("ok"):
            return (f"🔬 Barrera {r['barrera_id']} VERIFICADA con evidencia real "
                    f"(estado {r.get('estado')}):\n" + "\n".join(lineas))
        cabeza = (f"🚫 Barrera {r['barrera_id']} SIN evidencia"
                  + (" — FALSO POSITIVO registrado (afirmó éxito)" if r.get("falso_positivo") else "")
                  + ":\n")
        if r.get("escalada"):
            cola = f"\n⤴️ Escalado al dueño ({r['escalada'].get('motivo')}). Nota: {r['escalada'].get('nota')}"
        else:
            cola = "\n↩️ Vuelve al diagnóstico con OTRO enfoque (usá `rechazar`)."
        return cabeza + "\n".join(lineas) + cola

    if action in ("bucle", "ciclo", "resolver"):
        spec = params.get("spec") or params.get("especificacion")
        if isinstance(spec, str):
            try:
                spec = json.loads(spec)
            except Exception:
                spec = None
        r = bucle(params.get("id") or params.get("barrera_id") or "", spec=spec)
        if r.get("esperando_ok"):
            return (f"⏸️ Bucle {r['barrera_id']} corta en esperando_ok: {r.get('corte')}. "
                    f"Pasos: {', '.join(r.get('pasos', []))}. Necesita tu OK.")
        if r.get("error") and not r.get("pasos"):
            return f"⚠️ {r.get('error')}"
        pasos = ", ".join(r.get("pasos", []))
        if r.get("ok"):
            ev = r.get("evidencia") or {}
            det = "; ".join(c.get("nombre") for c in ev.get("checks", []))
            return (f"🏁 Bucle {r['barrera_id']} RESUELTO con evidencia. Pasos: {pasos}. "
                    f"Evidencia: {det}")
        if r.get("escalada"):
            return (f"⤴️ Bucle {r['barrera_id']} escalado: {r['escalada'].get('motivo')}. "
                    f"Pasos: {pasos}. Nota: {r['escalada'].get('nota')}")
        return (f"↩️ Bucle {r['barrera_id']} sin evidencia ({r.get('error')}). "
                f"Pasos: {pasos}. Probá otro enfoque (`rechazar`).")

    if action in ("escalar", "escalada"):
        r = escalar(params.get("id") or params.get("barrera_id") or "",
                    params.get("motivo") or "")
        if not r.get("ok"):
            return f"⚠️ {r.get('error')}"
        e = r["escalada"]
        return (f"⤴️ Barrera {r['barrera_id']} escalada al dueño.\n"
                f"• Motivo: {e['motivo']}\n"
                f"• Creó/reutilizó: {e['creado_o_reutilizado']}\n"
                f"• Enfoques: {', '.join(e['enfoques_intentados']) or '(ninguno)'}\n"
                f"• Nota para el dueño: {e['nota']}")

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
