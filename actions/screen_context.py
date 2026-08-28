# -*- coding: utf-8 -*-
"""
screen_context.py — Captura de pantalla + OCR + descripción visual.
Acciones:
  capture  — Tomar screenshot
  ocr      — Extraer texto de la pantalla
  analyze  — Describir qué hay en pantalla
  region   — Capturar una región específica
  history  — Historial de capturas
Storage: data/screenshots/
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any

_SCREENSHOT_DIR = Path(r"D:\Eris_Source\data\screenshots")
_SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
_HISTORY_FILE = Path(r"D:\Eris_Source\data\screenshot_history.json")


def _load_history() -> list:
    if _HISTORY_FILE.exists():
        try:
            return json.loads(_HISTORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def _save_history(history):
    _HISTORY_FILE.write_text(json.dumps(history[-100:], ensure_ascii=False, indent=2), encoding="utf-8")


def _take_screenshot(region=None) -> str:
    try:
        from PIL import ImageGrab
        if region:
            img = ImageGrab.grab(bbox=tuple(region))
        else:
            img = ImageGrab.grab()
        name = f"screen_{int(time.time())}.png"
        path = _SCREENSHOT_DIR / name
        img.save(str(path))
        history = _load_history()
        history.append({"path": str(path), "time": time.strftime("%Y-%m-%d %H:%M:%S"), "size": path.stat().st_size})
        _save_history(history)
        return str(path)
    except Exception as e:
        return f"Error screenshot: {str(e)[:100]}"


def _ocr_image(image_path: str) -> str:
    try:
        import pytesseract
        from PIL import Image
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img, lang="spa+eng")
        return text.strip()
    except ImportError:
        try:
            from PIL import Image
            import subprocess
            img = Image.open(image_path)
            temp_txt = image_path.replace(".png", ".txt")
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 f'Add-Type -AssemblyName System.Windows.Forms; '
                 f'[System.Windows.Forms.Clipboard]::SetText("ocr_unavailable")'],
                capture_output=True, text=True, timeout=10, creationflags=0x08000000)
            return "[pytesseract no instalado — pip install pytesseract + tesseract-ocr]"
        except Exception as e:
            return f"Error OCR: {str(e)[:100]}"
    except Exception as e:
        return f"Error OCR: {str(e)[:100]}"


def screen_context(parameters: dict = None, player=None) -> str:
    """Tool: Captura de pantalla, OCR y descripción visual."""
    params = parameters or {}
    action = str(params.get("action", "capture")).lower().strip()

    if action == "capture":
        region = params.get("region")
        path = _take_screenshot(region)
        if path.startswith("Error"):
            return path
        size_kb = Path(path).stat().st_size // 1024
        return f"📸 Screenshot guardado: {Path(path).name} ({size_kb}KB)"

    if action == "ocr":
        image_path = str(params.get("image", "")).strip()
        if not image_path:
            path = _take_screenshot()
            if path.startswith("Error"):
                return path
            image_path = path
        elif not os.path.exists(image_path):
            return f"Imagen no encontrada: {image_path}"
        text = _ocr_image(image_path)
        if not text:
            return "No se detectó texto en la imagen."
        return f"**Texto detectado ({len(text)} chars):**\n\n{text[:3000]}"

    if action == "analyze":
        image_path = str(params.get("image", "")).strip()
        if not image_path:
            path = _take_screenshot()
            if path.startswith("Error"):
                return path
            image_path = path
        elif not os.path.exists(image_path):
            return f"Imagen no encontrada: {image_path}"
        text = _ocr_image(image_path)
        try:
            from PIL import Image
            img = Image.open(image_path)
            w, h = img.size
            lines = [f"**Análisis de pantalla ({w}x{h}):**\n"]
            lines.append(f"📐 Dimensiones: {w}x{h}")
            lines.append(f"💾 Tamaño: {Path(image_path).stat().st_size // 1024}KB")
            if text:
                lines.append(f"\n📝 **Texto detectado:**\n{text[:1500]}")
            else:
                lines.append("\n📝 Sin texto detectable.")
            dominant = img.resize((1, 1)).getpixel((0, 0))
            lines.append(f"\n🎨 Color dominante: RGB{dominant[:3]}")
            return "\n".join(lines)
        except Exception as e:
            return f"Error analizando: {str(e)[:100]}"

    if action == "region":
        x = int(params.get("x", 0))
        y = int(params.get("y", 0))
        w = int(params.get("width", 400))
        h = int(params.get("height", 300))
        path = _take_screenshot(region=(x, y, x + w, y + h))
        if path.startswith("Error"):
            return path
        return f"📸 Región ({x},{y},{w}x{h}) capturada: {Path(path).name}"

    if action == "history":
        history = _load_history()
        max_entries = min(int(params.get("max_entries", 10)), 30)
        recent = history[-max_entries:]
        if not recent:
            return "Sin capturas previas."
        lines = [f"**Historial ({len(recent)}):**\n"]
        for h in reversed(recent):
            lines.append(f"• {h['time']} — {Path(h['path']).name} ({h.get('size', 0) // 1024}KB)")
        return "\n".join(lines)

    return "Acciones: capture, ocr, analyze, region, history"
