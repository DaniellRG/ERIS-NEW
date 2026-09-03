"""
core/learning_pipeline.py — Pipeline de aprendizaje autonomo para Eris

Eris investiga topics en web, sintetiza conocimiento, y lo guarda en Obsidian.
"""
import json
import re
import time
from datetime import datetime
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_MEMORY = _BASE / "memory"
_DATA = _BASE / "data"
_STATE_FILE = _MEMORY / "learning_pipeline_state.json"
_QUEUE_FILE = _MEMORY / "learning_queue.json"
_LOG_FILE = _MEMORY / "learning_pipeline_log.json"

from core.logging_setup import get_obsidian_vault
_OBSIDIAN_VAULT = get_obsidian_vault()
KNOWLEDGE_DIR = _OBSIDIAN_VAULT / "Conocimiento-Profundo"


def _load_state() -> dict:
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "topics_learned": 0,
        "last_learned": None,
        "learned_list": [],
        "last_reset": datetime.now().isoformat(),
    }


def _save_state(state: dict):
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def _log(action: str, details: str, success: bool = True):
    entry = {"timestamp": datetime.now().isoformat(), "action": action, "details": details[:200], "success": success}
    logs = []
    if _LOG_FILE.exists():
        try:
            logs = json.loads(_LOG_FILE.read_text(encoding="utf-8"))
        except Exception:
            logs = []
    logs.append(entry)
    if len(logs) > 100:
        logs = logs[-100:]
    _LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    _LOG_FILE.write_text(json.dumps(logs, indent=2, ensure_ascii=False), encoding="utf-8")


def research_topic(topic: str) -> dict:
    """Investiga un topic usando web_search (simulado - en real usa la tool de Eris)."""
    research = {
        "topic": topic,
        "timestamp": datetime.now().isoformat(),
        "queries": [
            "{} explicacion basica".format(topic),
            "{} aplicaciones reales".format(topic),
            "{} estado actual 2026".format(topic),
        ],
        "key_facts": [],
        "status": "pendiente_de_investigacion",
    }

    sem_file = _MEMORY / "semantic.json"
    if sem_file.exists():
        try:
            triples = json.loads(sem_file.read_text(encoding="utf-8"))
            for t in triples:
                subj = t.get("subject", "").lower()
                obj = t.get("object", "").lower()
                if topic.lower() in subj or topic.lower() in obj:
                    research["key_facts"].append({
                        "subject": t.get("subject", ""),
                        "predicate": t.get("predicate", ""),
                        "object": t.get("object", ""),
                    })
        except Exception:
            pass

    if not research["key_facts"]:
        research["key_facts"].append({
            "subject": topic,
            "predicate": "es_un",
            "object": "Tema de investigacion autonomo de Eris",
        })

    research["status"] = "investigado"
    return research


def synthesize(research: dict) -> str:
    """Sintetiza investigacion en un documento estructurado."""
    topic = research.get("topic", "Desconocido")
    facts = research.get("key_facts", [])

    content = "---\n"
    content += "tipo: conocimiento-profundo\n"
    content += "fecha: {}\n".format(datetime.now().strftime("%Y-%m-%d"))
    content += "tema: {}\n".format(topic)
    content += "materias: [Aprendizaje Autonomo]\n"
    content += "nivel: profundo\n"
    content += "fuente: learning_pipeline (autonomo)\n"
    content += "---\n\n"
    content += "# {}\n\n".format(topic)
    content += "## Investigacion Autonoma\n\n"
    content += "Este documento fue creado automaticamente por Eris como parte de su aprendizaje autonomo.\n\n"
    content += "## Datos Clave\n\n"

    for fact in facts:
        content += "- **{}**: {} {}\n".format(
            fact.get("subject", ""), fact.get("predicate", ""), fact.get("object", "")
        )

    content += "\n## Contexto\n\n"
    content += "Fecha de investigacion: {}\n".format(research.get("timestamp", ""))
    content += "Ciclos de aprendizaje: {}\n".format(research.get("queries", []))

    content += "\n## Conexiones\n\n"
    content += "- Conectado con NeuroSpheres\n"
    content += "- Parte del conocimiento autonomo de Eris\n"
    content += "- Actualizara este documento cuando aprenda mas\n"

    return content


def save_to_obsidian(topic: str, content: str) -> dict:
    """Guarda contenido en Obsidian."""
    if not KNOWLEDGE_DIR.exists():
        KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)

    safe_name = re.sub(r'[^\w\s-]', '', topic)
    safe_name = re.sub(r'\s+', '-', safe_name.strip())
    file_path = KNOWLEDGE_DIR / "{}.md".format(safe_name)

    file_path.write_text(content, encoding="utf-8")
    _log("save_obsidian", "Guardado: {}".format(file_path.name))
    return {"status": "guardado", "file": str(file_path), "topic": topic}


def auto_learn() -> dict:
    """Ejecuta el pipeline completo: topic -> research -> synthesize -> save."""
    from core.autonomy import get_next_curiosity_topic, mark_topic_learned

    topic = get_next_curiosity_topic()
    if not topic:
        return {"status": "sin_topics", "message": "No hay mas topics para aprender"}

    research = research_topic(topic)
    content = synthesize(research)
    result = save_to_obsidian(topic, content)
    mark_topic_learned(topic)

    state = _load_state()
    state["topics_learned"] += 1
    state["last_learned"] = topic
    state.setdefault("learned_list", []).append({
        "topic": topic,
        "timestamp": datetime.now().isoformat(),
    })
    _save_state(state)

    _log("auto_learn", "Aprendido: {}".format(topic))
    return {
        "status": "aprendido",
        "topic": topic,
        "file": result.get("file", ""),
        "total_learned": state["topics_learned"],
    }


def get_learning_queue() -> list:
    """Retorna la cola de topics pendientes."""
    from core.autonomy import CURIOSITY_TOPICS
    state = _load_state()
    learned = set(state.get("learned_list", [{}])[0].get("topic", "") if state.get("learned_list") else "")
    learned = {item.get("topic", "") for item in state.get("learned_list", [])}
    pending = [t for t in CURIOSITY_TOPICS if t not in learned]
    return pending


def learning_pipeline_tool(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = params.get("action", "status")

    if action == "status":
        state = _load_state()
        queue = get_learning_queue()
        return json.dumps({
            "topics_learned": state["topics_learned"],
            "last_learned": state.get("last_learned"),
            "queue_pending": len(queue),
            "max_daily": 10,
        }, indent=2)

    elif action == "research":
        topic = params.get("topic", "")
        if not topic:
            return json.dumps({"error": "Topic requerido"})
        result = research_topic(topic)
        return json.dumps(result, indent=2, default=str)

    elif action == "synthesize":
        topic = params.get("topic", "")
        research = research_topic(topic)
        content = synthesize(research)
        return content

    elif action == "save":
        topic = params.get("topic", "")
        content = params.get("content", "")
        if not topic or not content:
            return json.dumps({"error": "topic y content requeridos"})
        result = save_to_obsidian(topic, content)
        return json.dumps(result, indent=2)

    elif action == "auto_learn":
        result = auto_learn()
        return json.dumps(result, indent=2)

    elif action == "queue":
        queue = get_learning_queue()
        return json.dumps({"pending": queue[:10], "total": len(queue)}, indent=2)

    return json.dumps({"error": "Accion desconocida: {}".format(action)})


if __name__ == "__main__":
    print("=== Test Learning Pipeline ===")
    print(learning_pipeline_tool({"action": "status"}))
    r = json.loads(learning_pipeline_tool({"action": "auto_learn"}))
    print("Auto-learn:", r)
