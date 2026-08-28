import sys, json
sys.path.insert(0, "D:/Eris_Source")
from actions.ide_integration import ide_integration

# Test explain
print("=== EXPLAIN ===")
r = json.loads(ide_integration({"action": "explain", "focus": "general"}))
print(f"Lines explained: {r.get('line_count', '?')}")
print(f"Explanation (first 300 chars):")
print(r.get("explanation", "")[:300])
print()

# Test edit (small, reversible)
print("=== EDIT TEST ===")
# Add a comment at the top
r = json.loads(ide_integration({
    "action": "edit",
    "old_text": "namespace Ahorcado",
    "new_text": "// Juego del Ahorcado\nnamespace Ahorcado"
}))
print(f"Success: {r.get('success', '?')}")
print(f"Changes: {r.get('changes_made', '?')}")
print()

# Undo it
r2 = json.loads(ide_integration({
    "action": "edit",
    "old_text": "// Juego del Ahorcado\nnamespace Ahorcado",
    "new_text": "namespace Ahorcado"
}))
print(f"Undo: {r2.get('success', '?')}")
