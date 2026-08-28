# -*- coding: utf-8 -*-
"""
accessibility.py — Herramientas de accesibilidad de Windows.
Acciones:
  status        — Estado del módulo y acciones disponibles
  narrator      — Iniciar el Narrador de Windows (Win+Enter para detener)
  magnifier     — Iniciar la Lupa de Windows (Win + +/- para zoom)
  high_contrast — Orientación sobre alto contraste (Win+Ctrl+C)
  dictation     — Orientación sobre dictado por voz (Win+H)
  read_screen   — Leer pantalla en voz alta (requiere OCR/Tesseract)
"""
from __future__ import annotations

import os
import subprocess


def _start_system_app(exe_name: str) -> tuple[bool, str]:
    try:
        os.startfile(exe_name)
        return True, ""
    except Exception as e:
        return False, str(e)


def accessibility(parameters: dict = None, player=None) -> str:
    parameters = parameters or {}
    action = parameters.get("action") or ""

    if action == "status":
        return ("Módulo de accesibilidad activo. Acciones: narrator, magnifier, "
                "high_contrast, dictation, read_screen.")

    if action == "narrator":
        ok, err = _start_system_app("narrator")
        if ok:
            return "Narrador de Windows iniciado. Para detenerlo, presioná Win+Enter."
        return f"No se pudo iniciar el Narrador de Windows: {err}"

    if action == "magnifier":
        ok, err = _start_system_app("magnify.exe")
        if ok:
            return "Lupa de Windows iniciada. Ajustes de zoom: Win + (más) / Win - (menos)."
        return f"No se pudo iniciar la Lupa de Windows: {err}"

    if action == "high_contrast":
        return ("Alto contraste: activalo con Win+Ctrl+C o en Configuración > "
                "Accesibilidad > Contraste. ERIS no lo modifica para no alterar tu sesión visual.")

    if action == "dictation":
        return ("Dictado por voz: presioná Win+H (requiere el motor de dictado de Windows "
                "activo). ERIS no gestiona el dictado nativo de Windows.")

    if action == "read_screen":
        return ("Leer la pantalla en voz alta requiere un motor OCR (Tesseract) que no está "
                "instalado. Alternativas: usá el Narrador (Win+Enter) o la tool 'ocr_reader' "
                "para extraer texto de una captura.")

    return ("Acciones de accesibilidad: status, narrator, magnifier, high_contrast, "
            "dictation, read_screen.")
