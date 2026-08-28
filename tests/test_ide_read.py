import sys
sys.path.insert(0, "D:/Eris_Source")
from actions.ide_integration import read_code_from_editor, detect_active_ide
import json, pygetwindow as gw, time

# Activate VS
vs_wins = [w for w in gw.getAllWindows() if "Visual Studio" in (w.title or "") and "Code" not in (w.title or "")]
if vs_wins:
    vs_wins[0].activate()
    time.sleep(0.5)

# Detect
det = detect_active_ide()
print("=== DETECT ===")
for k, v in det.items():
    print(f"  {k}: {v}")

# Read
print("\n=== READ ===")
result = read_code_from_editor()
if "code" in result:
    print(f"Source: {result.get('source')}")
    print(f"File: {result.get('file_path')}")
    print(f"Lines: {result.get('line_count')}")
    print(f"Lang: {result.get('language')}")
    print(f"Chars: {result.get('char_count', '?')}")
    print()
    lines = result.get("lines", [])
    for i, line in enumerate(lines[:40], 1):
        safe = line.encode("ascii", "replace").decode("ascii")
        print(f"{i:3}: {safe}")
    if len(lines) > 40:
        print(f"... ({len(lines)} total)")
else:
    print(json.dumps(result, ensure_ascii=False, indent=2))
