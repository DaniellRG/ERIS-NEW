"""
anomaly_detector.py — Detección de patrones inusuales en archivos, logs y código.

Detecta:
  - Archivos modificados inesperadamente (tamaño, fecha)
  - Líneas de código anómalas (imports raros, funciones sospechosas)
  - Patrones de logs inusuales (errores repetidos, picos)
  - Cambios estructurales (archivos nuevos/eliminados)
"""
from __future__ import annotations

import os
import json
import time
import hashlib
from pathlib import Path
from collections import defaultdict
from datetime import datetime

_BASE = Path(__file__).resolve().parent.parent
_BASELINE_FILE = _BASE / "data" / "anomaly_baseline.json"


def _load_baseline() -> dict:
    try:
        if _BASELINE_FILE.exists():
            return json.loads(_BASELINE_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"files": {}, "snapshots": [], "patterns": {}}


def _save_baseline(data: dict):
    try:
        _BASELINE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _BASELINE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def _file_hash(path: Path) -> str:
    try:
        return hashlib.md5(path.read_bytes()).hexdigest()[:12]
    except Exception:
        return ""


def take_snapshot(directories: list[str] = None) -> dict:
    """Toma snapshot del estado actual de archivos."""
    dirs = directories or [str(_BASE / "core"), str(_BASE / "actions")]
    baseline = _load_baseline()

    current_files = {}
    for d in dirs:
        p = Path(d)
        if not p.exists():
            continue
        for f in p.rglob("*.py"):
            try:
                stat = f.stat()
                rel = str(f.relative_to(_BASE))
                current_files[rel] = {
                    "size": stat.st_size,
                    "mtime": stat.st_mtime,
                    "hash": _file_hash(f),
                }
            except Exception:
                continue

    # Detectar cambios
    anomalies = []
    old_files = baseline.get("files", {})
    for rel, info in current_files.items():
        if rel in old_files:
            old = old_files[rel]
            if old["hash"] != info["hash"]:
                size_delta = info["size"] - old["size"]
                anomalies.append({
                    "type": "modified",
                    "file": rel,
                    "size_delta": size_delta,
                    "old_size": old["size"],
                    "new_size": info["size"],
                })
        else:
            anomalies.append({
                "type": "new_file",
                "file": rel,
                "size": info["size"],
            })

    for rel in old_files:
        if rel not in current_files:
            anomalies.append({
                "type": "deleted",
                "file": rel,
            })

    # Guardar snapshot
    baseline["files"] = current_files
    baseline["snapshots"].append({
        "timestamp": time.time(),
        "files_count": len(current_files),
        "anomalies": anomalies,
    })
    baseline["snapshots"] = baseline["snapshots"][-20:]
    _save_baseline(baseline)

    return {
        "files_tracked": len(current_files),
        "anomalies_found": len(anomalies),
        "anomalies": anomalies,
        "timestamp": time.time(),
    }


def detect_code_anomalies(directory: str = None) -> list[dict]:
    """Detecta patrones sospechosos en código."""
    d = Path(directory or str(_BASE / "core"))
    anomalies = []
    suspicious_patterns = [
        ("exec\\s*\\(", "posible exec dinámico"),
        ("eval\\s*\\(", "posible eval dinámico"),
        ("__import__\\s*\\(", "import dinámico"),
        ("subprocess\\.call.*shell=True", "shell=True en subprocess"),
        ("password\\s*=\\s*[\"']", "posible password hardcodeada"),
        ("api[_-]?key\\s*=\\s*[\"']", "posible API key hardcodeada"),
        ("rm\\s+-rf", "rm -rf detectado"),
    ]

    if not d.exists():
        return anomalies

    for f in d.rglob("*.py"):
        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
            lines = content.split("\n")
            for i, line in enumerate(lines):
                for pattern, desc in suspicious_patterns:
                    import re
                    if re.search(pattern, line, re.IGNORECASE):
                        anomalies.append({
                            "file": str(f.relative_to(_BASE)),
                            "line": i + 1,
                            "pattern": desc,
                            "code": line.strip()[:100],
                        })
        except Exception:
            continue

    return anomalies


def detect_log_anomalies(log_file: str) -> dict:
    """Detecta patrones inusuales en un archivo de log."""
    p = Path(log_file)
    if not p.exists():
        return {"error": "Log file not found"}

    try:
        content = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return {"error": "Cannot read log file"}

    lines = content.split("\n")
    error_lines = [l for l in lines if "error" in l.lower() or "exception" in l.lower()]
    warning_lines = [l for l in lines if "warning" in l.lower() or "warn" in l.lower()]

    # Agrupar errores por tipo
    error_types = defaultdict(int)
    for line in error_lines:
        # Extraer tipo de error (primera parte significativa)
        parts = line.split()
        if len(parts) > 2:
            error_type = " ".join(parts[2:4])[:50]
            error_types[error_type] += 1

    return {
        "total_lines": len(lines),
        "error_count": len(error_lines),
        "warning_count": len(warning_lines),
        "error_ratio": round(len(error_lines) / max(1, len(lines)) * 100, 2),
        "top_errors": dict(sorted(error_types.items(), key=lambda x: x[1], reverse=True)[:5]),
    }


def get_file_size_anomalies(threshold_mb: float = 5.0) -> list[dict]:
    """Archivos inusualmente grandes."""
    anomalies = []
    for f in _BASE.rglob("*"):
        if f.is_file() and f.suffix in (".py", ".json", ".txt", ".md", ".log"):
            try:
                size_mb = f.stat().st_size / (1024 * 1024)
                if size_mb > threshold_mb:
                    anomalies.append({
                        "file": str(f.relative_to(_BASE)),
                        "size_mb": round(size_mb, 2),
                    })
            except Exception:
                continue
    anomalies.sort(key=lambda x: x["size_mb"], reverse=True)
    return anomalies[:10]


def format_anomalies(anomalies: list[dict]) -> str:
    """Formatea anomalías para mostrar."""
    if not anomalies:
        return "Sin anomalías detectadas"
    lines = ["%d anomalía(s) detectada(s):" % len(anomalies)]
    for a in anomalies[:10]:
        lines.append("  [%s] %s" % (a.get("type", "?"), a.get("file", "")[:60]))
        if a.get("pattern"):
            lines.append("    ⚠ %s" % a["pattern"])
    return "\n".join(lines)
