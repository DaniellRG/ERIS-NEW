"""
memory_consolidation.py — Consolidación y limpieza periódica de memorias.
Limpia episodios viejos, fusiona hechos duplicados, optimiza storage.
"""
import json
import time
from pathlib import Path
from datetime import datetime, timedelta

_BASE = Path(__file__).resolve().parent.parent
_MEMORY_DIR = _BASE / "memory"
_EPISODIC_FILE = _MEMORY_DIR / "episodic.json"
_SEMANTIC_FILE = _MEMORY_DIR / "semantic.json"
_LONG_TERM_FILE = _MEMORY_DIR / "long_term.json"
_KNOWLEDGE_GRAPH_FILE = _MEMORY_DIR / "knowledge_graph.json"
CONSOLIDATION_LOG = _BASE / "data" / "memory_consolidation.json"


def _load_json(path):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return [] if "episodic" in str(path) or "semantic" in str(path) else {}
    return [] if "episodic" in str(path) or "semantic" in str(path) else {}


def _save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def memory_consolidate(parameters: dict = None, player=None) -> str:
    """
    Consolida y limpia todas las memorias de ERIS.
    Acciones: full, episodic, semantic, long_term, status, auto
    """
    params = parameters or {}
    action = params.get("action", "full").lower()

    if action == "full":
        return _consolidate_all()
    elif action == "episodic":
        return _clean_episodic()
    elif action == "semantic":
        return _clean_semantic()
    elif action == "long_term":
        return _clean_long_term()
    elif action == "status":
        return _get_status()
    elif action == "auto":
        return _auto_consolidate()
    elif action == "deep":
        return _consolidate_episodic_deep()
    return "Acciones: full, episodic, semantic, long_term, status, auto, deep"


def _consolidate_all() -> str:
    results = []
    results.append(_clean_episodic())
    results.append(_clean_semantic())
    results.append(_clean_long_term())
    _log_consolidation("full", results)
    return "\n".join(results)


def _clean_episodic() -> str:
    episodes = _load_json(_EPISODIC_FILE)
    if not isinstance(episodes, list):
        return "Episodic: formato inválido"

    original_count = len(episodes)
    cleaned = []

    for ep in episodes:
        event = ep.get("event", "")
        importance = ep.get("importance", 0.5)
        timestamp = ep.get("timestamp", 0)

        if not event or len(event) < 10:
            continue
        if "no results" in event.lower() or "error" in event.lower() or "failed" in event.lower():
            continue
        if importance < 0.3:
            continue
        age_days = (time.time() - timestamp) / 86400 if timestamp else 999
        if age_days > 30 and importance < 0.6:
            continue
        cleaned.append(ep)

    cleaned.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
    cleaned = cleaned[:500]

    _save_json(_EPISODIC_FILE, cleaned)
    removed = original_count - len(cleaned)
    return "Episodic: {} → {} ({} removidos: vacíos, errores, viejos)".format(
        original_count, len(cleaned), removed)


def _consolidate_episodic_deep() -> str:
    """Consolidación profunda: agrupa episodios por tema y crea resúmenes
    compactos que preservan la información importante sin el ruido."""
    episodes = _load_json(_EPISODIC_FILE)
    if not isinstance(episodes, list) or len(episodes) < 10:
        return "Episodic: pocos episodios, no necesita consolidación profunda"

    # Agrupar por contexto/tema
    from collections import defaultdict
    groups = defaultdict(list)
    for ep in episodes:
        ctx = ep.get("context", "general")
        groups[ctx].append(ep)

    consolidated = []
    total_before = len(episodes)

    for ctx, eps in groups.items():
        if len(eps) <= 5:
            consolidated.extend(eps)
            continue

        # Tomar los más recientes y los de mayor importancia
        eps.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
        keep = eps[:5]  # Mantener 5 recientes
        rest = eps[5:]

        # Consolidar el resto en un resumen
        events = [e.get("event", "")[:200] for e in rest if e.get("event")]
        if events:
            summary_text = "Resumen de {} episodios previos en '{}': {}".format(
                len(rest), ctx, "; ".join(events[:10]))
            summary_ep = {
                "id": f"consolidated_{ctx}_{int(time.time())}",
                "event": summary_text,
                "context": ctx,
                "importance": 0.6,
                "timestamp": time.time(),
                "datetime": datetime.now().isoformat(),
                "consolidated": True,
                "original_count": len(rest),
            }
            keep.append(summary_ep)

        consolidated.extend(keep)

    _save_json(_EPISODIC_FILE, consolidated)
    return "Episodic consolidación profunda: {} → {} episodios ({} grupos)".format(
        total_before, len(consolidated), len(groups))


def _clean_semantic() -> str:
    facts = _load_json(_SEMANTIC_FILE)
    if not isinstance(facts, list):
        return "Semantic: formato inválido"

    original_count = len(facts)
    seen = {}
    cleaned = []

    for fact in facts:
        subj = str(fact.get("subject", "")).strip()[:100]
        pred = str(fact.get("predicate", "")).strip()[:50]
        obj = str(fact.get("object", "")).strip()[:200]
        key = "{}|{}|{}".format(subj.lower(), pred.lower(), obj.lower()[:50])

        if key in seen:
            existing = seen[key]
            new_conf = max(existing.get("confidence", 0), fact.get("confidence", 0))
            existing["confidence"] = new_conf
            existing["sources"] = list(set(existing.get("sources", []) + fact.get("sources", [])))
        else:
            if len(subj) > 2 and len(obj) > 5:
                fact["subject"] = subj
                fact["predicate"] = pred
                fact["object"] = obj
                seen[key] = fact
                cleaned.append(fact)

    _save_json(_SEMANTIC_FILE, cleaned)
    return "Semantic: {} → {} ({} duplicados fusionados)".format(
        original_count, len(cleaned), original_count - len(cleaned))


def _clean_long_term() -> str:
    data = _load_json(_LONG_TERM_FILE)
    if not isinstance(data, dict):
        return "Long-term: formato inválido"

    total_before = 0
    total_after = 0
    empty_cats = []

    for cat, entries in list(data.items()):
        if not isinstance(entries, dict):
            continue
        total_before += len(entries)
        cleaned = {}
        for key, val in entries.items():
            if isinstance(val, dict):
                value = str(val.get("value", ""))
                if len(value) > 5 and value != "None" and value != "":
                    cleaned[key] = val
            elif isinstance(val, str) and len(val) > 3:
                cleaned[key] = {"value": val}
        total_after += len(cleaned)
        if not cleaned:
            empty_cats.append(cat)
        data[cat] = cleaned

    _save_json(_LONG_TERM_FILE, data)
    return "Long-term: {} → {} entradas ({} categorías vacías marcadas)".format(
        total_before, total_after, len(empty_cats))


def _auto_consolidate() -> str:
    status = _get_status_summary()
    actions = []
    if status["episodic_errors"] > 3:
        actions.append("clean_episodic")
    if status["semantic_duplicates"] > 2:
        actions.append("clean_semantic")
    if status["total_size_kb"] > 500:
        actions.append("clean_all")

    if not actions:
        return "Auto: memorias en buen estado, no necesita limpieza"

    results = []
    if "clean_episodic" in actions:
        results.append(_clean_episodic())
    if "clean_semantic" in actions:
        results.append(_clean_semantic())
    if "clean_all" in actions:
        results.append(_clean_long_term())

    return "Auto-consolidación: {}\n{}".format(", ".join(actions), "\n".join(results))


def _get_status() -> str:
    s = _get_status_summary()
    lines = [
        "Memory Consolidation Status:",
        "  Episodic: {} entradas ({} errores/vacíos)".format(s["episodic_total"], s["episodic_errors"]),
        "  Semantic: {} hechos ({} posibles duplicados)".format(s["semantic_total"], s["semantic_duplicates"]),
        "  Long-term: {} entradas en {} categorías".format(s["longterm_total"], s["longterm_cats"]),
        "  Knowledge Graph: {} nodos, {} edges".format(s["kg_nodes"], s["kg_edges"]),
        "  Tamaño total: {:.1f} KB".format(s["total_size_kb"]),
        "  Última consolidación: {}".format(s["last_consolidation"]),
    ]
    return "\n".join(lines)


def _get_status_summary() -> dict:
    episodes = _load_json(_EPISODIC_FILE)
    facts = _load_json(_SEMANTIC_FILE)
    longterm = _load_json(_LONG_TERM_FILE)
    kg = _load_json(_KNOWLEDGE_GRAPH_FILE)

    errors = 0
    if isinstance(episodes, list):
        for ep in episodes:
            ev = ep.get("event", "").lower()
            if "no results" in ev or "error" in ev or "failed" in ev or len(ev) < 10:
                errors += 1

    dupes = 0
    if isinstance(facts, list):
        seen = set()
        for f in facts:
            key = "{}|{}|{}".format(
                str(f.get("subject", "")).lower()[:50],
                str(f.get("predicate", "")).lower()[:30],
                str(f.get("object", "")).lower()[:50])
            if key in seen:
                dupes += 1
            seen.add(key)

    total_size = 0
    for f in [_EPISODIC_FILE, _SEMANTIC_FILE, _LONG_TERM_FILE, _KNOWLEDGE_GRAPH_FILE]:
        if f.exists():
            total_size += f.stat().st_size

    lt_total = 0
    lt_cats = 0
    if isinstance(longterm, dict):
        for cat, entries in longterm.items():
            if isinstance(entries, dict):
                lt_total += len(entries)
                lt_cats += 1

    kg_nodes = 0
    kg_edges = 0
    if isinstance(kg, dict):
        kg_nodes = len(kg.get("nodes", {}))
        kg_edges = len(kg.get("edges", []))

    last_con = "nunca"
    if CONSOLIDATION_LOG.exists():
        try:
            log = json.loads(CONSOLIDATION_LOG.read_text(encoding="utf-8"))
            last_con = log.get("last_consolidation", "nunca")
        except Exception:
            pass

    return {
        "episodic_total": len(episodes) if isinstance(episodes, list) else 0,
        "episodic_errors": errors,
        "semantic_total": len(facts) if isinstance(facts, list) else 0,
        "semantic_duplicates": dupes,
        "longterm_total": lt_total,
        "longterm_cats": lt_cats,
        "kg_nodes": kg_nodes,
        "kg_edges": kg_edges,
        "total_size_kb": total_size / 1024,
        "last_consolidation": last_con,
    }


def _log_consolidation(action, results):
    log = {"last_consolidation": datetime.now().isoformat(), "action": action, "results": results}
    _save_json(CONSOLIDATION_LOG, log)
