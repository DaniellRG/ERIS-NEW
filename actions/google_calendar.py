# -*- coding: utf-8 -*-
"""
google_calendar.py — Integración con Google Calendar API.
Acciones:
  today     — Eventos de hoy
  week      — Eventos de la semana
  upcoming  — Próximos eventos
  create    — Crear evento
  delete    — Eliminar evento por ID
  search    — Buscar eventos
Requiere credentials.json en config/ (OAuth2).
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

_CRED_FILE = Path(r"D:\Eris_Source\config\credentials.json")
_TOKEN_FILE = Path(r"D:\Eris_Source\config\token_calendar.json")
_CALENDAR_ID = "primary"


def _get_service():
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build

        SCOPES = ["https://www.googleapis.com/auth/calendar"]

        creds = None
        if _TOKEN_FILE.exists():
            creds = Credentials.from_authorized_user_file(str(_TOKEN_FILE), SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not _CRED_FILE.exists():
                    return None, "No se encontró config/credentials.json"
                flow = InstalledAppFlow.from_client_secrets_file(str(_CRED_FILE), SCOPES)
                creds = flow.run_local_server(port=0)
            _TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")

        service = build("calendar", "v3", credentials=creds)
        return service, None
    except Exception as e:
        return None, str(e)[:200]


def _format_event(ev):
    start = ev.get("start", {}).get("dateTime", ev.get("start", {}).get("date", ""))
    end = ev.get("end", {}).get("dateTime", ev.get("end", {}).get("date", ""))
    summary = ev.get("summary", "(sin título)")
    location = ev.get("location", "")
    eid = ev.get("id", "")[:20]
    line = f"• **{summary}** | {start[:16]}"
    if location:
        line += f" | 📍{location}"
    line += f" [{eid}]"
    return line


def google_calendar(parameters: dict = None, player=None) -> str:
    """Tool: Google Calendar (eventos, crear, eliminar)."""
    params = parameters or {}
    action = str(params.get("action", "today")).lower().strip()

    service, err = _get_service()
    if err:
        return f"Error Google Calendar: {err}"

    now = datetime.now(timezone.utc)

    try:
        if action == "today":
            start = now.replace(hour=0, minute=0, second=0).isoformat()
            end = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0).isoformat()
            result = service.events().list(
                calendarId=_CALENDAR_ID, timeMin=start, timeMax=end,
                singleEvents=True, orderBy="startTime", maxResults=20
            ).execute()
            events = result.get("items", [])
            if not events:
                return "📅 Sin eventos hoy."
            lines = [f"**Eventos de hoy ({now.strftime('%d/%m')}):**\n"]
            for ev in events:
                lines.append(_format_event(ev))
            return "\n".join(lines)

        if action == "week":
            start = now.isoformat()
            end = (now + timedelta(days=7)).isoformat()
            result = service.events().list(
                calendarId=_CALENDAR_ID, timeMin=start, timeMax=end,
                singleEvents=True, orderBy="startTime", maxResults=30
            ).execute()
            events = result.get("items", [])
            if not events:
                return "📅 Sin eventos esta semana."
            lines = [f"**Eventos de la semana:**\n"]
            for ev in events:
                lines.append(_format_event(ev))
            return "\n".join(lines)

        if action == "upcoming":
            max_results = min(int(params.get("max_results", 10)), 30)
            result = service.events().list(
                calendarId=_CALENDAR_ID, timeMin=now.isoformat(),
                singleEvents=True, orderBy="startTime", maxResults=max_results
            ).execute()
            events = result.get("items", [])
            if not events:
                return "📅 Sin eventos próximos."
            lines = [f"**Próximos {len(events)} eventos:**\n"]
            for ev in events:
                lines.append(_format_event(ev))
            return "\n".join(lines)

        if action == "create":
            summary = str(params.get("summary", "")).strip()
            start_time = str(params.get("start", "")).strip()
            end_time = str(params.get("end", "")).strip()
            location = str(params.get("location", "")).strip()
            description = str(params.get("description", "")).strip()
            if not summary or not start_time:
                return "Necesitás summary y start (ISO format)."
            event = {"summary": summary}
            if "T" in start_time:
                event["start"] = {"dateTime": start_time, "timeZone": "America/Argentina/Buenos_Aires"}
                event["end"] = {"dateTime": end_time or start_time[:16], "timeZone": "America/Argentina/Buenos_Aires"}
            else:
                event["start"] = {"date": start_time}
                event["end"] = {"date": end_time or start_time}
            if location:
                event["location"] = location
            if description:
                event["description"] = description
            created = service.events().insert(calendarId=_CALENDAR_ID, body=event).execute()
            return f"✅ Evento creado: {created.get('htmlLink', '')}"

        if action == "delete":
            event_id = str(params.get("event_id", "")).strip()
            if not event_id:
                return "Necesitás el event_id."
            service.events().delete(calendarId=_CALENDAR_ID, eventId=event_id).execute()
            return f"✅ Evento eliminado: {event_id}"

        if action == "search":
            query = str(params.get("query", "")).strip()
            if not query:
                return "Necesitás un término de búsqueda."
            result = service.events().list(
                calendarId=_CALENDAR_ID, q=query, singleEvents=True,
                orderBy="startTime", maxResults=10
            ).execute()
            events = result.get("items", [])
            if not events:
                return f"Sin resultados para '{query}'"
            lines = [f"**Resultados para '{query}':**\n"]
            for ev in events:
                lines.append(_format_event(ev))
            return "\n".join(lines)

    except Exception as e:
        return f"Error Calendar: {str(e)[:200]}"

    return "Acciones: today, week, upcoming, create, delete, search"
