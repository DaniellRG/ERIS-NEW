import sys
sys.path.insert(0, r'D:\Eris_Source')
from actions.terminal_agent import terminal_agent

print("=== TEST FIXED ESCAPING ===")

# Test 1: PowerShell con $_
r = terminal_agent({"action": "run_ps", "command": 'Get-Service | Where-Object {$_.Status -eq "Running"} | Measure-Object | Select-Object -ExpandProperty Count'})
print("[1] Services running:", r)

# Test 2: PowerShell Get-Process
r = terminal_agent({"action": "run_ps", "command": "Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 3 Name, @{N='MB';E={[math]::Round($_.WorkingSet64/1MB)}} | Format-Table -AutoSize"})
print("\n[2] Top processes:", r)

# Test 3: CMD
r = terminal_agent({"action": "run_cmd", "command": "systeminfo | findstr /B /C:\"OS Name\" /C:\"Total Physical Memory\""})
print("\n[3] CMD systeminfo:", r)

# Test 4: PowerShell buscar en todos los discos
r = terminal_agent({"action": "run_ps", "command": "Get-PSDrive -PSProvider FileSystem | ForEach-Object { $drive = $_.Name; Get-ChildItem -Path \"$drive\\\" -Directory -ErrorAction SilentlyContinue | Select-Object -First 3 FullName } | Format-Table -AutoSize"})
print("\n[4] All drives:", r[:500])

# Test 5: elevated info
r = terminal_agent({"action": "info"})
print("\n[5] Info:", r[:200])
