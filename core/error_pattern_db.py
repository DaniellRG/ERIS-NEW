"""
error_pattern_db.py — Base de datos de errores y soluciones.

Registra errores encontrados, cómo se resolvieron, y permite buscar
soluciones a errores similares en el futuro. Aprende de cada fix.

Flujo:
  1. Se produce un error → se registra
  2. Se intenta solución → se registra resultado
  3. Próxima vez que aparezca error similar → sugerir la solución conocida
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_DB_FILE = _BASE / "data" / "error_patterns.json"


def _load_db() -> dict:
    try:
        if _DB_FILE.exists():
            return json.loads(_DB_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"errors": [], "solutions": {}, "stats": {"total": 0, "resolved": 0}}


def _save_db(db: dict):
    try:
        _DB_FILE.parent.mkdir(parents=True, exist_ok=True)
        _DB_FILE.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def _extract_signature(error_text: str) -> str:
    """Extrae una firma del error para matching (ignora números, paths específicos)."""
    sig = error_text.lower()
    # Reemplazar paths
    sig = re.sub(r"[a-z]:\\[^\s]+", "<PATH>", sig)
    sig = re.sub(r"/[^\s]+", "<PATH>", sig)
    # Reemplazar números
    sig = re.sub(r"\d+", "<N>", sig)
    # Reemplazar strings entre comillas
    sig = re.sub(r'"[^"]*"', "<STR>", sig)
    sig = re.sub(r"'[^']*'", "<STR>", sig)
    # Normalizar espacios
    sig = re.sub(r"\s+", " ", sig).strip()
    return sig[:300]


def record_error(error_text: str, tool: str = "", context: str = "") -> dict:
    """Registra un error nuevo.

    Returns:
        dict con: id, signature, similar_found, similar_solution
    """
    db = _load_db()
    sig = _extract_signature(error_text)

    # Buscar errores similares
    similar = None
    for entry in db["errors"]:
        if entry.get("signature") == sig:
            similar = entry
            break

    if similar:
        # Error ya conocido
        similar["occurrences"] = similar.get("occurrences", 1) + 1
        similar["last_seen"] = time.time()
        solution = db["solutions"].get(similar["id"], {})
        _save_db(db)
        return {
            "id": similar["id"],
            "signature": sig,
            "similar_found": True,
            "occurrences": similar["occurrences"],
            "previous_solution": solution.get("description", ""),
            "solution_steps": solution.get("steps", []),
        }

    # Error nuevo
    error_id = "err_%d" % int(time.time() * 1000)
    entry = {
        "id": error_id,
        "text": error_text[:500],
        "signature": sig,
        "tool": tool,
        "context": context[:200],
        "occurrences": 1,
        "first_seen": time.time(),
        "last_seen": time.time(),
        "resolved": False,
    }
    db["errors"].append(entry)
    db["stats"]["total"] = db["stats"].get("total", 0) + 1

    # Mantener solo últimos 500 errores
    if len(db["errors"]) > 500:
        db["errors"] = db["errors"][-500:]

    _save_db(db)

    return {
        "id": error_id,
        "signature": sig,
        "similar_found": False,
        "occurrences": 1,
        "previous_solution": "",
        "solution_steps": [],
    }


def record_solution(error_id: str, description: str, steps: list[str] = None, success: bool = True):
    """Registra la solución aplicada a un error."""
    db = _load_db()

    db["solutions"][error_id] = {
        "description": description,
        "steps": steps or [],
        "success": success,
        "timestamp": time.time(),
    }

    # Marcar error como resuelto
    for entry in db["errors"]:
        if entry["id"] == error_id:
            entry["resolved"] = success
            break

    db["stats"]["resolved"] = db["stats"].get("resolved", 0) + (1 if success else 0)
    _save_db(db)


def find_solution(error_text: str) -> dict | None:
    """Busca una solución conocida para un error dado."""
    db = _load_db()
    sig = _extract_signature(error_text)

    for entry in db["errors"]:
        if entry.get("signature") == sig and entry.get("resolved"):
            solution = db["solutions"].get(entry["id"], {})
            if solution:
                return {
                    "error_id": entry["id"],
                    "error_text": entry["text"][:200],
                    "solution": solution.get("description", ""),
                    "steps": solution.get("steps", []),
                    "occurrences": entry.get("occurrences", 1),
                    "resolved_at": solution.get("timestamp", 0),
                }
    return None


def get_error_stats() -> dict:
    """Estadísticas de errores."""
    db = _load_db()
    errors = db.get("errors", [])
    total = len(errors)
    resolved = sum(1 for e in errors if e.get("resolved"))
    unresolved = total - resolved

    # Tool con más errores
    tool_errors = {}
    for e in errors:
        t = e.get("tool", "unknown")
        tool_errors[t] = tool_errors.get(t, 0) + 1

    return {
        "total_errors": total,
        "resolved": resolved,
        "unresolved": unresolved,
        "resolution_rate": round(resolved / total * 100, 1) if total > 0 else 0,
        "errors_by_tool": dict(sorted(tool_errors.items(), key=lambda x: -x[1])[:5]),
    }


def format_error_db() -> str:
    """Formatea la base de errores para mostrar."""
    db = _load_db()
    errors = db.get("errors", [])
    if not errors:
        return "Base de errores vacía."

    lines = ["Base de datos de errores (%d total):" % len(errors)]
    for e in errors[-10:]:  # Últimos 10
        status = "✓" if e.get("resolved") else "✗"
        text = e.get("text", "")[:80]
        lines.append("  %s [%s] %s (x%d)" % (status, e.get("id", "")[:12], text, e.get("occurrences", 1)))

    return "\n".join(lines)
