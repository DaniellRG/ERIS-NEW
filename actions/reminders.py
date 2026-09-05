import json
import threading
from datetime import datetime, timedelta
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "reminders.json"
_reminders: list = []
_timers: list = []

def _load():
    global _reminders
    try:
        if DATA_FILE.exists():
            _reminders = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        _reminders = []

def _save():
    try:
        DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        DATA_FILE.write_text(json.dumps(_reminders, indent=2, ensure_ascii=False), encoding="utf-8")
    except OSError: pass

def reminders(parameters: dict, player=None) -> str:
    action = (parameters.get("action") or "list").lower()
    text = parameters.get("text") or parameters.get("message") or ""
    time_str = parameters.get("time") or parameters.get("duration") or ""
    reminder_id = parameters.get("id")

    _load()

    if player:
        player.write_log(f"⏰ Reminder: {action}")

    if action in ("add", "create", "crear", "agregar"):
        return _add_reminder(text, time_str, player)
    elif action in ("list", "listar", "mostrar"):
        return _list_reminders()
    elif action in ("cancel", "cancelar", "eliminar"):
        return _cancel_reminder(reminder_id or text)
    elif action in ("clear", "limpiar"):
        return _clear_past()
    else:
        return "Acciones: add, list, cancel, clear"

def _add_reminder(text, time_str, player):
    if not text:
        return "¿Qué querés que te recuerde?"
    if not time_str:
        return "¿Cuándo? Ej: 'en 30 minutos', 'en 2 horas', 'mañana a las 10'"

    delay = _parse_duration(time_str)
    if delay is None:
        return f"No entendí el tiempo: '{time_str}'. Decí 'en X minutos/horas'."

    reminder_id = len(_reminders) + 1
    trigger_at = datetime.now() + timedelta(seconds=delay)
    reminder = {
        "id": reminder_id,
        "text": text,
        "trigger_at": trigger_at.isoformat(),
        "created_at": datetime.now().isoformat(),
        "active": True
    }
    _reminders.append(reminder)
    _save()

    timer = threading.Timer(delay, _fire_reminder, args=[reminder_id, text, player])
    timer.daemon = True
    timer.start()
    _timers.append({"id": reminder_id, "timer": timer})

    return f"Recordatorio #{reminder_id} creado: '{text}' en {_format_seconds(delay)}"

def _fire_reminder(rid, text, player):
    _load()
    for r in _reminders:
        if r["id"] == rid:
            r["active"] = False
            break
    _save()
    if player:
        player.write_log(f"⏰ RECORDATORIO: {text}")
        player.set_state("SPEAKING")
    print(f"\n{'='*50}\n⏰ RECORDATORIO #{rid}: {text}\n{'='*50}")

def _list_reminders():
    active = [r for r in _reminders if r.get("active")]
    if not active:
        return "No tenés recordatorios activos."
    lines = []
    for r in active:
        trigger = datetime.fromisoformat(r["trigger_at"])
        remaining = (trigger - datetime.now()).total_seconds()
        if remaining > 0:
            lines.append(f"#{r['id']}: '{r['text']}' en {_format_seconds(int(remaining))}")
        else:
            lines.append(f"#{r['id']}: '{r['text']}' (vencido)")
    return f"Recordatorios activos ({len(lines)}):\n" + "\n".join(lines)

def _cancel_reminder(identifier):
    if identifier:
        for r in _reminders:
            if str(r["id"]) == str(identifier) or r["text"].lower() == str(identifier).lower():
                r["active"] = False
                _save()
                return f"Recordatorio #{r['id']} cancelado: '{r['text']}'"
    return "No encontré ese recordatorio."

def _clear_past():
    count = 0
    for r in _reminders:
        if r.get("active"):
            trigger = datetime.fromisoformat(r["trigger_at"])
            if trigger < datetime.now():
                r["active"] = False
                count += 1
    _save()
    return f"Limpiados {count} recordatorios vencidos."

def _parse_duration(time_str):
    time_str = time_str.lower().strip()
    total = 0
    parts = time_str.replace("en ", "").replace("dentro de ", "").split()

    i = 0
    while i < len(parts):
        try:
            num = int(parts[i])
            unit = parts[i + 1] if i + 1 < len(parts) else ""
            if "segundo" in unit or "seg" in unit:
                total += num
            elif "minuto" in unit or "min" in unit:
                total += num * 60
            elif "hora" in unit or "hr" in unit:
                total += num * 3600
            elif "día" in unit or "dia" in unit or "day" in unit:
                total += num * 86400
            i += 2
        except (ValueError, IndexError):
            i += 1

    return total if total > 0 else None

def _format_seconds(secs):
    if secs < 60:
        return f"{secs} segundos"
    elif secs < 3600:
        return f"{secs // 60} minutos"
    elif secs < 86400:
        h = secs // 3600
        m = (secs % 3600) // 60
        return f"{h} horas y {m} minutos" if m else f"{h} horas"
    else:
        d = secs // 86400
        return f"{d} días"
