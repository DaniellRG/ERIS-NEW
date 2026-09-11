# -*- coding: utf-8 -*-
"""
ab_automated.py — A/B AUTOMÁTICO de prompts para ERIS.

Cada `ab_interval_hours` (default 24h) un daemon de main.py corre una
ronda de experimentación: genera respuestas con variantes de ESTILO usando
el modelo local (Ollama), las puntúa con heurísticas (SelfEvaluator, sin
LLM extra), registra resultados en data/prompt_ab_metrics.json (tables
de prompt_ab) y, si hay ganadora clara (>=3 tests por variante y win_rate
máximo), la persiste como estilo activo en data/prompt_ab_active.json para
que main.py la inyecte como [ESTILO ACTIVO].
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_ACTIVE_FILE = _BASE / "data" / "prompt_ab_active.json"
_LAST_FILE = _BASE / "data" / "prompt_ab_last_round.json"
_METRICS_FILE = _BASE / "data" / "prompt_ab_metrics.json"

_VARIANTS = [
    {"name": "base", "prompt": "Respondé directo: claro, cálido y accionable.", "weight": 1.0},
    {"name": "proactiva", "prompt": "Respondé proactivo: proponé al final un siguiente paso concreto.", "weight": 1.0},
    {"name": "concisa", "prompt": "Respondé muy conciso: 2-4 frases, sin rodeos ni relleno.", "weight": 1.0},
]

_FALLBACK_PROBES = [
    "Contame qué es lo más importante que aprendiste hoy.",
    "¿Cómo estás?",
    "¿Qué podrías hacer para ser más útil para mí ahora mismo?",
    "Explicame en pocas palabras la idea de 'memoria total'.",
]


def _load(path: Path, default):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def _save(path: Path, data):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def _probes() -> list[str]:
    """Fráces de prueba: intereses propios de Eris si existen, si no, base."""
    probes = []
    try:
        intereses = _load(_BASE / "memory" / "intereses.json", {})
        items = intereses.get("temas") or intereses.get("intereses") or []
        if isinstance(items, list):
            for t in items[:3]:
                name = t.get("tema") or t.get("nombre") or (str(t) if isinstance(t, str) else "")
                if name:
                    probes.append(f"Contame algo interesante sobre {name}.")
    except Exception:
        pass
    try:
        lessons = _load(_BASE / "memory" / "self_lessons.json", {})
        items = lessons.get("lecciones") or lessons.get("lessons") or []
        if isinstance(items, list):
            for l in items[:2]:
                txt = l.get("lesson") or l.get("texto") or ""
                if txt:
                    probes.append(f"Recordame esta lección y cómo me ayuda: {txt[:120]}")
    except Exception:
        pass
    return (probes[:4] + _FALLBACK_PROBES)[:5]


def get_interval_hours() -> int:
    try:
        cfg = _load(_BASE / "config" / "config.json", {})
        return int(cfg.get("ab_interval_hours", 24))
    except Exception:
        return 24


def _due() -> bool:
    cfg = _load(_BASE / "config" / "config.json", {})
    interval_h = int(cfg.get("ab_interval_hours", 24))
    last = _load(_LAST_FILE, {"ts": 0}).get("ts", 0)
    return (time.time() - last) >= interval_h * 3600


def _score(user_input: str, response: str) -> float:
    try:
        from core.self_improvement import SelfEvaluator
        ev = SelfEvaluator()
        metrics = ev._calculate_metrics(user_input, response)
        scores = [m.get("score", 0.5) for m in metrics]
        return sum(scores) / len(scores) if scores else 0.5
    except Exception:
        return 0.5


def _generate(probe: str, style: str) -> tuple[str, int]:
    """Genera una respuesta corta con el modelo local + el estilo a testear."""
    try:
        from actions.ollama_provider import chat, is_available
        if not is_available():
            return "", 0
        system = ("Sos ERIS, asistente personal cálido. " + style +
                  " Respuesta breve y natural, sin markdown.")
        out = chat(probe, system=system, temperature=0.6, max_tokens=160)
        return out, max(1, len(out) // 4)
    except Exception:
        return "", 0


def _apply_winner():
    """Si hay ganadora con suficiente data, la persiste como estilo activo."""
    try:
        from core.prompt_ab_testing import PromptABTest
        test = PromptABTest("estilo_auto", _VARIANTS)
        winner = test.get_winner()
        if not winner:
            return None
        stats = test.metrics["variants"].get(winner["name"], {})
        min_tests = max(3, len(_VARIANTS))
        if stats.get("tests", 0) < min_tests:
            return None
        active = {
            "experiment": "estilo_auto",
            "winner": winner["name"],
            "prompt": winner.get("prompt", ""),
            "win_rate": round(stats.get("win_rate", 0), 3),
            "tests": stats.get("tests", 0),
            "ts": time.time(),
        }
        _save(_ACTIVE_FILE, active)
        return active
    except Exception:
        return None


def get_active_style() -> str:
    """Snippet [ESTILO ACTIVO] para inyección (vacío si no hay ganadora)."""
    active = _load(_ACTIVE_FILE, None)
    if not active or not active.get("prompt"):
        return ""
    return (f"[ESTILO ACTIVO] (testeo A/B automático, variante "
            f"{active.get('winner','')}, win_rate {active.get('win_rate',0):.0%}): "
            f"{active['prompt']}")


def run_ab_round() -> str:
    """Ejecuta UNA ronda de A/B automático si ya toca según el intervalo."""
    if not _due():
        return "SIN ronda: aún no corresponde (última hace menos del intervalo)."
    try:
        from core.prompt_ab_testing import PromptABTest
        test = PromptABTest("estilo_auto", _VARIANTS)
        probes = _probes()
        total_gen = 0
        for probe in probes:
            for variant in _VARIANTS:
                resp, tokens = _generate(probe, variant["prompt"])
                if not resp:
                    continue
                score = _score(probe, resp)
                test.record_result(variant["name"], score, tokens)
                total_gen += 1
            time.sleep(0.5)
        active = _apply_winner()
        test._save_metrics()
        _save(_LAST_FILE, {"ts": time.time(), "probes": len(probes), "gens": total_gen})
        report = test.get_report().replace("\n", " | ")
        if active:
            return f"A/B OK: {total_gen} gens. {report}. => Estilo activo: {active['winner']}"
        return f"A/B OK: {total_gen} gens. {report}. Ganador confirmado aún no."
    except Exception as e:
        return f"A/B error: {e}"


def ab_automated(parameters: dict = None, player=None) -> str:
    """Tool A/B automático de prompts: round (correr ronda), active, status."""
    params = parameters or {}
    action = str(params.get("action", "status")).lower().strip()
    if action in ("round", "run", "ahora"):
        return run_ab_round(force=True) if params.get("force") else run_ab_round()
    if action == "active":
        active = _load(_ACTIVE_FILE, None)
        if not active:
            return "No hay estilo activo aún (falta data de experimentos)."
        return (f"Estilo activo: variante {active['winner']} (win_rate "
                f"{active['win_rate']:.0%}, {active['tests']} tests): {active['prompt']}")
    if action == "status":
        last = _load(_LAST_FILE, {})
        since = int((time.time() - last.get("ts", 0)) // 60) if last.get("ts") else -1
        try:
            from core.prompt_ab_testing import PromptABTest
            report = PromptABTest("estilo_auto", _VARIANTS).get_report()
        except Exception:
            report = "sin experimento aún"
        active = _load(_ACTIVE_FILE, None)
        a = f", activa={active['winner']}" if active else ""
        mins = f"última ronda hace {since} min" if since >= 0 else "sin ronda aún"
        return f"A/B automático: intervalo {get_interval_hours()}h, {mins}{a}.\n{report}"
    return "Acciones: round, active, status"