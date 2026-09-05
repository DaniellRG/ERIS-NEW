import subprocess
import os
import json
import sys
import shutil
from pathlib import Path

_IS_LINUX = sys.platform.startswith("linux")
_IS_WINDOWS = sys.platform == "win32"
_IS_WAYLAND = _IS_LINUX and os.environ.get("XDG_SESSION_TYPE") == "wayland"

CONFIG_FILE = Path(__file__).resolve().parent.parent / "config" / "pc_control.json"

def _load_config():
    try:
        if CONFIG_FILE.exists():
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError): pass
    return {}

def _save_config(data):
    try:
        CONFIG_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except OSError: pass

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
    elif action in ("brightness_get", "estado brillo"):
        return _brightness("get", value)
    elif action in ("brightness_set", "poner brillo"):
        return _brightness("set", value)
    elif action in ("brightness_up", "subir brillo"):
        return _brightness("up", value)
    elif action in ("brightness_down", "bajar brillo"):
        return _brightness("down", value)
    elif action in ("lock", "bloquear"):
        return _lock_pc()
    elif action in ("restart", "reiniciar", "shutdown", "apagar pc", "sleep", "suspender",
                    "logout", "cerrar sesion", "hibernate", "hibernar"):
        return ("⛔ Acción de energía deshabilitada por seguridad: "
                "ERIS no puede apagar, suspender, reiniciar, hibernar ni cerrar la sesión del PC.")
    elif action in ("status", "estado"):
        return _full_status()
    else:
        return (
            f"Acciones disponibles: volume_up, volume_down, volume_set, mute, unmute, "
            f"monitor_on, monitor_off, wifi_on, wifi_off, wifi_status, "
            f"bluetooth_on, bluetooth_off, bluetooth_status, "
            f"brightness_get, brightness_set, brightness_up, brightness_down, "
            f"screenshot, lock, status"
        )

def _change_volume(delta):
    if _IS_LINUX:
        from actions.system_volume import _linux_sink_status, _linux_set_volume
        cur, _, _ = _linux_sink_status()
        base = cur if cur is not None else 50
        return f"Volumen ajustado a {_linux_set_volume(base + delta)}%"
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
    if _IS_LINUX:
        from actions.system_volume import _linux_set_volume
        return f"Volumen puesto a {_linux_set_volume(level)}%"
    try:
        from pycaw.pycaw import AudioUtilities
        volume = AudioUtilities.GetSpeakers().EndpointVolume
        vol = max(0.0, min(1.0, level / 100))
        volume.SetMasterVolumeLevelScalar(vol, None)
        return f"Volumen puesto a {level}%"
    except Exception as e:
        return f"Error al poner volumen: {e}"

def _mute_unmute(mute):
    if _IS_LINUX:
        from actions.system_volume import _linux_set_mute
        ok = _linux_set_mute(bool(mute))
        return ("Silenciado" if mute else "Sonido activado") if ok else "Error al cambiar mute"
    try:
        from pycaw.pycaw import AudioUtilities
        volume = AudioUtilities.GetSpeakers().EndpointVolume
        volume.SetMute(bool(mute), None)
        return "Silenciado" if mute else "Sonido activado"
    except Exception as e:
        return f"Error: {e}"

def _monitor_off():
    if _IS_LINUX:
        r = subprocess.run(["hyprctl", "dispatch", "hl.dsp.dpms({ action = 'off' })"],
                           capture_output=True, text=True, timeout=8)
        return "Monitor apagado" if r.returncode == 0 else f"Error al apagar monitor: {(r.stderr or '').strip()}"
    try:
        import ctypes
        ctypes.windll.user32.SendMessageW(0xFFFF, 0x0112, 0xF170, 2)
        return "Monitor apagado"
    except Exception as e:
        return f"Error al apagar monitor: {e}"

def _monitor_on():
    if _IS_LINUX:
        r = subprocess.run(["hyprctl", "dispatch", "hl.dsp.dpms({ action = 'on' })"],
                           capture_output=True, text=True, timeout=8)
        return "Monitor encendido" if r.returncode == 0 else f"Error al encender monitor: {(r.stderr or '').strip()}"
    try:
        import ctypes
        ctypes.windll.user32.SendMessageW(0xFFFF, 0x0112, 0xF170, -1)
        return "Monitor encendido"
    except Exception as e:
        return f"Error al encender monitor: {e}"

def _wifi_toggle(enable):
    if _IS_LINUX:
        r = subprocess.run(["nmcli", "radio", "wifi", "on" if enable else "off"],
                           capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            return f"WiFi {'encendido' if enable else 'apagado'}"
        return f"Error: {(r.stderr or '').strip() or 'permisos requeridos (nmcli radio) '}"
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
    if _IS_LINUX:
        r = subprocess.run(["nmcli", "-t", "-f", "WIFI", "radio"],
                           capture_output=True, text=True, timeout=10)
        state = (r.stdout or "").strip()
        ssid = ""
        r2 = subprocess.run(["nmcli", "-t", "-f", "ACTIVE,SSID", "dev", "wifi"],
                            capture_output=True, text=True, timeout=10)
        for line in (r2.stdout or "").splitlines():
            if line.startswith("yes:"):
                ssid = line.split(":", 1)[-1]
                break
        base = f"WiFi conectado a '{ssid}'" if ssid else "WiFi conectado"
        return (base if state in ("enabled", "yes") else "WiFi apagado") + f" (radio {state})"
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
    if _IS_LINUX:
        r = subprocess.run(["rfkill", "unblock" if enable else "block", "bluetooth"],
                           capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            return f"Bluetooth {'encendido' if enable else 'apagado'}"
        return f"Error Bluetooth: {(r.stderr or '').strip() or 'permisos requeridos (rfkill) '}"
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
    if _IS_LINUX:
        r = subprocess.run(["rfkill", "list", "bluetooth"],
                           capture_output=True, text=True, timeout=10)
        lines = (r.stdout or "").splitlines()
        soft = "no" if any("Soft blocked: no" in line for line in lines) else "blocked"
        hard = "no" if any("Hard blocked: no" in line for line in lines) else "blocked"
        state = "encendido" if soft == "no" else "apagado"
        return f"Bluetooth: {state} (soft {soft}, hard {hard})"
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
    from datetime import datetime
    if _IS_LINUX:
        shots = Path.home() / "Pictures" / "Eris"
        shots.mkdir(parents=True, exist_ok=True)
        filepath = shots / f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        if _IS_WAYLAND:
            grim = shutil.which("grim")
            if grim:
                r = subprocess.run([grim, str(filepath)], capture_output=True, text=True, timeout=15)
                if r.returncode == 0:
                    return f"Captura guardada en: {filepath}"
                return f"Error en captura: {(r.stderr or '').strip()}"
        try:
            from mss import mss
            with mss() as sct:
                sct.shot(mon=0, output=str(filepath))
            return f"Captura guardada en: {filepath}"
        except Exception as e:
            return f"Error en captura: {e}"
    try:
        from mss import mss
        desktop = Path.home() / "Desktop"
        filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = desktop / filename
        with mss() as sct:
            sct.shot(mon=0, output=str(filepath))
        return f"Captura guardada en: {filepath}"
    except Exception as e:
        return f"Error en captura: {e}"

def _lock_pc():
    if _IS_LINUX:
        locker = shutil.which("hyprlock") or shutil.which("swaylock") or shutil.which("i3lock")
        cmd = [locker] if locker else ["loginctl", "lock-session"]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
        if r.returncode == 0:
            return "PC bloqueada"
        return f"Error al bloquear: {(r.stderr or '').strip() or 'sin locker instalado (instala hyprlock)'}"
    try:
        subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"], timeout=5)
        return "PC bloqueada"
    except Exception as e:
        return f"Error al bloquear: {e}"

def _full_status():
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("C:\\" if _IS_WINDOWS else "/")
        bat = psutil.sensors_battery()
        bat_str = f"Batería: {bat.percent}% ({'cargando' if bat.power_plugged else 'batería'})" if bat else "Sin batería (desktop)"
        disk_label = "Disco C" if _IS_WINDOWS else "Disco /"
        return (
            f"CPU: {cpu}% | RAM: {mem.percent}% ({mem.used // (1024**3)}GB/{mem.total // (1024**3)}GB) | "
            f"{disk_label}: {disk.percent}% ({disk.free // (1024**3)}GB libres) | {bat_str}"
        )
    except ImportError:
        return "psutil no instalado. pip install psutil"
    except Exception as e:
        return f"Error: {e}"


def _brightness(action: str, value) -> str:
    """Brillo de pantalla vía brightnessctl (Linux)."""
    if not _IS_LINUX:
        return "Brillo: no disponible en Windows aún (pending)."
    bc = shutil.which("brightnessctl")
    if not bc:
        return "Brillo: brightnessctl no instalado (pacman -S brightnessctl)."
    try:
        if action == "get":
            r = subprocess.run([bc, "-m", "info"], capture_output=True, text=True, timeout=8)
            if r.returncode != 0:
                return f"Error brillo: {(r.stderr or '').strip()}"
            parts = (r.stdout or "").strip().split(",")
            pct = f"{parts[3].replace('%', '')}%" if len(parts) >= 4 else "?"
            return f"Brillo actual: {pct}"
        if action == "set":
            try:
                lvl = max(0, min(100, int(value)))
            except (TypeError, ValueError):
                return "Error: 'value' debe ser un numero (0-100)."
            r = subprocess.run([bc, "set", f"{lvl}%"], capture_output=True, text=True, timeout=8)
            if r.returncode == 0:
                return f"Brillo puesto a {lvl}%."
            return f"Error: {(r.stderr or '').strip() or 'permisos requeridos (udev rule / pkexec)'}"
        if action in ("up", "down"):
            try:
                step = max(1, abs(int(value or 10)))
            except (TypeError, ValueError):
                step = 10
            r = subprocess.run([bc, "set", f"{'+' if action == 'up' else '-'}{step}%"],
                               capture_output=True, text=True, timeout=8)
            if r.returncode == 0:
                return f"Brillo {'subido' if action == 'up' else 'bajado'} {step}%."
            return f"Error: {(r.stderr or '').strip() or 'permisos requeridos (udev rule / pkexec)'}"
    except Exception as e:
        return f"Error brillo: {e}"
    return "Acciones brillo: brightness_get, brightness_set (value 0-100), brightness_up/down."
