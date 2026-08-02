def conversation_search(parameters: dict = None, player=None) -> str:
    if parameters is None:
        parameters = {}
    query = parameters.get("query", "").strip()
    limit = min(int(parameters.get("limit", 10)), 50)

    try:
        from actions.eris_db import convo_search, convo_recent
    except Exception:
        return "Error: Base de datos de conversaciones no disponible."

    try:
        if query:
            results = convo_search(query, limit)
        else:
            results = convo_recent(limit)
    except Exception as e:
        return "Error buscando conversaciones: {}".format(str(e)[:80])

    if not results:
        if query:
            return "No encontre conversaciones sobre '{}'.".format(query)
        return "No hay historial de conversaciones."

    lines = []
    if query:
        lines.append("Conversaciones sobre '{}' ({}):".format(query, len(results)))
    else:
        lines.append("Conversaciones recientes ({}):".format(len(results)))

    for r in results[-limit:]:
        msg = r.get("content", r.get("message", ""))[:150]
        time = str(r.get("created_at", r.get("time", "")))[:16]
        role = r.get("role", "?")
        sid = str(r.get("session_id", ""))[:8]
        lines.append("  [{}] ({}): {}: {}".format(time, sid, role, msg))
    return "\n".join(lines)
