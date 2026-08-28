import sys, json
sys.path.insert(0, "D:/Eris_Source")
from actions.ide_integration import ide_integration

r = ide_integration({"action": "read"})
print(f"Type: {type(r).__name__}")
if isinstance(r, str):
    print(f"Sin BOM: {not r.startswith(chr(0xFEFF))}")
    print(f"Primeros 300 chars:")
    print(r[:300])
else:
    print(json.dumps(r, ensure_ascii=False)[:500])
