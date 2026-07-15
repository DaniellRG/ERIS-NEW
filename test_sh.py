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
tmp.write("print(\"debug\")\n")
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
out.append("")

print("\n".join(out), flush=True)
