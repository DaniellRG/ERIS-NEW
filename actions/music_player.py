import os
import json
import subprocess
from pathlib import Path
from datetime import datetime

MUSIC_DIRS = [
    Path.home() / "Music",
    Path.home() / "Downloads",
    Path("E:\\Music"),
    Path("D:\\Music"),
    Path("E:\\SteamLibrary\\music"),
]

def music_player(parameters: dict, player=None) -> str:
    action = (parameters.get("action") or "play").lower()
    query = parameters.get("query") or parameters.get("song") or parameters.get("artist") or ""
    volume = parameters.get("volume")

    if player:
        player.write_log(f"🎵 Música: {action} {query}")

    if action in ("play", "reproducir", "poner"):
        return _play_music(query)
    elif action in ("pause", "pausar"):
        return _pause()
    elif action in ("stop", "detener"):
        return _stop()
    elif action in ("next", "siguiente"):
        return _next_track()
    elif action in ("previous", "anterior"):
        return _prev_track()
    elif action in ("volume", "volumen"):
        return _set_volume_music(volume or "50")
    elif action in ("list", "listar", "biblioteca"):
        return _list_music()
    elif action in ("shuffle", "aleatorio"):
        return _shuffle()
    else:
        return f"Acciones: play, pause, stop, next, previous, volume, list, shuffle"

def _find_music_files(query=""):
    files = []
    for music_dir in MUSIC_DIRS:
        if music_dir.exists():
            for ext in ["*.mp3", "*.wav", "*.flac", "*.m4a", "*.ogg", "*.aac"]:
                for f in music_dir.rglob(ext):
                    if not query or query.lower() in f.stem.lower():
                        files.append(f)
    return files

def _play_music(query=""):
    files = _find_music_files(query)
    if not files:
        return f"No encontré música {'con ' + query if query else ''}. Mira en: {', '.join(str(d) for d in MUSIC_DIRS if d.exists())}"

    music_file = files[0]
    try:
        os.startfile(str(music_file))
        return f"Reproduciendo: {music_file.stem}"
    except:
        pass

    try:
        subprocess.Popen(["cmd", "/c", "start", "", str(music_file)])
        return f"Reproduciendo: {music_file.stem}"
    except Exception as e:
        return f"No pude reproducir: {e}"

def _pause():
    try:
        import pyautogui
        pyautogui.press("playpause")
        return "Música pausada/reproducida"
    except:
        return "Usá el reproductor del sistema para pausar"

def _stop():
    return _pause()

def _next_track():
    try:
        import pyautogui
        pyautogui.press("nexttrack")
        return "Siguiente tema"
    except:
        return "Usá el reproductor del sistema"

def _prev_track():
    try:
        import pyautogui
        pyautogui.press("prevtrack")
        return "Tema anterior"
    except:
        return "Usá el reproductor del sistema"

def _set_volume_music(vol_str):
    try:
        vol = int(vol_str)
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        from comtypes import CLSCTX_ALL
        devices = AudioUtilities.GetSpeakers()
        iface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = iface.QueryInterface(IAudioEndpointVolume)
        volume.SetMasterVolumeLevelScalar(max(0, min(100, vol)) / 100, None)
        return f"Volumen de música: {vol}%"
    except Exception as e:
        return f"Error: {e}"

def _list_music():
    files = _find_music_files()
    if not files:
        return "No encontré archivos de música."
    lines = [f"🎵 {f.stem}" for f in files[:20]]
    return f"Música encontrada ({len(files)} canciones):\n" + "\n".join(lines)

def _shuffle():
    import random
    files = _find_music_files()
    if not files:
        return "No hay música para mezclar."
    random.shuffle(files)
    try:
        os.startfile(str(files[0]))
        return f"🔀 Aleatorio: {files[0].stem}"
    except:
        return "No pude reproducir"
