import os
import sys
import json
import hashlib
import traceback
from datetime import datetime

POST_RESULTS = {
    "passed": False,
    "timestamp": None,
    "checks": [],
    "errors": [],
    "warnings": []
}

def _checksum_file(filepath):
    h = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
    except Exception:
        return None
    return h.hexdigest()

def run_post():
    POST_RESULTS["timestamp"] = datetime.now().isoformat()

    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    integrity_path = os.path.join(base, "config", "integrity.json")
    if os.path.isfile(integrity_path):
        try:
            with open(integrity_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            for relpath, expected in manifest.items():
                full = os.path.join(base, relpath) if not os.path.isabs(relpath) else relpath
                actual = _checksum_file(full)
                if actual is None:
                    POST_RESULTS["checks"].append({"file": relpath, "status": "missing"})
                    POST_RESULTS["warnings"].append(f"Archivo no encontrado: {relpath}")
                elif actual != expected:
                    POST_RESULTS["checks"].append({"file": relpath, "status": "corrupted"})
                    POST_RESULTS["errors"].append(f"Checksum falló: {relpath}")
                else:
                    POST_RESULTS["checks"].append({"file": relpath, "status": "ok"})
        except Exception as e:
            POST_RESULTS["warnings"].append(f"No se pudo leer integrity.json: {e}")
    else:
        POST_RESULTS["warnings"].append("No hay integrity.json — se omite verificación de integridad")

    PYTHON_ESSENTIALS = ["json", "os", "sys", "threading", "asyncio", "traceback", "hashlib", "datetime"]
    for mod in PYTHON_ESSENTIALS:
        try:
            __import__(mod)
            POST_RESULTS["checks"].append({"module": mod, "status": "ok"})
        except ImportError:
            POST_RESULTS["errors"].append(f"Módulo esencial faltante: {mod}")

    _log_result()

    if POST_RESULTS["errors"]:
        POST_RESULTS["passed"] = False
    else:
        POST_RESULTS["passed"] = True

    return POST_RESULTS

def _log_result():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    log_dir = os.path.join(base, "memory")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "post_log.json")
    try:
        existing = []
        if os.path.isfile(log_path):
            with open(log_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
        existing.append(POST_RESULTS)
        if len(existing) > 50:
            existing = existing[-50:]
        tmp = log_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)
        os.replace(tmp, log_path)
    except Exception:
        pass
