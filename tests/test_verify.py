import sys, json
sys.path.insert(0, "D:/Eris_Source")
from actions.ide_integration import ide_integration

result = ide_integration({"action": "read", "max_chars": 3000})
data = json.loads(result)
print("=== Eris verificando que puede leer tu codigo ===")
print("Source:", data.get("source", "N/A"))
print("File:", data.get("file_name", "N/A"))
print("Lines:", data.get("line_count", "N/A"))
print("Language:", data.get("language", "N/A"))
print("Path:", data.get("file_path", "N/A"))
print()
if data.get("code"):
    lines = data["code"].split("\n")
    print("Primeras 10 lineas del Ahorcado:")
    for i, l in enumerate(lines[:10], 1):
        safe = l.encode("ascii", "replace").decode("ascii")
        print(f"  {i:3}: {safe}")
    print(f"  ... ({len(lines)} lineas total)")
else:
    print("ERROR:", data.get("error", "unknown"))
