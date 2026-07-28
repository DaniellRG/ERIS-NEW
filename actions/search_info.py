# -*- coding: utf-8 -*-
"""
search_info.py — General-purpose search: web, news, images, videos, definitions.
Wraps web_search with a simpler interface.
"""
from actions.web_search import web_search


def search_info(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    query = params.get("query") or params.get("text") or params.get("search") or ""
    action = params.get("action", "search").lower()
    num = int(params.get("num_results") or params.get("count") or 5)

    if not query:
        return "Error: Se requiere 'query' para buscar."

    action_map = {
        "search": "search", "buscar": "search",
        "news": "news", "noticias": "news",
        "images": "images", "imagenes": "images",
        "videos": "videos",
        "definition": "definition", "definicion": "definition",
        "local": "local",
    }
    web_action = action_map.get(action, "search")

    return web_search({
        "query": query,
        "action": web_action,
        "num_results": num,
    }, player=player)
