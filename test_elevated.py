import sys
sys.path.insert(0, r'D:\Eris_Source')
from actions.terminal_agent import terminal_agent

print("=== TEST ELEVATED (ADMIN) ===")
print("NOTA: Aparecerá ventana UAC - dar click en Sí")
print()

# Test elevated: listar drivers (requiere admin)
r = terminal_agent({"action": "elevated", "command": "Get-WindowsDriver -Online | Select-Object -First 5 ClassName, ProviderName, Version | Format-Table -AutoSize", "timeout": 60})
print("[ELEVATED] Drivers:", r[:500])

print("\n=== TODOS LOS TESTS COMPLETADOS ===")
