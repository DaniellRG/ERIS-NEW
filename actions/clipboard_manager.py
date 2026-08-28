"""
clipboard_manager.py — Historial del portapapeles: guardar, buscar, reutilizar textos copiados.
Monitorea el clipboard en background y mantiene un historial persistente.
"""
import json
import time
import threading
from pathlib import Path
from datetime import datetime

_BASE = Path(__file__).resolve().parent.parent
_CLIPBOARD_FILE = _BASE / "data" / "clipboard_history.json"
_MAX_HISTORY = 200
_monitoring = False
_monitor_thread = None


def clipboard_manager(parameters: dict = None, player=None) -> str:
    """
    Gestión del portapapeles inteligente.
    Acciones: list, search, get, clear, copy, paste, start_monitor, stop_monitor, stats, pin, export, delete, snippet, snippets, format
    """
    params = parameters or {}
    action = params.get("action", "list").lower()

    if action == "list":
        return _list_history(params)
    elif action == "search":
        return _search_history(params)
    elif action == "get":
        return _get_clipboard()
    elif action == "clear":
        return _clear_history()
    elif action == "copy":
        return _copy_to_clipboard(params)
    elif action == "paste":
        return _paste_from_clipboard(params)
    elif action == "start_monitor":
        return _start_monitor()
    elif action == "stop_monitor":
        return _stop_monitor()
    elif action == "stats":
        return _get_stats()
    elif action == "pin":
        return _pin_entry(params)
    elif action == "unpin":
        return _unpin_entry(params)
    elif action == "export":
        return _export_history()
    elif action == "delete":
        return _delete_entry(params)
    elif action == "snippet":
        return _save_snippet(params)
    elif action == "snippets":
        return _list_snippets(params)
    elif action == "format":
        return _format_clipboard(params)
    elif action == "status":
        return "Monitor: {} | Historial: {} items | Snippets: {}".format(
            "activo" if _monitoring else "inactivo", len(_load_history()), len(_load_snippets()))
    return "Acciones: list, search, get, clear, copy, paste, start_monitor, stop_monitor, stats, pin, export, delete, snippet, snippets, format"


def _load_history() -> list:
    if _CLIPBOARD_FILE.exists():
        try:
            return json.loads(_CLIPBOARD_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def _save_history(history: list):
    _CLIPBOARD_FILE.parent.mkdir(parents=True, exist_ok=True)
    _CLIPBOARD_FILE.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")


def _list_history(params: dict) -> str:
    history = _load_history()
    if not history:
        return "Historial vacío"

    limit = params.get("limit", 10)
    pinned = [h for h in history if h.get("pinned")]
    unpinned = [h for h in history if not h.get("pinned")]
    unpinned.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    results = ["Portapapeles ({} items, {} fijados):".format(len(history), len(pinned))]

    if pinned:
        results.append("  Fijados:")
        for h in pinned[:5]:
            preview = h.get("content", "")[:60].replace("\n", " ")
            results.append("    [PIN] {} | {}".format(h.get("timestamp", "?")[:16], preview))

    results.append("  Recientes:")
    for h in unpinned[:limit]:
        preview = h.get("content", "")[:60].replace("\n", " ")
        results.append("    {} | {}".format(h.get("timestamp", "?")[:16], preview))

    return "\n".join(results)


def _search_history(params: dict) -> str:
    query = params.get("query", "").lower()
    if not query:
        return "Error: se requiere 'query'"

    history = _load_history()
    results = [h for h in history if query in h.get("content", "").lower()]

    if not results:
        return "No se encontró '{}' en el historial".format(query)

    lines = ["Resultados para '{}' ({}):".format(query, len(results))]
    for h in results[:10]:
        preview = h.get("content", "")[:80].replace("\n", " ")
        lines.append("  {} | {}".format(h.get("timestamp", "?")[:16], preview))
    return "\n".join(lines)


def _get_clipboard() -> str:
    try:
        import pyperclip
        content = pyperclip.paste()
        if content:
            _add_to_history(content, source="manual")
            return "Clipboard actual ({} chars): {}".format(len(content), content[:500])
        return "Clipboard vacío"
    except ImportError:
        return "pyperclip no instalado (pip install pyperclip)"


def _copy_to_clipboard(params: dict) -> str:
    content = params.get("content", "")
    if not content:
        return "Error: se requiere 'content'"
    try:
        import pyperclip
        pyperclip.copy(content)
        _add_to_history(content, source="eris_copy")
        return "Copiado al portapapeles ({} chars)".format(len(content))
    except ImportError:
        return "pyperclip no instalado"


def _paste_from_clipboard(params: dict) -> str:
    index = int(params.get("index", 0))
    history = _load_history()
    unpinned = [h for h in history if not h.get("pinned")]
    unpinned.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    if not unpinned:
        return "Historial vacío"

    idx = min(index, len(unpinned) - 1)
    content = unpinned[idx].get("content", "")

    try:
        import pyperclip
        pyperclip.copy(content)
        return "Pegado del historial: {}".format(content[:200])
    except ImportError:
        return "Contenido: {}".format(content[:500])


def _clear_history() -> str:
    count = len(_load_history())
    _save_history([])
    return "Historial limpiado ({} items removidos)".format(count)


def _start_monitor() -> str:
    global _monitoring, _monitor_thread
    if _monitoring:
        return "Monitor ya está activo"

    _monitoring = True
    _monitor_thread = threading.Thread(target=_monitor_loop, daemon=True)
    _monitor_thread.start()
    return "Monitor de portapapeles iniciado"


def _stop_monitor() -> str:
    global _monitoring
    _monitoring = False
    return "Monitor detenido"


def _monitor_loop():
    last_content = ""
    try:
        import pyperclip
        last_content = pyperclip.paste()
    except ImportError:
        return

    while _monitoring:
        try:
            current = pyperclip.paste()
            if current and current != last_content and len(current) > 1:
                last_content = current
                _add_to_history(current, source="auto_monitor")
        except Exception:
            pass
        time.sleep(1)


def _add_to_history(content: str, source: str = "manual"):
    history = _load_history()

    for h in history:
        if h.get("content") == content:
            h["timestamp"] = datetime.now().isoformat()
            h["access_count"] = h.get("access_count", 0) + 1
            _save_history(history)
            return

    entry = {
        "content": content,
        "timestamp": datetime.now().isoformat(),
        "source": source,
        "pinned": False,
        "access_count": 1,
        "length": len(content),
        "preview": content[:100].replace("\n", " "),
    }
    history.insert(0, entry)

    unpinned = [h for h in history if not h.get("pinned")]
    if len(unpinned) > _MAX_HISTORY:
        history = [h for h in history if h.get("pinned")] + unpinned[:_MAX_HISTORY]

    _save_history(history)


def _pin_entry(params: dict) -> str:
    index = int(params.get("index", 0))
    history = _load_history()
    if index < len(history):
        history[index]["pinned"] = True
        _save_history(history)
        return "Entrada fijada"
    return "Índice fuera de rango"


def _unpin_entry(params: dict) -> str:
    index = int(params.get("index", 0))
    history = _load_history()
    if index < len(history):
        history[index]["pinned"] = False
        _save_history(history)
        return "Entrada desfijada"
    return "Índice fuera de rango"


def _delete_entry(params: dict) -> str:
    index = int(params.get("index", 0))
    history = _load_history()
    if index < len(history):
        removed = history.pop(index)
        _save_history(history)
        return "Entrada eliminada: {}".format(removed.get("preview", "")[:50])
    return "Índice fuera de rango"


def _get_stats() -> str:
    history = _load_history()
    total_size = sum(h.get("length", 0) for h in history)
    pinned = sum(1 for h in history if h.get("pinned"))
    sources = {}
    for h in history:
        src = h.get("source", "unknown")
        sources[src] = sources.get(src, 0) + 1

    lines = [
        "Clipboard Stats:",
        "  Total items: {}".format(len(history)),
        "  Fijados: {}".format(pinned),
        "  Tamaño total: {:.1f} KB".format(total_size / 1024),
        "  Fuentes: {}".format(", ".join("{}:{}".format(k, v) for k, v in sources.items())),
    ]

    if history:
        most_used = max(history, key=lambda x: x.get("access_count", 0))
        lines.append("  Más usado ({} veces): {}".format(
            most_used.get("access_count", 0), most_used.get("preview", "")[:50]))

    return "\n".join(lines)


def _export_history() -> str:
    history = _load_history()
    export_path = _BASE / "data" / "clipboard_export.json"
    export_path.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")
    return "Exportados {} items a {}".format(len(history), str(export_path))


_SNIPPETS_FILE = _BASE / "data" / "clipboard_snippets.json"


def _load_snippets() -> dict:
    if _SNIPPETS_FILE.exists():
        try:
            return json.loads(_SNIPPETS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_snippets(snippets: dict):
    _SNIPPETS_FILE.write_text(json.dumps(snippets, ensure_ascii=False, indent=2), encoding="utf-8")


def _save_snippet(params: dict) -> str:
    name = params.get("name", "").strip()
    text = params.get("text", "").strip()
    tags = params.get("tags", [])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    if not name or not text:
        return "Necesitás 'name' y 'text'. Ej: snippet name='mi_firma' text='Saludos, Danie'"
    snippets = _load_snippets()
    snippets[name] = {"text": text, "tags": tags, "created": datetime.now().isoformat(), "uses": 0}
    _save_snippets(snippets)
    return "✅ Snippet '{}' guardado ({} chars)".format(name, len(text))


def _list_snippets(params: dict) -> str:
    query = params.get("query", "").strip().lower()
    snippets = _load_snippets()
    if not snippets:
        return "Sin snippets guardados. Usá: snippet name='...' text='...'"
    items = list(snippets.items())
    if query:
        items = [(k, v) for k, v in items if query in k.lower() or query in v.get("text", "").lower() or query in " ".join(v.get("tags", []))]
    if not items:
        return "Sin resultados para '{}'".format(query)
    lines = ["**Snippets ({}):**\n".format(len(items))]
    for name, s in sorted(items, key=lambda x: -x[1].get("uses", 0)):
        tags = " ".join("#{}".format(t) for t in s.get("tags", []))
        preview = s.get("text", "")[:80]
        lines.append("📌 **{}** {} (usado {} veces)".format(name, tags, s.get("uses", 0)))
        lines.append("   {}\n".format(preview))
    return "\n".join(lines)


def _format_clipboard(params: dict) -> str:
    fmt = params.get("format", "lower").strip().lower()
    text = params.get("text", "").strip()
    if not text:
        entry = _get_last_history_entry()
        if not entry:
            return "Nada en el portapapeles."
        text = entry.get("text", "")
    if not text:
        return "Necesitás 'text' o tener algo copiado."
    formatters = {
        "lower": text.lower(),
        "upper": text.upper(),
        "title": text.title(),
        "capitalize": text.capitalize(),
        "snake": text.lower().replace(" ", "_").replace("-", "_"),
        "kebab": text.lower().replace(" ", "-").replace("_", "-"),
        "camel": "".join(w.capitalize() if i else w.lower() for i, w in enumerate(text.split())),
        "trim": "\n".join(l.strip() for l in text.splitlines()),
        "md": "```\n{}\n```".format(text),
        "quote": "\n".join("> {}".format(l) for l in text.splitlines()),
    }
    if fmt in formatters:
        result = formatters[fmt]
        try:
            import subprocess
            process = subprocess.Popen("clip", stdin=subprocess.PIPE, shell=True, creationflags=0x08000000)
            process.communicate(result.encode("utf-16-le"))
        except Exception:
            pass
        return "**{} → clipboard:**\n{}".format(fmt, result[:500])
    return "Formatos: " + ", ".join(sorted(formatters.keys()))


def _get_last_history_entry() -> dict | None:
    history = _load_history()
    return history[-1] if history else None
