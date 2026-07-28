"""
skill_marketplace.py — Marketplace de skills: compartir y descargar skills de otros usuarios.
Permite publicar, buscar, instalar, y actualizar skills personalizados.
"""
import json
import hashlib
from pathlib import Path
from datetime import datetime

_BASE = Path(__file__).resolve().parent.parent
_SKILLS_DIR = _BASE / "data" / "marketplace_skills"
_MARKETPLACE_INDEX = _SKILLS_DIR / "_index.json"
_PUBLISHED_DIR = _BASE / "data" / "published_skills"


def skill_marketplace(parameters: dict = None, player=None) -> str:
    """
    Marketplace de skills.
    Acciones: search, install, list, publish, update, remove, info, rate, featured, my_skills
    """
    params = parameters or {}
    action = params.get("action", "search").lower()
    _SKILLS_DIR.mkdir(parents=True, exist_ok=True)

    if action == "search":
        return _search_skills(params)
    elif action == "install":
        return _install_skill(params)
    elif action == "list":
        return _list_available(params)
    elif action == "publish":
        return _publish_skill(params)
    elif action == "update":
        return _update_skill(params)
    elif action == "remove":
        return _remove_skill(params)
    elif action == "info":
        return _skill_info(params)
    elif action == "rate":
        return _rate_skill(params)
    elif action == "featured":
        return _featured_skills()
    elif action == "my_skills":
        return _my_skills()
    elif action == "status":
        return _get_status()
    return "Acciones: search, install, list, publish, update, remove, info, rate, featured, my_skills, status"


def _search_skills(params: dict) -> str:
    query = params.get("query", "").lower()
    category = params.get("category", "")
    index = _load_index()
    skills = index.get("skills", [])

    results = []
    for skill in skills:
        name = skill.get("name", "").lower()
        desc = skill.get("description", "").lower()
        tags = [t.lower() for t in skill.get("tags", [])]
        cat = skill.get("category", "")

        if query and query not in name and query not in desc and not any(query in t for t in tags):
            continue
        if category and cat != category:
            continue
        results.append(skill)

    if not results:
        return "No se encontraron skills para: {}".format(query or category)

    results.sort(key=lambda x: x.get("rating", 0), reverse=True)
    lines = ["Skills encontrados ({}):".format(len(results))]
    for s in results[:10]:
        lines.append("  {} | ⭐{} | v{} | {}".format(
            s.get("name"), s.get("rating", 0), s.get("version", "1.0"),
            s.get("description", "")[:40]))
    return "\n".join(lines)


def _install_skill(params: dict) -> str:
    name = params.get("name", "")
    if not name:
        return "Error: se requiere 'name'"

    index = _load_index()
    skill = next((s for s in index.get("skills", []) if s.get("name") == name), None)
    if not skill:
        return "Skill no encontrado: {}".format(name)

    skill_dir = _SKILLS_DIR / name
    skill_dir.mkdir(parents=True, exist_ok=True)

    skill_meta = {
        "name": name,
        "version": skill.get("version", "1.0"),
        "installed": datetime.now().isoformat(),
        "description": skill.get("description", ""),
        "author": skill.get("author", "unknown"),
        "category": skill.get("category", ""),
        "actions": skill.get("actions", []),
        "config": skill.get("default_config", {}),
    }

    (skill_dir / "skill.json").write_text(json.dumps(skill_meta, indent=2, ensure_ascii=False), encoding="utf-8")

    if skill.get("code"):
        (skill_dir / "main.py").write_text(skill["code"], encoding="utf-8")

    return "Skill '{}' v{} instalado".format(name, skill.get("version", "1.0"))


def _list_available(params: dict) -> str:
    index = _load_index()
    skills = index.get("skills", [])
    if not skills:
        return "No hay skills disponibles"

    category = params.get("category", "")
    if category:
        skills = [s for s in skills if s.get("category") == category]

    installed = set(f.parent.name for f in _SKILLS_DIR.glob("*/skill.json"))
    lines = ["Skills disponibles ({}):".format(len(skills))]
    for s in sorted(skills, key=lambda x: x.get("rating", 0), reverse=True):
        status = " [INSTALADO]" if s.get("name") in installed else ""
        lines.append("  {} | ⭐{} | {}{}".format(
            s.get("name"), s.get("rating", 0), s.get("description", "")[:40], status))
    return "\n".join(lines)


def _publish_skill(params: dict) -> str:
    name = params.get("name", "")
    description = params.get("description", "")
    if not name or not description:
        return "Error: se requiere 'name' y 'description'"

    skill = {
        "name": name,
        "description": description,
        "version": params.get("version", "1.0"),
        "author": params.get("author", "ERIS_user"),
        "category": params.get("category", "general"),
        "tags": params.get("tags", []),
        "actions": params.get("actions", []),
        "code": params.get("code", ""),
        "default_config": params.get("config", {}),
        "published": datetime.now().isoformat(),
        "rating": 0,
        "downloads": 0,
    }

    index = _load_index()
    existing = next((i for i, s in enumerate(index.get("skills", [])) if s.get("name") == name), None)
    if existing is not None:
        index["skills"][existing] = skill
    else:
        index.setdefault("skills", []).append(skill)

    _save_index(index)

    pub_dir = _PUBLISHED_DIR / name
    pub_dir.mkdir(parents=True, exist_ok=True)
    (pub_dir / "skill.json").write_text(json.dumps(skill, indent=2, ensure_ascii=False), encoding="utf-8")

    return "Skill '{}' publicado v{}".format(name, skill["version"])


def _update_skill(params: dict) -> str:
    name = params.get("name", "")
    if not name:
        return "Error: se requiere 'name'"

    index = _load_index()
    skill = next((s for s in index.get("skills", []) if s.get("name") == name), None)
    if not skill:
        return "Skill no encontrado: {}".format(name)

    for key in ["description", "version", "tags", "actions", "code", "config"]:
        if key in params:
            skill[key] = params[key]

    skill["updated"] = datetime.now().isoformat()
    _save_index(index)
    return "Skill '{}' actualizado a v{}".format(name, skill.get("version", "?"))


def _remove_skill(params: dict) -> str:
    name = params.get("name", "")
    if not name:
        return "Error: se requiere 'name'"

    index = _load_index()
    index["skills"] = [s for s in index.get("skills", []) if s.get("name") != name]
    _save_index(index)

    skill_dir = _SKILLS_DIR / name
    if skill_dir.exists():
        import shutil
        shutil.rmtree(str(skill_dir))

    return "Skill '{}' removido".format(name)


def _skill_info(params: dict) -> str:
    name = params.get("name", "")
    if not name:
        return "Error: se requiere 'name'"

    index = _load_index()
    skill = next((s for s in index.get("skills", []) if s.get("name") == name), None)
    if not skill:
        return "Skill no encontrado: {}".format(name)

    lines = [
        "Skill: {}".format(name),
        "  Versión: {}".format(skill.get("version", "?")),
        "  Autor: {}".format(skill.get("author", "?")),
        "  Categoría: {}".format(skill.get("category", "?")),
        "  Rating: ⭐{}".format(skill.get("rating", 0)),
        "  Descargas: {}".format(skill.get("downloads", 0)),
        "  Descripción: {}".format(skill.get("description", "")),
        "  Tags: {}".format(", ".join(skill.get("tags", []))),
        "  Acciones: {}".format(", ".join(skill.get("actions", []))),
    ]
    return "\n".join(lines)


def _rate_skill(params: dict) -> str:
    name = params.get("name", "")
    rating = float(params.get("rating", 0))
    if not name:
        return "Error: se requiere 'name'"
    if not 0 <= rating <= 5:
        return "Rating debe ser entre 0 y 5"

    index = _load_index()
    skill = next((s for s in index.get("skills", []) if s.get("name") == name), None)
    if not skill:
        return "Skill no encontrado"

    old_rating = skill.get("rating", 0)
    skill["rating"] = round((old_rating + rating) / 2, 1)
    _save_index(index)
    return "Skill '{}' calificado: {} → {}".format(name, old_rating, skill["rating"])


def _featured_skills() -> str:
    index = _load_index()
    skills = index.get("skills", [])
    featured = sorted(skills, key=lambda x: (x.get("rating", 0), x.get("downloads", 0)), reverse=True)[:5]

    if not featured:
        return "No hay skills destacados"

    lines = ["Skills destacados:"]
    for s in featured:
        lines.append("  ⭐{} | {} | {}".format(
            s.get("rating", 0), s.get("name"), s.get("description", "")[:40]))
    return "\n".join(lines)


def _my_skills() -> str:
    installed = list(_SKILLS_DIR.glob("*/skill.json"))
    if not installed:
        return "No tienes skills instalados"

    lines = ["Mis skills ({}):".format(len(installed))]
    for f in installed:
        try:
            skill = json.loads(f.read_text(encoding="utf-8"))
            lines.append("  {} v{} | {}".format(
                skill.get("name"), skill.get("version", "?"),
                skill.get("description", "")[:40]))
        except Exception:
            lines.append("  {} (error leyendo)".format(f.parent.name))
    return "\n".join(lines)


def _get_status() -> str:
    index = _load_index()
    total = len(index.get("skills", []))
    installed = len(list(_SKILLS_DIR.glob("*/skill.json")))
    return "Marketplace: {} skills disponibles | {} instalados".format(total, installed)


def _load_index():
    if _MARKETPLACE_INDEX.exists():
        try:
            return json.loads(_MARKETPLACE_INDEX.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"skills": []}


def _save_index(index):
    _MARKETPLACE_INDEX.parent.mkdir(parents=True, exist_ok=True)
    _MARKETPLACE_INDEX.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")
