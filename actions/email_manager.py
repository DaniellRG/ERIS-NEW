"""
email_manager.py — Gestión de email: leer, enviar, organizar, buscar.
Soporta Gmail via IMAP/SMTP. Requiere configuración de credenciales.
"""
import json
import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
from pathlib import Path
from datetime import datetime

_BASE = Path(__file__).resolve().parent.parent
_CREDENTIALS_FILE = _BASE / "config" / "email_credentials.json"
_EMAIL_CACHE = _BASE / "data" / "email_cache.json"
_EMAIL_CONFIG = {
    "imap_server": "imap.gmail.com",
    "imap_port": 993,
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
}


def email_manager(parameters: dict = None, player=None) -> str:
    """
    Gestión de email.
    Acciones: list, read, send, search, folders, configure, status, unread_count
    """
    params = parameters or {}
    action = params.get("action", "list").lower()

    if action == "configure":
        return _configure_email(params)
    elif action == "status":
        return _get_status()
    elif action == "list":
        return _list_emails(params)
    elif action == "list_inbox":
        return _list_emails(params)
    elif action == "read":
        return _read_email(params)
    elif action == "send":
        return _send_email(params)
    elif action == "search":
        return _search_emails(params)
    elif action == "folders":
        return _list_folders()
    elif action == "unread_count":
        return _unread_count()
    elif action in ("mark_read", "mark_as"):
        return _mark_read(params)
    elif action == "delete":
        return _delete_email(params)
    elif action == "label":
        return _label_email(params)
    return "Acciones: list, read, send, search, folders, configure, status, unread_count, mark_read, delete, label"


def _load_credentials():
    if _CREDENTIALS_FILE.exists():
        try:
            return json.loads(_CREDENTIALS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _configure_email(params: dict) -> str:
    creds = {
        "email": params.get("email", ""),
        "password": params.get("password", ""),
        "imap_server": params.get("imap_server", _EMAIL_CONFIG["imap_server"]),
        "smtp_server": params.get("smtp_server", _EMAIL_CONFIG["smtp_server"]),
        "display_name": params.get("display_name", "ERIS"),
    }
    if not creds["email"] or not creds["password"]:
        return "Error: se requiere email y password/app_password"
    _CREDENTIALS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _CREDENTIALS_FILE.write_text(json.dumps(creds, indent=2), encoding="utf-8")
    return "Email configurado para: {}".format(creds["email"])


def _get_status() -> str:
    creds = _load_credentials()
    if not creds:
        return "Email: NO configurado. Usa action: configure con email y password"
    return "Email: configurado para {} (IMAP: {})".format(
        creds.get("email", "?"), creds.get("imap_server", "?"))


def _connect_imap():
    creds = _load_credentials()
    if not creds:
        raise Exception("Email no configurado. Usa action: configure")
    mail = imaplib.IMAP4_SSL(creds["imap_server"])
    mail.login(creds["email"], creds["password"])
    return mail, creds


def _list_emails(params: dict) -> str:
    try:
        mail, creds = _connect_imap()
        folder = params.get("folder", "INBOX")
        limit = params.get("limit", 10)
        mail.select(folder)
        _, data = mail.search(None, "ALL")
        msg_ids = data[0].split()

        if not msg_ids:
            mail.logout()
            return "No hay emails en {}".format(folder)

        recent_ids = msg_ids[-limit:]
        recent_ids.reverse()

        results = ["Emails en {} ({} total, mostrando últimos {}):".format(
            folder, len(msg_ids), min(limit, len(msg_ids)))]

        for mid in recent_ids:
            _, msg_data = mail.fetch(mid, "(RFC822.HEADER)")
            msg = email.message_from_bytes(msg_data[0][1])
            subject = _decode_header_value(msg.get("Subject", "(sin asunto)"))
            sender = msg.get("From", "?")
            date = msg.get("Date", "?")
            results.append("  [{}] De: {} | Asunto: {}".format(date[:16], sender[:40], subject[:60]))

        mail.logout()
        return "\n".join(results)
    except Exception as e:
        return "Error listando emails: {}".format(str(e))


def _read_email(params: dict) -> str:
    try:
        mail, creds = _connect_imap()
        folder = params.get("folder", "INBOX")
        msg_id = params.get("msg_id", "")
        mail.select(folder)

        if not msg_id:
            _, data = mail.search(None, "ALL")
            ids = data[0].split()
            idx = min(int(params.get("index", 0)), len(ids) - 1)
            msg_id = ids[-(idx + 1)]

        _, msg_data = mail.fetch(msg_id, "(RFC822)")
        msg = email.message_from_bytes(msg_data[0][1])

        subject = _decode_header_value(msg.get("Subject", "(sin asunto)"))
        sender = msg.get("From", "?")
        date = msg.get("Date", "?")
        to = msg.get("To", "?")

        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        body = payload.decode("utf-8", errors="replace")[:3000]
                    break
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                body = payload.decode("utf-8", errors="replace")[:3000]

        mail.logout()
        return "From: {}\nTo: {}\nDate: {}\nSubject: {}\n\n{}".format(
            sender, to, date, subject, body)
    except Exception as e:
        return "Error leyendo email: {}".format(str(e))


def _send_email(params: dict) -> str:
    to = params.get("to", "")
    subject = params.get("subject", "")
    body = params.get("body", "")
    if not to or not body:
        return "Error: se requiere 'to' y 'body'"

    try:
        creds = _load_credentials()
        if not creds:
            return "Email no configurado"

        msg = MIMEMultipart()
        msg["From"] = creds.get("display_name", "ERIS") + " <" + creds["email"] + ">"
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        server = smtplib.SMTP(creds.get("smtp_server", _EMAIL_CONFIG["smtp_server"]),
                              _EMAIL_CONFIG["smtp_port"])
        server.starttls()
        server.login(creds["email"], creds["password"])
        server.send_message(msg)
        server.quit()

        _log_sent(to, subject, body)
        return "Email enviado a: {} | Asunto: {}".format(to, subject[:50])
    except Exception as e:
        return "Error enviando email: {}".format(str(e))


def _search_emails(params: dict) -> str:
    query = params.get("query", "")
    if not query:
        return "Error: se requiere 'query'"

    try:
        mail, creds = _connect_imap()
        folder = params.get("folder", "INBOX")
        mail.select(folder)
        _, data = mail.search(None, '(OR SUBJECT "{}" FROM "{}")'.format(query, query))
        msg_ids = data[0].split()

        if not msg_ids:
            mail.logout()
            return "No se encontraron resultados para: {}".format(query)

        limit = params.get("limit", 10)
        recent = msg_ids[-limit:]
        recent.reverse()

        results = ["Resultados para '{}' ({} encontrados):".format(query, len(msg_ids))]
        for mid in recent:
            _, msg_data = mail.fetch(mid, "(RFC822.HEADER)")
            msg = email.message_from_bytes(msg_data[0][1])
            subject = _decode_header_value(msg.get("Subject", "(sin asunto)"))
            sender = msg.get("From", "?")
            results.append("  De: {} | Asunto: {}".format(sender[:40], subject[:60]))

        mail.logout()
        return "\n".join(results)
    except Exception as e:
        return "Error buscando emails: {}".format(str(e))


def _list_folders() -> str:
    try:
        mail, creds = _connect_imap()
        _, folders = mail.list()
        mail.logout()
        folder_list = []
        for f in folders[:20]:
            decoded = f.decode("utf-8", errors="replace") if isinstance(f, bytes) else str(f)
            folder_list.append("  " + decoded.split('"')[-2] if '"' in decoded else decoded)
        return "Carpetas:\n" + "\n".join(folder_list)
    except Exception as e:
        return "Error listando carpetas: {}".format(str(e))


def _unread_count() -> str:
    try:
        mail, creds = _connect_imap()
        mail.select("INBOX")
        _, data = mail.search(None, "UNSEEN")
        count = len(data[0].split()) if data[0].strip() else 0
        mail.logout()
        return "Tienes {} emails sin leer en INBOX".format(count)
    except Exception as e:
        return "Error contando unread: {}".format(str(e))


def _mark_read(params: dict) -> str:
    try:
        mail, creds = _connect_imap()
        folder = params.get("folder", "INBOX")
        mail.select(folder)
        _, data = mail.search(None, "UNSEEN")
        ids = data[0].split()
        if not ids:
            mail.logout()
            return "No hay emails sin leer"
        idx = min(int(params.get("index", 0)), len(ids) - 1)
        mail.store(ids[-(idx + 1)], "+FLAGS", "\\Seen")
        mail.logout()
        return "Email marcado como leído"
    except Exception as e:
        return "Error: {}".format(str(e))


def _delete_email(params: dict) -> str:
    try:
        mail, creds = _connect_imap()
        folder = params.get("folder", "INBOX")
        mail.select(folder)
        _, data = mail.search(None, "ALL")
        ids = data[0].split()
        if not ids:
            mail.logout()
            return "No hay emails"
        idx = min(int(params.get("index", 0)), len(ids) - 1)
        mail.store(ids[-(idx + 1)], "+FLAGS", "\\Deleted")
        mail.expunge()
        mail.logout()
        return "Email eliminado"
    except Exception as e:
        return "Error eliminando: {}".format(str(e))


def _label_email(params: dict) -> str:
    label = params.get("label", "")
    if not label:
        return "Error: se requiere 'label'"
    try:
        mail, creds = _connect_imap()
        folder = params.get("folder", "INBOX")
        mail.select(folder)
        _, data = mail.search(None, "ALL")
        ids = data[0].split()
        if not ids:
            mail.logout()
            return "No hay emails"
        idx = min(int(params.get("index", 0)), len(ids) - 1)
        mail.store(ids[-(idx + 1)], "+X-GM-LABELS", label)
        mail.logout()
        return "Label '{}' aplicado".format(label)
    except Exception as e:
        return "Error aplicando label: {}".format(str(e))


def _decode_header_value(val):
    if not val:
        return ""
    parts = decode_header(val)
    decoded = []
    for part, charset in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(str(part))
    return " ".join(decoded)


def _log_sent(to, subject, body):
    cache = _load_cache()
    cache.setdefault("sent", []).append({
        "to": to, "subject": subject, "body_preview": body[:200],
        "timestamp": datetime.now().isoformat()
    })
    cache["sent"] = cache["sent"][-100:]
    _save_cache(cache)


def _load_cache():
    if _EMAIL_CACHE.exists():
        try:
            return json.loads(_EMAIL_CACHE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"sent": [], "last_check": None}


def _save_cache(cache):
    _EMAIL_CACHE.parent.mkdir(parents=True, exist_ok=True)
    _EMAIL_CACHE.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")
