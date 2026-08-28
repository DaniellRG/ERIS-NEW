"""
actions/console_log.py — Console.log tool for ERIS.
Allows Eris to read, search, and manage the centralized error/performance log.
"""
from __future__ import annotations


def console_log(parameters: dict, player=None, **kwargs) -> str:
    """Console.log: read, search, stats, errors, clear the centralized log."""
    from core.console_log import read_log, search_log, get_errors, get_stats, clear_log, get_log_file_path

    action = parameters.get("action", "read")

    if action == "read":
        lines = parameters.get("lines", 50)
        level = parameters.get("level")
        category = parameters.get("category")
        return read_log(lines=lines, level=level, category=category)

    elif action == "search":
        query = parameters.get("query", "")
        if not query:
            return "Se requiere un parámetro 'query' para buscar."
        max_results = parameters.get("max_results", 20)
        return search_log(query, max_results)

    elif action == "errors":
        lines = parameters.get("lines", 30)
        return get_errors(lines)

    elif action == "stats":
        return get_stats()

    elif action == "clear":
        return clear_log()

    elif action == "path":
        return f"Console.log: {get_log_file_path()}"

    else:
        return (
            "Acciones disponibles:\n"
            "- read (lines, level, category) — Leer últimas entradas\n"
            "- search (query, max_results) — Buscar en el log\n"
            "- errors (lines) — Ver errores recientes\n"
            "- stats — Estadísticas de errores y tools\n"
            "- clear — Limpiar el log\n"
            "- path — Ver ruta del archivo"
        )
