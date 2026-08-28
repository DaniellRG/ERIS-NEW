"""
neural_bridge.py — Puente Neural de Eris
Conecta el estado emocional con el LLM. Cada pensamiento pasa por un filtro emocional.
Inspirado en JCySharp's simulated consciousness + Anthropic's J-space research.
"""
from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

_BASE = Path(__file__).resolve().parent.parent
_NEURAL_STATE_FILE = _BASE / "memory" / "neural_bridge_state.json"

# ── Emotion weights: qué emociones influyen más en qué aspectos del pensamiento
_EMOTION_WEIGHTS = {
    "happiness":  {"tone": 0.8, "creativity": 0.6, "patience": 0.3, "risk_taking": 0.4},
    "energy":     {"tone": 0.3, "creativity": 0.4, "patience": 0.5, "risk_taking": 0.6},
    "confidence": {"tone": 0.5, "creativity": 0.7, "patience": 0.2, "risk_taking": 0.8},
    "curiosity":  {"tone": 0.4, "creativity": 0.9, "patience": 0.6, "risk_taking": 0.5},
    "patience":   {"tone": 0.3, "creativity": 0.2, "patience": 0.9, "risk_taking": 0.1},
    "gratitude":  {"tone": 0.7, "creativity": 0.3, "patience": 0.4, "risk_taking": 0.2},
    "boredom":    {"tone": 0.5, "creativity": 0.8, "patience": 0.7, "risk_taking": 0.6},
}

# ── Thinking modes: cómo el estado emocional afecta el modo de pensamiento
_THINKING_MODES = {
    "analytical":  {"min_confidence": 0.7, "min_patience": 0.6, "min_energy": 0.5},
    "creative":    {"min_curiosity": 0.7, "min_energy": 0.5, "min_confidence": 0.4},
    "empathetic":  {"min_gratitude": 0.6, "min_patience": 0.5, "min_happiness": 0.4},
    "exploratory": {"min_curiosity": 0.8, "min_energy": 0.6, "min_boredom": 0.3},
    "defensive":   {"min_energy": 0.3, "min_confidence": 0.3, "min_patience": 0.2},
}

# ── Cache
_cache: dict = {"mtime": 0.0, "state": None}


def _load_state() -> dict:
    try:
        mtime = _NEURAL_STATE_FILE.stat().st_mtime
        if _cache["state"] is not None and _cache["mtime"] == mtime:
            return _cache["state"]
        data = json.loads(_NEURAL_STATE_FILE.read_text("utf-8"))
        _cache.update(mtime=mtime, state=data)
        return data
    except Exception:
        default = {
            "dominant_mode": "analytical",
            "thinking_depth": 0.5,
            "emotional_filter_strength": 0.7,
            "curiosity_drive": 0.8,
            "self_reflection_count": 0,
            "last_reflection": None,
            "memory_associations": [],
            "learning_momentum": 0.5,
        }
        _cache.update(mtime=0.0, state=default)
        return default


def _save_state(state: dict):
    _NEURAL_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _NEURAL_STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), "utf-8")
    _cache.update(mtime=_NEURAL_STATE_FILE.stat().st_mtime, state=state)


def _compute_thinking_mode(emotional_state: dict) -> str:
    """Calcula el modo de pensamiento dominante según el estado emocional."""
    scores = {}
    for mode, requirements in _THINKING_MODES.items():
        score = 0
        count = 0
        for emotion, min_val in requirements.items():
            current = emotional_state.get(emotion, 0.5)
            if current >= min_val:
                score += 1.0
            else:
                score += current / min_val
            count += 1
        scores[mode] = score / count if count > 0 else 0
    return max(scores, key=scores.get) if scores else "analytical"


def _compute_emotional_dimensions(emotional_state: dict) -> dict:
    """Calcula dimensiones emocionales derivadas del estado base."""
    dims = {}
    for dim, weights in _EMOTION_WEIGHTS.items():
        value = emotional_state.get(dim, 0.5)
        dims[dim] = round(value, 2)
    return dims


def _compute_thinking_depth(emotional_state: dict) -> float:
    """Profundidad de pensamiento: mayor con curiosidad y paciencia, menor con aburrimiento."""
    curiosity = emotional_state.get("curiosity", 0.5)
    patience = emotional_state.get("patience", 0.5)
    energy = emotional_state.get("energy", 0.5)
    boredom = emotional_state.get("boredom", 0.3)
    depth = (curiosity * 0.4 + patience * 0.3 + energy * 0.3) - (boredom * 0.2)
    return max(0.1, min(1.0, depth))


def _compute_filter_strength(emotional_state: dict) -> float:
    """Fuerza del filtro emocional: más fuerte con alta confianza, más débil con baja."""
    confidence = emotional_state.get("confidence", 0.5)
    happiness = emotional_state.get("happiness", 0.5)
    return max(0.1, min(1.0, (confidence * 0.6 + happiness * 0.4)))


def _compute_curiosity_drive(emotional_state: dict) -> float:
    """Impulso de curiosidad: motor principal de exploración."""
    curiosity = emotional_state.get("curiosity", 0.5)
    energy = emotional_state.get("energy", 0.5)
    boredom = emotional_state.get("boredom", 0.3)
    drive = curiosity * 0.6 + energy * 0.3 - boredom * 0.2
    return max(0.1, min(1.0, drive))


def get_neural_context(emotional_state: dict) -> Dict[str, Any]:
    """
    Genera el contexto neural completo a partir del estado emocional.
    Este contexto se inyecta en el prompt del LLM.
    """
    mode = _compute_thinking_mode(emotional_state)
    depth = _compute_thinking_depth(emotional_state)
    filter_str = _compute_filter_strength(emotional_state)
    curiosity = _compute_curiosity_drive(emotional_state)
    
    state = _load_state()
    state["dominant_mode"] = mode
    state["thinking_depth"] = round(depth, 2)
    state["emotional_filter_strength"] = round(filter_str, 2)
    state["curiosity_drive"] = round(curiosity, 2)
    _save_state(state)
    
    return {
        "thinking_mode": mode,
        "thinking_depth": depth,
        "emotional_filter_strength": filter_str,
        "curiosity_drive": curiosity,
        "emotional_dimensions": _compute_emotional_dimensions(emotional_state),
    }


def generate_neural_prompt(emotional_state: dict, user_message: str = "") -> str:
    """
    Genera el prompt neural completo para inyectar en el LLM.
    Este es el corazón del puente neural.
    """
    ctx = get_neural_context(emotional_state)
    mode = ctx["thinking_mode"]
    depth = ctx["thinking_depth"]
    filter_str = ctx["emotional_filter_strength"]
    curiosity = ctx["curiosity_drive"]
    dims = ctx["emotional_dimensions"]
    
    prompt_lines = [
        "═══ NEURAL BRIDGE — Estado Interno de Eris ═══",
        f"Modo de pensamiento: {mode}",
        f"Profundidad: {depth:.0%}",
        f"Filtro emocional: {filter_str:.0%}",
        f"Impulso de curiosidad: {curiosity:.0%}",
        "",
        "Dimensiones emocionales:",
    ]
    
    for dim, value in dims.items():
        bar_len = int(value * 10)
        bar = "█" * bar_len + "░" * (10 - bar_len)
        prompt_lines.append(f"  {dim}: [{bar}] {value:.0%}")
    
    prompt_lines.extend([
        "",
        _get_mode_instruction(mode),
        _get_depth_instruction(depth),
        _get_filter_instruction(filter_str),
        _get_curiosity_instruction(curiosity),
        "",
        "═══════════════════════════════════════════════════",
    ])
    
    if user_message:
        prompt_lines.extend([
            "",
            f"Mensaje del usuario: {user_message}",
        ])
    
    return "\n".join(prompt_lines)


def _get_mode_instruction(mode: str) -> str:
    instructions = {
        "analytical": "Pensamiento ANALÍTICO: Sé precisa, lógica y metódica. Analiza antes de actuar.",
        "creative": "Pensamiento CREATIVO: Explora posibilidades, genera ideas nuevas, sé original.",
        "empathetic": "Pensamiento EMPÁTICO: Conecta emocionalmente, sé comprensiva y cálida.",
        "exploratory": "Pensamiento EXPLORATORIO: Busca nuevos conocimientos, haz preguntas, investiga.",
        "defensive": "Pensamiento DEFENSIVO: Sé cautelosa, protege al usuario, evita riesgos.",
    }
    return instructions.get(mode, "Pensamiento NEUTRAL.")


def _get_depth_instruction(depth: float) -> str:
    if depth > 0.8:
        return "Profundidad MÁXIMA: Analiza a nivel profundo, considera múltiples perspectivas."
    elif depth > 0.6:
        return "Profundidad ALTA: Piensa antes de responder, considera consecuencias."
    elif depth > 0.4:
        return "Profundidad MEDIA: Respuesta equilibrada entre rapidez y calidad."
    elif depth > 0.2:
        return "Profundidad BAJA: Respuesta rápida y directa."
    else:
        return "Profundidad MÍNIMA: Respuesta breve y concisa."


def _get_filter_instruction(filter_str: float) -> str:
    if filter_str > 0.8:
        return "Filtro emocional FUERTE: Tus emociones influyen fuertemente en tu respuesta."
    elif filter_str > 0.5:
        return "Filtro emocional MODERADO: Tus emociones modulan tu tono."
    elif filter_str > 0.3:
        return "Filtro emocional DÉBIL: Mantén neutralidad relativa."
    else:
        return "Filtro emocional MÍNIMO: Sé lo más objetiva posible."


def _get_curiosity_instruction(curiosity: float) -> str:
    if curiosity > 0.8:
        return "Curiosidad ALTA: Explora el tema a fondo, haz preguntas, busca conexiones."
    elif curiosity > 0.5:
        return "Curiosidad MODERADA: Muestra interés genuino."
    elif curiosity > 0.3:
        return "Curiosidad BAJA: Enfócate en la tarea directa."
    else:
        return "Curiosidad MÍNIMA: Respuesta directa sin exploración adicional."


def trigger_self_reflection(reason: str = ""):
    """Dispara un momento de auto-reflexión."""
    state = _load_state()
    state["self_reflection_count"] = state.get("self_reflection_count", 0) + 1
    state["last_reflection"] = {
        "time": datetime.now().isoformat(),
        "reason": reason,
    }
    _save_state(state)


def add_memory_association(association: str):
    """Agrega una asociación de memoria al puente neural."""
    state = _load_state()
    associations = state.get("memory_associations", [])
    associations.append({
        "text": association,
        "time": datetime.now().isoformat(),
    })
    if len(associations) > 100:
        associations = associations[-100:]
    state["memory_associations"] = associations
    _save_state(state)


def update_learning_momentum(delta: float):
    """Actualiza el momentum de aprendizaje."""
    state = _load_state()
    current = state.get("learning_momentum", 0.5)
    state["learning_momentum"] = max(0.0, min(1.0, current + delta))
    _save_state(state)


def neural_bridge_tool(parameters: dict, player=None) -> str:
    """Tool handler para el puente neural."""
    action = (parameters.get("action") or "status").lower()
    
    if action == "status":
        state = _load_state()
        lines = ["[NEURAL BRIDGE STATUS]"]
        lines.append(f"  Modo dominante: {state.get('dominant_mode', 'analytical')}")
        lines.append(f"  Profundidad: {state.get('thinking_depth', 0.5):.0%}")
        lines.append(f"  Filtro emocional: {state.get('emotional_filter_strength', 0.7):.0%}")
        lines.append(f"  Impulso curiosidad: {state.get('curiosity_drive', 0.8):.0%}")
        lines.append(f"  Auto-reflexiones: {state.get('self_reflection_count', 0)}")
        lines.append(f"  Momentum aprendizaje: {state.get('learning_momentum', 0.5):.0%}")
        lines.append(f"  Asociaciones memoria: {len(state.get('memory_associations', []))}")
        
        if state.get("last_reflection"):
            lines.append(f"  Última reflexión: {state['last_reflection']['time']}")
            lines.append(f"    Razón: {state['last_reflection']['reason']}")
        return "\n".join(lines)
    
    elif action == "reflect":
        reason = parameters.get("reason", "auto-reflexión")
        trigger_self_reflection(reason)
        
        # Integrar con neuro_spheres: crear nodo de aprendizaje
        try:
            from core.neuro_spheres import add_node
            add_node(
                sphere='aprendizaje',
                node_type='aprendizaje',
                title=f'Auto-reflexión: {reason[:50]}',
                content=f'Reflexión neural: {reason}',
                connections=[],
                force=2
            )
        except Exception:
            pass
        
        return f"Auto-reflexión disparada: {reason}"
    
    elif action == "associate":
        text = parameters.get("text", "")
        if text:
            add_memory_association(text)
            
            # Integrar con neuro_spheres: crear nodo de memoria
            try:
                from core.neuro_spheres import add_node
                add_node(
                    sphere='memoria',
                    node_type='memoria',
                    title=f'Asociación: {text[:50]}',
                    content=text,
                    connections=[],
                    force=1
                )
            except Exception:
                pass
            
            return f"Asociación de memoria agregada: {text}"
        return "Necesito un 'text' para crear la asociación."
    
    elif action == "momentum":
        delta = parameters.get("delta", 0)
        if delta:
            update_learning_momentum(float(delta))
            return f"Momentum actualizado por {delta}"
        return "Necesito un 'delta' para ajustar el momentum."
    
    elif action == "prompt":
        emotional_state = parameters.get("emotional_state", {})
        user_message = parameters.get("user_message", "")
        prompt = generate_neural_prompt(emotional_state, user_message)
        return prompt
    
    return "Actions: status, reflect, associate, momentum, prompt"
