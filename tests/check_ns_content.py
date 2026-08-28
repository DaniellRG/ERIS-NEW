import sys, json
sys.path.insert(0, "D:/Eris_Source")
from core.neuro_spheres import _load_state
state = _load_state()
nodes = state.get("nodes", {})
if isinstance(nodes, dict):
    node_list = list(nodes.values())
else:
    node_list = nodes

# Show ALL nodes with content
print("=== NODOS CON CONTENIDO ===")
for i, n in enumerate(node_list):
    if isinstance(n, dict) and n.get("content"):
        t = n.get("type", "?")
        title = str(n.get("title", "?"))[:60]
        content = str(n.get("content", ""))[:120]
        created = n.get("created", "?")[:19]
        print(f"  [{t}] {title}")
        print(f"    Content: {content}")
        print(f"    Created: {created}")
        print()

print(f"Total: {len(node_list)} nodos, {sum(1 for n in node_list if isinstance(n, dict) and n.get('content'))} con contenido")
