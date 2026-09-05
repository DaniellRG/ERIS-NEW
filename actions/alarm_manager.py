"""Alarmas y temporizadores - Eris te avisa cuando tu quieras."""
import threading, time, os

_timers = {}

def _timer_callback(name: str, message: str, player=None):
    """Called when timer fires."""
    try:
        # Play sound
        import winsound
        for _ in range(5):
            winsound.Beep(800, 200)
            winsound.Beep(1000, 200)
    except Exception: pass
    
    if player:
        try:
            player.write_log(f"\n[ALARMA] {name}: {message}\n")
        except Exception: pass
    
    # Show notification
    try:
        from PyQt6.QtWidgets import QSystemTrayIcon
        if player and hasattr(player, '_win') and hasattr(player._win, 'tray_icon'):
            player._win.tray_icon.showMessage(f"ERIS - {name}", message, QSystemTrayIcon.MessageIcon.Information, 5000)
    except Exception: pass
    
    if name in _timers:
        del _timers[name]

def _parse_time(value, seconds, minutes):
    """Parse declaraciones '14:30', 'en 5 minutos', '90 segundos', '1 hora'."""
    try:
        t = (value or "").strip().lower()
        if not t:
            return seconds + minutes * 60
        if ":" in t:
            h, m = t.split(":")
            now = time.localtime()
            target = (int(h) % 24) * 3600 + (int(m) % 60) * 60
            now_secs = now.tm_hour * 3600 + now.tm_min * 60 + now.tm_sec
            if target <= now_secs:
                target += 86400
            return target - now_secs
        import re
        m = re.search(r"(\d+)\s*(hora|hs?|min|mins?|minuto|seg|segs?|segundo)", t)
        if m:
            n = int(m.group(1))
            u = m.group(2)
            if u.startswith("h"):
                return n * 3600
            if u.startswith("min") or u.startswith("minuto"):
                return n * 60
            return n
        n = float(t)
        return int(n * 60 if n < 100 else n)
    except Exception:
        return seconds + minutes * 60


def alarm_manager(parameters: dict, player=None) -> str:
    """Gestiona alarmas y temporizadores."""
    action = parameters.get("action", "list")
    name = parameters.get("name") or parameters.get("label") or parameters.get("alarm_id") or ""
    message = parameters.get("message", "Tiempo cumplido!")
    seconds = int(parameters.get("seconds", 0))
    minutes = int(parameters.get("minutes", 0))

    total_seconds = _parse_time(parameters.get("time"), seconds, minutes)

    if action in ("set", "set_alarm", "set_timer"):
        if not name:
            name = f"alarma_{int(time.time())}"

        if name in _timers:
            _timers[name].cancel()

        timer = threading.Timer(max(1, total_seconds), _timer_callback, args=[name, message, player])
        timer.daemon = True
        timer.start()
        _timers[name] = timer

        mins, secs = divmod(max(1, total_seconds), 60)
        if mins > 0 and secs > 0:
            return f"Alarma '{name}' configurada para {mins}min {secs}s. Te aviso!"
        elif mins > 0:
            return f"Alarma '{name}' configurada para {mins} minutos. Te aviso!"
        else:
            return f"Temporizador '{name}' configurado para {secs} segundos. Te aviso!"

    elif action == "cancel":
        if not name:
            return "Dime el nombre de la alarma a cancelar."
        if name in _timers:
            _timers[name].cancel()
            del _timers[name]
            return f"Alarma '{name}' cancelada."
        return f"No hay alarma llamada '{name}'."

    elif action == "snooze":
        if name in _timers:
            _timers[name].cancel()
            timer = threading.Timer(300, _timer_callback, args=[name, message, player])
            timer.daemon = True
            timer.start()
            _timers[name] = timer
            return f"Alarma '{name}' pospuesta 5 minutos."
        return "No hay alarma activa para posponer."

    elif action == "list":
        if not _timers:
            return "No hay alarmas activas."
        lines = [f"Alarmas activas ({len(_timers)}):"]
        for n in _timers:
            lines.append(f"  - {n}")
        return "\n".join(lines)

    elif action == "clear":
        for t in _timers.values():
            t.cancel()
        _timers.clear()
        return "Todas las alarmas canceladas."

    return "Acciones: set_alarm, set_timer, list, cancel, snooze"
