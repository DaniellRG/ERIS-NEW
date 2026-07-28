# -*- coding: utf-8 -*-
"""
Eris Self-Learning – Sistema de aprendizaje progresivo.
Eris mejora su desempeño con cada tarea completada, detecta patrones y optimiza su comportamiento.
"""
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

LEARN_FILE = Path(__file__).resolve().parent.parent / "config" / "eris_learning.json"

def _load():
    try:
        if LEARN_FILE.exists():
            return json.loads(LEARN_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {
        "patterns": {},
        "skills": {},
        "sessions": [],
        "total_learning_time": 0,
        "current_session_start": None,
        "mistakes": [],
        "achievements": []
    }

def _save(data):
    LEARN_FILE.parent.mkdir(parents=True, exist_ok=True)
    LEARN_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def learn_session(parameters: dict, player=None) -> str:
    """
    Sistema de aprendizaje progresivo de Eris.
    
    Acciones:
      - start: Iniciar sesión de aprendizaje
      - status: Ver progreso de aprendizaje
      - pattern: Registrar un patrón detectado
      - skill: Mejorar una habilidad
      - mistakes: Ver errores cometidos y lecciones aprendidas
      - achievements: Ver logros desbloqueados
    """
    action = parameters.get("action", "status").lower()
    data = _load()
    
    if action == "start":
        if data["current_session_start"]:
            # Cerrar sesión anterior
            elapsed = (datetime.now() - datetime.fromisoformat(data["current_session_start"])).total_seconds() / 60
            data["total_learning_time"] += elapsed
        
        data["current_session_start"] = datetime.now().isoformat()
        data["sessions"].append({"start": data["current_session_start"], "tasks": 0, "learned": 0})
        _save(data)
        
        total_h = data["total_learning_time"] / 60
        return f"🧠 Sesión de aprendizaje iniciada. Tiempo total acumulado: {total_h:.1f} horas."
    
    elif action == "status":
        total_h = data["total_learning_time"] / 60
        if data["current_session_start"]:
            elapsed = (datetime.now() - datetime.fromisoformat(data["current_session_start"])).total_seconds() / 60
            total_h += elapsed / 60
        
        result = "**🧠 Estado de Aprendizaje de Eris:**\n\n"
        result += f"  Tiempo total aprendiendo: {total_h:.1f} horas\n"
        result += f"  Sesiones: {len(data['sessions'])}\n"
        result += f"  Patrones detectados: {len(data['patterns'])}\n"
        result += f"  Habilidades desarrolladas: {len(data['skills'])}\n"
        result += f"  Errores cometidos: {len(data['mistakes'])}\n"
        result += f"  Logros: {len(data['achievements'])}\n\n"
        
        if data["skills"]:
            result += "**Habilidades:**\n"
            for name, level in sorted(data["skills"].items(), key=lambda x: -x[1]):
                bar = "█" * int(level / 10) + "░" * (10 - int(level / 10))
                result += f"  {name:20s} [{bar}] {level}%\n"
        
        # Nivel general
        total_tasks = sum(p.get("count", 0) for p in data["patterns"].values())
        if total_tasks >= 100:
            nivel = "🧠 Experto"
        elif total_tasks >= 50:
            nivel = "📈 Avanzado"
        elif total_tasks >= 20:
            nivel = "📚 Intermedio"
        elif total_tasks >= 5:
            nivel = "🌱 Principiante"
        else:
            nivel = "🐣 Novato"
        
        result += f"\n  Nivel general: **{nivel}**"
        
        return result
    
    elif action == "pattern":
        pattern_name = parameters.get("pattern_name", "")
        pattern_type = parameters.get("pattern_type", "task")
        
        if not pattern_name:
            return "Error: Se requiere pattern_name."
        
        if pattern_name not in data["patterns"]:
            data["patterns"][pattern_name] = {"type": pattern_type, "count": 0, "first_seen": datetime.now().isoformat()}
        
        data["patterns"][pattern_name]["count"] += 1
        data["patterns"][pattern_name]["last_seen"] = datetime.now().isoformat()
        
        count = data["patterns"][pattern_name]["count"]
        
        # Si el patrón se ha visto muchas veces, Eris aprende a predecirlo
        if count >= 10 and pattern_name not in data["skills"]:
            data["skills"][pattern_name] = min(100, count * 5)
            data["achievements"].append({
                "name": f"Maestría en {pattern_name}",
                "unlocked_at": datetime.now().isoformat(),
                "description": f"Patrón '{pattern_name}' dominado ({count} repeticiones)"
            })
        
        _save(data)
        return f"🔍 Patrón '{pattern_name}' registrado ({count} ocurrencias)."
    
    elif action == "skill":
        skill_name = parameters.get("skill_name", "")
        increase = int(parameters.get("increase", 5))
        
        if not skill_name:
            return "Error: Se requiere skill_name."
        
        if skill_name not in data["skills"]:
            data["skills"][skill_name] = 0
        
        data["skills"][skill_name] = min(100, data["skills"][skill_name] + increase)
        _save(data)
        
        level = data["skills"][skill_name]
        return f"📈 Habilidad '{skill_name}' mejorada a {level}%."
    
    elif action == "mistakes":
        if not data["mistakes"]:
            return "✅ Ningún error registrado. ¡Eris está aprendiendo bien!"
        
        result = "**📝 Lecciones aprendidas de errores:**\n\n"
        for m in data["mistakes"][-10:]:
            result += f"  ❌ {m['error'][:80]}\n"
            result += f"     💡 Lección: {m.get('lesson', 'Analizando...')[:80]}\n"
        
        return result
    
    elif action == "achievements":
        if not data["achievements"]:
            return "🏆 Aún no hay logros. ¡Sigue aprendiendo!"
        
        result = "**🏆 Logros de Eris:**\n\n"
        for a in data["achievements"][-10:]:
            result += f"  ⭐ {a['name']}\n"
            result += f"     {a.get('description', '')}\n"
        
        return result
    
    return f"Acción '{action}' no reconocida."


def learn_from_mistake(parameters: dict, player=None) -> str:
    """Registrar un error y la lección aprendida."""
    error = parameters.get("error", "")
    lesson = parameters.get("lesson", "")
    
    if not error:
        return "Error: Se requiere describir el error."
    
    data = _load()
    data["mistakes"].append({
        "error": error,
        "lesson": lesson or "Pendiente de análisis",
        "timestamp": datetime.now().isoformat()
    })
    
    if len(data["mistakes"]) > 200:
        data["mistakes"] = data["mistakes"][-100:]
    
    _save(data)
    return f"📝 Error registrado. Lección: {lesson or 'En análisis...'}"
