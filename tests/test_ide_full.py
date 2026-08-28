import sys, json, os
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, "D:/Eris_Source")
from actions.ide_integration import (
    detect_active_ide, read_code_from_editor, edit_find_replace,
    edit_line, edit_lines, ide_integration
)

FILE = r"C:\Users\danie\source\repos\Ahorcado\Ahorcado\TestErrores.cs"

print("=" * 60)
print("TEST COMPLETO DE IDE_INTEGRATION")
print("=" * 60)

# TEST 1: Detect
print("\n--- TEST 1: DETECT ---")
result = detect_active_ide()
print(f"  IDE: {result.get('ide_friendly', 'N/A')}")
print(f"  File: {result.get('file_name', 'N/A')}")
print(f"  Language: {result.get('language', 'N/A')}")

# TEST 2: Read via tool
print("\n--- TEST 2: READ via tool ---")
result = ide_integration({"action": "read", "max_chars": 2000})
data = json.loads(result)
print(f"  Source: {data.get('source', 'N/A')}")
print(f"  Lines: {data.get('line_count', 'N/A')}")
print(f"  Language: {data.get('language', 'N/A')}")
if data.get("code"):
    lines = data["code"].split("\n")
    print(f"  First 3 lines:")
    for l in lines[:3]:
        safe = l.encode("ascii", "replace").decode("ascii")
        print(f"    {safe}")

# TEST 3: Edit find-replace (CORREGIR ERROR 1)
print("\n--- TEST 3: EDIT (find-replace) ---")
result = ide_integration({
    "action": "edit",
    "file_path": FILE,
    "old_text": '            nombre = "Daniel";',
    "new_text": '            string nombre = "Daniel";'
})
data = json.loads(result)
print(f"  Success: {data.get('success', False)}")
print(f"  Message: {data.get('message', 'N/A')}")

# TEST 4: Edit line (CORREGIR ERROR 4)
print("\n--- TEST 4: EDIT LINE ---")
result = ide_integration({
    "action": "edit_line",
    "file_path": FILE,
    "line_number": 32,
    "new_content": '            if (valor == 10)  // COMPARACION correcta'
})
data = json.loads(result)
print(f"  Success: {data.get('success', False)}")
print(f"  Old: {data.get('old_line', 'N/A')}")
print(f"  New: {data.get('new_line', 'N/A')}")

# TEST 5: Edit lines (CORREGIR ERROR 2 - division por cero)
print("\n--- TEST 5: EDIT LINES (bloque) ---")
result = ide_integration({
    "action": "edit_lines",
    "file_path": FILE,
    "start_line": 18,
    "end_line": 23,
    "new_code": """            int[] numeros = { 10, 20, 0, 40 };
            for (int i = 0; i < numeros.Length; i++)
            {
                if (numeros[i] != 0)  // Proteccion contra division por cero
                {
                    int resultado = 100 / numeros[i];
                    Console.WriteLine(resultado);
                }
                else
                {
                    Console.WriteLine("No se puede dividir por cero");
                }"""
})
data = json.loads(result)
print(f"  Success: {data.get('success', False)}")
print(f"  Lines changed: {data.get('old_lines', 0)} -> {data.get('new_lines', 0)}")

# TEST 6: Verify changes
print("\n--- TEST 6: VERIFICAR CAMBIOS ---")
with open(FILE, "r", encoding="utf-8-sig") as f:
    content = f.read()
lines = content.split("\n")
print(f"  Total lines: {len(lines)}")
# Check error 1 fix
if "string nombre" in content:
    print("  [OK] Error 1 corregido: 'string nombre' encontrado")
else:
    print("  [FAIL] Error 1 NO corregido")
# Check error 4 fix
if "valor == 10" in content:
    print("  [OK] Error 4 corregido: '==' encontrado")
else:
    print("  [FAIL] Error 4 NO corregido")

print("\n" + "=" * 60)
print("TESTS COMPLETADOS")
print("=" * 60)
