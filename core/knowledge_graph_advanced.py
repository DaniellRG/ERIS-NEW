"""
ERIS Knowledge Graph — Grafo de relaciones entre entidades extraídas del vault y conversaciones.
Almacena y consulta relaciones (entidad → relación → entidad).
"""
import json
import re
import time
from pathlib import Path
from collections import defaultdict

_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "knowledge_graph"
_DATA_DIR.mkdir(parents=True, exist_ok=True)

_GRAPH_FILE = _DATA_DIR / "graph.json"


def _load_graph() -> dict:
    if _GRAPH_FILE.exists():
        with open(_GRAPH_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"entities": {}, "relations": [], "last_updated": None}


def _save_graph(graph: dict):
    graph["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(_GRAPH_FILE, "w", encoding="utf-8") as f:
        json.dump(graph, f, ensure_ascii=False, indent=2)


def add_entity(name: str, entity_type: str = "concept", metadata: dict = None) -> dict:
    graph = _load_graph()
    key = name.lower().strip()
    if key not in graph["entities"]:
        graph["entities"][key] = {
            "name": name,
            "type": entity_type,
            "metadata": metadata or {},
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "mentions": 1,
        }
    else:
        graph["entities"][key]["mentions"] += 1
        if metadata:
            graph["entities"][key]["metadata"].update(metadata)
    _save_graph(graph)
    return {"ok": True, "entity": name}


def add_relation(source: str, relation: str, target: str, context: str = "") -> dict:
    graph = _load_graph()
    graph["relations"].append({
        "source": source.lower().strip(),
        "relation": relation.lower().strip(),
        "target": target.lower().strip(),
        "context": context,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    })
    # Ensure entities exist
    for name, etype in [(source, "entity"), (target, "entity")]:
        key = name.lower().strip()
        if key not in graph["entities"]:
            graph["entities"][key] = {
                "name": name, "type": etype, "metadata": {},
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S"), "mentions": 1,
            }
    _save_graph(graph)
    return {"ok": True, "relation": f"{source} →[{relation}]→ {target}"}


def query_entity(name: str) -> dict:
    graph = _load_graph()
    key = name.lower().strip()
    entity = graph["entities"].get(key)
    if not entity:
        return {"found": False, "name": name}

    related = []
    for r in graph["relations"]:
        if r["source"] == key:
            related.append({"type": "outgoing", "relation": r["relation"], "target": r["target"], "context": r.get("context", "")})
        elif r["target"] == key:
            related.append({"type": "incoming", "relation": r["relation"], "source": r["source"], "context": r.get("context", "")})

    return {"found": True, "entity": entity, "relations": related, "total_relations": len(related)}


def search_graph(query: str, limit: int = 10) -> list:
    """Search entities by name/type."""
    graph = _load_graph()
    query_lower = query.lower()
    results = []
    for key, entity in graph["entities"].items():
        if query_lower in key or query_lower in entity.get("type", ""):
            results.append(entity)
        if len(results) >= limit:
            break
    return results


def get_stats() -> dict:
    graph = _load_graph()
    types = defaultdict(int)
    for e in graph["entities"].values():
        types[e.get("type", "unknown")] += 1
    return {
        "total_entities": len(graph["entities"]),
        "total_relations": len(graph["relations"]),
        "entity_types": dict(types),
        "last_updated": graph.get("last_updated"),
    }


def knowledge_graph_tool(parameters: dict = None, player=None) -> str:
    """Tool entry point."""
    params = parameters or {}
    action = params.get("action", "stats").lower()

    if action == "add_entity":
        name = params.get("name", "")
        if not name:
            return "Necesito 'name' de la entidad."
        etype = params.get("type", "concept")
        result = add_entity(name, etype)
        return f"Entidad '{name}' ({etype}) agregada." if result["ok"] else "Error."

    elif action == "add_relation":
        source, relation, target = params.get("source", ""), params.get("relation", ""), params.get("target", "")
        if not all([source, relation, target]):
            return "Necesito 'source', 'relation' y 'target'."
        result = add_relation(source, relation, target, params.get("context", ""))
        return f"Relación: {result['relation']}" if result["ok"] else "Error."

    elif action == "query":
        name = params.get("name", "")
        if not name:
            return "Necesito 'name' para consultar."
        result = query_entity(name)
        if not result["found"]:
            return f"Entidad '{name}' no encontrada."
        output = f"Entidad: {result['entity']['name']} (tipo: {result['entity']['type']})\n"
        output += f"Menciones: {result['entity']['mentions']}\n"
        if result["relations"]:
            output += f"Relaciones ({result['total_relations']}):\n"
            for r in result["relations"][:10]:
                if r["type"] == "outgoing":
                    output += f"  → {r['relation']} → {r['target']}\n"
                else:
                    output += f"  ← {r['relation']} ← {r['source']}\n"
        return output

    elif action == "search":
        query = params.get("query", "")
        if not query:
            return "Necesito 'query' para buscar."
        results = search_graph(query)
        if not results:
            return f"Sin resultados para '{query}'."
        return f"Entidades ({len(results)}):\n" + "\n".join(
            f"  - {e['name']} ({e['type']}, {e['mentions']} menciones)" for e in results
        )

    elif action == "stats":
        stats = get_stats()
        return (f"Knowledge Graph: {stats['total_entities']} entidades, {stats['total_relations']} relaciones\n"
                f"Tipos: {stats['entity_types']}\nÚltima actualización: {stats['last_updated']}")

    return f"Acción '{action}' no reconocida. Usa: add_entity, add_relation, query, search, stats"
