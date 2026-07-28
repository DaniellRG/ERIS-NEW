import re
with open(r"D:\Eris_Source\core\tool_declarations.py", encoding="utf-8") as f:
    content = f.read()

descs = re.findall(r'"description":\s*"([^"]+)"', content)
long_descs = [d for d in descs if len(d) > 100]
print(f"Total descriptions: {len(descs)}")
print(f"Descriptions > 100 chars: {len(long_descs)}")
if descs:
    print(f"Longest: {max(len(d) for d in descs)} chars")
    print(f"Average: {sum(len(d) for d in descs)//len(descs)} chars")
    print(f"Top 10 longest:")
    for d in sorted(descs, key=len, reverse=True)[:10]:
        print(f"  {len(d)} chars: {d[:100]}")
