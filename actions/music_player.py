import os
import subprocess
from pathlib import Path

MEDIA_EXTS = {
    ".mp3", ".wav", ".flac", ".m4a", ".ogg", ".aac", ".wma",
    ".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v",
    ".mpg", ".mpeg", ".3gp",
}

MUSIC_DIRS = [
    Path.home() / "Music",
    Path.home() / "Downloads",
    Path("E:\\Music"), Path("D:\\Music"),
    Path("E:\\SteamLibrary\\music"),
]


def _find_media_files(query: str = "") -> list[Path]:
    files = []
    for d in MUSIC_DIRS:
        if d.exists():
            for ext in MEDIA_EXTS:
                for f in d.rglob(f"*{ext}"):
                    if not query or query.lower() in f.stem.lower():
                        files.append(f)
    return files


def _play_file(path: Path) -> str:
    try:
        os.startfile(str(path))
        return f"Reproduciendo: {path.name}"
    except Exception:
        pass
    try:
        subprocess.Popen(["cmd", "/c", "start", "", str(path)])
        return f"Reproduciendo: {path.name}"
    except Exception as e:
        return f"No pude reproducir {path.name}: {str(e)[:80]}"


def music_player(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = (params.get("action") or "play").lower()
    query = params.get("query") or params.get("song") or params.get("artist") or ""
    path_str = params.get("path", "")
    volume = params.get("volume")

    # ── Play a specific file by path (any format, any location) ──
    if action in ("play_file", "abrir", "reproducir_archivo"):
        if not path_str:
            return "Necesito la ruta del archivo. Usá 'path'."
        p = Path(path_str)
        if not p.exists():
            return f"No encontré el archivo: {p}"
        if p.suffix.lower() not in MEDIA_EXTS:
            return f"No reconozco el formato {p.suffix}. Soporto: {', '.join(sorted(MEDIA_EXTS))}"
        return _play_file(p)

    # ── Play by search query ──
    if action in ("play", "reproducir", "poner"):
        if path_str:
            p = Path(path_str)
            if p.exists():
                return _play_file(p)
        if query:
            files = _find_media_files(query)
            if files:
                return _play_file(files[0])
            return f"No encontré '{query}' en las carpetas de música."
        files = _find_media_files()
        if not files:
            return "No hay archivos de música en las carpetas habituales."
        return _play_file(files[0])

    elif action in ("pause", "pausar"):
        try:
            import pyautogui
            pyautogui.press("playpause")
            return "Pausado/reanudado"
        except Exception:
            return "Usá el reproductor del sistema para pausar"

    elif action in ("stop", "detener"):
        try:
            import pyautogui
            pyautogui.press("playpause")
            return "Detenido"
        except Exception:
            return "Usá el reproductor del sistema"

    elif action in ("next", "siguiente"):
        try:
            import pyautogui
            pyautogui.press("nexttrack")
            return "Siguiente"
        except Exception:
            return "Usá el reproductor del sistema"

    elif action in ("previous", "anterior"):
        try:
            import pyautogui
            pyautogui.press("prevtrack")
            return "Anterior"
        except Exception:
            return "Usá el reproductor del sistema"

    elif action in ("volume", "volumen"):
        try:
            vol = int(volume or "50")
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            from comtypes import CLSCTX_ALL
            devices = AudioUtilities.GetSpeakers()
            iface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            v = iface.QueryInterface(IAudioEndpointVolume)
            v.SetMasterVolumeLevelScalar(max(0, min(100, vol)) / 100, None)
            return f"Volumen: {vol}%"
        except Exception as e:
            return f"Error de volumen: {str(e)[:80]}"

    elif action in ("list", "listar", "biblioteca"):
        files = _find_media_files()
        if not files:
            return "No encontré archivos multimedia."
        audio = [f for f in files if f.suffix in {".mp3",".wav",".flac",".m4a",".ogg",".aac",".wma"}]
        video = [f for f in files if f not in audio]
        lines = []
        if audio:
            lines.append(f"Audio ({len(audio)}): " + ", ".join(f.stem for f in audio[:8]))
            if len(audio) > 8:
                lines[-1] += f" y {len(audio)-8} más"
        if video:
            lines.append(f"Video ({len(video)}): " + ", ".join(f.stem for f in video[:5]))
            if len(video) > 5:
                lines[-1] += f" y {len(video)-5} más"
        return "\n".join(lines) if lines else "No hay archivos multimedia."

    elif action in ("shuffle", "aleatorio"):
        import random
        files = _find_media_files()
        if not files:
            return "No hay archivos para mezclar."
        random.shuffle(files)
        return _play_file(files[0])

    else:
        return (
            "Acciones:\n"
            "  play / reproducir — Busca y reproduce (query o path)\n"
            "  play_file / abrir — Reproduce un archivo específico (path)\n"
            "  pause / stop / next / previous — Control de reproducción\n"
            "  volume — Volumen del sistema (0-100)\n"
            "  list — Listar biblioteca\n"
            "  shuffle — Reproducir aleatorio\n\n"
            "Soporta audio: MP3, WAV, FLAC, M4A, OGG, AAC\n"
            "Soporta video: MP4, AVI, MKV, MOV, WMV, FLV, WEBM, MPG\n"
            "Usá 'path' para reproducir archivos de cualquier ubicación."
        )
