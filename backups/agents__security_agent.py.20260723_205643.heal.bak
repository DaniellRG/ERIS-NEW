"""
agents/security_agent.py — ERIS Security Specialized Agent.
Handles security scanning and program management with safety gates.
"""
from __future__ import annotations

import time
from typing import Optional

def handle_security(text: str, player=None, **kwargs) -> str:
    """Handle security and program management requests."""
    from core.tracer import get_tracer
    tracer = get_tracer()
    t0 = time.perf_counter()

    text_lower = text.lower()

    try:
        # Security scanning
        if any(kw in text_lower for kw in ["escanear", "scan", "virus", "malware", "seguridad", "defender", "usb scan"]):
            from actions.security_scanner import security_scanner

            if "rapido" in text_lower or "quick" in text_lower:
                result = security_scanner(parameters={"action": "quick_scan"}, player=player)
            elif "completo" in text_lower or "full" in text_lower or "profundo" in text_lower:
                result = security_scanner(parameters={"action": "full_scan"}, player=player)
            elif "usb" in text_lower:
                result = security_scanner(parameters={"action": "usb_scan"}, player=player)
            elif "estado" in text_lower or "status" in text_lower:
                result = security_scanner(parameters={"action": "status"}, player=player)
            else:
                result = security_scanner(parameters={"action": "quick_scan"}, player=player)

        # Program management
        elif any(kw in text_lower for kw in ["instalar", "install", "desinstalar", "uninstall", "programa", "aplicacion", "winget", "choco"]):
            from actions.program_manager import program_manager

            if "instalar" in text_lower or "install" in text_lower:
                # Extract program name
                program = text_lower.replace("instalar", "").replace("install", "").strip()
                result = program_manager(parameters={"action": "install", "program": program}, player=player)

            elif "desinstalar" in text_lower or "uninstall" in text_lower or "quitar" in text_lower:
                program = text_lower.replace("desinstalar", "").replace("uninstall", "").replace("quitar", "").strip()
                result = program_manager(parameters={"action": "uninstall", "program": program}, player=player)

            elif "lista" in text_lower or "list" in text_lower or "instalados" in text_lower:
                result = program_manager(parameters={"action": "list_installed"}, player=player)

            elif "buscar" in text_lower or "search" in text_lower:
                program = text_lower.replace("buscar", "").replace("search", "").strip()
                result = program_manager(parameters={"action": "search", "program": program}, player=player)

            else:
                result = program_manager(parameters={"action": "status"}, player=player)

        else:
            result = (
                "Puedo ayudarte con seguridad y programas:\n"
                "- 'Escaneo rapido' → Scan rapido con Defender\n"
                "- 'Escaneo completo' → Scan profundo del sistema\n"
                "- 'Scan USB' → Verificar dispositivos USB\n"
                "- 'Instalar [programa]' → Instalar con winget/choco (con confirmacion)\n"
                "- 'Desinstalar [programa]' → Quitar programa (con confirmacion)\n"
                "- 'Lista de programas' → Ver programas instalados"
            )

        elapsed = time.perf_counter() - t0
        tracer.trace_handoff("security_agent", text, result, elapsed)
        return result

    except Exception as e:
        elapsed = time.perf_counter() - t0
        tracer.trace_handoff("security_agent", text, "", elapsed, success=False, error=str(e))
        return f"Error en SecurityAgent: {e}"
