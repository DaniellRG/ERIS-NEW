# -*- coding: utf-8 -*-
"""core/idle_learning_loop.py — Autonomous learning when ERIS is idle.

Hooks into the existing idle detection in main.py.
When ERIS has been idle for a while, she:
  1. Generates dynamic learning topics via Gemini
  2. Researches them on the web
  3. Ingests new knowledge (RAG, Obsidian, semantic memory)
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

TOPIC_HISTORY_FILE = _BASE / "data" / "idle_learning_topics.json"


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
    # Rotación: si el log supera 250KB se rota (evita crecimiento sin límite)
    try:
        if _LOG_FILE.exists() and _LOG_FILE.stat().st_size > 250 * 1024:
            _rot = _LOG_FILE.with_name(_LOG_FILE.name + ".old")
            if _rot.exists():
                _rot.unlink()
            _LOG_FILE.rename(_rot)
    except Exception:
        pass
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


def _generate_topics(num_topics: int = 2) -> list:
    """Generate dynamic learning topics via Gemini. Returns list of topic strings."""
    try:
        from google import genai
        from core.audio_config import get_api_key
        api_key = get_api_key()
        client = genai.Client(api_key=api_key)

        # Load history to avoid repetition
        history = _load_topic_history()
        recent = history.get("recent_topics", [])[-20:]

        prompt = (
            "Eres ERIS, una IA autonoma con curiosidad insaciable. "
            "Genera {} temas de aprendizaje interesantes y actuales "
            "que NO hayas investigado antes. "
            "Los temas deben ser variados: tecnologia, ciencia, historia, "
            "filosofia, innovacion, cultura digital, etc. "
            "Evita repetir estos temas ya investigados: {}.\n\n"
            "Responde SOLO con una lista numerada, un tema por linea. "
            "Cada tema debe ser una frase corta y concreta (max 10 palabras)."
        ).format(num_topics, ", ".join(recent[-10:]) if recent else "ninguno")

        from core.model_config import get_model
        response = client.models.generate_content(
                    model=get_model("fast"),
            contents=prompt,
        )
        text = response.text.strip()
        topics = []
        for line in text.split("\n"):
            line = line.strip()
            line = line.lstrip("0123456789.()-* \t")
            if line and len(line) > 10:
                topics.append(line[:80])

        if not topics:
            raise ValueError("Gemini returned no topics")

        # Save to history
        history["recent_topics"].extend(topics)
        history.setdefault("total_generated", 0)
        history["total_generated"] += len(topics)
        _save_topic_history(history)

        return topics[:num_topics]
    except Exception as e:
        _log("Topic generation failed: {}".format(str(e)[:60]))
        # Fallback: use curiosity_engine if available
        try:
            from actions.curiosity_engine import curiosity_engine
            fallback = curiosity_engine({"action": "suggest", "count": num_topics})
            if fallback and isinstance(fallback, str):
                return [fallback[:80]]
        except Exception:
            pass
        # Last resort fallback
        return ["ultimas tendencias tecnologia 2026", "descubrimientos cientificos recientes"]


def _load_topic_history() -> dict:
    if TOPIC_HISTORY_FILE.exists():
        try:
            return json.loads(TOPIC_HISTORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"recent_topics": [], "total_generated": 0}


def _save_topic_history(history: dict):
    TOPIC_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOPIC_HISTORY_FILE.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")


def _topic_seen(topic: str, state: dict, history: dict) -> bool:
    """True si el tema ya fue aprendido (normaliza mayúsculas/puntuación)."""
    norm = " ".join(topic.lower().split())
    learned = state.get("topics_learned", [])
    recent = history.get("recent_topics", [])
    for existing in list(learned[-100:]) + list(recent[-200:]):
        if " ".join(str(existing).lower().split()) == norm:
            return True
    return False


def run_idle_learning() -> str:
    """Execute one idle learning cycle. Returns summary of what was learned."""
    global _cycle_count, _last_learning_time

    with _lock:
        _cycle_count += 1
        _last_learning_time = time.time()

    state = _load_state()
    history = _load_topic_history()
    state["total_idle_sessions"] += 1
    state["last_session"] = datetime.now().isoformat()

    # Generate topics dynamically via Gemini
    topics_to_learn = _generate_topics(MAX_TOPICS_PER_SESSION)

    # Filtrar temas ya aprendidos: no repetir lo que ya se investigó
    fresh_topics = [t for t in topics_to_learn if not _topic_seen(t, state, history)]
    if not fresh_topics:
        summary = "Sesion #{}: sin temas nuevos (todo repetido)".format(state["total_idle_sessions"])
        _save_state(state)
        _log(summary)
        return summary
    topics_to_learn = fresh_topics[:MAX_TOPICS_PER_SESSION]

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

    # Recortar historiales para que no crezcan sin límite
    state["topics_learned"] = state["topics_learned"][-100:]
    state["research_history"] = state["research_history"][-100:]

    _save_state(state)

    summary = "Sesion #{}: {} temas aprendidos [{}]".format(
        state["total_idle_sessions"],
        len(results),
        ", ".join(topics_to_learn)
    )
    _log(summary)

    return summary


def _is_quality_result(result: str) -> bool:
    """Rechaza resultados vacios, mensajes de error/'no encontrado' y
    contenido dominado por links/publicidad (no debe indexarse)."""
    if not result or len(result) < 50:
        return False
    low = result.lower()
    markers = (
        "no encontr", "no se encontr", "no hay resumen", "error en busqueda",
        "error buscando", "pip install", "especifica que buscar", "search_failed",
        "insufficient_data", "no encontre resultados", "no encontre definicion",
        "no encontre noticias",
    )
    if any(m in low for m in markers):
        return False
    # Dominado por URLs sueltas / publicidad: >30% de lineas son solo enlaces
    lines = [l.strip() for l in result.splitlines() if l.strip()]
    if len(lines) >= 3:
        url_lines = sum(1 for l in lines if l.startswith("http"))
        if url_lines / len(lines) > 0.3:
            return False
    return True


def _learn_one_topic(topic: str) -> str:
    """Research a topic via web search and ingest into ALL memory systems."""
    # 1. Web search
    try:
        from actions.web_search import web_search
        search_result = web_search({"query": topic, "num_results": 3})
    except Exception as e:
        return "search_failed: {}".format(str(e)[:50])

    if not _is_quality_result(search_result):
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
    history = _load_topic_history()
    lines = [
        "Idle Learning Status:",
        "  Ciclos totales: {}".format(state.get("total_idle_sessions", 0)),
        "  Temas aprendidos: {}".format(state.get("total_topics_learned", 0)),
        "  Ultima sesion: {}".format(state.get("last_session", "nunca")),
        "  Temas generados por Gemini: {}".format(history.get("total_generated", 0)),
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
                full = VAULT_PATH / note_path
                content = full.read_text(encoding="utf-8", errors="replace")
                fm, body = _parse_frontmatter(content)
                if len(body.strip()) < 50:
                    skipped += 1
                    continue
                from core.rag_pipeline import index_document
                result = index_document(str(full))
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

    if not _is_quality_result(search_result):
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
