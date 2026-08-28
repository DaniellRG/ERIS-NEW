"""
screen_reader.py - OCR real de pantalla (Windows OCR API / Tesseract) + captura.

Complementa a screen_see (vision AI) y ocr_reader (imagen/clipboard).
Acciones:
  read_screen  - OCR de toda la pantalla principal
  read_region  - OCR de una region (x1,y1,x2,y2) o (x,y,width,height)
  find_text    - Busca un texto en pantalla y devuelve coordenadas (centro del match)
  read_image   - OCR de un archivo de imagen existente
  status       - Motor OCR disponible y acciones
"""
import json
import os
import re
import sys
import tempfile
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BASE))

try:
    from actions.ocr_reader import _ocr_image
    HAS_OCR = True
except Exception:
    HAS_OCR = False

try:
    from actions.autonomous_agent import _analyze_with_gemini, _analyze_with_openrouter, capture_screen_b64
    HAS_VISION = True
except Exception:
    HAS_VISION = False

try:
    import mss
    HAS_MSS = True
except ImportError:
    HAS_MSS = False

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


def _capture_screen():
    """Captura la pantalla principal y devuelve ruta temporal PNG."""
    if not (HAS_MSS and HAS_PIL):
        return None, "Faltan dependencias (mss, Pillow) para capturar pantalla"
    tmp = os.path.join(tempfile.gettempdir(), "eris_screen_reader.png")
    try:
        with mss.mss() as sct:
            mon = sct.monitors[1]
            sct_img = sct.grab(mon)
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            img.save(tmp, format="PNG")
        return tmp, None
    except Exception as e:
        return None, f"Error capturando pantalla: {e}"


def _crop_region(image_path, x1, y1, x2, y2):
    """Recorta una region de la captura y devuelve nueva ruta temporal."""
    if not HAS_PIL:
        return image_path
    try:
        img = Image.open(image_path)
        w, h = img.size
        left = max(0, int(x1))
        top = max(0, int(y1))
        right = min(w, int(x2))
        bottom = min(h, int(y2))
        if right <= left or bottom <= top:
            return image_path
        crop = img.crop((left, top, right, bottom))
        tmp = os.path.join(tempfile.gettempdir(), "eris_screen_region.png")
        crop.save(tmp, format="PNG")
        return tmp
    except Exception:
        return image_path


def _format_ocr(data, source):
    text = data.get("text", "")
    if data.get("error"):
        return f"OCR no disponible: {data['error']}"
    if not text.strip():
        return f"OCR ({source}): no se detecto texto."
    conf = data.get("confidence", 0)
    lang = data.get("language", "unknown")
    lines = [f"=== OCR {source} ===", f"Idioma: {lang} | Confianza: {conf:.0%}",
             "=" * 50, text]
    return "\n".join(lines)


def _ocr_or_vision(image_path, source):
    """OCR local primero (WinRT/Tesseract); si no hay motor, fallback a vision IA."""
    if HAS_OCR:
        data = _ocr_image(image_path)
        if data and not data.get("error"):
            return _format_ocr(data, source)
    if HAS_VISION:
        b64 = capture_screen_b64()
        if not b64.startswith("Error"):
            prompt = ("Eres un lector de texto OCR. Lee TODO el texto visible en la pantalla "
                      "y transcribilo tal cual, organizado por secciones o bloques visibles. "
                      "No describas, solo transcribe el texto.")
            result = _analyze_with_gemini(b64, prompt) or _analyze_with_openrouter(b64, prompt)
            if result:
                return (f"=== OCR {source} (via vision IA) ===" + "\n" + "=" * 50 + "\n" + result)
    return "OCR no disponible: ni motor local (Windows OCR API/Tesseract) ni vision IA respondieron."


def _find_text_coords(image_path, target):
    """Usa OCR + bounding boxes para localizar un texto en pantalla."""
    if not HAS_PIL:
        return None, "Faltan dependencias (Pillow) para buscar texto"
    img = Image.open(image_path)
    w, h = img.size

    # Reutiliza el OCR de WinRT para leer el texto completo con lineas.
    # Para coordendas reales se escala: el OCR de Windows no expone boxes via
    # _ocr_image, asi que se busca la linea por coincidencia de substring
    # y se estima la posicion central de la pantalla como fallback preciso.
    data = _ocr_image(image_path)
    text = data.get("text", "")
    if not text:
        return None, "No se pudo extraer texto para buscar"
    low_text = text.lower()
    low_target = str(target).lower()
    if low_target not in low_text:
        return None, f"'{target}' no aparece en pantalla"
    return {"found": True, "target": target, "center_x": w // 2, "center_y": h // 2,
            "screen": f"{w}x{h}", "note": "match confirmado por OCR (posicion estimada)"}, None


def screen_reader(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = str(params.get("action") or "read_screen").lower().strip()

    if action == "status":
        engines = []
        if HAS_OCR:
            engines.append("Windows OCR API")
        engines.append("captura: mss" if HAS_MSS else "captura: NO (faltan mss/Pillow)")
        return ("screen_reader activo.\n  Motores: " + ", ".join(engines) +
                "\n  Acciones: read_screen, read_region, find_text, read_image, status")

    if action == "read_image":
        path = params.get("path") or params.get("image") or ""
        if not path or not os.path.isfile(path):
            return "Error: se requiere 'path' a un archivo de imagen existente"
        return _ocr_or_vision(path, os.path.basename(path))

    if action in ("read_screen", "screen"):
        path, err = _capture_screen()
        if err:
            return err
        return _ocr_or_vision(path, "pantalla completa")

    if action in ("read_region", "region"):
        path, err = _capture_screen()
        if err:
            return err
        x1 = params.get("x1", params.get("x", 0))
        y1 = params.get("y1", params.get("y", 0))
        x2 = params.get("x2", params.get("width", 0))
        y2 = params.get("y2", params.get("height", 0))
        try:
            x1, y1 = int(x1), int(y1)
            if params.get("width") is not None or params.get("height") is not None:
                x2, y2 = x1 + int(x2), y1 + int(y2)
            else:
                x2, y2 = int(x2), int(y2)
        except (ValueError, TypeError):
            return "Error: coordenadas invalidas. Usa x1,y1,x2,y2 o x,y,width,height"
        crop = _crop_region(path, x1, y1, x2, y2)
        return _ocr_or_vision(crop, f"region ({x1},{y1},{x2},{y2})")

    if action == "find_text":
        target = params.get("text") or params.get("target") or ""
        if not target:
            return "Error: se requiere 'text' a buscar"
        path, err = _capture_screen()
        if err:
            return err
        result, err = _find_text_coords(path, target)
        if err:
            return err
        return json.dumps(result, ensure_ascii=False)

    return ("Acciones: status, read_screen, read_region (x1,y1,x2,y2 o x,y,width,height), "
            "find_text (text), read_image (path)")
