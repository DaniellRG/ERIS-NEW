import sys, time
sys.path.insert(0, r'D:\Eris_Source')
from actions.terminal_agent import terminal_agent

print("=== TEST COMPLETO TERMINAL AGENT ===")

# 1. Listar discos
print("\n--- 1. DISCOS DISPONIBLES ---")
r = terminal_agent({"action": "run_ps", "command": "Get-PSDrive -PSProvider FileSystem | Select-Object Name, @{N='GB';E={[math]::Round($_.Used/1GB,1)}}, @{N='Libre_GB';E={[math]::Round($_.Free/1GB,1)}} | Format-Table -AutoSize"})
print(r)

# 2. Buscar archivos en C:
print("\n--- 2. BUSCAR ARCHIVOS .PY EN C:\\Users\\danie ---")
r = terminal_agent({"action": "run_ps", "command": "Get-ChildItem -Path C:\\Users\\danie -Filter '*.py' -Recurse -ErrorAction SilentlyContinue | Select-Object -First 10 FullName"})
print(r[:500])

# 3. Buscar en D:
print("\n--- 3. LISTAR D:\\ ---")
r = terminal_agent({"action": "run_cmd", "command": "dir D:\\ /b"})
print(r[:500])

# 4. Copiar archivo
print("\n--- 4. COPIAR ARCHIVO ---")
r = terminal_agent({"action": "run_ps", "command": "Copy-Item 'C:\\Users\\danie\\Desktop\\screenshot.png' -Destination 'C:\\Users\\danie\\Desktop\\screenshot_backup.png' -Force; Write-Output 'Copia exitosa'"})
print(r)

# 5. Crear carpeta
print("\n--- 5. CREAR CARPETA ---")
r = terminal_agent({"action": "run_ps", "command": "New-Item -Path 'C:\\Users\\danie\\Desktop\\ERIS_TEST' -ItemType Directory -Force | Select-Object FullName"})
print(r)

# 6. Escribir archivo
print("\n--- 6. ESCRIBIR ARCHIVO ---")
r = terminal_agent({"action": "run_ps", "command": "Set-Content -Path 'C:\\Users\\danie\\Desktop\\ERIS_TEST\\test.txt' -Value 'Hola desde ERIS - Test de escritura' -Encoding UTF8; Get-Content 'C:\\Users\\danie\\Desktop\\ERIS_TEST\\test.txt'"})
print(r)

# 7. Buscar进程 (procesos)
print("\n--- 7. TOP 5 PROCESOS POR CPU ---")
r = terminal_agent({"action": "run_ps", "command": "Get-Process | Sort-Object CPU -Descending | Select-Object -First 5 Name, Id, @{N='CPU_s';E={[math]::Round($_.CPU,2)}} | Format-Table -AutoSize"})
print(r)

# 8. Info del sistema
print("\n--- 8. INFO SISTEMA ---")
r = terminal_agent({"action": "run_ps", "command": "Get-ComputerInfo | Select-Object WindowsProductName, WindowsVersion, OsArchitecture, CsProcessors, CsPhyicallyInstalledMemory"})
print(r[:500])

# 9. Red
print("\n--- 9. RED ---")
r = terminal_agent({"action": "run_ps", "command": "Get-NetIPAddress | Where-Object {$_.AddressFamily -eq 'IPv4' -and $_.IPAddress -ne '127.0.0.1'} | Select-Object InterfaceAlias, IPAddress | Format-Table -AutoSize"})
print(r)

# 10. Ping
print("\n--- 10. PING ---")
r = terminal_agent({"action": "run_cmd", "command": "ping -n 3 google.com"})
print(r[:300])

# 11. Buscar archivos grandes
print("\n--- 11. ARCHIVOS > 100MB EN C:\\Users\\danie ---")
r = terminal_agent({"action": "run_ps", "command": "Get-ChildItem -Path C:\\Users\\danie -Recurse -File -ErrorAction SilentlyContinue | Where-Object {$_.Length -gt 100MB} | Select-Object FullName, @{N='MB';E={[math]::Round($_.Length/1MB)}} | Sort-Object MB -Descending | Select-Object -First 10 | Format-Table -AutoSize"})
print(r[:500])

# 12. Servicios
print("\n--- 12. SERVICIOS CORRIENDO ---")
r = terminal_agent({"action": "run_ps", "command": "Get-Service | Where-Object {$_.Status -eq 'Running'} | Select-Object -First 10 Name, DisplayName | Format-Table -AutoSize"})
print(r[:400])

# 13. Historial
print("\n--- 13. HISTORIAL ---")
r = terminal_agent({"action": "list_history"})
print(r[:500])
