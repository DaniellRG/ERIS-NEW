"""
capability_self_assessment.py — Auto-evaluación de capacidades del agente.

Evalúa qué tan bueno es el agente en cada área y sugiere mejoras:
  - Porcentaje de éxito por tool/categoría
  - Áreas débiles que necesitan training
  - Comparación con sesiones anteriores
  - Recomendaciones de skills a instalar
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from collections import defaultdict

_BASE = Path(__file__).resolve().parent.parent
_ASSESSMENT_FILE = _BASE / "data" / "capability_assessment.json"

# Categorías de evaluación
CATEGORIES = {
    "coding": {
        "description": "Escritura y edición de código",
        "tools": ["file_write", "file_edit", "file_read"],
        "weight": 1.0,
    },
    "debugging": {
        "description": "Resolución de errores",
        "tools": ["shell", "file_read", "codebase"],
        "weight": 1.2,
    },
    "research": {
        "description": "Búsqueda y análisis de información",
        "tools": ["websearch", "webfetch", "codebase"],
        "weight": 0.8,
    },
    "file_management": {
        "description": "Gestión de archivos y directorios",
        "tools": ["file_write", "file_edit", "file_read", "file_delete"],
        "weight": 0.9,
    },
    "git": {
        "description": "Control de versiones",
        "tools": ["git_control"],
        "weight": 1.0,
    },
    "memory": {
        "description": "Gestión de memoria y conocimiento",
        "tools": ["memory_add", "memory_get", "obsidian_note"],
        "weight": 1.1,
    },
    "planning": {
        "description": "Planificación y ejecución",
        "tools": ["goals", "todowrite"],
        "weight": 1.0,
    },
}


def _load_assessment() -> dict:
    try:
        if _ASSESSMENT_FILE.exists():
            return json.loads(_ASSESSMENT_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {
        "sessions": [],
        "tool_stats": {},
        "category_scores": {},
        "last_assessment": 0,
    }


def _save_assessment(data: dict):
    try:
        _ASSESSMENT_FILE.parent.mkdir(parents=True, exist_ok=True)
        _ASSESSMENT_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def record_tool_usage(tool_name: str, success: bool, duration: float = 0, context: str = ""):
    """Registra uso de una tool para evaluación."""
    data = _load_assessment()
    stats = data.get("tool_stats", {})

    if tool_name not in stats:
        stats[tool_name] = {
            "total": 0, "success": 0, "failures": 0,
            "total_duration": 0, "avg_duration": 0,
        }

    entry = stats[tool_name]
    entry["total"] += 1
    if success:
        entry["success"] += 1
    else:
        entry["failures"] += 1
    entry["total_duration"] += duration
    entry["avg_duration"] = entry["total_duration"] / entry["total"]

    data["tool_stats"] = stats
    _save_assessment(data)


def calculate_category_scores() -> dict:
    """Calcula scores por categoría."""
    data = _load_assessment()
    stats = data.get("tool_stats", {})

    scores = {}
    for cat_name, cat_info in CATEGORIES.items():
        cat_tools = cat_info["tools"]
        total = 0
        successes = 0

        for tool in cat_tools:
            if tool in stats:
                total += stats[tool]["total"]
                successes += stats[tool]["success"]

        rate = successes / total if total > 0 else 0.0
        scores[cat_name] = {
            "success_rate": round(rate * 100, 1),
            "total_operations": total,
            "description": cat_info["description"],
            "weight": cat_info["weight"],
            "grade": _rate_to_grade(rate),
        }

    data["category_scores"] = scores
    data["last_assessment"] = time.time()
    _save_assessment(data)

    return scores


def _rate_to_grade(rate: float) -> str:
    if rate >= 0.95:
        return "A+"
    elif rate >= 0.90:
        return "A"
    elif rate >= 0.80:
        return "B"
    elif rate >= 0.70:
        return "C"
    elif rate >= 0.60:
        return "D"
    return "F"


def get_weak_areas(threshold: float = 0.70) -> list[dict]:
    """Encuentra áreas débiles que necesitan mejora."""
    scores = calculate_category_scores()
    weak = []

    for cat, info in scores.items():
        if info["success_rate"] < threshold * 100 and info["total_operations"] > 3:
            weak.append({
                "category": cat,
                "success_rate": info["success_rate"],
                "grade": info["grade"],
                "description": info["description"],
                "suggestion": _suggest_improvement(cat),
            })

    return sorted(weak, key=lambda x: x["success_rate"])


def _suggest_improvement(category: str) -> str:
    suggestions = {
        "coding": "Revisar style guide, usar type hints, crear tests antes de código",
        "debugging": "Usar error_pattern_db para aprender de errores previos",
        "research": "Mejorar queries de búsqueda, usar múltiples fuentes",
        "file_management": "Usar paths relativos, verificar existencia antes de operar",
        "git": "Hacer commits más pequeños, usar convención de mensajes",
        "memory": "Consolidar memoria regularmente, usar tags consistentes",
        "plan": "Descomponer tareas grandes, verificar dependencias",
    }
    return suggestions.get(category, "Practicar más en esta área")


def get_overall_score() -> dict:
    """Score general del agente."""
    scores = calculate_category_scores()
    if not scores:
        return {"score": 0, "grade": "N/A", "total_ops": 0}

    weighted_sum = 0
    weight_total = 0
    total_ops = 0

    for cat, info in scores.items():
        w = info["weight"]
        weighted_sum += info["success_rate"] * w
        weight_total += w * 100
        total_ops += info["total_operations"]

    overall = weighted_sum / weight_total if weight_total > 0 else 0

    return {
        "score": round(overall, 1),
        "grade": _rate_to_grade(overall / 100),
        "total_operations": total_ops,
        "categories": len(scores),
    }


def format_assessment() -> str:
    """Formatea la auto-evaluación completa."""
    scores = calculate_category_scores()
    overall = get_overall_score()
    weak = get_weak_areas()

    lines = [
        "Auto-evaluación del agente:",
        "Score general: %s/100 (grado %s)" % (overall["score"], overall["grade"]),
        "Total operaciones: %d" % overall["total_operations"],
        "",
        "Por categoría:",
    ]

    for cat, info in sorted(scores.items(), key=lambda x: -x[1]["success_rate"]):
        lines.append("  %s: %s/100 [%s] (%d ops)" % (
            cat, info["success_rate"], info["grade"], info["total_operations"]
        ))

    if weak:
        lines.append("")
        lines.append("Áreas débiles:")
        for w in weak:
            lines.append("  - %s: %s → %s" % (w["category"], w["grade"], w["suggestion"]))

    return "\n".join(lines)
