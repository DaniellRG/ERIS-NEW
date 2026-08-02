"""google_calendar.py — Google Calendar (requiere OAuth de Google)."""


def google_calendar(parameters: dict, player=None) -> str:
    """Acciones: add, update, delete, today, week. Requiere OAuth configurado."""
    action = (parameters or {}).get("action", "").lower()
    return (
        f"Google Calendar no está configurado (requiere OAuth de Google). "
        f"La acción '{action}' no está disponible hasta configurar credenciales. "
        f"Usá config/setup_integrations.py cuando tengas el client_id."
    )
