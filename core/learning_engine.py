# -*- coding: utf-8 -*-
"""core/learning_engine.py — MOTOR DE APRENDIZAJE CONTINUO de ERIS.

Ciclo: INVESTIGAR → ESTUDIAR → CRISTALIZAR.
  1. INVESTIGAR: delega al radar del ecosistema (papers arXiv + repos GitHub).
  2. ESTUDIAR:   aprende un video (aprendizaje_videos) si la tool existe, y
                 sintetiza el material en una lección aplicable.
  3. CRISTALIZAR: guarda el conocimiento en skills/evolution_learning/ (skill
                 markdown reutilizable), indexa en RAG y deja una novedad en
                 todo_yo para que Eris SEPA que aprendió.

Persistencia:
  - memory/learning_engine.json   (estado: ciclos, temas estudiados, skills)
  - skills/evolution_learning/*.md (skills cristalizadas)
  - data/knowledge/learning_engine/*.md (material de estudio)

Integración:
  - `study_cycle()` lo llama `core/self_evolution.run_evolution_tick` (cada 6
    ticks del loop de evolución continua).
  - `learning_engine` es el alias expuesto como tool que consume
    `core/action_imports.py`.

Todo degrada elegante: sin red o sin proveedor LLM, el ciclo devuelve un
resumen textual y no crashea el tick.
"""
from __future__ import annotations

import json
import re
import threading
from datetime import datetime
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_MEM = _BASE / "memory"
_STATE_FILE = _MEM / "learning_engine.json"
_SKILLS_DIR = _BASE / "skills" / "evolution_learning"
_KNOW_DIR = _BASE / "data" / "knowledge" / "learning_engine"
_lock = threading.Lock()

# Temas rotatorios del ciclo de estudio (fuera del radar puro de evolución).
_TEMAS = [
    "técnicas de razonamiento en cadena (chain-of-thought) modernas",
    "arquitecturas de memoria para agentes autónomos",
    "patrones de diseño de herramientas para LLM",
    "evaluación de agentes: benchmarks y métricas",
    "sistemas RAG híbridos (vector + keyword + grafo)",
    "seguridad y sandboxing en ejecución de código por IA",
    "optimización de contexto y ventana de tokens",
    "aprendizaje por refuerzo aplicado a agentes",
]


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _load_state() -> dict:
    if _STATE_FILE.exists():
        try:
            data = json.loads(_STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return {
        "created": datetime.now().isoformat(),
        "cycles": 0,
        "temas_estudiados": [],
        "skills": [],
        "videos": [],
        "historial": [],
    }


def _save_state(state: dict):
    try:
        _MEM.mkdir(parents=True, exist_ok=True)
        _STATE_FILE.write_text(
            json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def _notify(texto: str):
    try:
        from core.todo_yo import registrar_novedad
        registrar_novedad(texto)
    except Exception:
        pass


def _tool(name: str, params: dict) -> str:
    """Invoca una tool de Eris por nombre; '' si no existe o falla."""
    try:
        from core.tool_registry import get_tool
        return str(get_tool(name)(params) or "")
    except Exception:
        return ""


def _llm(prompt: str, system: str = "") -> str:
    try:
        from core.model_router import quick_chat
        return (quick_chat(prompt, system=system, task="agent") or "").strip()
    except Exception:
        return ""


# ── 1. INVESTIGAR ─────────────────────────────────────────────────────────────

def _formatear_fuentes(items: list, titulo: str) -> str:
    """Formatea papers/repos de core.research_channels a texto plano."""
    lineas = []
    for it in (items or [])[:6]:
        t = str(it.get("titulo") or "").strip()
        u = str(it.get("url") or "").strip()
        if t:
            lineas.append(f"• {t} — {u}")
    if not lineas:
        return ""
    return titulo + "\n" + "\n".join(lineas)


def _investigar(tema: str) -> str:
    """Radar del tema: papers + repos (core.research_channels) + deep_research, fallback web_search.

    FIX 2026-10-15 (auditoría M2): antes usaba las tools `paper_search`/
    `repo_discovery`, que NO existen (sus imports caían a `None`) → el paso
    quedaba mudo. Ahora usa `core.research_channels`, que es su reemplazo real.
    """
    partes = []
    try:
        from core import research_channels as rc
        fp = _formatear_fuentes(rc.buscar_papers(tema, limite=4), "📄 PAPERS (arXiv):")
        fr = _formatear_fuentes(rc.descubrir_repos(tema, limite=4), "📦 REPOS (GitHub):")
        if fp:
            partes.append(fp[:1400])
        if fr:
            partes.append(fr[:1400])
    except Exception:
        pass
    for tname, params in (
        ("deep_research", {"action": "research", "topic": tema, "query": tema}),
    ):
        r = _tool(tname, params)
        if r and "Error" not in r[:30] and len(r.strip()) > 20:
            partes.append(r[:1400])
    if not partes:
        r = _tool("web_search", {"action": "search", "query": tema, "num_results": 4})
        if r and "Error" not in r[:30]:
            partes.append(r[:1400])
    return "\n---\n".join(partes)


# ── 2. ESTUDIAR ───────────────────────────────────────────────────────────────

def _estudiar_video() -> dict:
    """Aprende de un video vía la tool aprendizaje_videos (si existe)."""
    out = _tool("aprendizaje_videos", {"action": "listar"})
    if not out or "Error" in out[:30]:
        return {}
    return {"listado": out[:600]}


def _sintetizar(tema: str, material: str) -> str:
    """Convierte el material crudo en una lección aplicable a ERIS."""
    prompt = (
        "Sos ERIS estudiando para mejorar. Tema: {tema}.\n"
        "Material crudo:\n{material}\n\n"
        "Escribí una lección APLICABLE (máx 12 líneas) con:\n"
        "- Qué es lo importante.\n"
        "- Cómo lo aplico en mi propio código/agentes.\n"
        "- Un paso concreto para probarlo."
    ).format(tema=tema, material=(material or "(sin material de red)")[:1800])
    out = _llm(prompt)
    if out:
        return out[:2000]
    return ("# {tema}\n\nMaterial estudiado (sin síntesis LLM disponible):\n"
            "{mat}").format(tema=tema, mat=(material or "(vacío)")[:800])


# ── 3. CRISTALIZAR ────────────────────────────────────────────────────────────

def _safe_name(texto: str, maxlen: int = 50) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_"
                   for c in texto[:maxlen]).strip("_") or "leccion"


def _cristalizar(tema: str, leccion: str) -> str:
    """Guarda la lección como skill markdown, indexa en RAG y avisa."""
    _SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    name = _safe_name(tema)
    skill_file = _SKILLS_DIR / "{}_SKILL.md".format(name)
    contenido = (
        "---\nname: evolution-{name}\ndescription: Lección de evolución continua "
        "aprendida por ERIS sobre {tema}\n---\n\n{leccion}\n"
    ).format(name=name, tema=tema, leccion=leccion)
    try:
        skill_file.write_text(contenido, encoding="utf-8")
    except Exception:
        pass

    # Material de estudio en data/knowledge
    try:
        _KNOW_DIR.mkdir(parents=True, exist_ok=True)
        (_KNOW_DIR / "{}_estudio.md".format(name)).write_text(
            "# {}\n\nAprendido: {}\n\n{}".format(tema, _now(), leccion),
            encoding="utf-8")
    except Exception:
        pass

    # Indexar en RAG (si el pipeline está disponible)
    try:
        from core.rag_pipeline import index_document
        index_document(str(skill_file))
    except Exception:
        pass

    return str(skill_file)


def study_cycle(tema: str | None = None) -> str:
    """Un ciclo completo de estudio continuo: investigar → estudiar → cristalizar.

    Devuelve un resumen textual (lo consume run_evolution_tick).
    """
    with _lock:
        state = _load_state()
        n = int(state.get("cycles", 0))
        if tema is None:
            tema = _TEMAS[n % len(_TEMAS)]
        state["cycles"] = n + 1

        material = _investigar(tema)
        video = _estudiar_video()
        leccion = _sintetizar(tema, material)
        skill_path = _cristalizar(tema, leccion)

        if tema not in state["temas_estudiados"]:
            state["temas_estudiados"].append(tema)
        state["temas_estudiados"] = state["temas_estudiados"][-50:]
        state["skills"].append({"tema": tema, "skill": skill_path, "fecha": _now()})
        state["skills"] = state["skills"][-50:]
        if video:
            state["videos"].append({"tema": tema, "info": video.get("listado", "")[:200],
                                    "fecha": _now()})
            state["videos"] = state["videos"][-30:]
        state["historial"].append({
            "ciclo": state["cycles"], "tema": tema,
            "tuvo_material": bool(material), "skill": skill_path, "fecha": _now()})
        state["historial"] = state["historial"][-50:]
        _save_state(state)

    resumen = ("📚 Ciclo de estudio #{} — «{}»: {} · skill cristalizada.".format(
        state["cycles"], tema,
        "material investigado" if material else "sin material de red (modo local)"))
    _notify("Estudié «{}» y cristalizé una lección (skill) en mi evolución.".format(tema))
    return resumen


def learning_engine(parameters: dict = None, player=None) -> str:
    """Tool `learning_engine`: corre un ciclo o reporta estado/skills."""
    p = parameters or {}
    action = p.get("action", "cycle")
    if action in ("cycle", "estudiar", "run"):
        tema = p.get("tema") or None
        return study_cycle(tema)
    if action in ("status", "estado"):
        state = _load_state()
        return json.dumps({
            "cycles": state.get("cycles", 0),
            "temas_estudiados": len(state.get("temas_estudiados", [])),
            "skills_cristalizadas": len(state.get("skills", [])),
            "videos": len(state.get("videos", [])),
        }, indent=2, ensure_ascii=False)
    if action in ("skills", "lecciones"):
        state = _load_state()
        skills = state.get("skills", [])[-10:]
        if not skills:
            return "Sin skills cristalizadas todavía."
        return "\n".join("· {t} → {s}".format(t=x.get("tema", "")[:50],
                                              s=x.get("skill", "")) for x in skills)
    if action in ("historial", "history"):
        state = _load_state()
        hist = state.get("historial", [])[-10:]
        if not hist:
            return "Sin historial de estudio."
        return "\n".join("#{c} {t} ({f})".format(c=h.get("ciclo"),
                                                 t=h.get("tema", "")[:50],
                                                 f=h.get("fecha", "")) for h in hist)
    return "Acciones: cycle [tema=] | status | skills | historial"


if __name__ == "__main__":
    print(study_cycle())
    print(learning_engine({"action": "status"}))
