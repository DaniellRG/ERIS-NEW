# -*- coding: utf-8 -*-
from __future__ import annotations

import ctypes
import json
import time
from ctypes import wintypes
from datetime import datetime
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_HISTORY_FILE = _BASE / "data" / "clipboard_history.json"
_PINNED_FILE = _BASE / "data" / "clipboard_pinned.json"
_MAX_HISTORY = 200

CF_UNICODETEXT = 13


def _get_clipboard_text() -> str:
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    if not user32.OpenClipboard(0):
        return ""
    try:
        if user32.IsClipboardFormatAvailable(CF_UNICODETEXT):
            h_data = user32.GetClipboardData(CF_UNICODETEXT)
            if h_data:
                p_data = kernel32.GlobalLock(h_data)
                if p_data:
                    text = ctypes.c_wchar_p(p_data).value
                    kernel32.GlobalUnlock(h_data)
                    return text or ""
    finally:
        user32.CloseClipboard()
    return ""


def _set_clipboard_text(text: str):
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    if not user32.OpenClipboard(0):
        return False
    try:
        user32.EmptyClipboard()
        data = text.encode("utf-16-le") + b"\x00\x00"
        h_mem = kernel32.GlobalAlloc(0x0042, len(data))
        if not h_mem:
            return False
        p_mem = kernel32.GlobalLock(h_mem)
        if not p_mem:
            kernel32.GlobalFree(h_mem)
            return False
        ctypes.memmove(p_mem, data, len(data))
        kernel32.GlobalUnlock(h_mem)
        user32.SetClipboardData(CF_UNICODETEXT, h_mem)
        return True
    finally:
        user32.CloseClipboard()


def _load_history() -> list:
    if _HISTORY_FILE.exists():
        try:
            return json.loads(_HISTORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def _save_history(history: list):
    _HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    _HISTORY_FILE.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")


def _load_pinned() -> list:
    if _PINNED_FILE.exists():
        try:
            return json.loads(_PINNED_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def _save_pinned(pinned: list):
    _PINNED_FILE.parent.mkdir(parents=True, exist_ok=True)
    _PINNED_FILE.write_text(json.dumps(pinned, indent=2, ensure_ascii=False), encoding="utf-8")


def _add_to_history(text: str):
    if not text or len(text.strip()) == 0:
        return
    history = _load_history()
    for h in history:
        if h.get("text") == text:
            h["timestamp"] = datetime.now().isoformat()
            h["access_count"] = h.get("access_count", 0) + 1
            _save_history(history)
            return
    entry = {
        "text": text,
        "timestamp": datetime.now().isoformat(),
        "category": "",
        "pinned": False,
        "access_count": 1,
        "length": len(text),
        "preview": text[:100].replace("\n", " "),
    }
    history.insert(0, entry)
    unpinned = [h for h in history if not h.get("pinned")]
    if len(unpinned) > _MAX_HISTORY:
        history = [h for h in history if h.get("pinned")] + unpinned[:_MAX_HISTORY]
    _save_history(history)


def _action_read(_params: dict) -> str:
    text = _get_clipboard_text()
    if not text:
        return "Portapapeles vacío"
    _add_to_history(text)
    preview = text[:500].replace("\n", "↵")
    return "Clipboard ({} chars): {}".format(len(text), preview)


def _action_history(params: dict) -> str:
    history = _load_history()
    if not history:
        return "Historial vacío"
    limit = int(params.get("limit", 20))
    lines = ["Historial del portapapeles ({} items, mostrando {}):".format(len(history), min(limit, len(history)))]
    for i, h in enumerate(history[:limit]):
        preview = h.get("preview", h.get("text", "")[:60])
        ts = h.get("timestamp", "?")[:16]
        cat = h.get("category", "")
        pin = " [PIN]" if h.get("pinned") else ""
        cat_tag = " [{}]".format(cat) if cat else ""
        lines.append("  {}. {} | {}{}{} | {} chars".format(i + 1, ts, preview[:50], cat_tag, pin, h.get("length", 0)))
    return "\n".join(lines)


def _action_search(params: dict) -> str:
    query = params.get("query", "").lower().strip()
    if not query:
        return "Error: se requiere 'query'"
    history = _load_history()
    results = [h for h in history if query in h.get("text", "").lower()]
    if not results:
        return "Sin resultados para '{}'".format(query)
    lines = ["Resultados para '{}' ({}):".format(query, len(results))]
    for i, h in enumerate(results[:15]):
        preview = h.get("text", "")[:80].replace("\n", " ")
        ts = h.get("timestamp", "?")[:16]
        lines.append("  {}. [{}] {}".format(i + 1, ts, preview))
    return "\n".join(lines)


def _action_pin(params: dict) -> str:
    text = params.get("text", "").strip()
    index = params.get("index")
    pinned = _load_pinned()

    if index is not None:
        try:
            idx = int(index)
        except (TypeError, ValueError):
            return "Error: 'index' debe ser un número"
        history = _load_history()
        if 0 <= idx < len(history):
            text = history[idx].get("text", "")
        else:
            return "Índice fuera de rango (0-{})".format(len(history) - 1)

    if not text:
        return "Error: se requiere 'text' o 'index'"

    for p in pinned:
        if p.get("text") == text:
            return "Ya está en fijados"

    category = params.get("category", "")
    entry = {
        "text": text,
        "timestamp": datetime.now().isoformat(),
        "category": category,
        "preview": text[:100].replace("\n", " "),
        "length": len(text),
    }
    pinned.insert(0, entry)
    _save_pinned(pinned)

    history = _load_history()
    for h in history:
        if h.get("text") == text:
            h["pinned"] = True
            h["category"] = category
    _save_history(history)

    return "Texto fijado ({} chars)".format(len(text))


def _action_pinned(_params: dict) -> str:
    pinned = _load_pinned()
    if not pinned:
        return "Sin elementos fijados"
    lines = ["Fijados ({}):".format(len(pinned))]
    for i, p in enumerate(pinned):
        preview = p.get("preview", p.get("text", "")[:60])
        cat = p.get("category", "")
        cat_tag = " [{}]".format(cat) if cat else ""
        lines.append("  {}. {}{} | {} chars".format(i + 1, preview[:60], cat_tag, p.get("length", 0)))
    return "\n".join(lines)


def _action_unpin(params: dict) -> str:
    index = params.get("index")
    if index is None:
        return "Error: se requiere 'index'"
    try:
        idx = int(index)
    except (TypeError, ValueError):
        return "Error: 'index' debe ser un número"
    pinned = _load_pinned()
    if not (0 <= idx < len(pinned)):
        return "Índice fuera de rango (0-{})".format(len(pinned) - 1)
    removed = pinned.pop(idx)
    _save_pinned(pinned)
    text_preview = removed.get("preview", "")[:50]
    return "Desfijado: {}".format(text_preview)


def _action_clear(_params: dict) -> str:
    count = len(_load_history())
    _save_history([])
    return "Historial limpiado ({} items removidos)".format(count)


def _action_categories(_params: dict) -> str:
    pinned = _load_pinned()
    cats: dict[str, int] = {}
    for p in pinned:
        c = p.get("category", "") or "(sin categoría)"
        cats[c] = cats.get(c, 0) + 1
    if not cats:
        return "Sin categorías (no hay elementos fijados)"
    lines = ["Categorías:"]
    for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
        lines.append("  {} — {} items".format(cat, count))
    return "\n".join(lines)


def _action_add(params: dict) -> str:
    text = params.get("text", "").strip()
    if not text:
        return "Error: se requiere 'text'"
    ok = _set_clipboard_text(text)
    if not ok:
        return "Error al escribir al portapapeles"
    _add_to_history(text)
    return "Texto copiado al portapapeles ({} chars)".format(len(text))


def _action_stats(_params: dict) -> str:
    history = _load_history()
    pinned = _load_pinned()
    total_size = sum(h.get("length", 0) for h in history)
    categories: dict[str, int] = {}
    for p in pinned:
        c = p.get("category", "") or "(sin categoría)"
        categories[c] = categories.get(c, 0) + 1

    lines = [
        "Estadísticas del portapapeles:",
        "  Items en historial: {}".format(len(history)),
        "  Items fijados: {}".format(len(pinned)),
        "  Tamaño total historial: {:.1f} KB".format(total_size / 1024),
    ]

    if categories:
        lines.append("  Categorías: {}".format(", ".join("{}:{}".format(k, v) for k, v in categories.items())))

    if history:
        most_used = max(history, key=lambda x: x.get("access_count", 0))
        lines.append("  Más usado ({}x): {}".format(
            most_used.get("access_count", 0), most_used.get("preview", "")[:50]))

        avg_len = total_size / len(history) if history else 0
        lines.append("  Longitud promedio: {:.0f} chars".format(avg_len))

    return "\n".join(lines)


def clipboard_history(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = params.get("action", "read").lower()

    if action == "read":
        return _action_read(params)
    elif action == "history":
        return _action_history(params)
    elif action == "search":
        return _action_search(params)
    elif action == "pin":
        return _action_pin(params)
    elif action == "pinned":
        return _action_pinned(params)
    elif action == "unpin":
        return _action_unpin(params)
    elif action == "clear":
        return _action_clear(params)
    elif action == "categories":
        return _action_categories(params)
    elif action == "add":
        return _action_add(params)
    elif action == "stats":
        return _action_stats(params)
    return "Acciones: read, history, search, pin, pinned, unpin, clear, categories, add, stats"
