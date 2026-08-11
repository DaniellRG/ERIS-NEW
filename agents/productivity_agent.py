"""
agents/productivity_agent.py — ERIS Productivity Specialized Agent.
Handles calendar, email, drive, documents, projects, goals.
"""
from __future__ import annotations

import time
from typing import Optional

def handle_productivity(text: str, player=None, **kwargs) -> str:
    """Handle productivity-related requests."""
    from core.tracer import get_tracer
    tracer = get_tracer()
    t0 = time.perf_counter()

    text_lower = text.lower()

    try:
        # Calendar
        if any(kw in text_lower for kw in ["calendario", "calendar", "agenda", "reunion", "meeting", "evento", "event"]):
            from actions.google_calendar import google_calendar
            if "crear" in text_lower or "create" in text_lower or "agendar" in text_lower:
                result = google_calendar(parameters={"action": "create_event"}, player=player)
            elif "lista" in text_lower or "list" in text_lower or "proximos" in text_lower:
                result = google_calendar(parameters={"action": "list_events"}, player=player)
            else:
                result = google_calendar(parameters={"action": "status"}, player=player)

        # Email / Gmail
        elif any(kw in text_lower for kw in ["email", "correo", "gmail", "mail"]):
            try:
                from actions.gmail_control import gmail_control
                if "enviar" in text_lower or "send" in text_lower:
                    result = gmail_control(parameters={"action": "send"}, player=player)
                elif "leer" in text_lower or "read" in text_lower or "inbox" in text_lower:
                    result = gmail_control(parameters={"action": "read_inbox"}, player=player)
                else:
                    result = gmail_control(parameters={"action": "status"}, player=player)
            except Exception:
                result = "La integraci\u00f3n con Gmail no est\u00e1 disponible en este momento."

        elif "drive" in text_lower or "google drive" in text_lower:
            try:
                from actions.google_drive import google_drive
                result = google_drive(parameters={"action": "status"}, player=player)
            except Exception:
                result = "La integraci\u00f3n con Google Drive no est\u00e1 disponible en este momento."

        # Document creation
        elif any(kw in text_lower for kw in ["documento", "document", "crear doc", "crear documento", "word", "pdf"]):
            from actions.document_generator import document_generator
            result = document_generator(parameters={"action": "create", "content": text}, player=player)

        # Project management
        elif any(kw in text_lower for kw in ["proyecto", "project", "tarea", "task", "kanban"]):
            from actions.project_manager import project_manager
            result = project_manager(parameters={"action": "status"}, player=player)

        # Goals
        elif any(kw in text_lower for kw in ["meta", "goal", "objetivo", "objetivos"]):
            from actions.goals import goals
            result = goals(parameters={"action": "status"}, player=player)

        # Reminders
        elif any(kw in text_lower for kw in ["recordatorio", "reminder", "recorda", "recordar"]):
            from actions.reminder import reminder
            result = reminder(parameters={"action": "list"}, player=player)

        else:
            result = (
                "Puedo ayudarte con productividad:\n"
                "- 'Calendario' → Ver eventos proximos\n"
                "- 'Agendar reunion' → Crear evento en Google Calendar\n"
                "- 'Email' → Leer inbox de Gmail\n"
                "- 'Drive' → Ver archivos de Google Drive\n"
                "- 'Crear documento' → Generar doc con IA\n"
                "- 'Proyectos' → Gestion de proyectos\n"
                "- 'Metas' → Seguimiento de objetivos\n"
                "- 'Recordatorios' → Ver recordatorios activos"
            )

        elapsed = time.perf_counter() - t0
        tracer.trace_handoff("productivity_agent", text, result, elapsed)
        return result

    except Exception as e:
        elapsed = time.perf_counter() - t0
        tracer.trace_handoff("productivity_agent", text, "", elapsed, success=False, error=str(e))
        return f"Error en ProductivityAgent: {e}"
