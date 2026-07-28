"""
youtube_video.py — Reproduccion de videos de YouTube con multiples modos.
Busca, reproduce, listas, obtiene info, y controla la reproduccion.
"""
import webbrowser
import urllib.parse
import urllib.request
import json
import re
import time
from pathlib import Path

_HISTORY_FILE = Path(__file__).resolve().parent.parent / "data" / "youtube_history.json"
_PLAYLIST_FILE = Path(__file__).resolve().parent.parent / "data" / "youtube_playlist.json"


def youtube_video(parameters: dict, response=None, player=None) -> str:
    params = parameters or {}
    action = params.get("action", "play").lower()
    query = params.get("query", "").strip()
    url = params.get("url", "").strip()
    video_id = params.get("video_id", "").strip()
    count = int(params.get("count") or 5)

    if action == "play":
        return _play_search(query, player)
    elif action == "play_direct":
        return _play_direct(query or url or video_id, player)
    elif action == "play_url":
        return _play_url(url, player)
    elif action == "play_id":
        return _play_id(video_id, player)
    elif action == "search":
        return _search_videos(query, count)
    elif action == "search_and_play":
        return _search_and_play(query, player)
    elif action == "playlist":
        return _play_playlist(query, count, player)
    elif action == "add_to_playlist":
        return _add_to_playlist(query or url or video_id)
    elif action == "show_playlist":
        return _show_playlist()
    elif action == "clear_playlist":
        return _clear_playlist()
    elif action == "get_info":
        return _get_video_info(url or video_id)
    elif action == "batch_info":
        return _batch_info(query, count)
    elif action == "trending":
        return _get_trending()
    elif action == "recent":
        return _get_history()
    elif action == "open":
        return _open_youtube()
    elif action == "pause":
        return _pause_video()
    elif action == "resume":
        return _resume_video()
    elif action == "fullscreen":
        return _toggle_fullscreen()
    elif action == "mute":
        return _toggle_mute()
    elif action == "next_video":
        return _next_video()
    elif action == "prev_video":
        return _prev_video()
    elif action == "stop":
        return _stop_video()
    return (
        "Acciones: play (buscar y reproducir), play_url (URL directa), "
        "play_id (por ID), search (buscar), search_and_play (buscar y reproducir el mejor), "
        "playlist (reproducir lista), add_to_playlist (agregar a mi lista), "
        "show_playlist (ver mi lista), clear_playlist (limpiar lista), "
        "get_info (info del video), batch_info (info de varios), "
        "trending (tendencias), recent (historial), open (abrir YouTube), "
        "pause (pausar), resume (reanudar), fullscreen (pantalla completa), "
        "mute (silenciar), next_video (siguiente), prev_video (anterior), stop (detener)"
    )


def _play_search(query: str, player=None) -> str:
    if not query:
        return "Error: especifica que buscar en YouTube"
    encoded = urllib.parse.quote(query)
    url = "https://www.youtube.com/results?search_query={}&sp=EgIQAQ%3D%3D".format(encoded)
    webbrowser.open(url)
    _log_history("play_search", query, url)
    _track_open_tab("YouTube: " + query[:40], url)
    if player:
        player.write_log("YouTube: buscando '{}'".format(query[:40]))
    return "Abriendo YouTube: '{}'".format(query[:60])


def _play_direct(target: str, player=None) -> str:
    if not target:
        return "Error: especifica URL, video_id, o nombre del video"
    target = target.strip()

    video_id = _extract_video_id(target)
    if video_id:
        play_url = "https://www.youtube.com/watch?v={}".format(video_id)
        webbrowser.open(play_url)
        _log_history("play_direct", target, play_url)
        _track_open_tab("YouTube: " + target[:40], play_url)
        if player:
            player.write_log("YouTube: reproduciendo directamente")
        return "Reproduciendo directamente: {}".format(play_url[:80])

    if target.startswith("http"):
        webbrowser.open(target)
        _log_history("play_direct", target, target)
        _track_open_tab("YouTube: " + target[:40], target)
        if player:
            player.write_log("YouTube: reproduciendo URL directa")
        return "Reproduciendo URL directa: {}".format(target[:80])

    try:
        encoded = urllib.parse.quote(target)
        search_url = "https://www.youtube.com/results?search_query={}".format(encoded)
        req = urllib.request.Request(search_url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        videos = _parse_search_results(html)
        if videos:
            best = videos[0]
            play_url = "https://www.youtube.com/watch?v={}".format(best["id"])
            webbrowser.open(play_url)
            _log_history("play_direct", target, play_url)
            _track_open_tab("YouTube: " + target[:40], play_url)
            if player:
                player.write_log("YouTube: '{}' -> {}".format(target[:30], best["title"][:30]))
            return "Reproduciendo: '{}' de {} ({})".format(
                best["title"][:40], best.get("channel", "?")[:20], best.get("views", "?"))
    except Exception:
        pass

    webbrowser.open("https://www.youtube.com/results?search_query={}".format(urllib.parse.quote(target)))
    return "Buscando '{}' en YouTube".format(target[:50])


def _play_url(url: str, player=None) -> str:
    if not url:
        return "Error: especifica la URL del video"
    video_id = _extract_video_id(url)
    if video_id:
        play_url = "https://www.youtube.com/watch?v={}".format(video_id)
    elif url.startswith("http"):
        play_url = url
    else:
        return "URL invalida: '{}'".format(url[:50])
    webbrowser.open(play_url)
    _log_history("play_url", play_url, play_url)
    _track_open_tab("YouTube Video", play_url)
    if player:
        player.write_log("YouTube: reproduciendo video")
    return "Reproduciendo: {}".format(play_url[:80])


def _play_id(video_id: str, player=None) -> str:
    if not video_id:
        return "Error: especifica el video_id"
    url = "https://www.youtube.com/watch?v={}".format(video_id)
    webbrowser.open(url)
    _log_history("play_id", video_id, url)
    _track_open_tab("YouTube Video", url)
    if player:
        player.write_log("YouTube: video {}".format(video_id))
    return "Reproduciendo video: {}".format(video_id)


def _search_videos(query: str, count: int = 5) -> str:
    if not query:
        return "Error: especifica que buscar"
    try:
        encoded = urllib.parse.quote(query)
        url = "https://www.youtube.com/results?search_query={}".format(encoded)
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        videos = _parse_search_results(html)
        if not videos:
            webbrowser.open("https://www.youtube.com/results?search_query={}".format(encoded))
            return "Abriendo busqueda en YouTube: '{}'".format(query[:50])
        lines = ["═══ YOUTUBE: '{}' ═══".format(query[:40]), ""]
        for i, v in enumerate(videos[:count], 1):
            lines.append("  {:2d}. {}".format(i, v["title"][:55]))
            lines.append("      {} vistas | {}".format(v.get("views", "?"), v.get("channel", "?")[:30]))
            lines.append("      ID: {}".format(v["id"]))
        lines.append("")
        lines.append("Para reproducir: play_id con el ID, o search_and_play")
        return "\n".join(lines)
    except Exception:
        webbrowser.open("https://www.youtube.com/results?search_query={}".format(encoded))
        return "Busqueda abierta en YouTube (error de red)"


def _search_and_play(query: str, player=None) -> str:
    if not query:
        return "Error: especifica que buscar"
    try:
        encoded = urllib.parse.quote(query)
        url = "https://www.youtube.com/results?search_query={}".format(encoded)
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        videos = _parse_search_results(html)
        if videos:
            best = videos[0]
            play_url = "https://www.youtube.com/watch?v={}".format(best["id"])
            webbrowser.open(play_url)
            _log_history("search_and_play", query, play_url)
            _track_open_tab("YouTube: " + query[:40], play_url)
            if player:
                player.write_log("YouTube: '{}' -> {}".format(query[:30], best["title"][:30]))
            lines = ["═══ REPRODUCIENDO ═══", ""]
            lines.append("  Titulo: {}".format(best["title"][:55]))
            lines.append("  Canal: {}".format(best.get("channel", "?")[:30]))
            lines.append("  Vistas: {}".format(best.get("views", "?")))
            lines.append("  Duracion: {}".format(best.get("duration", "?")))
            lines.append("  URL: {}".format(play_url))
            if len(videos) > 1:
                lines.append("")
                lines.append("  Otros resultados:")
                for v in videos[1:4]:
                    lines.append("    - {} (ID: {})".format(v["title"][:45], v["id"]))
            return "\n".join(lines)
        webbrowser.open("https://www.youtube.com/results?search_query={}".format(encoded))
        return "Busqueda abierta en YouTube: '{}'".format(query[:50])
    except Exception:
        webbrowser.open("https://www.youtube.com/results?search_query={}".format(urllib.parse.quote(query)))
        return "Busqueda abierta en YouTube"


def _play_playlist(query: str, count: int = 5, player=None) -> str:
    if not query:
        return "Error: especifica que buscar para la playlist"
    try:
        encoded = urllib.parse.quote(query)
        url = "https://www.youtube.com/results?search_query={}&sp=EgIQAw%3D%3D".format(encoded)
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        videos = _parse_search_results(html)
        if not videos:
            return "No encontre playlists para '{}'".format(query[:30])

        playlist = []
        lines = ["═══ PLAYLIST: '{}' ═══".format(query[:40]), ""]
        for i, v in enumerate(videos[:count], 1):
            playlist.append(v)
            lines.append("  {:2d}. {} ({})".format(i, v["title"][:50], v.get("duration", "?")))

        _save_playlist(playlist)
        if playlist:
            play_url = "https://www.youtube.com/watch?v={}".format(playlist[0]["id"])
            webbrowser.open(play_url)
            _track_open_tab("Playlist: " + query[:40], play_url)
            lines.append("")
            lines.append("Reproduciendo primero de {} videos.".format(len(playlist)))
            lines.append("Usa next_video para el siguiente.")
        return "\n".join(lines)
    except Exception:
        return "Error creando playlist"


def _add_to_playlist(target: str) -> str:
    playlist = _load_playlist()
    video_id = _extract_video_id(target) or target
    if len(video_id) == 11:
        playlist.append({"id": video_id, "title": target[:60], "added": __import__("datetime").datetime.now().isoformat()})
        _save_playlist(playlist)
        return "Agregado a playlist: {}".format(video_id)
    return "ID invalido: '{}'".format(target[:20])


def _show_playlist() -> str:
    playlist = _load_playlist()
    if not playlist:
        return "Playlist vacia."
    lines = ["═══ MI PLAYLIST ({} videos) ═══".format(len(playlist)), ""]
    for i, v in enumerate(playlist, 1):
        lines.append("  {:2d}. {} [{}]".format(i, v.get("title", "?")[:45], v.get("id", "?")))
    return "\n".join(lines)


def _clear_playlist() -> str:
    _save_playlist([])
    return "Playlist limpiada."


def _get_video_info(url_or_id: str) -> str:
    if not url_or_id:
        return "Error: especifica URL o video_id"
    video_id = _extract_video_id(url_or_id) or url_or_id
    if len(video_id) != 11:
        return "ID de video invalido: '{}'".format(video_id[:20])
    try:
        page_url = "https://www.youtube.com/watch?v={}".format(video_id)
        req = urllib.request.Request(page_url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "es-ES,es;q=0.9",
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        info = _parse_video_page(html, video_id)
        if info:
            lines = ["═══ INFO DEL VIDEO ═══", ""]
            lines.append("  Titulo:    {}".format(info.get("title", "?")))
            lines.append("  Canal:     {}".format(info.get("channel", "?")))
            lines.append("  Vistas:    {}".format(info.get("views", "?")))
            lines.append("  Likes:     {}".format(info.get("likes", "?")))
            lines.append("  Fecha:     {}".format(info.get("date", "?")))
            lines.append("  Duracion:  {}".format(info.get("duration", "?")))
            desc = info.get("description", "")
            if desc:
                lines.append("")
                lines.append("  Descripcion:")
                for line in desc[:500].split("\n")[:8]:
                    lines.append("    {}".format(line.strip()))
            return "\n".join(lines)
        return "No se pudo obtener info del video '{}'".format(video_id)
    except Exception as e:
        return "Error obteniendo info: {}".format(str(e)[:60])


def _batch_info(query: str, count: int = 3) -> str:
    if not query:
        return "Error: especifica que buscar"
    try:
        encoded = urllib.parse.quote(query)
        url = "https://www.youtube.com/results?search_query={}".format(encoded)
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        videos = _parse_search_results(html)
        if not videos:
            return "No encontre videos para '{}'".format(query[:30])

        lines = ["═══ INFO DETALLADA: '{}' ═══".format(query[:40]), ""]
        for v in videos[:count]:
            info_url = "https://www.youtube.com/watch?v={}".format(v["id"])
            try:
                req2 = urllib.request.Request(info_url, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept-Language": "es-ES,es;q=0.9",
                })
                with urllib.request.urlopen(req2, timeout=8) as resp2:
                    html2 = resp2.read().decode("utf-8", errors="ignore")
                info = _parse_video_page(html2, v["id"])
                lines.append("  ▸ {}".format(info.get("title", v["title"])[:55]))
                lines.append("    Canal: {} | Vistas: {} | Duracion: {}".format(
                    info.get("channel", v.get("channel", "?"))[:25],
                    info.get("views", v.get("views", "?")),
                    info.get("duration", v.get("duration", "?"))))
                desc = info.get("description", "")
                if desc:
                    lines.append("    Desc: {}".format(desc[:120]))
                lines.append("")
            except Exception:
                lines.append("  ▸ {} (info no disponible)".format(v["title"][:55]))
                lines.append("")
        return "\n".join(lines)
    except Exception as e:
        return "Error: {}".format(str(e)[:60])


def _pause_video() -> str:
    pyautogui = __import__("pyautogui")
    pyautogui.press("k")
    return "Video pausado."


def _resume_video() -> str:
    pyautogui = __import__("pyautogui")
    pyautogui.press("k")
    return "Video reanudado."


def _toggle_fullscreen() -> str:
    pyautogui = __import__("pyautogui")
    pyautogui.press("f")
    return "Pantalla completa alternada."


def _toggle_mute() -> str:
    pyautogui = __import__("pyautogui")
    pyautogui.press("m")
    return "Silencio alternado."


def _next_video() -> str:
    pyautogui = __import__("pyautogui")
    pyautogui.hotkey("shift", "n")
    return "Siguiente video."


def _prev_video() -> str:
    pyautogui = __import__("pyautogui")
    pyautogui.hotkey("shift", "p")
    return "Video anterior."


def _stop_video() -> str:
    pyautogui = __import__("pyautogui")
    pyautogui.press("k")
    pyautogui.press("k")
    return "Video detenido."


def _get_trending() -> str:
    try:
        url = "https://www.youtube.com/feed/trending"
        webbrowser.open(url)
        _track_open_tab("YouTube Trending", url)
        return "Abriendo tendencias de YouTube"
    except Exception as e:
        return "Error: {}".format(str(e)[:50])


def _open_youtube() -> str:
    webbrowser.open("https://www.youtube.com")
    _track_open_tab("YouTube", "https://www.youtube.com")
    return "YouTube abierto"


def _extract_video_id(url: str) -> str:
    patterns = [
        r'(?:v=|/v/|youtu\.be/)([a-zA-Z0-9_-]{11})',
        r'(?:embed/)([a-zA-Z0-9_-]{11})',
        r'^([a-zA-Z0-9_-]{11})$',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return ""


def _parse_search_results(html: str) -> list:
    videos = []
    try:
        json_match = re.search(r'var ytInitialData\s*=\s*(\{.*?\});\s*</script>', html, re.DOTALL)
        if not json_match:
            return videos
        data = json.loads(json_match.group(1))
        contents = data.get("contents", {}).get("twoColumnSearchResultsRenderer", {})
        primary = contents.get("primaryContents", {}).get("sectionListRenderer", {}).get("contents", [])
        for section in primary:
            items = section.get("itemSectionRenderer", {}).get("contents", [])
            for item in items:
                vid = item.get("videoRenderer", {})
                if not vid:
                    continue
                video_id = vid.get("videoId", "")
                title = vid.get("title", {}).get("runs", [{}])[0].get("text", "")
                channel = vid.get("ownerText", {}).get("runs", [{}])[0].get("text", "")
                views_text = vid.get("viewCountText", {}).get("simpleText", "")
                duration = vid.get("lengthText", {}).get("simpleText", "")
                if video_id and title:
                    videos.append({
                        "id": video_id,
                        "title": title,
                        "channel": channel,
                        "views": views_text,
                        "duration": duration,
                    })
    except Exception:
        pass
    return videos


def _parse_video_page(html: str, video_id: str) -> dict:
    info = {}
    try:
        json_match = re.search(r'var ytInitialPlayerResponse\s*=\s*(\{.*?\});\s*</script>', html, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(1))
            vd = data.get("videoDetails", {})
            info["title"] = vd.get("title", "")
            info["channel"] = vd.get("author", "")
            info["views"] = vd.get("viewCount", "")
            info["duration"] = "{}s".format(vd.get("lengthSeconds", ""))
            desc = vd.get("shortDescription", "")
            info["description"] = desc[:500]
        micro = re.search(r'"dateText":\s*\{"simpleText":\s*"([^"]+)"', html)
        if micro:
            info["date"] = micro.group(1)
        likes = re.search(r'"label":\s*"([\d,]+)\s*likes"', html)
        if likes:
            info["likes"] = likes.group(1)
    except Exception:
        pass
    return info


def _track_open_tab(title, url):
    try:
        tabs_file = Path(__file__).resolve().parent.parent / "data" / "open_tabs.json"
        tabs = []
        if tabs_file.exists():
            tabs = json.loads(tabs_file.read_text(encoding="utf-8"))
        tabs.append({
            "title": title[:80],
            "url": url[:200],
            "action": "open",
            "time": __import__("datetime").datetime.now().isoformat(),
        })
        tabs_file.parent.mkdir(parents=True, exist_ok=True)
        tabs_file.write_text(json.dumps(tabs[-50:], ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass


def _log_history(action: str, target: str, url: str):
    history = _load_history()
    history.append({
        "action": action,
        "target": target[:80],
        "url": url,
        "time": __import__("datetime").datetime.now().isoformat(),
    })
    if len(history) > 100:
        history = history[-100:]
    _save_history(history)


def _load_history() -> list:
    if _HISTORY_FILE.exists():
        try:
            return json.loads(_HISTORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def _save_history(history: list):
    _HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    _HISTORY_FILE.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")


def _get_history() -> str:
    history = _load_history()
    if not history:
        return "Sin historial de YouTube"
    lines = ["═══ HISTORIAL YOUTUBE ═══", ""]
    for h in history[-10:]:
        lines.append("  [{}] {} -> {}".format(
            h.get("time", "?")[:16],
            h.get("action", "?"),
            h.get("target", "?")[:50]))
    return "\n".join(lines)


def _load_playlist() -> list:
    if _PLAYLIST_FILE.exists():
        try:
            return json.loads(_PLAYLIST_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def _save_playlist(playlist: list):
    _PLAYLIST_FILE.parent.mkdir(parents=True, exist_ok=True)
    _PLAYLIST_FILE.write_text(json.dumps(playlist, indent=2, ensure_ascii=False), encoding="utf-8")
