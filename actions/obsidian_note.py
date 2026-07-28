# -*- coding: utf-8 -*-
"""
obsidian_note.py — Create, read, search, and manage Obsidian vault notes.
Actions: write, read, search, daily, link, backlinks, tags, browse
"""
import os
import re
from pathlib import Path
from datetime import datetime, date


_VAULT_PATH = Path(r"D:\Eris_Source\vault")


def _ensure_vault():
    _VAULT_PATH.mkdir(parents=True, exist_ok=True)


def _note_path(title: str) -> Path:
    safe = re.sub(r'[<>:"/\\|?*]', '_', title.strip())
    return _VAULT_PATH / f"{safe}.md"


def _list_notes() -> list:
    _ensure_vault()
    return sorted(_VAULT_PATH.glob("*.md"))


def obsidian_note(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = params.get("action", "write").lower().strip()
    title = params.get("title", "")
    content = params.get("content", "")
    tags = params.get("tags", "")
    folder = params.get("folder", "")
    query = params.get("query", "")
    field = params.get("field", "")
    value = params.get("value", "")
    from_title = params.get("from_title", params.get("source_title", ""))
    to_title = params.get("to_title", "")
    new_title = params.get("new_title", "")
    max_notes = int(params.get("max_notes", 200))

    if folder:
        global _VAULT_PATH
        _VAULT_PATH = Path(r"D:\Eris_Source\vault") / folder

    _ensure_vault()

    if action == "write":
        if not title:
            return "Error: Se requiere 'title' para crear nota."
        return _write_note(title, content, tags)
    elif action == "read":
        if not title:
            return "Error: Se requiere 'title' para leer nota."
        return _read_note(title)
    elif action == "search":
        return _search_notes(query or content)
    elif action == "daily":
        return _write_daily(content, tags)
    elif action == "link":
        return _link_notes(from_title, to_title)
    elif action == "backlinks":
        return _backlinks(title)
    elif action == "tags":
        return _list_tags()
    elif action in ("browse", "list"):
        return _browse_notes(max_notes)
    elif action == "graph":
        return _graph_info(max_notes)
    elif action in ("delete", "rename", "open", "append", "update_fm", "concepts"):
        return f"Acción '{action}' pendiente de implementación completa."
    else:
        return f"Acción '{action}' no reconocida. Usa: write, read, search, daily, link, backlinks, tags, browse, graph"


def _write_note(title: str, content: str, tags: str) -> str:
    path = _note_path(title)
    tag_line = ""
    if tags:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        tag_line = "tags: [" + ", ".join(tag_list) + "]\n"

    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if content and content not in existing:
            path.write_text(existing + "\n\n" + content, encoding="utf-8")
            return f"Nota actualizada: {title}"
        return f"Nota ya existe sin cambios: {title}"

    header = f"---\ntitle: {title}\ndate: {datetime.now().strftime('%Y-%m-%d')}\n{tag_line}---\n\n"
    path.write_text(header + (content or f"# {title}\n\n"), encoding="utf-8")
    return f"Nota creada: {title} → {path}"


def _read_note(title: str) -> str:
    path = _note_path(title)
    if not path.exists():
        return f"Nota '{title}' no encontrada. Notas disponibles: {', '.join(p.stem for p in _list_notes()[:20])}"
    text = path.read_text(encoding="utf-8")
    if len(text) > 4000:
        text = text[:4000] + "\n\n... [truncado]"
    return text


def _search_notes(query: str) -> str:
    if not query:
        return "Error: Se requiere 'query' para buscar."
    results = []
    query_lower = query.lower()
    for note in _list_notes():
        try:
            text = note.read_text(encoding="utf-8")
            if query_lower in text.lower() or query_lower in note.stem.lower():
                idx = text.lower().find(query_lower)
                context = text[max(0, idx - 60):idx + 120].replace("\n", " ")
                results.append(f"- **{note.stem}**: ...{context}...")
        except Exception:
            pass
    if not results:
        return f"No se encontró '{query}' en {_VAULT_PATH.name}."
    return f"Resultados para '{query}' ({len(results)}):\n" + "\n".join(results[:20])


def _write_daily(content: str, tags: str) -> str:
    today = date.today().isoformat()
    title = f"Daily {today}"
    default_content = content or f"## {today}\n\n### Tareas\n- [ ] \n\n### Notas\n\n### Reflexión\n"
    return _write_note(title, default_content, tags)


def _link_notes(from_title: str, to_title: str) -> str:
    if not from_title or not to_title:
        return "Error: Se requieren 'from_title' y 'to_title'."
    path = _note_path(from_title)
    if not path.exists():
        return f"Nota '{from_title}' no encontrada."
    text = path.read_text(encoding="utf-8")
    link = f"[[{to_title}]]"
    if link in text:
        return f"Ya existe enlace a '{to_title}' en '{from_title}'."
    path.write_text(text.rstrip() + f"\n\n{link}\n", encoding="utf-8")
    return f"Enlace agregado: {from_title} → {to_title}"


def _backlinks(title: str) -> str:
    if not title:
        return "Error: Se requiere 'title'."
    links = []
    link_pattern = f"[[{title}]]"
    for note in _list_notes():
        try:
            text = note.read_text(encoding="utf-8")
            if link_pattern in text:
                links.append(note.stem)
        except Exception:
            pass
    if not links:
        return f"No hay backlinks a '{title}'."
    return f"Backlinks a '{title}' ({len(links)}): {', '.join(links)}"


def _list_tags() -> str:
    all_tags = set()
    for note in _list_notes():
        try:
            text = note.read_text(encoding="utf-8")
            for match in re.findall(r'#(\w+)', text):
                all_tags.add(match)
            fm_tags = re.search(r'tags:\s*\[(.*?)\]', text)
            if fm_tags:
                for t in fm_tags.group(1).split(","):
                    t = t.strip().strip('"').strip("'")
                    if t:
                        all_tags.add(t)
        except Exception:
            pass
    if not all_tags:
        return "No hay tags en el vault."
    return f"Tags ({len(all_tags)}): {', '.join(sorted(all_tags))}"


def _browse_notes(max_notes: int = 200) -> str:
    notes = _list_notes()
    if not notes:
        return f"Vault vacío en {_VAULT_PATH}."
    lines = [f"Notas en {_VAULT_PATH.name} ({len(notes)} total):"]
    for note in notes[:max_notes]:
        try:
            size = note.stat().st_size
            lines.append(f"  {note.stem} ({size} bytes)")
        except Exception:
            lines.append(f"  {note.stem}")
    return "\n".join(lines)


def _graph_info(max_notes: int = 200) -> str:
    notes = _list_notes()
    links = {}
    for note in notes[:max_notes]:
        try:
            text = note.read_text(encoding="utf-8")
            outgoing = re.findall(r'\[\[(.+?)\]\]', text)
            if outgoing:
                links[note.stem] = outgoing
        except Exception:
            pass
    if not links:
        return "No hay enlaces en el grafo."
    total_links = sum(len(v) for v in links.values())
    return f"Grafo: {len(notes)} notas, {len(links)} con enlaces, {total_links} conexiones totales."
