# -*- coding: utf-8 -*-
"""
daily_digest.py — Memoria de largo plazo de ERIS.

Genera un "digest" diario (data/daily_reports/YYYY-MM-DD.md) que consolida qué
pasó, qué se hizo, qué se aprendió y qué falló cada día. Se inyecta en el prompt
para que ERIS "recuerde" el día sin depender del contexto corto de la sesión, y
la tool `daily_digest` permite al usuario pedir "¿qué hiciste hoy?" por voz.
"""
from __future__ import annotations

import json
import threading
from datetime import date, datetime
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_DIGEST_DIR = _BASE / "data" / "daily_reports"
_LOCK = threading.RLock()

_CACHE: dict = {"path": None, "mtime": 0.0, "text": ""}


def _date_str(d: date) -> str:
    return d.isoformat()


def _today_file(d: date = None) -> Path:
    _DIGEST_DIR.mkdir(parents=True, exist_ok=True)
    return _DIGEST_DIR / f"{_date_str(d or date.today())}.md"


def _load_json(path: Path) -> object:
    try:
        if path.exists():
            return json.loads(path.read_text("utf-8"))
    except Exception:
        pass
    return None


def _filter_today(items: object, date_str: str, time_keys=("time", "timestamp", "completed", "updated_at", "datetime")) -> list:
    """Filtra una lista/dict de items cuya clave de tiempo cae hoy."""
    if not items:
        return []
    out = []
    for it in items:
        if not isinstance(it, dict):
            continue
        for k in time_keys:
            t = str(it.get(k, ""))
            if t.startswith(date_str):
                out.append(it)
                break
    return out


def _collect_today(d: date = None) -> dict:
    ds = _date_str(d or date.today())
    today = {}

    tasks = _load_json(_BASE / "data" / "completed_tasks.json")
    today["tasks"] = _filter_today(list(tasks.values()) if isinstance(tasks, dict) else tasks, ds)

    errors = _load_json(_BASE / "data" / "self_healing_errors.json")
    today["errors"] = _filter_today(errors if isinstance(errors, list) else [], ds)

    learning = _load_json(_BASE / "data" / "self_learning_log.json")
    today["learning"] = _filter_today(learning if isinstance(learning, list) else [], ds)

    idle = _load_json(_BASE / "data" / "idle_learning.json")
    topics = []
    if isinstance(idle, dict):
        topics = _filter_today(idle.get("topics_learned", []), ds, ("timestamp", "time", "datetime"))
        today["idle_topics"] = len(topics)
        today["idle_names"] = [t.get("topic", t.get("title", t.get("summary", ""))) for t in topics[:5]
                               if isinstance(t, dict)]
    else:
        today["idle_topics"] = 0
        today["idle_names"] = []

    evals = _load_json(_BASE / "memory" / "self_evaluation.json")
    if isinstance(evals, list):
        ev = _filter_today(evals, ds)
        scores = [float(e.get("overall_score", 0) or 0) for e in ev]
        today["eval_count"] = len(scores)
        today["eval_avg"] = round(sum(scores) / len(scores), 2) if scores else None
    else:
        today["eval_count"] = 0
        today["eval_avg"] = None

    try:
        from actions.eris_db import convo_recent
        rows = convo_recent(200) or []
        today["convo_count"] = sum(1 for r in rows if str(r.get("time", "")).startswith(ds))
    except Exception:
        today["convo_count"] = 0

    try:
        from actions.eris_db import episodic_recent
        eps = episodic_recent(50) or []
        today["events"] = [e.get("event", "")[:160] for e in eps
                           if isinstance(e, dict) and str(e.get("datetime", "")).startswith(ds)]
    except Exception:
        today["events"] = []

    rel = _load_json(_BASE / "data" / "relationship.json")
    if isinstance(rel, dict):
        today["moments"] = _filter_today(rel.get("important_moments", []), ds, ("timestamp", "datetime"))
    else:
        today["moments"] = []

    return today


def _fmt(d: date) -> str:
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
             "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    return f"{d.day} de {meses[d.month - 1]} de {d.year}"


def generate_digest(d: date = None) -> str:
    """Genera (y guarda) el digest del día. Devuelve el texto markdown."""
    d = d or date.today()
    ds = _date_str(d)
    data = _collect_today(d)

    lines = [f"# Digest — {_fmt(d)}", ""]

    if data["convo_count"]:
        lines.append(f"## Conversación")
        lines.append(f"Se registraron {data['convo_count']} mensajes de la charla de hoy.")
        lines.append("")

    if data["tasks"]:
        tools = {}
        for t in data["tasks"]:
            tools[t.get("tool", "?")] = tools.get(t.get("tool", "?"), 0) + 1
        lines.append("## Tareas realizadas")
        lines.append(f"- Total: {len(data['tasks'])}")
        for name, n in sorted(tools.items()):
            lines.append(f"  - {name}: {n}")
        lines.append("")

    if data["moments"]:
        lines.append("## Momentos importantes")
        for m in data["moments"][-5:]:
            lines.append(f"- {m.get('text', '')[:200]}")
        lines.append("")

    if data["events"]:
        lines.append("## Eventos")
        for e in data["events"][-5:]:
            lines.append(f"- {e}")
        lines.append("")

    if data["idle_topics"]:
        lines.append("## Lo que aprendí")
        lines.append(f"- {data['idle_topics']} temas investigados en mi tiempo libre.")
        for name in data["idle_names"]:
            if name:
                lines.append(f"  - {str(name)[:120]}")
        lines.append("")

    if data["learning"]:
        lines.append("## Lecciones del día")
        for lr in data["learning"][-5:]:
            lines.append(f"- {lr.get('action', '')}: {str(lr.get('detail', ''))[:150]}")
        lines.append("")

    if data["errors"]:
        by_type = {}
        for e in data["errors"]:
            t = e.get("type", "unknown")
            by_type[t] = by_type.get(t, 0) + 1
        lines.append("## Errores del día")
        lines.append(f"- Total: {len(data['errors'])}")
        for t, n in sorted(by_type.items(), key=lambda x: -x[1])[:5]:
            lines.append(f"  - {t}: {n}")
        lines.append("")

    if data["eval_avg"] is not None:
        lines.append("## Autoevaluación")
        lines.append(f"- {data['eval_count']} evaluaciones, promedio {data['eval_avg']:.2f}")
        lines.append("")

    text = "\n".join(lines)
    f = _today_file(d)
    try:
        f.write_text(text, "utf-8")
    except Exception:
        pass
    return text


def _read_cached(f: Path) -> str:
    try:
        mtime = f.stat().st_mtime
    except Exception:
        return ""
    if _CACHE["path"] == str(f) and abs(_CACHE["mtime"] - mtime) < 1e-6 and _CACHE["text"]:
        return _CACHE["text"]
    try:
        text = f.read_text("utf-8")
    except Exception:
        return ""
    _CACHE.update(path=str(f), mtime=mtime, text=text)
    return text


def _recent_digest_paths(n: int = 3) -> list:
    if not _DIGEST_DIR.exists():
        return []
    files = sorted(_DIGEST_DIR.glob("*.md"), reverse=True)
    return files[:n]


def get_latest_digest(n: int = 3) -> list:
    """Devuelve lista de (fecha, texto) de los digests más recientes existentes."""
    out = []
    for f in _recent_digest_paths(n):
        out.append((f.stem, _read_cached(f)))
    return out


def inject_digest(max_chars: int = 900) -> str:
    """Bloque [RESUMEN RECIENTE] para inyectar en el prompt (memoria de días pasados)."""
    out = []
    budget = max_chars
    for f in _recent_digest_paths(2):
        if not budget:
            break
        text = _read_cached(f)
        if not text:
            continue
        short = " / ".join(line.strip() for line in text.splitlines()
                           if line.strip() and not line.startswith("#"))
        if not short:
            continue
        block = f"[{f.stem}] {short[:budget]}"
        out.append(block)
        budget -= len(block) + 20
    if not out:
        return ""
    return "[RESUMEN RECIENTE]\n" + "\n".join(out)


def daily_digest_tool(parameters: dict = None, player=None) -> str:
    """Tool: ver/generar el digest diario. Acciones: today, recent, generate."""
    params = parameters or {}
    action = (params.get("action") or "today").strip().lower()

    with _LOCK:
        if action in ("today", "hoy", "ver"):
            d = date.today()
            text = generate_digest(d)
            lines = [f"── DIGEST DE HOY ({_fmt(d)}) ──"]
            lines.extend(text.splitlines())
            return "\n".join(lines)

        elif action in ("recent", "ultimos"):
            digests = get_latest_digest(3)
            if not digests:
                return "Todavía no hay digests guardados."
            lines = ["── DIGESTS RECIENTES ──"]
            for ds, text in digests:
                lines.append(f"\n## {ds}")
                lines.extend(text.splitlines()[:14])
            return "\n".join(lines)

        elif action in ("generate", "generar", "forzar"):
            d = date.today()
            text = generate_digest(d)
            return f"Digest de hoy regenerado ({_today_file(d).name}):\n{text}"

        return (
            "Acciones de digest diario:\n"
            "- today: ver el digest de hoy (lo genera si no existe)\n"
            "- recent: ver los últimos digests\n"
            "- generate: regenerar el de hoy"
        )
