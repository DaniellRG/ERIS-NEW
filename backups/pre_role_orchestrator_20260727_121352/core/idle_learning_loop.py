# -*- coding: utf-8 -*-
"""core/idle_learning_loop.py — Autonomous learning when ERIS is idle.

Hooks into the existing idle detection in main.py.
When ERIS has been idle for a while, she:
  1. Detects knowledge gaps
  2. Researches weak areas
  3. Ingests new knowledge
  4. Logs what she learned

Runs in background thread, never interrupts the user.
"""
import json
import time
import random
import threading
from pathlib import Path
from datetime import datetime

_BASE = Path(__file__).resolve().parent.parent
_IDLE_STATE = _BASE / "data" / "idle_learning.json"
_LOG_FILE = _BASE / "data" / "idle_learning.log"

# Config
IDLE_THRESHOLD = 300       # 5 minutes idle before starting
LEARNING_INTERVAL = 1800   # Learn every 30 min max
MAX_TOPICS_PER_SESSION = 2  # Max topics per idle session

_cycle_count = 0
_last_learning_time = 0
_lock = threading.Lock()

# Topics ERIS can research autonomously (curated, high-value)
RESEARCH_POOL = [
    "ultimos avances inteligencia artificial 2026",
    "nuevos frameworks programacion tendencias",
    "ciberseguridad vulnerabilidades recientes",
    "Python nuevas caracteristicas version",
    "Docker Kubernetes mejoras recientes",
    "machine learning modelos nuevos 2026",
    "automatizacion tareas inteligentes IA",
    "bases de datos nuevas tendencias NoSQL",
    "cloud computing servicios nuevos",
    "robotica automatizacion avances",
    "blockchain aplicaciones reales 2026",
    "Big Data herramientas nuevas",
    "redes 5G 6G tecnologias nuevas",
    "computacion cuantica avances recientes",
    "seguridad datos privacidad GDPR",
    "desarrollo software metodologias agiles",
    "inteligencia artificial explicativa",
    "vehiculos autonomos avances",
    "biotecnologia bioinformatica avances",
    "energias renovables tecnologia",
]


def _load_state() -> dict:
    if _IDLE_STATE.exists():
        try:
            return json.loads(_IDLE_STATE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "total_idle_sessions": 0,
        "total_topics_learned": 0,
        "last_session": None,
        "topics_learned": [],
        "research_history": [],
    }


def _save_state(state: dict):
    _IDLE_STATE.parent.mkdir(parents=True, exist_ok=True)
    _IDLE_STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def _log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = "[{}] {}\n".format(ts, msg)
    _LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(str(_LOG_FILE), "a", encoding="utf-8") as f:
        f.write(line)


def should_learn(idle_seconds: float) -> bool:
    """Check if ERIS should start an idle learning session."""
    global _last_learning_time
    if idle_seconds < IDLE_THRESHOLD:
        return False
    if time.time() - _last_learning_time < LEARNING_INTERVAL:
        return False
    return True


def run_idle_learning() -> str:
    """Execute one idle learning cycle. Returns summary of what was learned."""
    global _cycle_count, _last_learning_time

    with _lock:
        _cycle_count += 1
        _last_learning_time = time.time()

    state = _load_state()
    state["total_idle_sessions"] += 1
    state["last_session"] = datetime.now().isoformat()

    # Pick a topic not yet learned
    learned_set = set(state.get("topics_learned", []))
    available = [t for t in RESEARCH_POOL if t not in learned_set]
    if not available:
        # Reset pool if all learned
        state["topics_learned"] = []
        available = RESEARCH_POOL[:]

    num_topics = min(MAX_TOPICS_PER_SESSION, len(available))
    topics_to_learn = random.sample(available, num_topics)

    results = []
    for topic in topics_to_learn:
        try:
            result = _learn_one_topic(topic)
            results.append(result)
            state["topics_learned"].append(topic)
            state["total_topics_learned"] += 1
            state["research_history"].append({
                "topic": topic,
                "time": datetime.now().isoformat(),
                "result": result[:100],
            })
        except Exception as e:
            _log("ERROR learning '{}': {}".format(topic, str(e)[:80]))
            results.append("ERROR: {}".format(str(e)[:80]))

    _save_state(state)

    summary = "Sesion #{}: {} temas aprendidos [{}]".format(
        state["total_idle_sessions"],
        len(results),
        ", ".join(topics_to_learn)
    )
    _log(summary)

    return summary


def _learn_one_topic(topic: str) -> str:
    """Research a topic via web search and ingest into ALL memory systems."""
    # 1. Web search
    try:
        from actions.web_search import web_search
        search_result = web_search({"query": topic, "num_results": 3})
    except Exception as e:
        return "search_failed: {}".format(str(e)[:50])

    if not search_result or len(search_result) < 50:
        return "insufficient_data"

    # 2. Create knowledge file
    _KNOWLEDGE_DIR = _BASE / "data" / "knowledge"
    _KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)

    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in topic[:50])
    knowledge_file = _KNOWLEDGE_DIR / "idle_{}.md".format(safe_name)

    content = "# {}\n\n".format(topic)
    content += "## Auto-investigacion (idle learning)\n\n"
    content += "Fecha: {}\n\n".format(datetime.now().strftime("%Y-%m-%d %H:%M"))
    content += search_result

    knowledge_file.write_text(content, encoding="utf-8")

    # 3. Index into RAG (vector search)
    rag_result = ""
    try:
        from core.rag_pipeline import index_document
        rag_result = index_document(str(knowledge_file))
    except Exception as e:
        rag_result = "rag_error: {}".format(str(e)[:50])

    # 4. Save to Obsidian (second brain)
    try:
        _save_to_obsidian(topic, search_result)
    except Exception:
        pass

    # 5. Save to semantic memory (memory system)
    try:
        _save_to_semantic_memory(topic, search_result)
    except Exception:
        pass

    return rag_result


def _save_to_obsidian(topic: str, content: str):
    """Write learned topic to Obsidian vault."""
    try:
        from actions.obsidian_brain import obsidian_note
        # Truncate for Obsidian (keep it concise)
        summary = content[:2000] if len(content) > 2000 else content
        obsidian_note({
            "action": "write",
            "title": "Auto-learn: {}".format(topic[:60]),
            "content": summary,
            "tags": "auto-learn,idle,research",
            "folder": "Aprendizaje",
        })
    except Exception:
        pass


def _save_to_semantic_memory(topic: str, content: str):
    """Store in semantic memory system."""
    try:
        from core.semantic_memory import get_memory_system
        mem = get_memory_system()
        if mem:
            mem.remember(
                text="Aprendi sobre: {}. {}".format(topic, content[:300]),
                context="idle_learning",
                importance=0.7,
            )
    except Exception:
        pass


def get_idle_status() -> str:
    """Get status of idle learning system."""
    state = _load_state()
    lines = [
        "Idle Learning Status:",
        "  Ciclos totales: {}".format(state.get("total_idle_sessions", 0)),
        "  Temas aprendidos: {}".format(state.get("total_topics_learned", 0)),
        "  Ultima sesion: {}".format(state.get("last_session", "nunca")),
        "  Pool disponible: {} temas".format(len(RESEARCH_POOL)),
    ]
    if state.get("topics_learned"):
        recent = state["topics_learned"][-5:]
        lines.append("  Ultimos: {}".format(", ".join(recent)))
    return "\n".join(lines)


def sync_obsidian_to_rag() -> str:
    """Sync all Obsidian notes into RAG vector store."""
    try:
        from actions.obsidian_brain import _all_notes, _parse_frontmatter, VAULT_PATH
        notes = _all_notes()
        indexed = 0
        skipped = 0
        for note_path in notes:
            try:
                content = note_path.read_text(encoding="utf-8", errors="replace")
                fm, body = _parse_frontmatter(content)
                if len(body.strip()) < 50:
                    skipped += 1
                    continue
                from core.rag_pipeline import index_document
                result = index_document(str(note_path))
                if result and "indexed" in result:
                    indexed += 1
                else:
                    skipped += 1
            except Exception:
                skipped += 1
                continue
        return "Sync Obsidian->RAG: {} indexados, {} saltados".format(indexed, skipped)
    except Exception as e:
        return "Sync error: {}".format(str(e)[:80])


def learn_from_user(context: str, user_msg: str) -> str:
    """When user asks something ERIS doesn't know, learn it and store everywhere."""
    topic = user_msg[:80]
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in topic[:50])

    # 1. Search web
    try:
        from actions.web_search import web_search
        search_result = web_search({"query": topic, "num_results": 3})
    except Exception:
        return "No pude investigar '{}'. Intentalo de nuevo.".format(topic)

    if not search_result or len(search_result) < 50:
        return "No encontre suficiente informacion sobre '{}'.".format(topic)

    # 2. Create knowledge file
    _KNOWLEDGE_DIR = _BASE / "data" / "knowledge"
    _KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    knowledge_file = _KNOWLEDGE_DIR / "user_learn_{}.md".format(safe_name)
    content = "# {}\n\n".format(topic)
    content += "## Aprendido por peticion del usuario\n\n"
    content += "Fecha: {}\n\n".format(datetime.now().strftime("%Y-%m-%d %H:%M"))
    content += "Contexto del usuario: {}\n\n".format(context[:200])
    content += search_result
    knowledge_file.write_text(content, encoding="utf-8")

    # 3. Index into RAG
    try:
        from core.rag_pipeline import index_document
        index_document(str(knowledge_file))
    except Exception:
        pass

    # 4. Save to Obsidian
    _save_to_obsidian("User: {}".format(topic[:60]), search_result)

    # 5. Save to semantic memory
    _save_to_semantic_memory("user_learned: {}".format(topic), search_result)

    return "Investigue '{}' y guarde el resultado. Preguntame ahora.".format(topic)
