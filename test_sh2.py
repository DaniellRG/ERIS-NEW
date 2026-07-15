import sys
sys.path.insert(0, "D:\\Eris_Source")
import importlib.util as iu
spec = iu.spec_from_file_location("sh", "D:\\Eris_Source\\actions\\self_heal.py")
mod = iu.module_from_spec(spec)
spec.loader.exec_module(mod)
import tempfile, os

tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, dir="D:\\Eris_Source\\actions")
tmp.write("import sys\n")
tmp.write("try:\n")
tmp.write("    print(\"hello\")\n")
tmp.write("except:\n")
tmp.write("    pass\n")
tmp.write("Flask()\n")
tmp.close()
fname = os.path.basename(tmp.name)

out = []
out.append("=== SCAN ===")
out.append(mod.self_heal({"action": "scan_file", "file": "actions/" + fname}))
out.append("")
out.append("=== AUTO FIX ===")
out.append(mod.self_heal({"action": "auto_fix", "file": "actions/" + fname}))
out.append("")
out.append("=== VERIFY ===")
out.append(mod.self_heal({"action": "scan_file", "file": "actions/" + fname}))

# Read the file to see what changed
fp = os.path.join("D:\\Eris_Source\\actions", fname)
content = open(fp, encoding="utf-8").read()
out.append("")
out.append("=== FILE CONTENT ===")
out.append(content)

print("\n".join(out), flush=True)
