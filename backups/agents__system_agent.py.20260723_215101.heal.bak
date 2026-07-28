"""
agents/system_agent.py — ERIS System Specialized Agent.
Handles computer control, desktop automation, system monitoring, Windows settings.
"""
from __future__ import annotations

import time
from typing import Optional

def handle_system(text: str, player=None, **kwargs) -> str:
    """Handle system-related requests."""
    from core.tracer import get_tracer
    tracer = get_tracer()
    t0 = time.perf_counter()

    text_lower = text.lower()

    try:
        # System monitoring
        if any(kw in text_lower for kw in ["cpu", "ram", "memoria", "disco", "disk", "bateria", "battery", "temperatura", "monitor de sistema"]):
            from actions.system_monitor import system_monitor
            result = system_monitor(parameters={"action": "status"}, player=player)

        # Desktop control
        elif any(kw in text_lower for kw in ["abrir app", "cerrar app", "minimizar", "maximizar", "ventana", "escritorio", "desktop"]):
            from actions.desktop import desktop_control
            if "abrir" in text_lower or "open" in text_lower:
                app = text_lower.replace("abrir", "").replace("open", "").replace("app", "").strip()
                result = desktop_control(parameters={"action": "open_app", "app_name": app}, player=player)
            elif "cerrar" in text_lower or "close" in text_lower:
                app = text_lower.replace("cerrar", "").replace("close", "").replace("app", "").strip()
                result = desktop_control(parameters={"action": "close_app", "app_name": app}, player=player)
            elif "minimizar" in text_lower:
                result = desktop_control(parameters={"action": "minimize_all"}, player=player)
            else:
                result = desktop_control(parameters={"action": "status"}, player=player)

        # Computer control
        elif any(kw in text_lower for kw in ["teclado", "mouse", "click", "escribir", "typing", "volumen", "brillo", "controlar computadora"]):
            from actions.computer_control import computer_control
            if "volumen" in text_lower:
                if "subir" in text_lower or "aumentar" in text_lower:
                    result = computer_control(parameters={"action": "volume_up"}, player=player)
                elif "bajar" in text_lower or "reducir" in text_lower:
                    result = computer_control(parameters={"action": "volume_down"}, player=player)
                elif "mute" in text_lower or "silenciar" in text_lower:
                    result = computer_control(parameters={"action": "volume_mute"}, player=player)
                else:
                    result = computer_control(parameters={"action": "volume_get"}, player=player)
            elif "click" in text_lower:
                result = computer_control(parameters={"action": "click"}, player=player)
            elif "escribir" in text_lower or "typing" in text_lower:
                text_to_type = text_lower.replace("escribir", "").replace("typing", "").strip()
                result = computer_control(parameters={"action": "type", "text": text_to_type}, player=player)
            else:
                result = computer_control(parameters={"action": "status"}, player=player)

        # Windows settings
        elif any(kw in text_lower for kw in ["configuracion", "settings", "windows settings", "preferencias"]):
            from actions.windows_settings import windows_settings
            result = windows_settings(parameters={"action": "status"}, player=player)

        # Accessibility
        elif any(kw in text_lower for kw in ["accesibilidad", "accessibility", "barra de accesibilidad", "screen reader"]):
            from actions.accessibility import accessibility
            if "mostrar" in text_lower or "activa" in text_lower:
                result = accessibility(parameters={"action": "enable"}, player=player)
            elif "ocultar" in text_lower or "desactiva" in text_lower:
                result = accessibility(parameters={"action": "disable"}, player=player)
            else:
                result = accessibility(parameters={"action": "status"}, player=player)

        else:
            result = (
                "Puedo controlar tu sistema de varias formas:\n"
                "- 'Como esta el sistema?' → CPU, RAM, disco, bateria\n"
                "- 'Abri [app]' → Abrir aplicacion\n"
                "- 'Cerra [app]' → Cerrar aplicacion\n"
                "- 'Subi/baja volumen' → Control de volumen\n"
                "- 'Minimiza todo' → Mostrar escritorio\n"
                "- 'Configuracion' → Settings de Windows"
            )

        elapsed = time.perf_counter() - t0
        tracer.trace_handoff("system_agent", text, result, elapsed)
        return result

    except Exception as e:
        elapsed = time.perf_counter() - t0
        tracer.trace_handoff("system_agent", text, "", elapsed, success=False, error=str(e))
        return f"Error en SystemAgent: {e}"
