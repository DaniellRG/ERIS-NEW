"""
plugins/hello_world.py — Sample plugin for ERIS.
Demonstrates the plugin interface: name, version, description, execute().
"""
from core.plugin_manager import Plugin


class HelloWorldPlugin(Plugin):
    name = "hello_world"
    version = "1.0.0"
    description = "Sample plugin that says hello."

    def on_load(self):
        print("[HelloWorld] Plugin loaded!")

    def execute(self, action: str, params: dict) -> str:
        if action == "greet":
            name = params.get("name", "ERIS user")
            return f"¡Hola, {name}! Este es el plugin hello_world funcionando."
        elif action == "ping":
            return "pong"
        return f"Hello from plugin! (action={action})"
