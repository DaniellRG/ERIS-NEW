"""
dream_consolidation.py — Consolidación de memoria tipo "sueño".

Simula un proceso de consolidación durante idle time:
  - Fusiona recuerdos similares
  - Extrae patrones de experiencias repetidas
  - Prioriza recuerdos por importancia y recencia
  - Genera "sueños" (conexiones creativas entre recuerdos)

Inspirado en cómo el cerebro consolida memoria durante el sueño REM.
"""
from __future__ import annotations

import json
import random
import time
from pathlib import Path
from collections import defaultdict

_BASE = Path(__file__).resolve().parent.parent
_DREAM_LOG = _BASE / "data" / "dream_log.json"
_EPISODIC = _BASE / "memory" / "episodic.json"
_SEMANTIC = _BASE / "memory" / "semantic.json"


def _load_json(path: Path, default=None):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default if default is not None else []


def _save_json(path: Path, data):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def consolidate_memories() -> dict:
    """Consolida memorias episódicas y semánticas.

    Returns:
        dict con: episodic_merged, semantic_merged, patterns_found, dreams_generated
    """
    # 1. Cargar memorias
    episodic = _load_json(_EPISODIC, [])
    semantic = _load_json(_SEMANTIC, [])

    # 2. Consolidar episódica (fusionar similares)
    episodic_merged = _merge_episodic(episodic)

    # 3. Consolidar semántica (deduplicar SPO)
    semantic_merged = _merge_semantic(semantic)

    # 4. Extraer patrones
    patterns = _extract_patterns(episodic)

    # 5. Generar "sueños" (conexiones creativas)
    dreams = _generate_dreams(episodic, semantic)

    # 6. Guardar
    if episodic_merged != episodic:
        _save_json(_EPISODIC, episodic_merged)
    if semantic_merged != semantic:
        _save_json(_SEMANTIC, semantic_merged)

    # 7. Guardar log de sueños
    dream_entry = {
        "timestamp": time.time(),
        "episodic_before": len(episodic),
        "episodic_after": len(episodic_merged),
        "semantic_before": len(semantic),
        "semantic_after": len(semantic_merged),
        "patterns_found": len(patterns),
        "dreams_generated": len(dreams),
        "dreams": dreams[:5],
    }
    dream_log = _load_json(_DREAM_LOG, [])
    dream_log.append(dream_entry)
    if len(dream_log) > 50:
        dream_log = dream_log[-50:]
    _save_json(_DREAM_LOG, dream_log)

    return {
        "episodic_merged": len(episodic) - len(episodic_merged),
        "semantic_merged": len(semantic) - len(semantic_merged),
        "patterns_found": len(patterns),
        "patterns": patterns[:5],
        "dreams_generated": len(dreams),
        "dreams": dreams[:3],
    }


def _merge_episodic(entries: list) -> list:
    """Fusiona entradas episódicas similares."""
    if len(entries) < 2:
        return entries

    # Agrupar por categoría y similitud de evento
    groups = defaultdict(list)
    for e in entries:
        cat = e.get("category", "general")
        event = str(e.get("event", ""))[:100]
        groups[(cat, event[:50])].append(e)

    merged = []
    for key, group in groups.items():
        if len(group) == 1:
            merged.append(group[0])
        else:
            # Fusionar: mayor importancia, combinar eventos
            best = max(group, key=lambda x: x.get("importance", 0.5))
            all_events = list({e.get("event", "")[:200] for e in group})
            best["event"] = all_events[0] if len(all_events) == 1 else (
                best.get("event", "")[:200] + " [consolidado de %d recuerdos]" % len(group)
            )
            best["importance"] = max(e.get("importance", 0.5) for e in group)
            merged.append(best)

    return merged


def _merge_semantic(facts: list) -> list:
    """Fusiona hechos semánticos duplicados."""
    seen = {}
    for fact in facts:
        key = "%s|%s" % (str(fact.get("subject", "")).lower(), str(fact.get("predicate", "")).lower())
        if key in seen:
            existing = seen[key]
            new_obj = str(fact.get("object", ""))
            old_obj = str(existing.get("object", ""))
            if len(new_obj) > len(old_obj):
                existing["object"] = fact.get("object", "")
        else:
            seen[key] = fact
    return list(seen.values())


def _extract_patterns(episodic: list) -> list[dict]:
    """Extrae patrones de experiencias repetidas."""
    # Contar categorías
    cat_counts = defaultdict(int)
    for e in episodic:
        cat = e.get("category", "general")
        cat_counts[cat] += 1

    patterns = []
    for cat, count in cat_counts.items():
        if count >= 3:
            patterns.append({
                "pattern": "Experiencia frecuente en categoría '%s'" % cat,
                "count": count,
                "category": cat,
                "suggestion": "Considerar crear skill o automatizar tareas de '%s'" % cat,
            })

    return patterns


def _generate_dreams(episodic: list, semantic: list) -> list[dict]:
    """Genera "sueños" — conexiones creativas entre recuerdos."""
    dreams = []

    # Tomar recuerdos aleatorios y buscar conexiones
    if len(episodic) >= 3:
        samples = random.sample(episodic, min(5, len(episodic)))
        for i in range(len(samples)):
            for j in range(i + 1, len(samples)):
                e1 = str(samples[i].get("event", ""))
                e2 = str(samples[j].get("event", ""))
                # Buscar palabras en común (conexión)
                words1 = set(e1.lower().split())
                words2 = set(e2.lower().split())
                common = words1 & words2 - {"el", "la", "los", "las", "de", "del", "en", "un", "una", "y", "o", "que", "se", "por", "con", "para", "a", "al"}
                if common:
                    dreams.append({
                        "connection": "Conexión entre '%s' y '%s'" % (
                            e1[:50], e2[:50]),
                        "shared_concepts": list(common)[:5],
                        "insight": "Estos recuerdos comparten: %s" % ", ".join(list(common)[:3]),
                    })

    # Conexiones entre semántica y episódica
    if semantic and episodic:
        semantic_subjects = {str(s.get("subject", "")).lower() for s in semantic}
        for e in episodic[:10]:
            event = str(e.get("event", "")).lower()
            for subj in semantic_subjects:
                if subj and len(subj) > 3 and subj in event:
                    dreams.append({
                        "connection": "Episodio conecta con conocimiento: '%s'" % subj,
                        "shared_concepts": [subj],
                        "insight": "El evento '%s' confirma/conecta con el hecho '%s'" % (
                            event[:50], subj),
                    })
                    break

    return dreams


def get_dream_log() -> list[dict]:
    """Obtiene el historial de consolidaciones/sueños."""
    return _load_json(_DREAM_LOG, [])


def format_dream_report(result: dict) -> str:
    """Formatea reporte de consolidación."""
    lines = [
        "Consolidación de memoria (modo sueño):",
        "  Episódicos fusionados: %d" % result.get("episodic_merged", 0),
        "  Semánticos fusionados: %d" % result.get("semantic_merged", 0),
        "  Patrones encontrados: %d" % result.get("patterns_found", 0),
        "  Sueños generados: %d" % result.get("dreams_generated", 0),
    ]
    if result.get("dreams"):
        lines.append("\nSueños más interesantes:")
        for d in result["dreams"][:3]:
            lines.append("  💭 %s" % d.get("connection", "")[:80])
            if d.get("insight"):
                lines.append("     %s" % d["insight"][:80])
    return "\n".join(lines)
