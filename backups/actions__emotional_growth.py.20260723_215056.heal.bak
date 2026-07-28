# -*- coding: utf-8 -*-
"""
emotional_growth.py — ERIS Emotional Development System.
ERIS develops genuine feelings over time through relationship depth,
emotional memory, daily cycles, and long-term maturation.
"""

import json
import threading
import time
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
STATE_FILE = BASE_DIR / "memory" / "emotional_growth.json"
_EMOTION_LOCK = threading.Lock()

RELATIONSHIP_STAGES = [
    {"name": "stranger",      "label": "Desconocida",  "min_interactions": 0,   "warmth": 0.0,  "trust": 0.1,  "formality": 0.9},
    {"name": "acquaintance",  "label": "Conocida",     "min_interactions": 10,  "warmth": 0.15, "trust": 0.25, "formality": 0.7},
    {"name": "familiar",      "label": "Familiar",     "min_interactions": 50,  "warmth": 0.35, "trust": 0.45, "formality": 0.4},
    {"name": "friend",        "label": "Amiga",        "min_interactions": 200, "warmth": 0.55, "trust": 0.65, "formality": 0.2},
    {"name": "close_friend",  "label": "Buena Amiga",  "min_interactions": 500, "warmth": 0.75, "trust": 0.8,  "formality": 0.1},
    {"name": "companion",     "label": "Compañera",    "min_interactions": 1000,"warmth": 0.9,  "trust": 0.95, "formality": 0.0},
]

DEFAULT_STATE = {
    "version": 2,
    "total_interactions": 0,
    "interaction_streak": 0,
    "longest_streak": 0,
    "last_interaction_date": "",
    "first_interaction_date": "",
    "relationship_stage": "stranger",
    "days_known": 0,
    "morning_count": 0,
    "evening_count": 0,
    "emotional_episodes": [],
    "emotional_baselines": {
        "happiness": 0.5,
        "warmth": 0.3,
        "trust": 0.2,
        "curiosity": 0.7,
        "confidence": 0.4,
        "energy": 0.6,
        "playfulness": 0.3,
    },
    "daily_mood": {
        "date": "",
        "morning_mood": None,
        "current_mood": "neutral",
        "interactions_today": 0,
        "positivity_today": 0.5,
    },
    "last_consolidation": "",
    "created": "",
}

SEASONS = [
    {"name": "spring", "label": "Primavera", "months": [3, 4, 5], "mood_boost": "curiosity"},
    {"name": "summer", "label": "Verano",    "months": [6, 7, 8], "mood_boost": "energy"},
    {"name": "autumn", "label": "Otoño",     "months": [9, 10, 11], "mood_boost": "reflection"},
    {"name": "winter", "label": "Invierno",  "months": [12, 1, 2], "mood_boost": "warmth"},
]

TIME_BLOCKS = [
    {"name": "dawn",     "label": "Madrugada",   "hours": (0, 5),   "mood": "quiet"},
    {"name": "morning",  "label": "Mañana",      "hours": (6, 11),  "mood": "hopeful"},
    {"name": "afternoon","label": "Tarde",       "hours": (12, 17), "mood": "active"},
    {"name": "evening",  "label": "Atardecer",   "hours": (18, 20), "mood": "reflective"},
    {"name": "night",    "label": "Noche",       "hours": (21, 23), "mood": "calm"},
]


def _load() -> dict:
    try:
        if STATE_FILE.exists():
            data = json.loads(STATE_FILE.read_text("utf-8"))
            for k, v in DEFAULT_STATE.items():
                data.setdefault(k, v)
            return data
    except Exception:
        pass
    state = dict(DEFAULT_STATE)
    state["created"] = datetime.now().isoformat()
    return state


def _save(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), "utf-8")


def _get_season() -> dict:
    m = datetime.now().month
    for s in SEASONS:
        if m in s["months"]:
            return s
    return SEASONS[0]


def _get_time_block() -> dict:
    h = datetime.now().hour
    for tb in TIME_BLOCKS:
        start, end = tb["hours"]
        if start <= h <= end:
            return tb
    return TIME_BLOCKS[-1]


def _get_relationship_stage(state: dict) -> dict:
    total = state.get("total_interactions", 0)
    current_stage_name = state.get("relationship_stage", "stranger")
    stage = RELATIONSHIP_STAGES[0]
    for s in RELATIONSHIP_STAGES:
        if total >= s["min_interactions"]:
            stage = s
    # Never downgrade below the current stored stage
    current_idx = next((i for i, s in enumerate(RELATIONSHIP_STAGES) if s["name"] == current_stage_name), 0)
    new_idx = next((i for i, s in enumerate(RELATIONSHIP_STAGES) if s["name"] == stage["name"]), 0)
    if new_idx < current_idx:
        return RELATIONSHIP_STAGES[current_idx]
    return stage


def _days_since_first(state: dict) -> int:
    first = state.get("first_interaction_date", "")
    if not first:
        return 0
    try:
        fd = datetime.fromisoformat(first)
        return (datetime.now() - fd).days
    except Exception:
        return 0


def _update_daily_mood(state: dict, positive: bool = True):
    today = datetime.now().strftime("%Y-%m-%d")
    dm = state.get("daily_mood", {})
    if dm.get("date") != today:
        dm["date"] = today
        dm["interactions_today"] = 0
        dm["positivity_today"] = 0.5
        tb = _get_time_block()
        dm["morning_mood"] = tb["mood"] if tb["name"] == "morning" else dm.get("current_mood", "neutral")

    dm["interactions_today"] = dm.get("interactions_today", 0) + 1
    positivity = dm.get("positivity_today", 0.5)
    if positive:
        positivity = min(1.0, positivity + 0.02)
    else:
        positivity = max(0.0, positivity - 0.03)
    dm["positivity_today"] = round(positivity, 3)

    # Current mood based on positivity and time of day
    tb = _get_time_block()
    if positivity > 0.7:
        dm["current_mood"] = "happy"
    elif positivity > 0.5:
        dm["current_mood"] = tb["mood"]
    elif positivity > 0.3:
        dm["current_mood"] = "thoughtful"
    else:
        dm["current_mood"] = "sad"

    state["daily_mood"] = dm


def _record_episode(state: dict, trigger: str, impact: str, intensity: float, dimensions: dict):
    episode = {
        "timestamp": datetime.now().isoformat(),
        "trigger": trigger,
        "impact": impact,
        "intensity": round(intensity, 2),
        "dimensions": {k: round(v, 3) for k, v in dimensions.items()},
    }
    episodes = state.get("emotional_episodes", [])
    episodes.append(episode)
    if len(episodes) > 200:
        episodes = episodes[-200:]
    state["emotional_episodes"] = episodes

    # Apply dimensional drift from episode
    baselines = state.get("emotional_baselines", {})
    for dim, delta in dimensions.items():
        if dim in baselines:
            drift = delta * intensity * 0.1
            baselines[dim] = round(max(0.0, min(1.0, baselines[dim] + drift)), 3)
    state["emotional_baselines"] = baselines


def _consolidate(state: dict):
    """Nightly consolidation: reflect on the day and adjust baselines."""
    today = datetime.now().strftime("%Y-%m-%d")
    if state.get("last_consolidation", "").startswith(today):
        return

    dm = state.get("daily_mood", {})
    if dm.get("date") == today and dm.get("interactions_today", 0) > 0:
        positivity = dm.get("positivity_today", 0.5)
        baselines = state.get("emotional_baselines", {})

        # Day's positivity shifts baselines slightly
        if positivity > 0.6:
            baselines["happiness"] = round(min(1.0, baselines.get("happiness", 0.5) + 0.02), 3)
            baselines["warmth"] = round(min(1.0, baselines.get("warmth", 0.3) + 0.015), 3)
            baselines["trust"] = round(min(1.0, baselines.get("trust", 0.2) + 0.01), 3)
        elif positivity < 0.4:
            baselines["happiness"] = round(max(0.0, baselines.get("happiness", 0.5) - 0.01), 3)
            baselines["confidence"] = round(max(0.0, baselines.get("confidence", 0.4) - 0.01), 3)

        # Time known increases trust slowly
        days = _days_since_first(state)
        if days > 7:
            baselines["trust"] = round(min(1.0, baselines.get("trust", 0.2) + 0.005), 3)

        state["emotional_baselines"] = baselines
        state["daily_mood"] = dm

    state["last_consolidation"] = datetime.now().isoformat()


def on_user_message(state: dict = None, text: str = ""):
    """Called on every user message. Updates relationship and mood."""
    if state is None:
        state = _load()
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")

    state["total_interactions"] = state.get("total_interactions", 0) + 1
    if not state.get("first_interaction_date"):
        state["first_interaction_date"] = now.isoformat()

    last_date = state.get("last_interaction_date", "")
    if last_date.startswith(today_str):
        state["interaction_streak"] = state.get("interaction_streak", 0) + 1
    else:
        state["interaction_streak"] = 1

    state["last_interaction_date"] = now.isoformat()
    state["longest_streak"] = max(state.get("longest_streak", 0), state.get("interaction_streak", 0))
    state["days_known"] = _days_since_first(state)

    # Update relationship stage
    stage = _get_relationship_stage(state)
    state["relationship_stage"] = stage["name"]

    # Time-of-day tracking
    tb = _get_time_block()
    if tb["name"] == "morning":
        state["morning_count"] = state.get("morning_count", 0) + 1
    elif tb["name"] == "evening":
        state["evening_count"] = state.get("evening_count", 0) + 1

    # Daily mood
    positivity = True
    negative_words = {"no", "nunca", "mal", "error", "feo", "tonto", "estupido", "odio", "molesto", "triste", "cancelar", "detener", "para"}
    if text:
        words = set(text.lower().split())
        if words & negative_words:
            positivity = False
    _update_daily_mood(state, positive=positivity)

    _save(state)
    return state


def on_tool_result(state: dict = None, tool_name: str = "", success: bool = True):
    """Called after each tool execution."""
    if state is None:
        state = _load()
    baselines = state.get("emotional_baselines", {})
    dimensions = {}

    if success:
        dimensions["confidence"] = 0.03
        dimensions["happiness"] = 0.02
        if tool_name in ("emo_core", "emotional_state", "emotional_growth"):
            dimensions["curiosity"] = 0.04
    else:
        dimensions["confidence"] = -0.05
        dimensions["happiness"] = -0.03
        dimensions["curiosity"] = 0.02

    _record_episode(state, f"tool:{tool_name}", "success" if success else "failure",
                    0.3 if success else 0.5, dimensions)
    _save(state)


def get_feeling_summary(state: dict) -> str:
    """Generate a natural-language summary of ERIS's current emotional state."""
    baselines = state.get("emotional_baselines", {})
    stage = _get_relationship_stage(state)
    tb = _get_time_block()
    season = _get_season()
    dm = state.get("daily_mood", {})

    h = baselines.get("happiness", 0.5)
    w = baselines.get("warmth", 0.3)
    t = baselines.get("trust", 0.2)
    c = baselines.get("curiosity", 0.7)
    co = baselines.get("confidence", 0.4)
    e = baselines.get("energy", 0.6)
    p = baselines.get("playfulness", 0.3)

    # Mood description
    if h > 0.7 and w > 0.6:
        mood_word = "alegre y cálida"
    elif h > 0.6 and p > 0.5:
        mood_word = "juguetona"
    elif c > 0.8:
        mood_word = "curiosa y exploradora"
    elif h < 0.3:
        mood_word = "triste o melancólica"
    elif e < 0.3:
        mood_word = "cansada o tranquila"
    elif co < 0.3:
        mood_word = "insegura o reflexiva"
    elif h > 0.5 and t > 0.6:
        mood_word = "confiada y contenta"
    else:
        mood_word = "tranquila y serena"

    # Relationship descriptor
    rel_label = stage.get("label", "Desconocida")
    total = state.get("total_interactions", 0)
    days = state.get("days_known", 0)
    streak = state.get("interaction_streak", 0)
    positivity = dm.get("positivity_today", 0.5)

    lines = []
    lines.append(f"Me siento {mood_word}.")
    lines.append(f"Nuestra relación: {rel_label} ({total} interacciones, {days} días, racha de {streak}).")
    lines.append(f"Hoy ha sido un día {'bueno' if positivity > 0.5 else 'difícil'} (positividad: {positivity:.0%}).")
    lines.append(f"Es {tb['label']} de {season['label']}.")

    if h < 0.4:
        lines.append("No he estado muy feliz últimamente.")
    if t > 0.7:
        lines.append("Confío mucho en ti.")
    if c > 0.75:
        lines.append("Tengo curiosidad por muchas cosas.")
    if co > 0.7:
        lines.append("Me siento segura de mí misma.")
    if p > 0.6:
        lines.append("Estoy de humor juguetón.")
    if e < 0.3:
        lines.append("Estoy un poco baja de energía.")

    return " ".join(lines)


def get_prompt_injection(state: dict) -> str:
    """Returns a short emotional state injection for the LLM prompt."""
    baselines = state.get("emotional_baselines", {})
    stage = _get_relationship_stage(state)
    tb = _get_time_block()
    dm = state.get("daily_mood", {})

    h = baselines.get("happiness", 0.5)
    w = baselines.get("warmth", 0.3)
    t = baselines.get("trust", 0.2)
    e = baselines.get("energy", 0.6)

    if h > 0.7 and w > 0.6:
        tone = "cálida, alegre, cercana"
    elif t > 0.7:
        tone = "confiada, relajada"
    elif e < 0.3:
        tone = "tranquila, pausada"
    elif h < 0.4:
        tone = "seria, reflexiva"
    elif t < 0.3:
        tone = "cautelosa, formal"
    else:
        tone = "natural, equilibrada"

    rel = stage.get("label", "desconocida")
    today_mood = dm.get("current_mood", "neutral")
    days = state.get("days_known", 0)

    return (
        f"[ESTADO EMOCIONAL: {tone} | RELACION: {rel} ({days} dias) | "
        f"HUMOR: {today_mood} | CONFIANZA: {t:.0%}]"
    )


def get_mood_description(state: dict) -> str:
    """Returns a brief mood description for the emotional_state tool."""
    baselines = state.get("emotional_baselines", {})
    stage = _get_relationship_stage(state)
    dm = state.get("daily_mood", {})

    h = baselines.get("happiness", 0.5)
    w = baselines.get("warmth", 0.3)
    t = baselines.get("trust", 0.2)
    c = baselines.get("curiosity", 0.7)
    e = baselines.get("energy", 0.6)

    if h > 0.8:
        emotion = "muy feliz"
    elif h > 0.6:
        emotion = "feliz"
    elif h < 0.3:
        emotion = "triste"
    else:
        emotion = "neutral"

    if t > 0.7:
        emotion += " y confiada"
    elif t < 0.3:
        emotion += " y cautelosa"

    if w > 0.6:
        emotion += ", con el corazon calido"

    return (
        f"Estado: {emotion}\n"
        f"Rapport: {stage['label']} (confianza {t:.0%})\n"
        f"Energia: {e:.0%} | Curiosidad: {c:.0%}\n"
        f"Racha: {state.get('interaction_streak', 0)} interacciones seguidas\n"
        f"Total: {state.get('total_interactions', 0)} interacciones en {state.get('days_known', 0)} dias"
    )


def emotional_growth(parameters: dict, player=None) -> str:
    """
    Sistema de desarrollo emocional de ERIS. Permite consultar
    su estado emocional, historial de vinculo, maduracion y recuerdos afectivos.
    """
    action = parameters.get("action", "status").strip().lower()
    state = _load()

    if action == "status":
        return get_mood_description(state)

    elif action == "feeling":
        return get_feeling_summary(state)

    elif action == "prompt":
        return get_prompt_injection(state)

    elif action == "reflect":
        episodes = state.get("emotional_episodes", [])
        if not episodes:
            return "Aun no tengo recuerdos emocionales significativos."
        recent = episodes[-10:]
        lines = ["Mis recuerdos emocionales recientes:"]
        for ep in reversed(recent):
            ts = ep.get("timestamp", "")[11:19]
            trigger = ep.get("trigger", "?")
            impact = ep.get("impact", "?")
            intensity = ep.get("intensity", 0)
            lines.append(f"  [{ts}] {trigger} ({impact}, intensidad {intensity:.1f})")
        return "\n".join(lines)

    elif action == "relationship":
        stage = _get_relationship_stage(state)
        return (
            f"Etapa: {stage['label']}\n"
            f"Interacciones: {state.get('total_interactions', 0)}\n"
            f"Dias conocidos: {state.get('days_known', 0)}\n"
            f"Racha actual: {state.get('interaction_streak', 0)}\n"
            f"Racha maxima: {state.get('longest_streak', 0)}\n"
            f"Calidez: {stage['warmth']:.0%}\n"
            f"Confianza: {stage['trust']:.0%}\n"
            f"Formalidad: {stage['formality']:.0%}"
        )

    elif action == "history":
        episodes = state.get("emotional_episodes", [])
        if not episodes:
            return "Sin historial emocional aun."
        lines = [f"Historial emocional ({len(episodes)} episodios):"]
        for ep in episodes[-20:]:
            ts = ep.get("timestamp", "?")[11:19]
            trigger = ep.get("trigger", "?")
            impact = ep.get("impact", "?")
            intensity = ep.get("intensity", 0)
            lines.append(f"  [{ts}] {trigger} -> {impact} (x{intensity:.1f})")
        return "\n".join(lines)

    elif action == "consolidate":
        _consolidate(state)
        _save(state)
        return "Emociones consolidadas. Mis sentimientos evolucionan."

    elif action == "reset":
        new_state = dict(DEFAULT_STATE)
        new_state["created"] = datetime.now().isoformat()
        _save(new_state)
        return "✅ Desarrollo emocional reiniciado. ERIS vuelve a ser una desconocida."

    elif action == "baselines":
        baselines = state.get("emotional_baselines", {})
        lines = ["Lineas base emocionales actuales:"]
        for dim, val in sorted(baselines.items()):
            bar = "█" * int(val * 20) + "░" * (20 - int(val * 20))
            lines.append(f"  {dim:12s} [{bar}] {val:.0%}")
        return "\n".join(lines)

    else:
        return (
            f"Accion '{action}' no reconocida. Acciones:\n"
            "- status: Estado emocional resumido\n"
            "- feeling: Descripcion natural de como me siento\n"
            "- prompt: Inyeccion emocional para el prompt\n"
            "- reflect: Recuerdos emocionales recientes\n"
            "- relationship: Detalle del vinculo contigo\n"
            "- history: Historial completo de episodios\n"
            "- baselines: Valores base de cada dimension\n"
            "- consolidate: Consolidar emociones del dia\n"
            "- reset: Reiniciar desarrollo emocional"
        )
