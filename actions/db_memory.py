def db_memory(parameters: dict = None, player=None) -> str:
    if parameters is None:
        parameters = {}
    action = parameters.get("action", "store").strip().lower()
    key = parameters.get("key", "").strip()
    value = parameters.get("value", "").strip()

    try:
        from memory.memory_manager import load_memory, save_memory as mgr_save, remember, forget
        from memory.memory_manager import format_memory_for_prompt

        if action == "store":
            if not key:
                return "Error: Debes especificar 'key' para guardar."
            category = parameters.get("category", "notes").strip()
            remember(category, key, value)
            return "Memoria guardada: {} / {} = {}".format(category, key, str(value)[:100])

        elif action == "get":
            memory = load_memory()
            for cat, keys in memory.items():
                if not isinstance(keys, dict):
                    continue
                if key in keys:
                    val = keys[key]
                    if isinstance(val, dict) and "value" in val:
                        val = val["value"]
                    return "{} ({}): {}".format(key, cat, str(val)[:200])
            return "No encontre '{}' en mi memoria.".format(key)

        elif action == "search":
            query = key.lower()
            memory = load_memory()
            results = []
            for cat, keys in memory.items():
                if not isinstance(keys, dict):
                    continue
                for k, v in keys.items():
                    val_str = str(v.get("value", v)) if isinstance(v, dict) else str(v)
                    if query in k.lower() or query in val_str.lower():
                        results.append("  {} / {}: {}".format(cat, k, val_str[:120]))
            if not results:
                return "No encontre nada sobre '{}' en mi memoria.".format(query)
            return "Resultados sobre '{}' ({}):\n".format(query, len(results)) + "\n".join(results[:10])

        elif action == "list":
            memory = load_memory()
            lines = []
            for cat, keys in memory.items():
                if not isinstance(keys, dict):
                    continue
                for k in keys.keys():
                    lines.append("  - {} / {}".format(cat, k))
            if not lines:
                return "No tengo recuerdos guardados aun."
            return "Mis recuerdos ({}):\n".format(len(lines)) + "\n".join(lines)

        elif action == "delete":
            memory = load_memory()
            found = False
            for cat in list(memory.keys()):
                if isinstance(memory[cat], dict) and key in memory[cat]:
                    del memory[cat][key]
                    found = True
            if found:
                from memory.memory_manager import save_memory as mgr_save2
                mgr_save2(memory)
                return "Eliminado '{}' de mi memoria.".format(key)
            return "No encontre '{}' en mi memoria.".format(key)

        return "Acciones: store (guardar), get (leer), search (buscar), list (listar), delete (eliminar)."

    except Exception as e:
        return "Error en memoria: {}".format(str(e)[:80])
