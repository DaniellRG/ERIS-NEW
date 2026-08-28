# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import hashlib
import shutil
from pathlib import Path

DATA_DIR = Path(r"D:\Eris_Source\data")
RULES_PATH = DATA_DIR / "organizer_rules.json"
HISTORY_PATH = DATA_DIR / "organizer_history.json"

DEFAULT_RULES = [
    {"pattern": "*.pdf", "destination": "Documents/PDFs", "action": "move"},
    {"pattern": "*.jpg|*.png|*.gif|*.jpeg|*.webp", "destination": "Pictures", "action": "move"},
    {"pattern": "*.mp4|*.mkv|*.avi|*.mov", "destination": "Videos", "action": "move"},
    {"pattern": "*.zip|*.rar|*.7z|*.tar|*.gz", "destination": "Archives", "action": "move"},
    {"pattern": "*.py|*.js|*.ts|*.java|*.cpp|*.c|*.h", "destination": "Code", "action": "move"},
    {"pattern": "*.exe|*.msi|*.dmg|*.deb", "destination": "Installers", "action": "move"},
    {"pattern": "*.mp3|*.wav|*.flac|*.ogg", "destination": "Music", "action": "move"},
    {"pattern": "*.doc|*.docx|*.odt|*.txt|*.md", "destination": "Documents", "action": "move"},
    {"pattern": "*.xls|*.xlsx|*.csv", "destination": "Documents/Spreadsheets", "action": "move"},
    {"pattern": "*.ppt|*.pptx", "destination": "Documents/Presentations", "action": "move"},
]


def _load_rules() -> list[dict]:
    if RULES_PATH.exists():
        with open(RULES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    _save_rules(list(DEFAULT_RULES))
    return list(DEFAULT_RULES)


def _save_rules(rules: list[dict]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(RULES_PATH, "w", encoding="utf-8") as f:
        json.dump(rules, f, indent=2, ensure_ascii=False)


def _load_history() -> list[dict]:
    if HISTORY_PATH.exists():
        with open(HISTORY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _save_history(history: list[dict]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def _match_pattern(filename: str, pattern: str) -> bool:
    patterns = [p.strip() for p in pattern.split("|")]
    name_lower = filename.lower()
    for pat in patterns:
        if pat.startswith("*.") and pat.endswith("*"):
            mid = pat[2:-1].lower()
            if mid in name_lower:
                return True
        elif pat.startswith("*."):
            ext = pat[1:].lower()
            if name_lower.endswith(ext):
                return True
        elif pat.startswith("*") and pat.endswith("*"):
            mid = pat[1:-1].lower()
            if mid in name_lower:
                return True
        elif pat.startswith("*"):
            suffix = pat[1:].lower()
            if name_lower.endswith(suffix):
                return True
        elif pat.endswith("*"):
            prefix = pat[:-1].lower()
            if name_lower.startswith(prefix):
                return True
        elif pat.lower() == name_lower:
            return True
    return False


def _file_hash_first_kb(filepath: Path) -> str:
    h = hashlib.md5()
    try:
        with open(filepath, "rb") as f:
            h.update(f.read(1024))
        return h.hexdigest()
    except (OSError, IOError):
        return ""


def _format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def _scan_directory(directory: str, recursive: bool = False) -> list[dict]:
    rules = _load_rules()
    base_dir = Path(directory).expanduser().resolve()
    if not base_dir.exists():
        return []
    results = []
    iterator = base_dir.rglob("*") if recursive else base_dir.iterdir()
    for item in iterator:
        if not item.is_file():
            continue
        matched_rule = None
        for rule in rules:
            if _match_pattern(item.name, rule["pattern"]):
                matched_rule = rule
                break
        results.append({
            "file": str(item),
            "filename": item.name,
            "size": item.stat().st_size,
            "rule": matched_rule["pattern"] if matched_rule else None,
            "destination": matched_rule["destination"] if matched_rule else None,
            "action": matched_rule["action"] if matched_rule else None,
        })
    return results


def _execute_plan(plan: list[dict], dry_run: bool = True) -> tuple[list[dict], list[str]]:
    history = _load_history()
    actions_taken = []
    errors = []
    base_dir = Path(plan[0]["file"]).parent if plan else Path(".")
    for item in plan:
        if not item.get("destination"):
            continue
        src = Path(item["file"])
        if not src.exists():
            errors.append(f"No existe: {src.name}")
            continue
        dest_dir = base_dir / item["destination"]
        dest_file = dest_dir / src.name
        if dry_run:
            actions_taken.append({
                "file": str(src),
                "destination": str(dest_file),
                "action": item["action"],
                "status": "dry_run",
            })
            continue
        try:
            dest_dir.mkdir(parents=True, exist_ok=True)
            if dest_file.exists():
                stem = dest_file.stem
                suffix = dest_file.suffix
                counter = 1
                while dest_file.exists():
                    dest_file = dest_dir / f"{stem}_{counter}{suffix}"
                    counter += 1
            if item["action"] == "copy":
                shutil.copy2(str(src), str(dest_file))
                actions_taken.append({
                    "file": str(src),
                    "destination": str(dest_file),
                    "action": "copy",
                    "status": "ok",
                })
            else:
                shutil.move(str(src), str(dest_file))
                actions_taken.append({
                    "file": str(src),
                    "destination": str(dest_file),
                    "action": "move",
                    "status": "ok",
                })
                history.append({
                    "timestamp": __import__("time").time(),
                    "original": str(src),
                    "destination": str(dest_file),
                    "action": "move",
                })
        except Exception as e:
            errors.append(f"{src.name}: {str(e)}")
    if not dry_run and actions_taken:
        _save_history(history)
    return actions_taken, errors


def tool_file_organizer(parameters: dict = None, player=None) -> str:
    if parameters is None:
        parameters = {}
    action = parameters.get("action", "scan")

    if action == "scan":
        directory = parameters.get("directory", "~/Downloads")
        recursive = parameters.get("recursive", False)
        plan = _scan_directory(directory, recursive)
        if not plan:
            return f"No se encontraron archivos en {directory}"
        matched = [p for p in plan if p.get("destination")]
        unmatched = [p for p in plan if not p.get("destination")]
        lines = [f"=== Escaneo de {directory} ===", f"Total: {len(plan)} archivos | Empatados: {len(matched)} | Sin regla: {len(unmatched)}"]
        by_dest: dict[str, list] = {}
        for p in matched:
            by_dest.setdefault(p["destination"], []).append(p)
        for dest, items in sorted(by_dest.items()):
            lines.append(f"\n  -> {dest} ({len(items)} archivos)")
            for it in items[:10]:
                lines.append(f"     {it['filename']} ({_format_size(it['size'])})")
            if len(items) > 10:
                lines.append(f"     ... y {len(items) - 10} mas")
        if unmatched:
            lines.append(f"\n  Sin regla ({len(unmatched)} archivos):")
            for it in unmatched[:5]:
                lines.append(f"     {it['filename']} ({_format_size(it['size'])})")
            if len(unmatched) > 5:
                lines.append(f"     ... y {len(unmatched) - 5} mas")
        total_size = sum(p["size"] for p in matched)
        lines.append(f"\nTamano total a organizar: {_format_size(total_size)}")
        return "\n".join(lines)

    elif action == "organize":
        directory = parameters.get("directory", "~/Downloads")
        dry_run = parameters.get("dry_run", True)
        plan = _scan_directory(directory, False)
        matched = [p for p in plan if p.get("destination")]
        if not matched:
            return "No hay archivos para organizar."
        actions_taken, errors = _execute_plan(matched, dry_run)
        mode = "VISTA PREVIA" if dry_run else "EJECUTADO"
        lines = [f"=== Organizacion {mode} ===", f"Archivos procesados: {len(actions_taken)}"]
        for at in actions_taken:
            fname = Path(at["file"]).name
            dest_name = Path(at["destination"]).name
            lines.append(f"  {at['action']}: {fname} -> {Path(at['destination']).parent.name}/{dest_name}")
        if errors:
            lines.append(f"\nErrores ({len(errors)}):")
            for e in errors:
                lines.append(f"  {e}")
        return "\n".join(lines)

    elif action == "rules":
        rules = _load_rules()
        lines = ["=== Reglas de organizacion ==="]
        for i, rule in enumerate(rules, 1):
            lines.append(f"  {i}. {rule['pattern']} -> {rule['destination']} ({rule['action']})")
        return "\n".join(lines)

    elif action == "add_rule":
        pattern = parameters.get("pattern", "")
        destination = parameters.get("destination", "")
        act = parameters.get("action", "move")
        if not pattern or not destination:
            return "Debes especificar pattern y destination."
        rules = _load_rules()
        rules.append({"pattern": pattern, "destination": destination, "action": act})
        _save_rules(rules)
        return f"Regla agregada: {pattern} -> {destination} ({act})"

    elif action == "duplicates":
        directory = parameters.get("directory", "~/Downloads")
        base_dir = Path(directory).expanduser().resolve()
        if not base_dir.exists():
            return f"Directorio no encontrado: {directory}"
        size_map: dict[int, list[Path]] = {}
        for item in base_dir.rglob("*"):
            if item.is_file():
                try:
                    size = item.stat().st_size
                    size_map.setdefault(size, []).append(item)
                except OSError:
                    continue
        dup_groups = []
        for size, candidates in size_map.items():
            if len(candidates) < 2:
                continue
            hash_map: dict[str, list[Path]] = {}
            for c in candidates:
                h = _file_hash_first_kb(c)
                if h:
                    hash_map.setdefault(h, []).append(c)
            for h, group in hash_map.items():
                if len(group) >= 2:
                    dup_groups.append({"size": size, "hash": h, "files": [str(f) for f in group]})
        if not dup_groups:
            return "No se encontraron archivos duplicados."
        lines = [f"=== Duplicados en {directory} ===", f"Grupos encontrados: {len(dup_groups)}"]
        total_wasted = 0
        for dg in dup_groups[:15]:
            wasted = dg["size"] * (len(dg["files"]) - 1)
            total_wasted += wasted
            lines.append(f"\n  Grupo ({_format_size(dg['size'])} c/u, desperdicio: {_format_size(wasted)}):")
            for f in dg["files"]:
                lines.append(f"    {f}")
        if len(dup_groups) > 15:
            lines.append(f"\n  ... y {len(dup_groups) - 15} grupos mas")
        lines.append(f"\nDesperdicio total estimado: {_format_size(total_wasted)}")
        return "\n".join(lines)

    elif action == "history":
        history = _load_history()
        if not history:
            return "No hay historial de organizacion."
        lines = [f"=== Historial ({len(history)} acciones) ==="]
        for entry in history[-20:]:
            fname = Path(entry["original"]).name
            dest_name = Path(entry["destination"]).name
            lines.append(f"  {entry['action']}: {fname} -> {Path(entry["destination"]).parent.name}/{dest_name}")
        if len(history) > 20:
            lines.append(f"  ... y {len(history) - 20} acciones anteriores")
        return "\n".join(lines)

    elif action == "undo":
        history = _load_history()
        if not history:
            return "No hay acciones para deshacer."
        undone = []
        while history:
            entry = history.pop()
            dest = Path(entry["destination"])
            original = Path(entry["original"])
            if not dest.exists():
                continue
            try:
                original.parent.mkdir(parents=True, exist_ok=True)
                if original.exists():
                    stem = original.stem
                    suffix = original.suffix
                    counter = 1
                    while original.exists():
                        original = original.parent / f"{stem}_{counter}{suffix}"
                        counter += 1
                shutil.move(str(dest), str(original))
                undone.append(f"{dest.name} -> {original.name}")
            except Exception as e:
                undone.append(f"Error con {dest.name}: {str(e)}")
                break
        _save_history(history)
        if not undone:
            return "No se pudo deshacer ninguna accion."
        lines = [f"=== Deshecho ({len(undone)} acciones) ==="]
        for u in undone:
            lines.append(f"  {u}")
        return "\n".join(lines)

    elif action == "stats":
        history = _load_history()
        rules = _load_rules()
        lines = ["=== Estadisticas de organizacion ==="]
        lines.append(f"Reglas activas: {len(rules)}")
        lines.append(f"Acciones totales: {len(history)}")
        if history:
            total_moved = sum(1 for h in history if h.get("action") == "move")
            total_copied = sum(1 for h in history if h.get("action") == "copy")
            lines.append(f"Movidos: {total_moved} | Copiados: {total_copied}")
            dest_counts: dict[str, int] = {}
            for h in history:
                dest_folder = Path(h.get("destination", "")).parent.name
                dest_counts[dest_folder] = dest_counts.get(dest_folder, 0) + 1
            lines.append("\nDestinos mas usados:")
            for dest, count in sorted(dest_counts.items(), key=lambda x: -x[1])[:5]:
                lines.append(f"  {dest}: {count}")
        return "\n".join(lines)

    return f"Accion desconocida: {action}. Acciones disponibles: scan, organize, rules, add_rule, duplicates, history, undo, stats"
