import sys, json
sys.path.insert(0, "D:/Eris_Source")
from actions.ide_integration import ide_integration

FILE = r"C:\Users\danie\source\repos\Ahorcado\Ahorcado\Program.cs"

# Test edit with file_path
r = ide_integration({
    "action": "edit",
    "file_path": FILE,
    "old_text": "namespace Ahorcado",
    "new_text": "// Test comment\nnamespace Ahorcado"
})
print("EDIT:", r[:500])
print()

# Undo
r2 = ide_integration({
    "action": "edit",
    "file_path": FILE,
    "old_text": "// Test comment\nnamespace Ahorcado",
    "new_text": "namespace Ahorcado"
})
print("UNDO:", r2[:300])
