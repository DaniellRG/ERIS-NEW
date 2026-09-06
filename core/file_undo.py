"""
core/file_undo.py — UNDO a nivel de archivo (patrón /undo de opencode).

Cada tool que modifica archivos pasa primero por snapshot() en el dispatcher:
se copia el estado previo de los archivos objetivo a memory/undo_backups/ y se
registra en memory/file_undo.json (anillo de las últimas 30 operaciones).

La tool `undo` restaura el snapshot más reciente (o uno indicado por índice),
como el /undo de opencode. Admite la misma firma que el resto de las tools:
    tool_undo(parameters={"action": "undo"|"underso"|"list"|"stats"}, player=...)

- undo      : restaura el último snapshot registrado
- undo_n=K  : restaura el snapshot K (1 = más reciente)
- list      : muestra el historial de operaciones con snapshots (n=cuántas)
- stats     : resumen (total snapshots, archivos respaldados, uso en disco)

Si el archivo no existía antes (creación), el restore lo ELIMINA.
Entre acciones, "/undo" puede invocarse también desde código con snapshot().
"""
from __future__ import annotations

import json
import shutil
import time
import traceback
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_BACKUP_DIR = _BASE / "memory" / "undo_backups"
_UNDO_LOG = _BASE / "memory" / "file_undo.json"
_MAX_ENTRIES = 30
_TIMEOUT = time.strftime("%Y%m%d_%H%M%S")
_BACKUP_DIR.mkdir(parents=True, exist_ok=True)

# Mapa name -> {acción o None(no discrimina): (clave del path, es_relativo_proyecto)}
_MODIFY_MAP = {
    "file_editor": {"write": ("path", False), "edit": ("path", False)},
    "file_controller": {
        "write": ("path", False),
        "append": ("path", False),
        "create_file": ("path", False),
        "delete": ("path", False),
    },
    "file_api": {"write": ("path", False), "delete": ("path", False)},
    "ast_edit": {None: ("file", False)},
    "self_edit": {
        "edit_file": ("file", True),
        "append_file": ("file", True),
        "create_file": ("file", True),
    },
    "self_modify": {
        "modify": ("file", True),
        "add_function": ("file", True),
        "add_import": ("file", True),
    },
}


def _resolve(raw, relative_to_project: bool = False) -> Path | None:
    """Resuelve la ruta absoluta. Para self_edit/self_modify, relativa al proyecto."""
    if not raw or not isinstance(raw, str):
        return None
    p = Path(raw.strip())
    if not p.is_absolute():
        p = _BASE / p
    return p


def _targets(name: str, args: dict) -> list[Path]:
    """Devuelve los archivos objetivo de una llamada, o [] si no modifica archivos."""
    actions = _MODIFY_MAP.get(name)
    if not actions or not isinstance(args, dict):
        return []
    action = args.get("action")
    spec = actions.get(action)
    if spec is None and len(actions) == 1 and None in actions:
        spec = actions[None]
        action = None
    if not spec:
        return []
    key, rel = spec
    candidates = [args.get(key)]
    if rel and action == "edit_file":
        candidates.append(args.get("file"))
    out = []
    for c in candidates:
        resolved = _resolve(c, rel)
        if resolved is not None:
            out.append(resolved)
    return out


def _load_log() -> list:
    try:
        if _UNDO_LOG.exists():
            data = json.loads(_UNDO_LOG.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
    except Exception:
        pass
    return []


def _save_log(entries: list):
    try:
        _UNDO_LOG.write_text(json.dumps(entries[-_MAX_ENTRIES:], indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def snapshot(name: str, args: dict) -> list[dict]:
    """Copia el estado previo de los archivos que `name` va a modificar.
    Devuelve los registros creados (vacío si nada que respaldar)."""
    if not isinstance(args, dict):
        return []
    t0 = time.time()
    try:
        targets = _targets(name, args)
        if not targets:
            return []
        created = []
        for path in targets:
            try:
                resolved = path
                existed = resolved.exists()
                content = None
                backup = None
                if existed and resolved.is_file():
                    # Evita respaldar dos veces la misma ruta en la misma llamada
                    if created and any(c.get("path") == str(resolved) for c in created):
                        continue
                    backup = _BACKUP_DIR / "{}_{}_{}.bak".format(_TIMEOUT, len(created), resolved.name)
                    shutil.copy2(resolved, backup)
                    content = None  # contenido en el backup, no en el json
                created.append({
                    "tool": name,
                    "action": args.get("action"),
                    "path": str(resolved),
                    "existed": existed,
                    "backup": str(backup) if backup else None,
                    "time": time.strftime("%Y-%m-%d %H:%M:%S"),
                })
            except Exception:
                traceback.print_exc()
        if created:
            log = _load_log()
            log.extend(created)
            _save_log(log)
        return created
    except Exception:
        traceback.print_exc()
        return []


def _restore_entry(entry: dict) -> str:
    path = Path(entry.get("path") or "")
    backup = entry.get("backup")
    if entry.get("existed") and backup:
        bp = Path(backup)
        if not bp.exists():
            return "No encuentro el backup de '{}'. Ya fue restaurado o se movió.".format(entry.get("path"))
        if not path.parent.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(bp, path)
        return "Restaurado {} desde su snapshot previo.".format(entry.get("path"))
    # No existía antes → restaurar = eliminar lo que se haya creado
    if path.exists():
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        else:
            path.unlink(missing_ok=True)
        return "Eliminado {} (antes de esa operación no existía).".format(entry.get("path"))
    return "Nada que hacer: '{}' no existe ahora y tampoco antes.".format(entry.get("path"))


def tool_undo(parameters=None, player=None) -> str:
    """Tool `undo` — restaura el snapshot más reciente (o el indicado)."""
    params = parameters or {}
    action = (params.get("action") or "undo").strip().lower()
    log = _load_log()

    if action == "list":
        n = int(params.get("n") or 10)
        if not log:
            return "No hay snapshots de undo."
        lines = []
        for i in range(min(n, len(log))):
            e = log[-(i + 1)]
            lines.append("#{}  {} · {} · {} [{}]".format(
                i + 1, e.get("tool"), e.get("action") or "-",
                e.get("path"), "existía" if e.get("existed") else "nuevo"
            ))
        return "Historial de undo (#1 = más reciente):\n" + "\n".join(lines)

    if action == "stats":
        total = len(log)
        backed = [e for e in log if e.get("existed")]
        size = sum(p.stat().st_size for p in _BACKUP_DIR.iterdir()) if _BACKUP_DIR.exists() else 0
        return "Undo: {} snapshots ({} con backup), {} en disco, máx {}.".format(
            total, len(backed), _human(size), _MAX_ENTRIES)

    if action in ("undo", "restore"):
        n = int(params.get("n") or 1)
        if n < 1:
            n = 1
        if not log:
            return "No hay nada que deshacer."
        idx = len(log) - n
        if idx < 0:
            return "Solo hay {} snapshots. Usá el más reciente.".format(len(log))
        entry = log[idx]
        try:
            result = _restore_entry(entry)
            del log[idx]
            _save_log(log)
            return "Undo aplicado: {}\n(Tool {})".format(result, entry.get("tool"))
        except Exception as e:
            return "No pude restaurar {}: {}".format(entry.get("path"), e)

    return "Acción válida de undo: undo, undo_n, list, stats."


def _human(size: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return "{:.1f} {}".format(size, unit)
        size /= 1024
    return "{:.1f} TB".format(size)