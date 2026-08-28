"""
ERIS Email/Calendar Deep Integration — Resumir emails, detectar conflictos de calendario,
enviar respuestas inteligentes, seguimiento automático.
"""
import json
import time
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "email_calendar"
_DATA_DIR.mkdir(parents=True, exist_ok=True)


def email_calendar_deep(parameters: dict = None, player=None) -> str:
    """Tool entry point."""
    params = parameters or {}
    action = params.get("action", "inbox_summary").lower()

    if action == "inbox_summary":
        try:
            from actions.email_manager import email_manager
            result = email_manager({"action": "list"}, player=player)
            return f"Resumen del inbox:\n{result[:1500]}"
        except Exception as e:
            return f"Error leyendo inbox: {str(e)[:200]}"

    elif action == "unread_count":
        try:
            from actions.email_manager import email_manager
            result = email_manager({"action": "count"}, player=player)
            return result
        except Exception as e:
            return f"Error: {str(e)[:200]}"

    elif action == "smart_reply":
        email_id = params.get("id", "")
        if not email_id:
            return "Necesito 'id' del email para generar respuesta."
        try:
            from actions.email_manager import email_manager
            content = email_manager({"action": "read", "id": email_id}, player=player)
            return f"Contenido del email:\n{content[:2000]}\n\nPuedo redactar una respuesta. ¿Qué tono querés? (formal, casual, directo)"
        except Exception as e:
            return f"Error: {str(e)[:200]}"

    elif action == "calendar_today":
        return "Función de calendario: conectá con Google Calendar API o Outlook para ver eventos de hoy. Configurá el provider en config/api_keys.json."

    elif action == "followup_tracker":
        tracker_file = _DATA_DIR / "followups.json"
        if tracker_file.exists():
            with open(tracker_file, "r", encoding="utf-8") as f:
                followups = json.load(f)
        else:
            followups = []
        if not followups:
            return "No hay follow-ups pendientes."
        pending = [f for f in followups if f.get("status") == "pending"]
        return f"Follow-ups pendientes ({len(pending)}):\n" + "\n".join(
            f"  - {f['subject']} → {f['to']} (esperando desde {f['date']})" for f in pending
        )

    return f"Acción '{action}' no reconocida. Usa: inbox_summary, unread_count, smart_reply, calendar_today, followup_tracker"
