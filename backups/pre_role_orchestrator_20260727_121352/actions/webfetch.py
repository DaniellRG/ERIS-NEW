"""webfetch.py — Descarga una URL y devuelve su contenido como texto."""
import json
import urllib.request
import urllib.error
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

def webfetch(parameters: dict, player=None) -> str:
    url = parameters.get("url", "").strip()
    if not url:
        return "URL requerida."
    fmt = parameters.get("format", "text").lower()
    timeout = int(parameters.get("timeout", 15))

    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")

        if fmt == "json":
            try:
                parsed = json.loads(raw)
                return json.dumps(parsed, indent=2, ensure_ascii=False)[:8000]
            except json.JSONDecodeError:
                return "No es JSON válido."

        import html
        text = html.unescape(raw)
        import re
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        lines = text.split('\n')
        cleaned = '\n'.join(line.strip() for line in lines if line.strip())
        if len(cleaned) > 8000:
            cleaned = cleaned[:8000] + "\n\n[...truncado...]"

        if player:
            player.write_log(f"🌐 webfetch: {url} ({len(raw)} bytes -> {len(cleaned)} chars)")
        return cleaned

    except urllib.error.HTTPError as e:
        return f"HTTP {e.code}: {e.reason}"
    except urllib.error.URLError as e:
        return f"Error de red: {e.reason}"
    except Exception as e:
        return f"Error: {e}"
