
"""memory_system — Sistema unificado de memoria persistente.
Delaga a db_memory, memory_consolidation, memory_nudge, memory_rag, save_memory."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def tool_handler(parameters: dict = None, player=None) -> str:
    """Manejador unificado de memory_system: delega a db_memory, memory_consolidation, memory_nudge, memory_rag, save_memory."""
    if parameters is None:
        parameters = {}

    from actions.db_memory import db_memory
    from actions.memory_consolidation import memory_consolidate as _memory_consolidation
    from actions.memory_nudge import memory_nudge
    from actions.memory_rag import memory_rag
    from actions.save_memory import save_memory

    action = parameters.get("action", "").lower()

    if action in ("store", "get", "search", "list", "delete", "stats",
                  "db_memory", "db_get", "db_store", "db_search", "db_list", "db_delete"):
        from actions.db_memory import db_memory as _tool
        return _tool(parameters, player)
    elif action in ("consolidate", "merge", "cleanup", "deduplicate", "compress",
                    "status", "consolidation_status", "last_consolidation"):
        from actions.memory_consolidation import memory_consolidate as _tool
        return _tool(parameters, player)
    elif action in ("nudge", "list_nudges", "add_nudge", "remove_nudge", "test_nudge",
                    "nudge_list", "nudge_create", "nudge_remove", "nudge_trigger"):
        return memory_nudge(parameters, player)
    elif action in ("semantic_search", "rag_search", "similarity", "find_related",
                    "context_search", "semantic", "search_rag"):
        from actions.memory_rag import memory_rag as _tool
        return _tool(parameters, player)
    elif action in ("save", "load", "delete_simple", "list_simple", "keys"):
        return save_memory(parameters, player)
    else:
        return db_memory(parameters, player)


def info() -> dict:
    return {
        "name": "memory_system",
        "description": "Sistema unificado de memoria persistente. Integra db_memory, memory_consolidation, memory_nudge, memory_rag y save_memory.",
        "actions": [
            "store", "get", "search", "list", "delete", "stats",
            "db_memory", "db_get", "db_store", "db_search", "db_list", "db_delete",
            "consolidate", "merge", "cleanup", "deduplicate", "compress",
            "status", "consolidation_status", "last_consolidation",
            "nudge", "list_nudges", "add_nudge", "remove_nudge", "test_nudge",
            "nudge_list", "nudge_create", "nudge_remove", "nudge_trigger",
            "semantic_search", "rag_search", "similarity", "find_related",
            "context_search", "semantic", "search_rag",
            "save", "load", "delete_simple", "list_simple", "keys",
        ],
        "version": "1.0.0",
        "module": "tools.memory_system",
    }


def get_actions() -> list:
    return info()["actions"]


if __name__ == "__main__":
    import json
    print(json.dumps(info(), indent=2, ensure_ascii=False))
