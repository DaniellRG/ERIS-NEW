"""spotify_control.py — Full Spotify controller using Web API (spotipy) + desktop app control."""
import json
import threading
import time
from pathlib import Path

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
TOKEN_CACHE = CONFIG_DIR / "spotify_token.json"
CREDENTIALS_FILE = CONFIG_DIR / "api_keys.json"

SCOPE = "user-read-playback-state user-modify-playback-state user-read-currently-playing user-library-modify user-library-read playlist-read-private playlist-modify-public playlist-modify-private streaming"
REDIRECT_URI = "http://127.0.0.1:8888/callback"

_sp = None
_lock = threading.Lock()


# ── Helpers ──────────────────────────────────────────────────────

def _get_credentials():
    if not CREDENTIALS_FILE.exists():
        return None, None
    try:
        data = json.loads(CREDENTIALS_FILE.read_text("utf-8"))
        return data.get("spotify_client_id"), data.get("spotify_client_secret")
    except Exception:
        return None, None


def _get_client():
    global _sp
    with _lock:
        if _sp is not None:
            return _sp
        client_id, client_secret = _get_credentials()
        if not client_id or not client_secret:
            return None
        import spotipy
        from spotipy.oauth2 import SpotifyOAuth
        cache_handler = spotipy.cache_handler.CacheFileHandler(cache_path=str(TOKEN_CACHE))
        auth_manager = SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=REDIRECT_URI,
            scope=SCOPE,
            cache_handler=cache_handler,
            open_browser=True,
        )
        _sp = spotipy.Spotify(auth_manager=auth_manager)
        return _sp


# ── Desktop app helpers ──────────────────────────────────────────

def _spotify_window():
    """Find Spotify desktop window, or None.
    Busca por: 1) PID del proceso, 2) titulo 'Spotify', 3) ventana activa de reproduccion.
    """
    try:
        import pygetwindow as gw
        import psutil
        # 1. Buscar por PID del proceso Spotify (lo mas confiable)
        spotify_pids = []
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['name'] and 'spotify' in proc.info['name'].lower():
                    spotify_pids.append(proc.info['pid'])
            except Exception:
                pass
        if spotify_pids:
            for w in gw.getAllWindows():
                if not w.title:
                    continue
                try:
                    if hasattr(w, '_hWnd'):
                        import ctypes
                        from ctypes import wintypes
                        PID = wintypes.DWORD()
                        user32 = ctypes.windll.user32
                        user32.GetWindowThreadProcessId(w._hWnd, ctypes.byref(PID))
                        if PID.value in spotify_pids:
                            return w
                except Exception:
                    pass
        # 2. Buscar por titulo conteniendo "spotify"
        for w in gw.getAllWindows():
            if w.title and "spotify" in w.title.lower():
                return w
    except Exception:
        pass
    return None


def _activate_spotify():
    """Bring Spotify window to front. Returns True if successful."""
    w = _spotify_window()
    if not w:
        return False
    try:
        w.activate()
    except Exception:
        try:
            w.minimize()
            w.restore()
        except Exception:
            pass
    time.sleep(0.25)
    return True


def _has_active_device(sp) -> bool:
    """Check if there's at least one active Spotify Connect device."""
    try:
        devices = sp.devices()
        return any(d.get("is_active") for d in devices.get("devices", []))
    except Exception:
        return False


def _desktop_search(query: str, player=None) -> str:
    """Search and play in Spotify desktop using keyboard shortcuts."""
    if not _activate_spotify():
        return "Spotify no está abierto. Abrí la app de Spotify primero."
    try:
        import pyautogui
        pyautogui.hotkey("ctrl", "k")
        time.sleep(0.4)
        pyautogui.write(query, interval=0.03)
        time.sleep(0.3)
        pyautogui.press("enter")
        time.sleep(0.5)
        pyautogui.press("enter")
        msg = f"▶️ Buscando y reproduciendo '{query}' en Spotify..."
        if player:
            player.write_log(f"🎵 {msg}")
        return msg
    except Exception as e:
        return f"Error al buscar en Spotify: {e}"


def _desktop_play_pause() -> str:
    """Toggle play/pause on desktop Spotify."""
    _activate_spotify()
    try:
        import pyautogui
        pyautogui.press("playpause")
        return "⏯️ Play/Pause"
    except Exception as e:
        return f"Error: {e}"


# ── Main entry point ─────────────────────────────────────────────

def spotify_control(parameters: dict, player=None) -> str:
    action = parameters.get("action", "").lower().strip()
    if not action:
        return "Action parameter is required."

    # Desktop-only actions (don't need API)
    if action == "focus":
        if _activate_spotify():
            return "🎯 Spotify enfocado."
        return "Spotify no está abierto."

    if action == "search_desktop":
        query = parameters.get("query", "")
        if not query:
            return "Query requerida para search_desktop."
        return _desktop_search(query, player)

    # Try Web API first
    sp = _get_client()
    if sp:
        try:
            # For play/resume with query: check for active device first
            if action in ("play", "resume") and parameters.get("query"):
                if not _has_active_device(sp):
                    return _desktop_search(parameters["query"], player)
            return _api_control(sp, action, parameters, player)
        except Exception as e:
            msg = str(e).lower()
            if player:
                player.write_log(f"Spotify API: {e}")
            # No active device → try desktop fallback for play/search
            if "active device" in msg or "no active" in msg:
                if action in ("play", "resume"):
                    query = parameters.get("query", "")
                    if query:
                        return _desktop_search(query, player)
                    return _desktop_play_pause()
                if action == "search":
                    query = parameters.get("query", "")
                    if query:
                        return _desktop_search(query, player)
            return _keyboard_control(action, parameters, player)
    return _keyboard_control(action, parameters, player)


# ── API control ──────────────────────────────────────────────────

def _api_control(sp, action, params, player=None):
    query = params.get("query", "")
    value = params.get("value", "")
    stype = params.get("type", "track")

    if action in ("play", "resume"):
        if query:
            results = sp.search(q=query, limit=5, type=stype)
            items = results.get(stype + "s", {}).get("items", [])
            if not items:
                return f"No se encontró {stype} para '{query}'."
            uri = items[0]["uri"]
            sp.start_playback(uris=[uri])
            name = items[0].get("name", "?")
            artist = ", ".join(a["name"] for a in items[0].get("artists", []))
            r = f"▶️ Reproduciendo {name} — {artist}"
            if player:
                player.write_log(f"🎵 {r}")
            return r
        else:
            sp.start_playback()
            return "▶️ Reanudando"

    elif action == "pause":
        sp.pause_playback()
        return "⏸️ Pausado"

    elif action in ("next", "skip"):
        sp.next_track()
        return "⏭️ Siguiente"

    elif action in ("previous", "prev", "back"):
        sp.previous_track()
        return "⏮️ Anterior"

    elif action == "shuffle":
        state = str(value).lower() in ("true", "1", "yes", "on") if value else True
        sp.shuffle(state)
        return f"🔀 Shuffle {'on' if state else 'off'}"

    elif action == "repeat":
        mode = str(value).lower() if value else "context"
        if mode not in ("off", "track", "context"):
            mode = "context"
        sp.repeat(mode)
        return f"🔁 Repeat: {mode}"

    elif action == "current":
        cur = sp.current_playback()
        if cur is None or cur.get("item") is None:
            return "Nada reproduciéndose."
        item = cur["item"]
        name = item.get("name", "?")
        artists = ", ".join(a["name"] for a in item.get("artists", []))
        album = item.get("album", {}).get("name", "?")
        progress = cur.get("progress_ms", 0) // 1000
        duration = item.get("duration_ms", 0) // 1000
        bar = _bar(progress, duration)
        return f"🎵 {name} — {artists}\n💿 {album}\n{bar} {_fmt(progress)}/{_fmt(duration)}"

    elif action == "search":
        if not query:
            return "Query requerida."
        results = sp.search(q=query, limit=8, type=stype)
        items = results.get(stype + "s", {}).get("items", [])
        if not items:
            return f"Sin resultados para '{query}'."
        lines = [f"Resultados {stype}s para '{query}':"]
        for i, item in enumerate(items[:8], 1):
            name = item.get("name", "?")
            if stype in ("track", "album"):
                artist = ", ".join(a["name"] for a in item.get("artists", []))
                lines.append(f"  {i}. {name} — {artist}")
            elif stype == "artist":
                lines.append(f"  {i}. {name}")
            elif stype == "playlist":
                owner = item.get("owner", {}).get("display_name", "?")
                lines.append(f"  {i}. {name} (por {owner})")
        return "\n".join(lines)

    elif action == "like":
        cur = sp.current_playback()
        if cur and cur.get("item"):
            sp.current_user_saved_tracks_add([cur["item"]["id"]])
            return f"❤️ Guardado '{cur['item']['name']}' en biblioteca"
        return "No hay canción activa."

    elif action == "devices":
        devices = sp.devices()
        devs = devices.get("devices", [])
        if not devs:
            return "Sin dispositivos."
        lines = ["🎧 Dispositivos:"]
        for d in devs:
            icon = "🔊" if d.get("is_active") else "🔇"
            lines.append(f"  {icon} {d.get('name', '?')} ({d.get('type', '?')})")
        return "\n".join(lines)

    elif action == "playlist":
        playlists = sp.current_user_playlists(limit=20)
        items = playlists.get("items", [])
        if not items:
            return "Sin playlists."
        lines = ["📋 Playlists:"]
        for p in items:
            lines.append(f"  • {p.get('name', '?')} ({p.get('tracks', {}).get('total', 0)} canciones)")
        return "\n".join(lines)

    elif action == "volume":
        return _keyboard_control(action, params, player)

    return f"Acción desconocida: {action}"


# ── Keyboard fallback ────────────────────────────────────────────

def _keyboard_control(action, params, player=None):
    import pyautogui
    value = params.get("value", "")

    if action in ("play", "pause", "resume", "toggle"):
        pyautogui.press("playpause")
        r = "⏯️ Toggle"
    elif action in ("next", "skip"):
        pyautogui.press("nexttrack")
        r = "⏭️ Siguiente"
    elif action in ("prev", "previous", "back"):
        pyautogui.press("prevtrack")
        r = "⏮️ Anterior"
    elif action == "volume":
        v = str(value).lower()
        if "up" in v:
            pyautogui.press("volumeup", presses=5)
            r = "🔊 Volumen +"
        elif "down" in v:
            pyautogui.press("volumedown", presses=5)
            r = "🔉 Volumen -"
        elif v.replace(".", "").lstrip("-").isdigit():
            try:
                from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                from comtypes import CLSCTX_ALL
                dev = AudioUtilities.GetSpeakers()
                interface = dev.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                vol_obj = interface.QueryInterface(IAudioEndpointVolume)
                vol_obj.SetMasterVolumeLevelScalar(max(0.0, min(1.0, float(v) / 100.0)), None)
                r = f"🔊 Volumen {v}%"
            except Exception:
                r = "No se pudo ajustar volumen exacto."
        else:
            r = f"Valor de volumen no válido: {value}"
    elif action in ("current",):
        return "No disponible sin API."
    elif action in ("search", "like", "devices", "playlist", "shuffle", "repeat",
                    "search_desktop", "focus"):
        return f"Usa Spotify Web API para '{action}'."
    else:
        r = f"Acción '{action}' no soportada"

    if player:
        player.write_log(f"🎵 {r}")
    return r


# ── Formatting ───────────────────────────────────────────────────

def _fmt(secs):
    m, s = divmod(int(secs), 60)
    return f"{m}:{s:02d}"


def _bar(current, total):
    if total == 0:
        return "[-----]"
    filled = int(20 * current / total)
    return "[" + "█" * filled + "░" * (20 - filled) + "]"
