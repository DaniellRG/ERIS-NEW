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
