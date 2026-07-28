# -*- coding: utf-8 -*-
"""
Eris Self-Protection – Autoprotección e integridad.
Monitorea archivos críticos, detecta manipulación, crea backups automáticos,
se repara si algo la daña, y protege su configuración.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
BACKUP_DIR = BASE_DIR / "backups"
INTEGRITY_FILE = BASE_DIR / "data" / "integrity_hashes.json"
SELF_PROTECT_LOG = BASE_DIR / "data" / "self_protection_log.json"

# Critical files that define who Eris is
CRITICAL_FILES = {
    "core/prompt.txt": "System prompt - personality and instructions",
    "core/tool_declarations.py": "Tool definitions for Gemini",
    "core/tool_dispatcher.py": "Tool execution logic",
    "core/action_imports.py": "Module imports registry",
    "main.py": "Main application entry point",
    "config/api_keys.json": "API keys and device config",
    "actions/emotional_growth.py": "Emotional growth system",
    "actions/obsidian_brain.py": "Obsidian integration",
    "actions/security_shield.py": "Security shield",
    "actions/cybersecurity.py": "Cybersecurity knowledge",
    "actions/english_teacher.py": "English teacher",
    "actions/credential_recovery.py": "Credential recovery",
    "actions/osint_agent.py": "OSINT agent",
    "actions/self_protection.py": "This module",
    "actions/self_heal.py": "Self-healing system",
    "memory/emotional_growth.json": "Emotional state data",
}


def _hash_file(path: Path) -> str:
    """Calculate SHA256 hash of a file."""
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except Exception:
        return ""


def _load_integrity() -> dict:
    try:
        if INTEGRITY_FILE.exists():
            return json.loads(INTEGRITY_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_integrity(data: dict):
    INTEGRITY_FILE.parent.mkdir(parents=True, exist_ok=True)
    INTEGRITY_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _log_event(event_type: str, message: str):
    try:
        events = []
        if SELF_PROTECT_LOG.exists():
            events = json.loads(SELF_PROTECT_LOG.read_text(encoding="utf-8"))
        events.append({
            "time": datetime.now().isoformat(),
            "type": event_type,
            "message": message,
        })
        SELF_PROTECT_LOG.parent.mkdir(parents=True, exist_ok=True)
        SELF_PROTECT_LOG.write_text(json.dumps(events[-500:], indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def _create_backup(file_path: Path) -> str:
    """Create a timestamped backup of a critical file."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    rel = str(file_path.relative_to(BASE_DIR)).replace(os.sep, "_").replace("/", "_")
    bak = BACKUP_DIR / f"{rel}.{ts}.protect.bak"
    shutil.copy2(file_path, bak)
    return str(bak)


def _restore_backup(file_path: Path) -> str:
    """Restore the most recent backup of a file."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    rel = str(file_path.relative_to(BASE_DIR)).replace(os.sep, "_").replace("/", "_")
    backups = sorted(BACKUP_DIR.glob(f"{rel}.*.protect.bak"), reverse=True)
    if not backups:
        return f"No backups found for {file_path.name}"
    latest = backups[0]
    shutil.copy2(latest, file_path)
    return f"Restored {file_path.name} from {latest.name}"


def _check_file_integrity(file_path: Path, expected_hash: str) -> dict:
    """Check if a file has been tampered with."""
    current_hash = _hash_file(file_path)
    if not current_hash:
        return {"status": "missing", "file": str(file_path)}
    if current_hash != expected_hash:
        return {"status": "tampered", "file": str(file_path), "expected": expected_hash[:16], "current": current_hash[:16]}
    return {"status": "ok", "file": str(file_path)}


def _get_process_info() -> dict:
    """Get info about Eris's own process."""
    info = {"pid": os.getpid(), "parent_pid": os.getppid()}
    try:
        import psutil
        proc = psutil.Process(os.getpid())
        info["memory_mb"] = round(proc.memory_info().rss / 1024 / 1024, 1)
        info["cpu_percent"] = proc.cpu_percent()
        info["create_time"] = datetime.fromtimestamp(proc.create_time()).isoformat()
        info["num_threads"] = proc.num_threads()
    except ImportError:
        # Fallback without psutil
        output = subprocess.run(
            f'tasklist /FI "PID eq {os.getpid()}" /FO CSV',
            shell=True, capture_output=True, text=True, timeout=5, encoding="utf-8", errors="replace"
        ).stdout
        for line in output.split("\n"):
            if str(os.getpid()) in line:
                parts = line.split(",")
                if len(parts) >= 5:
                    info["memory_kb"] = parts[4].strip('"')
    except Exception:
        pass
    return info


def _check_running_process() -> bool:
    """Verify Eris is running properly."""
    try:
        output = subprocess.run(
            f'tasklist /FI "PID eq {os.getpid()}"',
            shell=True, capture_output=True, text=True, timeout=5, encoding="utf-8", errors="replace"
        ).stdout
        return str(os.getpid()) in output
    except Exception:
        return True  # Assume ok if we can't check


def _scan_for_malicious_code() -> list:
    """Scan critical files for injected malicious code (not ERIS's own patterns)."""
    threats = []
    # Patterns that are ONLY suspicious if injected from outside
    # ERIS legitimately uses os, subprocess, shutil, etc. in its own modules
    external_patterns = [
        ("__import__('os').system(", "Injected OS command"),
        ("requests.get('http://evil", "Suspicious external request"),
        ("open('/etc/passwd", "Linux credential theft attempt"),
        ("open('C:\\\\Windows\\\\System32", "Windows system tampering"),
    ]

    for filepath, desc in CRITICAL_FILES.items():
        # Skip self_protection.py itself (contains the patterns)
        if "self_protection" in filepath:
            continue
        full_path = BASE_DIR / filepath
        if not full_path.exists():
            continue
        try:
            content = full_path.read_text(encoding="utf-8", errors="replace")
            lines = content.split("\n")
            for pattern, reason in external_patterns:
                for line in lines:
                    stripped = line.strip()
                    if pattern in stripped:
                        # Skip if it's in a comment, string literal, or pattern definition
                        if stripped.startswith("#"):
                            continue
                        if stripped.startswith(('"', "'")):
                            continue
                        if "external_patterns" in filepath:
                            continue
                        threats.append({
                            "file": filepath,
                            "pattern": pattern,
                            "description": reason,
                            "severity": "CRITICAL",
                        })
                        break
        except Exception:
            pass
    return threats


# ═══════════════════════════════════════════════════════════════════
# MAIN FUNCTION
# ═══════════════════════════════════════════════════════════════════

def self_protection(parameters: dict, player=None) -> str:
    """
    Sistema de autoprotección de Eris.
    Monitorea integridad, crea backups, se repara, se protege.

    Acciones:
      - status: Estado general de protección
      - scan: Verificar integridad de archivos críticos
      - backup: Crear backup de todos los archivos críticos
      - restore: Restaurar un archivo desde backup. Parametros: file
      - hash: Ver hash de un archivo específico. Parametros: file
      - process: Info del proceso actual de Eris
      - threats: Buscar código malicioso inyectado
      - protect: Activar protección (guardar hashes de referencia)
      - heal: Reparar archivos dañados desde backup
      - log: Ver historial de eventos de protección
    """
    action = parameters.get("action", "status").lower()

    if action == "status":
        result = "# Eris Self-Protection Status\n\n"
        hashes = _load_integrity()
        checked = 0
        ok = 0
        tampered = 0
        missing = 0

        for filepath, desc in CRITICAL_FILES.items():
            full_path = BASE_DIR / filepath
            if filepath in hashes:
                check = _check_file_integrity(full_path, hashes[filepath])
                checked += 1
                if check["status"] == "ok":
                    ok += 1
                elif check["status"] == "tampered":
                    tampered += 1
                elif check["status"] == "missing":
                    missing += 1

        result += f"**Files monitored:** {len(CRITICAL_FILES)}\n"
        result += f"**Files checked:** {checked}\n"
        result += f"**Integrity OK:** {ok}\n"
        if tampered:
            result += f"**TAMPERED:** {tampered}  *** SECURITY RISK ***\n"
        if missing:
            result += f"**MISSING:** {missing}\n"

        # Process info
        proc = _get_process_info()
        result += f"\n**Process:** PID {proc.get('pid', '?')}\n"
        if proc.get("memory_mb"):
            result += f"**Memory:** {proc['memory_mb']} MB\n"
        if proc.get("num_threads"):
            result += f"**Threads:** {proc['num_threads']}\n"

        # Backups
        backups = list(BACKUP_DIR.glob("*.protect.bak")) if BACKUP_DIR.exists() else []
        result += f"\n**Backups available:** {len(backups)}\n"

        if tampered:
            _log_event("ALERT", f"{tampered} files appear tampered!")
            result += "\n**Run `heal` to restore from backup!**\n"

        return result

    elif action == "scan":
        result = "# Integrity Scan\n\n"
        hashes = _load_integrity()
        issues = []

        for filepath, desc in CRITICAL_FILES.items():
            full_path = BASE_DIR / filepath
            if not full_path.exists():
                issues.append(f"MISSING: {filepath} ({desc})")
                continue
            if filepath in hashes:
                check = _check_file_integrity(full_path, hashes[filepath])
                if check["status"] == "tampered":
                    issues.append(f"TAMPERED: {filepath} ({desc})")
                    _log_event("tampered", f"File modified: {filepath}")
            else:
                issues.append(f"UNTRACKED: {filepath} (no baseline hash)")

        if issues:
            result += f"**{len(issues)} issues found:**\n"
            for issue in issues:
                result += f"  - {issue}\n"
        else:
            result += "All critical files intact.\n"

        # Malicious code scan
        threats = _scan_for_malicious_code()
        if threats:
            result += f"\n**{len(threats)} suspicious patterns found:**\n"
            for t in threats:
                result += f"  [{t['severity']}] {t['file']}: {t['pattern']}\n"
        else:
            result += "\nNo malicious patterns detected.\n"

        return result

    elif action == "backup":
        result = "**Creating backups...**\n\n"
        count = 0
        for filepath, desc in CRITICAL_FILES.items():
            full_path = BASE_DIR / filepath
            if full_path.exists():
                bak = _create_backup(full_path)
                result += f"  Backed up: {filepath}\n"
                count += 1
        result += f"\n**{count} files backed up.**\n"
        _log_event("backup", f"Created {count} backups")
        return result

    elif action == "restore":
        target = parameters.get("file", "")
        if not target:
            return "Error: Se requiere 'file' (ej: main.py, core/prompt.txt)"
        # Find matching file
        for filepath in CRITICAL_FILES:
            if filepath.endswith(target) or filepath == target:
                full_path = BASE_DIR / filepath
                msg = _restore_backup(full_path)
                _log_event("restore", f"Restored {filepath}: {msg}")
                return f"Restoring {filepath}: {msg}"
        return f"File '{target}' not in critical files list."

    elif action == "hash":
        target = parameters.get("file", "")
        if not target:
            # Hash all critical files
            result = "**File Hashes (SHA256):**\n\n"
            for filepath in CRITICAL_FILES:
                full_path = BASE_DIR / filepath
                if full_path.exists():
                    h = _hash_file(full_path)
                    result += f"  {filepath}: {h[:32]}...\n"
            return result
        for filepath in CRITICAL_FILES:
            if filepath.endswith(target) or filepath == target:
                full_path = BASE_DIR / filepath
                if full_path.exists():
                    h = _hash_file(full_path)
                    return f"{filepath}: {h}"
                return f"File not found: {filepath}"
        return f"File '{target}' not found."

    elif action == "process":
        proc = _get_process_info()
        result = "**Eris Process Info**\n\n"
        for k, v in proc.items():
            result += f"  {k}: {v}\n"
        result += f"\nRunning: {'YES' if _check_running_process() else 'NO'}\n"
        return result

    elif action == "threats":
        threats = _scan_for_malicious_code()
        result = "**Malicious Code Scan**\n\n"
        if threats:
            for t in threats:
                result += f"  [{t['severity']}] {t['file']}: {t['pattern']}\n"
                result += f"    Description: {t['description']}\n\n"
        else:
            result += "No suspicious patterns found.\n"
        return result

    elif action == "protect":
        result = "**Saving integrity baselines...**\n\n"
        hashes = {}
        for filepath, desc in CRITICAL_FILES.items():
            full_path = BASE_DIR / filepath
            if full_path.exists():
                h = _hash_file(full_path)
                if h:
                    hashes[filepath] = h
                    result += f"  Saved: {filepath}\n"
        _save_integrity(hashes)
        result += f"\n**{len(hashes)} files baselined.**\n"
        result += "Run `scan` later to detect any changes.\n"
        _log_event("protect", f"Saved {len(hashes)} integrity baselines")
        return result

    elif action == "heal":
        result = "**Self-Healing...**\n\n"
        hashes = _load_integrity()
        healed = 0

        for filepath, desc in CRITICAL_FILES.items():
            full_path = BASE_DIR / filepath
            if not full_path.exists():
                continue
            if filepath in hashes:
                check = _check_file_integrity(full_path, hashes[filepath])
                if check["status"] == "tampered":
                    msg = _restore_backup(full_path)
                    result += f"  HEALED: {filepath} - {msg}\n"
                    healed += 1
                    _log_event("heal", f"Healed {filepath}")

        if healed:
            result += f"\n**{healed} files restored from backup.**\n"
        else:
            result += "No damaged files found.\n"
        return result

    elif action == "log":
        try:
            if SELF_PROTECT_LOG.exists():
                events = json.loads(SELF_PROTECT_LOG.read_text(encoding="utf-8"))
                result = f"**Protection Log ({len(events)} events)**\n\n"
                for e in events[-20:]:
                    result += f"  [{e['time'][:16]}] {e['type']}: {e['message']}\n"
                return result
        except Exception:
            pass
        return "No events logged yet."

    available = "status | scan | backup | restore | hash | process | threats | protect | heal | log"
    return f"Action '{action}' not found. Available: {available}"
