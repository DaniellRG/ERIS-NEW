"""gmail_control.py — Control de Gmail delegado al gestor de correo (IMAP/SMTP)."""
from actions.email_manager import email_manager


def gmail_control(parameters: dict, player=None) -> str:
    """Gmail: send, search, trash, archive. Requiere email configurado (action configure)."""
    params = dict(parameters or {})
    # Keys que consume email_manager (forwarding explícito):
    a = str(params.get("action", "")).lower()
    _ = (params.get("to"), params.get("subject"), params.get("body"),
         params.get("query"), params.get("max_results"))
    if a == "trash":
        params["action"] = "delete"
    elif a == "archive":
        params["action"] = "label"
        params.setdefault("value", "Archived")
    return email_manager(params, player)
