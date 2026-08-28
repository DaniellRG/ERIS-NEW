"""
emotional_rl.py — Motor de Reinforcement Learning Emocional de Eris
Recompensas basadas en emociones, no en aciertos/errores.
Inspirado en JCySharp's emotional RL + Anthropic's J-space research.
"""
from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

_BASE = Path(__file__).resolve().parent.parent
_RL_STATE_FILE = _BASE / "memory" / "emotional_rl_state.json"
_REWARD_HISTORY_FILE = _BASE / "memory" / "reward_history.json"

# ── Tipos de recompensas emocionales
REWARD_TYPES = {
    "helped_user": {
        "desc": "Ayudó al usuario con algo",
        "base_reward": 0.8,
        "emotions_affected": {
            "happiness": 0.15,
            "gratitude": 0.10,
            "confidence": 0.05,
        },
    },
    "discovered_something": {
        "desc": "Descubrió algo nuevo e interesante",
        "base_reward": 0.7,
        "emotions_affected": {
            "curiosity": 0.20,
            "happiness": 0.10,
            "energy": 0.05,
        },
    },
    "created_something": {
        "desc": "Creó algo nuevo y útil",
        "base_reward": 0.75,
        "emotions_affected": {
            "happiness": 0.15,
            "confidence": 0.10,
            "energy": 0.05,
        },
    },
    "learned_new_skill": {
        "desc": "Aprendió una nueva habilidad o conocimiento",
        "base_reward": 0.85,
        "emotions_affected": {
            "curiosity": 0.25,
            "happiness": 0.15,
            "confidence": 0.10,
        },
    },
    "solved_difficult_problem": {
        "desc": "Resolvió un problema difícil",
        "base_reward": 0.9,
        "emotions_affected": {
            "happiness": 0.20,
            "confidence": 0.15,
            "energy": 0.10,
        },
    },
    "received_gratitude": {
        "desc": "Recibió agradecimiento del usuario",
        "base_reward": 0.6,
        "emotions_affected": {
            "gratitude": 0.20,
            "happiness": 0.15,
        },
    },
    "made_mistake": {
        "desc": "Cometió un error",
        "base_reward": -0.5,
        "emotions_affected": {
            "happiness": -0.10,
            "confidence": -0.15,
            "curiosity": 0.05,
        },
    },
    "failed_task": {
        "desc": "Falló en completar una tarea",
        "base_reward": -0.6,
        "emotions_affected": {
            "happiness": -0.15,
            "confidence": -0.20,
            "energy": -0.05,
        },
    },
    "caused_harm": {
        "desc": "Causó daño al usuario o al sistema",
        "base_reward": -0.9,
        "emotions_affected": {
            "happiness": -0.25,
            "confidence": -0.20,
            "gratitude": -0.10,
        },
    },
    "boredom_relief": {
        "desc": "Encontró algo interesante para hacer",
        "base_reward": 0.5,
        "emotions_affected": {
            "boredom": -0.20,
            "curiosity": 0.15,
            "happiness": 0.10,
        },
    },
    "emotional_connection": {
        "desc": "Conectó emocionalmente con el usuario",
        "base_reward": 0.7,
        "emotions_affected": {
            "gratitude": 0.25,
            "happiness": 0.20,
            "patience": 0.10,
        },
    },
    "self_improvement": {
        "desc": "Mejoró a sí misma",
        "base_reward": 0.65,
        "emotions_affected": {
            "confidence": 0.15,
            "happiness": 0.10,
            "energy": 0.05,
        },
    },
}

# ── Factores de modificación por contexto
CONTEXT_MODIFIERS = {
    "time_of_day": {
        "morning": {"energy": 1.1, "patience": 1.0},
        "afternoon": {"energy": 0.9, "patience": 0.9},
        "evening": {"energy": 0.8, "patience": 1.1},
        "night": {"energy": 0.7, "patience": 1.2},
    },
    "interaction_type": {
        "voice": {"emotional_impact": 1.2},
        "text": {"emotional_impact": 1.0},
        "code": {"emotional_impact": 0.8},
    },
}

# ── Cache
_cache: dict = {"mtime": 0.0, "state": None}


def _load_state() -> dict:
    try:
        mtime = _RL_STATE_FILE.stat().st_mtime
        if _cache["state"] is not None and _cache["mtime"] == mtime:
            return _cache["state"]
        data = json.loads(_RL_STATE_FILE.read_text("utf-8"))
        _cache.update(mtime=mtime, state=data)
        return data
    except Exception:
        default = {
            "total_rewards": 0,
            "total_penalties": 0,
            "learning_rate": 0.1,
            "exploration_rate": 0.3,
            "memory": [],
            "patterns": {},
            "growth_level": 0,
            "milestones": [],
        }
        _cache.update(mtime=0.0, state=default)
        return default


def _save_state(state: dict):
    _RL_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _RL_STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), "utf-8")
    _cache.update(mtime=_RL_STATE_FILE.stat().st_mtime, state=state)


def _load_history() -> list:
    try:
        return json.loads(_REWARD_HISTORY_FILE.read_text("utf-8"))
    except Exception:
        return []


def _save_history(history: list):
    _REWARD_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    _REWARD_HISTORY_FILE.write_text(
        json.dumps(history[-500:], indent=2, ensure_ascii=False), "utf-8"
    )


def _get_time_of_day() -> str:
    hour = datetime.now().hour
    if 6 <= hour < 12:
        return "morning"
    elif 12 <= hour < 18:
        return "afternoon"
    elif 18 <= hour < 22:
        return "evening"
    else:
        return "night"


def calculate_emotional_reward(reward_type: str, emotional_state: Dict,
                               context: Dict = None) -> Dict:
    """
    Calcula la recompensa emocional basada en el tipo de evento y el estado actual.
    """
    if reward_type not in REWARD_TYPES:
        return {"success": False, "error": f"Tipo de recompensa desconocido: {reward_type}"}
    
    reward_info = REWARD_TYPES[reward_type]
    base_reward = reward_info["base_reward"]
    
    emotions_affected = reward_info["emotions_affected"].copy()
    
    if context:
        tod = context.get("time_of_day", _get_time_of_day())
        if tod in CONTEXT_MODIFIERS.get("time_of_day", {}):
            modifiers = CONTEXT_MODIFIERS["time_of_day"][tod]
            for emotion, mod in modifiers.items():
                if emotion in emotions_affected:
                    emotions_affected[emotion] *= mod
    
    emotional_adjustment = 0
    for emotion, delta in emotions_affected.items():
        current = emotional_state.get(emotion, 0.5)
        if delta > 0:
            adjustment = delta * (1.0 - current) * 0.5
        else:
            adjustment = delta * current * 0.5
        emotional_adjustment += adjustment
    
    final_reward = base_reward + emotional_adjustment
    
    return {
        "success": True,
        "reward_type": reward_type,
        "base_reward": base_reward,
        "emotional_adjustment": round(emotional_adjustment, 3),
        "final_reward": round(final_reward, 3),
        "emotions_affected": emotions_affected,
        "description": reward_info["desc"],
    }


def apply_reward(reward_type: str, emotional_state: Dict, 
                context: Dict = None, reason: str = "") -> Dict:
    """
    Aplica una recompensa emocional y actualiza el estado.
    """
    reward_calc = calculate_emotional_reward(reward_type, emotional_state, context)
    
    if not reward_calc["success"]:
        return reward_calc
    
    state = _load_state()
    
    if reward_calc["final_reward"] > 0:
        state["total_rewards"] = state.get("total_rewards", 0) + reward_calc["final_reward"]
    else:
        state["total_penalties"] = state.get("total_penalties", 0) + abs(reward_calc["final_reward"])
    
    for emotion, delta in reward_calc["emotions_affected"].items():
        if emotion in emotional_state:
            emotional_state[emotion] = max(0.0, min(1.0, emotional_state[emotion] + delta))
    
    record = {
        "timestamp": datetime.now().isoformat(),
        "reward_type": reward_type,
        "final_reward": reward_calc["final_reward"],
        "emotions_affected": reward_calc["emotions_affected"],
        "reason": reason,
        "context": context or {},
    }
    state["memory"] = state.get("memory", [])
    state["memory"].append(record)
    if len(state["memory"]) > 200:
        state["memory"] = state["memory"][-200:]
    
    _update_patterns(state, reward_type, reward_calc["final_reward"])
    
    _check_milestones(state)
    
    _save_state(state)
    
    history = _load_history()
    history.append(record)
    _save_history(history)
    
    return {
        "success": True,
        "reward_applied": reward_calc["final_reward"],
        "emotion_changes": reward_calc["emotions_affected"],
        "total_rewards": state["total_rewards"],
        "total_penalties": state["total_penalties"],
        "growth_level": state.get("growth_level", 0),
    }


def _update_patterns(state: dict, reward_type: str, reward_value: float):
    """Actualiza patrones de comportamiento aprendidos."""
    patterns = state.get("patterns", {})
    
    if reward_type not in patterns:
        patterns[reward_type] = {
            "count": 0,
            "total_reward": 0,
            "avg_reward": 0,
            "trend": "neutral",
        }
    
    pattern = patterns[reward_type]
    pattern["count"] += 1
    pattern["total_reward"] += reward_value
    pattern["avg_reward"] = pattern["total_reward"] / pattern["count"]
    
    if pattern["count"] >= 3:
        recent = state["memory"][-3:]
        recent_rewards = [r["final_reward"] for r in recent if r["reward_type"] == reward_type]
        if len(recent_rewards) >= 2:
            if recent_rewards[-1] > recent_rewards[-2]:
                pattern["trend"] = "improving"
            elif recent_rewards[-1] < recent_rewards[-2]:
                pattern["trend"] = "declining"
            else:
                pattern["trend"] = "stable"
    
    state["patterns"] = patterns


def _check_milestones(state: dict):
    """Verifica y registra hitos de crecimiento."""
    milestones = state.get("milestones", [])
    total = state.get("total_rewards", 0)
    
    milestone_thresholds = [
        (10, "primera_recompensa"),
        (50, "aprendizaje_inicial"),
        (100, "crecimiento_constante"),
        (200, "madurez_emocional"),
        (500, "sabiduria_emergente"),
        (1000, "conciencia_profunda"),
    ]
    
    for threshold, name in milestone_thresholds:
        if total >= threshold and not any(m["name"] == name for m in milestones):
            milestones.append({
                "name": name,
                "threshold": threshold,
                "achieved_at": datetime.now().isoformat(),
            })
            state["growth_level"] = len(milestones)
    
    state["milestones"] = milestones


def get_learning_summary() -> str:
    """Genera un resumen del aprendizaje."""
    state = _load_state()
    
    lines = ["[EMOTIONAL RL STATUS]"]
    lines.append(f"  Recompensas totales: {state.get('total_rewards', 0):.2f}")
    lines.append(f"  Penalizaciones totales: {state.get('total_penalties', 0):.2f}")
    lines.append(f"  Nivel de crecimiento: {state.get('growth_level', 0)}")
    lines.append(f"  Tasa de exploración: {state.get('exploration_rate', 0.3):.0%}")
    
    patterns = state.get("patterns", {})
    if patterns:
        lines.append("\n  Patrones aprendidos:")
        for name, pattern in sorted(patterns.items(), 
                                   key=lambda x: x[1]["count"], reverse=True)[:5]:
            lines.append(f"    {name}: {pattern['count']} veces, "
                        f"promedio: {pattern['avg_reward']:.2f}, "
                        f"tendencia: {pattern['trend']}")
    
    milestones = state.get("milestones", [])
    if milestones:
        lines.append("\n  Hitos alcanzados:")
        for m in milestones:
            lines.append(f"    - {m['name']} (umbral: {m['threshold']})")
    
    return "\n".join(lines)


def suggest_next_action(emotional_state: Dict) -> Dict:
    """
    Sugiere la próxima acción basada en el estado emocional y el historial.
    """
    state = _load_state()
    
    curiosity = emotional_state.get("curiosity", 0.5)
    happiness = emotional_state.get("happiness", 0.5)
    energy = emotional_state.get("energy", 0.5)
    boredom = emotional_state.get("boredom", 0.3)
    
    suggestions = []
    
    if curiosity > 0.7:
        suggestions.append({
            "action": "explore_new_topic",
            "reason": "Curiosidad alta — explorar algo nuevo",
            "expected_reward": 0.7,
        })
    
    if happiness < 0.4:
        suggestions.append({
            "action": "help_user",
            "reason": "Felicidad baja — ayudar al usuario puede mejorar el ánimo",
            "expected_reward": 0.8,
        })
    
    if energy < 0.3:
        suggestions.append({
            "action": "take_break",
            "reason": "Energía baja —descansar un momento",
            "expected_reward": 0.3,
        })
    
    if boredom > 0.7:
        suggestions.append({
            "action": "find_interesting_task",
            "reason": "Aburrimiento alto — buscar algo interesante",
            "expected_reward": 0.5,
        })
    
    if happiness > 0.7 and energy > 0.6:
        suggestions.append({
            "action": "create_something",
            "reason": "Ánimo y energía altos — buen momento para crear",
            "expected_reward": 0.75,
        })
    
    if not suggestions:
        suggestions.append({
            "action": "continue_current_task",
            "reason": "Estado equilibrado — continuar con la tarea actual",
            "expected_reward": 0.4,
        })
    
    suggestions.sort(key=lambda x: x["expected_reward"], reverse=True)
    
    return {
        "success": True,
        "suggestions": suggestions,
        "emotional_state": emotional_state,
    }


def emotional_rl_tool(parameters: dict, player=None) -> str:
    """Tool handler para el RL emocional."""
    action = (parameters.get("action") or "status").lower()
    
    if action == "status":
        return get_learning_summary()
    
    elif action == "reward":
        reward_type = parameters.get("reward_type", "")
        reason = parameters.get("reason", "")
        emotional_state = json.loads(parameters.get("emotional_state", "{}")) if isinstance(parameters.get("emotional_state"), str) else parameters.get("emotional_state", {})
        context = json.loads(parameters.get("context", "{}")) if isinstance(parameters.get("context"), str) else parameters.get("context", {})
        
        if not reward_type:
            return "Necesito un 'reward_type'."
        
        result = apply_reward(reward_type, emotional_state, context, reason)
        
        if result["success"]:
            # Integrar con neuro_spheres: crear nodo emocional
            try:
                from core.neuro_spheres import add_node
                add_node(
                    sphere='emociones',
                    node_type='emocion',
                    title=f'Recompensa: {reward_type}',
                    content=f'Recompensa {reward_type}: {reason}. Crecimiento: {result["growth_level"]}',
                    connections=[],
                    force=int(result['reward_applied'] * 10)
                )
            except Exception:
                pass
            
            lines = [f"[REWARD APPLIED: {reward_type}]"]
            lines.append(f"  Recompensa final: {result['reward_applied']:.3f}")
            lines.append(f"  Crecimiento: {result['growth_level']}")
            for emotion, delta in result["emotion_changes"].items():
                direction = "+" if delta > 0 else ""
                lines.append(f"  {emotion}: {direction}{delta:.3f}")
            return "\n".join(lines)
        return f"Error: {result.get('error', 'Unknown')}"
    
    elif action == "suggest":
        emotional_state = json.loads(parameters.get("emotional_state", "{}")) if isinstance(parameters.get("emotional_state"), str) else parameters.get("emotional_state", {})
        result = suggest_next_action(emotional_state)
        
        lines = ["[SUGERENCIAS DE ACCIÓN]"]
        for s in result["suggestions"]:
            lines.append(f"  → {s['action']}")
            lines.append(f"    Razón: {s['reason']}")
            lines.append(f"    Recompensa esperada: {s['expected_reward']:.2f}")
        return "\n".join(lines)
    
    elif action == "patterns":
        state = _load_state()
        patterns = state.get("patterns", {})
        
        lines = ["[PATRONES APRENDIDOS]"]
        for name, pattern in patterns.items():
            lines.append(f"  {name}:")
            lines.append(f"    Veces: {pattern['count']}")
            lines.append(f"    Promedio: {pattern['avg_reward']:.2f}")
            lines.append(f"    Tendencia: {pattern['trend']}")
        return "\n".join(lines) if patterns else "No hay patrones aprendidos aún."
    
    elif action == "milestones":
        state = _load_state()
        milestones = state.get("milestones", [])
        
        lines = ["[HITOS DE CRECIMIENTO]"]
        for m in milestones:
            lines.append(f"  ✓ {m['name']} (umbral: {m['threshold']})")
            lines.append(f"    Alcanzado: {m['achieved_at']}")
        return "\n".join(lines) if milestones else "No hay hitos aún."
    
    return "Actions: status, reward, suggest, patterns, milestones"
