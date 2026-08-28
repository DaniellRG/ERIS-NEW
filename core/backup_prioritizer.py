"""
backup_prioritizer.py — Priorización inteligente de respaldos.

En vez de respaldar todo (lento y costoso), prioriza por:
  - Criticidad del archivo (config > logs)
  - Frecuencia de cambio
  - Última vez que se respaldó
  - Tamaño del archivo
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_BACKUP_STATE_FILE = _BASE / "data" / "backup_state.json"

# Prioridades por tipo de archivo
FILE_PRIORITY = {
    # Críticos (respaldar primero)
    ".json": 1, ".yaml": 1, ".yml": 1, ".toml": 1, ".env": 1, ".key": 1,
    ".pem": 1, ".cfg": 1, ".ini": 1,

    # Código fuente
    ".py": 2, ".js": 2, ".ts": 2, ".html": 2, ".css": 2,
    ".jsx": 2, ".tsx": 2, ".vue": 2, ".svelte": 2,

    # Documentos
    ".md": 3, ".txt": 3, ".pdf": 3, ".docx": 3,

    # Datos
    ".csv": 3, ".db": 3, ".sqlite": 3,

    # Baja prioridad
    ".log": 4, ".tmp": 5, ".cache": 5, ".pyc": 5,
}

# Patrones de directorios críticos
CRITICAL_DIRS = {
    "config": 1,
    "memory": 1,
    "vault": 2,
    "core": 2,
    "skills": 2,
    "actions": 3,
    "data": 3,
    "tests": 3,
}


def _load_state() -> dict:
    try:
        if _BACKUP_STATE_FILE.exists():
            return json.loads(_BACKUP_STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"backed_up": {}, "last_full_backup": 0}


def _save_state(state: dict):
    try:
        _BACKUP_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _BACKUP_STATE_FILE.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def get_file_priority(filepath: str) -> int:
    """Calcula prioridad de un archivo (1=crítico, 5=baja)."""
    path = Path(filepath)
    ext = path.suffix.lower()
    ext_priority = FILE_PRIORITY.get(ext, 3)

    # Ajustar por directorio
    dir_priority = 3
    for dir_name, pri in CRITICAL_DIRS.items():
        if dir_name in str(path).lower():
            dir_priority = min(dir_priority, pri) if dir_priority is not None else pri

    return min(ext_priority, dir_priority)


def prioritize_files(
    directory: str,
    max_files: int = 50,
    force: bool = False,
) -> list[dict]:
    """Prioriza archivos para respaldo.

    Args:
        directory: Directorio a analizar
        max_files: Máximo de archivos a respaldar
        force: Forzar respaldo aunque esté reciente

    Returns:
        Lista de [{path, priority, size, last_modified, needs_backup, reason}]
    """
    state = _load_state()
    dir_path = Path(directory)
    if not dir_path.exists():
        return []

    files = []
    for f in dir_path.rglob("*"):
        if not f.is_file():
            continue
        fp = str(f.resolve())
        stat = f.stat()
        ext = f.suffix.lower()

        # Calcular prioridad
        priority = get_file_priority(fp)

        # Verificar si necesita backup
        last_backup = state.get("backed_up", {}).get(fp, 0)
        last_modified = stat.st_mtime
        needs = force or last_modified > last_backup

        reason = ""
        if needs:
            if last_backup == 0:
                reason = "nunca respaldado"
            elif last_modified > last_backup:
                reason = "modificado después del último backup"

        # Saltar archivos muy grandes (>50MB)
        if stat.st_size > 50 * 1024 * 1024:
            continue

        files.append({
            "path": fp,
            "name": f.name,
            "priority": priority,
            "size": stat.st_size,
            "last_modified": last_modified,
            "last_backup": last_backup,
            "needs_backup": needs,
            "reason": reason,
        })

    # Ordenar: prioridad (menor = mejor), luego por necesidad
    files.sort(key=lambda x: (0 if x["needs_backup"] else 1, x["priority"], -x["size"]))
    return files[:max_files]


def mark_backed_up(filepath: str):
    """Marca un archivo como respaldado."""
    state = _load_state()
    fp = str(Path(filepath).resolve())
    state.setdefault("backed_up", {})[fp] = time.time()
    _save_state(state)


def get_backup_stats() -> dict:
    """Estadísticas de respaldo."""
    state = _load_state()
    backed = state.get("backed_up", {})
    total = len(backed)
    recent = sum(1 for t in backed.values() if time.time() - t < 86400)

    return {
        "total_backed_up": total,
        "backed_up_last_24h": recent,
        "last_full_backup": state.get("last_full_backup", 0),
    }
