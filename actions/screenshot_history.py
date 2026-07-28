"""
screenshot_history.py — Historial de screenshots: guardar, buscar, revisar capturas anteriores.
"""
import json
import hashlib
import shutil
from pathlib import Path
from datetime import datetime

_BASE = Path(__file__).resolve().parent.parent
_SCREENSHOTS_DIR = _BASE / "data" / "screenshots"
_INDEX_FILE = _SCREENSHOTS_DIR / "_index.json"


def screenshot_history(parameters: dict = None, player=None) -> str:
    """
    Historial de screenshots.
    Acciones: capture, list, search, get, delete, clean, compare, open, stats, tag
    """
    params = parameters or {}
    action = params.get("action", "list").lower()
    _SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    _ensure_index()

    if action == "capture":
        return _capture_screenshot(params)
    elif action == "list":
        return _list_screenshots(params)
    elif action == "search":
        return _search_screenshots(params)
    elif action == "get":
        return _get_screenshot(params)
    elif action == "delete":
        return _delete_screenshot(params)
    elif action == "clean":
        return _clean_old(params)
    elif action == "compare":
        return _compare_screenshots(params)
    elif action == "open":
        return _open_screenshot(params)
    elif action == "stats":
        return _get_stats()
    elif action == "tag":
        return _tag_screenshot(params)
    elif action == "folder":
        return "Carpeta de screenshots: {}".format(str(_SCREENSHOTS_DIR))
    return "Acciones: capture, list, search, get, delete, clean, compare, open, stats, tag, folder"


def _ensure_index():
    if _INDEX_FILE.exists():
        return
    _save_index({"screenshots": [], "created": datetime.now().isoformat()})


def _load_index():
    if _INDEX_FILE.exists():
        try:
            return json.loads(_INDEX_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"screenshots": []}


def _save_index(idx):
    _INDEX_FILE.write_text(json.dumps(idx, indent=2, ensure_ascii=False), encoding="utf-8")


def _capture_screenshot(params: dict) -> str:
    name = params.get("name", "screenshot_{}".format(int(datetime.now().timestamp())))
    region = params.get("region", None)

    try:
        import pyautogui
        if region:
            img = pyautogui.screenshot(region=tuple(region))
        else:
            img = pyautogui.screenshot()
    except ImportError:
        return "Error: pyautogui no instalado"
    except Exception as e:
        return "Error capturando: {}".format(str(e))

    filepath = _SCREENSHOTS_DIR / "{}.png".format(name)
    img.save(str(filepath))

    idx = _load_index()
    entry = {
        "name": name,
        "filename": "{}.png".format(name),
        "timestamp": datetime.now().isoformat(),
        "size_kb": round(filepath.stat().st_size / 1024, 1),
        "width": img.width,
        "height": img.height,
        "tags": params.get("tags", []) if isinstance(params.get("tags"), list) else [],
        "notes": params.get("notes", ""),
        "region": region,
    }
    idx["screenshots"].append(entry)
    _save_index(idx)

    return "Screenshot '{}' guardado ({}x{}, {:.1f}KB)".format(
        name, img.width, img.height, entry["size_kb"])


def _list_screenshots(params: dict) -> str:
    idx = _load_index()
    screenshots = idx.get("screenshots", [])
    if not screenshots:
        return "No hay screenshots guardados"

    limit = params.get("limit", 10)
    screenshots.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    results = ["Screenshots ({} total, mostrando {}):".format(len(screenshots), min(limit, len(screenshots)))]
    for s in screenshots[:limit]:
        tags = " [{}]".format(", ".join(s.get("tags", []))) if s.get("tags") else ""
        results.append("  {} | {} | {}x{} | {:.1f}KB{}".format(
            s.get("name", "?"), s.get("timestamp", "?")[:16],
            s.get("width", "?"), s.get("height", "?"),
            s.get("size_kb", 0), tags))
    return "\n".join(results)


def _search_screenshots(params: dict) -> str:
    query = params.get("query", "").lower()
    if not query:
        return "Error: se requiere 'query'"

    idx = _load_index()
    results_list = []
    for s in idx.get("screenshots", []):
        if (query in s.get("name", "").lower() or
            query in s.get("notes", "").lower() or
            any(query in t.lower() for t in s.get("tags", []))):
            results_list.append(s)

    if not results_list:
        return "No se encontraron screenshots para: {}".format(query)

    lines = ["Resultados para '{}' ({}):".format(query, len(results_list))]
    for s in results_list[:10]:
        lines.append("  {} | {} | {}".format(
            s.get("name", "?"), s.get("timestamp", "?")[:16], s.get("notes", "")[:50]))
    return "\n".join(lines)


def _get_screenshot(params: dict) -> str:
    name = params.get("name", "")
    if not name:
        return "Error: se requiere 'name'"

    filepath = _SCREENSHOTS_DIR / "{}.png".format(name)
    if filepath.exists():
        return "Screenshot: {} ({:.1f}KB) | {}".format(
            name, filepath.stat().st_size / 1024, str(filepath))
    return "Screenshot no encontrado: {}".format(name)


def _delete_screenshot(params: dict) -> str:
    name = params.get("name", "")
    if not name:
        return "Error: se requiere 'name'"

    filepath = _SCREENSHOTS_DIR / "{}.png".format(name)
    if not filepath.exists():
        return "Screenshot no encontrado: {}".format(name)

    filepath.unlink()
    idx = _load_index()
    idx["screenshots"] = [s for s in idx.get("screenshots", []) if s.get("name") != name]
    _save_index(idx)
    return "Screenshot '{}' eliminado".format(name)


def _clean_old(params: dict) -> str:
    days = int(params.get("days", 30))
    idx = _load_index()
    cutoff = datetime.now().timestamp() - (days * 86400)

    keep = []
    removed = 0
    for s in idx.get("screenshots", []):
        try:
            ts = datetime.fromisoformat(s.get("timestamp", "")).timestamp()
        except Exception:
            ts = 0
        if ts < cutoff:
            filepath = _SCREENSHOTS_DIR / s.get("filename", "")
            if filepath.exists():
                filepath.unlink()
            removed += 1
        else:
            keep.append(s)

    idx["screenshots"] = keep
    _save_index(idx)
    return "Limpiados {} screenshots mayores a {} días".format(removed, days)


def _compare_screenshots(params: dict) -> str:
    name1 = params.get("name1", "")
    name2 = params.get("name2", "")
    if not name1 or not name2:
        return "Error: se requiere 'name1' y 'name2'"

    idx = _load_index()
    s1 = next((s for s in idx.get("screenshots", []) if s.get("name") == name1), None)
    s2 = next((s for s in idx.get("screenshots", []) if s.get("name") == name2), None)

    if not s1 or not s2:
        return "Uno o ambos screenshots no encontrados"

    lines = ["Comparación:", "  A: {} ({}, {}x{})".format(name1, s1.get("timestamp", "?")[:16],
              s1.get("width", "?"), s1.get("height", "?")),
             "  B: {} ({}, {}x{})".format(name2, s2.get("timestamp", "?")[:16],
              s2.get("width", "?"), s2.get("height", "?")),
             "  Tamaño A: {:.1f}KB | B: {:.1f}KB".format(s1.get("size_kb", 0), s2.get("size_kb", 0))]
    return "\n".join(lines)


def _open_screenshot(params: dict) -> str:
    name = params.get("name", "")
    if not name:
        return "Error: se requiere 'name'"
    filepath = _SCREENSHOTS_DIR / "{}.png".format(name)
    if not filepath.exists():
        return "No encontrado: {}".format(name)
    try:
        import os
        os.startfile(str(filepath))
        return "Abriendo '{}'".format(name)
    except Exception as e:
        return "Error abriendo: {}".format(str(e))


def _get_stats() -> str:
    idx = _load_index()
    screenshots = idx.get("screenshots", [])
    total_size = sum(s.get("size_kb", 0) for s in screenshots)
    total = len(screenshots)

    tags_count = {}
    for s in screenshots:
        for t in s.get("tags", []):
            tags_count[t] = tags_count.get(t, 0) + 1

    lines = [
        "Stats de screenshots:",
        "  Total: {}".format(total),
        "  Tamaño total: {:.1f} MB".format(total_size / 1024),
        "  Tags más usados: {}".format(
            ", ".join("{}({})".format(t, c) for t, c in sorted(tags_count.items(), key=lambda x: -x[1])[:5])
            if tags_count else "ninguno"),
    ]

    if screenshots:
        oldest = min(screenshots, key=lambda x: x.get("timestamp", ""))
        newest = max(screenshots, key=lambda x: x.get("timestamp", ""))
        lines.append("  Más antiguo: {} ({})".format(oldest.get("name"), oldest.get("timestamp", "?")[:10]))
        lines.append("  Más reciente: {} ({})".format(newest.get("name"), newest.get("timestamp", "?")[:10]))

    return "\n".join(lines)


def _tag_screenshot(params: dict) -> str:
    name = params.get("name", "")
    tags = params.get("tags", [])
    if not name or not tags:
        return "Error: se requiere 'name' y 'tags'"
    if not isinstance(tags, list):
        tags = [tags]

    idx = _load_index()
    for s in idx.get("screenshots", []):
        if s.get("name") == name:
            existing = s.get("tags", [])
            s["tags"] = list(set(existing + tags))
            _save_index(idx)
            return "Tags actualizados para '{}': {}".format(name, ", ".join(s["tags"]))
    return "Screenshot no encontrado: {}".format(name)
