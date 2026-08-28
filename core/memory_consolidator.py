"""
core/memory_consolidator.py — Auto-consolidate and prune memories for ERIS.
Actions:
  consolidate — Merge similar memories, remove stale entries older than N days
  summary     — Show memory stats (count by category, total size, oldest/newest)
  prune       — Remove memories older than N days
  search      — Search across all memory files
  backup      — Backup memories before consolidation

Storage: D:/Eris_Source/data/memory/ (JSON memory files)
"""
from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from pathlib import Path

_BASE_DIR = Path(__file__).resolve().parent.parent
_MEMORY_DIR = _BASE_DIR / "data" / "memory"
_BACKUP_DIR = _BASE_DIR / "data" / "memory" / "_backups"


def _ensure_dirs():
    _MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    _BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def _load_memory_files() -> dict[str, list]:
    """Load all JSON memory files into a dict of filename -> list of entries."""
    _ensure_dirs()
    result: dict[str, list] = {}
    for f in sorted(_MEMORY_DIR.glob("*.json")):
        if f.parent == _BACKUP_DIR:
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if isinstance(data, list):
                result[f.name] = data
            elif isinstance(data, dict):
                entries = data.get("memories", data.get("entries", data.get("data", [])))
                if isinstance(entries, list):
                    result[f.name] = entries
                else:
                    result[f.name] = [data]
            else:
                result[f.name] = []
        except Exception:
            result[f.name] = []
    return result


def _save_memory_file(filename: str, entries: list) -> None:
    path = _MEMORY_DIR / filename
    path.write_text(
        json.dumps(entries, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )


def _entry_age_days(entry: dict) -> float | None:
    """Calculate age of an entry in days from its timestamp."""
    ts = entry.get("timestamp", entry.get("date", entry.get("created", entry.get("time", ""))))
    if not ts:
        return None
    try:
        if isinstance(ts, (int, float)):
            dt = datetime.fromtimestamp(ts)
        else:
            for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y %H:%M"):
                try:
                    dt = datetime.strptime(str(ts)[:19], fmt)
                    break
                except ValueError:
                    continue
            else:
                return None
        return (datetime.now() - dt).total_seconds() / 86400
    except Exception:
        return None


def _entry_text(entry: dict) -> str:
    """Extract text content from a memory entry."""
    for key in ("content", "text", "memory", "message", "summary", "description"):
        val = entry.get(key, "")
        if val:
            return str(val)
    return json.dumps(entry, ensure_ascii=False)[:200]


def _similarity(a: str, b: str) -> float:
    """Calculate text similarity ratio between two strings."""
    if not a or not b:
        return 0.0
    a_lower = a.lower().strip()
    b_lower = b.lower().strip()
    if a_lower == b_lower:
        return 1.0
    return SequenceMatcher(None, a_lower, b_lower).ratio()


def memory_consolidator(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = str(params.get("action", "summary")).strip().lower()

    if player:
        try:
            player.write_log(f"[MemoryConsolidator] action={action}")
        except Exception:
            pass

    _ensure_dirs()

    if action == "consolidate":
        return _consolidate(params)
    elif action == "summary":
        return _summary()
    elif action == "prune":
        return _prune(params)
    elif action == "search":
        return _search(params)
    elif action == "backup":
        return _backup()
    return "Actions: consolidate, summary, prune, search, backup"


def _consolidate(params: dict) -> str:
    """Read all memories, merge similar entries, remove stale ones."""
    days = int(params.get("days", 30))
    similarity_threshold = float(params.get("threshold", 0.75))

    files = _load_memory_files()
    if not files:
        return "No hay archivos de memoria para consolidar."

    total_before = sum(len(v) for v in files.values())
    total_removed_stale = 0
    total_merged = 0
    messages = []

    for filename, entries in files.items():
        if not entries:
            continue

        # Step 1: Remove stale entries
        fresh = []
        stale = 0
        for entry in entries:
            age = _entry_age_days(entry)
            if age is not None and age > days:
                stale += 1
            else:
                fresh.append(entry)
        total_removed_stale += stale

        # Step 2: Merge duplicates / similar entries
        if len(fresh) <= 1:
            if stale > 0:
                _save_memory_file(filename, fresh)
            continue

        merged = []
        skip_indices = set()
        file_merges = 0

        for i in range(len(fresh)):
            if i in skip_indices:
                continue
            current = fresh[i]
            current_text = _entry_text(current)
            group = [current]

            for j in range(i + 1, len(fresh)):
                if j in skip_indices:
                    continue
                other_text = _entry_text(fresh[j])
                sim = _similarity(current_text, other_text)
                if sim >= similarity_threshold:
                    group.append(fresh[j])
                    skip_indices.add(j)

            if len(group) > 1:
                # Merge: keep the newest, combine tags/categories
                merged_entry = _merge_entries(group)
                merged.append(merged_entry)
                file_merges += 1
            else:
                merged.append(current)

            skip_indices.add(i)

        total_merged += file_merges
        if stale > 0 or file_merges > 0:
            _save_memory_file(filename, merged)

    total_after = sum(len(v) for v in _load_memory_files().values())

    lines = [
        f"Consolidación completada:",
        f"  Archivos procesados: {len(files)}",
        f"  Entradas iniciales: {total_before}",
        f"  Entradas finales: {total_after}",
        f"  Stales eliminadas (> {days} días): {total_removed_stale}",
        f"  Duplicadas fusionadas: {total_merged}",
    ]

    if total_removed_stale == 0 and total_merged == 0:
        lines.append("\nNo se encontraron entradas para limpiar. Todo está al día.")

    return "\n".join(lines)


def _merge_entries(group: list[dict]) -> dict:
    """Merge a group of similar entries into one, keeping the best data."""
    # Sort by timestamp (newest first)
    dated = []
    undated = []
    for e in group:
        age = _entry_age_days(e)
        if age is not None:
            dated.append((age, e))
        else:
            undated.append(e)
    dated.sort(key=lambda x: x[0])

    newest = dated[0][1] if dated else (group[0] if group else {})

    merged = dict(newest)

    # Combine text content
    all_texts = [_entry_text(e) for e in group]
    unique_texts = list(dict.fromkeys(t for t in all_texts if t))
    if len(unique_texts) > 1:
        merged["content"] = unique_texts[0]
        merged["merged_from"] = len(group)

    # Combine tags/categories
    all_tags = set()
    for e in group:
        for key in ("tags", "categories", "category", "type"):
            val = e.get(key)
            if isinstance(val, list):
                all_tags.update(val)
            elif isinstance(val, str) and val:
                all_tags.add(val)
    if all_tags:
        merged["tags"] = sorted(all_tags)

    return merged


def _summary() -> str:
    """Show memory stats."""
    files = _load_memory_files()
    if not files:
        return "No hay archivos de memoria."

    total_entries = sum(len(v) for v in files.values())
    total_size = sum(
        f.stat().st_size for f in _MEMORY_DIR.glob("*.json")
        if f.parent != _BACKUP_DIR
    )

    categories: dict[str, int] = {}
    oldest_entry = None
    newest_entry = None
    oldest_age = 0.0
    newest_age = float("inf")

    for filename, entries in files.items():
        for entry in entries:
            # Count by category/type
            for key in ("type", "category", "tags"):
                val = entry.get(key)
                if isinstance(val, str) and val:
                    categories[val] = categories.get(val, 0) + 1
                elif isinstance(val, list):
                    for v in val:
                        categories[str(v)] = categories.get(str(v), 0) + 1

            age = _entry_age_days(entry)
            if age is not None:
                if age > oldest_age:
                    oldest_age = age
                    oldest_entry = entry
                if age < newest_age:
                    newest_age = age
                    newest_entry = entry

    size_str = f"{total_size / 1024:.1f} KB" if total_size < 1024 * 1024 else f"{total_size / (1024 * 1024):.1f} MB"

    lines = [
        f"Resumen de Memorias:",
        f"  Archivos: {len(files)}",
        f"  Total entradas: {total_entries}",
        f"  Tamaño total: {size_str}",
    ]

    if categories:
        lines.append(f"\n  Por categoría:")
        for cat, count in sorted(categories.items(), key=lambda x: -x[1])[:10]:
            lines.append(f"    {cat}: {count}")

    if oldest_entry:
        lines.append(f"\n  Más antigua: hace {oldest_age:.0f} días")
        lines.append(f"    {_entry_text(oldest_entry)[:80]}")

    if newest_entry and newest_age < float("inf"):
        lines.append(f"\n  Más reciente: hace {newest_age:.1f} días")
        lines.append(f"    {_entry_text(newest_entry)[:80]}")

    return "\n".join(lines)


def _prune(params: dict) -> str:
    """Remove memories older than N days."""
    days = int(params.get("days", 30))
    files = _load_memory_files()
    if not files:
        return "No hay archivos de memoria."

    total_removed = 0
    files_modified = 0

    for filename, entries in files.items():
        if not entries:
            continue
        fresh = []
        removed = 0
        for entry in entries:
            age = _entry_age_days(entry)
            if age is not None and age > days:
                removed += 1
            else:
                fresh.append(entry)

        if removed > 0:
            _save_memory_file(filename, fresh)
            total_removed += removed
            files_modified += 1

    if total_removed == 0:
        return f"No se encontraron entradas mayores a {days} días."

    return f"Prune completado: {total_removed} entradas eliminadas de {files_modified} archivos (>{days} días)."


def _search(params: dict) -> str:
    """Search across all memory files."""
    query = str(params.get("query", "")).strip()
    if not query:
        return "Falta el parámetro 'query' para buscar."

    files = _load_memory_files()
    if not files:
        return "No hay archivos de memoria."

    query_lower = query.lower()
    results = []

    for filename, entries in files.items():
        for i, entry in enumerate(entries):
            text = _entry_text(entry)
            if query_lower in text.lower():
                age = _entry_age_days(entry)
                age_str = f"hace {age:.0f}d" if age is not None else "?"
                category = entry.get("category", entry.get("type", ""))
                cat_str = f" [{category}]" if category else ""
                results.append(
                    f"  [{filename}:{i}]{cat_str} ({age_str}) {text[:100]}"
                )
                if len(results) >= 20:
                    break
        if len(results) >= 20:
            break

    if not results:
        return f"No encontré nada para '{query}' en las memorias."

    return f"Resultados para '{query}' ({len(results)}):\n" + "\n".join(results)


def _backup() -> str:
    """Backup all memory files before consolidation."""
    _ensure_dirs()
    files = list(_MEMORY_DIR.glob("*.json"))
    files = [f for f in files if f.parent != _BACKUP_DIR]

    if not files:
        return "No hay archivos de memoria para respaldar."

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_subdir = _BACKUP_DIR / timestamp
    backup_subdir.mkdir(parents=True, exist_ok=True)

    copied = 0
    for f in files:
        try:
            shutil.copy2(str(f), str(backup_subdir / f.name))
            copied += 1
        except Exception:
            pass

    # Keep only last 10 backups
    backups = sorted(_BACKUP_DIR.iterdir())
    while len(backups) > 10:
        oldest = backups.pop(0)
        if oldest.is_dir():
            shutil.rmtree(str(oldest), ignore_errors=True)

    total_size = sum(f.stat().st_size for f in backup_subdir.glob("*.json"))
    size_str = f"{total_size / 1024:.1f} KB"

    return f"Backup creado: {copied} archivos ({size_str}) en {backup_subdir.name}"
