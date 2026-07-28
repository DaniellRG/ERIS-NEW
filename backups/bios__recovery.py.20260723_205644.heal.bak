import os
import sys
import json
import subprocess
from datetime import datetime

RECOVERY_MODE_FILE = None
RECOVERY_COUNT_FILE = None

def _init_paths():
    global RECOVERY_MODE_FILE, RECOVERY_COUNT_FILE
    if RECOVERY_MODE_FILE is not None:
        return
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    memory_dir = os.path.join(base, "memory")
    os.makedirs(memory_dir, exist_ok=True)
    RECOVERY_MODE_FILE = os.path.join(memory_dir, "recovery_mode.json")
    RECOVERY_COUNT_FILE = os.path.join(memory_dir, "recovery_count.json")

def is_recovery_mode():
    _init_paths()
    if not os.path.isfile(RECOVERY_MODE_FILE):
        return False
    try:
        with open(RECOVERY_MODE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("recovery", False)
    except Exception:
        return False

def enter_recovery_mode(reason="unknown"):
    _init_paths()
    try:
        entry = {
            "recovery": True,
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
            "attempts": _get_recovery_count() + 1
        }
        tmp = RECOVERY_MODE_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(entry, f, indent=2)
        os.replace(tmp, RECOVERY_MODE_FILE)
        _increment_recovery_count()
    except Exception:
        pass

def exit_recovery_mode():
    _init_paths()
    try:
        if os.path.isfile(RECOVERY_MODE_FILE):
            os.remove(RECOVERY_MODE_FILE)
        if os.path.isfile(RECOVERY_COUNT_FILE):
            os.remove(RECOVERY_COUNT_FILE)
    except Exception:
        pass

def _get_recovery_count():
    _init_paths()
    if not os.path.isfile(RECOVERY_COUNT_FILE):
        return 0
    try:
        with open(RECOVERY_COUNT_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("count", 0)
    except Exception:
        return 0

def _increment_recovery_count():
    _init_paths()
    count = _get_recovery_count() + 1
    try:
        tmp = RECOVERY_COUNT_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"count": count}, f)
        os.replace(tmp, RECOVERY_COUNT_FILE)
    except Exception:
        pass

def reset_recovery_count():
    _init_paths()
    try:
        if os.path.isfile(RECOVERY_COUNT_FILE):
            os.remove(RECOVERY_COUNT_FILE)
    except Exception:
        pass

def launch_recovery_ui():
    _init_paths()
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    log_path = os.path.join(os.path.dirname(RECOVERY_MODE_FILE), "eris.log")

    lines = [
        "=" * 50,
        "ERIS - MODO RECUPERACION",
        "=" * 50,
        "",
        "ERIS entro en modo recovery debido a crashes repetidos.",
        "",
        "Posibles causas:",
        "  - Error de conexion con Gemini API",
        "  - Microfono no disponible",
        "  - Archivo de configuracion corrupto",
        "  - Conflicto con otro programa",
        "",
        "Para reintentar: elimina el archivo 'recovery_mode.json'",
        "de la carpeta memory/ y reinicia ERIS.",
        "",
        "Si el problema persiste, revisa el log:",
        f"  {log_path}",
        "",
        "Presiona cualquier tecla para cerrar esta ventana."
    ]
    title = "ERIS - Modo Recovery"
    try:
        script = f'''
        $host.UI.RawUI.WindowTitle = "{title}"
        Write-Host "`n"{"".join(lines)}"`n"
        $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
        '''
        subprocess.run(["powershell", "-NoProfile", "-Command", script], check=False)
    except Exception:
        print("\n".join(lines))
        input("\nPresiona Enter para cerrar...")

def get_recovery_log():
    _init_paths()
    log_path = os.path.join(os.path.dirname(RECOVERY_MODE_FILE), "post_log.json")
    if not os.path.isfile(log_path):
        return []
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []
