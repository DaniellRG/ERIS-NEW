"""
smart_file_organizer.py — Organizador inteligente de archivos.

Analiza patrones de uso y sugiere/agrupa archivos relacionados:
  - Archivos que se abren juntos frecuentemente
  - Archivos del mismo proyecto/tema
  - Archivos huérfanos (sin relación conocida)
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from collections import defaultdict

_BASE = Path(__file__).resolve().parent.parent
_USAGE_FILE = _BASE / "data" / "file_usage_patterns.json"


def _load_usage() -> dict:
    try:
        if _USAGE_FILE.exists():
            return json.loads(_USAGE_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"co_access": {}, "last_access": {}, "access_count": {}}


def _save_usage(data: dict):
    try:
        _USAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _USAGE_FILE.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def record_file_access(filepath: str):
    """Registra que un archivo fue accedido."""
    usage = _load_usage()
    filepath = str(Path(filepath).resolve())

    # Incrementar contador
    count = usage.get("access_count", {})
    count[filepath] = count.get(filepath, 0) + 1
    usage["access_count"] = count

    # Registrar timestamp
    last = usage.get("last_access", {})
    last[filepath] = time.time()
    usage["last_access"] = last

    _save_usage(usage)


def record_co_access(file1: str, file2: str):
    """Registra que dos archivos fueron accedidos juntos."""
    usage = _load_usage()
    co = usage.get("co_access", {})

    key1 = "%s|%s" % (file1, file2)
    key2 = "%s|%s" % (file2, file1)

    co[key1] = co.get(key1, 0) + 1
    co[key2] = co.get(key2, 0) + 1
    usage["co_access"] = co

    _save_usage(usage)


def suggest_related_files(filepath: str, top_n: int = 5) -> list[dict]:
    """Sugiere archivos relacionados con uno dado.

    Returns:
        Lista de [{path, score, reason}]
    """
    usage = _load_usage()
    co = usage.get("co_access", {})
    count = usage.get("access_count", {})

    related = {}
    filepath = str(Path(filepath).resolve())

    # Buscar co-access
    for key, freq in co.items():
        if filepath in key:
            other = key.replace(filepath, "").replace("|", "")
            if other and other != filepath:
                if other not in related:
                    related[other] = {"score": 0, "reasons": []}
                related[other]["score"] += freq
                related[other]["reasons"].append("co-accedido %d veces" % freq)

    # Buscar por directorio
    parent = str(Path(filepath).parent)
    for f in count:
        if str(Path(f).parent) == parent and f != filepath:
            if f not in related:
                related[f] = {"score": 0, "reasons": []}
            related[f]["score"] += 1
            related[f]["reasons"].append("mismo directorio")

    # Ordenar por score
    sorted_related = sorted(related.items(), key=lambda x: x[1]["score"], reverse=True)
    return [
        {"path": path, "score": info["score"], "reason": "; ".join(info["reasons"])}
        for path, info in sorted_related[:top_n]
    ]


def find_orphan_files(directory: str, min_age_days: int = 30) -> list[dict]:
    """Encuentra archivos que no se han accedido en mucho tiempo."""
    usage = _load_usage()
    last_access = usage.get("last_access", {})
    count = usage.get("access_count", {})
    cutoff = time.time() - (min_age_days * 86400)

    orphans = []
    dir_path = Path(directory)
    if not dir_path.exists():
        return []

    for f in dir_path.rglob("*"):
        if f.is_file():
            fp = str(f.resolve())
            last = last_access.get(fp, 0)
            accesses = count.get(fp, 0)
            if last < cutoff and accesses < 3:
                age_days = (time.time() - last) / 86400 if last > 0 else 999
                orphans.append({
                    "path": fp,
                    "name": f.name,
                    "age_days": int(age_days),
                    "accesses": accesses,
                })

    orphans.sort(key=lambda x: x["age_days"], reverse=True)
    return orphans[:20]


def get_usage_stats() -> dict:
    """Estadísticas de uso de archivos."""
    usage = _load_usage()
    count = usage.get("access_count", {})
    last = usage.get("last_access", {})

    total = len(count)
    total_accesses = sum(count.values())
    most_used = sorted(count.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "total_files_tracked": total,
        "total_accesses": total_accesses,
        "most_used": [{"path": p, "count": c} for p, c in most_used],
    }
