"""computer_settings.py — Clean Win32/system settings controls."""
import os
import sys
import platform as _plat
_IS_WIN = _plat.system() == "Windows"
if not _IS_WIN:
    class _Noop:
        def __call__(self, *a, **kw): return 0
        def __getitem__(self, k): return _Noop()
        def __getattr__(self, n): return _Noop()
    _WIN32 = _Noop()
    _KERNEL32 = _Noop()
    _SHELL32 = _Noop()
    _WINMM = _Noop()
else:
    import ctypes as _ctypes
    _WIN32 = _ctypes.windll.user32
    _KERNEL32 = _ctypes.windll.kernel32
    _SHELL32 = _ctypes.windll.shell32
    _WINMM = _ctypes.windll.winmm


def computer_settings(parameters: dict, response=None, player=None) -> str:
    """Adjust system settings like volume, brightness, or active window states."""
    action = parameters.get("action", "").lower()
    value = parameters.get("value", "")

    if action == "volume":
        try:
            import pyautogui
            if str(value).isdigit():
                target = int(value)
                try:
                    from ctypes import cast, POINTER
                    from comtypes import CoInitialize, CoUninitialize
                    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                    CoInitialize()
                    devices = AudioUtilities.GetSpeakers()
                    interface = devices.Activate(IAudioEndpointVolume._iid_, 1, None)
                    volume_ctrl = cast(interface, POINTER(IAudioEndpointVolume))
                    scalar_vol = max(0.0, min(1.0, target / 100.0))
                    volume_ctrl.SetMasterVolumeLevelScalar(scalar_vol, None)
                    CoUninitialize()
                    msg = f"Master volume adjusted to {target}%."
                except Exception as e:
                    msg = f"Could not set absolute volume: {e}"
            else:
                if "up" in value.lower() or "subir" in value.lower():
                    pyautogui.press("volumeup", presses=5)
                    msg = "Volume increased."
                elif "down" in value.lower() or "bajar" in value.lower():
                    pyautogui.press("volumedown", presses=5)
                    msg = "Volume decreased."
                elif "mute" in value.lower() or "silenciar" in value.lower():
                    pyautogui.press("volumemute")
                    msg = "Volume muted."
                else:
                    msg = f"Unrecognized volume value: {value}"
            if player:
                player.write_log(f"🔊 {msg}")
            return msg
        except Exception as e:
            return f"Failed to adjust volume: {e}"

    elif action in ("minimize", "window_minimize"):
        try:
            import ctypes
            hwnd = _WIN32.GetForegroundWindow() if _IS_WIN else None
            if hwnd:
                _WIN32.ShowWindow(hwnd, 6)  # SW_MINIMIZE = 6
                return "Active window minimized."
            return "No active window found."
        except Exception as e:
            return f"Failed to minimize window: {e}"

    # En Linux: usar herramientas nativas (pactl, notify-send, etc.)
    if not _IS_WIN:
        import subprocess as _sp
        if action in ("brightness",):
            try:
                r = _sp.run(["brightnessctl", "set", str(value)], capture_output=True, text=True, timeout=10)
                return f"Brightness set to {value}%" if r.returncode == 0 else f"brightnessctl failed: {r.stderr}"
            except Exception as e:
                return f"Could not set brightness: {e}"
        if action == "notification":
            try:
                _sp.run(["notify-send", "ERIS", str(value)], timeout=5)
                return "Notification sent."
            except Exception as e:
                return f"notify-send failed: {e}"

    return "Action not recognized."

