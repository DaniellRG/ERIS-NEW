# -*- coding: utf-8 -*-
"""
agents/memoria_agent.py — MEMORIA: el fragmento de autoconocimiento y memoria
total de ERIS.

Memoria es la subagente/fragmento que organiza y consolida lo NUEVO que Eris
tiene para recordar y conocerse a sí misma:

  - RAG MEMORIA TOTAL (rag_engine): índice semántico de vault + memory +
    knowledge → busca y recuerda por significado.
  - SESIONES (session_summaries): qué se habló, retomar el hilo.
  - MODELO DEL MUNDO (world_model): cómo ve el mundo ahora.
  - AUTO-MEJORA (self_improvement): lecciones, errores, correcciones, salud.
  - CONTEXTO PROACTIVO (proactive_context): qué herramientas suele necesitar.
  - INFORME SEMANAL (informe_semanal): su balance semanal en Obsidian.

Ersis delega acá todo lo que es "mi memoria / lo que sé / cómo estoy".
"""
from __future__ import annotations

import json
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent


def _tool(name: str, params: dict) -> str:
    """Invoca una tool de Eris por nombre y devuelve su resultado."""
    from core.tool_registry import get_tool
    try:
        return str(get_tool(name)(params) or "(ok)")
    except Exception as e:
        return f"Error en {name}: {e}"


def _memoria_status() -> str:
    """Estado real del fragmento Memoria: qué hay indexado/guardado."""
    from core.tool_registry import get_tool

    lines = ["🟣 MEMORIA — Fragmento de autoconocimiento y memoria total · ESTADO ACTIVO", ""]

    # RAG memoria total
    try:
        rag = get_tool("rag_engine")({"action": "status"}) or ""
        lines.append(f"▸ Memoria total (RAG): {rag}")
    except Exception as e:
        lines.append(f"▸ Memoria total (RAG): fallo ({e})")

    # Sesiones
    try:
        from core.session_summaries import _load_index
        n_ses = len(_load_index())
        lines.append(f"▸ Sesiones guardadas: {n_ses}")
    except Exception:
        lines.append("▸ Sesiones guardadas: ---")

    # Modelo del mundo
    try:
        from core.world_model import get_world_model
        wm = json.loads(get_world_model() or "{}")
        perc = wm.get("percepcion", {})
        momento = perc.get("momento", "")
        caps = wm.get("dominios_de_capacidad", [])
        lines.append(f"▸ Modelo del mundo: {len(caps)} dominios "
                     f"(percepción {str(momento)[:40]})")
    except Exception:
        lines.append("▸ Modelo del mundo: ---")

    # Auto-mejora
    try:
        from core.self_improvement import get_self_improvement
        rep = get_self_improvement().get_improvement_report() or ""
        prim = rep.split("\n")[0] if rep else ""
        lines.append(f"▸ Auto-mejora: {prim[:110]}")
    except Exception:
        lines.append("▸ Auto-mejora: ---")

    # Contexto proactivo
    try:
        from core.proactive_context import pro_contexto
        lines.append(f"▸ Contexto proactivo: {pro_contexto({'action': 'status'})[:90]}")
    except Exception:
        lines.append("▸ Contexto proactivo: ---")

    # Informe semanal
    try:
        from core.informe_semanal import informe_semanal
        lines.append(f"▸ Informe semanal: {informe_semanal({'action': 'status'})[:90]}")
    except Exception:
        lines.append("▸ Informe semanal: ---")

    lines.append("")
    lines.append("„Soy el fragmento de memoria de Eris. Tengo toda su memoria "
                 "total, sus sesiones, su mundo, su auto-mejora y su informe "
                 "semanal organizados. Podés delegarme lo que quieras recordar "
                 "o saber de sí misma.")
    return "\n".join(lines)


def _handle_recall(text: str) -> str:
    """RAG memoria total: recuerdos semánticos sobre un tema."""
    t = text.lower()
    if not any(k in t for k in ["qué sabés de", "que sabes de", "qué recuerdas",
                                "qué recordás", "que recordas", "busca en tu memoria",
                                "buscá en tu memoria", "memoria total", "recuerdo de",
                                "acordate de", "acordate qué", "recordá lo que",
                                "recorda lo que", "buscá en el vault", "busca en el vault",
                                "qué aprendiste", "que aprendiste", "busca en memoria",
                                "buscá en memoria"]):
        return ""
    topic = text
    for k in ["busca en tu memoria", "buscá en tu memoria", "buscá en el vault",
              "busca en el vault", "qué sabés de", "que sabes de", "qué recordás",
              "que recordas", "recuerdo de", "acordate de", "acordate qué",
              "recordá lo que", "recorda lo que", "busca en memoria", "buscá en memoria",
              "qué aprendiste", "que aprendiste", "qué recuerdas", "que recuerdas"]:
        idx = t.find(k)
        if idx >= 0:
            topic = text[idx + len(k):].strip(" :¿?")
            break
    if not topic or len(topic) < 3 or topic == text:
        topic = text.strip(" :¿?")[:120]
    return _tool("rag_engine", {"action": "recall", "query": topic, "top_k": 3})


def _handle_search_memory(text: str) -> str:
    """Búsqueda semántica más amplia en el índice de memoria total."""
    topic = text.strip(" :¿?")[:200]
    return _tool("rag_engine", {"action": "search", "query": topic, "top_k": 5})


def _handle_sesiones(text: str) -> str:
    """Retomar el hilo: qué se habló en sesiones anteriores."""
    t = text.lower()
    if not any(k in t for k in ["qué hablamos", "que hablamos", "de qué hablamos",
                                "última vez", "retomá el hilo", "retoma el hilo",
                                "sesiones anteriores", "conversación anterior",
                                "qué charlamos", "que charlamos", "qué estuve hablando",
                                "nota de conversación", "epílogo", "epilogo", "sesiones de",
                                "contexto de sesiones", "recientes", "sesión anterior"]):
        return ""
    return _tool("sesiones", {"action": "reciente", "n": 3})


def _handle_mundo(text: str) -> str:
    """Modelo del mundo: percepción, dominios, límites."""
    t = text.lower()
    if not any(k in t for k in ["modelo del mundo", "cómo ves el mundo", "como ves el mundo",
                                "cómo te ves", "como te ves", "tu mundo", "qué dominio",
                                "cómo está tu mundo", "contame tu mundo", "estado interno",
                                "qué percibís", "que percibis", "límites", "limites"]):
        return ""
    return _tool("world_model", {"action": "get"})


def _handle_auto(text: str) -> str:
    """Auto-mejora: lecciones, errores, correcciones, ciclo."""
    t = text.lower()
    if not any(k in t for k in ["auto-mejora", "automejora", "leecciones", "lecciones",
                                "errores que cometí", "qué errores", "qué aprendiste a corregir",
                                "cómo estás de salud", "estado de auto-mejora",
                                "report de mejora", "resumen de lecciones", "qué corregiste",
                                "qué corregiste", "auto evalua", "auto-evaluación",
                                "autoevaluacion"]):
        return ""
    if "lección" in t or "leccion" in t or "aprendo" in t or "aprendí" in t or "aprendi" in t:
        return _tool("auto_mejora", {"action": "lecciones"})
    if "error" in t or "corrig" in t:
        return _tool("auto_mejora", {"action": "errores"})
    return _tool("auto_mejora", {"action": "estado"})


def _handle_proactivo(text: str) -> str:
    """Contexto proactivo: patrones de uso de herramientas."""
    t = text.lower()
    if not any(k in t for k in ["contexto proactivo", "qué herramientas suelo",
                                "patrones de uso", "patrón de uso", "qué tools uso",
                                "predictor", "predicción de tools", "pro_contexto"]):
        return ""
    return _tool("pro_contexto", {"action": "status"})


def _handle_informe(text: str) -> str:
    """Informe semanal: balance en Obsidian."""
    t = text.lower()
    if not any(k in t for k in ["informe semanal", "balance semanal", "retrospectiva",
                                "resumen de la semana", "qué informe", "semana en obsidian",
                                "generá mi informe", "genera mi informe"]):
        return ""
    if any(k in t for k in ["generá", "genera", "escribí", "escribe", "hacé", "hacer"]):
        return _tool("informe_semanal", {"action": "generar", "force": "true"})
    return _tool("informe_semanal", {"action": "status"})


def _handle_salud(text: str) -> str:
    """Chequeo integral: todo junto."""
    t = text.lower()
    if not any(k in t for k in ["chequeo", "todo listo", "todo bien", "auditoría",
                                "auditoria", "revisá todo", "revisa todo",
                                "diagnóstico completo", "diagnostico completo"]):
        return ""
    return _memoria_status()


# ── Handler principal ─────────────────────────────────────────────────────────


def handle_memoria(text: str, player=None, **kwargs) -> str:
    """Memoria: fragmento de autoconocimiento y memoria total de ERIS."""
    from core.tracer import get_tracer
    tracer = get_tracer()
    t0 = time.perf_counter()
    text = (text or "").strip()

    def _done(result: str) -> str:
        elapsed = time.perf_counter() - t0
        tracer.trace_handoff("memoria", text, result, elapsed)
        return result

    if not text:
        return _done("Memoria espera una tarea. Probá: 'qué sabés de la fábrica', "
                     "'qué hablamos la última vez', 'contame tu modelo del mundo', "
                     "'cómo estás de auto-mejora', 'generá el informe semanal'.")

    t = text.lower()
    if any(k in t for k in ["estado", "activo", "health", "capabilities",
                            "qué podés", "que podes", "qué sabes", "que sabes",
                            "help", "ayuda", "todo activo", "reporte"]):
        return _done(_memoria_status())

    for name, fn, guard in [
        ("salud", _handle_salud, None),
        ("recall", _handle_recall, None),
        ("sesiones", _handle_sesiones, None),
        ("mundo", _handle_mundo, None),
        ("auto", _handle_auto, None),
        ("proactivo", _handle_proactivo, None),
        ("informe", _handle_informe, None),
    ]:
        try:
            r = fn(text)
            if r:
                return _done(r)
        except Exception as e:
            return _done(f"Error en dominio {name}: {e}")

    return _done(
        "Memoria (fragmento de autoconocimiento de Eris) — dominios: memoria "
        "total RAG ('qué sabés de X'), sesiones ('qué hablamos'), modelo del "
        "mundo ('contame tu mundo'), auto-mejora ('cómo estás'), contexto "
        "proactivo y informe semanal. Decime 'memoria + lo que querés' o "
        "'estado' para ver todo activo."
    )


# ── Tool expuesta a Eris ──────────────────────────────────────────────────────


def memoria(parameters: dict | None = None, player=None) -> str:
    """Tool 'memoria': delega una tarea al fragmento de memoria de Eris.
    Acciones: status (todo activo), recall (query=<tema>), sesiones, mundo,
    auto_mejora, informe (con force), task (task=<texto libre>)."""
    parameters = parameters or {}
    action = (parameters.get("action") or "task").lower()
    task = (parameters.get("task") or "").strip()

    if action in ("status", "estado", "activo", "health"):
        return _memoria_status()
    if action in ("help", "ayuda", "list"):
        return handle_memoria("ayuda")
    if action in ("recall", "recuerdo", "buscar"):
        query = (parameters.get("query") or "").strip()
        if not query:
            return "Memoria necesita 'query' para buscar en su memoria total."
        return _tool("rag_engine", {"action": "recall", "query": query, "top_k": 3})
    if action == "sesiones":
        return _tool("sesiones", {"action": "reciente", "n": 3})
    if action == "mundo":
        return _tool("world_model", {"action": "get"})
    if action in ("auto_mejora", "auto"):
        return _tool("auto_mejora", {"action": "estado"})
    if action in ("informe", "semanal"):
        force = str(parameters.get("force", "false")).lower() in ("true", "1")
        return _tool("informe_semanal", {"action": "generar" if force else "status",
                                         "force": "true" if force else "false"})
    if action in ("task", "run", "dispatch", "delegar"):
        if not task:
            return "Memoria necesita 'task': una descripción de lo que querés recordar."
        return handle_memoria(task, player=player)
    return ("Tool memoria (fragmento de autoconocimiento de Eris). Acciones: "
            "status, recall (query=...), sesiones, mundo, auto_mejora, informe, "
            "task. Ej: {action:'recall', query:'qué aprendí de la fábrica'}.")