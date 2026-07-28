# -*- coding: utf-8 -*-
"""core/autonomous_learner.py — Autonomous learning brain for ERIS.

Detects knowledge gaps, researches topics, ingests into RAG,
and self-assesses learning progress. This is the "self-teaching" loop.

Flow:
  1. Detect gaps (poor RAG scores, user questions without answers)
  2. Research via web_search
  3. Ingest results into knowledge base + RAG
  4. Track what was learned
  5. Self-assess weak areas
"""
import json
import time
from pathlib import Path
from datetime import datetime

_BASE = Path(__file__).resolve().parent.parent
_LEARN_STATE = _BASE / "data" / "autonomous_learn.json"
_KNOWLEDGE_DIR = _BASE / "data" / "knowledge"


def _load_state() -> dict:
    if _LEARN_STATE.exists():
        try:
            return json.loads(_LEARN_STATE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "learned_topics": [],
        "knowledge_gaps": [],
        "research_log": [],
        "total_researched": 0,
        "total_ingested": 0,
        "last_auto_expand": None,
        "weak_areas": [],
        "strong_areas": [],
    }


def _save_state(state: dict):
    _LEARN_STATE.parent.mkdir(parents=True, exist_ok=True)
    _LEARN_STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def autonomous_learner(parameters: dict, player=None) -> str:
    """Main entry point for autonomous learning."""
    action = parameters.get("action", "").lower().strip()

    if not action:
        return "Error: Se requiere 'action' (learn_topic, detect_gaps, auto_expand, status, assess)."

    if action == "learn_topic":
        return _learn_topic(parameters)
    elif action == "detect_gaps":
        return _detect_gaps(parameters)
    elif action == "auto_expand":
        return _auto_expand(parameters)
    elif action == "status":
        return _status()
    elif action == "assess":
        return _assess()
    elif action == "log_gap":
        return _log_gap(parameters)
    else:
        return f"Acción '{action}' no reconocida."


def _learn_topic(params: dict) -> str:
    """Research a topic and ingest results into RAG."""
    topic = params.get("topic", "")
    if not topic:
        return "Error: Se requiere 'topic'."

    state = _load_state()

    if topic in state["learned_topics"]:
        return f"Ya aprendí sobre '{topic}'."

    # Step 1: Research
    from actions.web_search import web_search
    search_result = web_search({"query": topic, "num_results": 3})

    # Step 2: Create knowledge file
    _KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in topic[:50])
    knowledge_file = _KNOWLEDGE_DIR / f"auto_{safe_name}.md"

    content = f"# {topic}\n\n## Investigación automática\n\n"
    content += f"Fuente: web_search | Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
    content += search_result

    knowledge_file.write_text(content, encoding="utf-8")

    # Step 3: Ingest into RAG
    try:
        from core.rag_pipeline import index_document
        rag_result = index_document(str(knowledge_file))
    except Exception as e:
        rag_result = f"Error indexando: {e}"

    # Step 4: Update state
    state["learned_topics"].append(topic)
    state["total_researched"] += 1
    state["total_ingested"] += 1
    state["research_log"].append({
        "topic": topic,
        "time": datetime.now().isoformat(),
        "rag_result": rag_result,
    })
    state["last_auto_expand"] = datetime.now().isoformat()
    _save_state(state)

    return f"Aprendido: '{topic}' -> {rag_result}"


def _detect_gaps(params: dict) -> str:
    """Detect knowledge gaps by testing RAG on common topics."""
    test_queries = [
        "machine learning algoritmos",
        "ciberseguridad OWASP vulnerabilidades",
        "bases de datos NoSQL",
        "redes TCP/IP protocolos",
        "inteligencia artificial agentes",
        "cloud computing AWS Kubernetes",
        "programación Python estructuras datos",
        "ingeniería de software patrones",
        "blockchain smart contracts",
        "Big Data Hadoop Spark",
    ]

    from core.rag_pipeline import query_documents
    gaps = []
    strong = []

    for q in test_queries:
        results = query_documents(q, top_k=1)
        if results and results[0].get("score", 1.0) < 0.5:
            strong.append(q)
        else:
            gaps.append(q)

    state = _load_state()
    state["weak_areas"] = gaps
    state["strong_areas"] = strong
    state["knowledge_gaps"] = gaps
    _save_state(state)

    lines = [f"Análisis de conocimiento ({len(test_queries)} temas):"]
    lines.append(f"\nFUERTE ({len(strong)}):")
    for s in strong:
        lines.append(f"  + {s}")
    lines.append(f"\nDÉBIL / GAP ({len(gaps)}):")
    for g in gaps:
        lines.append(f"  - {g}")
    return "\n".join(lines)


def _auto_expand(params: dict) -> str:
    """Automatically research and ingest the weakest areas."""
    state = _load_state()
    gaps = state.get("knowledge_gaps", [])

    if not gaps:
        return "No hay gaps detectados. Ejecutá 'detect_gaps' primero."

    max_topics = int(params.get("max_topics", 3))
    learned = []

    for topic in gaps[:max_topics]:
        if topic in state["learned_topics"]:
            continue
        result = _learn_topic({"topic": topic})
        learned.append(f"  {topic}: {result[:80]}")

    if not learned:
        return "Todos los gaps ya fueron cubiertos."

    return f"Auto-expand completado ({len(learned)} temas):\n" + "\n".join(learned)


def _status() -> str:
    """Show autonomous learning status."""
    state = _load_state()

    try:
        from core.rag_pipeline import stats
        rag = stats()
    except Exception:
        rag = {"documents": 0, "chunks": 0}

    lines = [
        "Estado de Aprendizaje Autónomo:",
        f"  Temas aprendidos: {len(state.get('learned_topics', []))}",
        f"  Research total: {state.get('total_researched', 0)}",
        f"  RAG docs: {rag.get('documents', 0)} | chunks: {rag.get('chunks', 0)}",
        f"  Último auto-expand: {state.get('last_auto_expand', 'nunca')}",
        f"  Áreas débiles: {len(state.get('weak_areas', []))}",
        f"  Áreas fuertes: {len(state.get('strong_areas', []))}",
    ]

    if state.get("learned_topics"):
        lines.append("\n  Temas aprendidos:")
        for t in state["learned_topics"][-10:]:
            lines.append(f"    - {t}")

    return "\n".join(lines)


def _assess() -> str:
    """Self-assessment: what do I know well, what needs work."""
    state = _load_state()

    try:
        from core.rag_pipeline import stats, list_indexed
        rag = stats()
        docs = list_indexed()
    except Exception:
        return "Error accediendo al RAG."

    lines = ["Auto-evaluación de conocimiento:"]
    lines.append(f"  Base de datos: {rag.get('documents', 0)} documentos, {rag.get('chunks', 0)} chunks")

    if docs:
        lines.append("\n  Documentos indexados:")
        for d in docs:
            lines.append(f"    {d['filename']}: {d['chunks']} chunks")

    lines.append(f"\n  Temas autónomos: {len(state.get('learned_topics', []))}")
    lines.append(f"  Áreas débiles: {len(state.get('weak_areas', []))}")

    if state.get("weak_areas"):
        lines.append("\n  Para mejorar, ejecutá 'auto_expand' para investigar automáticamente.")

    return "\n".join(lines)


def _log_gap(params: dict) -> str:
    """Log a knowledge gap detected from user interaction."""
    topic = params.get("topic", "")
    context = params.get("context", "")
    if not topic:
        return "Error: Se requiere 'topic'."

    state = _load_state()
    if topic not in state["knowledge_gaps"]:
        state["knowledge_gaps"].append(topic)
        state["research_log"].append({
            "type": "gap_detected",
            "topic": topic,
            "context": context,
            "time": datetime.now().isoformat(),
        })
        _save_state(state)
        return f"Gap registrado: '{topic}'. Se investigará en el próximo auto_expand."

    return f"Gap '{topic}' ya registrado."
