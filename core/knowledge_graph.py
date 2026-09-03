# -*- coding: utf-8 -*-
from __future__ import annotations

import re
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict, deque
from core.logging_setup import get_obsidian_vault, BASE_DIR

_VAULT = get_obsidian_vault()
_DATA_FILE = BASE_DIR / "data" / "knowledge_graph_vault.json"
_WIKILINK_RE = re.compile(r"\[\[([^\]|]+?)(?:\|[^\]]+)?\]\]")
_MD_LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+\.md)\)")
_TAG_RE = re.compile(r"^(?:tags?:\s*(.+)|#\w+)", re.MULTILINE)


def knowledge_graph(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = params.get("action", "build").lower()

    if action == "build":
        return _build(params)
    elif action == "query":
        return _query(params)
    elif action == "clusters":
        return _clusters(params)
    elif action == "central":
        return _central(params)
    elif action == "path":
        return _path(params)
    elif action == "orphan":
        return _orphan(params)
    elif action == "stats":
        return _stats(params)
    elif action == "export":
        return _export(params)
    elif action == "visualize":
        return _visualize(params)

    return (
        "Acciones disponibles: build, query, clusters, central, "
        "path, orphan, stats, export, visualize"
    )


def _load_vault_graph() -> dict:
    if _DATA_FILE.exists():
        try:
            data = json.loads(_DATA_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "nodes" in data:
                return data
        except Exception:
            pass
    return {"nodes": {}, "metadata": {}}


def _save_vault_graph(data: dict):
    _DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    _DATA_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _extract_tags(content: str) -> list:
    tags = []
    for match in _TAG_RE.finditer(content):
        raw = match.group(1) if match.group(1) else match.group(0)
        for t in re.findall(r"#[\w/]+", raw):
            tags.append(t.lstrip("#"))
    fm_match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if fm_match:
        for t in re.findall(r"tags:\s*\n((?:\s*-\s*\w+\n?)+)", fm_match.group(1)):
            for item in re.findall(r"-\s*(\w+)", t):
                tags.append(item)
    return list(set(tags))


def _extract_links(content: str) -> list:
    links = []
    for m in _WIKILINK_RE.finditer(content):
        links.append(m.group(1).strip())
    for m in _MD_LINK_RE.finditer(content):
        name = Path(m.group(2)).stem
        links.append(name)
    return list(set(links))


def _scan_vault(vault_path: Path) -> dict:
    nodes = {}
    if not vault_path.exists():
        return nodes

    for md_file in vault_path.rglob("*.md"):
        if md_file.name.startswith("."):
            continue
        try:
            content = md_file.read_text(encoding="utf-8")
        except Exception:
            continue

        note_name = md_file.stem
        rel_path = str(md_file.relative_to(vault_path))
        tags = _extract_tags(content)
        links = _extract_links(content)

        nodes[note_name] = {
            "path": rel_path,
            "connections": links,
            "degree": len(links),
            "tags": tags,
        }

    for name, node in nodes.items():
        resolved = []
        for link in node["connections"]:
            if link in nodes:
                resolved.append(link)
        node["connections"] = resolved
        node["degree"] = len(resolved)

    return nodes


def _build(params: dict) -> str:
    vault = Path(params.get("vault_path", str(_VAULT)))
    if not vault.exists():
        return "Vault no encontrado: {}".format(vault)

    nodes = _scan_vault(vault)
    total_edges = sum(n["degree"] for n in nodes.values()) // 2

    graph = {
        "nodes": nodes,
        "metadata": {
            "total_notes": len(nodes),
            "total_edges": total_edges,
            "built_at": datetime.now().isoformat(),
            "vault_path": str(vault),
        },
    }
    _save_vault_graph(graph)

    orphans = [n for n, v in nodes.items() if v["degree"] == 0]
    most_connected = sorted(nodes.items(), key=lambda x: x[1]["degree"], reverse=True)[:5]

    lines = [
        "═══ GRAFO DEL VAULT CONSTRUIDO ═══",
        "",
        "  Notas:      {}".format(len(nodes)),
        "  Conexiones: {}".format(total_edges),
        "  Huérfanas:  {}".format(len(orphans)),
        "",
    ]

    if most_connected:
        lines.append("  Top 5 notas más conectadas:")
        for name, data in most_connected:
            lines.append("    {} → {} conexiones".format(name, data["degree"]))

    lines.append("")
    lines.append("  Vault: {}".format(vault))
    return "\n".join(lines)


def _query(params: dict) -> str:
    note = params.get("note", "").strip()
    depth = int(params.get("depth", 1))

    if not note:
        return "Error: se requiere el parámetro 'note'"

    graph = _load_vault_graph()
    nodes = graph.get("nodes", {})

    if note not in nodes:
        matches = [n for n in nodes if note.lower() in n.lower()]
        if matches:
            return "Nota '{}' no encontrada. ¿Quisiste decir? {}".format(
                note, ", ".join(matches[:5])
            )
        return "Nota '{}' no encontrada en el grafo".format(note)

    node = nodes[note]
    lines = [
        "═══ NOTA: {} ═══".format(note),
        "",
        "  Archivo: {}".format(node["path"]),
        "  Conexiones: {}".format(node["degree"]),
    ]

    if node["tags"]:
        lines.append("  Tags: {}".format(", ".join(node["tags"])))

    if node["connections"]:
        lines.append("")
        lines.append("  Enlazada con ({}):".format(len(node["connections"])))
        for conn in node["connections"]:
            cn = nodes.get(conn, {})
            deg = cn.get("degree", 0)
            lines.append("    → {} (grado={})".format(conn, deg))

    if depth > 1:
        visited = {note}
        frontier = list(node["connections"])
        for d in range(2, depth + 1):
            next_frontier = []
            for fn in frontier:
                if fn in visited or fn not in nodes:
                    continue
                visited.add(fn)
                for c in nodes[fn].get("connections", []):
                    if c not in visited:
                        next_frontier.append(c)
            if next_frontier:
                lines.append("")
                lines.append("  Profundidad {}:".format(d))
                for fn in next_frontier:
                    lines.append("    → {}".format(fn))
            frontier = next_frontier

    return "\n".join(lines)


def _clusters(params: dict) -> str:
    graph = _load_vault_graph()
    nodes = graph.get("nodes", {})

    if not nodes:
        return "Grafo vacío. Ejecuta 'build' primero"

    adj = defaultdict(set)
    for name, data in nodes.items():
        for conn in data.get("connections", []):
            if conn in nodes:
                adj[name].add(conn)
                adj[conn].add(name)

    visited = set()
    clusters = []

    for node_name in sorted(nodes.keys()):
        if node_name in visited:
            continue
        cluster = []
        queue = deque([node_name])
        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
            cluster.append(current)
            for neighbor in adj.get(current, set()):
                if neighbor not in visited:
                    queue.append(neighbor)
        if cluster:
            internal_edges = 0
            for n in cluster:
                for c in adj.get(n, set()):
                    if c in cluster:
                        internal_edges += 1
            internal_edges //= 2
            clusters.append({
                "nodes": cluster,
                "size": len(cluster),
                "internal_edges": internal_edges,
                "density": (
                    round(2 * internal_edges / (len(cluster) * (len(cluster) - 1)), 4)
                    if len(cluster) > 1
                    else 0
                ),
            })

    clusters.sort(key=lambda c: c["size"], reverse=True)

    lines = [
        "═══ CLUSTERS / COMUNIDADES ═══",
        "",
        "  Total clusters: {}".format(len(clusters)),
        "",
    ]

    for i, cl in enumerate(clusters):
        lines.append("  Cluster {} ({} notas, {} aristas internas, densidad={})".format(
            i + 1, cl["size"], cl["internal_edges"], cl["density"]
        ))
        for n in cl["nodes"][:8]:
            deg = nodes[n].get("degree", 0)
            lines.append("    - {} (grado={})".format(n, deg))
        if cl["size"] > 8:
            lines.append("    ... y {} más".format(cl["size"] - 8))
        lines.append("")

    return "\n".join(lines)


def _central(params: dict) -> str:
    graph = _load_vault_graph()
    nodes = graph.get("nodes", {})
    limit = int(params.get("limit", 10))

    if not nodes:
        return "Grafo vacío. Ejecuta 'build' primero"

    ranked = sorted(nodes.items(), key=lambda x: x[1].get("degree", 0), reverse=True)

    lines = [
        "═══ NOTAS MÁS IMPORTANTES (por grado) ═══",
        "",
    ]

    for i, (name, data) in enumerate(ranked[:limit]):
        degree = data.get("degree", 0)
        tags = data.get("tags", [])
        bar = "█" * min(degree, 40)
        lines.append("  {:>2}. {} — grado={} {}".format(
            i + 1, name, degree, bar
        ))
        if tags:
            lines.append("      Tags: {}".format(", ".join(tags[:5])))
        lines.append("      Path: {}".format(data.get("path", "?")))

    lines.append("")
    lines.append("  Total notas: {}".format(len(nodes)))
    avg = sum(d.get("degree", 0) for d in nodes.values()) / max(len(nodes), 1)
    lines.append("  Grado promedio: {:.2f}".format(avg))
    return "\n".join(lines)


def _path(params: dict) -> str:
    start = params.get("start", "").strip()
    end = params.get("end", "").strip()

    if not start or not end:
        return "Error: se requieren 'start' y 'end'"

    graph = _load_vault_graph()
    nodes = graph.get("nodes", {})

    if start not in nodes:
        return "Nota inicio '{}' no encontrada".format(start)
    if end not in nodes:
        return "Nota fin '{}' no encontrada".format(end)

    if start == end:
        return "Inicio y fin son la misma nota: {}".format(start)

    adj = defaultdict(set)
    for name, data in nodes.items():
        for conn in data.get("connections", []):
            if conn in nodes:
                adj[name].add(conn)
                adj[conn].add(name)

    queue = deque([(start, [start])])
    visited = {start}

    while queue:
        current, route = queue.popleft()
        for neighbor in adj.get(current, set()):
            if neighbor in visited:
                continue
            new_route = route + [neighbor]
            if neighbor == end:
                lines = [
                    "═══ CAMINO MÁS CORTO ═══",
                    "",
                    "  {}".format(" → ".join(new_route)),
                    "  Longitud: {} saltos".format(len(new_route) - 1),
                    "",
                ]
                for i in range(len(new_route) - 1):
                    a, b = new_route[i], new_route[i + 1]
                    tags_a = nodes[a].get("tags", [])
                    tag_str = " [{}]".format(",".join(tags_a[:3])) if tags_a else ""
                    lines.append("  {}{} → {}".format(a, tag_str, b))
                return "\n".join(lines)
            visited.add(neighbor)
            queue.append((neighbor, new_route))

    return "No existe camino entre '{}' y '{}'".format(start, end)


def _orphan(params: dict) -> str:
    graph = _load_vault_graph()
    nodes = graph.get("nodes", {})

    if not nodes:
        return "Grafo vacío. Ejecuta 'build' primero"

    orphans = [(n, d) for n, d in nodes.items() if d.get("degree", 0) == 0]

    lines = [
        "═══ NOTAS HUÉRFANAS (sin conexiones) ═══",
        "",
        "  Total: {} de {} notas".format(len(orphans), len(nodes)),
        "",
    ]

    for name, data in sorted(orphans, key=lambda x: x[0]):
        lines.append("  - {} ({})".format(name, data.get("path", "?")))

    if len(orphans) > 20:
        lines.append("")
        lines.append("  ... y {} más".format(len(orphans) - 20))

    return "\n".join(lines)


def _stats(params: dict) -> str:
    graph = _load_vault_graph()
    nodes = graph.get("nodes", {})
    meta = graph.get("metadata", {})

    if not nodes:
        return "Grafo vacío. Ejecuta 'build' primero"

    degrees = [d.get("degree", 0) for d in nodes.values()]
    total_edges = sum(degrees) // 2
    max_deg = max(degrees) if degrees else 0
    avg_deg = sum(degrees) / max(len(degrees), 1)

    tag_counter = defaultdict(int)
    for data in nodes.values():
        for tag in data.get("tags", []):
            tag_counter[tag] += 1

    top_tags = sorted(tag_counter.items(), key=lambda x: x[1], reverse=True)[:10]

    path_ext = defaultdict(int)
    for data in nodes.values():
        p = data.get("path", "")
        ext = Path(p).suffix if p else "?"
        path_ext[ext] += 1

    lines = [
        "═══ ESTADÍSTICAS DEL GRAFO ═══",
        "",
        "  Notas totales:    {}".format(len(nodes)),
        "  Aristas totales:  {}".format(total_edges),
        "  Grado máximo:     {}".format(max_deg),
        "  Grado promedio:   {:.2f}".format(avg_deg),
        "  Huérfanas:        {}".format(sum(1 for d in degrees if d == 0)),
        "",
    ]

    if top_tags:
        lines.append("  Tags más usados:")
        for tag, count in top_tags:
            lines.append("    #{} — {} notas".format(tag, count))
        lines.append("")

    lines.append("  Extensiones:")
    for ext, count in sorted(path_ext.items(), key=lambda x: x[1], reverse=True):
        lines.append("    {} — {}".format(ext, count))

    lines.append("")
    lines.append("  Vault: {}".format(meta.get("vault_path", "?")))
    lines.append("  Última build: {}".format(meta.get("built_at", "?")))
    return "\n".join(lines)


def _export(params: dict) -> str:
    graph = _load_vault_graph()
    nodes = graph.get("nodes", {})

    if not nodes:
        return "Grafo vacío. Ejecuta 'build' primero"

    vis_nodes = []
    vis_edges = []
    edge_set = set()

    for name, data in nodes.items():
        vis_nodes.append({
            "id": name,
            "label": name,
            "size": max(5, min(50, data.get("degree", 1) * 3)),
            "tags": data.get("tags", []),
        })
        for conn in data.get("connections", []):
            edge_key = tuple(sorted([name, conn]))
            if edge_key not in edge_set and conn in nodes:
                edge_set.add(edge_key)
                vis_edges.append({
                    "source": name,
                    "target": conn,
                })

    export_data = {
        "nodes": vis_nodes,
        "edges": vis_edges,
        "stats": {
            "total_nodes": len(vis_nodes),
            "total_edges": len(vis_edges),
        },
        "exported_at": datetime.now().isoformat(),
    }

    out = Path(r"D:\Eris_Source\data\knowledge_graph_vault_export.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(export_data, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "═══ GRAFO EXPORTADO ═══",
        "",
        "  Nodos: {}".format(len(vis_nodes)),
        "  Aristas: {}".format(len(vis_edges)),
        "  Archivo: {}".format(out),
    ]
    return "\n".join(lines)


def _visualize(params: dict) -> str:
    graph = _load_vault_graph()
    nodes = graph.get("nodes", {})

    if not nodes:
        return "Grafo vacío. Ejecuta 'build' primero"

    top_n = int(params.get("limit", 20))
    ranked = sorted(nodes.items(), key=lambda x: x[1].get("degree", 0), reverse=True)
    top_nodes = [n for n, _ in ranked[:top_n]]

    positions = {}
    cols = 5
    for i, name in enumerate(top_nodes):
        row = i // cols
        col = i % cols
        positions[name] = (col * 18, row * 6)

    width = cols * 18
    height = ((len(top_nodes) - 1) // cols + 1) * 6 + 2
    canvas = [[" " for _ in range(width)] for _ in range(height)]

    for name, (x, y) in positions.items():
        deg = nodes[name].get("degree", 0)
        label = "({})".format(name[:12])
        center_x = x + 9
        center_y = y + 1
        if 0 <= center_y < height and 0 <= center_x - len(label) // 2 < width:
            start = max(0, center_x - len(label) // 2)
            for ci, ch in enumerate(label):
                if start + ci < width:
                    canvas[center_y][start + ci] = ch

        ring = "o"
        if deg >= 10:
            ring = "@"
        elif deg >= 5:
            ring = "*"
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = center_x + dx, center_y + dy
            if 0 <= ny < height and 0 <= nx < width:
                canvas[ny][nx] = ring

    edge_drawn = set()
    for name in top_nodes:
        for conn in nodes[name].get("connections", []):
            if conn not in positions:
                continue
            edge_key = tuple(sorted([name, conn]))
            if edge_key in edge_drawn:
                continue
            edge_drawn.add(edge_key)
            x1, y1 = positions[name]
            x2, y2 = positions[conn]
            mid_x1 = x1 + 9
            mid_x2 = x2 + 9
            line_y = max(y1, y2) + 2
            if line_y < height:
                for lx in range(min(mid_x1, mid_x2) + 1, max(mid_x1, mid_x2)):
                    if 0 <= lx < width:
                        canvas[line_y][lx] = "."

    lines = [
        "═══ VISUALIZACIÓN DEL GRAFO (top {} notas) ═══".format(top_n),
        "",
        "  @ = grado >= 10  |  * = grado >= 5  |  o = grado < 5",
        "  . = conexión entre notas",
        "",
    ]

    for row in canvas:
        lines.append("  " + "".join(row).rstrip())

    lines.append("")
    lines.append("  Notas mostradas: {} de {}".format(len(top_nodes), len(nodes)))
    return "\n".join(lines)
