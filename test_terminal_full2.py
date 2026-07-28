import sys
sys.path.insert(0, r'D:\Eris_Source')
from actions.terminal_agent import terminal_agent

print("=== TEST TERMINAL AGENT COMPLETO ===\n")

# 1. Abrir carpeta
print("[1] ABRIR CARPETA Desktop:")
r = terminal_agent({"action": "open", "command": "C:\\Users\\danie\\Desktop"})
print(f"  {r}\n")

# 2. Abrir app
print("[2] ABRIR APP notepad:")
r = terminal_agent({"action": "open", "command": "notepad"})
print(f"  {r}\n")
import time; time.sleep(2)

# 3. Cerrar notepad
print("[3] CERRAR notepad:")
r = terminal_agent({"action": "run_cmd", "command": "taskkill /F /IM notepad.exe"})
print(f"  {r}\n")

# 4. Win+R — abrir calculadora
print("[4] WIN+R calculadora:")
r = terminal_agent({"action": "win_r", "command": "calc"})
print(f"  {r}\n")
time.sleep(2)

# 5. Abrir URL
print("[5] ABRIR URL:")
r = terminal_agent({"action": "open", "command": "https://www.google.com"})
print(f"  {r}\n")

# 6. Abrir carpeta D:\
print("[6] ABRIR D:\\:")
r = terminal_agent({"action": "open", "command": "D:\\"})
print(f"  {r}\n")

# 7. Shell execute
print("[7] SHELL_EXECUTE paint:")
r = terminal_agent({"action": "shell_execute", "command": "mspaint"})
print(f"  {r}\n")

# 8. PowerShell normal
print("[8] PS Get-Date:")
r = terminal_agent({"action": "run_ps", "command": "Get-Date"})
print(f"  {r}\n")

# 9. CMD normal
print("[9] CMD echo:")
r = terminal_agent({"action": "run_cmd", "command": "echo Hola desde ERIS en CMD"})
print(f"  {r}\n")

# 10. Info
print("[10] INFO:")
r = terminal_agent({"action": "info"})
print(f"  {r}\n")

# 11. Historial
print("[11] HISTORIAL:")
r = terminal_agent({"action": "list_history"})
print(f"  {r}")
