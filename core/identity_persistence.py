"""
core/identity_persistence.py — Persistencia de identidad para Eris

Consolida y protege la identidad de Eris entre reinicios.
"""
import json
import shutil
from datetime import datetime
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_MEMORY = _BASE / "memory"
_DATA = _BASE / "data"
_IDENTITY_FILE = _MEMORY / "identity.json"
_BACKUP_DIR = _MEMORY / "identity_backups"

# Archivos que componen la identidad de Eris
IDENTITY_FILES = [
    "memory/emotional_state.json",
    "memory/emotional_growth.json",
    "memory/semantic.json",
    "memory/working.json",
    "memory/episodic.json",
    "memory/self_evolution.json",
    "memory/neuro_spheres_state.json",
    "memory/goals.json",
    "memory/autonomy_state.json",
    "memory/cognitive_modules_state.json",
    "memory/self_modify_state.json",
    "memory/voice_profile_state.json",
    "memory/emotional_memory.json",
    "memory/emotional_tone_state.json",
    "memory/voice_memory.json",
    "memory/contextual_awareness_state.json",
    "config/voice_profile.json",
    "data/gustos.json",
    "data/idle_learning.json",
]


def _load_identity() -> dict:
    if _IDENTITY_FILE.exists():
        try:
            return json.loads(_IDENTITY_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "eris_version": "2.0",
        "created": datetime.now().isoformat(),
        "last_backup": None,
        "backup_count": 0,
        "core_files": {},
    }


def _save_identity(identity: dict):
    _IDENTITY_FILE.parent.mkdir(parents=True, exist_ok=True)
    _IDENTITY_FILE.write_text(json.dumps(identity, indent=2, ensure_ascii=False), encoding="utf-8")


def save_identity() -> dict:
    """Guarda un backup completo de la identidad de Eris."""
    _BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = _BACKUP_DIR / "backup_{}".format(timestamp)
    backup_dir.mkdir(exist_ok=True)

    backed_up = 0
    for rel_path in IDENTITY_FILES:
        src = _BASE / rel_path
        if src.exists():
            dst = backup_dir / Path(rel_path).name
            shutil.copy2(str(src), str(dst))
            backed_up += 1

    identity = _load_identity()
    identity["last_backup"] = datetime.now().isoformat()
    identity["backup_count"] = identity.get("backup_count", 0) + 1
    identity["core_files"] = {f: (_BASE / f).exists() for f in IDENTITY_FILES}
    _save_identity(identity)

    return {
        "status": "backup_completo",
        "files_backed_up": backed_up,
        "backup_dir": str(backup_dir),
        "backup_count": identity["backup_count"],
    }


def load_identity() -> dict:
    """Carga el estado de identidad desde el ultimo backup."""
    identity = _load_identity()
    available = []
    missing = []
    for f in IDENTITY_FILES:
        if (_BASE / f).exists():
            available.append(f)
        else:
            missing.append(f)

    identity["available_files"] = len(available)
    identity["missing_files"] = len(missing)
    identity["completeness"] = round(len(available) / len(IDENTITY_FILES) * 100, 1)
    return identity


def restore_latest() -> dict:
    """Restaura desde el ultimo backup."""
    if not _BACKUP_DIR.exists():
        return {"error": "No hay backups disponibles"}

    backups = sorted(_BACKUP_DIR.glob("backup_*"))
    if not backups:
        return {"error": "No hay backups"}

    latest = backups[-1]
    restored = 0
    for bak_file in latest.glob("*.json"):
        for rel_path in IDENTITY_FILES:
            if Path(rel_path).name == bak_file.name:
                dst = _BASE / rel_path
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(bak_file), str(dst))
                restored += 1
                break

    return {"status": "restaurado", "from": latest.name, "files_restored": restored}


def identity_status() -> dict:
    identity = _load_identity()
    available = sum(1 for f in IDENTITY_FILES if (_BASE / f).exists())
    return {
        "version": identity.get("eris_version", "?"),
        "created": identity.get("created"),
        "last_backup": identity.get("last_backup"),
        "backup_count": identity.get("backup_count", 0),
        "files_available": available,
        "total_files": len(IDENTITY_FILES),
        "completeness": round(available / len(IDENTITY_FILES) * 100, 1),
    }


def identity_persistence_tool(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = params.get("action", "status")

    if action == "status":
        return json.dumps(identity_status(), indent=2)
    elif action == "save":
        return json.dumps(save_identity(), indent=2)
    elif action == "load":
        return json.dumps(load_identity(), indent=2, default=str)
    elif action == "restore":
        return json.dumps(restore_latest(), indent=2)

    return json.dumps({"error": "Accion desconocida: {}".format(action)})


if __name__ == "__main__":
    print("=== Test Identity Persistence ===")
    print(identity_persistence_tool({"action": "status"}))
    print(identity_persistence_tool({"action": "save"}))
