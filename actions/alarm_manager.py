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
    except: pass
    
    if player:
        try:
            player.write_log(f"\n[ALARMA] {name}: {message}\n")
        except: pass
    
    # Show notification
    try:
        from PyQt6.QtWidgets import QSystemTrayIcon
        if player and hasattr(player, '_win') and hasattr(player._win, 'tray_icon'):
            player._win.tray_icon.showMessage(f"ERIS - {name}", message, QSystemTrayIcon.MessageIcon.Information, 5000)
    except: pass
    
    if name in _timers:
        del _timers[name]

def alarm_manager(parameters: dict, player=None) -> str:
    """Gestiona alarmas y temporizadores."""
    action = parameters.get("action", "list")
    name = parameters.get("name", "")
    message = parameters.get("message", "Tiempo cumplido!")
    seconds = int(parameters.get("seconds", 60))
    minutes = int(parameters.get("minutes", 0))
    
    total_seconds = seconds + minutes * 60
    
    if action == "set":
        if not name:
            name = f"alarma_{int(time.time())}"
        
        if name in _timers:
            _timers[name].cancel()
        
        timer = threading.Timer(total_seconds, _timer_callback, args=[name, message, player])
        timer.daemon = True
        timer.start()
        _timers[name] = timer
        
        if minutes > 0 and seconds > 0:
            return f"Alarma '{name}' configurada para {minutes}min {seconds}s. Te aviso!"
        elif minutes > 0:
            return f"Alarma '{name}' configurada para {minutes} minutos. Te aviso!"
        else:
            return f"Temporizador '{name}' configurado para {seconds} segundos. Te aviso!"
    
    elif action == "cancel":
        if not name:
            return "Dime el nombre de la alarma a cancelar."
        if name in _timers:
            _timers[name].cancel()
            del _timers[name]
            return f"Alarma '{name}' cancelada."
        return f"No hay alarma llamada '{name}'."
    
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
    
    return "Acciones: set, cancel, list, clear"
