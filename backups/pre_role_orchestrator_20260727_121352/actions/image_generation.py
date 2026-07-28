"""
image_generation.py — Generación real de imágenes usando Stable Diffusion local, DALL-E, o fallback.
"""
import json
import base64
import time
from pathlib import Path
from datetime import datetime

_BASE = Path(__file__).resolve().parent.parent
_IMAGES_DIR = _BASE / "data" / "generated_images"
_IMAGE_LOG = _BASE / "data" / "image_generation_log.json"
_API_KEYS_FILE = _BASE / "config" / "api_keys.json"


def image_generation(parameters: dict = None, player=None) -> str:
    """
    Generación de imágenes.
    Acciones: generate, list, get, delete, style, upscale, variations, batch, status, gallery
    """
    params = parameters or {}
    action = params.get("action", "generate").lower()
    _IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    if action == "generate":
        return _generate_image(params)
    elif action == "list":
        return _list_images(params)
    elif action == "get":
        return _get_image_info(params)
    elif action == "delete":
        return _delete_image(params)
    elif action == "style":
        return _get_styles()
    elif action == "upscale":
        return _upscale_image(params)
    elif action == "variations":
        return _generate_variations(params)
    elif action == "batch":
        return _batch_generate(params)
    elif action == "status":
        return _get_status()
    elif action == "gallery":
        return _gallery_view()
    elif action == "download":
        return _download_image(params)
    return "Acciones: generate, list, get, delete, style, upscale, variations, batch, status, gallery, download"


def _generate_image(params: dict) -> str:
    prompt = params.get("prompt", "")
    if not prompt:
        return "Error: se requiere 'prompt'"

    style = params.get("style", "default")
    width = int(params.get("width", 512))
    height = int(params.get("height", 512))
    seed = params.get("seed", int(time.time()))
    provider = params.get("provider", "auto")

    enhanced_prompt = _enhance_prompt(prompt, style)

    if provider in ("auto", "ollama"):
        result = _try_ollama_generate(enhanced_prompt, width, height)
        if result:
            return result

    if provider in ("auto", "stability"):
        result = _try_stability_ai(enhanced_prompt, width, height, seed)
        if result:
            return result

    if provider in ("auto", "local"):
        result = _try_local_diffusion(enhanced_prompt, width, height, seed)
        if result:
            return result

    return _fallback_image_generate(enhanced_prompt, width, height, seed)


def _enhance_prompt(prompt: str, style: str) -> str:
    style_modifiers = {
        "default": prompt,
        "realistic": "highly detailed, photorealistic, 8k, professional photography, " + prompt,
        "artistic": "digital art, vibrant colors, detailed illustration, " + prompt,
        "anime": "anime style, detailed, vibrant, studio ghibli inspired, " + prompt,
        "oil_painting": "oil painting, classical art, detailed brushwork, " + prompt,
        "3d": "3d render, octane render, highly detailed, volumetric lighting, " + prompt,
        "pixel_art": "pixel art, retro, 16-bit style, " + prompt,
        "watercolor": "watercolor painting, soft colors, artistic, " + prompt,
        "cyberpunk": "cyberpunk style, neon lights, dark atmosphere, " + prompt,
        "fantasy": "fantasy art, magical, ethereal, detailed, " + prompt,
        "minimalist": "minimalist design, clean lines, simple, " + prompt,
        "cinematic": "cinematic lighting, movie still, dramatic, " + prompt,
    }
    return style_modifiers.get(style, prompt)


def _try_ollama_generate(prompt, width, height):
    try:
        import requests
        models = ["minicpm-v", "llava", "bakllava"]
        for model in models:
            try:
                resp = requests.post("http://localhost:11434/api/generate", json={
                    "model": model,
                    "prompt": "Generate an image: {}".format(prompt),
                    "stream": False
                }, timeout=30)
                if resp.status_code == 200:
                    return "Generado via Ollama ({}). Nota: modelos de texto generan descripción, no imagen directa".format(model)
            except Exception:
                continue
    except Exception:
        pass
    return None


def _try_stability_ai(prompt, width, height, seed):
    try:
        api_key = _get_api_key("stability")
        if not api_key:
            return None

        import requests
        resp = requests.post(
            "https://api.stability.ai/v1/generation/stable-diffusion-xl/text-to-image",
            headers={"Authorization": "Bearer {}".format(api_key), "Content-Type": "application/json"},
            json={
                "text_prompts": [{"text": prompt, "weight": 1}],
                "cfg_scale": 7,
                "width": width,
                "height": height,
                "seed": seed,
                "steps": 30,
            },
            timeout=60
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("artifacts"):
                img_data = base64.b64decode(data["artifacts"][0]["base64"])
                name = "stability_{}".format(int(time.time()))
                filepath = _IMAGES_DIR / "{}.png".format(name)
                filepath.write_bytes(img_data)
                _log_generation(name, prompt, "stability_ai", filepath)
                return "Imagen generada via Stability AI: {}".format(str(filepath))
    except Exception:
        pass
    return None


def _try_local_diffusion(prompt, width, height, seed):
    try:
        from diffusers import StableDiffusionPipeline
        import torch
        pipe = StableDiffusionPipeline.from_pretrained(
            "runwayml/stable-diffusion-v1-5",
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32
        )
        if torch.cuda.is_available():
            pipe = pipe.to("cuda")
        image = pipe(prompt, num_inference_steps=30, width=width, height=height, generator=torch.manual_seed(seed)).images[0]
        name = "local_{}".format(int(time.time()))
        filepath = _IMAGES_DIR / "{}.png".format(name)
        image.save(str(filepath))
        _log_generation(name, prompt, "local_diffusion", filepath)
        return "Imagen generada localmente: {}".format(str(filepath))
    except ImportError:
        return None
    except Exception:
        return None


def _fallback_image_generate(prompt, width, height, seed):
    try:
        from PIL import Image, ImageDraw, ImageFont
        img = Image.new("RGB", (width, height), color=(30, 30, 50))
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("arial.ttf", 14)
        except Exception:
            font = ImageFont.load_default()

        draw.text((20, 20), "ERIS Image Generator", fill=(100, 200, 255), font=font)
        draw.text((20, 50), "Prompt: {}".format(prompt[:50]), fill=(200, 200, 200), font=font)
        draw.text((20, 80), "Provider: fallback (no hay servicio disponible)", fill=(150, 150, 150), font=font)
        draw.text((20, 110), "Instala: pip install diffusers transformers torch", fill=(150, 150, 150), font=font)

        for i in range(20):
            x = (hash(prompt + str(i)) % width)
            y = (hash(prompt + str(i + 100)) % height)
            r = 5 + (i % 10)
            color = ((i * 37) % 256, (i * 73) % 256, (i * 111) % 256)
            draw.ellipse([x - r, y - r, x + r, y + r], fill=color)

        name = "fallback_{}".format(int(time.time()))
        filepath = _IMAGES_DIR / "{}.png".format(name)
        img.save(str(filepath))
        _log_generation(name, prompt, "fallback", filepath)
        return "Imagen placeholder generada (instala diffusers para generación real): {}".format(str(filepath))
    except Exception as e:
        return "Error en fallback: {}".format(str(e))


def _list_images(params: dict) -> str:
    images = sorted(_IMAGES_DIR.glob("*.png"), key=lambda x: x.stat().st_mtime, reverse=True)
    if not images:
        return "No hay imágenes generadas"

    limit = params.get("limit", 10)
    results = ["Imágenes generadas ({} total):".format(len(images))]
    for img in images[:limit]:
        size_kb = img.stat().st_size / 1024
        mtime = datetime.fromtimestamp(img.stat().st_mtime)
        results.append("  {} | {:.1f}KB | {}".format(img.stem, size_kb, mtime.strftime("%Y-%m-%d %H:%M")))
    return "\n".join(results)


def _get_image_info(params: dict) -> str:
    name = params.get("name", "")
    if not name:
        return "Error: se requiere 'name'"
    filepath = _IMAGES_DIR / "{}.png".format(name)
    if not filepath.exists():
        return "Imagen no encontrada: {}".format(name)

    log = _load_log()
    meta = next((e for e in log.get("generations", []) if e.get("name") == name), {})

    return "Imagen: {} | {:.1f}KB | Prompt: {} | Provider: {}".format(
        name, filepath.stat().st_size / 1024,
        meta.get("prompt", "?")[:60], meta.get("provider", "?"))


def _delete_image(params: dict) -> str:
    name = params.get("name", "")
    if not name:
        return "Error: se requiere 'name'"
    filepath = _IMAGES_DIR / "{}.png".format(name)
    if filepath.exists():
        filepath.unlink()
        return "Imagen '{}' eliminada".format(name)
    return "No encontrada: {}".format(name)


def _get_styles() -> str:
    return "Estilos disponibles:\n" + "\n".join(
        "  - {}".format(s) for s in [
            "default", "realistic", "artistic", "anime", "oil_painting",
            "3d", "pixel_art", "watercolor", "cyberpunk", "fantasy",
            "minimalist", "cinematic"])


def _upscale_image(params: dict) -> str:
    name = params.get("name", "")
    if not name:
        return "Error: se requiere 'name'"
    filepath = _IMAGES_DIR / "{}.png".format(name)
    if not filepath.exists():
        return "No encontrada: {}".format(name)
    try:
        from PIL import Image
        img = Image.open(str(filepath))
        scale = int(params.get("scale", 2))
        new_size = (img.width * scale, img.height * scale)
        upscaled = img.resize(new_size, Image.Resampling.LANCZOS)
        out_name = "{}_upscaled".format(name)
        out_path = _IMAGES_DIR / "{}.png".format(out_name)
        upscaled.save(str(out_path))
        return "Imagen '{}' upscaled {}x → {}".format(name, scale, str(out_path))
    except ImportError:
        return "Pillow necesario: pip install Pillow"


def _generate_variations(params: dict) -> str:
    prompt = params.get("prompt", "")
    count = min(int(params.get("count", 4)), 8)
    results = []
    for i in range(count):
        result = _generate_image({
            "prompt": prompt,
            "seed": int(time.time()) + i * 1000,
            "style": params.get("style", "default"),
        })
        results.append(result)
    return "Variaciones generadas ({}):\n{}".format(count, "\n".join(results))


def _batch_generate(params: dict) -> str:
    prompts = params.get("prompts", [])
    if not prompts:
        return "Error: se requiere 'prompts' (lista)"
    results = []
    for p in prompts:
        result = _generate_image({"prompt": p, "style": params.get("style", "default")})
        results.append("  {} → {}".format(p[:30], result[:50]))
    return "Batch ({}):\n{}".format(len(prompts), "\n".join(results))


def _gallery_view() -> str:
    images = sorted(_IMAGES_DIR.glob("*.png"), key=lambda x: x.stat().st_mtime, reverse=True)
    if not images:
        return "Galería vacía"
    lines = ["Galería de imágenes:"]
    for i, img in enumerate(images[:20]):
        lines.append("  {}. {} ({:.1f}KB)".format(i + 1, img.stem, img.stat().st_size / 1024))
    return "\n".join(lines)


def _download_image(params: dict) -> str:
    name = params.get("name", "")
    dest = params.get("destination", "")
    if not name or not dest:
        return "Error: se requiere 'name' y 'destination'"
    src = _IMAGES_DIR / "{}.png".format(name)
    if not src.exists():
        return "No encontrada: {}".format(name)
    import shutil
    shutil.copy2(str(src), dest)
    return "Imagen copiada a: {}".format(dest)


def _get_status() -> str:
    images = list(_IMAGES_DIR.glob("*.png"))
    total_size = sum(f.stat().st_size for f in images) / (1024 * 1024)
    providers = {"stability": _get_api_key("stability") is not None}
    try:
        import diffusers
        providers["local"] = True
    except ImportError:
        providers["local"] = False
    return "Image Gen: {} imágenes ({:.1f}MB) | Providers: {}".format(
        len(images), total_size,
        ", ".join("{}:{}".format(k, "ok" if v else "no") for k, v in providers.items()))


def _log_generation(name, prompt, provider, filepath):
    log = _load_log()
    log.setdefault("generations", []).append({
        "name": name, "prompt": prompt, "provider": provider,
        "filename": filepath.name, "timestamp": datetime.now().isoformat()
    })
    log["generations"] = log["generations"][-500:]
    _IMAGE_LOG.write_text(json.dumps(log, indent=2, ensure_ascii=False), encoding="utf-8")


def _load_log():
    if _IMAGE_LOG.exists():
        try:
            return json.loads(_IMAGE_LOG.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"generations": []}


def _get_api_key(service):
    if _API_KEYS_FILE.exists():
        try:
            keys = json.loads(_API_KEYS_FILE.read_text(encoding="utf-8"))
            return keys.get(service, keys.get("{}_api_key".format(service)))
        except Exception:
            pass
    return None
