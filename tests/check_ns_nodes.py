import sys, json
sys.path.insert(0, "D:/Eris_Source")
from core.neuro_spheres import _load_state
state = _load_state()
nodes = state.get("nodes", {})
if isinstance(nodes, dict):
    node_list = list(nodes.values())
else:
    node_list = nodes
print(f"Total nodos: {len(node_list)}")
with_content = sum(1 for n in node_list if isinstance(n, dict) and n.get("content"))
empty = len(node_list) - with_content
print(f"Con contenido: {with_content}")
print(f"VACIOS: {empty}")
print()
print("=== ULTIMOS 5 ===")
for n in node_list[-5:]:
    if isinstance(n, dict):
        t = n.get("type", "?")
        title = str(n.get("title", "?"))[:50]
        content = str(n.get("content", "VACIO"))[:80]
        print(f"  Tipo: {t} | Title: {title}")
        print(f"  Content: {content}")
        print()
