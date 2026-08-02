"""gmail_control.py — Control de Gmail delegado al gestor de correo (IMAP/SMTP)."""
from actions.email_manager import email_manager


def gmail_control(parameters: dict, player=None) -> str:
    """Gmail: send, search, trash, archive. Requiere email configurado (action configure)."""
    p = dict(parameters or {})
    a = str(p.get("action", "")).lower()
    if a == "trash":
        p["action"] = "delete"
    elif a == "archive":
        p["action"] = "label"
        p.setdefault("value", "Archived")
    return email_manager(p, player)
