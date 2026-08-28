import json
from pathlib import Path

ns_path = Path(r"D:\Eris_Source\memory\neuro_spheres_state.json")
data = json.loads(ns_path.read_text(encoding="utf-8"))

nodes = data.get("nodes", [])
edges = data.get("edges", [])
print(f"Nodes type: {type(nodes).__name__}")
print(f"Edges type: {type(edges).__name__}")
print(f"Total nodes: {data.get('total_nodes', '?')}")
print(f"Total connections: {data.get('total_connections', '?')}")
print()

# If nodes is a dict, iterate values
if isinstance(nodes, dict):
    node_list = list(nodes.values())
elif isinstance(nodes, list):
    node_list = nodes
else:
    print("Unknown nodes structure")
    node_list = []

print(f"Node count: {len(node_list)}")
print()

# Show last 10
print("=== ULTIMOS 10 NODOS ===")
for n in node_list[-10:]:
    if isinstance(n, dict):
        label = n.get("label", n.get("name", "?"))
        ntype = n.get("type", n.get("category", "?"))
        content = n.get("content", n.get("description", n.get("data", "")))
        created = n.get("created_at", n.get("timestamp", "?"))
        print(f"  [{ntype}] {label}")
        if content:
            print(f"    Content: {str(content)[:200]}")
        else:
            print(f"    Content: ** VACIO **")
        print(f"    Created: {created}")
        print()
    else:
        print(f"  Node (not dict): {str(n)[:100]}")
        print()

# Count with/without content
with_content = sum(1 for n in node_list if isinstance(n, dict) and (n.get("content") or n.get("description") or n.get("data")))
empty = len(node_list) - with_content
print(f"=== RESUMEN ===")
print(f"  Con contenido real: {with_content}")
print(f"  VACIOS: {empty}")
print(f"  Conexiones: {len(edges) if isinstance(edges, list) else len(edges.values()) if isinstance(edges, dict) else '?'}")
