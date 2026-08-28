"""
actions/spotify_control.py — Spotify control for ERIS.
Uses spotipy library to interact with Spotify Web API.
Actions:
  status   — Current playing track info
  play     — Resume or play specific track/artist/album
  pause    — Pause playback
  next     — Skip to next track
  previous — Go to previous track
  volume   — Set volume (0-100)
  search   — Search tracks/artists/albums
  queue    — Add track to queue
  devices  — List available devices
  playlist — List or play playlists

Requires SPOTIPY_CLIENT_ID/SECRET in config/api_keys.json or env vars.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "api_keys.json"

_spotify_client = None


def _get_spotify():
    global _spotify_client
    if _spotify_client is not None:
        return _spotify_client

    try:
        import spotipy
        from spotipy.oauth2 import SpotifyOAuth
    except ImportError:
        return None

    client_id = ""
    client_secret = ""
    redirect_uri = "http://localhost:8888/callback"

    try:
        cfg = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
        spotify_cfg = cfg.get("spotify", {})
        client_id = spotify_cfg.get("client_id", "") or cfg.get("spotify_client_id", "")
        client_secret = spotify_cfg.get("client_secret", "") or cfg.get("spotify_client_secret", "")
        redirect_uri = spotify_cfg.get("redirect_uri", redirect_uri)
    except Exception:
        pass

    if not client_id:
        client_id = os.environ.get("SPOTIPY_CLIENT_ID", "")
    if not client_secret:
        client_secret = os.environ.get("SPOTIPY_CLIENT_SECRET", "")

    if not client_id or not client_secret:
        return None

    os.environ["SPOTIPY_CLIENT_ID"] = client_id
    os.environ["SPOTIPY_CLIENT_SECRET"] = client_secret
    os.environ["SPOTIPY_REDIRECT_URI"] = redirect_uri

    try:
        scope = (
            "user-read-playback-state user-modify-playback-state "
            "user-read-currently-playing user-library-read "
            "playlist-read-private playlist-read-collaborative"
        )
        cache_path = str(Path(__file__).resolve().parent.parent / "data" / ".spotify_cache")
        auth_manager = SpotifyOAuth(scope=scope, cache_path=cache_path)
        _spotify_client = spotipy.Spotify(auth_manager=auth_manager)
        return _spotify_client
    except Exception:
        return None


def _no_spotify():
    return (
        "Spotify no está configurado. Necesitás:\n"
        "1. Crear app en https://developer.spotify.com/dashboard\n"
        "2. Agregar client_id y client_secret en config/api_keys.json:\n"
        '   "spotify": {"client_id": "...", "client_secret": "..."}\n'
        "3. pip install spotipy"
    )


def _fmt_track(track_info: dict) -> str:
    if not track_info:
        return "Sin información de pista."
    name = track_info.get("name", "?")
    artists = ", ".join(a.get("name", "?") for a in track_info.get("artists", []))
    album = track_info.get("album", {}).get("name", "?")
    duration_ms = track_info.get("duration_ms", 0)
    mins, secs = divmod(duration_ms // 1000, 60)
    return f"{name} — {artists} ({album}) [{mins}:{secs:02d}]"


def spotify_control(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = str(params.get("action", "status")).strip().lower()

    if player:
        try:
            player.write_log(f"[Spotify] action={action}")
        except Exception:
            pass

    sp = _get_spotify()
    if sp is None and action != "status":
        return _no_spotify()

    if action == "status":
        return _status(sp)
    elif action == "play":
        return _play(sp, params)
    elif action == "pause":
        return _pause(sp)
    elif action == "next":
        return _skip(sp, "next")
    elif action == "previous":
        return _skip(sp, "previous")
    elif action == "volume":
        return _volume(sp, params)
    elif action == "search":
        return _search(sp, params)
    elif action == "queue":
        return _queue(sp, params)
    elif action == "devices":
        return _devices(sp)
    elif action == "playlist":
        return _playlist(sp, params)
    return "Actions: status, play, pause, next, previous, volume, search, queue, devices, playlist"


def _status(sp) -> str:
    if sp is None:
        return _no_spotify()
    try:
        current = sp.current_playback()
        if not current or not current.get("item"):
            return "No hay nada reproduciéndose actualmente."

        track = current["item"]
        is_playing = current.get("is_playing", False)
        progress_ms = current.get("progress_ms", 0)
        duration_ms = track.get("duration_ms", 0)

        state = "Reproduciendo" if is_playing else "Pausado"
        progress_s, _ = divmod(progress_ms // 1000, 60)
        progress_m, progress_sec = divmod(progress_ms // 1000, 60)
        dur_m, dur_sec = divmod(duration_ms // 1000, 60)

        device = current.get("device", {})
        device_name = device.get("name", "?")
        volume = device.get("volume_percent", "?")

        repeat = current.get("repeat_state", "off")
        shuffle = current.get("shuffle_state", False)

        lines = [
            f"Estado: {state}",
            f"Pista: {_fmt_track(track)}",
            f"Progreso: {progress_m}:{progress_sec:02d} / {dur_m}:{dur_sec:02d}",
            f"Dispositivo: {device_name} (volumen {volume}%)",
            f"Repetir: {repeat} | Shuffle: {'sí' if shuffle else 'no'}",
        ]

        if current.get("context"):
            ctx = current["context"]
            ctx_type = ctx.get("type", "?")
            ctx_name = ctx.get("name", "?")
            lines.append(f"Contexto: {ctx_type} — {ctx_name}")

        return "\n".join(lines)

    except Exception as e:
        return f"Error obteniendo estado: {e}"


def _play(sp, params: dict) -> str:
    if sp is None:
        return _no_spotify()
    try:
        query = str(params.get("query", "")).strip()
        if not query:
            sp.start_playback()
            return "Reproducción reanudada."

        results = sp.search(q=query, type="track", limit=5)
        tracks = results.get("tracks", {}).get("items", [])
        if not tracks:
            return f"No encontré resultados para '{query}'."

        track = tracks[0]
        uri = track["uri"]
        sp.start_playback(uris=[uri])
        return f"Reproduciendo: {_fmt_track(track)}"

    except Exception as e:
        return f"Error en play: {e}"


def _pause(sp) -> str:
    if sp is None:
        return _no_spotify()
    try:
        sp.pause_playback()
        return "Playback pausado."
    except Exception as e:
        return f"Error pausando: {e}"


def _skip(sp, direction: str) -> str:
    if sp is None:
        return _no_spotify()
    try:
        if direction == "next":
            sp.next_track()
            return "Saltando a siguiente pista."
        else:
            sp.previous_track()
            return "Volviendo a pista anterior."
    except Exception as e:
        return f"Error saltando pista: {e}"


def _volume(sp, params: dict) -> str:
    if sp is None:
        return _no_spotify()
    level = params.get("level", params.get("value", ""))
    if not level:
        try:
            dev = sp.current_playback()
            if dev and dev.get("device"):
                return f"Volumen actual: {dev['device'].get('volume_percent', '?')}%"
            return "No se pudo obtener el volumen."
        except Exception as e:
            return f"Error: {e}"

    try:
        vol = int(float(level))
        vol = max(0, min(100, vol))
        sp.volume(vol)
        return f"Volumen ajustado a {vol}%."
    except Exception as e:
        return f"Error ajustando volumen: {e}"


def _search(sp, params: dict) -> str:
    if sp is None:
        return _no_spotify()
    query = str(params.get("query", "")).strip()
    search_type = str(params.get("type", "track")).strip().lower()

    if not query:
        return "Falta el parámetro 'query' para buscar."

    type_map = {
        "track": "track", "cancion": "track", "canción": "track",
        "artist": "artist", "artista": "artist",
        "album": "album",
    }
    sp_type = type_map.get(search_type, "track")

    try:
        results = sp.search(q=query, type=sp_type, limit=5)

        if sp_type == "track":
            items = results.get("tracks", {}).get("items", [])
            if not items:
                return f"No encontré canciones para '{query}'."
            lines = [f"Canciones para '{query}' ({len(items)}):"]
            for i, t in enumerate(items, 1):
                lines.append(f"  {i}. {_fmt_track(t)}")
            return "\n".join(lines)

        elif sp_type == "artist":
            items = results.get("artists", {}).get("items", [])
            if not items:
                return f"No encontré artistas para '{query}'."
            lines = [f"Artistas para '{query}' ({len(items)}):"]
            for i, a in enumerate(items, 1):
                followers = a.get("followers", {}).get("total", "?")
                genres = ", ".join(a.get("genres", [])[:3]) or "sin géneros"
                lines.append(f"  {i}. {a['name']} — {followers} seguidores — {genres}")
            return "\n".join(lines)

        elif sp_type == "album":
            items = results.get("albums", {}).get("items", [])
            if not items:
                return f"No encontré álbumes para '{query}'."
            lines = [f"Álbumes para '{query}' ({len(items)}):"]
            for i, a in enumerate(items, 1):
                artists = ", ".join(x.get("name", "?") for x in a.get("artists", []))
                year = a.get("release_date", "?")[:4]
                tracks = a.get("total_tracks", "?")
                lines.append(f"  {i}. {a['name']} — {artists} ({year}) [{tracks} tracks]")
            return "\n".join(lines)

    except Exception as e:
        return f"Error en búsqueda: {e}"


def _queue(sp, params: dict) -> str:
    if sp is None:
        return _no_spotify()
    query = str(params.get("query", "")).strip()
    if not query:
        return "Falta el parámetro 'query' para agregar a la cola."

    try:
        results = sp.search(q=query, type="track", limit=1)
        tracks = results.get("tracks", {}).get("items", [])
        if not tracks:
            return f"No encontré '{query}' para agregar a la cola."

        track = tracks[0]
        sp.add_to_queue(track["uri"])
        return f"Agregado a la cola: {_fmt_track(track)}"
    except Exception as e:
        return f"Error agregando a cola: {e}"


def _devices(sp) -> str:
    if sp is None:
        return _no_spotify()
    try:
        devices = sp.devices().get("devices", [])
        if not devices:
            return "No hay dispositivos disponibles. Abrí Spotify en algún dispositivo."

        lines = [f"Dispositivos ({len(devices)}):"]
        for d in devices:
            active = " [ACTIVO]" if d.get("is_active") else ""
            vol = d.get("volume_percent", "?")
            lines.append(f"  - {d['name']} ({d.get('type', '?')}) vol={vol}%{active}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error listando dispositivos: {e}"


def _playlist(sp, params: dict) -> str:
    if sp is None:
        return _no_spotify()
    pl_action = str(params.get("action", "list")).strip().lower()
    playlist_id = str(params.get("playlist_id", "")).strip()

    if pl_action == "list" and not playlist_id:
        try:
            results = sp.current_user_playlists(limit=20)
            playlists = results.get("items", [])
            if not playlists:
                return "No tenés playlists."
            lines = [f"Playlists ({len(playlists)}):"]
            for p in playlists:
                tracks_count = p.get("tracks", {}).get("total", "?")
                lines.append(f"  - {p['name']} [{tracks_count} tracks] id={p['id']}")
            return "\n".join(lines)
        except Exception as e:
            return f"Error listando playlists: {e}"

    if pl_action == "play" or playlist_id:
        pid = playlist_id
        if not pid:
            name_q = str(params.get("query", params.get("name", ""))).strip()
            if not name_q:
                return "Falta 'playlist_id' o 'query' con el nombre de la playlist."
            try:
                results = sp.current_user_playlists(limit=50)
                for p in results.get("items", []):
                    if name_q.lower() in p.get("name", "").lower():
                        pid = p["id"]
                        break
                if not pid:
                    return f"No encontré playlist '{name_q}'."
            except Exception as e:
                return f"Error buscando playlist: {e}"

        try:
            sp.start_playback(context_uri=f"spotify:playlist:{pid}")
            return f"Reproduciendo playlist {pid}."
        except Exception as e:
            return f"Error reproduciendo playlist: {e}"

    return "Acciones playlist: list, play (con playlist_id o query)"
