# -*- coding: utf-8 -*-
"""
play_direct.py — Direct video playback: YouTube, URLs, local files.
Simplified wrapper around youtube_video with direct playback.
"""
import webbrowser
import os
from pathlib import Path


def play_direct(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    query = params.get("query", "").strip()
    url = params.get("url", "").strip()
    video_id = params.get("video_id", "").strip()
    action = params.get("action", "play").lower().strip()
    file_path = params.get("file_path", "").strip()

    target = query or url or video_id or file_path

    if not target:
        return "Error: Se requiere 'query', 'url', 'video_id', o 'file_path'."

    if action in ("play", "play_direct", "abrir"):
        if os.path.exists(target):
            os.startfile(target)
            return f"Abriendo archivo local: {target}"
        return _play_youtube(target, player)

    elif action == "url":
        if target.startswith("http"):
            webbrowser.open(target)
            return f"Abriendo URL: {target}"
        return "Error: La URL debe empezar con http/https."

    elif action == "file":
        if os.path.exists(target):
            os.startfile(target)
            return f"Abriendo archivo: {target}"
        return f"Error: '{target}' no existe."

    return f"Acción '{action}' no reconocida. Usa: play, url, file"


def _play_youtube(target: str, player=None) -> str:
    from actions.youtube_video import youtube_video
    return youtube_video({"action": "play_direct", "query": target}, player=player)
