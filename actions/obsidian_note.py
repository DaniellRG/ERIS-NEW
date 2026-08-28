# -*- coding: utf-8 -*-
"""
obsidian_note.py — Segundo cerebro de ERIS: Obsidian vault.
Actions: write, read, search, daily, link, backlinks, tags, browse, graph,
         promote, inbox, conventions, stats
Estructura del vault:
  /raw     — capturas en bruto (dumping ground; write sin folder cae acá)
  /wiki    — artículos codificados / notas atómicas
  /outputs — productos terminados (decks, reportes)
  CLAUDE.md — convenciones del vault (wiki-links, notas atómicas, daily notes)
Flujo: capturá en /raw → promové a /wiki cuando esté destilado → /outputs cuando sea un producto.
"""
import os
import re
from pathlib import Path
from datetime import datetime, date

_VAULT_PATH = Path(r"D:\Eris_Source\vault")
_FOLDERS = ("raw", "wiki", "outputs")
_CONVENTIONS_FILE = "CLAUDE.md"


def _ensure_vault():
    _VAULT_PATH.mkdir(parents=True, exist_ok=True)
    for f in _FOLDERS:
        (_VAULT_PATH / f).mkdir(parents=True, exist_ok=True)
    _ensure_conventions()


def _ensure_conventions():
    path = _VAULT_PATH / _CONVENTIONS_FILE
    if path.exists():
        return
    text = (
        "# Vault de ERIS — Segundo cerebro\n\n"
        "Este vault es la memoria a largo plazo de ERIS. Seguí estas convenciones:\n\n"
        "- Usá **wiki-links** `[[Nota]]` para conectar notas relacionadas.\n"
        "- Mantené las notas **atómicas**: una idea por nota.\n"
        "- Las notas diarias (`Daily YYYY-MM-DD`) resumen la jornada.\n"
        "- **/raw**: capturas en bruto (ideas, fragmentos, apuntes). El write por defecto cae acá.\n"
        "- **/wiki**: artículos codificados y notas atómicas con enlaces.\n"
        "- **/outputs**: productos terminados (reportes, decks, resultados).\n"
        "- Promové notas con `promote` cuando pasen de raw a wiki a outputs.\n"
    )
    path.write_text(text, encoding="utf-8")


def _note_path(title: str) -> Path:
    safe = re.sub(r'[<>:"/\\|?*]', "_", title.strip())
    return _VAULT_PATH / f"{safe}.md"


def _folder_path(folder: str) -> Path:
    folder = (folder or "").strip().strip("/")
    if not folder:
        return _VAULT_PATH
    return _VAULT_PATH / folder


def _list_notes() -> list:
    _ensure_vault()
    return sorted(_VAULT_PATH.rglob("*.md"))


def _list_notes_in_folder(folder: str) -> list:
    _ensure_vault()
    return sorted(_folder_path(folder).glob("*.md"))


def _note_in_folder(folder: str, title: str) -> Path:
    safe = re.sub(r'[<>:"/\\|?*]', "_", title.strip())
    return _folder_path(folder) / f"{safe}.md"


def _find_note(title: str) -> Path:
    """Busca una nota por título en todo el vault (con y sin extensión)."""
    _ensure_vault()
    title = title.strip()
    if title.endswith(".md"):
        title = title[:-3]
    for path in _list_notes():
        if path.stem.lower() == title.lower():
            return path
    return _VAULT_PATH / f"{re.sub(r'[<>:\"/\\\\|?*]', '_', title)}.md"


def _relative(note: Path) -> str:
    try:
        return note.relative_to(_VAULT_PATH).as_posix()
    except Exception:
        return note.name


def _parse_frontmatter(text: str) -> tuple:
    """Devuelve (frontmatter_dict, body)."""
    fm = {}
    body = text
    if text.startswith("---"):
        end = text.find("---", 3)
        if end > 0:
            raw = text[3:end]
            body = text[end + 3:].lstrip("\n")
            for line in raw.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    fm[k.strip()] = v.strip().strip('"').strip("[]")
    return fm, body


def _with_frontmatter(title: str, content: str, tags: str, folder: str, status: str) -> str:
    tag_line = ""
    if tags:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        tag_line = "tags: [" + ", ".join(tag_list) + "]\n"
    status_line = f"status: {status}\n" if status else ""
    folder_line = f"folder: {folder}\n" if folder else ""
    return (
        f"---\ntitle: {title}\ndate: {datetime.now().strftime('%Y-%m-%d')}\n"
        f"{status_line}{folder_line}{tag_line}---\n\n"
        + (content or f"# {title}\n\n")
    )


def obsidian_note(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = params.get("action", "write").lower().strip()
    title = params.get("title", "")
    content = params.get("content", "")
    tags = params.get("tags", "")
    folder = (params.get("folder", "") or "").strip()
    query = params.get("query", "")
    from_title = params.get("from_title", params.get("source_title", ""))
    to_title = params.get("to_title", "")
    to_folder = params.get("to_folder", "")
    new_title = params.get("new_title", "")
    max_notes = int(params.get("max_notes", 200))

    _ensure_vault()

    if action == "write":
        if not title:
            return "Error: Se requiere 'title' para crear nota."
        return _write_note(title, content, tags, folder)
    elif action == "read":
        if not title:
            return "Error: Se requiere 'title' para leer nota."
        return _read_note(title)
    elif action == "search":
        return _search_notes(query or content, folder)
    elif action == "daily":
        return _write_daily(content, tags)
    elif action == "link":
        return _link_notes(from_title, to_title)
    elif action == "backlinks":
        return _backlinks(title)
    elif action == "tags":
        return _list_tags()
    elif action in ("browse", "list"):
        return _browse_notes(max_notes, folder)
    elif action == "graph":
        return _graph_info(max_notes)
    elif action == "promote":
        if not title:
            return "Error: Se requiere 'title' para promover."
        return _promote_note(title, to_folder or folder)
    elif action == "rename":
        if not title or not new_title:
            return "Error: Se requieren 'title' y 'new_title'."
        return _rename_note(title, new_title)
    elif action == "inbox":
        return _browse_notes(max_notes, "raw")
    elif action == "conventions":
        return _read_conventions()
    elif action == "stats":
        return _stats()
    elif action in ("delete", "rename", "open", "append", "update_fm", "concepts"):
        return f"Acción '{action}' pendiente de implementación completa."
    else:
        return (f"Acción '{action}' no reconocida. Usa: write, read, search, daily, "
                f"link, backlinks, tags, browse, graph, promote, inbox, conventions, stats")


def _write_note(title: str, content: str, tags: str, folder: str = "") -> str:
    folder = (folder or "").strip().strip("/")
    if not folder:
        folder = "raw"  # captura por defecto; se promueve con `promote`
    target = _note_in_folder(folder, title)
    target.parent.mkdir(parents=True, exist_ok=True)

    if target.exists():
        existing = target.read_text(encoding="utf-8")
        if content and content not in existing:
            target.write_text(existing + "\n\n" + content, encoding="utf-8")
            return f"Nota actualizada: {title} → {_relative(target)}"
        return f"Nota ya existe sin cambios: {title}"

    status = {"raw": "raw", "wiki": "wiki", "outputs": "done"}.get(folder, "")
    header = _with_frontmatter(title, content, tags, folder, status)
    target.write_text(header, encoding="utf-8")
    return f"Nota creada: {title} → {_relative(target)}"


def _read_note(title: str) -> str:
    path = _find_note(title)
    if not path.exists():
        all_notes = ", ".join(f"{_relative(p)}" for p in _list_notes()[:30])
        return f"Nota '{title}' no encontrada. Notas disponibles: {all_notes}"
    text = path.read_text(encoding="utf-8")
    if len(text) > 4000:
        text = text[:4000] + "\n\n... [truncado]"
    return text


def _search_notes(query: str, folder: str = "") -> str:
    if not query:
        return "Error: Se requiere 'query' para buscar."
    notes = _list_notes_in_folder(folder) if folder else _list_notes()
    results = []
    query_lower = query.lower()
    for note in notes:
        try:
            text = note.read_text(encoding="utf-8")
            if query_lower in text.lower() or query_lower in note.stem.lower():
                idx = text.lower().find(query_lower)
                context = text[max(0, idx - 60):idx + 120].replace("\n", " ")
                results.append(f"- **{_relative(note)}**: ...{context}...")
        except Exception:
            pass
    if not results:
        return f"No se encontró '{query}' en el vault."
    return f"Resultados para '{query}' ({len(results)}):\n" + "\n".join(results[:20])


def _write_daily(content: str, tags: str) -> str:
    today = date.today().isoformat()
    title = f"Daily {today}"
    default_content = content or f"## {today}\n\n### Tareas\n- [ ] \n\n### Notas\n\n### Reflexión\n"
    # La daily se linkea a las notas recientes para crecer el grafo
    recent = [p.stem for p in _list_notes_in_folder("raw")][:5]
    if recent:
        default_content += "\n### Conexiones\n" + "\n".join(f"- [[{r}]]" for r in recent) + "\n"
    return _write_note(title, default_content, tags, "")


def _link_notes(from_title: str, to_title: str) -> str:
    if not from_title or not to_title:
        return "Error: Se requieren 'from_title' y 'to_title'."
    path = _find_note(from_title)
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
                links.append(_relative(note))
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


def _browse_notes(max_notes: int = 200, folder: str = "") -> str:
    notes = _list_notes_in_folder(folder) if folder else _list_notes()
    if not notes:
        return f"Vault vacío en {_VAULT_PATH}."
    lines = [f"Notas en {_VAULT_PATH.name} ({len(notes)} total):"]
    for note in notes[:max_notes]:
        try:
            size = note.stat().st_size
            lines.append(f"  {_relative(note)} ({size} bytes)")
        except Exception:
            lines.append(f"  {_relative(note)}")
    return "\n".join(lines)


def _graph_info(max_notes: int = 200) -> str:
    notes = _list_notes()
    links = {}
    for note in notes[:max_notes]:
        try:
            text = note.read_text(encoding="utf-8")
            outgoing = re.findall(r'\[\[(.+?)\]\]', text)
            if outgoing:
                links[_relative(note)] = outgoing
        except Exception:
            pass
    if not links:
        return "No hay enlaces en el grafo."
    total_links = sum(len(v) for v in links.values())
    return f"Grafo: {len(notes)} notas, {len(links)} con enlaces, {total_links} conexiones totales."


def _rename_note(title: str, new_title: str) -> str:
    """Renombra una nota manteniendo su carpeta y frontmatter."""
    path = _find_note(title)
    if not path.exists():
        return f"Nota '{title}' no encontrada."
    folder = path.parent.name if path.parent != _VAULT_PATH else ""
    dest = _note_in_folder(folder, new_title) if folder else _note_path(new_title)
    if dest.exists():
        return f"Ya existe una nota llamada '{new_title}'."
    text = path.read_text(encoding="utf-8")
    text = text.replace(f"title: {title}", f"title: {new_title}", 1)
    dest.write_text(text, encoding="utf-8")
    path.unlink()
    return f"Nota renombrada: {_relative(path)} → {_relative(dest)}"


def _promote_note(title: str, to_folder: str) -> str:
    """Promueve una nota entre carpetas: raw → wiki → outputs (o a to_folder)."""
    path = _find_note(title)
    if not path.exists():
        return f"Nota '{title}' no encontrada."
    current = path.parent.name if path.parent != _VAULT_PATH else ""
    if not to_folder:
        order = ["", "raw", "wiki", "outputs"]
        idx = order.index(current) if current in order else 1
        to_folder = order[idx + 1] if idx + 1 < len(order) else "outputs"
    to_folder = to_folder.strip().strip("/")
    if to_folder not in _FOLDERS:
        return f"Carpeta destino '{to_folder}' inválida. Usa: raw, wiki, outputs."
    if to_folder == current:
        return f"La nota ya está en {to_folder or 'raíz'}."

    dest = _note_in_folder(to_folder, title)
    dest.parent.mkdir(parents=True, exist_ok=True)
    text = path.read_text(encoding="utf-8")

    # Actualizar frontmatter: status y folder
    text = _update_fm_field(text, "status", {"raw": "raw", "wiki": "wiki", "outputs": "done"}.get(to_folder, ""))
    text = _update_fm_field(text, "folder", to_folder)

    dest.write_text(text, encoding="utf-8")
    path.unlink()
    return f"Nota promovida: {_relative(path)} → {_relative(dest)}"


def _update_fm_field(text: str, field: str, value: str) -> str:
    if text.startswith("---"):
        end = text.find("---", 3)
        if end > 0:
            raw = text[3:end]
            lines = raw.splitlines()
            replaced = False
            new_lines = []
            for line in lines:
                if line.startswith(field + ":"):
                    new_lines.append(f"{field}: {value}" if value else f"# {line}")
                    replaced = True
                else:
                    new_lines.append(line)
            if not replaced and value:
                new_lines.append(f"{field}: {value}")
            return "---\n" + "\n".join(new_lines) + text[end:]
    return text


def _read_conventions() -> str:
    _ensure_conventions()
    return (_VAULT_PATH / _CONVENTIONS_FILE).read_text(encoding="utf-8")


def _stats() -> str:
    _ensure_vault()
    lines = [f"Vault: {_VAULT_PATH}"]
    for f in ("",) + _FOLDERS:
        notes = _list_notes_in_folder(f) if f else list(_VAULT_PATH.glob("*.md"))
        label = f or "raíz"
        lines.append(f"  /{label}: {len(notes)} notas")
    total_links = 0
    for note in _list_notes():
        try:
            total_links += len(re.findall(r'\[\[.+?\]\]', note.read_text(encoding="utf-8")))
        except Exception:
            pass
    lines.append(f"  Enlaces totales: {total_links}")
    return "\n".join(lines)
