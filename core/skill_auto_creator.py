"""
skill_auto_creator.py — Creador automático de skills.

Detecta patrones repetitivos en las acciones del usuario y sugiere
o crea automáticamente skills para automatizarlos.

Ejemplo: si el usuario siempre hace lo mismo para "deploy", se crea
un skill `deploy` que encapsula esos pasos.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from collections import Counter

_BASE = Path(__file__).resolve().parent.parent
_SKILLS_DIR = _BASE / "skills" / "user_created"
_PATTERNS_FILE = _BASE / "data" / "repetitive_patterns.json"


def _load_patterns() -> dict:
    try:
        if _PATTERNS_FILE.exists():
            return json.loads(_PATTERNS_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"sequences": {}, "tool_combos": {}}


def _save_patterns(patterns: dict):
    try:
        _PATTERNS_FILE.parent.mkdir(parents=True, exist_ok=True)
        _PATTERNS_FILE.write_text(json.dumps(patterns, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def record_tool_sequence(tools: list[str], context: str = ""):
    """Registra una secuencia de tools usadas."""
    patterns = _load_patterns()
    seqs = patterns.get("sequences", {})

    if len(tools) < 2:
        return

    # Generar n-gramas de 2 y 3
    for n in [2, 3]:
        for i in range(len(tools) - n + 1):
            ngram = tuple(tools[i:i + n])
            key = "|".join(ngram)
            if key not in seqs:
                seqs[key] = {"count": 0, "contexts": [], "last_seen": 0}
            seqs[key]["count"] += 1
            seqs[key]["last_seen"] = time.time()
            if context and context not in seqs[key]["contexts"]:
                seqs[key]["contexts"].append(context[:100])
                seqs[key]["contexts"] = seqs[key]["contexts"][-5:]

    patterns["sequences"] = seqs
    _save_patterns(patterns)


def record_tool_combo(tool1: str, tool2: str):
    """Registra que dos tools se usaron juntas."""
    patterns = _load_patterns()
    combos = patterns.get("tool_combos", {})
    key = "%s+%s" % (tool1, tool2)
    combos[key] = combos.get(key, 0) + 1
    patterns["tool_combos"] = combos
    _save_patterns(patterns)


def detect_repetitive_patterns(min_count: int = 3) -> list[dict]:
    """Detecta patrones repetitivos que justifican un skill."""
    patterns = _load_patterns()
    seqs = patterns.get("sequences", {})

    suggestions = []
    for key, data in seqs.items():
        if data["count"] >= min_count:
            tools = key.split("|")
            suggestions.append({
                "pattern": key,
                "tools": tools,
                "count": data["count"],
                "contexts": data.get("contexts", []),
                "suggested_name": _suggest_skill_name(tools),
                "reason": "Secuencia repetida %d veces" % data["count"],
            })

    return sorted(suggestions, key=lambda x: x["count"], reverse=True)[:10]


def _suggest_skill_name(tools: list[str]) -> str:
    """Sugiere un nombre de skill basado en las tools."""
    name_map = {
        "shell": "run",
        "file_write": "write",
        "file_read": "read",
        "file_edit": "edit",
        "codebase": "search",
        "websearch": "research",
        "git_control": "git",
        "obsidian_note": "note",
        "memory_get": "recall",
        "memory_add": "remember",
    }
    parts = [name_map.get(t, t) for t in tools[:3]]
    return "-".join(parts)


def create_skill_from_pattern(
    pattern: dict,
    name: str = None,
    description: str = "",
) -> str:
    """Crea un skill YAML a partir de un patrón detectado.

    Returns:
        Path del skill creado
    """
    skill_name = name or pattern.get("suggested_name", "auto-skill")
    tools = pattern.get("tools", [])
    contexts = pattern.get("contexts", [])

    skill_dir = _SKILLS_DIR / skill_name
    skill_dir.mkdir(parents=True, exist_ok=True)

    # Generar SKILL.md
    steps = []
    for i, tool in enumerate(tools, 1):
        steps.append("  %d. Usar tool `%s`" % (i, tool))

    yaml_content = '''---
name: %s
description: "%s"
trigger: "Cuando se repita la secuencia: %s"
tools: %s
auto_created: true
created_at: %s
repetition_count: %d
---

# Skill: %s

## Descripción
%s

## Cuando Usar
- Cuando se detecte la secuencia: %s
- Contextos previos: %s

## Procedimiento
%s

## Notas
Este skill fue creado automáticamente por patrón repetido.
Puedes editarlo en `skills/user_created/%s/SKILL.md`.
''' % (
        skill_name,
        description or "Skill auto-generado de patrón repetido",
        pattern.get("pattern", ""),
        json.dumps(tools),
        time.strftime("%Y-%m-%d"),
        pattern.get("count", 0),
        skill_name,
        description or "Automatiza la secuencia: %s" % pattern.get("pattern", ""),
        pattern.get("pattern", ""),
        "; ".join(contexts[:3]) if contexts else "N/A",
        "\n".join(steps),
        skill_name,
    )

    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(yaml_content, encoding="utf-8")

    return str(skill_file)


def suggest_skills() -> list[dict]:
    """Sugiere skills que deberían crearse."""
    return detect_repetitive_patterns(min_count=3)
