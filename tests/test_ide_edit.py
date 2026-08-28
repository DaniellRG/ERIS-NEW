import sys, json
sys.path.insert(0, "D:/Eris_Source")
from actions.ide_integration import ide_integration

# Test edit
r = ide_integration({
    "action": "edit",
    "old_text": "namespace Ahorcado",
    "new_text": "// Test comment\nnamespace Ahorcado"
})
print("EDIT raw:", r[:500] if isinstance(r, str) else json.dumps(r, ensure_ascii=False)[:500])
print()

# Parse it
if isinstance(r, str):
    r = json.loads(r)
print("Edit result:", json.dumps(r, ensure_ascii=False, indent=2)[:500])
print()

# Undo
r2 = ide_integration({
    "action": "edit",
    "old_text": "// Test comment\nnamespace Ahorcado",
    "new_text": "namespace Ahorcado"
})
print("UNDO:", r2[:300] if isinstance(r2, str) else json.dumps(r2, ensure_ascii=False)[:300])
