import sys
sys.path.insert(0, r'D:\Eris_Source')
from actions.terminal_agent import terminal_agent

print("=== TERMINAL AGENT TEST ===")

r = terminal_agent({"action": "info"})
print("[1] INFO:", r[:200])

r = terminal_agent({"action": "run_cmd", "command": "dir C:\\Users\\danie\\Desktop /b"})
print("\n[2] CMD dir:", r[:200])

r = terminal_agent({"action": "run_ps", "command": "Get-Date"})
print("\n[3] PS Get-Date:", r[:200])

r = terminal_agent({"action": "run_ps", "command": "Get-Process | Select-Object -First 5 Name, Id, CPU"})
print("\n[4] PS Processes:", r[:300])

r = terminal_agent({"action": "run_ps", "command": "Get-ComputerInfo | Select-Object WindowsProductName, WindowsVersion"})
print("\n[5] PS System:", r[:300])

r = terminal_agent({"action": "run", "command": "echo Hola desde ERIS"})
print("\n[6] AUTO:", r[:200])

r = terminal_agent({"action": "list_history"})
print("\n[7] HISTORY:", r[:300])
