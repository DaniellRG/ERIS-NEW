"""
superpowers.py — Superpowers SDLC Methodology Registry for ERIS
Integrates the obra/superpowers software development methodology
as loadable skills with progressive disclosure.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

_SUPERPOWERS_DIR = Path(__file__).resolve().parent / "builtin"

SUPERPOWERS_SKILLS = [
    "using-superpowers",
    "brainstorming",
    "writing-plans",
    "test-driven-development",
    "subagent-driven-development",
    "executing-plans",
    "systematic-debugging",
    "root-cause-tracing",
    "verification-before-completion",
    "defense-in-depth",
    "requesting-code-review",
    "receiving-code-review",
    "using-git-worktrees",
    "finishing-a-development-branch",
    "dispatching-parallel-agents",
    "condition-based-waiting",
    "testing-anti-patterns",
]


def _read_skill_frontmatter(name: str) -> dict[str, Any] | None:
    """Read YAML frontmatter from a Superpowers SKILL.md."""
    path = _SUPERPOWERS_DIR / name / "SKILL.md"
    if not path.exists():
        return None
    try:
        content = path.read_text(encoding="utf-8")
    except Exception:
        return None
    if not content.startswith("---"):
        return None
    parts = content.split("---", 2)
    if len(parts) < 3:
        return None
    meta: dict[str, Any] = {}
    for line in parts[1].strip().splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip()
            if val.startswith("[") and val.endswith("]"):
                inner = val[1:-1].strip()
                meta[key] = [t.strip().strip("'\"") for t in inner.split(",") if t.strip()] if inner else []
            else:
                try:
                    meta[key] = int(val)
                except ValueError:
                    meta[key] = val.strip("'\"")
    return meta


def _read_skill_body(name: str) -> str | None:
    """Read the body content (after frontmatter) from a Superpowers SKILL.md."""
    path = _SUPERPOWERS_DIR / name / "SKILL.md"
    if not path.exists():
        return None
    try:
        content = path.read_text(encoding="utf-8")
    except Exception:
        return None
    if "---" in content:
        return content.split("---", 2)[-1].strip()
    return content


def superpowers_list() -> str:
    """Level 0: Return compact list of available Superpowers skills."""
    lines = ["[SUPERPOWERS — Software Development Methodology]"]
    for name in SUPERPOWERS_SKILLS:
        meta = _read_skill_frontmatter(name)
        if meta:
            desc = meta.get("description", "")
            lines.append(f"  - {name}: {desc}")
        else:
            lines.append(f"  - {name}")
    lines.append("")
    lines.append("Usa superpowers_activate(name='skill-name') para ver instrucciones completas.")
    lines.append("Los skills se activan automáticamente según la tarea.")
    return "\n".join(lines)


def superpowers_activate(name: str) -> str:
    """Level 1: Return full SKILL.md content for a specific Superpowers skill."""
    normalized = name.lower().strip().replace(" ", "-")
    for skill in SUPERPOWERS_SKILLS:
        if skill.lower() == normalized or skill.lower().replace("-", " ") == name.lower().strip():
            body = _read_skill_body(skill)
            if body:
                meta = _read_skill_frontmatter(skill)
                header = f"# Superpowers: {skill}\n"
                if meta and "description" in meta:
                    header += f"**{meta['description']}**\n\n"
                return header + body
            return f"Skill '{skill}' encontrada pero no se pudo leer."
    return f"Superpowers skill '{name}' no encontrada. Skills disponibles: {', '.join(SUPERPOWERS_SKILLS)}."


def superpowers_tool_declaration() -> dict:
    """Return the tool declaration dict for main.py integration."""
    return {
        "name": "superpowers_activate",
        "description": (
            "Activate a Superpowers software development methodology skill. "
            "Use this when the user asks to develop software, plan a feature, "
            "debug an issue, write tests, review code, or any SDLC task. "
            "Available skills: brainstorming, writing-plans, test-driven-development, "
            "subagent-driven-development, executing-plans, systematic-debugging, "
            "root-cause-tracing, verification-before-completion, defense-in-depth, "
            "requesting-code-review, receiving-code-review, using-git-worktrees, "
            "finishing-a-development-branch, dispatching-parallel-agents, "
            "condition-based-waiting, testing-anti-patterns."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "name": {
                    "type": "STRING",
                    "description": "Skill name slug (e.g., 'test-driven-development', 'brainstorming')",
                },
            },
            "required": ["name"],
        },
    }
