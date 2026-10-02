#!/usr/bin/env python3
"""terminal_commands wrapper — ejecución de comandos de terminal para Linux Arch"""
import subprocess
from pathlib import Path

TOOL_NAME = "terminal_commands"

ACTIONS_AVAILABLE = ["exec", "info", "list_tools", "status"]

def tool_handler(params=None):
    """Handler para terminal_commands."""
    if params is None:
        params = {}

    action = params.get("action", "status")

    if action == "status":
        return f"terminal_commands: {', '.join(ACTIONS_AVAILABLE)}"
    elif action == "exec":
        command = params.get("command", "echo 'ERIS terminal_commands'")
        shell = params.get("shell", True)
        timeout = params.get("timeout", 30)
        try:
            result = subprocess.run(
                command, shell=shell,
                capture_output=True, text=True, timeout=timeout
            )
            output = result.stdout.strip() if result.stdout else ""
            if result.stderr:
                output += "\nSTDERR: " + result.stderr.strip()[:200]
            return output if output else "Command executed (no output)"
        except subprocess.TimeoutExpired:
            return f"Error: Command timed out after {timeout}s"
        except Exception as e:
            return f"Error: {str(e)[:100]}"
    elif action == "info":
        return "terminal_commands: Ejecuta comandos de terminal de forma segura"
    elif action == "list_tools":
        return "Available system tools: network_manager, file_system, process_manager, system_monitor, desktop_notifications"
    else:
        return f"Error: Unknown action '{action}'. Available: {', '.join(ACTIONS_AVAILABLE)}"

def get_declarations():
    return {
        "terminal_commands": "Ejecución de comandos de terminal — exec, info, status",
    }

if __name__ == "__main__":
    import sys
    action = sys.argv[1] if len(sys.argv) > 1 else "status"
    print(tool_handler({"action": action}))
