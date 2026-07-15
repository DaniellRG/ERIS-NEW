# -*- coding: utf-8 -*-
"""
Eris Predictive Engine – Anticipa necesidades basándose en patrones de uso.
Aprende rutinas del usuario y prepara el entorno antes de que se lo pidan.
"""
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

PREDICT_FILE = Path(__file__).resolve().parent.parent / "config" / "eris_predictions.json"

def _load():
    try:
        if PREDICT_FILE.exists():
            return json.loads(PREDICT_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {
        "hourly_patterns": {},
        "daily_patterns": {},
        "frequent_actions": {},
        "predictions_made": 0,
        "predictions_correct": 0
    }

def _save(data):
    PREDICT_FILE.parent.mkdir(parents=True, exist_ok=True)
    PREDICT_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def predict_analyze(parameters: dict, player=None) -> str:
    """
    Motor predictivo de Eris – analiza patrones y anticipa necesidades.
    
    Acciones:
      - record: Registrar una acción del usuario para aprender patrones
      - predict: Predecir qué acción es más probable ahora
      - stats: Ver estadísticas de predicciones
      - routine: Ver la rutina diaria detectada
    """
    action = parameters.get("action", "predict").lower()
    data = _load()
    
    if action == "record":
        action_name = parameters.get("action_name", "")
        if not action_name:
            return "Error: Se requiere action_name."
        
        now = datetime.now()
        hour_key = f"{now.hour:02d}:00"
        day_key = now.strftime("%A").lower()
        
        # Registrar patrón horario
        if hour_key not in data["hourly_patterns"]:
            data["hourly_patterns"][hour_key] = {}
        if action_name not in data["hourly_patterns"][hour_key]:
            data["hourly_patterns"][hour_key][action_name] = 0
        data["hourly_patterns"][hour_key][action_name] += 1
        
        # Registrar patrón diario
        if day_key not in data["daily_patterns"]:
            data["daily_patterns"][day_key] = {}
        if action_name not in data["daily_patterns"][day_key]:
            data["daily_patterns"][day_key][action_name] = 0
        data["daily_patterns"][day_key][action_name] += 1
        
        # Registrar frecuencia general
        if action_name not in data["frequent_actions"]:
            data["frequent_actions"][action_name] = 0
        data["frequent_actions"][action_name] += 1
        
        _save(data)
        
        freq = data["frequent_actions"][action_name]
        return f"📊 '{action_name}' registrada ({freq} veces)."
    
    elif action == "predict":
        now = datetime.now()
        hour_key = f"{now.hour:02d}:00"
        day_key = now.strftime("%A").lower()
        
        predictions = []
        
        # Buscar patrones para esta hora
        if hour_key in data["hourly_patterns"]:
            for act, count in sorted(data["hourly_patterns"][hour_key].items(), key=lambda x: -x[1]):
                if count >= 2:
                    confidence = min(95, count * 10)
                    predictions.append((act, confidence, "horario"))
        
        # Buscar patrones para este día
        if day_key in data["daily_patterns"]:
            for act, count in sorted(data["daily_patterns"][day_key].items(), key=lambda x: -x[1]):
                if count >= 2:
                    confidence = min(90, count * 8)
                    predictions.append((act, confidence, "diario"))
        
        if not predictions:
            return "🤷 No hay suficientes datos para predecir. Sigue usando a Eris para que aprenda tus rutinas."
        
        # Mostrar top 3 predicciones
        result = "**🔮 Predicciones de Eris:**\n\n"
        for i, (act, conf, tipo) in enumerate(predictions[:5]):
            bar = "█" * int(conf / 10) + "░" * (10 - int(conf / 10))
            result += f"  {i+1}. **{act}** [{bar}] {conf}% confianza\n"
            result += f"     Basado en patrón {tipo}\n"
        
        # Estadísticas de aciertos
        if data["predictions_made"] > 0:
            accuracy = data["predictions_correct"] / data["predictions_made"] * 100
            result += f"\n  Precisión histórica: {accuracy:.1f}% ({data['predictions_correct']}/{data['predictions_made']})"
        
        return result
    
    elif action == "stats":
        total_predictions = data["predictions_made"]
        correct = data["predictions_correct"]
        accuracy = (correct / total_predictions * 100) if total_predictions > 0 else 0
        
        result = "**📊 Estadísticas Predictivas:**\n\n"
        result += f"  Predicciones hechas: {total_predictions}\n"
        result += f"  Predicciones acertadas: {correct}\n"
        result += f"  Precisión: {accuracy:.1f}%\n"
        result += f"  Patrones horarios: {len(data['hourly_patterns'])} horas con datos\n"
        result += f"  Patrones diarios: {len(data['daily_patterns'])} días con datos\n"
        result += f"  Acciones frecuentes: {len(data['frequent_actions'])}\n\n"
        
        if data["frequent_actions"]:
            result += "**Top 5 acciones más frecuentes:**\n"
            for act, count in sorted(data["frequent_actions"].items(), key=lambda x: -x[1])[:5]:
                result += f"  {act}: {count} veces\n"
        
        return result
    
    elif action == "routine":
        now = datetime.now()
        result = f"**📅 Rutina diaria de Eris ({now.strftime('%A')}):**\n\n"
        
        day_key = now.strftime("%A").lower()
        if day_key in data["daily_patterns"] and data["daily_patterns"][day_key]:
            for act, count in sorted(data["daily_patterns"][day_key].items(), key=lambda x: -x[1])[:8]:
                result += f"  • {act} ({count}x)\n"
        else:
            result += "  Sin datos para hoy aún.\n"
        
        result += "\n**Por horas:**\n"
        for h in range(24):
            hour_key = f"{h:02d}:00"
            if hour_key in data["hourly_patterns"]:
                acts = data["hourly_patterns"][hour_key]
                top_act = max(acts, key=acts.get)
                result += f"  {hour_key}: {top_act} ({acts[top_act]}x)\n"
        
        return result
    
    elif action == "feedback":
        # El usuario confirma si la predicción fue correcta
        was_correct = parameters.get("correct", "true").lower() in ("true", "yes", "1", "si", "sí")
        data["predictions_made"] += 1
        if was_correct:
            data["predictions_correct"] += 1
        _save(data)
        return f"👍 Feedback registrado. Precisión actual: {data['predictions_correct']}/{data['predictions_made']}"

    return f"Acción '{action}' no reconocida."
