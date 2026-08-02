def save_memory(parameters: dict = None, player=None) -> str:
    if parameters is None:
        parameters = {}
    key = parameters.get("key", "").strip()
    value = parameters.get("value", "").strip()
    if not key:
        return "Error: Debes especificar 'key' y 'value' para guardar en memoria."
    try:
        from memory.memory_manager import remember
        category = parameters.get("category", "notes").strip()
        remember(category, key, value)
        return "Recordado: {} / {} = {}".format(category, key, str(value)[:100])
    except Exception as e:
        return "Error guardando memoria: {}".format(str(e)[:80])
