# -*- coding: utf-8 -*-
"""
core/lesson_applier.py — Aplicador de lecciones aprendidas
Carga las skills cristalizadas en evolution_learning y las hace disponibles.
Cuando hay una lección aplicable al código, puede proponerla/aplicarla.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from datetime import datetime

_BASE = Path(__file__).resolve().parent.parent
_SKILLS_DIR = _BASE / "skills" / "evolution_learning"
_MEM_DIR = _BASE / "memory"
_APPLIED_FILE = _MEM_DIR / "lessons_applied.json"


def _load_applied() -> dict:
    try:
        if _APPLIED_FILE.exists():
            return json.loads(_APPLIED_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"applied": [], "proposed": [], "ignored": []}


def _save_applied(data: dict):
    try:
        _MEM_DIR.mkdir(parents=True, exist_ok=True)
        _APPLIED_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def load_lessons() -> list:
    """Carga todas las lecciones cristalizadas."""
    lessons = []
    try:
        if not _SKILLS_DIR.exists():
            return lessons
        for f in _SKILLS_DIR.glob("*_SKILL.md"):
            try:
                txt = f.read_text(encoding="utf-8")
                # Extraer contenido sin frontmatter
                if txt.startswith("---"):
                    parts = txt.split("---", 2)
                    if len(parts) >= 3:
                        content = parts[2].strip()
                    else:
                        content = txt
                else:
                    content = txt
                lessons.append({
                    "file": str(f),
                    "name": f.stem,
                    "content": content[:1500]
                })
            except Exception:
                continue
    except Exception:
        pass
    return lessons


def inject_learned_lessons() -> str:
    """Inyecta lecciones aprendidas en el contexto para que las tenga presentes."""
    lessons = load_lessons()
    if not lessons:
        return ""
    applied = _load_applied()
    applied_names = set(applied.get("applied", []))
    
    lines = ["[LECCIONES APRENDIDAS — APLICAR CUANDO CORRESPONDA]"]
    lines.append("Estas lecciones fueron investigadas y cristalizadas por mí. Cuando vayan con lo que estoy haciendo, APLICALAS al código si es útil.")
    count = 0
    for l in lessons[-8:]:  # últimas 8
        if l["name"] in applied_names:
            continue
        count += 1
        # Extraer título/idea principal
        content = l["content"]
        first_line = content.split("\n")[0][:80]
        lines.append(f"- {l['name'].replace('_SKILL','').replace('_',' ')}: {first_line}")
        if count >= 5:
            break
    if count == 0:
        return ""
    lines.append("Si detectás que alguna se aplica al código que estás tocando, proponé aplicarla con un cambio concreto.")
    return "\n".join(lines)


def lesson_applier(params: dict | None = None):
    params = params or {}
    action = str(params.get("action") or "status").strip().lower()
    
    if action == "status":
        lessons = load_lessons()
        applied = _load_applied()
        return f"Lecciones cristalizadas: {len(lessons)} | Aplicadas: {len(applied.get('applied',[]))} | Propuestas: {len(applied.get('proposed',[]))}"
    
    if action == "list":
        lessons = load_lessons()
        if not lessons:
            return "No hay lecciones cristalizadas aún."
        out = ["[LECCIONES]"]
        for l in lessons[-10:]:
            out.append(f"- {l['name']}")
        return "\n".join(out)
    
    if action == "read":
        name = params.get("name") or params.get("lesson") or ""
        lessons = load_lessons()
        for l in lessons:
            if name in l["name"]:
                return l["content"]
        return "Lección no encontrada"
    
    if action == "mark_applied":
        name = params.get("name") or ""
        applied = _load_applied()
        if name not in applied["applied"]:
            applied["applied"].append(name)
        _save_applied(applied)
        return f"Marcada como aplicada: {name}"
    
    if action == "inject":
        return inject_learned_lessons()
    
    return lesson_applier({"action": "status"})


__all__ = ["load_lessons", "inject_learned_lessons", "lesson_applier"]
