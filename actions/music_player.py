import os
import shutil
import subprocess
import sys
import urllib.parse
from pathlib import Path

MEDIA_EXTS = {
    ".mp3", ".wav", ".flac", ".m4a", ".ogg", ".aac", ".wma",
    ".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v",
    ".mpg", ".mpeg", ".3gp",
}

_AUDIO_EXTS = {".mp3", ".wav", ".flac", ".m4a", ".ogg", ".aac", ".wma"}


def _music_dirs() -> list[Path]:
    """Carpetas de música PORTABLES (sin rutas Windows hardcodeadas).
    Extra: ERIS_MUSIC_DIRS (separadas por os.pathsep)."""
    dirs = [
        Path.home() / "Music",
        Path.home() / "Música",
        Path.home() / "Downloads",
    ]
    env = os.environ.get("ERIS_MUSIC_DIRS", "")
    for extra in env.split(os.pathsep):
        if extra.strip():
            dirs.append(Path(extra.strip()).expanduser())
    if os.name == "nt":
        drives = [Path(f"{d}:\\Music") for d in "CDEFGH"]
        dirs.extend(p for p in drives if p.exists())
    return dirs


def _find_media_files(query: str = "") -> list[Path]:
    files = []
    for d in _music_dirs():
        if d.exists():
            for ext in MEDIA_EXTS:
                for f in d.rglob(f"*{ext}"):
                    if not query or query.lower() in f.stem.lower():
                        files.append(f)
    return files


def _open_path(path: Path) -> None:
    """Abre un archivo con el reproductor por defecto. Multiplataforma."""
    p = str(path)
    if os.name == "nt":
        os.startfile(p)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", p])
    else:
        # Linux/Wayland: xdg-open respeta la app por defecto (mpv/vlc/etc.).
        opener = shutil.which("xdg-open") or "xdg-open"
        subprocess.Popen(
            [opener, p],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )


def _play_file(path: Path, player=None) -> str:
    try:
        _open_path(path)
        if player is not None:
            try:
                player.set_music(1.0)
            except Exception:
                pass
        return f"Reproduciendo: {path.name}"
    except Exception as e:
        return f"No pude reproducir {path.name}: {str(e)[:80]}"


def _play_youtube(query: str) -> str:
    """Sin archivo local: abre la búsqueda en el navegador (reproduce en vivo).
    Metal/francotirador: no descarga nada, usa el navegador por defecto."""
    if not query:
        return "No hay archivos locales de música y no me diste qué querés escuchar."
    url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(query)
    try:
        if os.name == "nt":
            os.startfile(url)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", url])
        else:
            opener = shutil.which("xdg-open") or "xdg-open"
            subprocess.Popen([opener, url], stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
        return f"No hay '{query}' local; abrí YouTube con la búsqueda '{query}' en tu navegador."
    except Exception as e:
        return f"No encontré '{query}' local y no pude abrir el navegador: {str(e)[:80]}"


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
        return _play_file(p, player)

    # ── Play by search query ──
    if action in ("play", "reproducir", "poner"):
        if path_str:
            p = Path(path_str)
            if p.exists():
                return _play_file(p, player)
        if query:
            files = _find_media_files(query)
            if files:
                return _play_file(files[0], player)
            return _play_youtube(query)
        files = _find_media_files()
        if not files:
            return "No hay archivos locales de música. Decime qué querés escuchar y lo busco en YouTube."
        return _play_file(files[0], player)

    elif action in ("pause", "pausar"):
        try:
            import pyautogui
            pyautogui.press("playpause")
            if player is not None:
                try:
                    player.set_music(0.0)
                except Exception:
                    pass
            return "Pausado/reanudado"
        except Exception:
            return "Usá el reproductor del sistema para pausar"

    elif action in ("stop", "detener"):
        try:
            import pyautogui
            pyautogui.press("playpause")
            if player is not None:
                try:
                    player.set_music(0.0)
                except Exception:
                    pass
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
        return _play_file(files[0], player)

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
