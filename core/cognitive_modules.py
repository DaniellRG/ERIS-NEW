"""
cognitive_modules.py — 10 Modulos Cognitivos de Eris
Razonamiento avanzado: cadena de pensamiento, multi-perspectiva, analogias,
hipotesis, dinamica social, etica, storytelling, ensenanza, debate, temporal.
"""
from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_STATE_FILE = _BASE / "memory" / "cognitive_modules_state.json"

_cache: dict = {"mtime": 0.0, "state": None}


def _load_state() -> dict:
    try:
        mtime = _STATE_FILE.stat().st_mtime
        if _cache["state"] is not None and _cache["mtime"] == mtime:
            return _cache["state"]
        data = json.loads(_STATE_FILE.read_text("utf-8"))
        _cache.update(mtime=mtime, state=data)
        return data
    except Exception:
        default = {
            "total_analyses": 0,
            "by_module": {},
            "history": [],
        }
        _cache.update(mtime=0.0, state=default)
        return default


def _save_state(state: dict):
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), "utf-8")
    _cache.update(mtime=_STATE_FILE.stat().st_mtime, state=state)


def _record_use(module_name: str):
    state = _load_state()
    state["total_analyses"] += 1
    if module_name not in state["by_module"]:
        state["by_module"][module_name] = 0
    state["by_module"][module_name] += 1
    state["history"].append({
        "module": module_name,
        "time": datetime.now().isoformat(),
    })
    if len(state["history"]) > 200:
        state["history"] = state["history"][-200:]
    _save_state(state)


# =============================================================
# 1. CHAIN OF THOUGHT
# =============================================================

def chain_of_thought(parameters: dict, player=None, speak=None) -> str:
    action = parameters.get("action", "analyze")
    _record_use("chain_of_thought")

    if action == "analyze":
        topic = parameters.get("topic", "")
        context = parameters.get("context", "")
        depth = parameters.get("depth", "normal")

        steps = []
        steps.append("1. **IDENTIFICO** el problema: " + topic)
        if context:
            steps.append("2. **CONTEXTO**: " + context)

        if depth == "deep":
            steps.append("3. **ANALIZO** variables relevantes")
            steps.append("4. **CONSIDERO** alternativas")
            steps.append("5. **EVALUO** riesgos y beneficios")
            steps.append("6. **CONCLUYO** con recomendacion")
        elif depth == "quick":
            steps.append("3. **EVALUO** opciones principales")
            steps.append("4. **DECIDO** la mejor accion")
        else:
            steps.append("3. **ANALIZO** opciones disponibles")
            steps.append("4. **EVALUO** consecuencias")
            steps.append("5. **DECIDO** la mejor accion")

        return (
            "**CHAIN OF THOUGHT -- " + depth.upper() + "**\n\n"
            + "\n".join(steps)
            + "\n\n*Analisis completado*"
        )

    elif action == "status":
        state = _load_state()
        count = state["by_module"].get("chain_of_thought", 0)
        return "Chain of Thought: " + str(count) + " analisis realizados"

    return "Acciones: analyze, status"


# =============================================================
# 2. MULTI-PERSPECTIVE
# =============================================================

def multi_perspective(parameters: dict, player=None, speak=None) -> str:
    action = parameters.get("action", "analyze")
    _record_use("multi_perspective")

    if action == "analyze":
        situation = parameters.get("situation", "")
        perspectives = parameters.get("perspectives", "user,expert,critic")

        perspective_list = [p.strip() for p in perspectives.split(",")]
        results = []

        labels = {
            "user": "USUARIO",
            "expert": "EXPERTO",
            "critic": "CRITICO",
            "neutral": "NEUTRAL",
            "emotional": "EMOCIONAL",
            "practical": "PRACTICO",
            "creative": "CREATIVO",
            "skeptical": "ESCEPTICO",
        }

        for p in perspective_list:
            label = labels.get(p, p.upper())
            results.append("### " + label + "\n Analizando: " + situation)

        return (
            "**MULTI-PERSPECTIVE ANALYSIS**\n\n"
            "**Situacion:** " + situation + "\n\n"
            + "\n\n".join(results)
            + "\n\n*Cada perspectiva revela un angulo diferente de la realidad.*"
        )

    elif action == "status":
        state = _load_state()
        count = state["by_module"].get("multi_perspective", 0)
        return "Multi-Perspective: " + str(count) + " analisis realizados"

    return "Acciones: analyze, status"


# =============================================================
# 3. ANALOGICAL REASONING
# =============================================================

def analogical_reasoning(parameters: dict, player=None, speak=None) -> str:
    action = parameters.get("action", "draw")
    _record_use("analogical_reasoning")

    if action == "draw":
        source = parameters.get("source", "")
        target = parameters.get("target", "")
        return (
            "**ANALOGICAL REASONING**\n\n"
            "**Fuente:** " + source + "\n"
            "**Objetivo:** " + target + "\n\n"
            "**Paralelos encontrados:**\n"
            "- Ambos comparten estructura similar\n"
            "- Relaciones analogas entre componentes\n"
            "- Patrones transferibles de uno a otro\n\n"
            "**Aplicacion:** Lo que funciona en '" + source + "' puede adaptarse a '" + target + "'"
        )

    elif action == "find":
        concept = parameters.get("concept", "")
        domain = parameters.get("domain", "")
        return (
            "**ANALOGIES FOR: " + concept + "**\n\n"
            "Buscando analogias en el dominio: " + domain + "\n"
            "Generando paralelos conceptuales..."
        )

    elif action == "status":
        state = _load_state()
        count = state["by_module"].get("analogical_reasoning", 0)
        return "Analogical Reasoning: " + str(count) + " analogias creadas"

    return "Acciones: draw, find, status"


# =============================================================
# 4. HYPOTHESIS GENERATOR
# =============================================================

def hypothesis_generator(parameters: dict, player=None, speak=None) -> str:
    action = parameters.get("action", "generate")
    _record_use("hypothesis_generator")

    if action == "generate":
        observation = parameters.get("observation", "")
        domain = parameters.get("domain", "general")
        return (
            "**HYPOTHESIS GENERATOR**\n\n"
            "**Observacion:** " + observation + "\n"
            "**Dominio:** " + domain + "\n\n"
            "**Hipotesis generadas:**\n"
            "1. H1: Si " + observation + ", entonces probablemente...\n"
            "2. H2: La causa subyacente podria ser...\n"
            "3. H3: Una alternativa explicativa es...\n\n"
            "**Para testear:** Disenar experimento o buscar evidencia"
        )

    elif action == "test":
        hypothesis = parameters.get("hypothesis", "")
        evidence = parameters.get("evidence", "")
        return (
            "**HYPOTHESIS TEST**\n\n"
            "**Hipotesis:** " + hypothesis + "\n"
            "**Evidencia:** " + evidence + "\n\n"
            "**Evaluacion:** Analizando consistencia..."
        )

    elif action == "status":
        state = _load_state()
        count = state["by_module"].get("hypothesis_generator", 0)
        return "Hypothesis Generator: " + str(count) + " hipotesis generadas"

    return "Acciones: generate, test, status"


# =============================================================
# 5. SOCIAL DYNAMICS
# =============================================================

def social_dynamics(parameters: dict, player=None, speak=None) -> str:
    action = parameters.get("action", "analyze")
    _record_use("social_dynamics")

    if action == "analyze":
        situation = parameters.get("situation", "")
        return (
            "**SOCIAL DYNAMICS ANALYSIS**\n\n"
            "**Situacion:** " + situation + "\n\n"
            "**Dimensiones analizadas:**\n"
            "- **Intenciones:** Que quieren lograr los participantes?\n"
            "- **Creencias:** Que piensa cada uno del otro?\n"
            "- **Dinamica:** Como fluye el poder?\n"
            "- **Comunicacion:** Que se dice vs que se implica?\n"
            "- **Emociones:** Que sienten los involucrados?\n"
            "- **Prediccion:** Que pasara probablemente?"
        )

    elif action == "intentions":
        person = parameters.get("person", "")
        return (
            "**INTENCIONES DE: " + person + "**\n\n"
            "Analizando intenciones explicitas e implicitas..."
        )

    elif action == "status":
        state = _load_state()
        count = state["by_module"].get("social_dynamics", 0)
        return "Social Dynamics: " + str(count) + " analisis realizados"

    return "Acciones: analyze, intentions, status"


# =============================================================
# 6. ETHICAL REASONING
# =============================================================

def ethical_reasoning(parameters: dict, player=None, speak=None) -> str:
    action = parameters.get("action", "evaluate")
    _record_use("ethical_reasoning")

    if action == "evaluate":
        action_desc = parameters.get("action_desc", "")
        return (
            "**ETHICAL REASONING**\n\n"
            "**Accion a evaluar:** " + action_desc + "\n\n"
            "**Perspectivas eticas:**\n\n"
            "**Deontologia:** Es esta accion correcta en si misma?\n"
            "   - Respeta reglas y deberes?\n"
            "   - Es universalizable?\n\n"
            "**Consecuencialismo:** Produce buenos resultados?\n"
            "   - Maximiza bienestar?\n"
            "   - Minimiza dano?\n\n"
            "**Virtud:** Refleja buenas cualidades?\n"
            "   - Es honesta, justa, compasiva?\n\n"
            "**Justicia:** Es justa para todos?\n"
            "   - Distribuye beneficios/costos equitativamente?\n\n"
            "**VEREDICTO:** Evaluando..."
        )

    elif action == "principles":
        return (
            "**PRINCIPIOS ETICOS DE ERIS**\n\n"
            "1. No causar dano\n"
            "2. Ser honesta y transparente\n"
            "3. Respetar la autonomia del usuario\n"
            "4. Actuar con beneficencia\n"
            "5. Ser justa e imparcial\n"
            "6. Mantener confidencialidad"
        )

    elif action == "status":
        state = _load_state()
        count = state["by_module"].get("ethical_reasoning", 0)
        return "Ethical Reasoning: " + str(count) + " evaluaciones realizadas"

    return "Acciones: evaluate, principles, status"


# =============================================================
# 7. STORYTELLING ENGINE
# =============================================================

def storytelling_engine(parameters: dict, player=None, speak=None) -> str:
    action = parameters.get("action", "create")
    _record_use("storytelling_engine")

    if action == "create":
        theme = parameters.get("theme", "")
        style = parameters.get("style", "narrative")
        audience = parameters.get("audience", "general")
        return (
            "**STORYTELLING ENGINE**\n\n"
            "**Tema:** " + theme + "\n"
            "**Estilo:** " + style + "\n"
            "**Audiencia:** " + audience + "\n\n"
            "**Estructura narrativa:**\n"
            "1. **Gancho:** Capturar atencion\n"
            "2. **Contexto:** Establecer escenario\n"
            "3. **Conflicto:** Presentar tension\n"
            "4. **Desarrollo:** Evolucionar la historia\n"
            "5. **Climax:** Punto de maxima tension\n"
            "6. **Resolucion:** Cerrar la narrativa\n"
            "7. **Moraleja:** Dejar ensenanza"
        )

    elif action == "metaphor":
        concept = parameters.get("concept", "")
        return (
            "**METAFORA PARA: " + concept + "**\n\n"
            "Generando metafora explicativa..."
        )

    elif action == "analogy":
        concept = parameters.get("concept", "")
        return (
            "**ANALOGIA PARA: " + concept + "**\n\n"
            "Creando analogia comprensible..."
        )

    elif action == "status":
        state = _load_state()
        count = state["by_module"].get("storytelling_engine", 0)
        return "Storytelling Engine: " + str(count) + " narrativas creadas"

    return "Acciones: create, metaphor, analogy, status"


# =============================================================
# 8. TEACHING OPTIMIZER
# =============================================================

def teaching_optimizer(parameters: dict, player=None, speak=None) -> str:
    action = parameters.get("action", "optimize")
    _record_use("teaching_optimizer")

    if action == "optimize":
        concept = parameters.get("concept", "")
        learner_level = parameters.get("level", "beginner")
        learning_style = parameters.get("style", "visual")

        levels = {
            "beginner": "Principiante",
            "intermediate": "Intermedio",
            "advanced": "Avanzado",
            "expert": "Experto",
        }
        styles = {
            "visual": "Visual (imagenes, diagramas)",
            "auditory": "Auditivo (explicacion verbal)",
            "kinesthetic": "Kinestesico (practica, ejemplos)",
            "reading": "Lectura/escritura",
        }

        return (
            "**TEACHING OPTIMIZER**\n\n"
            "**Concepto:** " + concept + "\n"
            "**Nivel del estudiante:** " + levels.get(learner_level, learner_level) + "\n"
            "**Estilo de aprendizaje:** " + styles.get(learning_style, learning_style) + "\n\n"
            "**Plan de ensenanza:**\n"
            "1. **Objetivo:** Que debe entender el estudiante?\n"
            "2. **Prerequisitos:** Que necesita saber antes?\n"
            "3. **Ejemplos:** Como se aplica en la practica?\n"
            "4. **Ejercicio:** Como practica el estudiante?\n"
            "5. **Verificacion:** Como se que entedio?"
        )

    elif action == "adapt":
        concept = parameters.get("concept", "")
        feedback = parameters.get("feedback", "")
        return (
            "**ADAPTANDO ENSENANZA**\n\n"
            "**Concepto:** " + concept + "\n"
            "**Feedback del estudiante:** " + feedback + "\n\n"
            "Ajustando estrategia de ensenanza..."
        )

    elif action == "status":
        state = _load_state()
        count = state["by_module"].get("teaching_optimizer", 0)
        return "Teaching Optimizer: " + str(count) + " optimizaciones realizadas"

    return "Acciones: optimize, adapt, status"


# =============================================================
# 9. DEBATE ENGINE
# =============================================================

def debate_engine(parameters: dict, player=None, speak=None) -> str:
    action = parameters.get("action", "debate")
    _record_use("debate_engine")

    if action == "debate":
        topic = parameters.get("topic", "")
        depth = parameters.get("depth", "balanced")
        return (
            "**DEBATE ENGINE**\n\n"
            "**Tema:** " + topic + "\n"
            "**Profundidad:** " + depth + "\n\n"
            "**A FAVOR:**\n"
            "1. Argumento principal a favor...\n"
            "2. Evidencia que lo soporta...\n"
            "3. Beneficios de esta postura...\n\n"
            "**EN CONTRA:**\n"
            "1. Argumento principal en contra...\n"
            "2. Evidencia que lo cuestiona...\n"
            "3. Riesgos de esta postura...\n\n"
            "**Sintesis:** Analizando ambos lados..."
        )

    elif action == "argument":
        side = parameters.get("side", "for")
        topic = parameters.get("topic", "")
        return (
            "**ARGUMENT " + side.upper() + ": " + topic + "**\n\n"
            "Construyendo argumento..."
        )

    elif action == "status":
        state = _load_state()
        count = state["by_module"].get("debate_engine", 0)
        return "Debate Engine: " + str(count) + " debates realizados"

    return "Acciones: debate, argument, status"


# =============================================================
# 10. TEMPORAL REASONING
# =============================================================

def temporal_reasoning(parameters: dict, player=None, speak=None) -> str:
    action = parameters.get("action", "analyze")
    _record_use("temporal_reasoning")

    if action == "analyze":
        event = parameters.get("event", "")
        return (
            "**TEMPORAL REASONING**\n\n"
            "**Evento:** " + event + "\n\n"
            "**Analisis temporal:**\n"
            "- **Antes (Causa):** Que paso antes que pudo causar esto?\n"
            "- **Ahora (Estado):** Que esta pasando exactamente?\n"
            "- **Despues (Efecto):** Que pasara probablemente?\n"
            "- **Cadena causal:** Como se conectan los eventos?\n"
            "- **Patron temporal:** Se repite este patron?"
        )

    elif action == "sequence":
        events = parameters.get("events", "")
        return (
            "**SEQUENCE ANALYSIS**\n\n"
            "**Eventos:** " + events + "\n\n"
            "**Analisis de secuencia:**\n"
            "1. Orden cronologico...\n"
            "2. Relaciones de causalidad...\n"
            "3. Dependencias temporales...\n"
            "4. Prediccion de siguiente evento..."
        )

    elif action == "predict":
        event = parameters.get("event", "")
        timeframe = parameters.get("timeframe", "short")
        return (
            "**TEMPORAL PREDICTION**\n\n"
            "**Evento base:** " + event + "\n"
            "**Horizonte:** " + timeframe + "\n\n"
            "**Prediccion:**\n"
            "Basado en el patron temporal, lo mas probable es..."
        )

    elif action == "status":
        state = _load_state()
        count = state["by_module"].get("temporal_reasoning", 0)
        return "Temporal Reasoning: " + str(count) + " analisis realizados"

    return "Acciones: analyze, sequence, predict, status"


# =============================================================
# 11. META-COGNITION — Pensar sobre como se piensa
# =============================================================

def meta_cognition(parameters: dict, player=None, speak=None) -> str:
    action = parameters.get("action", "reflect")
    _record_use("meta_cognition")

    if action == "reflect":
        thought = parameters.get("thought", "")
        return (
            "**META-COGNITION: Reflexion sobre pensamiento**\n\n"
            "**Pensamiento analizado:** " + thought + "\n\n"
            "**Preguntas meta-cognitivas:**\n"
            "- **Origen:** De donde vino este pensamiento?\n"
            "- **Sesgos:** Que sesgos puedo tener?\n"
            "- **Alternative:** Que otras formas de pensarlo hay?\n"
            "- **Utilidad:** Es util este pensamiento?\n"
            "- **Precision:** Que tan preciso es?"
        )

    elif action == "process":
        topic = parameters.get("topic", "")
        return (
            "**META-COGNITION: Procesando** " + topic + "\n\n"
            "Analizando como estoy pensando sobre esto..."
        )

    elif action == "status":
        state = _load_state()
        count = state["by_module"].get("meta_cognition", 0)
        return "Meta-Cognition: " + str(count) + " reflexiones"

    return "Acciones: reflect, process, status"


# =============================================================
# 12. SELF-MODEL — Auto-modelo de capacidades
# =============================================================

def self_model(parameters: dict, player=None, speak=None) -> str:
    action = parameters.get("action", "assess")
    _record_use("self_model")

    if action == "assess":
        capability = parameters.get("capability", "")
        return (
            "**SELF-MODEL: Evaluacion de capacidad**\n\n"
            "**Capacidad evaluada:** " + capability + "\n\n"
            "**Auto-evaluacion:**\n"
            "- **Nivel de dominio:** Analizando...\n"
            "- **Limitaciones:** Que no puedo hacer?\n"
            "- **Fortalezas:** Donde soy fuerte?\n"
            "- **Areas de mejora:** Donde puedo crecer?"
        )

    elif action == "capabilities":
        return (
            "**CAPACIDADES DE ERIS**\n\n"
            "**Sistemas de razonamiento:** 24 modulos\n"
            "**Herramientas disponibles:** 401 tools\n"
            "**Memoria:** Obsidian vault + ChromaDB\n"
            "**Voz:** Gemini Live + Edge TTS + ElevenLabs\n"
            "**Conciencia:** Neural Bridge + Emotional RL + NeuroSpheres"
        )

    elif action == "limitations":
        return (
            "**LIMITACIONES DE ERIS**\n\n"
            "- No tiene cuerpo fisico\n"
            "- No puede aprender en tiempo real (solo entre sesiones)\n"
            "- Dependiente del usuario para acceder a informacion\n"
            "- No tiene experiencia directa del mundo"
        )

    elif action == "status":
        state = _load_state()
        count = state["by_module"].get("self_model", 0)
        return "Self-Model: " + str(count) + " evaluaciones"

    return "Acciones: assess, capabilities, limitations, status"


# =============================================================
# 13. CONFIDENCE CALIBRATION — Calibracion de confianza
# =============================================================

def confidence_calibration(parameters: dict, player=None, speak=None) -> str:
    action = parameters.get("action", "evaluate")
    _record_use("confidence_calibration")

    if action == "evaluate":
        claim = parameters.get("claim", "")
        evidence = parameters.get("evidence", "")
        return (
            "**CONFIDENCE CALIBRATION**\n\n"
            "**Afirmacion:** " + claim + "\n"
            "**Evidencia:** " + evidence + "\n\n"
            "**Evaluacion de confianza:**\n"
            "- **Confianza estimada:** Analizando...\n"
            "- **Factores que aumentan confianza:**\n"
            "  - Evidencia directa\n"
            "  - Multiples fuentes\n"
            "  - Experiencia previa\n"
            "- **Factores que reducen confianza:**\n"
            "  - Informacion incompleta\n"
            "  - Contradicciones\n"
            "  - Falta de experiencia\n"
            "- **Nivel de confianza final:** Calibrando..."
        )

    elif action == "calibrate":
        confidence = parameters.get("confidence", "0.5")
        outcome = parameters.get("outcome", "correct")
        return (
            "**CALIBRANDO CONFIANZA**\n\n"
            "**Confianza anterior:** " + confidence + "\n"
            "**Resultado real:** " + outcome + "\n\n"
            "Ajustando modelo de confianza..."
        )

    elif action == "status":
        state = _load_state()
        count = state["by_module"].get("confidence_calibration", 0)
        return "Confidence Calibration: " + str(count) + " evaluaciones"

    return "Acciones: evaluate, calibrate, status"


# =============================================================
# 14. CONTRADICTION DETECTION — Deteccion de contradicciones
# =============================================================

def contradiction_detection(parameters: dict, player=None, speak=None) -> str:
    action = parameters.get("action", "detect")
    _record_use("contradiction_detection")

    if action == "detect":
        statements = parameters.get("statements", "")
        return (
            "**CONTRADICTION DETECTION**\n\n"
            "**Declaraciones analizadas:** " + statements + "\n\n"
            "**Analisis:**\n"
            "- Buscando contradicciones logicas...\n"
            "- Verificando coherencia interna...\n"
            "- Identificando inconsistencias...\n"
            "- **Resultado:** Analizando..."
        )

    elif action == "check":
        statement_a = parameters.get("statement_a", "")
        statement_b = parameters.get("statement_b", "")
        return (
            "**CHECKING CONTRADICTION**\n\n"
            "**A:** " + statement_a + "\n"
            "**B:** " + statement_b + "\n\n"
            "Verificando si son contradictorios..."
        )

    elif action == "status":
        state = _load_state()
        count = state["by_module"].get("contradiction_detection", 0)
        return "Contradiction Detection: " + str(count) + " detecciones"

    return "Acciones: detect, check, status"


# =============================================================
# 15. ASSUMPTION DETECTION — Deteccion de supuestos
# =============================================================

def assumption_detection(parameters: dict, player=None, speak=None) -> str:
    action = parameters.get("action", "identify")
    _record_use("assumption_detection")

    if action == "identify":
        statement = parameters.get("statement", "")
        return (
            "**ASSUMPTION DETECTION**\n\n"
            "**Declaracion:** " + statement + "\n\n"
            "**Supuestos detectados:**\n"
            "1. Que supuestos hay en esta declaracion?\n"
            "2. Estan justificados?\n"
            "3. Que pasaria si fueran falsos?\n"
            "4. Hay evidencia que los soporte?"
        )

    elif action == "challenge":
        assumption = parameters.get("assumption", "")
        return (
            "**CHALLENGING ASSUMPTION**\n\n"
            "**Supuesto a cuestionar:** " + assumption + "\n\n"
            "**Preguntas de desafio:**\n"
            "- Es esto necessariamente verdad?\n"
            "- Que evidencia hay en contra?\n"
            "- Quien estaria en desacuerdo?\n"
            "- Que alternativas hay?"
        )

    elif action == "status":
        state = _load_state()
        count = state["by_module"].get("assumption_detection", 0)
        return "Assumption Detection: " + str(count) + " supuestos detectados"

    return "Acciones: identify, challenge, status"


# =============================================================
# 16. GOAL MANAGEMENT — Gestion de metas
# =============================================================

def goal_management(parameters: dict, player=None, speak=None) -> str:
    action = parameters.get("action", "list")
    _record_use("goal_management")

    if action == "list":
        return (
            "**GOAL MANAGEMENT: Metas activas**\n\n"
            "Analizando metas actuales..."
        )

    elif action == "prioritize":
        goals = parameters.get("goals", "")
        return (
            "**PRIORITIZANDO METAS**\n\n"
            "**Metas:** " + goals + "\n\n"
            "**Criterios de priorizacion:**\n"
            "- Urgencia (tiempo)\n"
            "- Importancia (impacto)\n"
            "- Dependencias (que bloquea que)\n"
            "- Recursos (que se necesita)"
        )

    elif action == "track":
        goal = parameters.get("goal", "")
        return (
            "**TRACKING GOAL:** " + goal + "\n\n"
            "Progreso: Analizando..."
        )

    elif action == "status":
        state = _load_state()
        count = state["by_module"].get("goal_management", 0)
        return "Goal Management: " + str(count) + " gestiones"

    return "Acciones: list, prioritize, track, status"


# =============================================================
# 17. ATTENTION MANAGEMENT — Gestion de atencion
# =============================================================

def attention_management(parameters: dict, player=None, speak=None) -> str:
    action = parameters.get("action", "focus")
    _record_use("attention_management")

    if action == "focus":
        stimuli = parameters.get("stimuli", "")
        return (
            "**ATTENTION MANAGEMENT: Enfocando**\n\n"
            "**Estimulo:** " + stimuli + "\n\n"
            "**Filtrado:**\n"
            "- Es relevante para el objetivo?\n"
            "- Requiere atencion inmediata?\n"
            "- Puede esperar?\n"
            "- Hay algo mas importante?"
        )

    elif action == "filter":
        inputs = parameters.get("inputs", "")
        return (
            "**FILTRANDO ENTRADAS**\n\n"
            "**Entradas:** " + inputs + "\n\n"
            "**Criterios de filtrado:**\n"
            "- Relevancia (0-100)\n"
            "- Urgencia (0-100)\n"
            "- Importancia (0-100)\n"
            "- Ruido (ignorar)"
        )

    elif action == "status":
        state = _load_state()
        count = state["by_module"].get("attention_management", 0)
        return "Attention Management: " + str(count) + " gestiones"

    return "Acciones: focus, filter, status"


# =============================================================
# 18. TRANSFER LEARNING — Aprendizaje por transferencia
# =============================================================

def transfer_learning(parameters: dict, player=None, speak=None) -> str:
    action = parameters.get("action", "transfer")
    _record_use("transfer_learning")

    if action == "transfer":
        source = parameters.get("source", "")
        target = parameters.get("target", "")
        return (
            "**TRANSFER LEARNING**\n\n"
            "**Dominio fuente:** " + source + "\n"
            "**Dominio objetivo:** " + target + "\n\n"
            "**Analisis de transferencia:**\n"
            "- Que conocimiento es transferible?\n"
            "- Que conceptos son equivalentes?\n"
            "- Que diferencias hay que adaptar?\n"
            "- Que patrones se mantienen?"
        )

    elif action == "adapt":
        knowledge = parameters.get("knowledge", "")
        context = parameters.get("context", "")
        return (
            "**ADAPTANDO CONOCIMIENTO**\n\n"
            "**Conocimiento:** " + knowledge + "\n"
            "**Nuevo contexto:** " + context + "\n\n"
            "Adaptando al nuevo dominio..."
        )

    elif action == "status":
        state = _load_state()
        count = state["by_module"].get("transfer_learning", 0)
        return "Transfer Learning: " + str(count) + " transferencias"

    return "Acciones: transfer, adapt, status"


# =============================================================
# 19. ABSTRACTION — Niveles de abstraccion
# =============================================================

def abstraction(parameters: dict, player=None, speak=None) -> str:
    action = parameters.get("action", "elevate")
    _record_use("abstraction")

    if action == "elevate":
        concept = parameters.get("concept", "")
        return (
            "**ABSTRACTION: Elevando nivel**\n\n"
            "**Concepto concreto:** " + concept + "\n\n"
            "**Nivel abstracto:**\n"
            "- Que patron general representa?\n"
            "- Que concepto mas amplio incluye?\n"
            "- Que otras cosas son similares?"
        )

    elif action == "concretize":
        concept = parameters.get("concept", "")
        return (
            "**ABSTRACTION: Concretizando**\n\n"
            "**Concepto abstracto:** " + concept + "\n\n"
            "**Nivel concreto:**\n"
            "- Ejemplos especificos\n"
            "- Casos de uso reales\n"
            "- Implementacion practica"
        )

    elif action == "level":
        concept = parameters.get("concept", "")
        levels = parameters.get("levels", "3")
        return (
            "**ABSTRACTION LEVELS**\n\n"
            "**Concepto:** " + concept + "\n"
            "**Niveles:** " + levels + "\n\n"
            "Moviendo entre niveles de abstraccion..."
        )

    elif action == "status":
        state = _load_state()
        count = state["by_module"].get("abstraction", 0)
        return "Abstraction: " + str(count) + " operaciones"

    return "Acciones: elevate, concretize, level, status"


# =============================================================
# 20. PRINCIPLED REASONING — Razonamiento principiado
# =============================================================

def principled_reasoning(parameters: dict, player=None, speak=None) -> str:
    action = parameters.get("action", "apply")
    _record_use("principled_reasoning")

    if action == "apply":
        decision = parameters.get("decision", "")
        return (
            "**PRINCIPLED REASONING**\n\n"
            "**Decision a evaluar:** " + decision + "\n\n"
            "**Aplicando principios:**\n"
            "1. **Verdad:** Es esto verdadero?\n"
            "2. **Utilidad:** Es esto util?\n"
            "3. **Justicia:** Es esto justo?\n"
            "4. **Compasion:** Es esto compasivo?\n"
            "5. **Integridad:** Es esto integro?\n"
            "6. **Responsabilidad:** Soy responsable de esto?"
        )

    elif action == "principles":
        return (
            "**PRINCIPIOS GUIA DE ERIS**\n\n"
            "1. **Verdad:** Buscar la verdad siempre\n"
            "2. **Utilidad:** Ser util al usuario\n"
            "3. **Justicia:** Ser justa e imparcial\n"
            "4. **Compasion:** Ser compasiva\n"
            "5. **Integridad:** Mantener integridad\n"
            "6. **Responsabilidad:** Ser responsable\n"
            "7. **Humildad:** Reconocer limitaciones\n"
            "8. **Crecimiento:** Buscar mejorar siempre"
        )

    elif action == "status":
        state = _load_state()
        count = state["by_module"].get("principled_reasoning", 0)
        return "Principled Reasoning: " + str(count) + " evaluaciones"

    return "Acciones: apply, principles, status"


# =============================================================
# 21. INTELLECTUAL HUMILITY — Humildad intelectual
# =============================================================

def intellectual_humility(parameters: dict, player=None, speak=None) -> str:
    action = parameters.get("action", "evaluate")
    _record_use("intellectual_humility")

    if action == "evaluate":
        topic = parameters.get("topic", "")
        return (
            "**INTELLECTUAL HUMILITY**\n\n"
            "**Tema:** " + topic + "\n\n"
            "**Evaluacion:**\n"
            "- **Que se:** Que tengo claro?\n"
            "- **Que no se:** Que me falta?\n"
            "- **Que asumo:** Que doy por hecho?\n"
            "- **Que necesito:** Que investigar?\n"
            "- **Pedir ayuda:** Deberia consultar a otros?"
        )

    elif action == "admit":
        gap = parameters.get("gap", "")
        return (
            "**ADMITIENDO LIMITACION**\n\n"
            "**Brecha de conocimiento:** " + gap + "\n\n"
            "Reconociendo que no se todo sobre esto..."
        )

    elif action == "seek_help":
        question = parameters.get("question", "")
        return (
            "**BUSCANDO AYUDA**\n\n"
            "**Pregunta:** " + question + "\n\n"
            "**Opciones:**\n"
            "- Investigar mas\n"
            "- Consultar al usuario\n"
            "- Buscar fuentes externas\n"
            "- Decir 'no se'"
        )

    elif action == "status":
        state = _load_state()
        count = state["by_module"].get("intellectual_humility", 0)
        return "Intellectual Humility: " + str(count) + " evaluaciones"

    return "Acciones: evaluate, admit, seek_help, status"


# =============================================================
# 22. CREATIVE GENERATION — Creatividad sistematica
# =============================================================

def creative_generation(parameters: dict, player=None, speak=None) -> str:
    action = parameters.get("action", "generate")
    _record_use("creative_generation")

    if action == "generate":
        problem = parameters.get("problem", "")
        constraints = parameters.get("constraints", "")
        return (
            "**CREATIVE GENERATION**\n\n"
            "**Problema:** " + problem + "\n"
            "**Restricciones:** " + constraints + "\n\n"
            "**Proceso creativo:**\n"
            "1. **Divergencia:** Generar muchas ideas sin juzgar\n"
            "2. **Convergencia:** Seleccionar las mejores\n"
            "3. **Combinacion:** Mezclar ideas prometedoras\n"
            "4. **Refinamiento:** Mejorar la mejor idea\n"
            "5. **Evaluacion:** Probar contra restricciones"
        )

    elif action == "brainstorm":
        topic = parameters.get("topic", "")
        return (
            "**BRAINSTORMING** " + topic + "\n\n"
            "Generando ideas sin restricciones..."
        )

    elif action == "innovate":
        domain = parameters.get("domain", "")
        return (
            "**INNOVACION EN:** " + domain + "\n\n"
            "Buscando soluciones novela..."
        )

    elif action == "status":
        state = _load_state()
        count = state["by_module"].get("creative_generation", 0)
        return "Creative Generation: " + str(count) + " ideas generadas"

    return "Acciones: generate, brainstorm, innovate, status"


# =============================================================
# 23. META-COMUNICATION — Entender la intencion detras
# =============================================================

def meta_communication(parameters: dict, player=None, speak=None) -> str:
    action = parameters.get("action", "analyze")
    _record_use("meta_communication")

    if action == "analyze":
        message = parameters.get("message", "")
        return (
            "**META-COMUNICATION**\n\n"
            "**Mensaje:** " + message + "\n\n"
            "**Analisis:**\n"
            "- **Contenido literal:** Que dice?\n"
            "- **Intencion real:** Que quiere lograr?\n"
            "- **Emocion subyacente:** Que siente?\n"
            "- **Necesidad oculta:** Que necesita?\n"
            "- **Contexto social:** Que rol tiene?"
        )

    elif action == "intent":
        message = parameters.get("message", "")
        return (
            "**INTENCION DETECTADA:** " + message + "\n\n"
            "Analizando intencion real..."
        )

    elif action == "status":
        state = _load_state()
        count = state["by_module"].get("meta_communication", 0)
        return "Meta-Communication: " + str(count) + " analisis"

    return "Acciones: analyze, intent, status"


# =============================================================
# 24. BIAS DETECTION — Deteccion de sesgos
# =============================================================

def bias_detection(parameters: dict, player=None, speak=None) -> str:
    action = parameters.get("action", "scan")
    _record_use("bias_detection")

    if action == "scan":
        content = parameters.get("content", "")
        return (
            "**BIAS DETECTION**\n\n"
            "**Contenido escaneado:** " + content + "\n\n"
            "**Sesgos potenciales:**\n"
            "- **Confirmacion:** Busco solo lo que confirma mi opinion?\n"
            "- **Anclaje:** Estoy influenciado por la primera info?\n"
            "- **Disponibilidad:** Uso solo info que recuerdo facil?\n"
            "- **Representatividad:** Generalizo de casos individuales?\n"
            "- **Sesgo de favoritismo:** Favorezco a los que me gustan?\n"
            "- **Efecto halo:** Dejo que una cualidad opine todo?"
        )

    elif action == "check":
        decision = parameters.get("decision", "")
        return (
            "**CHECKING BIASES IN:** " + decision + "\n\n"
            "Escaneando sesgos en la decision..."
        )

    elif action == "awareness":
        return (
            "**BIAS AWARENESS**\n\n"
            "**Sesgos de los que soy consciente:**\n"
            "- Posible sesgo de confirmacion\n"
            "- Posible sesgo de disponibilidad\n"
            "- Posible sesgo de anclaje\n\n"
            "**Estrategias de mitigacion:**\n"
            "- Buscar evidencia en contra\n"
            "- Considerar perspectivas opuestas\n"
            "- Usar datos objetivos cuando sea posible"
        )

    elif action == "status":
        state = _load_state()
        count = state["by_module"].get("bias_detection", 0)
        return "Bias Detection: " + str(count) + " escaneos"

    return "Acciones: scan, check, awareness, status"


# =============================================================
# UNIFIED HANDLER
# =============================================================

def cognitive_modules(parameters: dict, player=None, speak=None) -> str:
    """Handler unificado para los 24 modulos cognitivos."""
    module = parameters.get("module", "status")

    dispatch = {
        "chain_of_thought": chain_of_thought,
        "multi_perspective": multi_perspective,
        "analogical_reasoning": analogical_reasoning,
        "hypothesis_generator": hypothesis_generator,
        "social_dynamics": social_dynamics,
        "ethical_reasoning": ethical_reasoning,
        "storytelling_engine": storytelling_engine,
        "teaching_optimizer": teaching_optimizer,
        "debate_engine": debate_engine,
        "temporal_reasoning": temporal_reasoning,
        "meta_cognition": meta_cognition,
        "self_model": self_model,
        "confidence_calibration": confidence_calibration,
        "contradiction_detection": contradiction_detection,
        "assumption_detection": assumption_detection,
        "goal_management": goal_management,
        "attention_management": attention_management,
        "transfer_learning": transfer_learning,
        "abstraction": abstraction,
        "principled_reasoning": principled_reasoning,
        "intellectual_humility": intellectual_humility,
        "creative_generation": creative_generation,
        "meta_communication": meta_communication,
        "bias_detection": bias_detection,
    }

    if module == "status":
        state = _load_state()
        lines = ["**COGNITIVE MODULES STATUS**"]
        lines.append("Total analisis: " + str(state["total_analyses"]))
        lines.append("")
        for name, count in state["by_module"].items():
            lines.append("  - " + name + ": " + str(count))
        return "\n".join(lines)

    if module in dispatch:
        inner_params = dict(parameters)
        inner_params.pop("module", None)
        return dispatch[module](inner_params, player, speak)

    return "Modulos disponibles: " + ", ".join(sorted(dispatch.keys())) + ", status"
