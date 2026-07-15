# -*- coding: utf-8 -*-
"""
Eris ↔ Obsidian Integration – Segundo cerebro interconectado.
Lee, escribe, busca y conecta notas Markdown con [[wikilinks]] y YAML frontmatter.
"""
import json
import re
import yaml
from pathlib import Path
from datetime import datetime
from collections import defaultdict

VAULT_PATH = Path(r"D:\Eris_NEW\BaseDatosObsidian\BaseObsiEris")
VAULT_PATH.mkdir(parents=True, exist_ok=True)

# Ensure .obsidian config folder exists (tells Obsidian this is a vault)
OBSIDIAN_CONFIG = VAULT_PATH / ".obsidian"
OBSIDIAN_CONFIG.mkdir(parents=True, exist_ok=True)
(OBSIDIAN_CONFIG / "app.json").write_text('{\n  "livePreview": true,\n  "showLineNumber": false,\n  "spellcheck": false\n}', encoding="utf-8")
(OBSIDIAN_CONFIG / "appearance.json").write_text('{\n  "theme": "obsidian"\n}', encoding="utf-8")

# Inicializar estructura
TEMPLATES_DIR = VAULT_PATH / "Templates"
DAILY_DIR = VAULT_PATH / "Daily"
CONCEPTS_DIR = VAULT_PATH / "Conceptos"
RESEARCH_DIR = VAULT_PATH / "Investigacion"
MEMORY_DIR = VAULT_PATH / "Memoria"
LOG_DIR = VAULT_PATH / "Logs"
for d in [TEMPLATES_DIR, DAILY_DIR, CONCEPTS_DIR, RESEARCH_DIR, MEMORY_DIR, LOG_DIR]:
    d.mkdir(parents=True, exist_ok=True)

INDEX_FILE = VAULT_PATH / "_INDEX.md"

def _frontmatter(data: dict) -> str:
    """Generate YAML frontmatter string."""
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
    """Parse YAML frontmatter from markdown content."""
    if content.startswith("---"):
        end = content.find("---", 3)
        if end > 0:
            try:
                fm = yaml.safe_load(content[3:end])
                body = content[end+3:].strip()
                return fm or {}, body
            except:
                pass
    return {}, content

def _wikilink(title: str, alias: str = None) -> str:
    """Create Obsidian [[wikilink]]."""
    if alias:
        return f"[[{title}|{alias}]]"
    return f"[[{title}]]"

def _slugify(text: str) -> str:
    """Convert text to filename-safe slug."""
    return re.sub(r'[<>:"/\\|?*]', '', text).strip()[:100]

def _all_notes() -> list:
    """List all .md files in vault."""
    notes = []
    for f in VAULT_PATH.rglob("*.md"):
        if f.name.startswith(".") or f.name.startswith("_"):
            continue
        if f.suffix == ".md":
            notes.append(f.relative_to(VAULT_PATH))
    return notes

def _search_notes(query: str) -> list:
    """Search all notes for a query string."""
    results = []
    q = query.lower()
    for f in VAULT_PATH.rglob("*.md"):
        if f.name.startswith(".") or f.name.startswith("_"):
            continue
        try:
            content = f.read_text(encoding="utf-8", errors="replace")
            if q in content.lower() or q in f.stem.lower():
                fm, body = _parse_frontmatter(content)
                # Find context around match
                idx = content.lower().find(q)
                ctx = content[max(0,idx-40):idx+len(q)+40].replace("\n", " ") if idx >= 0 else f.stem
                results.append({
                    "path": str(f.relative_to(VAULT_PATH)),
                    "title": f.stem,
                    "tags": fm.get("tags", []),
                    "context": f"...{ctx}..."
                })
        except:
            pass
    return results

def _get_links(content: str) -> list:
    """Extract all [[wikilinks]] from content."""
    return re.findall(r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]', content)

def _update_index():
    """Regenerate the vault index file."""
    notes = _all_notes()
    tags_map = defaultdict(list)
    concepts = []
    daily = []
    other = []
    
    for note_path in notes:
        try:
            content = (VAULT_PATH / note_path).read_text(encoding="utf-8", errors="replace")
            fm, _ = _parse_frontmatter(content)
            tags = fm.get("tags", [])
            for t in tags:
                tags_map[t].append(note_path.stem)
            if "Conceptos" in str(note_path):
                concepts.append(note_path.stem)
            elif "Daily" in str(note_path):
                daily.append(note_path.stem)
            else:
                other.append(note_path.stem)
        except:
            pass
    
    index = _frontmatter({
        "tags": ["index"],
        "updated": datetime.now().isoformat(),
        "total_notes": len(notes)
    })
    index += "# 🧠 Base de Conocimiento de Eris\n\n"
    index += f"**{len(notes)} notas** | Actualizado: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n"
    
    if concepts:
        index += "## 📚 Conceptos\n\n"
        for c in sorted(concepts):
            index += f"- {_wikilink(c)}\n"
        index += "\n"
    
    if daily:
        index += "## 📅 Diario\n\n"
        for d in sorted(daily, reverse=True)[:7]:
            index += f"- {_wikilink(d)}\n"
        index += "\n"
    
    if other:
        index += "## 📝 Notas\n\n"
        for o in sorted(other):
            index += f"- {_wikilink(o)}\n"
        index += "\n"
    
    if tags_map:
        index += "## Tags\n\n"
        for tag, items in sorted(tags_map.items(), key=lambda x: str(x[0])):
            index += f"- **#{tag}**: {', '.join(_wikilink(i) for i in items[:5])}"
            if len(items) > 5:
                index += f" (+{len(items)-5})"
            index += "\n"
    
    INDEX_FILE.write_text(index, encoding="utf-8")

def obsidian_note(parameters: dict, player=None) -> str:
    """
    Integración con Obsidian – segundo cerebro de Eris.
    
    Acciones:
      - write: Crear/actualizar una nota en el vault
        Parámetros: title, content, tags (opcional, separados por coma), folder (opcional)
      - read: Leer una nota del vault
        Parámetros: title
      - search: Buscar en todas las notas
        Parámetros: query
      - daily: Crear nota diaria con resumen
        Parámetros: content (opcional)
      - link: Vincular dos notas entre sí
        Parámetros: from_title, to_title
      - index: Ver el índice del vault
      - tags: Ver todas las tags y sus notas
      - concepts: Extraer conceptos clave de un texto y crear notas interconectadas
        Parámetros: text, source_title
    """
    action = parameters.get("action", "index").lower()
    
    if action == "write":
        title = parameters.get("title", "")
        content = parameters.get("content", "")
        tags_str = parameters.get("tags", "")
        folder = parameters.get("folder", "")
        
        if not title:
            return "Error: Se requiere 'title'."
        
        filename = _slugify(title) + ".md"
        
        if folder:
            target_dir = VAULT_PATH / folder
        else:
            target_dir = VAULT_PATH
        target_dir.mkdir(parents=True, exist_ok=True)
        
        filepath = target_dir / filename
        
        tags = [t.strip() for t in tags_str.split(",") if t.strip()] if tags_str else []
        fm = {
            "title": title,
            "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "tags": tags
        }
        
        # Check if note exists to update
        if filepath.exists():
            _, existing_body = _parse_frontmatter(filepath.read_text(encoding="utf-8"))
            fm["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            content = existing_body + "\n\n" + content
        
        full_content = _frontmatter(fm) + content
        filepath.write_text(full_content, encoding="utf-8")
        _update_index()
        
        return f"📝 Nota creada: **{title}** ({filename}) en {filepath.relative_to(VAULT_PATH)}"
    
    elif action == "read":
        title = parameters.get("title", "")
        if not title:
            return "Error: Se requiere 'title'."
        
        filename = _slugify(title) + ".md"
        found = None
        for f in VAULT_PATH.rglob("*.md"):
            if f.name.lower() == filename.lower() and not f.name.startswith("_"):
                found = f
                break
        
        if not found:
            return f"❌ Nota '{title}' no encontrada en el vault."
        
        content = found.read_text(encoding="utf-8", errors="replace")
        fm, body = _parse_frontmatter(content)
        
        result = f"📄 **{title}**\n\n"
        if fm:
            result += f"Tags: {', '.join(fm.get('tags', []))}\n"
            result += f"Creado: {fm.get('created', '?')}\n"
        result += f"\n{body[:1500]}"
        if len(body) > 1500:
            result += f"\n...(truncado, {len(body)} chars total)"
        
        return result
    
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
                response += f"  `{' '.join('#'+t for t in r['tags'])}`"
            response += f"\n  {r['context']}\n\n"
        
        return response
    
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
        
        fm = {
            "date": today,
            "day": datetime.now().strftime("%A"),
            "tags": ["daily"]
        }
        filepath.write_text(_frontmatter(fm) + body, encoding="utf-8")
        _update_index()
        
        return f"📅 Nota diaria actualizada: {today}"
    
    elif action == "link":
        from_title = parameters.get("from_title", "")
        to_title = parameters.get("to_title", "")
        
        if not from_title or not to_title:
            return "Error: Se requieren 'from_title' y 'to_title'."
        
        from_file = None
        for f in VAULT_PATH.rglob("*.md"):
            if f.stem.lower() == _slugify(from_title).lower():
                from_file = f
                break
        
        if not from_file:
            return f"❌ Nota origen '{from_title}' no encontrada."
        
        content = from_file.read_text(encoding="utf-8", errors="replace")
        link = _wikilink(to_title)
        
        if f"[[{to_title}" in content:
            return f"🔗 El vínculo {from_title} → {to_title} ya existe."
        
        content += f"\n\n**Ver también:** {link}"
        from_file.write_text(content, encoding="utf-8")
        
        return f"🔗 Vinculado: {from_title} → {to_title}"
    
    elif action == "index":
        _update_index()
        content = INDEX_FILE.read_text(encoding="utf-8", errors="replace")
        return content[:2000]
    
    elif action == "tags":
        tags = defaultdict(list)
        for f in VAULT_PATH.rglob("*.md"):
            if f.name.startswith(".") or f.name.startswith("_"):
                continue
            try:
                fm, _ = _parse_frontmatter(f.read_text(encoding="utf-8", errors="replace"))
                for t in fm.get("tags", []):
                    tags[t].append(f.stem)
            except:
                pass
        
        if not tags:
            return "🏷️ No hay tags en el vault aún."
        
        result = "**🏷️ Tags en el vault:**\n\n"
        for tag, notes in sorted(tags.items(), key=lambda x: -len(x[1])):
            result += f"- **#{tag}** ({len(notes)}): {', '.join(notes[:5])}"
            if len(notes) > 5:
                result += f" +{len(notes)-5} más"
            result += "\n"
        
        return result
    
    elif action == "concepts":
        text = parameters.get("text", "")
        source_title = parameters.get("source_title", "Investigacion")
        
        if not text:
            return "Error: Se requiere 'text' para extraer conceptos."
        
        # Extraer frases clave (líneas con sustantivos propios, términos técnicos)
        lines = text.split("\n")
        concepts_found = []
        
        # Buscar términos en mayúsculas, entre comillas, o tras ":" 
        for line in lines:
            # Términos después de :
            if ":" in line:
                term = line.split(":")[0].strip()
                if 3 < len(term) < 60 and not term.startswith("http"):
                    concepts_found.append(term)
            
            # Palabras con mayúscula (posibles nombres propios)
            capitalized = re.findall(r'\b[A-Z][a-záéíóúñ]{2,}(?:\s[A-Z][a-záéíóúñ]{2,}){0,2}\b', line)
            concepts_found.extend(capitalized)
        
        # Deduplicar y limitar
        unique = list(dict.fromkeys(concepts_found))[:10]
        
        if not unique:
            return "No se encontraron conceptos clave para extraer."
        
        # Crear notas para cada concepto y vincularlas
        created = []
        for concept in unique[:5]:
            note_title = concept.strip()
            filepath = CONCEPTS_DIR / f"{_slugify(note_title)}.md"
            
            if not filepath.exists():
                fm = {
                    "tags": ["concepto"],
                    "source": source_title,
                    "created": datetime.now().strftime("%Y-%m-%d %H:%M")
                }
                filepath.write_text(
                    _frontmatter(fm) + f"# {note_title}\n\n*Extraído de {_wikilink(source_title)}*\n\nPendiente de desarrollar.",
                    encoding="utf-8"
                )
                created.append(note_title)
        
        # Vincular la nota fuente con los conceptos
        source_file = None
        for f in VAULT_PATH.rglob("*.md"):
            if f.stem.lower() == _slugify(source_title).lower():
                source_file = f
                break
        
        if source_file:
            sc = source_file.read_text(encoding="utf-8", errors="replace")
            if "## Conceptos Relacionados" not in sc:
                sc += "\n\n## Conceptos Relacionados\n"
                for c in unique[:5]:
                    sc += f"- {_wikilink(c)}\n"
                source_file.write_text(sc, encoding="utf-8")
        
        _update_index()
        return f"🧠 **{len(created)} conceptos extraídos:**\n" + "\n".join(f"- {_wikilink(c)}" for c in created[:10])
    
    return f"Acción '{action}' no reconocida. Usa: write, read, search, daily, link, index, tags, concepts"
