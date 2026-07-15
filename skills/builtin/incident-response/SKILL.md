# Incident Response for Windows

## When to Use
When a security incident is detected: malware found, suspicious activity, data breach, or system compromise.

## Prerequisites
- `security_scanner.py`
- `threat-hunting/SKILL.md`
- `malware-analysis/SKILL.md`
- `res_monitor.py`
- `obsidian_brain.py` (document everything)

## Workflow - 6 Phases

### Phase 1: IDENTIFY
1. What triggered the alert? (user report, scanner, unusual behavior)
2. When did it start? (check timestamps, logs)
3. What systems are affected? (this PC only, or network spread)
4. Initial severity assessment: LOW / MEDIUM / HIGH / CRITICAL
5. Document initial findings in Obsidian

### Phase 2: CONTAIN
CRITICAL/HIGH: Immediate action required
1. Disconnect from network (if spreading)
2. Kill malicious processes via `res_monitor`
3. Quarantine affected files via `security_scanner quarantine_file`
4. Block suspicious IPs in Windows Firewall

MEDIUM/LOW: Monitor first
1. Log all activity without blocking
2. Gather evidence before taking action
3. Prepare containment plan

### Phase 3: ERADICATE
1. Remove malware using `malware-analysis` skill workflow
2. Delete persistence mechanisms (registry, startup, scheduled tasks)
3. Patch the vulnerability that allowed the incident
4. Scan entire system: `security_scanner scan_folder`

### Phase 4: RECOVER
1. Restore affected files from backup if needed
2. Verify system integrity: run `res_monitor status`
3. Check all critical apps are functioning
4. Re-enable security features if disabled

### Phase 5: LEARN
1. Document root cause in Obsidian
2. Register lesson: `learn_from_mistake`
3. Update security policies based on findings
4. Schedule follow-up scan in 24 hours

### Phase 6: REPORT
Generate incident report with:
- Timeline of events
- Impact assessment
- Actions taken
- Root cause analysis
- Recommendations to prevent recurrence

## Verification
- Threat contained and eradicated
- System restored to normal operation
- Root cause identified and documented
- Prevention measures implemented

## Communication Templates

**Initial Alert:**
"⚠️ Security Incident Detected: [description]. Severity: [level]. Beginning response protocol."

**Status Update:**
"Incident Response Update: Phase [X] - [action]. [progress]. Next: [next step]."

**Resolution:**
"Incident Resolved: [summary]. Full report saved to Obsidian. Lessons learned: [count]."
