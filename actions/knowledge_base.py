"""Base de conocimiento local con ChromaDB vectorial."""
import hashlib
import json
import time
from pathlib import Path


_BASE = Path(__file__).resolve().parent.parent
_DB_DIR = _BASE / "data" / "knowledge_base"
_ENTRIES_FILE = _DB_DIR / "entries.json"
_EMBED_DIM = 384


def _ensure_dirs():
    _DB_DIR.mkdir(parents=True, exist_ok=True)


def _normalize_dim(vec: list[float], target: int = _EMBED_DIM) -> list[float]:
    n = len(vec)
    if n == target:
        return vec
    if n > target:
        step = n / target
        out = []
        for i in range(target):
            start = int(i * step)
            end = max(start + 1, int((i + 1) * step))
            chunk = vec[start:end]
            out.append(sum(chunk) / len(chunk))
        return out
    return vec + [0.0] * (target - n)


def _get_embedding(text: str) -> list[float]:
    try:
        import httpx
        cfg_path = _BASE / "config" / "api_keys.json"
        cfg = json.loads(cfg_path.read_text()) if cfg_path.exists() else {}
        base_url = cfg.get("ollama_base_url", "http://localhost:11434")
        model = cfg.get("ollama_embed_model", "nomic-embed-text")
        with httpx.Client(timeout=30) as client:
            resp = client.post(
                f"{base_url}/api/embeddings",
                json={"model": model, "prompt": text[:8192]},
            )
            resp.raise_for_status()
            return _normalize_dim(resp.json()["embedding"])
    except Exception:
        import numpy as np
        h = hashlib.sha256(text.encode()).digest()
        seed = int.from_bytes(h[:4], "big")
        rng = np.random.RandomState(seed)
        return rng.randn(_EMBED_DIM).tolist()


def _get_chroma():
    # chromadb es OPCIONAL: si no esta, degrada a "no disponible" en vez
    # de crashear el arranque del GUI (patron de deps opcionales de AGENTS).
    try:
        import chromadb
    except Exception:
        raise RuntimeError("chromadb no instalado (pip install chromadb)")
    _ensure_dirs()
    client = chromadb.PersistentClient(path=str(_DB_DIR))
    return client.get_or_create_collection(
        name="knowledge_base",
        metadata={"hnsw:space": "cosine"},
    )


def _load_entries() -> dict:
    if _ENTRIES_FILE.exists():
        try:
            return json.loads(_ENTRIES_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_entries(entries: dict):
    _ensure_dirs()
    _ENTRIES_FILE.write_text(json.dumps(entries, indent=2, ensure_ascii=False), encoding="utf-8")


def _generate_id(title: str) -> str:
    raw = f"{title}_{time.time_ns()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


def knowledge_base(parameters: dict = None, player=None) -> str:
    """Gestiona la base de conocimiento personal con búsqueda semántica."""
    try:
        return _kb_entry(parameters, player)
    except RuntimeError as e:
        return f"Knowledge Base no disponible: {e}"
    except Exception as e:
        return f"Error en Knowledge Base: {e}"


def _kb_entry(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = params.get("action", "search")

    if action in ("add", "save", "store"):
        title = (params.get("title") or "").strip()
        content = (params.get("content") or "").strip()
        if not title or not content:
            return "Falta 'title' y 'content' para guardar."
        entry_type = params.get("type", "note")
        tags = [t.strip() for t in params.get("tags", "").split(",") if t.strip()]

        entry_id = _generate_id(title)
        text_for_embed = f"{title}\n{content}"
        embedding = _get_embedding(text_for_embed)

        entry = {
            "id": entry_id,
            "title": title,
            "content": content,
            "type": entry_type,
            "tags": tags,
            "created": time.strftime("%Y-%m-%d %H:%M:%S"),
            "updated": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        collection = _get_chroma()
        collection.add(
            ids=[entry_id],
            documents=[text_for_embed],
            metadatas=[{
                "title": title,
                "type": entry_type,
                "tags": ",".join(tags),
                "created": entry["created"],
            }],
            embeddings=[embedding],
        )

        entries = _load_entries()
        entries[entry_id] = entry
        _save_entries(entries)

        return f"Guardado: '{title}' ({entry_type}, {len(content)} chars)"

    elif action in ("search", "find"):
        query = (params.get("query") or "").strip()
        if not query:
            return "¿Qué querés buscar?"
        collection = _get_chroma()
        try:
            count = collection.count()
        except Exception:
            count = 0
        if count == 0:
            return "No hay entradas en la base de conocimiento."

        query_emb = _get_embedding(query)
        results = collection.query(
            query_embeddings=[query_emb],
            n_results=min(10, count),
        )
        entries = _load_entries()
        lines = []
        if results and results.get("ids") and results["ids"][0]:
            for i in range(len(results["ids"][0])):
                eid = results["ids"][0][i]
                entry = entries.get(eid, {})
                title = entry.get("title", results["metadatas"][0][i].get("title", "?"))
                etype = entry.get("type", results["metadatas"][0][i].get("type", "?"))
                tags = entry.get("tags", [])
                score = float(results["distances"][0][i]) if results.get("distances") else 0
                tag_str = f" [{', '.join(tags)}]" if tags else ""
                snippet = (entry.get("content") or results["documents"][0][i] if results.get("documents") else "")[:120]
                lines.append(f"#{i+1} [{etype}] {title}{tag_str} (score:{score:.3f})\n   {snippet}...")
        if not lines:
            return "Sin resultados."
        return "\n\n".join(lines)

    elif action == "list":
        entries = _load_entries()
        if not entries:
            return "No hay entradas en la base de conocimiento."
        by_type = {}
        for e in entries.values():
            by_type.setdefault(e.get("type", "unknown"), []).append(e)
        lines = [f"Total: {len(entries)} entradas"]
        for etype, items in sorted(by_type.items()):
            lines.append(f"\n[{etype}] ({len(items)}):")
            for e in items:
                tags = f" [{', '.join(e['tags'])}]" if e.get("tags") else ""
                lines.append(f"  {e['id'][:8]} {e['title']}{tags}")
        return "\n".join(lines)

    elif action in ("get", "read", "view"):
        eid = (params.get("entry_id") or "").strip()
        if not eid:
            return "Falta 'entry_id'."
        entries = _load_entries()
        entry = entries.get(eid)
        if not entry:
            return f"No se encontró entrada con ID {eid[:12]}"
        tags = ", ".join(entry.get("tags", []))
        return (
            f"ID: {entry['id']}\n"
            f"Título: {entry['title']}\n"
            f"Tipo: {entry['type']}\n"
            f"Tags: {tags}\n"
            f"Creado: {entry['created']}\n"
            f"Actualizado: {entry['updated']}\n"
            f"---\n{entry['content']}"
        )

    elif action == "update":
        eid = (params.get("entry_id") or "").strip()
        if not eid:
            return "Falta 'entry_id'."
        entries = _load_entries()
        if eid not in entries:
            return f"No se encontró entrada con ID {eid[:12]}"

        entry = entries[eid]
        if params.get("title"):
            entry["title"] = params["title"].strip()
        if params.get("content"):
            entry["content"] = params["content"].strip()
        if params.get("type"):
            entry["type"] = params["type"].strip()
        if params.get("tags"):
            entry["tags"] = [t.strip() for t in params["tags"].split(",") if t.strip()]
        entry["updated"] = time.strftime("%Y-%m-%d %H:%M:%S")

        text_for_embed = f"{entry['title']}\n{entry['content']}"
        embedding = _get_embedding(text_for_embed)

        collection = _get_chroma()
        collection.update(
            ids=[eid],
            documents=[text_for_embed],
            metadatas=[{
                "title": entry["title"],
                "type": entry["type"],
                "tags": ",".join(entry.get("tags", [])),
                "created": entry["created"],
            }],
            embeddings=[embedding],
        )

        _save_entries(entries)
        return f"Actualizado: '{entry['title']}'"

    elif action == "delete":
        eid = (params.get("entry_id") or "").strip()
        if not eid:
            return "Falta 'entry_id'."
        entries = _load_entries()
        if eid not in entries:
            return f"No se encontró entrada con ID {eid[:12]}"
        title = entries[eid]["title"]
        del entries[eid]
        _save_entries(entries)

        collection = _get_chroma()
        collection.delete(ids=[eid])
        return f"Eliminado: '{title}'"

    elif action == "stats":
        entries = _load_entries()
        collection = _get_chroma()
        try:
            chroma_count = collection.count()
        except Exception:
            chroma_count = 0
        by_type = {}
        for e in entries.values():
            by_type[e.get("type", "unknown")] = by_type.get(e.get("type", "unknown"), 0) + 1
        type_summary = ", ".join(f"{k}: {v}" for k, v in sorted(by_type.items()))
        return (
            f"Total entradas: {len(entries)}\n"
            f"Índice vectorial: {chroma_count}\n"
            f"Por tipo: {type_summary}"
        )

    elif action == "export":
        path = (params.get("path") or "").strip()
        if not path:
            return "Falta 'path' para exportar."
        entries = _load_entries()
        out = []
        for e in entries.values():
            out.append(f"# {e['title']}\n- Tipo: {e['type']}\n- Tags: {', '.join(e['tags'])}\n- Creado: {e['created']}\n\n{e['content']}\n")
        Path(path).write_text("\n---\n".join(out), encoding="utf-8")
        return f"Exportado {len(entries)} entradas a {path}"

    return "Acciones: add, search, list, get, update, delete, stats, export"
