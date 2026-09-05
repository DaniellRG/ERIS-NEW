"""
knowledge_graph.py — Grafo de conocimiento: visualiza relaciones entre documentos RAG.
Construye nodos y aristas basado en contenido, similitud y co-ocurrencia.
"""
import json
import math
from pathlib import Path
from datetime import datetime
from collections import defaultdict

_BASE = Path(__file__).resolve().parent.parent
_KG_FILE = _BASE / "data" / "knowledge_graph.json"


def knowledge_graph(parameters: dict = None, player=None) -> str:
    """Grafo de conocimiento."""
    params = parameters or {}
    action = params.get("action", "build").lower()

    if action == "build":
        return _build_graph(params)
    elif action == "status":
        return _get_status()
    elif action == "nodes":
        return _list_nodes(params)
    elif action == "edges":
        return _list_edges(params)
    elif action == "neighbors":
        return _get_neighbors(params)
    elif action == "clusters":
        return _get_clusters()
    elif action == "search":
        return _search_graph(params)
    elif action == "shortest_path":
        return _shortest_path(params)
    elif action == "stats":
        return _get_stats()
    elif action == "export_html":
        return _export_html()
    elif action == "export_json":
        return _export_json()
    elif action == "suggest":
        return _suggest_connections(params)
    return "Acciones: build, status, nodes, edges, neighbors, clusters, search, shortest_path, stats, export_html, export_json, suggest"


def _load_knowledge_docs() -> list:
    """Carga documentos del knowledge base."""
    docs = []
    kb_dir = _BASE / "data" / "knowledge"
    if kb_dir.exists():
        for f in sorted(kb_dir.glob("*.md")):
            try:
                content = f.read_text(encoding="utf-8")
                lines = content.split("\n")
                title = lines[0].lstrip("# ").strip() if lines else f.stem
                words = set(content.lower().split())
                bigrams = set()
                word_list = [w.strip(".,;:!?()[]{}\"'") for w in content.lower().split() if len(w) > 3]
                for i in range(len(word_list) - 1):
                    bigrams.add("{} {}".format(word_list[i], word_list[i + 1]))
                docs.append({
                    "id": f.stem,
                    "title": title,
                    "file": f.name,
                    "size": len(content),
                    "words": words,
                    "bigrams": bigrams,
                    "word_list": word_list,
                })
            except OSError:
                pass
    return docs


def _compute_similarity(doc1: dict, doc2: dict) -> float:
    """Jaccard similarity entre dos documentos."""
    w1 = doc1.get("words", set())
    w2 = doc2.get("words", set())
    if not w1 or not w2:
        return 0.0
    intersection = len(w1 & w2)
    union = len(w1 | w2)
    return intersection / union if union > 0 else 0.0


def _build_graph(params: dict) -> str:
    """Construye el grafo de conocimiento."""
    docs = _load_knowledge_docs()
    if not docs:
        return "No hay documentos en data/knowledge/"

    threshold = float(params.get("threshold", 0.05))
    nodes = []
    edges = []

    for doc in docs:
        nodes.append({
            "id": doc["id"],
            "label": doc["title"],
            "file": doc["file"],
            "size": doc["size"],
            "word_count": len(doc["word_list"]),
        })

    for i, d1 in enumerate(docs):
        for j, d2 in enumerate(docs):
            if i >= j:
                continue
            sim = _compute_similarity(d1, d2)
            if sim >= threshold:
                shared_words = d1["words"] & d2["words"]
                important = [w for w in shared_words if len(w) > 4][:5]
                edges.append({
                    "source": d1["id"],
                    "target": d2["id"],
                    "weight": round(sim, 4),
                    "shared_words": important,
                })

    graph = {
        "nodes": nodes,
        "edges": edges,
        "doc_count": len(nodes),
        "edge_count": len(edges),
        "threshold": threshold,
        "built_at": datetime.now().isoformat(),
    }
    _save_graph(graph)

    lines = [
        "═══ GRAFO DE CONOCIMIENTO CONSTRUIDO ═══",
        "",
        "  Nodos:    {} documentos".format(len(nodes)),
        "  Aristas:  {} conexiones (threshold={})".format(len(edges), threshold),
        "",
    ]
    if edges:
        top = sorted(edges, key=lambda e: e["weight"], reverse=True)[:5]
        lines.append("  Top conexiones:")
        for e in top:
            lines.append("    {} <-> {} (sim={:.3f})".format(
                e["source"], e["target"], e["weight"]))
            if e["shared_words"]:
                lines.append("      Shared: {}".format(", ".join(e["shared_words"][:3])))
    lines.append("")
    lines.append("  Usa 'export_html' para visualizar el grafo")
    return "\n".join(lines)


def _list_nodes(params: dict) -> str:
    graph = _load_graph()
    nodes = graph.get("nodes", [])
    if not nodes:
        return "Grafo vacío. Ejecuta 'build' primero"
    limit = int(params.get("limit", 20))
    lines = ["═══ NODOS ({}/{}) ═══".format(min(limit, len(nodes)), len(nodes)), ""]
    for n in nodes[:limit]:
        lines.append("  {} — {} ({} words, {} bytes)".format(
            n["id"], n.get("label", "?"), n.get("word_count", "?"), n.get("size", "?")))
    return "\n".join(lines)


def _list_edges(params: dict) -> str:
    graph = _load_graph()
    edges = graph.get("edges", [])
    if not edges:
        return "Sin aristas. Ejecuta 'build' primero"
    limit = int(params.get("limit", 20))
    lines = ["═══ ARISTAS ({}/{}) ═══".format(min(limit, len(edges)), len(edges)), ""]
    for e in sorted(edges, key=lambda x: x["weight"], reverse=True)[:limit]:
        lines.append("  {} <-> {} (peso={:.4f})".format(
            e["source"], e["target"], e["weight"]))
        if e.get("shared_words"):
            lines.append("    keywords: {}".format(", ".join(e["shared_words"][:5])))
    return "\n".join(lines)


def _get_neighbors(params: dict) -> str:
    node_id = params.get("node", "")
    if not node_id:
        return "Error: se requiere 'node'"
    graph = _load_graph()
    edges = graph.get("edges", [])
    neighbors = []
    for e in edges:
        if e["source"] == node_id:
            neighbors.append((e["target"], e["weight"]))
        elif e["target"] == node_id:
            neighbors.append((e["source"], e["weight"]))
    if not neighbors:
        return "Sin vecinos para '{}'".format(node_id)
    neighbors.sort(key=lambda x: x[1], reverse=True)
    lines = ["═══ VECINOS DE '{}' ═══".format(node_id), ""]
    for nid, w in neighbors:
        lines.append("  {} (sim={:.4f})".format(nid, w))
    return "\n".join(lines)


def _get_clusters() -> str:
    graph = _load_graph()
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])

    adj = defaultdict(list)
    for e in edges:
        adj[e["source"]].append(e["target"])
        adj[e["target"]].append(e["source"])

    visited = set()
    clusters = []
    for node in nodes:
        nid = node["id"]
        if nid in visited:
            continue
        cluster = []
        stack = [nid]
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            cluster.append(current)
            for neighbor in adj.get(current, []):
                if neighbor not in visited:
                    stack.append(neighbor)
        if cluster:
            clusters.append(cluster)

    lines = ["═══ CLUSTERS ═══", ""]
    for i, c in enumerate(clusters):
        lines.append("  Cluster {} ({} docs): {}".format(i + 1, len(c), ", ".join(c[:5])))
    lines.append("")
    lines.append("  Total clusters: {}".format(len(clusters)))
    return "\n".join(lines)


def _search_graph(params: dict) -> str:
    query = params.get("query", "").lower()
    if not query:
        return "Error: se requiere 'query'"
    graph = _load_graph()
    nodes = graph.get("nodes", [])
    matches = []
    for n in nodes:
        label = n.get("label", "").lower()
        nid = n["id"].lower()
        if query in label or query in nid:
            matches.append(n)
    if not matches:
        return "Sin resultados para '{}'".format(query)
    lines = ["═══ RESULTADOS PARA '{}' ═══".format(query), ""]
    for m in matches:
        lines.append("  {} — {}".format(m["id"], m.get("label", "?")))
    return "\n".join(lines)


def _shortest_path(params: dict) -> str:
    start = params.get("start", "")
    end = params.get("end", "")
    if not start or not end:
        return "Error: se requiere 'start' y 'end'"
    graph = _load_graph()
    edges = graph.get("edges", [])
    adj = defaultdict(list)
    for e in edges:
        adj[e["source"]].append(e["target"])
        adj[e["target"]].append(e["source"])

    from collections import deque
    queue = deque([(start, [start])])
    visited = {start}
    while queue:
        current, path = queue.popleft()
        if current == end:
            lines = ["═══ CAMINO MÁS CORTO ═══", ""]
            lines.append("  {}".format(" -> ".join(path)))
            lines.append("  Longitud: {} saltos".format(len(path) - 1))
            return "\n".join(lines)
        for neighbor in adj.get(current, []):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, path + [neighbor]))
    return "Sin camino entre '{}' y '{}'".format(start, end)


def _get_stats() -> str:
    graph = _load_graph()
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    if not nodes:
        return "Grafo vacío"
    degrees = defaultdict(int)
    for e in edges:
        degrees[e["source"]] += 1
        degrees[e["target"]] += 1
    max_node = max(nodes, key=lambda n: degrees.get(n["id"], 0)) if nodes else None
    avg_degree = (sum(degrees.values()) / len(nodes)) if nodes else 0
    lines = [
        "═══ ESTADÍSTICAS DEL GRAFO ═══",
        "",
        "  Nodos:         {}".format(len(nodes)),
        "  Aristas:       {}".format(len(edges)),
        "  Grado promedio: {:.2f}".format(avg_degree),
    ]
    if max_node:
        lines.append("  Nodo central:  {} (grado={})".format(
            max_node["id"], degrees.get(max_node["id"], 0)))
    lines.append("  Última build:  {}".format(graph.get("built_at", "?")))
    return "\n".join(lines)


def _export_html() -> str:
    graph = _load_graph()
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])

    if not nodes:
        return "Grafo vacío. Ejecuta 'build' primero"

    node_colors = ["#4FC3F7", "#81C784", "#FFB74D", "#E57373", "#BA68C8",
                   "#4DB6AC", "#FF8A65", "#A1887F", "#90A4AE", "#F06292"]

    html_nodes = []
    for i, n in enumerate(nodes):
        color = node_colors[i % len(node_colors)]
        html_nodes.append(
            '{{id:"{}", label:"{}", color:"{}", size:{}}}'.format(
                n["id"], n.get("label", n["id"])[:20], color,
                max(10, min(50, n.get("word_count", 10)))))

    html_edges = []
    for e in edges:
        html_edges.append(
            '{{source:"{}", target:"{}", weight:{}}}'.format(
                e["source"], e["target"], e["weight"]))

    html = """<!DOCTYPE html>
<html><head><title>ERIS Knowledge Graph</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/sigma.js/2.0.0/sigma.min.js"></script>
<style>body{{margin:0;background:#1a1a2e;color:#fff;font-family:monospace}}
#graph-container{{width:100vw;height:100vh}}
.info{{position:absolute;top:10px;left:10px;background:rgba(0,0,0,0.8);
padding:15px;border-radius:8px;border:1px solid #4FC3F7}}</style></head>
<body>
<div class="info"><h3>ERIS Knowledge Graph</h3>
<p>Nodos: {{nodes_count}} | Aristas: {{edges_count}}</p></div>
<div id="graph-container"></div>
<script>
const nodes = [{nodes}];
const edges = [{edges}];
const s = new sigma({{
  graph: {{nodes: nodes.map(n=>({{
    id:n.id, label:n.label, size:n.size,
    color:n.label?'#4FC3F7':'#666',
    x:Math.random()*100, y:Math.random()*100
  }})), edges: edges.map((e,i)=>({{
    id:'e'+i, source:e.source, target:e.target,
    size:e.weight*10, color:'#ffffff33'
  }}))}},
  renderer: {{container:'graph-container', type:'webgl'}},
  settings: {{defaultNodeColor:'#4FC3F7', labelThreshold:0}}
}});
</script></body></html>"""

    html = html.replace("{nodes}", json.dumps(html_nodes, ensure_ascii=False))
    html = html.replace("{edges}", json.dumps(html_edges, ensure_ascii=False))
    html = html.replace("{{nodes_count}}", str(len(nodes)))
    html = html.replace("{{edges_count}}", str(len(edges)))

    out = _BASE / "data" / "knowledge_graph.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return "Grafo exportado a: {}".format(out)


def _export_json() -> str:
    graph = _load_graph()
    if not graph.get("nodes"):
        return "Grafo vacío"
    out = _BASE / "data" / "knowledge_graph.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(graph, indent=2, ensure_ascii=False), encoding="utf-8")
    return "Grafo exportado a: {}".format(out)


def _suggest_connections(params: dict) -> str:
    doc_id = params.get("node", "")
    if not doc_id:
        return "Error: se requiere 'node'"
    graph = _load_graph()
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])

    existing = set()
    for e in edges:
        if e["source"] == doc_id:
            existing.add(e["target"])
        elif e["target"] == doc_id:
            existing.add(e["source"])

    candidates = []
    for n in nodes:
        if n["id"] == doc_id or n["id"] in existing:
            continue
        candidates.append(n["id"])

    if not candidates:
        return "Sin sugerencias para '{}'".format(doc_id)
    lines = ["═══ SUGERENCIAS PARA '{}' ═══".format(doc_id), ""]
    lines.append("  No conectado con:")
    for c in candidates[:10]:
        lines.append("    - {}".format(c))
    return "\n".join(lines)


def _get_status() -> str:
    graph = _load_graph()
    nodes = len(graph.get("nodes", []))
    edges = len(graph.get("edges", []))
    return "Knowledge Graph: {} nodos, {} aristas, build: {}".format(
        nodes, edges, graph.get("built_at", "nunca"))


def _load_graph() -> dict:
    if _KG_FILE.exists():
        try:
            return json.loads(_KG_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {"nodes": [], "edges": []}


def _save_graph(graph: dict):
    _KG_FILE.parent.mkdir(parents=True, exist_ok=True)
    _KG_FILE.write_text(json.dumps(graph, indent=2, ensure_ascii=False), encoding="utf-8")
