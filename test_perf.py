from pathlib import Path

# Check prompt size
prompt = Path(r"D:\Eris_Source\core\prompt.txt").read_text(encoding="utf-8")
lines = len(prompt.splitlines())
chars = len(prompt)
words = len(prompt.split())
print(f"prompt.txt: {lines} lines, {words} words, {chars} chars")

# Check tool declarations size
content = Path(r"D:\Eris_Source\core\tool_declarations.py").read_text(encoding="utf-8")
tool_count = content.count('"name":')
print(f"Tool declarations: {tool_count} tools")

# Check action imports count
imports = Path(r"D:\Eris_Source\core\action_imports.py").read_text(encoding="utf-8")
import_count = imports.count("from actions.")
print(f"Action imports: {import_count}")

# Check dispatcher entries
dispatcher = Path(r"D:\Eris_Source\core\tool_dispatcher.py").read_text(encoding="utf-8")
dispatch_count = dispatcher.count("elif name ==")
print(f"Dispatch entries: {dispatch_count}")

# Check total file size of all core files
core_dir = Path(r"D:\Eris_Source\core")
total = sum(f.stat().st_size for f in core_dir.glob("*.py"))
print(f"Total core .py size: {total/1024:.0f} KB")

actions_dir = Path(r"D:\Eris_Source\actions")
total_actions = sum(f.stat().st_size for f in actions_dir.glob("*.py"))
print(f"Total actions .py size: {total_actions/1024:.0f} KB")
print(f"Action files: {len(list(actions_dir.glob('*.py')))}")

# Estimate prompt tokens (rough: 1 token per 4 chars)
print(f"\nEstimated prompt tokens: ~{chars//4}")
print(f"Estimated tool schema tokens: ~{len(content)//4}")
