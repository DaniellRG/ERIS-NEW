import subprocess
import os
import json
from pathlib import Path

CONFIG_FILE = Path(__file__).resolve().parent.parent / "config" / "pc_control.json"

def _load_config():
    try:
        if CONFIG_FILE.exists():
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except: pass
    return {}

def _save_config(data):
    try:
        CONFIG_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except: pass

def pc_control(parameters: dict, player=None) -> str:
    action = (parameters.get("action") or parameters.get("command") or "").lower()
    value = parameters.get("value") or parameters.get("target") or ""

    if player:
        player.write_log(f"🖥️ PC Control: {action}")

    if action in ("volume_up", "subir volumen"):
        return _change_volume(5)
    elif action in ("volume_down", "bajar volumen"):
        return _change_volume(-5)
    elif action in ("volume_set", "poner volumen"):
        return _set_volume(int(value) if value else 50)
    elif action in ("mute", "silenciar"):
        return _mute_unmute(True)
    elif action in ("unmute", "desilenciar"):
        return _mute_unmute(False)
    elif action in ("monitor_on", "encender monitor"):
        return _monitor_on()
    elif action in ("monitor_off", "apagar monitor"):
        return _monitor_off()
    elif action in ("wifi_on", "encender wifi"):
        return _wifi_toggle(True)
    elif action in ("wifi_off", "apagar wifi"):
        return _wifi_toggle(False)
    elif action in ("wifi_status", "estado wifi"):
        return _wifi_status()
    elif action in ("bluetooth_on", "encender bluetooth"):
        return _bluetooth_toggle(True)
    elif action in ("bluetooth_off", "apagar bluetooth"):
        return _bluetooth_toggle(False)
    elif action in ("bluetooth_status", "estado bluetooth"):
        return _bluetooth_status()
    elif action in ("screenshot", "captura"):
        return _screenshot()
    elif action in ("lock", "bloquear"):
        return _lock_pc()
    elif action in ("restart", "reiniciar"):
        return _shutdown("restart")
    elif action in ("shutdown", "apagar pc"):
        return _shutdown("shutdown")
    elif action in ("sleep", "suspender"):
        return _sleep_pc()
    elif action in ("logout", "cerrar sesion"):
        return _logout_pc()
    elif action in ("hibernate", "hibernar"):
        return _shutdown("hibernate")
    elif action in ("status", "estado"):
        return _full_status()
    else:
        return (
            f"Acciones disponibles: volume_up, volume_down, volume_set, mute, unmute, "
            f"monitor_on, monitor_off, wifi_on, wifi_off, wifi_status, "
            f"bluetooth_on, bluetooth_off, bluetooth_status, "
            f"screenshot, lock, sleep, hibernate, logout, restart, shutdown, status"
        )

def _change_volume(delta):
    try:
        from pycaw.pycaw import AudioUtilities
        volume = AudioUtilities.GetSpeakers().EndpointVolume
        current = volume.GetMasterVolumeLevelScalar()
        new_vol = max(0.0, min(1.0, current + delta / 100))
        volume.SetMasterVolumeLevelScalar(new_vol, None)
        return f"Volumen ajustado a {int(new_vol * 100)}%"
    except Exception as e:
        return f"Error al cambiar volumen: {e}"

def _set_volume(level):
    try:
        from pycaw.pycaw import AudioUtilities
        volume = AudioUtilities.GetSpeakers().EndpointVolume
        vol = max(0.0, min(1.0, level / 100))
        volume.SetMasterVolumeLevelScalar(vol, None)
        return f"Volumen puesto a {level}%"
    except Exception as e:
        return f"Error al poner volumen: {e}"

def _mute_unmute(mute):
    try:
        from pycaw.pycaw import AudioUtilities
        volume = AudioUtilities.GetSpeakers().EndpointVolume
        volume.SetMute(bool(mute), None)
        return "Silenciado" if mute else "Sonido activado"
    except Exception as e:
        return f"Error: {e}"

def _monitor_off():
    try:
        import ctypes
        ctypes.windll.user32.SendMessageW(0xFFFF, 0x0112, 0xF170, 2)
        return "Monitor apagado"
    except Exception as e:
        return f"Error al apagar monitor: {e}"

def _monitor_on():
    try:
        import ctypes
        ctypes.windll.user32.SendMessageW(0xFFFF, 0x0112, 0xF170, -1)
        return "Monitor encendido"
    except Exception as e:
        return f"Error al encender monitor: {e}"

def _wifi_toggle(enable):
    try:
        state = "enable" if enable else "disable"
        result = subprocess.run(
            ["netsh", "interface", "set", "interface", "Wi-Fi", state],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return f"WiFi {'encendido' if enable else 'apagado'}"
        return f"Error: {result.stderr.strip() or 'permisos requeridos'}"
    except Exception as e:
        return f"Error WiFi: {e}"

def _wifi_status():
    try:
        result = subprocess.run(["netsh", "interface", "show", "interface", "Wi-Fi"],
                                capture_output=True, text=True, timeout=10)
        if "Connected" in result.stdout or "Conectado" in result.stdout:
            result2 = subprocess.run(["netsh", "wlan", "show", "interfaces"],
                                     capture_output=True, text=True, timeout=10)
            ssid = ""
            for line in result2.stdout.split("\n"):
                if "SSID" in line or "Nombre" in line:
                    ssid = line.split(":")[-1].strip()
                    break
            return f"WiFi conectado a '{ssid}'" if ssid else "WiFi conectado"
        return "WiFi desconectado"
    except Exception as e:
        return f"Error: {e}"

def _bluetooth_toggle(enable):
    try:
        state = "enable" if enable else "disable"
        result = subprocess.run(
            ["powershell", "-Command", f"Get-Service bthserv | {'Start-Service' if enable else 'Stop-Service'}"],
            capture_output=True, text=True, timeout=10
        )
        return f"Bluetooth {'encendido' if enable else 'apagado'}"
    except Exception as e:
        return f"Error Bluetooth: {e}"

def _bluetooth_status():
    try:
        result = subprocess.run(
            ["powershell", "-Command", "(Get-Service bthserv).Status.ToString()"],
            capture_output=True, text=True, timeout=10
        )
        status = result.stdout.strip()
        return f"Bluetooth: {status}"
    except Exception as e:
        return f"Error: {e}"

def _screenshot():
    try:
        from mss import mss
        from datetime import datetime
        desktop = Path.home() / "Desktop"
        filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = desktop / filename
        with mss() as sct:
            sct.shot(mon=0, output=str(filepath))
        return f"Captura guardada en: {filepath}"
    except Exception as e:
        return f"Error en captura: {e}"

def _lock_pc():
    try:
        subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"], timeout=5)
        return "PC bloqueada"
    except Exception as e:
        return f"Error al bloquear: {e}"

def _shutdown(mode):
    try:
        if mode == "restart":
            subprocess.run(["shutdown", "/r", "/t", "10", "/c", "ERIS reiniciando el PC"], timeout=5)
            return "PC reiniciando en 10 segundos"
        if mode == "hibernate":
            subprocess.run(["shutdown", "/h"], timeout=5)
            return "PC hibernando"
        else:
            subprocess.run(["shutdown", "/s", "/t", "10", "/c", "ERIS apagando el PC"], timeout=5)
            return "PC apagando en 10 segundos"
    except Exception as e:
        return f"Error: {e}"

def _sleep_pc():
    try:
        subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], timeout=5)
        return "PC en suspensión"
    except Exception as e:
        return f"Error al suspender: {e}"

def _logout_pc():
    try:
        subprocess.run(["shutdown", "/l"], timeout=5)
        return "Cerrando sesión"
    except Exception as e:
        return f"Error al cerrar sesión: {e}"

def _full_status():
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("C:\\")
        bat = psutil.sensors_battery()
        bat_str = f"Batería: {bat.percent}% ({'cargando' if bat.power_plugged else 'batería'})" if bat else "Sin batería (desktop)"
        return (
            f"CPU: {cpu}% | RAM: {mem.percent}% ({mem.used // (1024**3)}GB/{mem.total // (1024**3)}GB) | "
            f"Disco C: {disk.percent}% ({disk.free // (1024**3)}GB libres) | {bat_str}"
        )
    except ImportError:
        return "psutil no instalado. pip install psutil"
    except Exception as e:
        return f"Error: {e}"
