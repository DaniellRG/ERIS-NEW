# -*- coding: utf-8 -*-
"""
email_manager.py — Gestión de email vía IMAP/SMTP.
Acciones:
  list    — Listar emails recientes
  read    — Leer un email por ID
  send    — Enviar email
  search  — Buscar emails
  folders — Listar carpetas
  count   — Contar no leídos
Configuración en config/api_keys.json → email: {host, port, user, pass, imap_port, smtp_port}
"""
from __future__ import annotations

import email
import json
import os
import smtplib
import imaplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
from pathlib import Path
from typing import Any


def _get_config():
    cfg_path = Path(r"D:\Eris_Source\config\api_keys.json")
    if not cfg_path.exists():
        return {}
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        return cfg.get("email", {})
    except Exception:
        return {}


def _decode_header_value(val):
    if val is None:
        return ""
    parts = decode_header(val)
    decoded = []
    for data, charset in parts:
        if isinstance(data, bytes):
            decoded.append(data.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(data)
    return " ".join(decoded)


def _get_body(msg):
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="replace")
            elif ct == "text/html" and not msg.find("text/plain"):
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="replace")[:2000]
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            return payload.decode(charset, errors="replace")
    return ""


def email_manager(parameters: dict = None, player=None) -> str:
    """Tool: Gestión de email (IMAP lectura, SMTP envío)."""
    params = parameters or {}
    action = str(params.get("action", "count")).lower().strip()
    cfg = _get_config()

    if not cfg.get("host"):
        return "Email no configurado. Agregá 'email' en config/api_keys.json con host, user, pass."

    if action == "folders":
        try:
            conn = imaplib.IMAP4_SSL(cfg["host"], cfg.get("imap_port", 993))
            conn.login(cfg["user"], cfg["pass"])
            status, folders = conn.list()
            conn.logout()
            lines = ["**Carpetas:**\n"]
            for f in folders:
                if isinstance(f, bytes):
                    parts = f.decode().split('" ')
                    if len(parts) >= 2:
                        lines.append(f"• {parts[-1].strip('\"')}")
            return "\n".join(lines) if len(lines) > 1 else "Sin carpetas."
        except Exception as e:
            return f"Error conexión IMAP: {str(e)[:150]}"

    if action == "count":
        try:
            conn = imaplib.IMAP4_SSL(cfg["host"], cfg.get("imap_port", 993))
            conn.login(cfg["user"], cfg["pass"])
            conn.select("INBOX")
            status, data = conn.search(None, "UNSEEN")
            unread = len(data[0].split()) if data[0] else 0
            status, data = conn.search(None, "ALL")
            total = len(data[0].split()) if data[0] else 0
            conn.logout()
            return f"📧 {unread} no leídos / {total} total en INBOX"
        except Exception as e:
            return f"Error: {str(e)[:150]}"

    if action == "list":
        try:
            folder = str(params.get("folder", "INBOX")).strip()
            max_emails = min(int(params.get("max_emails", 10)), 30)
            conn = imaplib.IMAP4_SSL(cfg["host"], cfg.get("imap_port", 993))
            conn.login(cfg["user"], cfg["pass"])
            conn.select(folder)
            status, data = conn.search(None, "ALL")
            msg_ids = data[0].split()[-max_emails:]
            lines = [f"**{folder} ({len(msg_ids)} recientes):**\n"]
            for mid in reversed(msg_ids):
                status, msg_data = conn.fetch(mid, "(FLAGS RFC822.HEADER)")
                flags = msg_data[0][0].decode() if msg_data[0][0] else ""
                seen = "\\Seen" in flags
                header_raw = msg_data[0][1] if msg_data[1] else b""
                if header_raw:
                    msg = email.message_from_bytes(header_raw)
                    subj = _decode_header_value(msg.get("Subject", ""))
                    sender = _decode_header_value(msg.get("From", ""))
                    date = msg.get("Date", "")[:25]
                    prefix = "  " if seen else "🔵"
                    lines.append(f"{prefix} **{subj[:60]}**")
                    lines.append(f"   De: {sender[:50]} | {date}\n")
            conn.logout()
            return "\n".join(lines)
        except Exception as e:
            return f"Error: {str(e)[:150]}"

    if action == "read":
        try:
            msg_id = str(params.get("id", "")).strip()
            if not msg_id:
                return "Necesitás el ID del email."
            conn = imaplib.IMAP4_SSL(cfg["host"], cfg.get("imap_port", 993))
            conn.login(cfg["user"], cfg["pass"])
            conn.select("INBOX")
            status, data = conn.fetch(msg_id.encode(), "(RFC822)")
            raw = data[0][1]
            msg = email.message_from_bytes(raw)
            subj = _decode_header_value(msg.get("Subject", ""))
            sender = _decode_header_value(msg.get("From", ""))
            date = msg.get("Date", "")
            body = _get_body(msg)[:3000]
            conn.logout()
            return f"**{subj}**\nDe: {sender}\nFecha: {date}\n\n{body}"
        except Exception as e:
            return f"Error: {str(e)[:150]}"

    if action == "search":
        try:
            query = str(params.get("query", "")).strip()
            max_emails = min(int(params.get("max_emails", 5)), 15)
            if not query:
                return "Necesitás un término de búsqueda."
            conn = imaplib.IMAP4_SSL(cfg["host"], cfg.get("imap_port", 993))
            conn.login(cfg["user"], cfg["pass"])
            conn.select("INBOX")
            status, data = conn.search(None, f'(SUBJECT "{query}")')
            msg_ids = data[0].split()[-max_emails:]
            if not msg_ids:
                return f"Sin resultados para '{query}'"
            lines = [f"**Resultados para '{query}':**\n"]
            for mid in reversed(msg_ids):
                status, msg_data = conn.fetch(mid, "(RFC822.HEADER)")
                header_raw = msg_data[0][1] if msg_data[1] else b""
                if header_raw:
                    m = email.message_from_bytes(header_raw)
                    subj = _decode_header_value(m.get("Subject", ""))
                    sender = _decode_header_value(m.get("From", ""))
                    lines.append(f"• **{subj[:60]}** — {sender[:40]}")
            conn.logout()
            return "\n".join(lines)
        except Exception as e:
            return f"Error: {str(e)[:150]}"

    if action == "send":
        try:
            to = str(params.get("to", "")).strip()
            subject = str(params.get("subject", "")).strip()
            body = str(params.get("body", "")).strip()
            if not to or not subject or not body:
                return "Necesitás to, subject y body."
            msg = MIMEMultipart()
            msg["From"] = cfg["user"]
            msg["To"] = to
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain", "utf-8"))
            port = cfg.get("smtp_port", 587)
            with smtplib.SMTP(cfg["host"], port) as server:
                server.starttls()
                server.login(cfg["user"], cfg["pass"])
                server.send_message(msg)
            return f"✅ Email enviado a {to}: {subject}"
        except Exception as e:
            return f"Error enviando email: {str(e)[:150]}"

    return "Acciones: count, list, read, send, search, folders"
