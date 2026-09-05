# -*- coding: utf-8 -*-
"""
system_volume.py — Control del volumen y audio del sistema.
Windows: pycaw (Core Audio). Linux: pactl (PulseAudio/WirePlumber) con fallback wpctl.
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

import re
import shutil
import subprocess
import sys

_IS_LINUX = sys.platform.startswith("linux")


# ── Backend Linux (pactl / wpctl) ─────────────────────────────────────────────

def _run(cmd, timeout=8):
    """Ejecutar subprocess y devolver (rc, stdout, stderr)."""
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout or "", p.stderr or ""
    except Exception as e:
        return -1, "", str(e)


def _linux_has_pactl():
    return bool(shutil.which("pactl"))


def _linux_sinks():
    """Lista de sinks de reproduccion: {index, name, description, volume, muted, is_default}."""
    rc, out, _ = _run(["pactl", "list", "sinks"])
    if rc != 0:
        return []
    drc, dout, _ = _run(["pactl", "get-default-sink"])
    default = (dout or "").strip() if drc == 0 else ""
    sinks, cur = [], {}
    for line in (out or "").splitlines():
        if line.startswith("Sink #"):
            if cur:
                sinks.append(cur)
            cur = {}
        m = re.match(r"\s+(Name|Description|Mute):\s+(.+)", line)
        if m:
            cur[m.group(1).lower()] = m.group(2).strip()
        m = re.match(r"\s+Volume:.*?(\d+)%", line)
        if m and "volume" not in cur:
            cur["volume"] = int(m.group(1))
    if cur:
        sinks.append(cur)
    for idx, s in enumerate(sinks):
        s["index"] = idx
        s.setdefault("volume", -1)
        s.setdefault("muted", None)
        s["is_default"] = s.get("name") == default
    return sinks


def _linux_sink_status():
    """(volumen 0-100|None, muted|None, sink_name|None) del sink por defecto."""
    rc, out, _ = _run(["pactl", "get-sink-volume", "@DEFAULT_SINK@"])
    if rc != 0:
        return _linux_wpctl_status()
    m = re.search(r"(\d+)%", out or "")
    level = int(m.group(1)) if m else None
    rc2, out2, _ = _run(["pactl", "get-sink-mute", "@DEFAULT_SINK@"])
    muted = ("yes" in (out2 or "").lower()) if rc2 == 0 else None
    rc3, out3, _ = _run(["pactl", "get-default-sink"])
    sink = (out3 or "").strip() if rc3 == 0 else None
    return level, muted, sink


def _linux_wpctl_status():
    """Fallback sin pactl (PipeWire nativo)."""
    rc, out, _ = _run(["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"])
    if rc != 0:
        return None, None, None
    m = re.search(r"([\d.]+)", out or "")
    level = int(round(float(m.group(1)) * 100)) if m else None
    return level, "[MUTED]" in (out or "").upper(), None


def _linux_set_volume(level: int):
    level = max(0, min(100, int(level)))
    rc, _, _ = _run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{level}%"])
    if rc != 0:
        _run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"{level}%"])
    return level


def _linux_set_mute(muted: bool):
    val = "1" if muted else "0"
    rc, _, _ = _run(["pactl", "set-sink-mute", "@DEFAULT_SINK@", val])
    if rc != 0:
        rc, _, _ = _run(["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", val])
    return rc == 0


def _linux_toggle_mute():
    rc, _, _ = _run(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "toggle"])
    if rc != 0:
        rc, _, _ = _run(["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "toggle"])
    return rc == 0


def _linux_set_default_sink(name: str) -> bool:
    rc, _, _ = _run(["pactl", "set-default-sink", name])
    return rc == 0


def _linux_devices_lines():
    lines = ["Dispositivos de audio del sistema:"]
    for d in _linux_sinks():
        vol = f"{d['volume']}%" if d["volume"] >= 0 else "?"
        star = " *" if d["is_default"] else ""
        lst = f" (mute:{d['muted']})" if isinstance(d["muted"], bool) else ""
        lines.append(f"  #{d['index']}{star} {d['name']} ({vol}){lst}")
    return "\n".join(lines) if len(lines) > 1 else "No hay dispositivos de audio."


def _linux_volume_control(action, params):
    if action == "devices":
        return _linux_devices_lines()

    if action == "set_device":
        device = (params.get("device") or "").strip()
        if not device:
            return "Error: se requiere 'device' (nombre o indice). Usa 'devices' para listar."
        devs = _linux_sinks()
        if not devs:
            return "No hay dispositivos de audio."
        target = None
        if device.isdigit():
            target = next((d for d in devs if d["index"] == int(device)), None)
        else:
            target = next((d for d in devs
                           if device.lower() in (d.get("name") or "").lower()
                           or device.lower() in (d.get("description") or "").lower()), None)
        if not target:
            names = ", ".join(f"#{d['index']} {d.get('description') or d['name']}" for d in devs[:8])
            return f"No encontre '{device}'. Dispositivos: {names}"
        if _linux_set_default_sink(target["name"]):
            return f"Dispositivo de audio cambiado a: {target.get('description') or target['name']}"
        return "Error cambiando el dispositivo de audio."

    level, muted, _ = _linux_sink_status()
    if level is None and not (shutil.which("pactl") or shutil.which("wpctl")):
        return "Error accediendo al audio del sistema (sin pactl ni wpctl)."

    if action == "get":
        vol = f"Volumen del sistema: {level}%" if level is not None else "Volumen del sistema: n/d."
        st = f" Silencio: {'ACTIVADO' if muted else 'off'}." if isinstance(muted, bool) else ""
        return vol + st

    if action == "set":
        try:
            lvl = int(params.get("level") or params.get("value") or 0)
        except (TypeError, ValueError):
            return "Error: 'level' debe ser un numero (0-100)."
        return f"Volumen del sistema fijado al {_linux_set_volume(lvl)}%."

    if action in ("up", "down"):
        try:
            step = int(params.get("step", 10))
        except (TypeError, ValueError):
            step = 10
        base = level if level is not None else 50
        lvl = max(0, min(100, base + (step if action == "up" else -step)))
        return f"Volumen {'subido' if action == 'up' else 'bajado'} al {_linux_set_volume(lvl)}%."

    if action == "mute":
        return "Audio silenciado." if _linux_set_mute(True) else "Error cambiando mute."
    if action == "unmute":
        return "Audio con sonido." if _linux_set_mute(False) else "Error cambiando mute."
    if action == "toggle_mute":
        return "Alternado silencio." if _linux_toggle_mute() else "Error cambiando mute."

    return "Acciones: get, set (level), up/down (step), mute, unmute, toggle_mute, devices, set_device (device)."


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

    if _IS_LINUX:
        return _linux_volume_control(action, parameters)

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
