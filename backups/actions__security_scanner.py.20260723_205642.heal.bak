"""
security_scanner.py — ERIS Security Scanner.
Detector de virus, malware y archivos sospechosos usando:
  - Windows Defender (MpCmdRun.exe)
  - PowerShell Get-MpThreat (amenazas activas)
  - Análisis heurístico (patrones sospechosos)
  - Hash SHA256 para verificación
  - Escaneo de USB y dispositivos conectados

REGLA DE SEGURIDAD: SIEMPRE pide confirmación antes de eliminar o poner en cuarentena.
"""
from __future__ import annotations

import hashlib
import os
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# ── Suspicious patterns ───────────────────────────────────────────────────────

_SUSPICIOUS_EXTENSIONS = {
    ".exe", ".bat", ".cmd", ".ps1", ".vbs", ".js", ".wsf", ".scr", ".pif",
    ".com", ".msi", ".dll", ".sys", ".drv", ".inf", ".reg",
}

_HIGH_RISK_EXTENSIONS = {
    ".vbs", ".ps1", ".bat", ".cmd", ".scr", ".pif", ".wsf",
}

_SUSPICIOUS_NAMES = [
    "keygen", "crack", "patch", "activator", "loader", "trojan", "virus",
    "worm", "backdoor", "rootkit", "spyware", "ransomware", "miner",
    "stealer", "logger", "injector", "exploit",
]

# ─ Helpers ───────────────────────────────────────────────────────────────────

def _run_cmd(cmd: list[str], timeout: int = 60) -> str:
    """Run command and return stdout. Cross-platform."""
    try:
        import sys
        creationflags = 0
        if sys.platform == "win32":
            creationflags = 0x08000000  # CREATE_NO_WINDOW
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=creationflags,
            encoding="utf-8",
            errors="ignore",
        )
        return result.stdout or ""
    except subprocess.TimeoutExpired:
        return f"Timeout after {timeout}s"
    except Exception as e:
        return f"Error: {e}"

def _run_ps(script: str, timeout: int = 30) -> str:
    """Run PowerShell script (Windows only)."""
    import sys
    if sys.platform != "win32":
        return "PowerShell not available on this platform"
    cmd = ["powershell", "-NoProfile", "-Command", script]
    return _run_cmd(cmd, timeout)

def _defender_available() -> bool:
    """Check if Windows Defender is available."""
    import sys
    if sys.platform != "win32":
        return False
    try:
        mp_path = Path(r"C:\Program Files\Windows Defender\MpCmdRun.exe")
        if mp_path.exists():
            return True
        # Try via PowerShell
        output = _run_ps("Get-MpPreference | Select-Object -ExpandProperty DisableRealtimeMonitoring", timeout=5)
        return "error" not in output.lower()
    except Exception:
        return False

def _clamav_available() -> bool:
    """Check if ClamAV is available (Linux)."""
    import sys
    if sys.platform != "linux":
        return False
    import shutil
    return shutil.which("clamscan") is not None

def _rkhunter_available() -> bool:
    """Check if RKHunter is available (Linux)."""
    import sys
    if sys.platform != "linux":
        return False
    import shutil
    return shutil.which("rkhunter") is not None

def _get_scanner_type() -> str:
    """Return the available scanner type: defender, clamav, rkhunter, or none."""
    if _defender_available():
        return "defender"
    if _clamav_available():
        return "clamav"
    if _rkhunter_available():
        return "rkhunter"
    return "none"

def _calculate_hash(path: str) -> str:
    """Calculate SHA256 hash of a file."""
    try:
        sha256 = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
    except Exception:
        return ""

def _format_size(b: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} TB"

# ── Scan file with Windows Defender ──────────────────────────────────────────

def _scan_file_defender(path: str) -> dict:
    """Scan a single file with Windows Defender."""
    result = {
        "path": path,
        "name": Path(path).name,
        "status": "clean",
        "threats": [],
        "details": "",
    }
    
    try:
        mp_path = Path(r"C:\Program Files\Windows Defender\MpCmdRun.exe")
        if not mp_path.exists():
            result["status"] = "unknown"
            result["details"] = "Windows Defender no encontrado."
            return result
        
        cmd = [
            str(mp_path), "-Scan", "-ScanType", "3", "-File", path,
            "-DisableRemediation"
        ]
        output = _run_cmd(cmd, timeout=120)
        
        if "No threats found" in output or "No se encontraron amenazas" in output:
            result["status"] = "clean"
            result["details"] = "No se detectaron amenazas."
        elif "threat" in output.lower() or "amenaza" in output.lower():
            result["status"] = "infected"
            result["details"] = output.strip()[:500]
            # Extract threat name
            threat_match = re.search(r'Threat:\s*(\S+)', output)
            if threat_match:
                result["threats"].append(threat_match.group(1))
        else:
            result["status"] = "unknown"
            result["details"] = output.strip()[:500]
    except Exception as e:
        result["status"] = "error"
        result["details"] = str(e)
    
    return result

# ── Scan folder with Windows Defender ────────────────────────────────────────

def _scan_folder_defender(path: str) -> dict:
    """Scan a folder with Windows Defender."""
    result = {
        "path": path,
        "status": "clean",
        "threats_found": 0,
        "details": "",
        "scanned_files": 0,
    }
    
    try:
        mp_path = Path(r"C:\Program Files\Windows Defender\MpCmdRun.exe")
        if not mp_path.exists():
            result["status"] = "unknown"
            result["details"] = "Windows Defender no encontrado."
            return result
        
        cmd = [
            str(mp_path), "-Scan", "-ScanType", "3", "-File", path,
            "-DisableRemediation"
        ]
        output = _run_cmd(cmd, timeout=300)
        
        if "No threats found" in output or "No se encontraron amenazas" in output:
            result["status"] = "clean"
            result["details"] = "No se detectaron amenazas en la carpeta."
        elif "threat" in output.lower() or "amenaza" in output.lower():
            result["status"] = "infected"
            result["details"] = output.strip()[:1000]
            threat_count = len(re.findall(r'Threat:', output, re.IGNORECASE))
            result["threats_found"] = threat_count if threat_count > 0 else 1
        else:
            result["status"] = "unknown"
            result["details"] = output.strip()[:500]
    except Exception as e:
        result["status"] = "error"
        result["details"] = str(e)
    
    return result

# ── Scan file with ClamAV (Linux) ────────────────────────────────────────────

def _scan_file_clamav(path: str) -> dict:
    """Scan a single file with ClamAV."""
    import shutil
    result = {
        "path": path,
        "name": Path(path).name,
        "status": "clean",
        "threats": [],
        "details": "",
    }
    
    try:
        clamscan = shutil.which("clamscan")
        if not clamscan:
            result["status"] = "unknown"
            result["details"] = "ClamAV no encontrado. Instalá: sudo apt install clamav"
            return result
        
        cmd = [clamscan, "--no-summary", "--stdout", path]
        output = _run_cmd(cmd, timeout=120)
        
        if "OK" in output:
            result["status"] = "clean"
            result["details"] = "No se detectaron amenazas."
        elif "FOUND" in output:
            result["status"] = "infected"
            result["details"] = output.strip()[:500]
            threat_match = re.search(r'(\S+):\s+(\S+)\s+FOUND', output)
            if threat_match:
                result["threats"].append(threat_match.group(2))
        else:
            result["status"] = "unknown"
            result["details"] = output.strip()[:500]
    except Exception as e:
        result["status"] = "error"
        result["details"] = str(e)
    
    return result

# ── Scan folder with ClamAV (Linux) ──────────────────────────────────────────

def _scan_folder_clamav(path: str) -> dict:
    """Scan a folder with ClamAV."""
    import shutil
    result = {
        "path": path,
        "status": "clean",
        "threats_found": 0,
        "details": "",
        "scanned_files": 0,
    }
    
    try:
        clamscan = shutil.which("clamscan")
        if not clamscan:
            result["status"] = "unknown"
            result["details"] = "ClamAV no encontrado. Instalá: sudo apt install clamav"
            return result
        
        cmd = [clamscan, "-r", "--no-summary", "--stdout", path]
        output = _run_cmd(cmd, timeout=300)
        
        if "OK" in output:
            result["status"] = "clean"
            result["details"] = "No se detectaron amenazas en la carpeta."
        elif "FOUND" in output:
            result["status"] = "infected"
            result["details"] = output.strip()[:1000]
            result["threats_found"] = len(re.findall(r'FOUND', output))
        else:
            result["status"] = "unknown"
            result["details"] = output.strip()[:500]
    except Exception as e:
        result["status"] = "error"
        result["details"] = str(e)
    
    return result

# ── RKHunter scan (Linux) ────────────────────────────────────────────────────

def _scan_rkhunter() -> dict:
    """Run RKHunter rootkit scan (Linux)."""
    import shutil
    result = {
        "status": "unknown",
        "details": "",
        "warnings": [],
    }
    
    try:
        rkhunter = shutil.which("rkhunter")
        if not rkhunter:
            result["status"] = "unknown"
            result["details"] = "RKHunter no encontrado. Instalá: sudo apt install rkhunter"
            return result
        
        cmd = [rkhunter, "--check", "--skip-keypress", "--nocolors"]
        output = _run_cmd(cmd, timeout=300)
        
        if "System checks summary" in output:
            # Parse summary
            warnings = re.findall(r'Warning: (.+)', output)
            result["warnings"] = warnings
            if warnings:
                result["status"] = "warning"
                result["details"] = f"{len(warnings)} advertencias encontradas."
            else:
                result["status"] = "clean"
                result["details"] = "No se detectaron rootkits."
        else:
            result["status"] = "unknown"
            result["details"] = output.strip()[:500]
    except Exception as e:
        result["status"] = "error"
        result["details"] = str(e)
    
    return result

# ── Check active threats ─────────────────────────────────────────────────────

def _check_active_threats() -> list[dict]:
    """Check for active threats via PowerShell."""
    threats = []
    try:
        output = _run_ps("Get-MpThreat | Select-Object -Property ThreatName, Severity, Resources, InitialDetectionTime | Format-List", timeout=10)
        if output.strip():
            # Parse threat info
            lines = output.strip().split("\n")
            current_threat = {}
            for line in lines:
                if ":" in line:
                    key, _, val = line.partition(":")
                    key = key.strip()
                    val = val.strip()
                    if key == "ThreatName":
                        current_threat["name"] = val
                    elif key == "Severity":
                        current_threat["severity"] = val
                    elif key == "Resources":
                        current_threat["resources"] = val
                    elif key == "InitialDetectionTime":
                        current_threat["detected"] = val
                        if current_threat.get("name"):
                            threats.append(current_threat)
                            current_threat = {}
    except Exception:
        pass
    return threats

# ── Heuristic analysis ───────────────────────────────────────────────────────

def _heuristic_analysis(path: str) -> dict:
    """Analyze file for suspicious patterns."""
    result = {
        "path": path,
        "name": Path(path).name,
        "risk_level": "low",
        "flags": [],
    }
    
    p = Path(path)
    ext = p.suffix.lower()
    name_lower = p.name.lower()
    
    # Check extension
    if ext in _HIGH_RISK_EXTENSIONS:
        result["risk_level"] = "high"
        result["flags"].append(f"Extensión de alto riesgo: {ext}")
    elif ext in _SUSPICIOUS_EXTENSIONS:
        result["risk_level"] = "medium"
        result["flags"].append(f"Extensión sospechosa: {ext}")
    
    # Check name
    for suspicious in _SUSPICIOUS_NAMES:
        if suspicious in name_lower:
            result["risk_level"] = "high"
            result["flags"].append(f"Nombre sospechoso: contiene '{suspicious}'")
    
    # Check if in Downloads folder
    if "downloads" in path.lower():
        if ext in _SUSPICIOUS_EXTENSIONS:
            result["flags"].append("Archivo ejecutable en Downloads (común en malware)")
    
    # Check file size (very small executables are suspicious)
    try:
        size = p.stat().st_size
        if ext in (".exe", ".dll", ".scr") and size < 10000:
            result["risk_level"] = "high"
            result["flags"].append(f"Tamaño muy pequeño para {ext}: {_format_size(size)}")
    except Exception:
        pass
    
    # Check if recently created
    try:
        created = datetime.fromtimestamp(p.stat().st_ctime)
        age_hours = (datetime.now() - created).total_seconds() / 3600
        if age_hours < 1 and ext in _SUSPICIOUS_EXTENSIONS:
            result["flags"].append(f"Archivo creado hace menos de 1 hora")
    except Exception:
        pass
    
    return result

# ── Scan USB drives ──────────────────────────────────────────────────────────

def _scan_usb_drives() -> list[dict]:
    """Scan connected USB drives for threats."""
    results = []
    try:
        output = _run_ps("Get-WmiObject Win32_LogicalDisk | Where-Object { $_.DriveType -eq 2 } | Select-Object -ExpandProperty DeviceID", timeout=10)
        drives = [d.strip() for d in output.strip().split("\n") if d.strip()]
        
        for drive in drives:
            result = {
                "drive": drive,
                "status": "clean",
                "threats": [],
                "files_scanned": 0,
            }
            
            # Quick scan for suspicious files
            try:
                ps_script = f"""
                Get-ChildItem -Path "{drive}" -Recurse -File | Where-Object {{
                    $ext = $_.Extension.ToLower()
                    $ext -in @('.exe', '.bat', '.cmd', '.vbs', '.ps1', '.scr', '.pif', '.js')
                }} | Select-Object -First 20 FullName, Length, LastWriteTime | Format-List
                """
                suspicious_output = _run_ps(ps_script, timeout=30)
                
                if suspicious_output.strip():
                    result["status"] = "suspicious"
                    result["details"] = suspicious_output.strip()[:1000]
            except Exception:
                pass
            
            results.append(result)
    except Exception:
        pass
    
    return results

# ── Quick scan of common locations ───────────────────────────────────────────

def _quick_scan() -> dict:
    """Quick scan of common malware locations."""
    result = {
        "status": "clean",
        "locations_scanned": [],
        "threats_found": 0,
        "details": "",
    }
    
    locations = [
        str(Path.home() / "Downloads"),
        str(Path.home() / "Desktop"),
        str(Path.home() / "AppData" / "Local" / "Temp"),
        str(Path.home() / "AppData" / "Roaming"),
    ]
    
    for loc in locations:
        if not os.path.exists(loc):
            continue
        result["locations_scanned"].append(loc)
        
        # Check for suspicious files
        try:
            ps_script = f"""
            Get-ChildItem -Path "{loc}" -File | Where-Object {{
                $ext = $_.Extension.ToLower()
                $ext -in @('.exe', '.bat', '.cmd', '.vbs', '.ps1', '.scr', '.pif', '.js', '.wsf')
            }} | Select-Object -First 10 FullName, Length, LastWriteTime | Format-List
            """
            output = _run_ps(ps_script, timeout=15)
            if output.strip():
                result["status"] = "suspicious"
                result["details"] += f"\n\n{loc}:\n{output.strip()[:500]}"
        except Exception:
            pass
    
    if result["status"] == "clean":
        result["details"] = "No se encontraron archivos sospechosos en las ubicaciones comunes."
    
    return result

# ── Quarantine ───────────────────────────────────────────────────────────────

def _quarantine_file(path: str) -> str:
    """Move file to quarantine folder."""
    try:
        quarantine_dir = Path.home() / "ERIS_Quarantine"
        quarantine_dir.mkdir(exist_ok=True)
        
        p = Path(path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_name = f"{timestamp}_{p.name}"
        new_path = quarantine_dir / new_name
        
        p.rename(new_path)
        return f"✅ Archivo movido a cuarentena: {new_path}"
    except Exception as e:
        return f"Error moviendo a cuarentena: {e}"

def _delete_file(path: str) -> str:
    """Delete file permanently."""
    try:
        p = Path(path)
        if p.exists():
            p.unlink()
            return f"✅ Archivo eliminado: {p.name}"
        return f"Archivo no encontrado: {path}"
    except Exception as e:
        return f"Error eliminando archivo: {e}"

# ── Tool function ─────────────────────────────────────────────────────────────

def security_scanner(parameters: dict, player=None, **kwargs) -> str:
    """
    Escáner de seguridad de ERIS. Detecta virus, malware y archivos sospechosos.
    
    parameters:
        action: 'scan_file' | 'scan_folder' | 'quick_scan' | 'full_scan' | 'scan_usb' | 'check_threats' | 'analyze' | 'quarantine' | 'delete' | 'status'
        path: ruta del archivo o carpeta a escanear
        deep: escaneo profundo (default: False)
        confirm: confirmación del usuario (obligatorio para delete/quarantine)
    """
    params = parameters or {}
    action = params.get("action", "quick_scan").lower()
    path = params.get("path", "")
    confirm = params.get("confirm", False)
    
    if player:
        player.write_log(f"🛡️ Security Scanner: {action} {path}")
    
    # ── STATUS ────────────────────────────────────────────────────────────────
    if action in ("status", "estado"):
        scanner_type = _get_scanner_type()
        threats = _check_active_threats()
        
        lines = ["️ Estado de Seguridad:"]
        
        if scanner_type == "defender":
            lines.append(f"  Windows Defender: ✅ Activo")
        elif scanner_type == "clamav":
            lines.append(f"  ClamAV: ✅ Activo")
        elif scanner_type == "rkhunter":
            lines.append(f"  RKHunter: ✅ Activo")
        else:
            lines.append(f"  Scanner: ❌ No disponible (instalá clamav o rkhunter en Linux)")
        
        if threats:
            lines.append(f"  ⚠️ Amenazas activas: {len(threats)}")
            for t in threats:
                lines.append(f"    • {t.get('name', '?')} (Severidad: {t.get('severity', '?')})")
        else:
            lines.append("  ✅ No hay amenazas activas detectadas")
        
        return "\n".join(lines)
    
    # ── SCAN FILE ─────────────────────────────────────────────────────────────
    elif action in ("scan_file", "scan"):
        if not path:
            return "Especificá la ruta del archivo a escanear."
        
        if not os.path.exists(path):
            return f"Archivo no encontrado: {path}"
        
        # Heuristic analysis first
        heuristic = _heuristic_analysis(path)
        
        # Cross-platform scanner
        scanner_type = _get_scanner_type()
        if scanner_type == "defender":
            scanner_result = _scan_file_defender(path)
            scanner_name = "Windows Defender"
        elif scanner_type == "clamav":
            scanner_result = _scan_file_clamav(path)
            scanner_name = "ClamAV"
        else:
            scanner_result = {"status": "unknown", "details": "No hay scanner disponible."}
            scanner_name = "Ninguno"
        
        # Calculate hash
        file_hash = _calculate_hash(path)
        
        # Format results
        lines = [f"🛡️ Análisis de: {Path(path).name}"]
        lines.append(f"  📍 {path}")
        lines.append(f"  📏 {_format_size(os.path.getsize(path))}")
        lines.append(f"  🔑 SHA256: {file_hash[:32]}...")
        lines.append("")
        
        lines.append(f"  {scanner_name}: {scanner_result['status'].upper()}")
        if scanner_result.get("details"):
            lines.append(f"    {scanner_result['details'][:200]}")
        
        if heuristic["flags"]:
            lines.append(f"  ⚠️ Análisis heurístico:")
            for flag in heuristic["flags"]:
                lines.append(f"    • {flag}")
            lines.append(f"  Nivel de riesgo: {heuristic['risk_level'].upper()}")
        else:
            lines.append("  ✅ Análisis heurístico: Sin banderas sospechosas")
        
        return "\n".join(lines)
    
    # ── SCAN FOLDER ───────────────────────────────────────────────────────────
    elif action in ("scan_folder", "folder"):
        if not path:
            return "Especificá la ruta de la carpeta a escanear."
        
        if not os.path.exists(path):
            return f"Carpeta no encontrada: {path}"
        
        scanner_type = _get_scanner_type()
        if scanner_type == "defender":
            result = _scan_folder_defender(path)
            scanner_name = "Windows Defender"
        elif scanner_type == "clamav":
            result = _scan_folder_clamav(path)
            scanner_name = "ClamAV"
        else:
            return "No hay scanner disponible para escanear carpetas. Instalá clamav (Linux) o usá Windows Defender (Windows)."
        
        lines = [f"️ Escaneo de carpeta: {path}"]
        lines.append(f"  Scanner: {scanner_name}")
        lines.append(f"  Estado: {result['status'].upper()}")
        if result.get("threats_found", 0) > 0:
            lines.append(f"  ⚠️ Amenazas encontradas: {result['threats_found']}")
        lines.append(f"  {result.get('details', '')[:500]}")
        return "\n".join(lines)
    
    # ── QUICK SCAN ────────────────────────────────────────────────────────────
    elif action in ("quick_scan", "rapido"):
        result = _quick_scan()
        lines = ["🛡️ Escaneo rápido de seguridad:"]
        lines.append(f"  Ubicaciones escaneadas: {len(result['locations_scanned'])}")
        for loc in result["locations_scanned"]:
            lines.append(f"    • {loc}")
        lines.append("")
        lines.append(f"  Estado: {result['status'].upper()}")
        if result.get("details"):
            lines.append(f"  {result['details'][:500]}")
        return "\n".join(lines)
    
    # ── FULL SCAN ─────────────────────────────────────────────────────────────
    elif action in ("full_scan", "completo", "full"):
        scanner_type = _get_scanner_type()
        
        if scanner_type == "defender":
            mp_path = r"C:\Program Files\Windows Defender\MpCmdRun.exe"
            if not confirm:
                return (
                    "️ Voy a realizar un escaneo COMPLETO del sistema con Windows Defender.\n"
                    "   Esto puede tardar 30-60 minutos.\n"
                    "   ¿Confirmás el escaneo completo? Respondé 'sí, escaneá' para continuar."
                )
            
            output = _run_cmd([mp_path, "-Scan", "-ScanType", "2"], timeout=3600)
            return f"🛡️ Escaneo completo:\n{output.strip()[:2000]}"
        
        elif scanner_type == "clamav":
            import shutil
            clamscan = shutil.which("clamscan")
            if not confirm:
                return (
                    "⚠️ Voy a realizar un escaneo COMPLETO del sistema con ClamAV.\n"
                    "   Esto puede tardar 30-60 minutos.\n"
                    "   ¿Confirmás el escaneo completo? Respondé 'sí, escaneá' para continuar."
                )
            
            output = _run_cmd([clamscan, "-r", "/"], timeout=3600)
            return f"🛡️ Escaneo completo:\n{output.strip()[:2000]}"
        
        elif scanner_type == "rkhunter":
            if not confirm:
                return (
                    "⚠️ Voy a realizar un escaneo de rootkits con RKHunter.\n"
                    "   Esto puede tardar 10-20 minutos.\n"
                    "   ¿Confirmás el escaneo? Respondé 'sí, escaneá' para continuar."
                )
            
            result = _scan_rkhunter()
            lines = ["🛡️ Escaneo de rootkits:"]
            lines.append(f"  Estado: {result['status'].upper()}")
            if result.get("warnings"):
                lines.append(f"  ⚠️ Advertencias: {len(result['warnings'])}")
                for w in result["warnings"][:10]:
                    lines.append(f"    • {w}")
            lines.append(f"  {result.get('details', '')[:500]}")
            return "\n".join(lines)
        
        else:
            return "No hay scanner disponible. Instalá clamav (Linux) o usá Windows Defender (Windows)."
    
    # ── SCAN USB ──────────────────────────────────────────────────────────────
    elif action in ("scan_usb", "usb"):
        results = _scan_usb_drives()
        if not results:
            return "🛡️ No se detectaron unidades USB conectadas."
        
        lines = ["🛡️ Escaneo de unidades USB:"]
        for r in results:
            lines.append(f"  Unidad: {r['drive']}")
            lines.append(f"  Estado: {r['status'].upper()}")
            if r.get("details"):
                lines.append(f"  {r['details'][:300]}")
            lines.append("")
        return "\n".join(lines)
    
    # ─ CHECK ACTIVE THREATS ──────────────────────────────────────────────────
    elif action in ("check_threats", "threats", "amenazas"):
        import sys
        if sys.platform != "win32":
            return "🛡️ La detección de amenazas activas solo está disponible en Windows (Windows Defender)."
        
        threats = _check_active_threats()
        if not threats:
            return "🛡️ No hay amenazas activas detectadas por Windows Defender."
        
        lines = ["⚠️ Amenazas activas detectadas:"]
        for t in threats:
            lines.append(f"  • {t.get('name', '?')}")
            lines.append(f"    Severidad: {t.get('severity', '?')}")
            if t.get("resources"):
                lines.append(f"    Recursos: {t['resources'][:200]}")
            if t.get("detected"):
                lines.append(f"    Detectado: {t['detected']}")
            lines.append("")
        return "\n".join(lines)
    
    # ── ANALYZE (heuristic only) ──────────────────────────────────────────────
    elif action in ("analyze", "analizar", "heuristic"):
        if not path:
            return "Especificá la ruta del archivo a analizar."
        
        result = _heuristic_analysis(path)
        lines = [f"🔍 Análisis heurístico: {Path(path).name}"]
        lines.append(f"  Nivel de riesgo: {result['risk_level'].upper()}")
        if result["flags"]:
            for flag in result["flags"]:
                lines.append(f"  ⚠️ {flag}")
        else:
            lines.append("  ✅ Sin banderas sospechosas")
        
        file_hash = _calculate_hash(path)
        lines.append(f"  🔑 SHA256: {file_hash[:32]}...")
        return "\n".join(lines)
    
    # ── QUARANTINE ────────────────────────────────────────────────────────────
    elif action in ("quarantine", "cuarentena"):
        if not path:
            return "Especificá la ruta del archivo a poner en cuarentena."
        
        if not confirm:
            p = Path(path)
            return (
                f"⚠️ Voy a mover '{p.name}' a la carpeta de cuarentena.\n"
                f"   El archivo no se eliminará, pero se aislará.\n"
                f"   ¿Confirmás? Respondé 'sí, poné en cuarentena' para continuar."
            )
        
        return _quarantine_file(path)
    
    # ── DELETE ────────────────────────────────────────────────────────────────
    elif action in ("delete", "eliminar"):
        if not path:
            return "Especificá la ruta del archivo a eliminar."
        
        if not confirm:
            p = Path(path)
            return (
                f"⚠️ Voy a eliminar PERMANENTEMENTE '{p.name}'.\n"
                f"   Esta acción NO se puede deshacer.\n"
                f"   ¿Confirmás la eliminación? Respondé 'sí, eliminá' para continuar."
            )
        
        return _delete_file(path)
    
    else:
        return f"Acción '{action}' desconocida. Opciones: scan_file, scan_folder, quick_scan, full_scan, scan_usb, check_threats, analyze, quarantine, delete, status."
