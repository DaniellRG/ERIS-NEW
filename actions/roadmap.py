# -*- coding: utf-8 -*-
"""
actions/roadmap.py — ROADMAP DE MADUREZ (Command Deck de mejora continua).

Checklist de las ~15 areas epicas de ERIS con score 0-100. Reporta el estado
y detecta cuando se alcanza el PLATEAU: el momento en que las unicas mejoras
restantes dependen de tecnologia nueva (modelos, APIs, hardware, workflows
nuevos del usuario) y no queda nada estrutural interno.

Acciones de la tool:
  show    (default) tabla completa + veredicto
  plateau veredicto solamente
  update  area=<id> score=<0-100> [note=...]
  init    recrea data/roadmap.json con los defaults
CLI: python -m actions.roadmap [show|plateau|update area=... score=N]
"""
import json
import sys
from pathlib import Path
from datetime import datetime

_BASE = Path(__file__).resolve().parent.parent
_DECK = _BASE / "data" / "roadmap.json"

DEFAULT_AREAS = [
    {
        "id": "voz",
        "name": "Voz (STT/TTS)",
        "score": 92,
        "note": "Fish/edge/vosk, voz personalizada, TTS en tiempo real. Local-first.",
        "internal_next": [],
        "external_next": ["TTS local SOTA sin cuota", "clon de voz mas natural"],
    },
    {
        "id": "vision",
        "name": "Vision (camara/OCR/screens)",
        "score": 85,
        "note": "Cadena local_first minicpm-v -> Gemini -> OpenRouter; OCR; guardia continua.",
        "internal_next": ["pulir fallback OpenRouter"],
        "external_next": ["modelo vision local mas potente"],
    },
    {
        "id": "memoria",
        "name": "Memoria (NeuroSpheres/RAG)",
        "score": 82,
        "note": "Semantica + episodica + NeuroSpheres. WARN de consistencia a resolver.",
        "internal_next": ["estabilizar conteo NeuroSpheres", "RAG sobre vault raw/wiki"],
        "external_next": [],
    },
    {
        "id": "agentes",
        "name": "Agentes verticales (9)",
        "score": 88,
        "note": "Router con 9 handlers (corre, estudio, seg, etc).",
        "internal_next": ["afinar enrutamiento"],
        "external_next": ["otro agente vertical cuando tu vida cambie"],
    },
    {
        "id": "skills",
        "name": "Skills (39)",
        "score": 86,
        "note": "21 builtin + 18 user_created, bajo demanda; voz-humana anti-slop.",
        "internal_next": [],
        "external_next": ["skills de workflows nuevos tuyos"],
    },
    {
        "id": "cli",
        "name": "CLI (sessions)",
        "score": 80,
        "note": "Sesiones con nombre, streaming, /status.",
        "internal_next": ["completar alias y autocompletado"],
        "external_next": [],
    },
    {
        "id": "gui",
        "name": "GUI / HUD",
        "score": 82,
        "note": "Orbe, cara, themes, terminal, command deck (Ctrl+D).",
        "internal_next": ["dashboard de datos (metricas/agenda en HUD)"],
        "external_next": [],
    },
    {
        "id": "vault",
        "name": "Vault (raw/wiki/outputs)",
        "score": 84,
        "note": "Layout unificado; write->raw por defecto; promote manual.",
        "internal_next": ["auto-promote raw->wiki", "indexacion RAG del vault"],
        "external_next": [],
    },
    {
        "id": "autonomia",
        "name": "Autonomia (schedulers/backups)",
        "score": 85,
        "note": "Auto-backup 6h, auto-eval post-sesion, tareas programadas.",
        "internal_next": [],
        "external_next": ["servicio de Windows al arranque (NSSM)"],
    },
    {
        "id": "seguridad",
        "name": "Seguridad",
        "score": 84,
        "note": "Escudo, firewall, encriptacion, OSINT, permisos.",
        "internal_next": [],
        "external_next": [],
    },
    {
        "id": "confiabilidad",
        "name": "Confiabilidad / tests",
        "score": 80,
        "note": "test_all 55 PASS; tareas resilientes; seguimiento de errores.",
        "internal_next": ["cerrar WARNs de test_all", "bajar tasas de error"],
        "external_next": [],
    },
    {
        "id": "busqueda",
        "name": "Busqueda / investigacion",
        "score": 78,
        "note": "web_search, deep_research, DuckDuckGo. Bloqueos externos.",
        "internal_next": [],
        "external_next": ["Google CAPTCHA", "yt-dlp 403", "mejores motores"],
    },
    {
        "id": "domotica",
        "name": "PC control / domotica",
        "score": 72,
        "note": "Control de PC, monitores, celular limitado.",
        "internal_next": ["pulir integracion celular"],
        "external_next": ["hardware home devices"],
    },
    {
        "id": "aprendizaje",
        "name": "Aprendizaje continuo",
        "score": 82,
        "note": "evaluate_session, daily digest, learn_from_sessions.",
        "internal_next": [],
        "external_next": [],
    },
    {
        "id": "privacidad",
        "name": "Privacidad / local-first",
        "score": 90,
        "note": "Ollama default, vision/STT locales, vault en markdown.",
        "internal_next": [],
        "external_next": [],
    },
]

_PLATEAU_MIN = 80


def _load() -> dict:
    if _DECK.exists():
        try:
            return json.loads(_DECK.read_text(encoding="utf-8"))
        except Exception:
            pass
    return _init_data()


def _init_data() -> dict:
    data = {
        "meta": {
            "created": datetime.now().isoformat(),
            "updated": datetime.now().isoformat(),
            "rule": ("PLATEAU cuando: score minimo >= 80 y no quedan items "
                     "internos pendientes. Si solo quedan items externos "
                     "(modelos/APIs/hardware/workflows nuevos) -> Fase 3."),
        },
        "areas": DEFAULT_AREAS,
    }
    _save(data)
    return data


def _save(data: dict):
    try:
        _DECK.parent.mkdir(parents=True, exist_ok=True)
        _DECK.write_text(json.dumps(data, indent=2, ensure_ascii=False),
                         encoding="utf-8")
    except Exception:
        pass


def _verdict(data: dict) -> dict:
    areas = data["areas"]
    scores = [a["score"] for a in areas]
    avg = round(sum(scores) / len(scores), 1) if scores else 0.0
    mn = min(scores) if scores else 0
    internal = sum(len(a.get("internal_next", [])) for a in areas)
    external = sum(len(a.get("external_next", [])) for a in areas)

    if mn >= _PLATEAU_MIN and internal == 0:
        stage = "PLATEAU"
        msg = ("Sin mejoras internas estructurales. Lo unico que la mueve es "
               "tecnologia nueva (Fase 3): modelos, APIs, hardware o tus "
               "workflows nuevos.")
    elif internal <= 2:
        stage = "CASI PLATEAU"
        msg = f"Quedan {internal} mejoras internas chicas; el resto ya es Fase 3."
    else:
        stage = "EN CURSO"
        msg = "Todavia queda trabajo interno estructurado listado en internal_next."
    return {
        "stage": stage, "avg": avg, "min": mn,
        "internal": internal, "external": external, "msg": msg,
    }


def _render_show(data: dict, v: dict) -> str:
    lines = [
        "ROADMAP DE MADUREZ ERIS",
        f"  Promedio: {v['avg']}/100  |  Min: {v['min']}  |  "
        f"Pendientes internos: {v['internal']}  |  externos (Fase 3): {v['external']}",
        f"  VEREDICTO: {v['stage']} — {v['msg']}",
        "",
    ]
    for a in data["areas"]:
        bar = "█" * int(a["score"] // 10) + "░" * (10 - int(a["score"] // 10))
        lines.append(f"  {a['score']:>3} {bar} {a['id']:<14} {a['name']}")
    lines.append("")
    for a in data["areas"]:
        if a.get("internal_next"):
            lines.append(f"  [{a['id']}] INTERNO: {'; '.join(a['internal_next'])}")
    for a in data["areas"]:
        if a.get("external_next"):
            lines.append(f"  [{a['id']}] FASE 3: {'; '.join(a['external_next'])}")
    return "\n".join(lines)


def roadmap(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = str(params.get("action", "show")).strip().lower()
    data = _load()

    if action in ("update", "set"):
        area = str(params.get("area", "")).strip().lower()
        score = params.get("score")
        note = str(params.get("note", ""))
        try:
            score = int(score)
        except (TypeError, ValueError):
            return "Error: 'score' debe ser un entero 0-100."
        if not (0 <= score <= 100):
            return "Error: 'score' debe estar entre 0 y 100."
        for a in data["areas"]:
            if a["id"] == area:
                a["score"] = score
                if note:
                    a["note"] = note
                data["meta"]["updated"] = datetime.now().isoformat()
                _save(data)
                v = _verdict(data)
                return (f"Area '{area}' actualizada a {score}. "
                        f"Promedio {v['avg']}. Veredicto: {v['stage']}.")
        return (f"Area '{area}' no valida. Disponibles: "
                + ", ".join(a["id"] for a in data["areas"]))
    elif action in ("plateau", "verdict", "status"):
        v = _verdict(data)
        return (f"ROADMAP: {v['stage']} — {v['msg']} "
                f"(promedio {v['avg']}, min {v['min']}, "
                f"internos {v['internal']}, Fase3 {v['external']}).")
    elif action == "init":
        data = _init_data()
        return "Roadmap reiniciado con defaults."
    elif action in ("show", "list", ""):
        v = _verdict(data)
        return _render_show(data, v)

    return ("Acciones: show | update (area, score, note) | plateau | init")


if __name__ == "__main__":
    args = sys.argv[1:]
    params = {}
    for a in args:
        if "=" in a:
            k, _, val = a.partition("=")
            params[k.strip()] = val.strip()
        else:
            params.setdefault("action", a.strip())
    print(roadmap(params))