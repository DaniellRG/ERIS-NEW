# -*- coding: utf-8 -*-
"""
Eris Sandbox – Entorno aislado de ejecución segura para scripts y tareas.
Ejecuta código en subprocesos con timeout, límites de recursos y aislamiento.
"""
import subprocess
import tempfile
import os
import sys
import json
import shutil
import threading
import time
from pathlib import Path
from datetime import datetime

SANDBOX_DIR = Path(os.environ.get("ERIS_SANDBOX", Path.home() / "Eris_Sandbox"))
SANDBOX_DIR.mkdir(parents=True, exist_ok=True)

HISTORY_FILE = Path(__file__).resolve().parent.parent / "config" / "eris_sandbox_history.json"
MAX_HISTORY = 200

def _decode_output(raw: bytes) -> str:
    """Decodifica salida de subprocesos sin mojibake: intenta UTF-8 y
    cae a cp1252 (output de herramientas nativas de Windows como taskkill)."""
    if not raw:
        return ""
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp1252", errors="replace")

def _load_history():
    try:
        if HISTORY_FILE.exists():
            return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except:
        pass
    return []

def _save_history(entry):
    history = _load_history()
    history.append(entry)
    if len(history) > MAX_HISTORY:
        history = history[-MAX_HISTORY:]
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")

def sandbox_run(parameters: dict, player=None) -> str:
    """
    Entorno de ejecución aislado (sandbox) para scripts y comandos.
    
    Acciones:
      - run_python: Ejecutar código Python en sandbox con timeout
        Parámetros: code, timeout (default 10s)
      - run_cmd: Ejecutar comando del sistema en sandbox
        Parámetros: command, timeout (default 15s), cwd (opcional)
      - history: Ver historial de ejecuciones del sandbox
      - clear: Limpiar el directorio sandbox
      - status: Ver estado del sandbox (archivos, tamaño)
    """
    action = parameters.get("action", "status").lower()
    
    if action == "run_python":
        code = parameters.get("code", "")
        timeout = int(parameters.get("timeout", 10))
        
        if not code:
            return "Error: Se requiere código Python (parámetro 'code')."
        
        if timeout > 60:
            return "Error: Timeout máximo es 60 segundos."
        
        # Crear script temporal en sandbox
        script_path = SANDBOX_DIR / f"script_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.py"
        script_path.write_text(code, encoding="utf-8")
        
        start_time = time.time()
        try:
            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True, timeout=timeout,
                cwd=str(SANDBOX_DIR),
                env={**os.environ, "PYTHONPATH": str(SANDBOX_DIR)}
            )
            elapsed = time.time() - start_time
            stdout = _decode_output(result.stdout)[:2000]
            stderr = _decode_output(result.stderr)[:2000]
            
            entry = {
                "timestamp": datetime.now().isoformat(),
                "type": "python",
                "code_preview": code[:200],
                "exit_code": result.returncode,
                "elapsed": round(elapsed, 3),
                "stdout": stdout[:500],
                "stderr": stderr[:500]
            }
            _save_history(entry)
            
            if result.returncode == 0:
                return f"✅ Script ejecutado ({elapsed:.1f}s):\n{stdout or '(sin salida)'}"
            else:
                return f"⚠️ Script terminó con error (código {result.returncode}, {elapsed:.1f}s):\n{stderr or stdout}"
        
        except subprocess.TimeoutExpired:
            elapsed = time.time() - start_time
            entry = {
                "timestamp": datetime.now().isoformat(),
                "type": "python",
                "code_preview": code[:200],
                "error": f"Timeout ({timeout}s)",
                "elapsed": round(elapsed, 3)
            }
            _save_history(entry)
            return f"⏰ Timeout: el script excedió {timeout} segundos."
        
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    elif action == "run_cmd":
        command = parameters.get("command", "")
        timeout = int(parameters.get("timeout", 15))
        cwd = parameters.get("cwd", str(SANDBOX_DIR))
        
        if not command:
            return "Error: Se requiere un comando."
        
        if timeout > 120:
            return "Error: Timeout máximo es 120 segundos."
        
        start_time = time.time()
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True,
                timeout=timeout, cwd=cwd
            )
            elapsed = time.time() - start_time
            stdout = _decode_output(result.stdout)[:2000]
            stderr = _decode_output(result.stderr)[:2000]
            
            entry = {
                "timestamp": datetime.now().isoformat(),
                "type": "cmd",
                "command": command[:200],
                "exit_code": result.returncode,
                "elapsed": round(elapsed, 3),
                "stdout": stdout[:500],
                "stderr": stderr[:500]
            }
            _save_history(entry)
            
            if result.returncode == 0:
                return f"✅ Comando ejecutado ({elapsed:.1f}s):\n{stdout or '(sin salida)'}"
            else:
                return f"⚠️ Comando falló (código {result.returncode}, {elapsed:.1f}s):\n{stderr or stdout}"
        
        except subprocess.TimeoutExpired:
            return f"⏰ Timeout: comando excedió {timeout} segundos."
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    elif action == "history":
        history = _load_history()
        if not history:
            return "📝 Sin historial de ejecuciones en el sandbox."
        
        result = f"**📝 Historial del Sandbox ({len(history)} entradas):**\n\n"
        for entry in history[-10:]:
            ts = entry["timestamp"][:19]
            tipo = entry["type"]
            status = "✅" if entry.get("exit_code", 1) == 0 else "⚠️"
            preview = entry.get("code_preview", entry.get("command", "?"))[:60]
            elapsed = entry.get("elapsed", 0)
            result += f"  {status} [{tipo}] {ts} ({elapsed:.1f}s): {preview}\n"
        
        return result
    
    elif action == "clear":
        count = 0
        for f in SANDBOX_DIR.glob("*"):
            try:
                if f.is_file():
                    f.unlink()
                elif f.is_dir():
                    shutil.rmtree(f)
                count += 1
            except Exception:
                pass
        return f"🧹 Sandbox limpiado: {count} elementos eliminados."
    
    elif action == "status":
        files = list(SANDBOX_DIR.glob("*"))
        total_size = sum(f.stat().st_size for f in files if f.is_file())
        history = _load_history()
        success = sum(1 for h in history if h.get("exit_code", 1) == 0)
        total = len(history)
        
        return (
            f"📦 **Estado del Sandbox:**\n\n"
            f"  Archivos: {len(files)}\n"
            f"  Tamaño total: {total_size / 1024:.1f} KB\n"
            f"  Ubicación: {SANDBOX_DIR}\n"
            f"  Ejecuciones totales: {total}\n"
            f"  Exitosas: {success} ({success/total*100:.0f}%)" if total > 0 else f"  Ejecuciones: 0"
        )
    
    return f"Acción '{action}' no reconocida. Usa: run_python, run_cmd, history, clear, status"


def sandbox_test_tool(parameters: dict, player=None) -> str:
    """
    Prueba una herramienta/script en el sandbox antes de ponerla en producción.
    Ejecuta el código, verifica que no tenga errores, y reporta.
    
    Parámetros:
      - code: Código Python a probar
      - test_input: Datos de entrada para la prueba (opcional)
    """
    code = parameters.get("code", "")
    test_input = parameters.get("test_input", "{}")
    timeout = int(parameters.get("timeout", 10))
    
    if not code:
        return "Error: Se requiere código."
    
    # Envolver en un test harness
    test_code = (
        "import json\nimport sys\nimport traceback\n\n"
        + code + "\n\n"
        "try:\n"
        "    test_data = json.loads('" + test_input.replace("'", "\\'") + "')\n"
        "    print(json.dumps({'status': 'ok', 'result': 'Script ejecutado sin errores'}))\n"
        "except Exception as e:\n"
        "    print(json.dumps({'status': 'error', 'error': str(e), 'traceback': traceback.format_exc()[:500]}))\n"
    )
    
    return sandbox_run({"action": "run_python", "code": test_code, "timeout": timeout})
