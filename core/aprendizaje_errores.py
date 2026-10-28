# -*- coding: utf-8 -*-
"""
core/aprendizaje_errores.py — MEMORIA DE PROBLEMAS → SOLUCIONES de ERIS.

Qué hace distinto a lo que ya existía:
  - `mistake_learner` guarda errores con causa/solución, pero nadie los
    empareja con el arreglo real que funcionó.
  - `procedimientos` guarda secuencias de tools, pero con una intención
    inventada a partir del resultado, no con el pedido real del usuario.
  - `learning_engine` cristaliza lecciones de estudio, no de la práctica.

Este módulo cierra ese hueco: observa la práctica real de ERIS.
  1. Cuando una tool falla, guarda el fallo como PENDIENTE (con el pedido
     real del usuario, la tool y los parámetros).
  2. Cuando después una tool funciona, EMPAREJA el fallo pendiente con el
     éxito y guarda una receta reutilizable: problema → solución.
  3. Cuando vuelve a aparecer un pedido parecido, `inject_relevant()` inyecta
     la solución en el contexto para que ERIS no vuelva a tropezar.

Estado: memory/aprendizajes_problemas.json
"""
from __future__ import annotations

import json
import re
import time
import unicodedata
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_STATE_FILE = _BASE / "memory" / "aprendizajes_problemas.json"

# Una ventana de 20 minutos para emparejar fallo → solución (mismo turno o
# corrección inmediata del usuario). Más viejo que eso ya no es "el arreglo".
_PAIR_WINDOW_S = 20 * 60
_MAX_APRENDIZAJES = 400
_MAX_PENDIENTES = 12

_STOPWORDS = {
    "que", "como", "para", "por", "con", "los", "las", "una", "uno", "unos",
    "unas", "del", "este", "esta", "esto", "eso", "esa", "ese", "pero", "mas",
    "muy", "sin", "sobre", "entre", "cuando", "donde", "porque", "todo",
    "toda", "todos", "todas", "hay", "ser", "esta", "estoy", "hacer", "haz",
    "puedes", "puede", "quiero", "necesito", "ayuda", "ayudame", "favor",
    "the", "and", "for", "with", "that", "this", "from", "error", "failed",
    "tool", "none", "true", "false",
}


# ── Estado ───────────────────────────────────────────────────────────────────

def _empty() -> dict:
    return {
        "aprendizajes": [],
        "pendientes": [],
        "stats": {"fallos": 0, "soluciones": 0, "reutilizadas": 0},
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "updated_at": "",
    }


def _load() -> dict:
    try:
        if _STATE_FILE.exists():
            data = json.loads(_STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                for k, v in _empty().items():
                    data.setdefault(k, v)
                return data
    except Exception:
        pass
    return _empty()


def _save(state: dict):
    try:
        _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        state["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        _STATE_FILE.write_text(
            json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


# ── Texto ────────────────────────────────────────────────────────────────────

def _norm(texto: str) -> str:
    s = unicodedata.normalize("NFKD", str(texto or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.lower()


def _tokens(texto: str) -> set[str]:
    palabras = re.findall(r"[a-z0-9_]{3,}", _norm(texto))
    return {p for p in palabras if p not in _STOPWORDS}


# ── Registro ─────────────────────────────────────────────────────────────────

def record_failure(tool: str, args=None, error: str = "", contexto: str = "") -> dict:
    """Guarda un fallo PENDIENTE de solución. No crea receta todavía."""
    state = _load()
    ahora = time.time()
    # Limpiar pendientes viejos.
    state["pendientes"] = [
        p for p in state.get("pendientes", [])
        if ahora - float(p.get("ts", 0)) <= _PAIR_WINDOW_S
    ]
    entry = {
        "tool": str(tool or ""),
        "args": _resumir(args),
        "error": str(error or "")[:600],
        "contexto": str(contexto or "")[:400],
        "ts": ahora,
    }
    state["pendientes"].append(entry)
    state["pendientes"] = state["pendientes"][-_MAX_PENDIENTES:]
    state.setdefault("stats", {})["fallos"] = int(
        state.get("stats", {}).get("fallos", 0)) + 1
    _save(state)
    return entry


def record_success(tool: str, args=None, result: str = "", contexto: str = "") -> dict | None:
    """Empareja el último fallo pendiente con este éxito → receta reutilizable.

    Devuelve la receta creada, o None si no había nada pendiente que emparejar.
    """
    state = _load()
    ahora = time.time()
    pendientes = [
        p for p in state.get("pendientes", [])
        if ahora - float(p.get("ts", 0)) <= _PAIR_WINDOW_S
    ]
    if not pendientes:
        state["pendientes"] = []
        _save(state)
        return None

    fallo = pendientes[-1]
    state["pendientes"] = pendientes[:-1]

    problema = (fallo.get("contexto") or "").strip()
    if not problema:
        problema = "{} falló: {}".format(
            fallo.get("tool") or "una tool", (fallo.get("error") or "")[:160])

    solucion = str(result or "").strip()[:400]
    if not solucion:
        solucion = "reintentar {} con otros parámetros".format(tool)

    receta = {
        "id": "ap_%d" % int(ahora * 1000),
        "problema": problema[:500],
        "error": fallo.get("error", "")[:500],
        "tool_fallida": fallo.get("tool", ""),
        "args_fallidos": fallo.get("args", ""),
        "solucion": solucion,
        "tool_exitosa": str(tool or ""),
        "args_exitosos": _resumir(args),
        "contexto": contexto[:300],
        "ts": ahora,
        "fecha": time.strftime("%Y-%m-%d %H:%M"),
        "usos": 0,
    }
    state.setdefault("aprendizajes", []).append(receta)
    state["aprendizajes"] = state["aprendizajes"][-_MAX_APRENDIZAJES:]
    state.setdefault("stats", {})["soluciones"] = int(
        state.get("stats", {}).get("soluciones", 0)) + 1
    _save(state)
    print("[APRENDIZAJE] {} → {}: {}".format(
        receta["tool_fallida"], receta["tool_exitosa"],
        problema[:70]))
    return receta


def _resumir(args) -> str:
    if not args:
        return ""
    try:
        txt = json.dumps(args, ensure_ascii=False, default=str)
    except Exception:
        txt = str(args)
    return txt[:300]


# ── Búsqueda / inyección ─────────────────────────────────────────────────────

def search(query: str, limite: int = 3) -> list[dict]:
    """Busca recetas parecidas al pedido/error actual (solapamiento de tokens)."""
    q = _tokens(query)
    if not q:
        return []
    state = _load()
    puntuadas = []
    for r in state.get("aprendizajes", []):
        campo = " ".join(str(r.get(k, "")) for k in (
            "problema", "error", "tool_fallida", "tool_exitosa", "solucion"))
        tokens = _tokens(campo)
        if not tokens:
            continue
        comunes = q & tokens
        if not comunes:
            continue
        # Normalizado por el tamaño de la consulta: castiga coincidencias flojas.
        score = len(comunes) / max(1, len(q))
        if r.get("tool_fallida") and r["tool_fallida"] in query:
            score += 0.2
        puntuadas.append((score, r))
    puntuadas.sort(key=lambda x: (x[0], x[1].get("ts", 0)), reverse=True)
    out = []
    for score, r in puntuadas[:limite]:
        if score < 0.25:
            continue
        item = dict(r)
        item["_score"] = round(score, 2)
        out.append(item)
    return out


def inject_relevant(user_text: str) -> str:
    """Bloque `[SOLUCIONES QUE YA APRENDÍ]` para el contexto del turno."""
    try:
        if not user_text:
            return ""
        hits = search(user_text, limite=2)
        if not hits:
            return ""
        state = _load()
        lines = ["[SOLUCIONES QUE YA APRENDÍ — REUTILIZAR SI APLICA]"]
        lines.append("Esto ya me pasó antes. Si el problema de ahora se parece, "
                     "voy directo a la solución que funcionó, sin repetir el error.")
        for h in hits:
            lines.append(
                "- Problema: {p} → Solución: {s} (con `{t}`).".format(
                    p=(h.get("problema") or "")[:180],
                    s=(h.get("solucion") or "")[:220],
                    t=h.get("tool_exitosa") or "tool",
                ))
            h["usos"] = int(h.get("usos", 0)) + 1
        # Persistir contador de reutilización (best-effort).
        ids = {h.get("id") for h in hits}
        for r in state.get("aprendizajes", []):
            if r.get("id") in ids:
                r["usos"] = int(h["usos"])
        state.setdefault("stats", {})["reutilizadas"] = int(
            state.get("stats", {}).get("reutilizadas", 0)) + len(hits)
        _save(state)
        return "\n".join(lines)
    except Exception:
        return ""


def _ultimo_pedido() -> str:
    """Último mensaje del usuario (best-effort, sin depender de la GUI)."""
    try:
        from core.shared_context import get_shared_context
        convo = get_shared_context().get_conversation() or []
        for item in reversed(convo):
            s = str(item)
            if s.startswith("Usuario: "):
                return s[len("Usuario: "):]
            if not s.startswith("ERIS: "):
                return s
    except Exception:
        pass
    return ""


# ── Tool ─────────────────────────────────────────────────────────────────────

def _status(state: dict) -> str:
    st = state.get("stats", {})
    return ("Aprendizajes problema→solución: {} | pendientes: {} | "
            "fallos vistos: {} | soluciones: {} | reutilizadas: {}").format(
        len(state.get("aprendizajes", [])),
        len(state.get("pendientes", [])),
        st.get("fallos", 0), st.get("soluciones", 0), st.get("reutilizadas", 0))


def aprendizaje_errores(params: dict | None = None, player=None) -> str:
    """Tool `aprendizaje_errores`: consulta/administra las recetas de fallos."""
    params = params or {}
    accion = str(params.get("action") or "status").strip().lower()
    state = _load()

    if accion == "status":
        return _status(state)

    if accion in ("list", "listar"):
        ap = state.get("aprendizajes", [])
        if not ap:
            return "Todavía no tengo soluciones aprendidas de fallos reales."
        out = ["[PROBLEMAS → SOLUCIONES]"]
        for r in ap[-15:]:
            out.append("- {} → {} (usos: {})".format(
                (r.get("problema") or "")[:90],
                (r.get("solucion") or "")[:90],
                r.get("usos", 0)))
        return "\n".join(out)

    if accion in ("search", "buscar"):
        q = params.get("query") or params.get("texto") or ""
        hits = search(q, limite=int(params.get("limit", 3)))
        if not hits:
            return "No encontré soluciones parecidas a: {}".format(q[:100])
        return "\n\n".join(
            "Problema: {}\nError: {}\nSolución: {}\nTool: {}".format(
                h.get("problema"), h.get("error"), h.get("solucion"),
                h.get("tool_exitosa"))
            for h in hits)

    if accion in ("record", "registrar"):
        r = record_success(
            params.get("tool") or "manual",
            args={"nota": params.get("nota", "")},
            result=params.get("solucion") or params.get("solution") or "",
            contexto=params.get("problema") or params.get("problem") or "",
        )
        return "Guardado: {}".format(r.get("problema") if r else "sin fallo previo que emparejar")

    if accion in ("inject", "contexto"):
        txt = inject_relevant(params.get("query") or _ultimo_pedido())
        return txt or "No hay soluciones parecidas para este pedido."

    if accion in ("clear", "limpiar"):
        if params.get("confirm") not in (True, "si", "sí", "true"):
            return "Para borrar necesito confirm=true."
        state["aprendizajes"] = []
        state["pendientes"] = []
        _save(state)
        return "Memoria de problemas→soluciones vaciada."

    return _status(state)


__all__ = [
    "record_failure", "record_success", "search", "inject_relevant",
    "aprendizaje_errores",
]
