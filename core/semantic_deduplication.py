"""
semantic_deduplication.py — Deduplicación semántica de conocimiento.

Detecta información duplicada o muy similar en memorias, hechos y notas,
y la fusiona en vez de guardar duplicados.

Funciona con:
  - Memoria episódica (episodic.json)
  - Memoria semántica (semantic.json)
  - Notas del vault de Obsidian
  - Patrones destilados
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from collections import defaultdict

_BASE = Path(__file__).resolve().parent.parent

# Similitud por palabras compartidas (ligero, sin embeddings)
_SIMILARITY_THRESHOLD = 0.55


def _tokenize(text: str) -> set[str]:
    """Tokeniza en palabras normalizadas."""
    text = text.lower()
    text = re.sub(r"[^\w\sáéíóúñü]", " ", text)
    return set(text.split())


def _similarity(a: str, b: str) -> float:
    """Calcula similitud Jaccard simplificada."""
    tokens_a = _tokenize(a)
    tokens_b = _tokenize(b)
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    return len(intersection) / len(union) if union else 0.0


def deduplicate_episodic(filepath: str | Path = None) -> dict:
    """Deduplica memoria episódica.

    Returns:
        dict con: original, deduplicated, removed, groups
    """
    path = Path(filepath or (_BASE / "memory" / "episodic.json"))
    if not path.exists():
        return {"error": "Archivo no encontrado"}

    try:
        entries = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        return {"error": str(e)}

    if not isinstance(entries, list):
        return {"error": "Formato inválido"}

    original = len(entries)
    groups = defaultdict(list)

    # Agrupar por similitud
    used = set()
    for i, e1 in enumerate(entries):
        if i in used:
            continue
        event1 = str(e1.get("event", ""))
        group = [e1]
        used.add(i)

        for j, e2 in enumerate(entries[i + 1:], i + 1):
            if j in used:
                continue
            event2 = str(e2.get("event", ""))
            if _similarity(event1, event2) >= _SIMILARITY_THRESHOLD:
                group.append(e2)
                used.add(j)

        if len(group) > 1:
            # Fusionar: quedarse con el de mayor importancia y combinar eventos
            best = max(group, key=lambda x: x.get("importance", 0))
            combined_events = list({e.get("event", "")[:200] for e in group})
            best["event"] = best.get("event", "")[:300] + " [fusionado de %d entradas]" % len(group)
            best["importance"] = max(e.get("importance", 0.5) for e in group)
            groups[i] = group

        # Reemplazar grupo con la entrada fusionada (la primera/ mejor)
        entries = [e for idx, e in enumerate(entries) if idx not in used or idx == i]
        used = {idx for idx in used if idx <= i}

    # Reconstruir lista limpia
    seen = set()
    cleaned = []
    for e in entries:
        event = str(e.get("event", ""))[:100]
        if event not in seen:
            seen.add(event)
            cleaned.append(e)

    path.write_text(json.dumps(cleaned, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "original": original,
        "deduplicated": len(cleaned),
        "removed": original - len(cleaned),
        "groups_merged": len(groups),
    }


def deduplicate_semantic(filepath: str | Path = None) -> dict:
    """Deduplica memoria semántica (hechos SPO)."""
    path = Path(filepath or (_BASE / "memory" / "semantic.json"))
    if not path.exists():
        return {"error": "Archivo no encontrado"}

    try:
        facts = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        return {"error": str(e)}

    if not isinstance(facts, list):
        return {"error": "Formato inválido"}

    original = len(facts)

    # Deduplicar por subject+predicate similares
    seen = {}
    cleaned = []
    for fact in facts:
        subj = str(fact.get("subject", "")).lower()
        pred = str(fact.get("predicate", "")).lower()
        key = "%s|%s" % (subj, pred)

        if key in seen:
            # Fusionar: mantener la descripción más larga
            existing = seen[key]
            existing_obj = str(existing.get("object", ""))
            new_obj = str(fact.get("object", ""))
            if len(new_obj) > len(existing_obj):
                existing["object"] = fact.get("object", "")
            existing["confidence"] = max(
                existing.get("confidence", 0.5),
                fact.get("confidence", 0.5)
            )
        else:
            seen[key] = fact
            cleaned.append(fact)

    path.write_text(json.dumps(cleaned, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "original": original,
        "deduplicated": len(cleaned),
        "removed": original - len(cleaned),
    }


def deduplicate_all() -> str:
    """Ejecuta deduplicación completa de todas las memorias."""
    results = []
    results.append("Episodic: %s" % json.dumps(deduplicate_episodic()))
    results.append("Semantic: %s" % json.dumps(deduplicate_semantic()))
    return "\n".join(results)
