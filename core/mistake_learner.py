"""
mistake_learner.py — Aprende explícitamente de errores propios.

Registra cada error, su contexto, solución aplicada, y genera reglas "nunca más":
  - Patrón: qué salió mal
  - Causa raíz: por qué
  - Solución: cómo se arregló
  - Regla: qué hacer diferente la próxima vez
  - Prevención: checks para evitar repetir
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from collections import defaultdict

_BASE = Path(__file__).resolve().parent.parent
_MISTAKES_FILE = _BASE / "data" / "mistakes.json"


def _load_mistakes() -> dict:
    try:
        if _MISTAKES_FILE.exists():
            return json.loads(_MISTAKES_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"mistakes": [], "rules": [], "stats": {"total": 0, "resolved": 0}}


def _save_mistakes(data: dict):
    try:
        _MISTAKES_FILE.parent.mkdir(parents=True, exist_ok=True)
        _MISTAKES_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def record_mistake(
    pattern: str,
    cause: str = "",
    solution: str = "",
    context: str = "",
    severity: str = "medium",
    category: str = "general",
) -> dict:
    """Registra un mistake."""
    data = _load_mistakes()
    mistake_id = "mistake_%d" % int(time.time())

    mistake = {
        "id": mistake_id,
        "pattern": pattern,
        "cause": cause,
        "solution": solution,
        "context": context,
        "severity": severity,
        "category": category,
        "resolved": bool(solution),
        "recurrence_count": 0,
        "created_at": time.time(),
    }
    data["mistakes"].append(mistake)
    data["stats"]["total"] = data["stats"].get("total", 0) + 1
    if solution:
        data["stats"]["resolved"] = data["stats"].get("resolved", 0) + 1

    # Mantener últimos 200
    if len(data["mistakes"]) > 200:
        data["mistakes"] = data["mistakes"][-200:]

    _save_mistakes(data)
    return mistake


def create_rule(
    trigger: str,
    action: str,
    reason: str = "",
    category: str = "general",
) -> dict:
    """Crea una regla 'nunca más'."""
    data = _load_mistakes()
    rule_id = "rule_%d" % int(time.time())

    rule = {
        "id": rule_id,
        "trigger": trigger,
        "action": action,
        "reason": reason,
        "category": category,
        "created_at": time.time(),
        "times_applied": 0,
    }
    data["rules"].append(rule)

    # Mantener últimas 100 reglas
    if len(data["rules"]) > 100:
        data["rules"] = data["rules"][-100:]

    _save_mistakes(data)
    return rule


def check_before_acting(action_description: str) -> list[dict]:
    """Verifica si una acción viola alguna regla existente."""
    data = _load_mistakes()
    violations = []
    for rule in data.get("rules", []):
        trigger = rule.get("trigger", "").lower()
        if trigger and trigger in action_description.lower():
            violations.append(rule)
    return violations


def get_related_mistakes(current_error: str) -> list[dict]:
    """Busca mistakes similares al error actual."""
    data = _load_mistakes()
    current_words = set(current_error.lower().split())

    scored = []
    for m in data.get("mistakes", []):
        m_words = set(m.get("pattern", "").lower().split())
        overlap = len(current_words & m_words)
        if overlap > 0:
            scored.append({"mistake": m, "similarity": overlap})

    scored.sort(key=lambda x: x["similarity"], reverse=True)
    return [s["mistake"] for s in scored[:5]]


def get_unresolved() -> list[dict]:
    """Mistakes sin solución registrada."""
    data = _load_mistakes()
    return [m for m in data.get("mistakes", []) if not m.get("resolved")]


def mark_resolved(mistake_id: str, solution: str) -> bool:
    """Marca un mistake como resuelto."""
    data = _load_mistakes()
    for m in data["mistakes"]:
        if m["id"] == mistake_id:
            m["resolved"] = True
            m["solution"] = solution
            _save_mistakes(data)
            return True
    return False


def increment_recurrence(mistake_id: str):
    """Incrementa contador de recurrencia."""
    data = _load_mistakes()
    for m in data["mistakes"]:
        if m["id"] == mistake_id:
            m["recurrence_count"] = m.get("recurrence_count", 0) + 1
            _save_mistakes(data)
            return


def get_pattern_analysis() -> dict:
    """Análisis de patrones de errores."""
    data = _load_mistakes()
    mistakes = data.get("mistakes", [])

    by_category = defaultdict(int)
    by_severity = defaultdict(int)
    recurring = []

    for m in mistakes:
        by_category[m.get("category", "general")] += 1
        by_severity[m.get("severity", "medium")] += 1
        if m.get("recurrence_count", 0) > 0:
            recurring.append(m)

    return {
        "total_mistakes": len(mistakes),
        "resolved": sum(1 for m in mistakes if m.get("resolved")),
        "unresolved": sum(1 for m in mistakes if not m.get("resolved")),
        "total_rules": len(data.get("rules", [])),
        "by_category": dict(by_category),
        "by_severity": dict(by_severity),
        "recurring_count": len(recurring),
        "top_recurring": [
            {"pattern": m["pattern"][:60], "count": m["recurrence_count"]}
            for m in sorted(recurring, key=lambda x: x.get("recurrence_count", 0), reverse=True)[:5]
        ],
    }


def format_mistakes() -> str:
    """Formatea resumen de mistakes."""
    analysis = get_pattern_analysis()
    lines = [
        "Mistakes: %d total (%d resueltos, %d pendientes, %d recurrentes)" % (
            analysis["total_mistakes"], analysis["resolved"],
            analysis["unresolved"], analysis["recurring_count"]),
        "Reglas 'nunca más': %d" % analysis["total_rules"],
    ]
    if analysis["top_recurring"]:
        lines.append("\nErrores recurrentes:")
        for r in analysis["top_recurring"]:
            lines.append("  ⚠ %s (×%d)" % (r["pattern"], r["count"]))
    if analysis["by_category"]:
        lines.append("\nPor categoría:")
        for cat, count in sorted(analysis["by_category"].items(), key=lambda x: x[1], reverse=True):
            lines.append("  %s: %d" % (cat, count))
    return "\n".join(lines)
