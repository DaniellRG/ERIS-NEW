"""
agents/media_agent.py — ERIS Media Specialized Agent.
Handles Spotify, YouTube, image generation, TikTok analysis.
"""
from __future__ import annotations

import time
from typing import Optional

def handle_media(text: str, player=None, **kwargs) -> str:
    """Handle media-related requests."""
    from core.tracer import get_tracer
    tracer = get_tracer()
    t0 = time.perf_counter()

    text_lower = text.lower()

    try:
        # Spotify
        if "spotify" in text_lower:
            from actions.spotify_control import spotify_control
            if "reproducir" in text_lower or "play" in text_lower:
                query = text_lower.replace("spotify", "").replace("reproducir", "").replace("play", "").strip()
                result = spotify_control(parameters={"action": "play", "query": query}, player=player)
            elif "pausar" in text_lower or "pause" in text_lower:
                result = spotify_control(parameters={"action": "pause"}, player=player)
            elif "siguiente" in text_lower or "next" in text_lower:
                result = spotify_control(parameters={"action": "next"}, player=player)
            elif "anterior" in text_lower or "previous" in text_lower:
                result = spotify_control(parameters={"action": "previous"}, player=player)
            elif "volumen" in text_lower:
                vol = text_lower.replace("spotify", "").replace("volumen", "").strip()
                result = spotify_control(parameters={"action": "volume", "value": vol}, player=player)
            else:
                result = spotify_control(parameters={"action": "status"}, player=player)

        # YouTube
        elif "youtube" in text_lower or "video" in text_lower:
            from actions.youtube_video import youtube_video
            query = text_lower.replace("youtube", "").replace("video", "").strip()
            result = youtube_video(parameters={"action": "search", "query": query}, player=player)

        # Image generation
        elif any(kw in text_lower for kw in ["generar imagen", "generate image", "crear imagen", "crea una imagen"]):
            try:
                from actions.image_generation import image_generation
                prompt = text_lower.replace("generar imagen", "").replace("generate image", "").replace("crear imagen", "").replace("crea una imagen", "").strip()
                result = image_generation(parameters={"action": "generate", "prompt": prompt}, player=player)
            except Exception:
                result = "La generaci\u00f3n de im\u00e1genes no est\u00e1 disponible en este momento."

        elif "tiktok" in text_lower:
            try:
                from actions.tiktok_analyzer import tiktok_analyzer
                result = tiktok_analyzer(parameters={"action": "analyze"}, player=player)
            except Exception:
                result = "El an\u00e1lisis de TikTok no est\u00e1 disponible en este momento."

        else:
            result = (
                "Puedo ayudarte con media:\n"
                "- 'Spotify reproduce [cancion]' → Buscar y reproducir musica\n"
                "- 'Spotify pausa/siguiente/anterior' → Controles de reproduccion\n"
                "- 'YouTube [busqueda]' → Buscar videos\n"
                "- 'Genera una imagen de [descripcion]' → Crear imagen con IA\n"
                "- 'TikTok' → Analizar tendencias de TikTok"
            )

        elapsed = time.perf_counter() - t0
        tracer.trace_handoff("media_agent", text, result, elapsed)
        return result

    except Exception as e:
        elapsed = time.perf_counter() - t0
        tracer.trace_handoff("media_agent", text, "", elapsed, success=False, error=str(e))
        return f"Error en MediaAgent: {e}"
