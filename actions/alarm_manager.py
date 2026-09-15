"""Alarmas y temporizadores - Eris te avisa cuando tu quieras.

Las alarmas se persistén en ``data/alarms.json`` y se RE-ARMAN solas al
arrancar (o en el primer uso posterior a un reinicio): si la alarma venció
mientras Eris estaba apagada, se dispara apenas vuelve a correr.
"""
import json
import threading
import time
from pathlib import Path

_timers: dict = {}

_DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "alarms.json"


def _load_store() -> dict:
    try:
        if _DATA_FILE.exists():
            data = json.loads(_DATA_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {}


def _save_store(store: dict) -> None:
    try:
        _DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        _DATA_FILE.write_text(json.dumps(store, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def _notify(name: str, message: str, player=None) -> None:
    """Notificación de sistema (tray de Eris; notify-send en Linux/Wayland)."""
    try:
        from PyQt6.QtWidgets import QSystemTrayIcon
        if player and getattr(player, "_win", None) and getattr(player._win, "tray_icon", None):
            player._win.tray_icon.showMessage(
                f"ERIS - {name}", message, QSystemTrayIcon.MessageIcon.Information, 5000
            )
    except Exception:
        pass
    try:
        import shutil
        import subprocess
        if shutil.which("notify-send"):
            subprocess.Popen(["notify-send", "-a", "ERIS", f"{name}: {message}"])
    except Exception:
        pass


def _timer_callback(name: str, message: str, player=None):
    """Called when timer fires."""
    try:
        import winsound
        for _ in range(5):
            winsound.Beep(800, 200)
            winsound.Beep(1000, 200)
    except Exception:
        pass

    _notify(name, message, player)

    if player:
        try:
            player.write_log(f"\n[ALARMA] {name}: {message}\n")
        except Exception:
            pass

    if name in _timers:
        del _timers[name]

    # Reflejar en disco (la alarma ya se disparó)
    store = _load_store()
    if name in store:
        del store[name]
        _save_store(store)


def _reload_timers(player=None) -> None:
    """Re-arma alarmas persistidas tras un reinicio.

    - Futuras → nuevo threading.Timer con el tiempo restante.
    - Vencidas mientras Eris estaba apagada → se disparan ahora.
    """
    store = _load_store()
    now = time.time()
    changed = False
    for name in list(store):
        entry = store[name]
        fire_at = float(entry.get("fire_at", 0) or 0)
        msg = str(entry.get("message", "Tiempo cumplido!"))
        if name in _timers:
            continue
        if fire_at <= now:
            _timer_callback(name, msg, player)  # vencida: avisá ahora
            del store[name]
            changed = True
        else:
            timer = threading.Timer(fire_at - now, _timer_callback, args=[name, msg, player])
            timer.daemon = True
            timer.start()
            _timers[name] = timer
    if changed:
        _save_store(store)


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
    """Gestiona alarmas y temporizadores (persistidos + re-armados al reboot)."""
    action = parameters.get("action", "list")
    name = parameters.get("name") or parameters.get("label") or parameters.get("alarm_id") or ""
    message = parameters.get("message", "Tiempo cumplido!")
    seconds = int(parameters.get("seconds", 0))
    minutes = int(parameters.get("minutes", 0))

    # Re-armar alarmas persistidas de una sesión anterior
    _reload_timers(player)

    total_seconds = _parse_time(parameters.get("time"), seconds, minutes)

    if action in ("set", "set_alarm", "set_timer"):
        if not name:
            name = f"alarma_{int(time.time())}"
        name = str(name)

        if name in _timers:
            _timers[name].cancel()

        fire_at = time.time() + max(1, total_seconds)
        timer = threading.Timer(max(1, total_seconds), _timer_callback, args=[name, message, player])
        timer.daemon = True
        timer.start()
        _timers[name] = timer

        store = _load_store()
        store[name] = {"message": message, "fire_at": fire_at}
        _save_store(store)

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
        store = _load_store()
        if name in store:
            del store[name]
            _save_store(store)
        return f"Alarma '{name}' cancelada."

    elif action == "snooze":
        if name in _timers:
            _timers[name].cancel()
            fire_at = time.time() + 300
            timer = threading.Timer(300, _timer_callback, args=[name, message, player])
            timer.daemon = True
            timer.start()
            _timers[name] = timer
            store = _load_store()
            store[name] = {"message": message, "fire_at": fire_at}
            _save_store(store)
            return f"Alarma '{name}' pospuesta 5 minutos."
        return "No hay alarma activa para posponer."

    elif action == "list":
        if not _timers and not _load_store():
            return "No hay alarmas activas."
        lines = [f"Alarmas activas ({len(_timers)}):"]
        for n in _timers:
            lines.append(f"  - {n}")
        return "\n".join(lines)

    elif action == "clear":
        for t in _timers.values():
            t.cancel()
        _timers.clear()
        _save_store({})
        return "Todas las alarmas canceladas."

    return "Acciones: set_alarm, set_timer, list, cancel, snooze"