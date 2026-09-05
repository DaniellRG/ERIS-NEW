# -*- coding: utf-8 -*-
"""
screen_control.py — Control de la pantalla: brillo.
Windows: WMI (WmiMonitorBrightness). Linux: brightnessctl.
Acciones: brightness_get, brightness_set (level 0-100).
"""
from __future__ import annotations
import shutil
import subprocess
import sys

_IS_LINUX = sys.platform.startswith("linux")

_PS = (
    "powershell -NoProfile -NonInteractive -Command "
)


def _get_brightness() -> int:
    cmd = _PS + "(Get-CimInstance -Namespace root/wmi -ClassName WmiMonitorBrightness).CurrentBrightness"
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    try:
        return int(out.stdout.strip())
    except (TypeError, ValueError):
        raise RuntimeError("No se pudo leer el brillo (probablemente no es una laptop con sensor WMI).")


def _set_brightness(level: int) -> None:
    cmd = (
        _PS + "$m = Get-CimInstance -Namespace root/wmi -ClassName WmiMonitorBrightnessMethods; "
        "$m.WmiSetBrightness(1, " + str(level) + ")"
    )
    subprocess.run(cmd, capture_output=True, text=True, timeout=15)


def _get_brightness_linux() -> int:
    bc = shutil.which("brightnessctl")
    if not bc:
        raise RuntimeError("brightnessctl no instalado (pacman -S brightnessctl).")
    r = subprocess.run([bc, "-m", "info"], capture_output=True, text=True, timeout=8)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or "").strip() or "brightnessctl fallo.")
    parts = (r.stdout or "").strip().split(",")
    if len(parts) < 4:
        raise RuntimeError("Formato brightnessctl inesperado.")
    return int(parts[3].replace("%", "").strip())


def _set_brightness_linux(level: int) -> None:
    bc = shutil.which("brightnessctl")
    if not bc:
        raise RuntimeError("brightnessctl no instalado (pacman -S brightnessctl).")
    r = subprocess.run([bc, "set", f"{level}%"], capture_output=True, text=True, timeout=8)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or "").strip() or "permisos requeridos (udev rule / pkexec).")


def screen_control(parameters: dict = None, player=None) -> str:
    if parameters is None:
        parameters = {}
    action = parameters.get("action", "brightness_get").lower()

    if action in ("brightness_get", "get", "brightness"):
        try:
            level = _get_brightness_linux() if _IS_LINUX else _get_brightness()
            return f"Brillo de pantalla: {level}%."
        except Exception as e:
            return f"Error leyendo brillo: {e}"

    if action in ("brightness_set", "set"):
        try:
            level = int(parameters.get("level") or parameters.get("value") or 0)
        except (TypeError, ValueError):
            return "Error: 'level' debe ser un numero (0-100)."
        level = max(0, min(100, level))
        try:
            if _IS_LINUX:
                _set_brightness_linux(level)
            else:
                _set_brightness(level)
            return f"Brillo de pantalla fijado al {level}%."
        except Exception as e:
            return f"Error fijando brillo: {e}"

    return "Acciones: brightness_get, brightness_set (level)."
