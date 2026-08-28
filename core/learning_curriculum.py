"""
learning_curriculum.py — Plan estructurado de auto-mejora.

Crea y sigue un currículum de aprendizaje para el agente:
  - Identifica áreas débiles (de capability_self_assessment)
  - Crea ejercicios/targets específicos
  - Rastrea progreso
  - Sugiere siguientes pasos
"""
from __future__ import annotations

import json
import time
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_CURRICULUM_FILE = _BASE / "data" / "learning_curriculum.json"

# Currículum predefinido por categoría
DEFAULT_CURRICULUM = {
    "coding": {
        "description": "Mejorar calidad de código generado",
        "targets": [
            "Crear tests para cada función nueva",
            "Usar type hints consistentemente",
            "Manejar edge cases explícitamente",
            "Seguir PEP 8 / estilo del proyecto",
        ],
        "exercises": [
            "Refactorizar un archivo existente manteniendo compatibilidad",
            "Escribir 3 tests unitarios para una función",
            "Detectar y fixear un code smell",
        ],
    },
    "debugging": {
        "description": "Mejorar resolución de bugs",
        "targets": [
            "Diagnosticar errores en <2 intentos",
            "Usar error_pattern_db para errores conocidos",
            "Crear test de regresión al fixear",
        ],
        "exercises": [
            "Simular debugging de un error de importación",
            "Reproducir un bug aisladamente antes de fixear",
        ],
    },
    "research": {
        "description": "Mejorar búsqueda de información",
        "targets": [
            "Usar múltiples fuentes para verificar",
            "Distinguir fuentes confiables de no confiables",
            "Sintetizar findings en actionable items",
        ],
        "exercises": [
            "Investigar una tecnología nueva y crear un resumen ejecutivo",
            "Comparar 2 approaches para resolver un problema",
        ],
    },
    "planning": {
        "description": "Mejorar planificación de tareas",
        "targets": [
            "Descomponer tareas grandes en pasos accionables",
            "Estimar complejidad realistas",
            "Identificar dependencias entre pasos",
        ],
        "exercises": [
            "Crear un plan de 5+ pasos para un feature complejo",
            "Re-planificar cuando algo falla a mitad de camino",
        ],
    },
    "communication": {
        "description": "Mejorar comunicación con el usuario",
        "targets": [
            "Explicar decisiones con self_explainer",
            "Adaptar estilo según feedback del usuario",
            "Ser conciso sin perder información clave",
        ],
        "exercises": [
            "Explicar un concepto técnico a alguien no técnico",
            "Resumir una solución compleja en 3 oraciones",
        ],
    },
}


def _load_curriculum() -> dict:
    try:
        if _CURRICULUM_FILE.exists():
            return json.loads(_CURRICULUM_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {
        "categories": {},
        "completed_exercises": [],
        "current_focus": "",
        "start_date": time.time(),
        "last_updated": time.time(),
    }


def _save_curriculum(data: dict):
    try:
        _CURRICULUM_FILE.parent.mkdir(parents=True, exist_ok=True)
        _CURRICULUM_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def initialize_curriculum() -> dict:
    """Inicializa el currículum con valores por defecto."""
    data = _load_curriculum()
    if not data.get("categories"):
        for cat, info in DEFAULT_CURRICULUM.items():
            data["categories"][cat] = {
                "description": info["description"],
                "targets": info["targets"],
                "exercises": info["exercises"],
                "completed": [],
                "score": 0,
                "total": len(info["exercises"]),
            }
        data["start_date"] = time.time()
        _save_curriculum(data)
    return data


def get_next_exercise(category: str = None) -> dict | None:
    """Obtiene el siguiente ejercicio sin completar."""
    data = _load_curriculum()
    if not data.get("categories"):
        initialize_curriculum()
        data = _load_curriculum()

    cats = data["categories"]
    if category:
        cats = {category: cats.get(category, {})} if category in cats else {}

    for cat_name, cat_info in cats.items():
        completed = set(cat_info.get("completed", []))
        for exercise in cat_info.get("exercises", []):
            if exercise not in completed:
                return {
                    "category": cat_name,
                    "exercise": exercise,
                    "targets": cat_info.get("targets", []),
                    "progress": "%d/%d" % (len(completed), cat_info.get("total", 0)),
                }
    return None


def complete_exercise(category: str, exercise: str, success: bool = True, notes: str = ""):
    """Marca un ejercicio como completado."""
    data = _load_curriculum()
    if category not in data.get("categories", {}):
        return

    cat = data["categories"][category]
    if success:
        completed = cat.get("completed", [])
        if exercise not in completed:
            completed.append(exercise)
            cat["completed"] = completed
            cat["score"] = len(completed)

    data["completed_exercises"].append({
        "category": category,
        "exercise": exercise,
        "success": success,
        "notes": notes[:200],
        "timestamp": time.time(),
    })
    data["last_updated"] = time.time()
    _save_curriculum(data)


def get_progress() -> dict:
    """Resumen de progreso del currículum."""
    data = _load_curriculum()
    if not data.get("categories"):
        return {"total": 0, "completed": 0, "categories": {}}

    total = 0
    completed = 0
    cat_progress = {}
    for cat, info in data["categories"].items():
        t = info.get("total", 0)
        c = len(info.get("completed", []))
        total += t
        completed += c
        cat_progress[cat] = {
            "progress": c,
            "total": t,
            "percentage": round(c / t * 100, 1) if t > 0 else 0,
        }

    return {
        "total": total,
        "completed": completed,
        "percentage": round(completed / total * 100, 1) if total > 0 else 0,
        "categories": cat_progress,
    }


def suggest_focus() -> str | None:
    """Sugiere en qué categoría enfocarse (la más débil)."""
    progress = get_progress()
    cats = progress.get("categories", {})
    if not cats:
        return None
    weakest = min(cats.items(), key=lambda x: x[1]["percentage"])
    if weakest[1]["percentage"] < 100:
        return weakest[0]
    return None


def format_curriculum() -> str:
    """Formatea el currículum para mostrar."""
    progress = get_progress()
    lines = [
        "Currículum de auto-mejora:",
        "  Progreso total: %d/%d (%.0f%%)" % (
            progress["completed"], progress["total"], progress["percentage"]),
        "",
        "Por categoría:",
    ]
    for cat, info in progress.get("categories", {}).items():
        bar = "#" * int(info["percentage"] / 10) + "-" * (10 - int(info["percentage"] / 10))
        lines.append("  %s: [%s] %d/%d (%.0f%%)" % (
            cat, bar, info["progress"], info["total"], info["percentage"]))

    focus = suggest_focus()
    if focus:
        lines.append("\nEnfocarse en: %s" % focus)

    next_ex = get_next_exercise()
    if next_ex:
        lines.append("Siguiente ejercicio: [%s] %s" % (next_ex["category"], next_ex["exercise"]))

    return "\n".join(lines)
