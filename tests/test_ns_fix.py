import sys, json
sys.path.insert(0, "D:/Eris_Source")
from core.neuro_spheres import add_node, _load_state

# Create a test node with real content
result = add_node(
    sphere="aprendizaje",
    node_type="aprendizaje",
    title="Test: C# Ahorcado - juego de adivinar palabras",
    content="El usuario Daniel esta aprendiendo C# con un juego del ahorcado. Usa HashSet para letras acertadas/falladas, while loop para el juego, y validacion de input.",
    connections=[],
    force=5
)
print("Create result:", json.dumps(result, ensure_ascii=False, indent=2))

# Now verify it's stored in the state
state = _load_state()
nodes = state.get("nodes", {})
last_node_id = result.get("node_id", "")
if last_node_id and last_node_id in nodes:
    node = nodes[last_node_id]
    print(f"\nNode stored:")
    print(f"  Title: {node.get('title', 'EMPTY')}")
    print(f"  Content: {node.get('content', 'EMPTY')}")
    print(f"  Type: {node.get('type', 'EMPTY')}")
else:
    print("\nNode NOT found in state!")
