
"""skill_system — Sistema de gestión de habilidades y skills.
Delaga a skill_marketplace, superpowers_skill, plugin_loader."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def tool_handler(parameters: dict = None, player=None) -> str:
    """Manejador unificado de skill_system: delega a skill_marketplace, superpowers_skill, plugin_loader."""
    if parameters is None:
        parameters = {}

    from actions.skill_marketplace import skill_marketplace
    from actions.superpowers_skill import superpowers_skill
    from actions.plugin_loader import plugin_loader

    action = parameters.get("action", "").lower()

    if action in ("list_skills", "get_skill", "install_skill", "remove_skill",
                  "update_skill", "skill_info", "marketplace", "browse"):
        return skill_marketplace(parameters, player)
    elif action in ("get_superpower", "enable_superpower", "disable_superpower",
                    "list_superpowers", "superpower_info", "use"):
        return superpowers_skill(parameters, player)
    elif action in ("load_plugin", "unload_plugin", "reload_plugin", "list_plugins",
                    "scan", "plugin_info"):
        return plugin_loader(parameters, player)
    else:
        return skill_marketplace(parameters, player)


def info() -> dict:
    return {
        "name": "skill_system",
        "description": "Sistema unificado de gestión de habilidades y skills. Integra skill_marketplace, superpowers_skill y plugin_loader.",
        "actions": [
            "list_skills", "get_skill", "install_skill", "remove_skill",
            "update_skill", "skill_info", "marketplace", "browse",
            "get_superpower", "enable_superpower", "disable_superpower",
            "list_superpowers", "superpower_info", "use",
            "load_plugin", "unload_plugin", "reload_plugin", "list_plugins", "scan", "plugin_info",
        ],
        "version": "1.0.0",
        "module": "tools.skill_system",
    }


def get_actions() -> list:
    return info()["actions"]


if __name__ == "__main__":
    import json
    print(json.dumps(info(), indent=2, ensure_ascii=False))
