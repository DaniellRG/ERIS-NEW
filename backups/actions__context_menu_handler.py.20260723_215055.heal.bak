"""Manejador de acciones invocadas desde el menu contextual de Windows."""
import os
import sys
from pathlib import Path


def handle_action(action: str, file_path: str = "") -> str:
    """Ejecuta una accion solicitada desde el menu contextual."""
    p = file_path.strip('"')
    if action == "analyze":
        if os.path.isfile(p):
            size = os.path.getsize(p)
            name = os.path.basename(p)
            return f"[ERIS] Analizando: {name} ({size/1024:.0f} KB)"
        return f"[ERIS] Ruta no encontrada: {p}"

    if action == "translate":
        if os.path.isfile(p) and p.lower().endswith((".txt", ".md", ".srt", ".vtt")):
            try:
                text = Path(p).read_text(encoding="utf-8")[:2000]
                from actions.translator import translate
                result = translate(text, "es")
                return f"[ERIS] Traduccion:\n{result}"
            except Exception as e:
                return f"[ERIS] Error al traducir: {e}"
        return "[ERIS] Solo archivos de texto (.txt, .md, .srt, .vtt)"

    if action == "summarize":
        if os.path.isfile(p) and p.lower().endswith((".txt", ".md")):
            try:
                text = Path(p).read_text(encoding="utf-8")[:3000]
                from google import genai
                from memory.config_manager import get_gemini_key
                key = get_gemini_key()
                if not key:
                    return "[ERIS] No hay API key de Gemini configurada."
                client = genai.Client(api_key=key)
                resp = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=[{"role": "user", "parts": [{"text": f"Resume este texto en 3 lineas:\n\n{text}"}]}],
                )
                return f"[ERIS] Resumen:\n{resp.text}"
            except Exception as e:
                return f"[ERIS] Error: {e}"
        return "[ERIS] Solo archivos de texto (.txt, .md)"

    return f"[ERIS] Accion desconocida: {action}"
