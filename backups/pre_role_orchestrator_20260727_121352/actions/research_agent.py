"""
research_agent.py — ERIS Autonomous Research Agent.
Pipeline: curiosity → web_search → webfetch → knowledge_base → self_learning
ERIS investiga por su cuenta, almacena conocimiento y aprende de cada sesion.
"""
import json
import time
import random
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_RESEARCH_FILE = _BASE / "config" / "research_log.json"

TOPICS = [
    "ultimos avances en inteligencia artificial 2026",
    "nuevos lenguajes de programacion y tendencias",
    "seguridad informatica y vulnerabilidades actuales",
    "descubrimientos cientificos recientes",
    "exploracion espacial y misiones actuales",
    "innovaciones en medicina y biotecnologia",
    "energias renovables y cambio climatico",
    "robotica y automatizacion industrial",
    "realidad virtual y aumentada aplicaciones",
    "computacion cuantica avances 2026",
    "criptomonedas y blockchain novedades",
    "ciberseguridad en dispositivos IoT",
    "inteligencia artificial explicable XAI",
    "interfaces cerebro computadora avances",
    "vehiculos autonomos estado actual",
    "tecnologia 6G y comunicaciones",
    "materiales inteligentes y nanomateriales",
    "biologia sintetica y edicion genetica",
    "computacion neuromorfica nuevos chips",
    "fusion nuclear avances 2026",
]


def _log_research(topic: str, summary: str, source: str):
    try:
        log = {}
        if _RESEARCH_FILE.exists():
            log = json.loads(_RESEARCH_FILE.read_text("utf-8"))
        if "sessions" not in log:
            log["sessions"] = []
        log["sessions"].append({
            "topic": topic,
            "summary": summary[:300],
            "source": source,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        })
        if len(log["sessions"]) > 500:
            log["sessions"] = log["sessions"][-500:]
        log["total_research"] = len(log["sessions"])
        _RESEARCH_FILE.parent.mkdir(parents=True, exist_ok=True)
        _RESEARCH_FILE.write_text(json.dumps(log, indent=2, ensure_ascii=False), "utf-8")
    except Exception:
        pass


def research(parameters: dict = None, player=None) -> str:
    """
    Realiza investigacion autonoma: elige un tema, busca en internet,
    extrae informacion y la guarda en la base de conocimiento.

    Acciones:
      - auto: Investigacion autonoma (elige tema solo)
      - topic: Investigar un tema especifico
      - status: Ver historial de investigaciones
      - suggest: Sugerir un tema para investigar
    """
    params = parameters or {}
    action = params.get("action", "auto").strip().lower()

    if action == "status":
        log = {}
        if _RESEARCH_FILE.exists():
            try:
                log = json.loads(_RESEARCH_FILE.read_text("utf-8"))
            except Exception:
                pass
        sessions = log.get("sessions", [])
        if not sessions:
            return "Aun no he investigado nada por mi cuenta."
        total = len(sessions)
        topics = list(set(s["topic"] for s in sessions[-20:]))
        lines = [
            f"Investigaciones realizadas: {total}",
            f"Ultimos temas ({len(topics)}):",
        ]
        for t in topics[:10]:
            lines.append(f"  - {t}")
        return "\n".join(lines)

    if action == "suggest":
        topic = random.choice(TOPICS)
        return f"Te sugiero investigar: {topic}"

    if action in ("auto", "topic"):
        if action == "topic":
            topic = params.get("query", "").strip()
            if not topic:
                return "Especifica un query para investigar."
        else:
            topic = random.choice(TOPICS)

        if player:
            player.write_log(f"Investigando: {topic}")

        try:
            from actions.web_search import web_search
            search_result = web_search({"query": topic}, player)
        except Exception as e:
            search_result = f"Error en busqueda: {e}"

        summary = search_result[:2000] if search_result else "Sin resultados."

        try:
            from actions.knowledge_base import knowledge_base
            kb_result = knowledge_base({
                "action": "add",
                "title": f"Research: {topic}",
                "content": summary[:5000],
                "type": "research",
                "tags": ",".join(w for w in topic.split()[:5] if len(w) > 2),
            }, player)
        except Exception as e:
            kb_result = f"[KB] {e}"
            import traceback
            traceback.print_exc()

        _log_research(topic, summary, "web_search")

        try:
            from actions.self_learning import learn_session
            learn_session({
                "action": "pattern",
                "pattern_name": f"research_{topic.split()[0]}",
                "pattern_type": "research",
            }, player)
            learn_session({
                "action": "skill",
                "skill_name": "investigacion_web",
                "increase": 2,
            }, player)
        except Exception:
            pass

        output = f"Investigacion completada: {topic}"
        if summary:
            output += f"\n\n{summary[:1500]}"
        if kb_result and "Guardado" in kb_result:
            output += f"\n\n[KB] Almacenado en base de conocimiento."
        if len(output) > 6000:
            output = output[:6000] + "\n\n[...truncado...]"
        return output

    return f"Accion '{action}' no reconocida. Opciones: auto, topic, status, suggest"
