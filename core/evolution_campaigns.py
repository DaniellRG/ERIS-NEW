# -*- coding: utf-8 -*-
"""core/evolution_campaigns.py — CAMPAÑAS DE EVOLUCIÓN SINERGÉTICA de ERIS.

Radar del ecosistema AGI: papers arXiv + repos GitHub, con DOBLE REVISIÓN y
puntuación ELO (modelo Darwin Gödel Machine + Ouroboros). Cada campaña corre
sobre un tema ROTATORIO, produce ideas candidatas, las critica dos veces
(propuesta → crítica → refinamiento) y rankea las supervivientes por ELO.

Persistencia:
  - data/evolution_campaigns.json   (estado estructurado: campañas, temas,
                                     ideas con ELO, historial)
  - data/evolution_campaigns.log    (log legible append-only)

Integración:
  - `run_campaign()` lo llama `core/self_evolution.run_evolution_tick` (cada 3
    ticks del loop de evolución continua).
  - `evolve_campaigns` es el alias expuesto como tool (`evolution_campaigns`)
    que consume `core/action_imports.py`.

Todas las dependencias externas (web, LLM) están envueltas en try/except: si
no hay red o proveedor, la campaña degrada a un resultado textual, nunca
crashea el tick de evolución.
"""
from __future__ import annotations

import json
import random
import re
import threading
from datetime import datetime
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_DATA = _BASE / "data"
_STATE_FILE = _DATA / "evolution_campaigns.json"
_LOG_FILE = _DATA / "evolution_campaigns.log"
_lock = threading.Lock()

# Temas rotatorios del radar AGI (el ecosistema que Eris vigila).
_TEMAS = [
    "razonamiento y planificación en agentes LLM",
    "memoria de largo plazo y RAG avanzado en agentes",
    "auto-mejora y self-modification de agentes (Darwin Gödel Machine)",
    "orquestación multi-agente y protocolos de comunicación",
    "evaluación y verificación de agentes autónomos",
    "herramientas y function-calling en modelos frontier",
    "aprendizaje continuo y catastrophic forgetting",
    "sistemas de agentes con sandbox y seguridad",
    "meta-aprendizaje y optimización de prompts",
    "world models y simulación para agentes",
]

# ELO base y factor K (estilo torneo, modelo Darwin Gödel Machine + Ouroboros).
_ELO_BASE = 1200.0
_ELO_K = 32.0


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
        "campaigns": 0,
        "tema_actual": None,
        "historial": [],
        "ideas": [],
        "ranking": [],
    }


def _save_state(state: dict):
    try:
        _DATA.mkdir(parents=True, exist_ok=True)
        _STATE_FILE.write_text(
            json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def _log(msg: str):
    try:
        _DATA.mkdir(parents=True, exist_ok=True)
        line = "[{}] {}\n".format(_now(), msg)
        with open(str(_LOG_FILE), "a", encoding="utf-8") as f:
            f.write(line)
        # Rotación si supera 250KB
        if _LOG_FILE.stat().st_size > 250 * 1024:
            rot = _LOG_FILE.with_name(_LOG_FILE.name + ".old")
            if rot.exists():
                rot.unlink()
            _LOG_FILE.rename(rot)
    except Exception:
        pass


def _notify(texto: str):
    """Deja constancia en todo_yo (novedad) para que Eris sepa lo que logró."""
    try:
        from core.todo_yo import registrar_novedad
        registrar_novedad(texto)
    except Exception:
        pass


# ── LLM helper ────────────────────────────────────────────────────────────────

def _llm(prompt: str, system: str = "") -> str:
    """Una pasada de texto con el mejor proveedor disponible (o '' si falla)."""
    try:
        from core.model_router import quick_chat
        out = quick_chat(prompt, system=system, task="agent")
        return (out or "").strip()
    except Exception as e:
        _log("LLM no disponible: {}".format(str(e)[:80]))
        return ""


# ── Radar: papers + repos ─────────────────────────────────────────────────────

def _radar_tema(tema: str) -> dict:
    """Busca papers y repos sobre el tema vía core.research_channels (canales
    reales: arXiv + GitHub por DDGS); si no hay red, cae a web_search; si no,
    devuelve vacío (degrada elegante).
    """
    papers, repos, fuentes = [], [], []

    # 1. Canales reales de investigación (auditoría 2026-10-15, M2: antes
    #    despachaba las tools paper_search/repo_discovery, que NO existen).
    try:
        from core import research_channels as rc
        for key, items in (("papers", rc.buscar_papers(tema, limite=5)),
                           ("repos", rc.descubrir_repos(tema, limite=5))):
            txt = "\n".join(f"• {x.get('titulo', '')} — {x.get('url', '')}"
                            for x in (items or []) if x.get("titulo"))
            if len(txt.strip()) > 20:
                (papers if key == "papers" else repos).append(txt[:1500])
                fuentes.append(key)
    except Exception:
        pass

    # 2. Fallback: web_search directo
    if not papers and not repos:
        try:
            from core.tool_registry import get_tool
            r = str(get_tool("web_search")(
                {"action": "search", "query": tema + " arXiv paper github repo", "num_results": 5}) or "")
            if r and "Error" not in r[:30]:
                papers.append(r[:1500])
                fuentes.append("web_search")
        except Exception:
            pass

    return {"papers": papers, "repos": repos, "fuentes": fuentes}


# ── Doble revisión + ELO ──────────────────────────────────────────────────────

def _generar_ideas(tema: str, contexto: str, n: int = 3) -> list:
    """Propone N ideas de mejora para Eris a partir del radar del tema."""
    prompt = (
        "Sos el motor de evolución de ERIS (una IA agéntica). Tema de la campaña: {tema}.\n"
        "Contexto del ecosistema (papers/repos):\n{ctx}\n\n"
        "Proponé exactamente {n} ideas CONCRETAS y aplicables de mejora para ERIS "
        "(código, memoria, agentes, herramientas). Una por línea, formato:\n"
        "IDEA: <título corto> | <qué hacer y por qué>"
    ).format(tema=tema, ctx=(contexto or "(sin contexto de red)")[:1800], n=n)
    out = _llm(prompt)
    ideas = []
    for line in (out or "").splitlines():
        line = line.strip()
        m = re.search(r"IDEA:\s*(.+)", line, re.I)
        if m:
            body = m.group(1).strip()
            if "|" in body:
                titulo, detalle = body.split("|", 1)
            else:
                titulo, detalle = body[:60], body
            ideas.append({"titulo": titulo.strip()[:80], "detalle": detalle.strip()[:400],
                          "origen": tema})
    if not ideas:
        # Fallback determinista: ideas basadas en el tema (no inventa resultados de red)
        ideas = [{
            "titulo": "Explorar {} en ERIS".format(tema[:50]),
            "detalle": "Revisar cómo aplicar '{}' a los módulos de ERIS y documentar hallazgos.".format(tema),
            "origen": tema,
        }]
    return ideas[:n]


def _revisar_idea(idea: dict) -> dict:
    """Revisión 1: crítica dura (¿es viable, útil, no duplica?)."""
    prompt = (
        "Sos un revisor crítico (estilo Ouroboros). Evaluá esta idea de mejora para ERIS:\n"
        "TÍTULO: {t}\nDETALLE: {d}\n\n"
        "Respondé SOLO: VEREDICTO: <aprobar|rechazar> | MOTIVO: <1 frase> | VALOR: <0-10>"
    ).format(t=idea["titulo"], d=idea["detalle"])
    out = _llm(prompt)
    aprobar = True
    valor = 5.0
    motivo = "sin revisión LLM (fallback)"
    m = re.search(r"VEREDICTO:\s*(aprobar|rechazar).*?MOTIVO:\s*(.*?)(?:\||VALOR:|$)", out or "", re.I | re.S)
    if m:
        aprobar = m.group(1).strip().lower() == "aprobar"
        motivo = m.group(2).strip()[:150]
    mv = re.search(r"VALOR:\s*([0-9]+(?:\.[0-9]+)?)", out or "")
    if mv:
        try:
            valor = max(0.0, min(10.0, float(mv.group(1))))
        except Exception:
            pass
    idea["revision_1"] = {"aprobar": aprobar, "motivo": motivo, "valor": valor}
    return idea


def _refinar_idea(idea: dict) -> dict:
    """Revisión 2: refinamiento (segunda pasada) → sube el valor si aporta."""
    prompt = (
        "Refiná esta idea de mejora para ERIS en 1-2 frases accionables (qué archivo/tool tocar):\n"
        "TÍTULO: {t}\nDETALLE: {d}\nMOTIVO DE REVISIÓN: {m}\n\n"
        "Respondé SOLO el texto refinado."
    ).format(t=idea["titulo"], d=idea["detalle"],
             m=idea.get("revision_1", {}).get("motivo", ""))
    out = _llm(prompt)
    idea["refinada"] = (out or idea["detalle"])[:500]
    return idea


def _elo_update(ranking: list, idea: dict):
    """Actualiza el ranking ELO con la idea nueva (duelo contra el campeón)."""
    valor = float(idea.get("revision_1", {}).get("valor", 5.0))
    # score normalizado 0..1 a partir del valor 0..10
    score = valor / 10.0
    champion = ranking[0] if ranking else {"titulo": "(vacío)", "elo": _ELO_BASE}
    elo_champ = float(champion.get("elo", _ELO_BASE))
    elo_new = _ELO_BASE
    # expectativa ELO
    exp_new = 1.0 / (1.0 + 10 ** ((elo_champ - elo_new) / 400.0))
    elo_new += _ELO_K * (score - exp_new)
    idea["elo"] = round(elo_new, 1)
    ranking.append({"titulo": idea["titulo"], "elo": idea["elo"],
                    "tema": idea.get("origen", ""), "fecha": _now()})
    ranking.sort(key=lambda x: x.get("elo", 0), reverse=True)
    return ranking[:20]


# ── Campaña ───────────────────────────────────────────────────────────────────

def run_campaign(tema: str | None = None) -> str:
    """Ejecuta UNA campaña de evolución sobre un tema rotatorio.

    Radar (papers+repos) → ideas → doble revisión → ELO → persistencia.
    Devuelve un resumen textual (lo consume run_evolution_tick).
    """
    with _lock:
        state = _load_state()
        n = int(state.get("campaigns", 0))
        if tema is None:
            tema = _TEMAS[n % len(_TEMAS)]
        state["campaigns"] = n + 1
        state["tema_actual"] = tema

        radar = _radar_tema(tema)
        contexto = "\n---\n".join((radar["papers"] + radar["repos"])[:3])

        ideas = _generar_ideas(tema, contexto, n=3)
        revisadas = []
        for idea in ideas:
            idea = _revisar_idea(idea)
            idea = _refinar_idea(idea)
            revisadas.append(idea)

        aprobadas = [i for i in revisadas
                     if i.get("revision_1", {}).get("aprobar", False)]
        ranking = list(state.get("ranking", []))
        for idea in aprobadas:
            ranking = _elo_update(ranking, idea)

        state["ideas"].extend(revisadas)
        state["ideas"] = state["ideas"][-100:]
        state["ranking"] = ranking
        state["historial"].append({
            "campana": state["campaigns"],
            "tema": tema,
            "fuentes": radar["fuentes"],
            "ideas": len(revisadas),
            "aprobadas": len(aprobadas),
            "mejor_elo": max((i.get("elo", 0) for i in aprobadas), default=0),
            "fecha": _now(),
        })
        state["historial"] = state["historial"][-50:]
        _save_state(state)

    mejor = aprobadas[0]["titulo"] if aprobadas else "(ninguna aprobada)"
    resumen = ("🧬 Campaña #{} — tema «{}»: {} ideas, {} aprobadas, "
               "mejor: {} (ELO {}).").format(
        state["campaigns"], tema, len(revisadas), len(aprobadas), mejor,
        max((i.get("elo", 0) for i in aprobadas), default=0))
    _log(resumen)
    _notify("Campaña de evolución #{} sobre «{}» — {} ideas revisadas.".format(
        state["campaigns"], tema, len(revisadas)))
    return resumen


def evolve_campaigns(parameters: dict = None, player=None) -> str:
    """Tool `evolution_campaigns`: corre una campaña o reporta estado/ranking."""
    p = parameters or {}
    action = p.get("action", "run")
    if action in ("run", "campaign", "campaña"):
        tema = p.get("tema") or None
        return run_campaign(tema)
    if action in ("status", "estado"):
        state = _load_state()
        lines = ["🧬 Campañas de evolución — estado",
                 "Campañas corridas: {}".format(state.get("campaigns", 0)),
                 "Tema actual: {}".format(state.get("tema_actual") or "-")]
        ranking = state.get("ranking", [])
        if ranking:
            lines.append("Top ideas por ELO:")
            for r in ranking[:5]:
                lines.append("  · [{elo}] {t} ({tema})".format(
                    elo=r.get("elo"), t=r.get("titulo", "")[:60],
                    tema=r.get("tema", "")))
        return "\n".join(lines)
    if action in ("ranking", "top"):
        state = _load_state()
        ranking = state.get("ranking", [])[:10]
        if not ranking:
            return "Sin ranking todavía. Corré una campaña."
        return "\n".join("[{elo}] {t}".format(elo=r.get("elo"),
                                              t=r.get("titulo", ""))
                         for r in ranking)
    if action in ("historial", "history", "log"):
        state = _load_state()
        hist = state.get("historial", [])[-10:]
        if not hist:
            return "Sin historial de campañas."
        return "\n".join("#{c} {t} — {i} ideas / {a} ok ({f})".format(
            c=h.get("campana"), t=h.get("tema", "")[:40], i=h.get("ideas"),
            a=h.get("aprobadas"), f=h.get("fecha", "")) for h in hist)
    return ("Acciones: run [tema=] | status | ranking | historial")


if __name__ == "__main__":
    print(run_campaign())
    print(evolve_campaigns({"action": "status"}))
