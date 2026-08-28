import base64
import json
import os
import re
import hashlib
from pathlib import Path
from datetime import datetime

import requests

try:
    from PIL import Image
    from PIL.ExifTags import TAGS
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


def _get_gemini_key():
    config_path = Path("D:/Eris_Source/opencode.json")
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            providers = cfg.get("providers", {})
            for pname, pdata in providers.items():
                if "gemini" in pname.lower() or "google" in pname.lower():
                    key = pdata.get("api_key", "") or pdata.get("apiKey", "")
                    if key:
                        return key
            env_path = Path("D:/Eris_Source/.env")
            if env_path.exists():
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("GEMINI_API_KEY="):
                            return line.split("=", 1)[1].strip().strip('"').strip("'")
        except Exception:
            pass
    env_var = os.environ.get("GEMINI_API_KEY", "")
    if env_var:
        return env_var
    config_path = Path(__file__).resolve().parent.parent / "config" / "api_keys.json"
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            return cfg.get("gemini_api_key", "") or None
        except Exception:
            pass
    return None


def _image_to_base64(image_path):
    with open(image_path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode("utf-8")


def _get_mime_type(image_path):
    ext = Path(image_path).suffix.lower()
    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
        ".tiff": "image/tiff",
        ".tif": "image/tiff",
    }
    return mime_map.get(ext, "image/png")


def _call_gemini(image_base64, prompt, mime_type="image/png"):
    api_key = _get_gemini_key()
    if not api_key:
        return "Error: Gemini API key not found. Configure it in opencode.json or set GEMINI_API_KEY environment variable."
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    payload = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {
                    "inline_data": {
                        "mime_type": mime_type,
                        "data": image_base64
                    }
                }
            ]
        }],
        "generationConfig": {
            "temperature": 0.4,
            "maxOutputTokens": 2048
        }
    }
    try:
        resp = requests.post(url, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            texts = [p.get("text", "") for p in parts if "text" in p]
            return "\n".join(texts) if texts else "No response from Gemini."
        return f"Gemini API error: {json.dumps(data, indent=2)[:500]}"
    except requests.exceptions.RequestException as e:
        return f"Gemini API request error: {e}"
    except Exception as e:
        return f"Error: {e}"


def _get_ollama_cfg():
    config_path = Path(__file__).resolve().parent.parent / "config" / "api_keys.json"
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
        return {
            "base_url": data.get("ollama_base_url", "http://localhost:11434"),
            "vision_model": data.get("ollama_vision_model", "minicpm-v"),
        }
    except Exception:
        return {"base_url": "http://localhost:11434", "vision_model": "minicpm-v"}


def _call_openrouter(image_base64, prompt, mime_type="image/png"):
    config_path = Path(__file__).resolve().parent.parent / "config" / "api_keys.json"
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
        api_key = data.get("openrouter_api_key", "")
    except Exception:
        api_key = ""
    if not api_key:
        return ""
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://github.com/eris-beta",
        "X-Title": "ERIS AI Assistant",
        "Content-Type": "application/json",
    }
    for model in ["google/gemini-2.5-flash", "google/gemini-2.5-flash-lite"]:
        payload = {
            "model": model,
            "max_tokens": 1500,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_base64}"}},
                    ],
                }
            ],
        }
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=60)
            if resp.status_code != 200:
                continue
            data = resp.json()
            if data.get("choices"):
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"[ImageAnalyzer] OpenRouter error ({model}): {e}")
    return ""


def _call_ollama(image_base64, prompt):
    cfg = _get_ollama_cfg()
    base_url = cfg["base_url"]
    model = cfg["vision_model"]
    try:
        resp = requests.get(f"{base_url}/api/tags", timeout=3)
        if resp.status_code != 200:
            return ""
        available = [m.get("name", "") for m in resp.json().get("models", [])]
        if not any(model in m for m in available):
            print(f"[ImageAnalyzer] Ollama vision model '{model}' not found. Available: {available}")
            return ""
    except Exception:
        return ""
    payload = {
        "model": model,
        "prompt": prompt,
        "images": [image_base64],
        "stream": False,
        "options": {"num_predict": 1500, "temperature": 0.3},
    }
    try:
        resp = requests.post(f"{base_url}/api/generate", json=payload, timeout=120)
        resp.raise_for_status()
        return resp.json().get("response", "")
    except Exception as e:
        print(f"[ImageAnalyzer] Ollama error: {e}")
        return ""


def _is_error_result(result):
    if not result:
        return True
    prefixes = ("Error", "Gemini API request error", "Gemini API error", "No response from Gemini")
    return result.startswith(prefixes)


def _analyze_vision(image_base64, prompt, mime_type="image/png"):
    """Chain según vision_mode. local_first: Ollama local → Gemini → OpenRouter."""
    mode = "local_first"
    try:
        API_FILE = Path(__file__).resolve().parent.parent / "config" / "api_keys.json"
        mode = json.loads(API_FILE.read_text("utf-8")).get("vision_mode", "local_first").lower()
    except Exception:
        pass

    chain = [
        (_call_gemini, "Gemini"),
        (_call_openrouter, "OpenRouter"),
        (_call_ollama, "Ollama (local)"),
    ]
    if mode == "local_first":
        chain = [
            (_call_ollama, "Ollama (local)"),
            (_call_gemini, "Gemini"),
            (_call_openrouter, "OpenRouter"),
        ]

    for fn, source in chain:
        try:
            result = fn(image_base64, prompt, mime_type) if fn is not _call_ollama else fn(image_base64, prompt)
            if result and not _is_error_result(result):
                return result, source
        except Exception:
            continue
    return "Error: No se pudo analizar la imagen (Gemini, OpenRouter y Ollama fallaron).", None


def _extract_exif(image_path):
    if not HAS_PIL:
        return {"error": "Pillow not installed. Cannot extract EXIF data."}
    try:
        img = Image.open(image_path)
        exif_data = img._getexif()
        if not exif_data:
            return {"info": "No EXIF data found.", "size": list(img.size), "format": img.format, "mode": img.mode}
        result = {"size": list(img.size), "format": img.format or "Unknown", "mode": img.mode}
        for tag_id, value in exif_data.items():
            tag_name = TAGS.get(tag_id, str(tag_id))
            if isinstance(value, bytes):
                try:
                    value = value.decode("utf-8", errors="replace")
                except Exception:
                    value = f"<{len(value)} bytes>"
            if isinstance(value, (tuple, list)):
                value = list(value)
            result[tag_name] = value
        return result
    except Exception as e:
        return {"error": str(e)}


def _compare_images(path1, path2):
    if not os.path.isfile(path1):
        return f"Error: File not found: {path1}"
    if not os.path.isfile(path2):
        return f"Error: File not found: {path2}"
    try:
        b64_1 = _image_to_base64(path1)
        b64_2 = _image_to_base64(path2)
        prompt = (
            "Compare these two images. Describe the similarities and differences between them. "
            "Be specific about: colors, objects, composition, text, and any notable changes. "
            "If they appear to be different versions of the same thing, explain what changed."
        )
        api_key = _get_gemini_key()
        if not api_key:
            s1 = os.path.getsize(path1)
            s2 = os.path.getsize(path2)
            return (
                f"Local comparison (no API key):\n"
                f"Image 1: {path1} ({s1:,} bytes)\n"
                f"Image 2: {path2} ({s2:,} bytes)\n"
                f"Files {'are identical' if open(path1, 'rb').read() == open(path2, 'rb').read() else 'are different'}."
            )
        try:
            from core.model_config import get_model as _gm
            _imodel = _gm("vision")
        except Exception:
            _imodel = "gemini-flash-latest"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{_imodel}:generateContent?key={api_key}"
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": _get_mime_type(path1), "data": b64_1}},
                    {"inline_data": {"mime_type": _get_mime_type(path2), "data": b64_2}}
                ]
            }],
            "generationConfig": {"temperature": 0.3, "maxOutputTokens": 2048}
        }
        resp = requests.post(url, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            texts = [p.get("text", "") for p in parts if "text" in p]
            return "\n".join(texts)
        return "Could not compare images."
    except Exception as e:
        return f"Error comparing images: {e}"


def image_analyzer(parameters: dict, player=None) -> str:
    action = parameters.get("action", "analyze")
    path = parameters.get("path", parameters.get("image", ""))

    if action == "metadata":
        if not path:
            return "Error: No image path provided."
        if not os.path.isfile(path):
            return f"Error: File not found: {path}"
        exif = _extract_exif(path)
        size = os.path.getsize(path)
        lines = [f"File: {path}", f"Size: {size:,} bytes"]
        if "error" in exif:
            lines.append(f"EXIF Error: {exif['error']}")
        else:
            for k, v in exif.items():
                if isinstance(v, list):
                    v = ", ".join(str(x) for x in v)
                lines.append(f"{k}: {v}")
        return "\n".join(lines)

    if action == "compare":
        path2 = parameters.get("path2", parameters.get("image2", ""))
        if not path or not path2:
            return "Error: Provide both 'path'/'image' and 'path2'/'image2'."
        return _compare_images(path, path2)

    if not path:
        return "Error: No image path provided."
    if not os.path.isfile(path):
        return f"Error: File not found: {path}"

    b64 = _image_to_base64(path)
    mime = _get_mime_type(path)
    file_size = os.path.getsize(path)

    if action == "analyze":
        prompt = (
            "Analyze this image in detail. Describe what you see including:\n"
            "- Main subject and content\n"
            "- Colors, lighting, and mood\n"
            "- Any text visible in the image\n"
            "- Setting/background\n"
            "- Notable details or unusual elements\n"
            "Be thorough but concise."
        )
        result, source = _analyze_vision(b64, prompt, mime)
        return f"=== Image Analysis ===\nFile: {path} ({file_size:,} bytes)\n\n{result}" + (f"\n\n[Fuente: {source}]" if source else "")

    elif action == "identify":
        prompt = (
            "Identify and list all objects, people, animals, drawings/illustrations, text, "
            "and notable elements in this image. For each item, describe its approximate location "
            "in the image (top-left, center, etc.). Count how many of each category there are "
            "(e.g. '3 personas', '2 perros', '1 letrero con texto'). Be as specific as possible."
        )
        result, source = _analyze_vision(b64, prompt, mime)
        return f"=== Object Identification ===\nFile: {path}\n\n{result}" + (f"\n\n[Fuente: {source}]" if source else "")

    elif action == "read_text":
        prompt = (
            "Extract and transcribe ALL visible text from this image. "
            "Include text from signs, labels, documents, screens, handwriting, etc. "
            "Maintain the original structure and layout as much as possible. "
            "If text is partially obscured or unclear, note that."
        )
        result, source = _analyze_vision(b64, prompt, mime)
        return f"=== OCR Result ===\nFile: {path}\n\n{result}" + (f"\n\n[Fuente: {source}]" if source else "")

    return f"Unknown action: {action}. Available: analyze, identify, read_text, compare, metadata"
