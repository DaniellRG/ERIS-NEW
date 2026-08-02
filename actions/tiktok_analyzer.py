# -*- coding: utf-8 -*-
"""
tiktok_analyzer.py — Análisis de contenido TikTok.
Requiere credenciales de la API de TikTok (no configuradas en ERIS).
Acciones (todas honestas, requieren TikTokApi + credenciales):
  profile  — Datos de un perfil
  video    — Detalles de un video
  trending — Tendencias actuales
  search   — Búsqueda de contenido
"""
from __future__ import annotations


def tiktok_analyzer(parameters: dict = None, player=None) -> str:
    parameters = parameters or {}
    action = parameters.get("action", "").lower()

    if action in ("profile", "video", "trending", "search"):
        target = parameters.get("username") or parameters.get("url") or parameters.get("query") or ""
        return (f"TikTok '{action}' no disponible: requiere la API de TikTok con credenciales. "
                "Instalá 'TikTokApi' (pip install TikTokApi) y configurá credenciales/cookies en "
                "config/api_keys.json" + (f" para '{target}'" if target else "") + ".")

    return ("TikTok Analyzer: acciones = profile, video, trending, search. "
            "Requiere credenciales de la API de TikTok, no configuradas.")
