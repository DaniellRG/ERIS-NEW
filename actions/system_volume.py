# -*- coding: utf-8 -*-
"""
system_volume.py — Control del volumen y audio del sistema (Windows Core Audio, pycaw).
Acciones:
  get        — Volumen y mute actuales
  set        — Fijar volumen (0-100) | params: level
  up         — Subir volumen | params: step (default 10)
  down       — Bajar volumen | params: step (default 10)
  mute       — Silenciar
  unmute     — Quitar silencio
  toggle_mute— Alternar silencio
  devices    — Listar dispositivos de reproduccion activos
  set_device — Cambiar dispositivo de reproduccion por defecto | params: device (nombre o indice)
"""
from __future__ import annotations


def _volume_interface():
    from pycaw.pycaw import AudioUtilities
    return AudioUtilities.GetSpeakers().EndpointVolume


def _set_mute(volume, muted: bool) -> str:
    try:
        volume.SetMute(bool(muted), None)
        state = "silenciado" if muted else "con sonido"
        return f"Audio {state}."
    except Exception as e:
        return f"Error al cambiar mute: {e}"


def _get_devices():
    from pycaw.pycaw import AudioUtilities
    out = []
    for i, dev in enumerate(AudioUtilities.GetAllDevices()):
        try:
            lvl = int(round(dev.EndpointVolume.GetMasterVolumeLevelScalar() * 100))
        except Exception:
            lvl = -1
        out.append({"index": i, "name": dev.FriendlyName or "(sin nombre)", "id": dev.id, "volume": lvl})
    return out


def system_volume(parameters: dict = None, player=None) -> str:
    if parameters is None:
        parameters = {}
    action = parameters.get("action", "get").lower()

    if action == "devices":
        try:
            devs = _get_devices()
        except Exception as e:
            return f"Error listando dispositivos: {e}"
        if not devs:
            return "No hay dispositivos de audio."
        lines = ["Dispositivos de audio del sistema:"]
        for d in devs:
            vol = f"{d['volume']}%" if d["volume"] >= 0 else "?"
            lines.append(f"  #{d['index']} {d['name']} ({vol})")
        return "\n".join(lines)

    if action == "set_device":
        device = (parameters.get("device") or "").strip()
        if not device:
            return "Error: se requiere 'device' (nombre o indice). Usa 'devices' para listar."
        try:
            devs = _get_devices()
        except Exception as e:
            return f"Error listando dispositivos: {e}"
        target = None
        if device.isdigit():
            target = next((d for d in devs if d["index"] == int(device)), None)
        else:
            target = next((d for d in devs if device.lower() in (d["name"] or "").lower()), None)
        if not target:
            names = ", ".join(f"#{d['index']} {d['name']}" for d in devs[:8])
            return f"No encontre '{device}'. Dispositivos: {names}"
        try:
            from pycaw.pycaw import AudioUtilities
            AudioUtilities.SetDefaultDevice(target["id"])
            return f"Dispositivo de audio cambiado a: {target['name']}"
        except Exception as e:
            return f"Error cambiando dispositivo: {e}"

    try:
        volume = _volume_interface()
    except Exception as e:
        return f"Error accediendo al audio del sistema: {e}"

    if action == "get":
        try:
            level = int(round(volume.GetMasterVolumeLevelScalar() * 100))
            muted = volume.GetMute()
            return f"Volumen del sistema: {level}%. Silencio: {'ACTIVADO' if muted else 'off'}."
        except Exception as e:
            return f"Error leyendo volumen: {e}"

    if action == "set":
        try:
            level = int(parameters.get("level") or parameters.get("value") or 0)
        except (TypeError, ValueError):
            return "Error: 'level' debe ser un numero (0-100)."
        level = max(0, min(100, level))
        try:
            volume.SetMasterVolumeLevelScalar(level / 100.0, None)
            return f"Volumen del sistema fijado al {level}%."
        except Exception as e:
            return f"Error fijando volumen: {e}"

    if action in ("up", "down"):
        step = int(parameters.get("step", 10))
        try:
            current = volume.GetMasterVolumeLevelScalar() * 100
        except Exception:
            current = 50
        level = max(0, min(100, int(round(current + (step if action == "up" else -step)))))
        volume.SetMasterVolumeLevelScalar(level / 100.0, None)
        return f"Volumen {'subido' if action == 'up' else 'bajado'} al {level}%."

    if action == "mute":
        return _set_mute(volume, True)

    if action == "unmute":
        return _set_mute(volume, False)

    if action == "toggle_mute":
        try:
            muted = volume.GetMute()
        except Exception:
            muted = False
        return _set_mute(volume, not muted)

    return "Acciones: get, set (level), up/down (step), mute, unmute, toggle_mute, devices, set_device (device)."
