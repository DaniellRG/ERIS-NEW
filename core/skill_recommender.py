"""
skill_recommender.py — Motor de recomendación de skills para ERIS.

Dado el contexto de una tarea o pregunta del usuario, sugiere automáticamente
qué skills del catálogo cargar. Usa matching de keywords + scoring por relevancia.

Flujo:
  1. Extrae keywords de la tarea (términos significativos)
  2. Compara con metadata de cada skill (name, description, tags, category)
  3. Scoring por relevancia (ponderado: tags > name > description)
  4. Devuelve las N más relevantes con nivel de confianza
"""
from __future__ import annotations

import json
import re
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_SKILLS_DIR = _BASE / "skills"
_CACHE_FILE = _BASE / "data" / "skills_cache.json"

# Palabras vacías (no indexar)
_STOPWORDS = {
    "el", "la", "los", "las", "un", "una", "de", "del", "en", "con", "por",
    "para", "que", "qué", "es", "son", "está", "hay", "tiene", "hacer",
    "puedo", "como", "cómo", "donde", "cuando", "quien", "porque", "por qué",
    "necesito", "quiero", "ayudame", "ayuda", "decime", "mostrame", "creá",
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "dare", "ought",
    "used", "to", "of", "in", "for", "on", "with", "at", "by", "from",
    "as", "into", "through", "during", "before", "after", "above", "below",
    "between", "out", "off", "over", "under", "again", "further", "then",
    "once", "here", "there", "when", "where", "why", "how", "all", "both",
    "each", "few", "more", "most", "other", "some", "such", "no", "nor",
    "not", "only", "own", "same", "so", "than", "too", "very", "just",
    "and", "or", "but", "if", "while", "this", "that", "these", "those",
    "it", "its",
}


def _extract_keywords(text: str) -> list[str]:
    """Extrae keywords significativas de un texto."""
    text = text.lower()
    text = re.sub(r"[^\w\sáéíóúñü]", " ", text)
    words = text.split()
    return [w for w in words if len(w) > 2 and w not in _STOPWORDS]


def _load_skills_index() -> list[dict]:
    """Carga el índice de skills desde skills_index.json o escanea directorios."""
    # Intentar cache
    if _CACHE_FILE.exists():
        try:
            data = json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
            if data:
                return data
        except Exception:
            pass

    skills = []

    # Escanear skills de usuario
    for skill_dir in sorted(_SKILLS_DIR.glob("user_created/*/")):
        skill_file = skill_dir / "SKILL.md"
        if skill_file.exists():
            meta = _parse_skill_frontmatter(skill_file)
            meta["source"] = "user_created"
            meta["path"] = str(skill_file)
            skills.append(meta)

    # Escanear skills builtin
    for skill_dir in sorted(_SKILLS_DIR.glob("builtin/*/")):
        skill_file = skill_dir / "SKILL.md"
        if skill_file.exists():
            meta = _parse_skill_frontmatter(skill_file)
            meta["source"] = "builtin"
            meta["path"] = str(skill_file)
            skills.append(meta)

    # Guardar cache
    try:
        _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _CACHE_FILE.write_text(json.dumps(skills, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

    return skills


def _parse_skill_frontmatter(skill_file: Path) -> dict:
    """Parsea el frontmatter YAML de un SKILL.md sin depender de PyYAML."""
    text = skill_file.read_text(encoding="utf-8", errors="replace")
    meta = {"name": skill_file.parent.name, "description": "", "tags": [], "category": ""}

    if text.startswith("---"):
        end = text.find("---", 3)
        if end > 0:
            fm = text[3:end].strip()
            for line in fm.splitlines():
                if ":" in line:
                    key, _, val = line.partition(":")
                    key = key.strip().lower()
                    val = val.strip()
                    if key == "name":
                        meta["name"] = val
                    elif key == "description":
                        meta["description"] = val
                    elif key == "category":
                        meta["category"] = val
                    elif key == "tags":
                        # Parsear [tag1, tag2, ...]
                        val = val.strip("[]")
                        meta["tags"] = [t.strip() for t in val.split(",") if t.strip()]

    # Agregar keywords del nombre del directorio
    meta["dir_name"] = skill_file.parent.name
    return meta


def _score_skill(skill: dict, keywords: list[str]) -> float:
    """Calcula un score de relevancia entre keywords y una skill."""
    score = 0.0

    skill_name = skill.get("name", "").lower()
    skill_dir = skill.get("dir_name", "").lower()
    skill_desc = skill.get("description", "").lower()
    skill_tags = [t.lower() for t in skill.get("tags", [])]
    skill_cat = skill.get("category", "").lower()

    for kw in keywords:
        # Match en tags (mayor peso)
        for tag in skill_tags:
            if kw in tag or tag in kw:
                score += 3.0
        # Match en nombre
        if kw in skill_name or skill_name in kw:
            score += 2.5
        # Match en dir_name
        if kw in skill_dir or skill_dir in kw:
            score += 2.0
        # Match en descripción
        if kw in skill_desc:
            score += 1.0
        # Match en categoría
        if kw in skill_cat:
            score += 1.5

    return score


def recommend_skills(query: str, top_n: int = 3, min_score: float = 2.0) -> list[dict]:
    """Recomienda skills relevantes para una tarea dada.

    Args:
        query: Texto de la tarea/pregunta del usuario.
        top_n: Máximo de skills a devolver.
        min_score: Score mínimo para considerar una skill.

    Returns:
        Lista de dicts con: name, description, score, confidence, source, path
    """
    keywords = _extract_keywords(query)
    if not keywords:
        return []

    skills = _load_skills_index()
    if not skills:
        return []

    scored = []
    for skill in skills:
        score = _score_skill(skill, keywords)
        if score >= min_score:
            # Normalizar confianza (0-1)
            max_possible = len(keywords) * 7.0
            confidence = min(score / max_possible, 1.0) if max_possible > 0 else 0
            scored.append({
                "name": skill.get("name", ""),
                "description": skill.get("description", "")[:200],
                "score": round(score, 2),
                "confidence": round(confidence, 3),
                "source": skill.get("source", ""),
                "path": skill.get("path", ""),
            })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_n]


def format_recommendation(recommendations: list[dict]) -> str:
    """Formatea las recomendaciones para mostrar al agente/usuario."""
    if not recommendations:
        return "No se encontraron skills relevantes para esta tarea."

    lines = ["Skills recomendadas para esta tarea:"]
    for i, rec in enumerate(recommendations, 1):
        conf = rec["confidence"]
        conf_label = "alta" if conf > 0.5 else "media" if conf > 0.25 else "baja"
        lines.append(
            f"  {i}. {rec['name']} (confianza: {conf_label}, score: {rec['score']})"
        )
        if rec["description"]:
            lines.append(f"     {rec['description'][:100]}")
        lines.append(
            f"     Cargar con: skill_manage(action='view', name='{rec['name']}')"
        )
    return "\n".join(lines)


def refresh_cache():
    """Fuerza la recarga del índice de skills."""
    if _CACHE_FILE.exists():
        _CACHE_FILE.unlink()
    _load_skills_index()
    return "Cache de skills recargado."
