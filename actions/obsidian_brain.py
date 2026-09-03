# -*- coding: utf-8 -*-
"""
Eris ↔ Obsidian Integration – Segundo cerebro interconectado.
Lee, escribe, busca, conecta, elimina, renombra y navega notas Markdown
con [[wikilinks]], YAML frontmatter, y grafo de conocimiento.
También lanza Obsidian al vault/nota específica.
"""
import json
import re
import yaml
import subprocess
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from core.logging_setup import get_obsidian_vault

VAULT_PATH = get_obsidian_vault()
VAULT_PATH.mkdir(parents=True, exist_ok=True)

# Ensure .obsidian config folder exists
OBSIDIAN_CONFIG = VAULT_PATH / ".obsidian"
OBSIDIAN_CONFIG.mkdir(parents=True, exist_ok=True)
if not (OBSIDIAN_CONFIG / "app.json").exists():
    (OBSIDIAN_CONFIG / "app.json").write_text('{"livePreview": true, "showLineNumber": false, "spellcheck": false}', encoding="utf-8")

# Inicializar estructura
TEMPLATES_DIR = VAULT_PATH / "Templates"
DAILY_DIR = VAULT_PATH / "Daily"
CONCEPTS_DIR = VAULT_PATH / "Conceptos"
RESEARCH_DIR = VAULT_PATH / "Investigacion"
MEMORY_DIR = VAULT_PATH / "Memoria"
LOG_DIR = VAULT_PATH / "Logs"
PROJECTS_DIR = VAULT_PATH / "Proyectos"
LEARNING_DIR = VAULT_PATH / "Aprendizaje"
IDEAS_DIR = VAULT_PATH / "Ideas"
for d in [TEMPLATES_DIR, DAILY_DIR, CONCEPTS_DIR, RESEARCH_DIR, MEMORY_DIR, LOG_DIR, PROJECTS_DIR, LEARNING_DIR, IDEAS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

INDEX_FILE = VAULT_PATH / "_INDEX.md"


# ─── HELPERS ────────────────────────────────────────────────────────

def _frontmatter(data: dict) -> str:
    if not data:
        return ""
    lines = ["---"]
    for k, v in data.items():
        if isinstance(v, list):
            lines.append(f"{k}:")
            for item in v:
                lines.append(f"  - {item}")
        elif isinstance(v, str) and "\n" in v:
            lines.append(f'{k}: "{v}"')
        else:
            lines.append(f"{k}: {v}")
    lines.append("---\n")
    return "\n".join(lines) + "\n"


def _parse_frontmatter(content: str):
    if content.startswith("---"):
        end = content.find("---", 3)
        if end > 0:
            try:
                fm = yaml.safe_load(content[3:end])
                body = content[end + 3 :].strip()
                return fm or {}, body
            except Exception:
                pass
    return {}, content


def _wikilink(title: str, alias: str = None) -> str:
    if alias:
        return f"[[{title}|{alias}]]"
    return f"[[{title}]]"


def _slugify(text: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "", text).strip()[:100]


def _all_notes() -> list:
    notes = []
    for f in VAULT_PATH.rglob("*.md"):
        if f.name.startswith(".") or f.name.startswith("_"):
            continue
        notes.append(f.relative_to(VAULT_PATH))
    return notes


def _find_note(title: str) -> Path | None:
    filename = _slugify(title) + ".md"
    for f in VAULT_PATH.rglob("*.md"):
        if f.name.lower() == filename.lower() and not f.name.startswith("_"):
            return f
    return None


def _get_links(content: str) -> list:
    return re.findall(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", content)


def _get_backlinks(title: str) -> list:
    target = _slugify(title)
    results = []
    for f in VAULT_PATH.rglob("*.md"):
        if f.name.startswith(".") or f.name.startswith("_"):
            continue
        try:
            content = f.read_text(encoding="utf-8", errors="replace")
            if f"[[{target}" in content or f"[[{title}" in content:
                results.append(str(f.relative_to(VAULT_PATH)))
        except Exception:
            pass
    return results


def _summary(content: str, limit: int = 120) -> str:
    """Primer párrafo de texto plano de una nota (sin frontmatter ni markdown)."""
    _, body = _parse_frontmatter(content)
    # Descartar bloques YAML incrustados (appends repetidos con frontmatter)
    body = re.sub(r"---\s*\n(?:.*\n)*?---\s*\n?", " ", body)
    body = re.sub(r"\[\[[^\]|]+\|[^\]]+\]\]", "", body)  # [[link|alias]]
    body = re.sub(r"\[\[([^\]]+)\]\]", r"\1", body)        # [[link]] → link
    body = re.sub(r"```.*?```", " ", body, flags=re.S)      # code blocks
    body = re.sub(r"`[^`]*`", "", body)                     # inline code
    body = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", body)        # images
    body = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", body)    # md links
    body = re.sub(r"[#>*_~\-|]", " ", body)                 # markdown symbols
    body = re.sub(r"\s+", " ", body).strip()
    if not body:
        return ""
    return body[:limit].strip() + ("…" if len(body) > limit else "")


def _update_index():
    notes = _all_notes()
    tags_map = defaultdict(list)
    folders = defaultdict(list)
    summaries = {}
    backlinks_map = defaultdict(list)
    concepts = []
    daily = []
    memoria = []
    aprendizaje = []
    proyectos = []
    ideas = []
    other = []

    for note_path in notes:
        try:
            content = (VAULT_PATH / note_path).read_text(encoding="utf-8", errors="replace")
            fm, _ = _parse_frontmatter(content)
            summaries[note_path.stem] = _summary(content)
            tags = fm.get("tags", [])
            for t in tags:
                tags_map[t].append(note_path.stem)
            folder = str(note_path.parent) if note_path.parent != Path(".") else ""
            if folder:
                folders[folder].append(note_path.stem)
            if "Conceptos" in str(note_path):
                concepts.append(note_path.stem)
            elif "Daily" in str(note_path):
                daily.append(note_path.stem)
            elif "Memoria" in str(note_path):
                memoria.append(note_path.stem)
            elif "Aprendizaje" in str(note_path):
                aprendizaje.append(note_path.stem)
            elif "Proyectos" in str(note_path):
                proyectos.append(note_path.stem)
            elif "Ideas" in str(note_path):
                ideas.append(note_path.stem)
            else:
                other.append(note_path.stem)
        except Exception:
            pass

    total_links = 0
    for note_path in notes:
        try:
            content = (VAULT_PATH / note_path).read_text(encoding="utf-8", errors="replace")
            links = _get_links(content)
            total_links += len(links)
            for link, _ in links:
                backlinks_map[link].append(note_path.stem)
        except Exception:
            pass

    # Conexiones más fuertes: notas que más apuntan a otras y sus backlinks
    connected = sorted(
        [(stem, len(refs)) for stem, refs in backlinks_map.items() if refs],
        key=lambda x: -x[1],
    )[:15]

    def _line(stem: str) -> str:
        s = summaries.get(stem, "")
        if s:
            return f"- {_wikilink(stem)} — {s}"
        return f"- {_wikilink(stem)}"

    index = _frontmatter({
        "tags": ["index"],
        "updated": datetime.now().isoformat(),
        "total_notes": len(notes),
        "total_links": total_links,
    })
    index += "# 🧠 Base de Conocimiento de Eris\n\n"
    index += f"**{len(notes)} notas** | **{total_links} conexiones** | Actualizado: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"

    if concepts:
        index += "## 📚 Conceptos\n\n"
        for c in sorted(concepts):
            index += _line(c) + "\n"
        index += "\n"

    if daily:
        index += "## 📅 Diario\n\n"
        for d in sorted(daily, reverse=True)[:14]:
            index += _line(d) + "\n"
        index += "\n"

    if memoria:
        index += "## 🧠 Memoria\n\n"
        for m in sorted(memoria, reverse=True)[:10]:
            index += _line(m) + "\n"
        index += "\n"

    if aprendizaje:
        index += "## 📖 Aprendizaje\n\n"
        for a in sorted(aprendizaje):
            index += _line(a) + "\n"
        index += "\n"

    if proyectos:
        index += "## 🚧 Proyectos\n\n"
        for p in sorted(proyectos):
            index += _line(p) + "\n"
        index += "\n"

    if ideas:
        index += "## 💡 Ideas\n\n"
        for i in sorted(ideas):
            index += _line(i) + "\n"
        index += "\n"

    if other:
        index += "## 📝 Otras Notas\n\n"
        for o in sorted(other):
            index += _line(o) + "\n"
        index += "\n"

    if folders:
        index += "## 📂 Por Carpeta\n\n"
        for folder, items in sorted(folders.items()):
            index += f"### {folder}/\n"
            for item in sorted(items)[:10]:
                index += _line(item) + "\n"
            if len(items) > 10:
                index += f"  *(+{len(items)-10} más)*\n"
            index += "\n"

    if connected:
        index += "## 🔗 Conexiones (más referenciadas)\n\n"
        for stem, count in connected:
            refs = backlinks_map[stem]
            index += f"- {_wikilink(stem)} ← {count} nota(s): "
            index += ", ".join(_wikilink(r) for r in refs[:5])
            if len(refs) > 5:
                index += f" (+{len(refs)-5})"
            index += "\n"
        index += "\n"

    if tags_map:
        index += "## 🏷️ Tags\n\n"
        for tag, items in sorted(tags_map.items(), key=lambda x: -len(x[1])):
            index += f"- **#{tag}** ({len(items)}): {', '.join(_wikilink(i) for i in items[:8])}"
            if len(items) > 8:
                index += f" (+{len(items)-8})"
            index += "\n"

    INDEX_FILE.write_text(index, encoding="utf-8")


def _search_notes(query: str) -> list:
    results = []
    q = query.lower()
    for f in VAULT_PATH.rglob("*.md"):
        if f.name.startswith(".") or f.name.startswith("_"):
            continue
        try:
            content = f.read_text(encoding="utf-8", errors="replace")
            if q in content.lower() or q in f.stem.lower():
                fm, body = _parse_frontmatter(content)
                idx = content.lower().find(q)
                ctx = (
                    content[max(0, idx - 40) : idx + len(q) + 40].replace("\n", " ")
                    if idx >= 0
                    else f.stem
                )
                results.append({
                    "path": str(f.relative_to(VAULT_PATH)),
                    "title": f.stem,
                    "tags": fm.get("tags", []),
                    "context": f"...{ctx}...",
                })
        except Exception:
            pass
    return results


def _open_in_obsidian(note_path: str = ""):
    """Launch Obsidian to the vault, optionally to a specific note."""
    encoded = VAULT_PATH.as_posix()
    if note_path:
        uri = f"obsidian://open?vault={encoded}&file={note_path.replace('\\','/')}"
    else:
        uri = f"obsidian://open?vault={encoded}"
    try:
        os.startfile(uri)
        return True
    except Exception:
        return False


# ─── MAIN FUNCTION ──────────────────────────────────────────────────

def obsidian_note(parameters: dict, player=None) -> str:
    """
    Integración con Obsidian – segundo cerebro de Eris.

    Acciones:
      write          Crear/actualizar nota
      read           Leer nota
      search         Buscar texto en todas las notas
      daily          Crear/actualizar nota diaria
      link           Vincular dos notas con [[wikilink]]
      delete         Eliminar o mover a papelera una nota
      rename         Renombrar nota y actualizar todos los [[wikilinks]] en el vault
      backlinks      Mostrar qué notas apuntan a esta
      graph          Devolver grafo de nodos y conexiones (JSON)
      append         Agregar contenido al final de una nota
      update_fm      Actualizar campos de YAML frontmatter
      browse         Listar notas en una carpeta
      search_tags    Buscar notas por etiqueta(s)
      open           Abrir Obsidian en el vault o nota específica
      index          Mostrar el índice del vault
      wiki           Wiki curada: índice con resúmenes + conexiones/backlinks
      tags           Listar todas las etiquetas
      concepts       Extraer conceptos clave de un texto y crear notas
    """
    action = parameters.get("action", "index").lower()

    # ─── WRITE ──────────────────────────────────────────────────────
    if action == "write":
        title = parameters.get("title", "")
        content = parameters.get("content", "")
        tags_str = parameters.get("tags", "")
        folder = parameters.get("folder", "")
        if not title:
            return "Error: Se requiere 'title'."
        filename = _slugify(title) + ".md"
        target_dir = VAULT_PATH / folder if folder else VAULT_PATH
        target_dir.mkdir(parents=True, exist_ok=True)
        filepath = target_dir / filename
        tags = [t.strip() for t in tags_str.split(",") if t.strip()] if tags_str else []
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        fm = {"title": title, "created": now_str, "tags": tags}
        if filepath.exists():
            _, existing_body = _parse_frontmatter(filepath.read_text(encoding="utf-8"))
            fm["updated"] = now_str
            content = existing_body + "\n\n---\n\n" + content
        full_content = _frontmatter(fm) + content
        filepath.write_text(full_content, encoding="utf-8")
        _update_index()
        return f"📝 Nota **{title}** guardada en {filepath.relative_to(VAULT_PATH)}"

    # ─── READ ───────────────────────────────────────────────────────
    elif action == "read":
        title = parameters.get("title", "")
        if not title:
            return "Error: Se requiere 'title'."
        found = _find_note(title)
        if not found:
            return f"❌ Nota '{title}' no encontrada."
        content = found.read_text(encoding="utf-8", errors="replace")
        fm, body = _parse_frontmatter(content)
        result = f"📄 **{title}**\n"
        if fm:
            tags = ", ".join(f"#{t}" for t in fm.get("tags", []))
            created = fm.get("created", "?")
            updated = fm.get("updated", "")
            result += f"   Tags: {tags}\n   Creado: {created}"
            if updated:
                result += f" | Actualizado: {updated}"
            result += "\n\n"
        result += body[:2000]
        if len(body) > 2000:
            result += f"\n...(*truncado, {len(body)} chars total*)"
        return result

    # ─── SEARCH ─────────────────────────────────────────────────────
    elif action == "search":
        query = parameters.get("query", "")
        if not query:
            return "Error: Se requiere 'query'."
        results = _search_notes(query)
        if not results:
            return f"🔍 Sin resultados para '{query}'."
        response = f"🔍 **{len(results)} resultados para '{query}':**\n\n"
        for r in results[:10]:
            response += f"- {_wikilink(r['title'])}"
            if r.get("tags"):
                response += f"  `{' '.join('#' + t for t in r['tags'])}`"
            response += f"\n  {r['context']}\n\n"
        return response

    # ─── DAILY ──────────────────────────────────────────────────────
    elif action == "daily":
        content = parameters.get("content", "")
        today = datetime.now().strftime("%Y-%m-%d")
        today_title = datetime.now().strftime("%A %d %B %Y")
        filename = f"{today}.md"
        filepath = DAILY_DIR / filename
        if filepath.exists():
            existing = filepath.read_text(encoding="utf-8", errors="replace")
            fm, body = _parse_frontmatter(existing)
            body += f"\n\n{datetime.now().strftime('%H:%M')}\n{content}"
        else:
            body = f"# {today_title}\n\n{content}"
        fm = {"date": today, "day": datetime.now().strftime("%A"), "tags": ["daily"]}
        filepath.write_text(_frontmatter(fm) + body, encoding="utf-8")
        _update_index()
        return f"📅 Nota diaria actualizada: {today}"

    # ─── LINK ───────────────────────────────────────────────────────
    elif action == "link":
        from_title = parameters.get("from_title", "")
        to_title = parameters.get("to_title", "")
        if not from_title or not to_title:
            return "Error: Se requieren 'from_title' y 'to_title'."
        from_file = _find_note(from_title)
        if not from_file:
            return f"❌ Nota origen '{from_title}' no encontrada."
        content = from_file.read_text(encoding="utf-8", errors="replace")
        link = _wikilink(to_title)
        if f"[[{_slugify(to_title)}" in content or f"[[{to_title}" in content:
            return f"🔗 El vínculo {from_title} → {to_title} ya existe."
        content += f"\n\n**Ver también:** {link}"
        from_file.write_text(content, encoding="utf-8")
        _update_index()
        return f"🔗 Vinculado: {from_title} → {to_title}"

    # ─── DELETE ─────────────────────────────────────────────────────
    elif action == "delete":
        title = parameters.get("title", "")
        if not title:
            return "Error: Se requiere 'title'."
        found = _find_note(title)
        if not found:
            return f"❌ Nota '{title}' no encontrada."
        backlinks = _get_backlinks(title)
        trash = VAULT_PATH / ".trash"
        trash.mkdir(exist_ok=True)
        dest = trash / found.name
        found.rename(dest)
        _update_index()
        msg = f"🗑️ Nota **{title}** movida a la papelera."
        if backlinks:
            msg += f"\n⚠️ **{len(backlinks)} nota(s)** aún apuntan a esta: {', '.join(b.replace('.md','') for b in backlinks[:5])}"
        return msg

    # ─── RENAME ─────────────────────────────────────────────────────
    elif action == "rename":
        old = parameters.get("title", "")
        new = parameters.get("new_title", "")
        if not old or not new:
            return "Error: Se requieren 'title' (actual) y 'new_title' (nuevo)."
        found = _find_note(old)
        if not found:
            return f"❌ Nota '{old}' no encontrada."
        new_filename = _slugify(new) + ".md"
        new_path = found.parent / new_filename
        if new_path.exists():
            return f"❌ Ya existe una nota llamada '{new}'."
        # Renombrar archivo
        found.rename(new_path)
        # Actualizar [[wikilinks]] en todo el vault
        old_slug = _slugify(old)
        new_slug = _slugify(new)
        updated_count = 0
        for f in VAULT_PATH.rglob("*.md"):
            if f.name.startswith("."):
                continue
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
                # [[old]] → [[new]], [[old|alias]] → [[new|alias]]
                new_text = re.sub(
                    rf"\[\[{re.escape(old_slug)}(\|[^\]]+)?\]\]",
                    lambda m: f"[[{new_slug}{m.group(1) if m.group(1) else ''}]]",
                    text,
                )
                new_text = re.sub(
                    rf"\[\[{re.escape(old)}(\|[^\]]+)?\]\]",
                    lambda m: f"[[{new}{m.group(1) if m.group(1) else ''}]]",
                    new_text,
                )
                if new_text != text:
                    f.write_text(new_text, encoding="utf-8")
                    updated_count += 1
            except Exception:
                pass
        _update_index()
        msg = f"✏️ Nota **{old}** renombrada a **{new}**."
        if updated_count:
            msg += f"\n🔄 {updated_count} nota(s) actualizadas con el nuevo nombre."
        return msg

    # ─── BACKLINKS ──────────────────────────────────────────────────
    elif action == "backlinks":
        title = parameters.get("title", "")
        if not title:
            return "Error: Se requiere 'title'."
        found = _find_note(title)
        if not found:
            return f"❌ Nota '{title}' no encontrada."
        backlinks = _get_backlinks(title)
        if not backlinks:
            return f"🔗 Ninguna nota apunta a **{title}**."
        # Show context snippets
        result = f"🔗 **{len(backlinks)} nota(s) apuntan a '{title}':**\n\n"
        for bl in backlinks[:15]:
            try:
                text = (VAULT_PATH / bl).read_text(encoding="utf-8", errors="replace")
                idx = text.lower().find(_slugify(title).lower())
                if idx < 0:
                    idx = text.lower().find(title.lower())
                ctx = text[max(0, idx - 50) : idx + len(title) + 50].replace("\n", " ") if idx >= 0 else ""
                result += f"- {_wikilink(bl.replace('.md',''))}: `...{ctx}...`\n"
            except Exception:
                result += f"- {_wikilink(bl.replace('.md',''))}\n"
        if len(backlinks) > 15:
            result += f"\n*y {len(backlinks)-15} más*"
        return result

    # ─── GRAPH ──────────────────────────────────────────────────────
    elif action == "graph":
        title = parameters.get("title", "")
        max_notes = int(parameters.get("max_notes", 200))
        if title:
            result = _graph_around(title, max_notes)
        else:
            result = _graph_full(max_notes)
        return result

    # ─── APPEND ─────────────────────────────────────────────────────
    elif action == "append":
        title = parameters.get("title", "")
        content = parameters.get("content", "")
        if not title or not content:
            return "Error: Se requieren 'title' y 'content'."
        found = _find_note(title)
        if not found:
            return f"❌ Nota '{title}' no encontrada."
        text = found.read_text(encoding="utf-8", errors="replace")
        fm, body = _parse_frontmatter(text)
        # Rebuild
        new_text = _frontmatter(fm) + body + "\n\n" + content
        found.write_text(new_text, encoding="utf-8")
        _update_index()
        return f"✏️ Contenido agregado a **{title}**."

    # ─── UPDATE FRONTMATTER ─────────────────────────────────────────
    elif action == "update_fm":
        title = parameters.get("title", "")
        field = parameters.get("field", "")
        value = parameters.get("value", "")
        if not title or not field:
            return "Error: Se requieren 'title' y 'field'."
        found = _find_note(title)
        if not found:
            return f"❌ Nota '{title}' no encontrada."
        text = found.read_text(encoding="utf-8", errors="replace")
        fm, body = _parse_frontmatter(text)
        # Parse value
        if value.startswith("[") and value.endswith("]"):
            try:
                fm[field] = json.loads(value)
            except Exception:
                fm[field] = [v.strip() for v in value[1:-1].split(",") if v.strip()]
        elif value.lower() in ("true", "false"):
            fm[field] = value.lower() == "true"
        elif value.isdigit():
            fm[field] = int(value)
        else:
            fm[field] = value
        new_text = _frontmatter(fm) + body
        found.write_text(new_text, encoding="utf-8")
        _update_index()
        return f"🏷️ Frontmatter de **{title}** actualizado: `{field} = {value}`"

    # ─── BROWSE ─────────────────────────────────────────────────────
    elif action == "browse":
        folder = parameters.get("folder", "")
        target = VAULT_PATH / folder if folder else VAULT_PATH
        if not target.exists() or not target.is_dir():
            return f"❌ Carpeta '{folder}' no encontrada."
        notes = sorted(target.glob("*.md"))
        subdirs = sorted(d for d in target.iterdir() if d.is_dir() and not d.name.startswith("."))
        result = f"📂 **{folder or '/'}** — {len(notes)} nota(s), {len(subdirs)} subcarpeta(s)\n\n"
        if subdirs:
            result += "**Carpetas:**\n"
            for d in subdirs:
                child_count = len(list(d.glob("*.md")))
                result += f"- 📁 {d.name}/ ({child_count} notas)\n"
            result += "\n"
        if notes:
            result += "**Notas:**\n"
            for n in notes:
                result += f"- {_wikilink(n.stem)}\n"
        if not notes and not subdirs:
            result += "*(vacía)*\n"
        return result

    # ─── SEARCH TAGS ────────────────────────────────────────────────
    elif action == "search_tags":
        query = parameters.get("query", "")
        if not query:
            return "Error: Se requiere 'query' (tag a buscar)."
        q = query.lower().lstrip("#")
        results = []
        for f in VAULT_PATH.rglob("*.md"):
            if f.name.startswith(".") or f.name.startswith("_"):
                continue
            try:
                fm, _ = _parse_frontmatter(f.read_text(encoding="utf-8", errors="replace"))
                tags = [t.lower() for t in fm.get("tags", [])]
                if any(q in t for t in tags):
                    results.append((f.stem, [t for t in fm.get("tags", []) if q in t.lower()]))
            except Exception:
                pass
        if not results:
            return f"🏷️ No hay notas con tag que contenga '{query}'."
        result = f"🏷️ **{len(results)} nota(s)** con tag '{query}':\n\n"
        for name, matched in sorted(results):
            result += f"- {_wikilink(name)}  `{' '.join('#'+t for t in matched)}`\n"
        return result

    # ─── OPEN IN OBSIDIAN ───────────────────────────────────────────
    elif action == "open":
        title = parameters.get("title", "")
        if title:
            found = _find_note(title)
            if found:
                rel = found.relative_to(VAULT_PATH)
                ok = _open_in_obsidian(str(rel).replace("\\", "/").replace(".md", ""))
            else:
                ok = _open_in_obsidian()
                _open_in_obsidian()
                return f"❌ Nota '{title}' no encontrada. Abrí el vault."
        else:
            ok = _open_in_obsidian()
        return "📂 Obsidian abierto en el vault de Eris." if ok else "⚠️ No se pudo abrir Obsidian."

    # ─── INDEX ──────────────────────────────────────────────────────
    elif action == "index":
        _update_index()
        content = INDEX_FILE.read_text(encoding="utf-8", errors="replace")
        return content[:2500]

    # ─── WIKI ───────────────────────────────────────────────────────
    elif action == "wiki":
        _update_index()
        content = INDEX_FILE.read_text(encoding="utf-8", errors="replace")
        header, _, body = content.partition("\n\n")
        # Compacto: solo resúmenes + conexiones, sin lista duplicada de carpetas
        compact = [header, body.split("## 📂 Por Carpeta")[0], body.split("## 📂 Por Carpeta")[-1].split("## 🏷️ Tags")[0]]
        return "\n\n".join(compact)[:3000]

    # ─── TAGS ───────────────────────────────────────────────────────
    elif action == "tags":
        tags = defaultdict(list)
        for f in VAULT_PATH.rglob("*.md"):
            if f.name.startswith(".") or f.name.startswith("_"):
                continue
            try:
                fm, _ = _parse_frontmatter(f.read_text(encoding="utf-8", errors="replace"))
                for t in fm.get("tags", []):
                    tags[t].append(f.stem)
            except Exception:
                pass
        if not tags:
            return "🏷️ No hay tags en el vault aún."
        result = "**🏷️ Tags en el vault:**\n\n"
        for tag, notes in sorted(tags.items(), key=lambda x: -len(x[1])):
            result += f"- **#{tag}** ({len(notes)}): {', '.join(notes[:8])}"
            if len(notes) > 8:
                result += f" +{len(notes)-8} más"
            result += "\n"
        return result

    # ─── CONCEPTS ───────────────────────────────────────────────────
    elif action == "concepts":
        text = parameters.get("text", "")
        source_title = parameters.get("source_title", "Investigacion")
        if not text:
            return "Error: Se requiere 'text' para extraer conceptos."
        lines = text.split("\n")
        concepts_found = []
        for line in lines:
            if ":" in line:
                term = line.split(":")[0].strip()
                if 3 < len(term) < 60 and not term.startswith("http"):
                    concepts_found.append(term)
            capitalized = re.findall(
                r"\b[A-Z][a-záéíóúñ]{2,}(?:\s[A-Z][a-záéíóúñ]{2,}){0,2}\b", line
            )
            concepts_found.extend(capitalized)
        unique = list(dict.fromkeys(concepts_found))[:10]
        if not unique:
            return "No se encontraron conceptos clave para extraer."
        created = []
        for concept in unique[:5]:
            note_title = concept.strip()
            filepath = CONCEPTS_DIR / f"{_slugify(note_title)}.md"
            if not filepath.exists():
                fm = {
                    "tags": ["concepto"],
                    "source": source_title,
                    "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
                }
                filepath.write_text(
                    _frontmatter(fm)
                    + f"# {note_title}\n\n*Extraído de {_wikilink(source_title)}*\n\nPendiente de desarrollar.",
                    encoding="utf-8",
                )
                created.append(note_title)
        source_file = _find_note(source_title)
        if source_file:
            sc = source_file.read_text(encoding="utf-8", errors="replace")
            if "## Conceptos Relacionados" not in sc:
                sc += "\n\n## Conceptos Relacionados\n"
                for c in unique[:5]:
                    sc += f"- {_wikilink(c)}\n"
                source_file.write_text(sc, encoding="utf-8")
        _update_index()
        return (
            f"🧠 **{len(created)} conceptos extraídos:**\n"
            + "\n".join(f"- {_wikilink(c)}" for c in created[:10])
        )

    return (
        f"Acción '{action}' no reconocida. "
        "Usa: write, read, search, daily, link, delete, rename, backlinks, "
        "graph, append, update_fm, browse, search_tags, open, index, wiki, tags, concepts"
    )


# ─── GRAPH HELPERS ─────────────────────────────────────────────────

def _graph_full(max_notes: int = 200) -> str:
    """Full knowledge graph – all nodes and edges."""
    nodes = []
    edges = set()
    count = 0
    for f in VAULT_PATH.rglob("*.md"):
        if f.name.startswith(".") or f.name.startswith("_"):
            continue
        if count >= max_notes:
            break
        try:
            rel = f.relative_to(VAULT_PATH)
            fm, body = _parse_frontmatter(f.read_text(encoding="utf-8", errors="replace"))
            nodes.append({"id": f.stem, "path": str(rel), "tags": fm.get("tags", [])})
            links = _get_links(body)
            for link, _ in links:
                edges.add((f.stem, link))
            count += 1
        except Exception:
            pass
    return json.dumps(
        {"nodes": nodes, "edges": [{"source": s, "target": t} for s, t in edges]},
        indent=2,
        ensure_ascii=False,
    )


def _graph_around(title: str, max_notes: int = 50) -> str:
    """Subgraph centered on a specific note (BFS up to 2 hops)."""
    found = _find_note(title)
    if not found:
        return json.dumps({"error": f"Nota '{title}' no encontrada"})
    # BFS
    visited = {found.stem}
    queue = [(found.stem, 0)]
    edges = set()
    nodes = []
    while queue and len(nodes) < max_notes:
        current, depth = queue.pop(0)
        cf = _find_note(current)
        if not cf:
            continue
        try:
            fm, body = _parse_frontmatter(cf.read_text(encoding="utf-8", errors="replace"))
            nodes.append({"id": current, "depth": depth, "tags": fm.get("tags", [])})
            links = _get_links(body)
            for link, _ in links:
                edges.add((current, link))
                if link not in visited and depth < 2:
                    visited.add(link)
                    queue.append((link, depth + 1))
                elif link not in visited:
                    visited.add(link)
        except Exception:
            pass
    # Also pull backlinks
    for bl_path in _get_backlinks(title):
        bl = Path(bl_path).stem
        if bl not in visited and len(nodes) < max_notes:
            visited.add(bl)
            try:
                bf = _find_note(bl)
                if bf:
                    fm, _ = _parse_frontmatter(bf.read_text(encoding="utf-8", errors="replace"))
                    nodes.append({"id": bl, "depth": -1, "tags": fm.get("tags", [])})
                    edges.add((bl, found.stem))
            except Exception:
                pass
    return json.dumps(
        {"nodes": nodes, "edges": [{"source": s, "target": t} for s, t in edges]},
        indent=2,
        ensure_ascii=False,
    )
