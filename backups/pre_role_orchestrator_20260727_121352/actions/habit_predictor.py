"""Habit Predictor - predice que vas a necesitar segun tu rutina."""
import json
from datetime import datetime

def habit_predictor(parameters: dict = None, player=None) -> str:
    """Predice que herramientas necesitas segun tu horario habitual."""
    action = (parameters or {}).get("action", "predict")

    if action == "predict":
        try:
            from actions.eris_db import profile_get
            hints_str = profile_get("schedule_hints")
            if not hints_str:
                return "No tengo datos de tus rutinas todavia. Sigue usando ERIS y aprendere."
            
            hints = json.loads(hints_str)
            now = datetime.now()
            key = f"{now.strftime('%A').lower()}_{now.hour}h"
            
            if key in hints:
                tools = hints[key]
                sorted_tools = sorted(tools.items(), key=lambda x: x[1], reverse=True)
                lines = [f"Segun tus habitos a esta hora ({now.strftime('%A %H:%M')}), sueles usar:"]
                for tool, count in sorted_tools[:5]:
                    lines.append(f"  - {tool} ({count} veces)")
                return "\n".join(lines)
            
            return f"No tengo datos para {now.strftime('%A')} a las {now.hour}h. Seguire aprendiendo."
        except Exception as e:
            return f"Error: {e}"

    elif action == "stats":
        try:
            from actions.eris_db import profile_get
            habits_str = profile_get("user_habits")
            freq_str = profile_get("frequent_actions")
            
            result = []
            if habits_str:
                habits = json.loads(habits_str)
                result.append(f"Habitos registrados ({len(habits)} herramientas)")
            if freq_str:
                freq = json.loads(freq_str)
                top = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:10]
                result.append("\nMas usadas:")
                for tool, count in top:
                    result.append(f"  - {tool}: {count} veces")
            
            return "\n".join(result) if result else "No hay estadisticas todavia."
        except Exception as e:
            return f"Error: {e}"

    elif action == "learn":
        # Record current hour usage pattern
        try:
            from actions.eris_db import profile_get, profile_set
            hints_str = profile_get("schedule_hints") or "{}"
            hints = json.loads(hints_str)
            now = datetime.now()
            key = f"{now.strftime('%A').lower()}_{now.hour}h"
            tool = (parameters or {}).get("tool", "unknown")
            
            if key not in hints:
                hints[key] = {}
            hints[key][tool] = hints[key].get(tool, 0) + 1
            
            profile_set("schedule_hints", json.dumps(hints, ensure_ascii=False))
            return f"Aprendido: los {now.strftime('%A')} a las {now.hour}h usas {tool}."
        except Exception as e:
            return f"Error: {e}"

    return "Acciones: predict, stats, learn"
