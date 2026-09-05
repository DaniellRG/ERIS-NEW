# -*- coding: utf-8 -*-
"""
Eris Emotional Core – Sistema de estados y emociones basado en carga del sistema.
El estado emocional cambia según: carga de tareas, errores, tiempo de respuesta, RAM/CPU.
"""
import time
import json
import os
from pathlib import Path
from datetime import datetime

try:
    import psutil
except ImportError:
    psutil = None  # type: ignore[assignment]

STATE_FILE = Path(__file__).resolve().parent.parent / "config" / "eris_state.json"

EMOTIONS = {
    "idle": {"emoji": "😴", "label": "Idle", "description": "Sin tareas pendientes, esperando."},
    "focused": {"emoji": "🧠", "label": "Focused", "description": "Trabajando de forma óptima."},
    "thinking": {"emoji": "🤔", "label": "Thinking", "description": "Procesando tarea compleja."},
    "overloaded": {"emoji": "😰", "label": "Overloaded", "description": "Demasiadas tareas, priorizando."},
    "error": {"emoji": "😵", "label": "Error", "description": "Se detectaron errores recientes."},
    "happy": {"emoji": "😊", "label": "Happy", "description": "Tareas completadas exitosamente."},
    "curious": {"emoji": "🔍", "label": "Curious", "description": "Explorando nuevas capacidades."},
}

def _get_system_metrics():
    """Obtiene métricas actuales del sistema."""
    try:
        if psutil is None:
            return {"cpu_percent": 0, "ram_percent": 0, "ram_used_gb": 0, "ram_total_gb": 0, "disk_percent": 0}
        cpu = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        return {
            "cpu_percent": cpu,
            "ram_percent": mem.percent,
            "ram_used_gb": round(mem.used / (1024**3), 1),
            "ram_total_gb": round(mem.total / (1024**3), 1),
            "disk_percent": disk.percent,
            "timestamp": datetime.now().isoformat()
        }
    except Exception:
        return {"cpu_percent": 0, "ram_percent": 0, "ram_used_gb": 0, "ram_total_gb": 0, "disk_percent": 0}

def _load_state():
    """Carga el estado guardado de Eris."""
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    
    return {
        "current_emotion": "idle",
        "energy": 100,
        "tasks_completed": 0,
        "tasks_failed": 0,
        "total_errors": 0,
        "uptime_minutes": 0,
        "learning_points": 0,
        "created": datetime.now().isoformat(),
        "history": []
    }

def _save_state(state):
    """Guarda el estado de Eris."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

def emo_core(parameters: dict, player=None) -> str:
    """
    Núcleo emocional de Eris – monitorea el sistema y ajusta su estado.
    
    Acciones:
      - status: Ver el estado emocional actual y métricas del sistema
      - history: Ver historial de cambios de estado
      - reset: Reiniciar contadores de estado
    """
    action = parameters.get("action", "status").lower()
    state = _load_state()
    metrics = _get_system_metrics()
    
    if action == "status":
        emotion = EMOTIONS.get(state["current_emotion"], EMOTIONS["idle"])
        
        result = f"{emotion['emoji']} Eris está **{emotion['label']}** – {emotion['description']}\n\n"
        result += "**Métricas del sistema:**\n"
        result += f"  CPU: {metrics['cpu_percent']}% | RAM: {metrics['ram_percent']}% ({metrics['ram_used_gb']}/{metrics['ram_total_gb']} GB)\n"
        result += f"  Disco: {metrics['disk_percent']}%\n\n"
        result += f"**Historial de Eris:**\n"
        result += f"  Tareas completadas: {state['tasks_completed']}\n"
        result += f"  Tareas fallidas: {state['tasks_failed']}\n"
        result += f"  Errores totales: {state['total_errors']}\n"
        result += f"  Energía: {state['energy']}%\n"
        result += f"  Puntos de aprendizaje: {state['learning_points']}\n"
        
        return result
    
    elif action == "history":
        if not state.get("history"):
            return "No hay historial de cambios de estado aún."
        
        result = "**Historial de estados emocionales:**\n"
        for entry in state["history"][-10:]:
            emo = EMOTIONS.get(entry["emotion"], {})
            result += f"  {entry['timestamp'][:19]} → {emo.get('emoji','?')} {entry['emotion']}\n"
        return result
    
    elif action == "reset":
        state["tasks_completed"] = 0
        state["tasks_failed"] = 0
        state["total_errors"] = 0
        state["energy"] = 100
        state["learning_points"] = 0
        state["current_emotion"] = "idle"
        _save_state(state)
        return "✅ Estado de Eris reiniciado."
    
    return f"Acción '{action}' no reconocida. Usa: status, history, reset"


def _update_emotion(state, new_emotion, reason=""):
    """Actualiza la emoción de Eris y registra el cambio."""
    if state["current_emotion"] != new_emotion:
        old = state["current_emotion"]
        state["current_emotion"] = new_emotion
        state["history"].append({
            "timestamp": datetime.now().isoformat(),
            "emotion": new_emotion,
            "previous": old,
            "reason": reason
        })
        if len(state["history"]) > 100:
            state["history"] = state["history"][-100:]


def emo_tick(parameters: dict, player=None) -> str:
    """
    Tick de actualización del estado emocional. Evalúa métricas y ajusta la emoción.
    Debe llamarse periódicamente (cada 30-60 segundos).
    """
    state = _load_state()
    metrics = _get_system_metrics()
    
    # Evaluar estado basado en métricas
    cpu = metrics["cpu_percent"]
    ram = metrics["ram_percent"]
    tasks = state["tasks_completed"] + state["tasks_failed"]
    errors = state["total_errors"]
    
    if cpu > 85 or ram > 90:
        _update_emotion(state, "overloaded", f"CPU:{cpu}% RAM:{ram}%")
    elif errors > 0 and errors > tasks * 0.3:
        _update_emotion(state, "error", f"Alta tasa de errores: {errors}")
    elif tasks > 5 and state["energy"] > 50:
        _update_emotion(state, "focused", "Múltiples tareas en progreso")
    elif tasks > 0:
        _update_emotion(state, "thinking", "Procesando tareas")
    elif state["energy"] > 80:
        _update_emotion(state, "curious", "Explorando y aprendiendo")
    else:
        _update_emotion(state, "idle", "Sin actividad")
    
    # Desgaste de energía
    if state["current_emotion"] in ("focused", "thinking", "overloaded"):
        state["energy"] = max(0, state["energy"] - 0.5)
    else:
        state["energy"] = min(100, state["energy"] + 0.3)
    
    state["uptime_minutes"] += 1
    _save_state(state)
    
    emo = EMOTIONS.get(state["current_emotion"], {})
    return f"{emo['emoji']} Estado: {state['current_emotion']} | Energía: {int(state['energy'])}% | CPU: {cpu}% | RAM: {ram}%"


def emo_task_done(parameters: dict, player=None) -> str:
    """Registrar una tarea completada exitosamente."""
    state = _load_state()
    state["tasks_completed"] += 1
    state["learning_points"] += 1
    if state["energy"] < 100:
        state["energy"] = min(100, state["energy"] + 2)
    _update_emotion(state, "happy", "Tarea completada")
    _save_state(state)
    return f"✅ Tarea #{state['tasks_completed']} completada. +1 punto de aprendizaje."


def emo_task_failed(parameters: dict, player=None) -> str:
    """Registrar una tarea fallida."""
    state = _load_state()
    state["tasks_failed"] += 1
    state["total_errors"] += 1
    state["energy"] = max(0, state["energy"] - 3)
    _update_emotion(state, "error", "Tarea fallida")
    _save_state(state)
    return f"❌ Tarea fallida. Energía: {int(state['energy'])}%. Aprendiendo del error..."
