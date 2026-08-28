import sys, json
sys.path.insert(0, "D:/Eris_Source")
from core.neuro_spheres import _load_state
state = _load_state()
nodes = state.get("nodes", {})
if isinstance(nodes, dict):
    node_list = list(nodes.values())
else:
    node_list = nodes

# Analyze ALL nodes
print(f"=== ANALISIS DE {len(node_list)} NODOS ===")
print()

# Count by type
types = {}
for n in node_list:
    if isinstance(n, dict):
        t = n.get("type", "unknown")
        types[t] = types.get(t, 0) + 1

print("Por tipo:")
for t, c in sorted(types.items(), key=lambda x: -x[1]):
    print(f"  {t}: {c}")
print()

# Check content diversity
contents = []
for n in node_list:
    if isinstance(n, dict) and n.get("content"):
        contents.append(n["content"])

print(f"Con contenido: {len(contents)}/{len(node_list)}")
print()

# Check what triggers node creation
print("=== QUE DISPARA NODOS ===")
print("Buscando en main.py el codigo de auto-creacion...")
print()

# Read the auto-creation code
with open("D:/Eris_Source/main.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "neuro_spheres" in line.lower() and "auto" in line.lower():
        # Show context
        start = max(0, i-2)
        end = min(len(lines), i+15)
        print(f"Linea {i+1}:")
        for j in range(start, end):
            print(f"  {j+1}: {lines[j].rstrip()}")
        print()
        break

# Find all places where neuro_spheres is called
print("=== TODAS LAS LLAMADAS A NEUROSPHERES ===")
for i, line in enumerate(lines):
    if "neuro_spheres" in line.lower() and "import" not in line.lower() and "#" not in line[:5]:
        print(f"  Linea {i+1}: {line.strip()[:100]}")
