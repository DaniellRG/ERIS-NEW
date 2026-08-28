"""
skill_registry.py — Sistema de Skills Auto-Mejorables para ERIS
Inspirado en Hermes Agent (NousResearch), adaptado para ERIS.

Skills son procedimientos guardados que ERIS puede reutilizar.
Formato: SKILL.md con YAML frontmatter, compatible con agentskills.io

Progressive Disclosure:
  Level 0: skills_list()     → [{name, description, category}]  (~500 tokens)
  Level 1: skill_view(name)  → Contenido completo SKILL.md       (~200-800 tokens)
"""
from __future__ import annotations

import json
import os
import re
import shutil
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path
from typing import Any

SKILLS_DIR = Path(__file__).resolve().parent
BUILTIN_DIR = SKILLS_DIR / "builtin"
USER_CREATED_DIR = SKILLS_DIR / "user_created"
BUNDLES_DIR = SKILLS_DIR / "bundles"
INDEX_FILE = SKILLS_DIR / "skills_index.json"

# Remote skill registry source (community skills index)
REMOTE_INDEX_URL = os.environ.get(
    "ERIS_SKILLS_REPO",
    "https://raw.githubusercontent.com/open-jarvis/skills/main/index.json"
)
REMOTE_SKILLS_BASE = os.environ.get(
    "ERIS_SKILLS_BASE",
    "https://raw.githubusercontent.com/open-jarvis/skills/main/builtin"
)

SYNCED_DIR = SKILLS_DIR / "synced"
SYNCED_DIR.mkdir(exist_ok=True)

SKILL_MD_TEMPLATE = """---
name: {name}
description: {description}
version: 1.0.0
category: {category}
tags: [{tags}]
---
# {title}

## When to Use
{when_to_use}

## Procedure
{procedure}

## Pitfalls
{pitfalls}
"""


def _parse_frontmatter(content: str) -> dict[str, Any]:
    """Parse YAML frontmatter from SKILL.md content."""
    if not content.startswith("---"):
        return {}
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}
    meta = {}
    for line in parts[1].strip().splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip()
            if val.startswith("[") and val.endswith("]"):
                inner = val[1:-1].strip()
                meta[key] = [t.strip().strip("'\"") for t in inner.split(",") if t.strip()] if inner else []
            elif val.lower() == "true":
                meta[key] = True
            elif val.lower() == "false":
                meta[key] = False
            else:
                try:
                    meta[key] = int(val)
                except ValueError:
                    try:
                        meta[key] = float(val)
                    except ValueError:
                        meta[key] = val.strip("'\"")
    return meta


def _load_skill_file(skill_dir: Path) -> dict[str, Any] | None:
    """Load a single skill directory's SKILL.md and return metadata + content."""
    sk_path = skill_dir / "SKILL.md"
    if not sk_path.exists():
        return None
    try:
        content = sk_path.read_text(encoding="utf-8")
        frontmatter = _parse_frontmatter(content)
        body = content.split("---", 2)[-1].strip() if "---" in content else content
        return {
            "name": frontmatter.get("name", skill_dir.name),
            "description": frontmatter.get("description", ""),
            "version": frontmatter.get("version", "1.0.0"),
            "category": frontmatter.get("category", "general"),
            "tags": frontmatter.get("tags", []),
            "content": body,
            "full_content": content,
            "path": str(sk_path),
            "source": "builtin" if skill_dir.parent == BUILTIN_DIR else "user_created",
        }
    except Exception:
        return None


def _scan_skills() -> list[dict[str, Any]]:
    """Scan builtin and user_created directories for skills."""
    skills = []
    for base_dir in [BUILTIN_DIR, USER_CREATED_DIR]:
        if not base_dir.exists():
            continue
        for skill_dir in sorted(base_dir.iterdir()):
            if skill_dir.is_dir() and not skill_dir.name.startswith("_"):
                skill = _load_skill_file(skill_dir)
                if skill:
                    skills.append(skill)
    return skills


def _scan_synced_skills() -> list[dict[str, Any]]:
    """Scan synced skills directory."""
    skills = []
    if not SYNCED_DIR.exists():
        return skills
    for skill_dir in sorted(SYNCED_DIR.iterdir()):
        if skill_dir.is_dir() and not skill_dir.name.startswith("_"):
            skill = _load_skill_file(skill_dir)
            if skill:
                skill["source"] = "synced"
                skills.append(skill)
    return skills


def _scan_all_skills() -> list[dict[str, Any]]:
    return _scan_skills() + _scan_synced_skills()


def sync_remote_skills() -> str:
    """Fetch remote skills index and download new/updated skills."""
    try:
        req = urllib.request.Request(REMOTE_INDEX_URL, headers={"User-Agent": "ERIS/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return f"No se pudo obtener el índice remoto: {e}"

    if not isinstance(data, list):
        return "Formato de índice remoto inválido: se esperaba una lista."

    local_names = {s["name"].lower() for s in _scan_all_skills()}
    downloaded = 0
    errors = []

    for entry in data:
        name = entry.get("name", "").strip().lower().replace(" ", "-")
        if not name:
            continue
        if name in local_names:
            continue
        description = entry.get("description", "")
        category = entry.get("category", "general")
        tags = entry.get("tags", [])
        skill_url = f"{REMOTE_SKILLS_BASE}/{name}/SKILL.md"
        try:
            skill_req = urllib.request.Request(skill_url, headers={"User-Agent": "ERIS/1.0"})
            with urllib.request.urlopen(skill_req, timeout=15) as skill_resp:
                content = skill_resp.read().decode("utf-8")
        except Exception as e:
            errors.append(f"{name}: {e}")
            continue
        target_dir = SYNCED_DIR / name
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / "SKILL.md").write_text(content, encoding="utf-8")
        downloaded += 1

    _rebuild_index()
    msg = f"Habilidades sincronizadas: {downloaded} nuevas descargadas."
    if errors:
        msg += f"\nErrores ({len(errors)}): " + "; ".join(errors[:5])
    return msg


def _rebuild_index() -> list[dict[str, Any]]:
    """Rebuild the skills index cache."""
    skills = _scan_all_skills()
    try:
        index_data = []
        for s in skills:
            index_data.append({
                "name": s["name"],
                "description": s["description"],
                "category": s["category"],
                "tags": s["tags"],
                "version": s["version"],
                "source": s["source"],
            })
        INDEX_FILE.write_text(json.dumps(index_data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass
    return skills


def _get_cached_index() -> list[dict[str, Any]] | None:
    """Get skills from cache if available."""
    if INDEX_FILE.exists():
        try:
            return json.loads(INDEX_FILE.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def skills_list(parameters: dict | None = None) -> str:
    """
    Level 0: Return list of available skills (progressive disclosure).
    parameters: optional filter by category or tag.
    """
    params = parameters or {}
    category = params.get("category", "").lower().strip() if isinstance(params, dict) else ""
    tag = params.get("tag", "").lower().strip() if isinstance(params, dict) else ""

    cached = _get_cached_index()
    if cached is None:
        cached = _rebuild_index()
    else:
        live = _scan_all_skills()
        if len(live) != len(cached):
            cached = _rebuild_index()

    skills = cached or []
    if category:
        skills = [s for s in skills if s.get("category", "").lower() == category]
    if tag:
        skills = [s for s in skills if tag in [t.lower() for t in s.get("tags", [])]]

    if not skills:
        return "No skills available."

    lines = [f"Skills disponibles ({len(skills)}):"]
    for s in skills:
        src_tag = " [📥 synced]" if s.get("source") == "synced" else ""
        lines.append(f"  - {s['name']}: {s['description']} [{s['category']}]{src_tag}")
    lines.append("")
    lines.append("Usa skill_manage(action='view', name='skill-name') para ver instrucciones completas.")
    lines.append("Usa skill_manage(action='sync') para sincronizar skills desde el repositorio comunitario.")
    return "\n".join(lines)


def skill_view(name: str) -> str:
    """
    Level 1: Return full SKILL.md content for a specific skill.
    """
    all_skills = _scan_skills()
    for s in all_skills:
        if s["name"].lower() == name.lower() or s["name"].lower().replace("-", " ") == name.lower().replace("-", " "):
            return s["full_content"]
    return f"Skill '{name}' no encontrada. Usa skill_manage(action='list') para ver skills disponibles."


def skill_manage(parameters: dict, player=None) -> str:
    """
    CRUD operations for skills.
    Actions: sync, create, patch, edit, delete, list, view
    """
    params = parameters or {}
    # Compatibilidad: el nombre de la skill puede llegar como 'skill' (declaración
    # de la herramienta) o como 'name'. Aceptar ambos para no romper llamadas.
    if "name" not in params and isinstance(params, dict) and "skill" in params:
        params = dict(params)
        params["name"] = params["skill"]
    action = params.get("action", "").lower().strip()

    if action in ("sync", "sincronizar"):
        return sync_remote_skills()

    if action in ("list", "skills_list"):
        return skills_list()

    if action in ("view", "read"):
        name = params.get("name", "")
        if not name:
            return "Especifica el nombre de la skill."
        return skill_view(name)

    if action == "create":
        name = params.get("name", "").strip().lower().replace(" ", "-")
        content = params.get("content", "")
        category = params.get("category", "general")

        if not name:
            return "Especifica un nombre para la skill (slug: lowercase-con-guiones)."
        if not content:
            return "Especifica el contenido del SKILL.md."

        target_dir = USER_CREATED_DIR / name
        if target_dir.exists():
            return f"La skill '{name}' ya existe. Usa action='patch' o action='edit' para modificarla."

        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / "SKILL.md").write_text(content, encoding="utf-8")
        _rebuild_index()
        return f"Skill '{name}' creada en {target_dir}."

    if action == "patch":
        name = params.get("name", "").strip().lower().replace(" ", "-")
        old_string = params.get("old_string", "")
        new_string = params.get("new_string", "")

        if not name:
            return "Especifica el nombre de la skill."
        if not old_string:
            return "Especifica old_string (texto a reemplazar)."
        if not new_string:
            return "Especifica new_string (texto de reemplazo)."

        skill_path = _find_skill_path(name)
        if not skill_path:
            return f"Skill '{name}' no encontrada."

        try:
            content = skill_path.read_text(encoding="utf-8")
            if old_string not in content:
                return f"old_string no encontrado en la skill '{name}'. Verifica el texto exacto."

            new_content = content.replace(old_string, new_string, 1)
            skill_path.write_text(new_content, encoding="utf-8")
            _rebuild_index()
            return f"Skill '{name}' actualizada (patch aplicado)."
        except Exception as e:
            return f"Error aplicando patch a '{name}': {e}"

    if action == "edit":
        name = params.get("name", "").strip().lower().replace(" ", "-")
        content = params.get("content", "")

        if not name:
            return "Especifica el nombre de la skill."
        if not content:
            return "Especifica el nuevo contenido completo del SKILL.md."

        skill_path = _find_skill_path(name)
        if not skill_path:
            return f"Skill '{name}' no encontrada."

        try:
            skill_path.write_text(content, encoding="utf-8")
            _rebuild_index()
            return f"Skill '{name}' reescrita completamente."
        except Exception as e:
            return f"Error editando '{name}': {e}"

    if action == "delete":
        name = params.get("name", "").strip().lower().replace(" ", "-")
        if not name:
            return "Especifica el nombre de la skill."

        skill_path = _find_skill_path(name)
        if not skill_path:
            return f"Skill '{name}' no encontrada."

        skill_dir = skill_path.parent
        try:
            shutil.rmtree(skill_dir)
            _rebuild_index()
            return f"Skill '{name}' eliminada."
        except Exception as e:
            return f"Error eliminando '{name}': {e}"

    return f"Accion desconocida: '{action}'. Opciones: sync, create, patch, edit, delete, list, view."


def _find_skill_path(name: str) -> Path | None:
    """Find the SKILL.md path for a given skill name."""
    for base_dir in [BUILTIN_DIR, USER_CREATED_DIR, SYNCED_DIR]:
        if not base_dir.exists():
            continue
        for skill_dir in base_dir.iterdir():
            if skill_dir.is_dir() and (
                skill_dir.name.lower() == name.lower() or
                skill_dir.name.lower().replace("-", " ") == name.lower().replace("-", " ")
            ):
                sk = skill_dir / "SKILL.md"
                if sk.exists():
                    return sk
    return None


def skill_auto_create(tool_calls: list[dict], session_summary: str = "") -> dict | None:
    """
    Analyze a session's tool calls and generate a skill automatically.
    Called after complex tasks (5+ tool calls).
    """
    if len(tool_calls) < 3:
        return None

    tool_names = [tc.get("name", "") for tc in tool_calls]
    unique_tools = list(set(tool_names))

    if len(unique_tools) < 2:
        return None

    category_map = {
        ("document_creator",): "productivity",
        ("computer_control", "desktop_control"): "automation",
        ("file_controller",): "files",
        ("web_search", "browser_control"): "research",
        ("system_monitor",): "monitoring",
        ("open_app", "computer_control"): "automation",
        ("code_helper", "dev_agent"): "development",
        ("knowledge_base",): "knowledge",
    }

    category = "general"
    for tools, cat in category_map.items():
        if any(t in unique_tools for t in tools):
            category = cat
            break

    name = f"auto-{'-'.join(unique_tools[:3])}"
    title = f"{' / '.join(t.replace('_', ' ').title() for t in unique_tools[:4])}"
    description = f"Workflow automatizado usando {', '.join(unique_tools)}."

    procedure_lines = []
    for i, tc in enumerate(tool_calls[:10], 1):
        tname = tc.get("name", "unknown")
        targs = str(tc.get("args", {}))[:100]
        procedure_lines.append(f"{i}. Usar {tname} con: {targs}")

    procedure = "\n".join(procedure_lines)

    content = SKILL_MD_TEMPLATE.format(
        name=name,
        description=description,
        category=category,
        tags=", ".join(unique_tools),
        title=title,
        when_to_use=f"Cuando necesites realizar una tarea que involucre: {', '.join(unique_tools)}.",
        procedure=procedure,
        pitfalls="- Revisar que todas las herramientas esten disponibles.\n- Verificar resultados intermedios antes de continuar.",
    )

    return {
        "name": name,
        "content": content,
        "category": category,
        "trigger": f"{len(tool_calls)} tool calls: {', '.join(unique_tools)}",
    }


def skill_manage_bundle(parameters: dict) -> str:
    """
    Manage skill bundles (groups of skills loaded together).
    Actions: create, list, delete, view
    """
    params = parameters or {}
    action = params.get("action", "").lower().strip()

    if action == "create":
        name = params.get("name", "").strip().lower().replace(" ", "-")
        skills = params.get("skills", [])
        description = params.get("description", "")

        if not name or not skills:
            return "Especifica name y skills (lista de nombres de skills)."

        bundle = {
            "name": name,
            "description": description,
            "skills": skills,
        }
        bundle_path = BUNDLES_DIR / f"{name}.yaml"
        try:
            import yaml
            bundle_path.write_text(yaml.dump(bundle, default_flow_style=False, allow_unicode=True), encoding="utf-8")
        except ImportError:
            content = f"name: {name}\ndescription: {description}\nskills:\n"
            for s in skills:
                content += f"  - {s}\n"
            bundle_path.write_text(content, encoding="utf-8")
        return f"Bundle '{name}' creado con {len(skills)} skills."

    if action == "list":
        if not BUNDLES_DIR.exists():
            return "No hay bundles disponibles."
        bundles = list(BUNDLES_DIR.glob("*.yaml")) + list(BUNDLES_DIR.glob("*.yml"))
        if not bundles:
            return "No hay bundles disponibles."
        lines = [f"Bundles disponibles ({len(bundles)}):"]
        for b in bundles:
            try:
                content = b.read_text(encoding="utf-8")
                name_match = re.search(r"name:\s*(.+)", content)
                desc_match = re.search(r"description:\s*(.+)", content)
                n = name_match.group(1).strip() if name_match else b.stem
                d = desc_match.group(1).strip() if desc_match else ""
                lines.append(f"  - {n}: {d}")
            except Exception:
                lines.append(f"  - {b.stem}")
        return "\n".join(lines)

    if action == "delete":
        name = params.get("name", "").strip().lower().replace(" ", "-")
        bundle_path = BUNDLES_DIR / f"{name}.yaml"
        if not bundle_path.exists():
            bundle_path = BUNDLES_DIR / f"{name}.yml"
        if not bundle_path.exists():
            return f"Bundle '{name}' no encontrado."
        bundle_path.unlink()
        return f"Bundle '{name}' eliminado."

    if action == "view":
        name = params.get("name", "").strip().lower().replace(" ", "-")
        bundle_path = BUNDLES_DIR / f"{name}.yaml"
        if not bundle_path.exists():
            bundle_path = BUNDLES_DIR / f"{name}.yml"
        if not bundle_path.exists():
            return f"Bundle '{name}' no encontrado."
        return bundle_path.read_text(encoding="utf-8")

    return f"Accion desconocida: '{action}'. Opciones: create, list, delete, view."
