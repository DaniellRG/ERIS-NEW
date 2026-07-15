# Threat Hunting on Windows

## When to Use
When user asks to check system security, find suspicious activity, or hunt for threats.

## Prerequisites
- `security_scanner.py` tool
- `res_monitor.py` for system metrics
- `super_search.py` for file discovery

## Workflow

### Phase 1: Quick System Scan
1. Run `security_scanner` with action `quick_scan`
2. Check for active threats in running processes
3. Review any flagged items

### Phase 2: Suspicious Process Detection
1. Use `res_monitor top_processes` to see all running processes
2. Look for:
   - Processes with random/gibberish names
   - Processes running from Temp folders
   - Processes with high CPU but unknown origin
   - Processes connecting to unusual IPs
3. Flag any suspicious processes

### Phase 3: Persistence Mechanisms Check
1. Check Run registry keys via PowerShell:
   ```
   Get-ItemProperty HKLM:\Software\Microsoft\Windows\CurrentVersion\Run
   Get-ItemProperty HKCU:\Software\Microsoft\Windows\CurrentVersion\Run
   ```
2. Check Startup folder for suspicious entries
3. Check Scheduled Tasks for persistence

### Phase 4: Network Connection Audit
1. List active network connections:
   ```
   netstat -ano | findstr ESTABLISHED
   ```
2. Look for connections to unusual ports or IPs
3. Cross-reference with known malicious IPs

### Phase 5: File System Anomalies
1. Search for recently modified files in system directories
2. Look for files with double extensions (.txt.exe)
3. Check for hidden files in user directories

## Verification
- All scans completed without errors
- Suspicious findings documented in Obsidian
- Report summary generated for user

## Response Template
```
Threat Hunt Results:
- Processes scanned: X
- Suspicious processes: Y
- Persistence mechanisms: Z
- Network connections: W
- Filesystem anomalies: V
- Verdict: CLEAN / NEEDS INVESTIGATION / THREAT FOUND
```
