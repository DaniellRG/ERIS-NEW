"""
calendar_manager.py — Gestión de calendario: crear eventos, listar, buscar, recordatorios.
Soporta Google Calendar API y almacenamiento local como fallback.
"""
import json
import os
from pathlib import Path
from datetime import datetime, timedelta

_BASE = Path(__file__).resolve().parent.parent
_CALENDAR_FILE = _BASE / "data" / "calendar_events.json"
_CREDENTIALS_FILE = _BASE / "config" / "google_credentials.json"

EVENT_TEMPLATE = {
    "id": "", "title": "", "description": "", "start": "", "end": "",
    "location": "", "reminder_minutes": 15, "recurring": "",
    "created": "", "tags": [], "priority": "normal"
}


def calendar_manager(parameters: dict = None, player=None) -> str:
    """
    Gestión de calendario.
    Acciones: list, create, update, delete, search, today, tomorrow, week, reminders, import_gcal, configure_gcal
    """
    params = parameters or {}
    action = params.get("action", "list").lower()

    if action == "create":
        return _create_event(params)
    elif action == "list":
        return _list_events(params)
    elif action == "today":
        return _today_events()
    elif action == "tomorrow":
        return _tomorrow_events()
    elif action == "week":
        return _week_events()
    elif action == "update":
        return _update_event(params)
    elif action == "delete":
        return _delete_event(params)
    elif action == "search":
        return _search_events(params)
    elif action == "reminders":
        return _get_reminders(params)
    elif action == "configure_gcal":
        return _configure_gcal(params)
    elif action == "import_gcal":
        return _import_from_gcal()
    elif action == "status":
        return _get_status()
    elif action == "export":
        return _export_events()
    return "Acciones: list, create, update, delete, search, today, tomorrow, week, reminders, import_gcal, configure_gcal, status, export"


def _load_events() -> list:
    if _CALENDAR_FILE.exists():
        try:
            return json.loads(_CALENDAR_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def _save_events(events: list):
    _CALENDAR_FILE.parent.mkdir(parents=True, exist_ok=True)
    _CALENDAR_FILE.write_text(json.dumps(events, indent=2, ensure_ascii=False), encoding="utf-8")


def _create_event(params: dict) -> str:
    title = params.get("title", "")
    if not title:
        return "Error: se requiere 'title'"

    now = datetime.now()
    start_str = params.get("start") or params.get("date") or now.isoformat()
    try:
        start = datetime.fromisoformat(start_str.replace("Z", "+00:00").replace("+00:00", ""))
    except Exception:
        start = now

    duration_hours = float(params.get("duration_hours") or params.get("duration") or 1)
    end_str = params.get("end") or (start + timedelta(hours=duration_hours)).isoformat()

    event = {
        "id": "evt_{}_{}".format(int(now.timestamp()), hash(title) % 10000),
        "title": title,
        "description": params.get("description", ""),
        "start": start_str,
        "end": end_str,
        "location": params.get("location", ""),
        "reminder_minutes": int(params.get("reminder_minutes", 15)),
        "recurring": params.get("recurring", ""),
        "created": now.isoformat(),
        "tags": params.get("tags", []) if isinstance(params.get("tags"), list) else [],
        "priority": params.get("priority", "normal"),
    }

    events = _load_events()
    events.append(event)
    _save_events(events)
    return "Evento creado: '{}' | {} | Recuerda {} minutos antes".format(
        title, start.strftime("%Y-%m-%d %H:%M"), event["reminder_minutes"])


def _list_events(params: dict) -> str:
    events = _load_events()
    if not events:
        return "No hay eventos programados"

    limit = params.get("limit", 10)
    now = datetime.now()
    future = [e for e in events if _parse_date(e.get("start", "")) >= now - timedelta(hours=1)]
    future.sort(key=lambda x: _parse_date(x.get("start", now.isoformat())))

    results = ["Próximos eventos ({} total):".format(len(future))]
    for e in future[:limit]:
        start = _parse_date(e.get("start", ""))
        tags = " [{}]".format(", ".join(e.get("tags", []))) if e.get("tags") else ""
        priority = " !" if e.get("priority") == "high" else ""
        results.append("  {} {} | {}{}{}".format(
            start.strftime("%Y-%m-%d %H:%M"), e.get("title", "?"), e.get("location", ""), tags, priority))
    return "\n".join(results)


def _today_events() -> str:
    events = _load_events()
    today = datetime.now().date()
    today_events = [e for e in events if _parse_date(e.get("start", "")).date() == today]

    if not today_events:
        return "No tienes eventos hoy {}".format(today.strftime("%Y-%m-%d"))

    results = ["Eventos de hoy {} ({}):".format(today.strftime("%Y-%m-%d"), len(today_events))]
    for e in sorted(today_events, key=lambda x: _parse_date(x.get("start", ""))):
        start = _parse_date(e.get("start", ""))
        results.append("  {} | {} | {}".format(
            start.strftime("%H:%M"), e.get("title", "?"), e.get("location", "")))
    return "\n".join(results)


def _tomorrow_events() -> str:
    events = _load_events()
    tomorrow = (datetime.now() + timedelta(days=1)).date()
    tmrw_events = [e for e in events if _parse_date(e.get("start", "")).date() == tomorrow]

    if not tmrw_events:
        return "No tienes eventos mañana"

    results = ["Eventos de mañana ({}):".format(len(tmrw_events))]
    for e in sorted(tmrw_events, key=lambda x: _parse_date(x.get("start", ""))):
        start = _parse_date(e.get("start", ""))
        results.append("  {} | {} | {}".format(
            start.strftime("%H:%M"), e.get("title", "?"), e.get("location", "")))
    return "\n".join(results)


def _week_events() -> str:
    events = _load_events()
    now = datetime.now()
    week_end = now + timedelta(days=7)
    week_events = [e for e in events
                   if now <= _parse_date(e.get("start", "")) <= week_end]

    if not week_events:
        return "No hay eventos esta semana"

    results = ["Eventos de esta semana ({}):".format(len(week_events))]
    for e in sorted(week_events, key=lambda x: _parse_date(x.get("start", ""))):
        start = _parse_date(e.get("start", ""))
        results.append("  {} {} | {}".format(
            start.strftime("%a %m-%d %H:%M"), e.get("title", "?"), e.get("location", "")))
    return "\n".join(results)


def _update_event(params: dict) -> str:
    event_id = params.get("event_id", "")
    if not event_id:
        return "Error: se requiere 'event_id'"

    events = _load_events()
    for e in events:
        if e.get("id") == event_id:
            for key in ["title", "description", "start", "end", "location", "priority"]:
                if key in params and params[key]:
                    e[key] = params[key]
            if "tags" in params and isinstance(params["tags"], list):
                e["tags"] = params["tags"]
            _save_events(events)
            return "Evento actualizado: {}".format(e.get("title", "?"))
    return "Evento no encontrado: {}".format(event_id)


def _delete_event(params: dict) -> str:
    event_id = params.get("event_id", "")
    title_search = params.get("title", "")
    events = _load_events()

    if event_id:
        events = [e for e in events if e.get("id") != event_id]
    elif title_search:
        events = [e for e in events if title_search.lower() not in e.get("title", "").lower()]
    else:
        return "Se requiere 'event_id' o 'title'"

    _save_events(events)
    return "Evento eliminado"


def _search_events(params: dict) -> str:
    query = params.get("query", "").lower()
    if not query:
        return "Error: se requiere 'query'"

    events = _load_events()
    results = [e for e in events if query in e.get("title", "").lower()
               or query in e.get("description", "").lower()
               or query in e.get("location", "").lower()
               or any(query in t.lower() for t in e.get("tags", []))]

    if not results:
        return "No se encontraron eventos para: {}".format(query)

    lines = ["Resultados para '{}' ({}):".format(query, len(results))]
    for e in results[:10]:
        start = _parse_date(e.get("start", ""))
        lines.append("  {} | {} | {}".format(
            start.strftime("%Y-%m-%d %H:%M"), e.get("title", "?"), e.get("location", "")))
    return "\n".join(lines)


def _get_reminders(params: dict) -> str:
    events = _load_events()
    now = datetime.now()
    upcoming = []

    for e in events:
        start = _parse_date(e.get("start", ""))
        reminder_mins = int(e.get("reminder_minutes", 15))
        reminder_time = start - timedelta(minutes=reminder_mins)
        if reminder_time <= now <= start:
            upcoming.append(e)

    if not upcoming:
        return "No hay recordatorios pendientes"

    lines = ["Recordatorios pendientes ({}):".format(len(upcoming))]
    for e in upcoming:
        start = _parse_date(e.get("start", ""))
        mins_left = int((start - now).total_seconds() / 60)
        lines.append("  '{}' en {} minutos ({})".format(
            e.get("title", "?"), mins_left, start.strftime("%H:%M")))
    return "\n".join(lines)


def _configure_gcal(params: dict) -> str:
    creds = {
        "client_id": params.get("client_id", ""),
        "client_secret": params.get("client_secret", ""),
        "calendar_id": params.get("calendar_id", "primary"),
    }
    if not creds["client_id"] or not creds["client_secret"]:
        return "Error: se requiere client_id y client_secret de Google Cloud Console"
    _CREDENTIALS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _CREDENTIALS_FILE.write_text(json.dumps(creds, indent=2), encoding="utf-8")
    return "Google Calendar configurado. Ahora usa 'import_gcal' para sincronizar"


def _import_from_gcal() -> str:
    if not _CREDENTIALS_FILE.exists():
        return "Google Calendar no configurado. Usa configure_gcal primero"

    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        creds_data = json.loads(_CREDENTIALS_FILE.read_text(encoding="utf-8"))
        creds = Credentials.from_authorized_user_info(creds_data)
        service = build("calendar", "v3", credentials=creds)

        now = datetime.utcnow().isoformat() + "Z"
        future = (datetime.utcnow() + timedelta(days=30)).isoformat() + "Z"

        events_result = service.events().list(
            calendarId=creds_data.get("calendar_id", "primary"),
            timeMin=now, timeMax=future, singleEvents=True, orderBy="startTime"
        ).execute()

        gcal_events = events_result.get("items", [])
        local_events = _load_events()
        imported = 0

        for gcal in gcal_events:
            event = {
                "id": "gcal_" + gcal.get("id", ""),
                "title": gcal.get("summary", "(sin título)"),
                "description": gcal.get("description", ""),
                "start": gcal.get("start", {}).get("dateTime", gcal.get("start", {}).get("date", "")),
                "end": gcal.get("end", {}).get("dateTime", gcal.get("end", {}).get("date", "")),
                "location": gcal.get("location", ""),
                "reminder_minutes": 15,
                "recurring": "",
                "created": datetime.now().isoformat(),
                "tags": ["gcal"],
                "priority": "normal",
                "gcal_id": gcal.get("id"),
            }
            if not any(e.get("gcal_id") == event["gcal_id"] for e in local_events):
                local_events.append(event)
                imported += 1

        _save_events(local_events)
        return "Importados {} eventos de Google Calendar (total local: {})".format(
            imported, len(local_events))
    except ImportError:
        return "Instala google-api-python-client y google-auth: pip install google-api-python-client google-auth"
    except Exception as e:
        return "Error importando de Google Calendar: {}".format(str(e))


def _get_status() -> str:
    events = _load_events()
    now = datetime.now()
    today = sum(1 for e in events if _parse_date(e.get("start", "")).date() == now.date())
    week = sum(1 for e in events if now <= _parse_date(e.get("start", "")) <= now + timedelta(days=7))
    gcal = _CREDENTIALS_FILE.exists()
    return "Calendario: {} eventos totales | {} hoy | {} esta semana | Google Calendar: {}".format(
        len(events), today, week, "sincronizado" if gcal else "no configurado")


def _export_events() -> str:
    events = _load_events()
    export_path = _BASE / "data" / "calendar_export.json"
    export_path.write_text(json.dumps(events, indent=2, ensure_ascii=False), encoding="utf-8")
    return "Exportados {} eventos a {}".format(len(events), str(export_path))


def _parse_date(date_str):
    if not date_str:
        return datetime(2099, 1, 1)
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00").replace("+00:00", ""))
    except Exception:
        try:
            return datetime.strptime(date_str[:19], "%Y-%m-%dT%H:%M:%S")
        except Exception:
            return datetime(2099, 1, 1)
