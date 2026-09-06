"""
actions/ocr_tool.py — OCR offline con tesseract para ERIS.

Lee texto de archivos de imagen/PDF, o de la pantalla (captura grim) sin
consumir API. Idiomas: spa + eng.
"""
from __future__ import annotations

import io
import os
import shutil
import subprocess

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _tess(img_path: str, lang: str, psm: int) -> str:
    bin_ = shutil.which("tesseract")
    if not bin_:
        return "Error: tesseract no está instalado (`sudo pacman -S tesseract tesseract-data-spa`)."
    try:
        r = subprocess.run([bin_, img_path, "stdout", "-l", lang, "--psm", str(psm)],
                           capture_output=True, text=True, timeout=90)
        if r.returncode != 0:
            return f"Error tesseract ({r.returncode}): {r.stderr.strip()[:200]}"
        return r.stdout.strip() or "(sin texto detectable)"
    except subprocess.TimeoutExpired:
        return "Error: tesseract tardó demasiado."
    except Exception as e:
        return f"Error: {type(e).__name__}: {e}"


def _lang(parameters) -> str:
    l = (parameters.get("lang") or "auto").lower()
    if l in ("spa", "es", "español", "spanish"):
        return "spa"
    if l == "eng":
        return "eng"
    return "spa+eng"


def ocr_tool(parameters: dict | None = None, player=None) -> str:
    """OCR offline (tesseract). Acciones: file (path), screen (captura grim),
    region (x,y,w,h vía grim), pdf (primera página), langs."""
    parameters = parameters or {}
    action = (parameters.get("action") or "screen").lower()
    lang = _lang(parameters)

    if action in ("langs", "idiomas"):
        try:
            r = subprocess.run([shutil.which("tesseract") or "tesseract", "--list-langs"],
                               capture_output=True, text=True)
            return "Idiomas OCR: " + r.stdout.split("\n", 1)[1].replace("\n", " ").strip()
        except Exception as e:
            return f"Error: {e}"

    tmp = "/tmp/eris_ocr.png"

    if action in ("file", "archivo"):
        path = (parameters.get("path") or parameters.get("file") or "").strip()
        if not path or not os.path.exists(path):
            return "Falta 'path' (archivo de imagen existente)."
        psm = int(parameters.get("psm", 3) or 3)
        return _tess(path, lang, psm)

    if action in ("screen", "pantalla"):
        try:
            from actions.screen_vision import _capture_screen_base64
            import base64
            b64 = _capture_screen_base64()
            if not b64 or b64.startswith("Error"):
                return f"Error capturando pantalla: {b64}"
            with open(tmp, "wb") as f:
                f.write(base64.b64decode(b64))
            psm = int(parameters.get("psm", 3) or 3)
            return _tess(tmp, lang, psm)
        except Exception as e:
            return f"Error: {type(e).__name__}: {e}"

    if action in ("region", "region", "zona"):
        try:
            import base64
            x = int(parameters.get("x", 0)); y = int(parameters.get("y", 0))
            w = int(parameters.get("w", parameters.get("width", 400)))
            h = int(parameters.get("h", parameters.get("height", 200)))
            from actions.autonomous_agent import capture_region_b64
            b64 = capture_region_b64(x, y, w, h)
            if not b64 or b64.startswith("Error"):
                return f"Error capturando región: {b64}"
            with open(tmp, "wb") as f:
                f.write(base64.b64decode(b64))
            psm = int(parameters.get("psm", 6) or 6)
            return _tess(tmp, lang, psm)
        except Exception as e:
            return f"Error: {type(e).__name__}: {e}"

    if action in ("pdf",):
        path = (parameters.get("path") or parameters.get("file") or "").strip()
        if not path or not os.path.exists(path):
            return "Falta 'path' del PDF."
        conv = shutil.which("pdftoppm") or shutil.which("mutool")
        if not conv:
            return "Para PDF necesitás poppler: `sudo pacman -S poppler`."
        try:
            if conv.endswith("pdftoppm"):
                subprocess.run(["pdftoppm", "-f", "1", "-l", "1", "-png", "-r", "180",
                                path, "/tmp/eris_pdfpage"], timeout=60, check=True)
                out = "/tmp/eris_pdfpage-1.png"
            else:
                subprocess.run(["mutool", "draw", "-o", tmp, "-r", "180", path, "1"],
                               timeout=60, check=True)
                out = tmp
            return _tess(out, lang, int(parameters.get("psm", 3) or 3))
        except subprocess.CalledProcessError as e:
            return f"Error convirtiendo PDF: {e}"
        except Exception as e:
            return f"Error: {type(e).__name__}: {e}"

    return ("Acciones: file (path), screen, region (x,y,w,h), pdf (path), langs. "
            "Params: lang (auto|spa|eng), psm.")