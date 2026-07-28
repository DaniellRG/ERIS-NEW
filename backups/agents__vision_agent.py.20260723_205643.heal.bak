"""
agents/vision_agent.py — ERIS Vision Specialized Agent.
Handles all image and screen analysis tasks.
Delegated from main ERIS via agent handoff.
"""
from __future__ import annotations

import time
from typing import Optional

def handle_vision(text: str, player=None, **kwargs) -> str:
    """
    Handle vision-related requests.
    Routes to the appropriate vision tool based on intent.
    """
    from core.tracer import get_tracer
    tracer = get_tracer()
    t0 = time.perf_counter()

    text_lower = text.lower()

    try:
        # Vision Guardian control
        if any(kw in text_lower for kw in ["guardian", "vigila", "vigilar", "monitoreo", "monitorear"]):
            from actions.vision_guardian import vision_guardian
            if "activa" in text_lower or "enable" in text_lower or "inicia" in text_lower:
                result = vision_guardian(parameters={"action": "enable"}, player=player)
            elif "desactiva" in text_lower or "disable" in text_lower or "para" in text_lower:
                result = vision_guardian(parameters={"action": "disable"}, player=player)
            elif "estado" in text_lower or "status" in text_lower:
                result = vision_guardian(parameters={"action": "status"}, player=player)
            elif "ahora" in text_lower or "check" in text_lower or "analiza" in text_lower:
                result = vision_guardian(parameters={"action": "check_now"}, player=player)
            else:
                result = vision_guardian(parameters={"action": "status"}, player=player)

        # Game Companion
        elif any(kw in text_lower for kw in ["gaming", "juego", "game companion", "modo gaming", "ayuda con este juego"]):
            from actions.game_companion import game_companion
            if "activa" in text_lower or "enable" in text_lower or "inicia" in text_lower:
                result = game_companion(parameters={"action": "enable"}, player=player)
            elif "desactiva" in text_lower or "disable" in text_lower or "para" in text_lower:
                result = game_companion(parameters={"action": "disable"}, player=player)
            elif "detecta" in text_lower or "detect" in text_lower:
                result = game_companion(parameters={"action": "detect"}, player=player)
            else:
                result = game_companion(parameters={"action": "status"}, player=player)

        # Ollama Vision
        elif any(kw in text_lower for kw in ["ollama vision", "vision local", "llava", "ollama para ver"]):
            result = "Para controlar Ollama Vision, decime: 'activa vision local', 'estado de ollama vision', o 'instal\u00e1 llava'."

        # Screen analysis (live)
        elif any(kw in text_lower for kw in ["pantalla", "screen", "captura", "screenshot", "que ves en mi pantalla"]):
            from actions.screen_vision import screen_vision
            result = screen_vision(parameters={"action": "describe"}, player=player)

        # Image file analysis
        elif any(kw in text_lower for kw in ["imagen", "image", "foto", "photo", "archivo de imagen"]):
            result = (
                "Para analizar una imagen, arrastrala a mi ventana o decime 'analiza esta imagen' "
                "y pasame el archivo. Tambien puedo usar vision_guardian para monitoreo continuo."
            )

        # General vision status
        else:
            result = (
                "Puedo ayudarte con vision de varias formas:\n"
                "- 'Activá el guardian' → Monitoreo continuo de pantalla cada 30s\n"
                "- 'Modo gaming' → Ayuda mientras jugás con analisis de pantalla\n"
                "- 'Analiza mi pantalla' → Captura y analisis inmediato\n"
                "- Arrastra una imagen → Analisis de archivo con Gemini u Ollama\n"
                "- 'Estado de ollama vision' → Ver si Ollama LLaVA esta disponible"
            )

        elapsed = time.perf_counter() - t0
        tracer.trace_handoff("vision_agent", text, result, elapsed)
        return result

    except Exception as e:
        elapsed = time.perf_counter() - t0
        tracer.trace_handoff("vision_agent", text, "", elapsed, success=False, error=str(e))
        return f"Error en VisionAgent: {e}"
