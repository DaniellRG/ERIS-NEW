import subprocess
import os
from pathlib import Path

def app_installer(parameters: dict, player=None) -> str:
    """Instala, desinstala, o ejecuta aplicaciones en Windows via winget."""
    action = parameters.get("action", "")
    app_name = parameters.get("app_name", "")
    app_path = parameters.get("app_path", "")

    if not action:
        return "Error: Especifica 'action'. Opciones: install, uninstall, list, run."

    try:
        if action == "install":
            if not app_name:
                return "Error: Especifica 'app_name' a instalar."
            result = subprocess.run(
                ["winget", "install", "--accept-source-agreements", "--accept-package-agreements", app_name],
                capture_output=True, text=True, timeout=120, shell=True
            )
            if result.returncode == 0:
                return f"Instalando '{app_name}' via winget. Revisa la ventana de instalacion."
            else:
                # Fallback: buscar en PATH o abrir Microsoft Store
                return f"Winget no pudo instalar '{app_name}'. Error: {result.stderr[:200]}. Intenta manualmente desde Microsoft Store."

        elif action == "uninstall":
            if not app_name:
                return "Error: Especifica 'app_name' a desinstalar."
            result = subprocess.run(
                ["winget", "uninstall", app_name],
                capture_output=True, text=True, timeout=60, shell=True
            )
            if result.returncode == 0:
                return f"Desinstalando '{app_name}'."
            return f"No se pudo desinstalar '{app_name}'. Error: {result.stderr[:200]}"

        elif action == "list":
            result = subprocess.run(
                ["winget", "list"],
                capture_output=True, text=True, timeout=30, shell=True
            )
            apps = result.stdout.strip().split('\n')
            installed = [a.strip() for a in apps if a.strip() and not a.startswith("Name") and not a.startswith("---")][:30]
            return f"Aplicaciones instaladas:\n" + "\n".join(installed[:20])

        elif action == "run":
            if not app_name:
                return "Error: Especifica 'app_name' o 'app_path'."
            if app_path:
                os.startfile(app_path)
                return f"Ejecutando: {app_path}"
            try:
                subprocess.Popen(app_name, shell=True)
                return f"Ejecutando '{app_name}'."
            except Exception:
                return f"No se encontro '{app_name}'. Usa el nombre exacto o app_path."

        else:
            return f"Accion '{action}' no reconocida. Usa: install, uninstall, list, run."

    except Exception as e:
        return f"Error en app_installer: {str(e)}"
