# -*- coding: utf-8 -*-
"""
page_summarizer.py — Resume automatico de paginas web, videos de YouTube,
y cualquier contenido. Extrae texto limpio, transcripciones, y genera resumenes.
"""
import json
import re
import urllib.request
import urllib.parse
from pathlib import Path
from datetime import datetime

_HISTORY_FILE = Path(__file__).resolve().parent.parent / "data" / "summarizer_history.json"
_CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "page_cache"


def page_summarizer(parameters: dict, player=None) -> str:
    """Resume paginas web, videos, y contenido."""
    params = parameters or {}
    action = (params.get("action") or "summarize_url").lower().strip()
    url = (params.get("url") or "").strip()
    text = (params.get("text") or "").strip()
    video_id = (params.get("video_id") or "").strip()
    query = (params.get("query") or "").strip()
    max_chars = int(params.get("max_chars") or 2000)

    if action == "summarize_url" or action == "url":
        return _summarize_url(url, max_chars)
    elif action == "summarize_video" or action == "video":
        return _summarize_video(video_id or url, max_chars)
    elif action == "summarize_text" or action == "text":
        return _summarize_text(text, query)
    elif action == "fetch_page" or action == "fetch":
        return _fetch_page_text(url, max_chars)
    elif action == "fetch_transcript" or action == "transcript":
        return _fetch_youtube_transcript(video_id or url)
    elif action == "batch_summarize" or action == "batch":
        return _batch_summarize(text, max_chars)
    elif action == "history":
        return _get_history()
    elif action == "search_and_summarize":
        return _search_and_summarize(query, max_chars)
    return (
        "Acciones: summarize_url (resumir pagina), summarize_video (resumir video YouTube), "
        "summarize_text (resumir texto), fetch_page (obtener texto de URL), "
        "fetch_transcript (obtener transcripcion de video), batch_summarize (resumir multiples URLs), "
        "search_and_summarize (buscar y resumir), history (historial)"
    )


def _summarize_url(url: str, max_chars: int = 2000) -> str:
    if not url:
        return "Error: especifica la URL a resumir"
    if not url.startswith("http"):
        url = "https://" + url

    is_youtube = "youtube.com" in url or "youtu.be" in url
    if is_youtube:
        return _summarize_video(url, max_chars)

    text = _fetch_page_text(url, max_chars * 2)
    if text.startswith("Error"):
        return text

    summary = _generate_summary(text, max_chars)
    _log_history("summarize_url", url[:100])
    return _format_summary("PAGINA WEB", url, summary, len(text))


def _summarize_video(url_or_id: str, max_chars: int = 2000) -> str:
    if not url_or_id:
        return "Error: especifica la URL o video_id del video"

    video_id = _extract_video_id(url_or_id)
    if not video_id:
        return "No pude extraer el ID del video de '{}'".format(url_or_id[:50])

    info = _get_video_metadata(video_id)
    transcript = _fetch_youtube_transcript(video_id)

    parts = []
    if info:
        parts.append("TITLE: {}".format(info.get("title", "?")))
        parts.append("CHANNEL: {}".format(info.get("channel", "?")))
        parts.append("VIEWS: {}".format(info.get("views", "?")))
        parts.append("DURATION: {}".format(info.get("duration", "?")))
        desc = info.get("description", "")
        if desc:
            parts.append("DESCRIPTION: {}".format(desc[:1000]))

    if transcript and not transcript.startswith("Error"):
        parts.append("TRANSCRIPT: {}".format(transcript[:5000]))
    elif not parts:
        return "No pude obtener info del video '{}'".format(url_or_id[:50])

    full_text = "\n".join(parts)
    summary = _generate_summary(full_text, max_chars)
    _log_history("summarize_video", url_or_id[:100])
    return _format_summary("VIDEO YOUTUBE", url_or_id, summary, len(full_text))


def _summarize_text(text: str, query: str = "") -> str:
    if not text:
        return "Error: especifica el texto a resumir"
    summary = _generate_summary(text, 2000)
    _log_history("summarize_text", query or text[:50])
    return _format_summary("TEXTO", query or "texto proporcionado", summary, len(text))


def _fetch_page_text(url: str, max_chars: int = 5000) -> str:
    if not url:
        return "Error: especifica la URL"
    if not url.startswith("http"):
        url = "https://" + url
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return "Error: pip install beautifulsoup4"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

        soup = BeautifulSoup(html, "html.parser")

        for tag in soup(["script", "style", "nav", "footer", "header", "aside",
                         "form", "button", "iframe", "noscript"]):
            tag.decompose()

        title = soup.title.get_text(strip=True) if soup.title else ""
        meta_desc = ""
        meta = soup.find("meta", attrs={"name": "description"})
        if meta:
            meta_desc = meta.get("content", "")

        article = soup.find("article")
        if article:
            body_text = article.get_text(separator="\n", strip=True)
        else:
            main = soup.find("main") or soup.find("div", {"role": "main"})
            if main:
                body_text = main.get_text(separator="\n", strip=True)
            else:
                body_text = soup.get_text(separator="\n", strip=True)

        lines = [l.strip() for l in body_text.split("\n") if len(l.strip()) > 20]
        body_text = "\n".join(lines)

        result_parts = []
        if title:
            result_parts.append("TITLE: {}".format(title))
        if meta_desc:
            result_parts.append("DESCRIPTION: {}".format(meta_desc))
        result_parts.append("CONTENT:")
        result_parts.append(body_text[:max_chars])

        return "\n".join(result_parts)
    except Exception as e:
        return "Error fetching '{}': {}".format(url[:50], str(e)[:100])


def _fetch_youtube_transcript(video_id: str) -> str:
    if not video_id:
        return "Error: especifica video_id"
    video_id = _extract_video_id(video_id) or video_id
    if len(video_id) != 11:
        return "Error: video_id invalido"

    try:
        page_url = "https://www.youtube.com/watch?v={}".format(video_id)
        req = urllib.request.Request(page_url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "es-ES,es;q=0.9",
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

        caption_match = re.search(
            r'"captionTracks":\s*(\[.*?\])', html)
        if caption_match:
            tracks = json.loads(caption_match.group(1))
            for track in tracks:
                lang = track.get("languageCode", "")
                if lang in ("es", "en") or (not lang.startswith("zh")):
                    transcript_url = track.get("baseUrl", "")
                    if transcript_url:
                        return _fetch_transcript_from_url(transcript_url)

        desc_match = re.search(
            r'"shortDescription":\s*"((?:[^"\\]|\\.)*)"', html)
        if desc_match:
            desc = desc_match.group(1).replace("\\n", "\n").replace('\\"', '"')
            return "Sin transcripcion. Descripcion del video:\n{}".format(desc[:3000])

        return "No se pudo obtener transcripcion"
    except Exception as e:
        return "Error obteniendo transcripcion: {}".format(str(e)[:80])


def _fetch_transcript_from_url(url: str) -> str:
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0",
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            xml = resp.read().decode("utf-8", errors="ignore")

        texts = re.findall(r'<text[^>]*>(.*?)</text>', xml, re.DOTALL)
        clean_texts = []
        for t in texts:
            clean = re.sub(r'<[^>]+>', '', t)
            clean = clean.replace("&amp;", "&").replace("&#39;", "'")
            clean = clean.replace("&quot;", '"').replace("&lt;", "<").replace("&gt;", ">")
            if clean.strip():
                clean_texts.append(clean.strip())

        return " ".join(clean_texts[:500])
    except Exception as e:
        return "Error procesando transcripcion: {}".format(str(e)[:60])


def _get_video_metadata(video_id: str) -> dict:
    try:
        page_url = "https://www.youtube.com/watch?v={}".format(video_id)
        req = urllib.request.Request(page_url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "es-ES,es;q=0.9",
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

        info = {}
        json_match = re.search(r'var ytInitialPlayerResponse\s*=\s*(\{.*?\});\s*</script>', html, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(1))
            vd = data.get("videoDetails", {})
            info["title"] = vd.get("title", "")
            info["channel"] = vd.get("author", "")
            info["views"] = vd.get("viewCount", "")
            info["duration"] = "{}s".format(vd.get("lengthSeconds", ""))
            info["description"] = vd.get("shortDescription", "")[:1000]

        micro = re.search(r'"dateText":\s*\{"simpleText":\s*"([^"]+)"', html)
        if micro:
            info["date"] = micro.group(1)
        likes = re.search(r'"label":\s*"([\d,]+)\s*likes"', html)
        if likes:
            info["likes"] = likes.group(1)

        return info
    except Exception:
        return {}


def _generate_summary(text: str, max_chars: int = 2000) -> str:
    if not text:
        return "Sin contenido para resumir"

    sentences = re.split(r'(?<=[.!?])\s+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 15]

    if len(sentences) <= 5:
        return "\n".join(sentences)

    scored = []
    word_freq = {}
    all_words = []
    for s in sentences:
        words = re.findall(r'\b\w{4,}\b', s.lower())
        all_words.extend(words)

    for w in all_words:
        word_freq[w] = word_freq.get(w, 0) + 1

    top_words = sorted(word_freq.items(), key=lambda x: -x[1])[:15]
    important_words = set(w for w, _ in top_words)

    for i, s in enumerate(sentences):
        score = 0
        words = set(re.findall(r'\b\w{4,}\b', s.lower()))
        overlap = words & important_words
        score += len(overlap) * 2

        if i < 3:
            score += 3
        if i >= len(sentences) - 2:
            score += 1

        if any(kw in s.lower() for kw in ["importante", "conclusion", "resumen",
                                           "en resumen", "finalmente", "resultados"]):
            score += 4

        scored.append((score, i, s))

    scored.sort(key=lambda x: -x[0])
    top_sentences = sorted(scored[:max(5, len(sentences) // 3)], key=lambda x: x[1])

    summary = " ".join(s for _, _, s in top_sentences)
    if len(summary) > max_chars:
        summary = summary[:max_chars].rsplit(" ", 1)[0] + "..."

    return summary


def _format_summary(content_type: str, source: str, summary: str, original_len: int) -> str:
    lines = []
    lines.append("═" * 60)
    lines.append("  RESUMEN — {}".format(content_type))
    lines.append("═" * 60)
    lines.append("  Fuente: {}".format(source[:80]))
    lines.append("  Tamano original: {} caracteres".format(original_len))
    lines.append("─" * 60)
    lines.append("")
    lines.append(summary)
    lines.append("")
    lines.append("═" * 60)
    return "\n".join(lines)


def _batch_summarize(text: str, max_chars: int = 1500) -> str:
    urls = re.findall(r'https?://[^\s<>"\']+', text)
    if not urls:
        urls = [u.strip() for u in text.split("\n") if u.strip().startswith("http")]

    if not urls:
        return "Error: no se encontraron URLs en el texto proporcionado"

    results = []
    for url in urls[:5]:
        result = _summarize_url(url, max_chars // len(urls[:5]))
        results.append(result)

    return "\n\n".join(results)


def _search_and_summarize(query: str, max_chars: int = 2000) -> str:
    if not query:
        return "Error: especifica que buscar"

    links = []
    try:
        data = urllib.parse.urlencode({'q': query, 'b': ''}).encode()
        req = urllib.request.Request('https://lite.duckduckgo.com/lite/', data=data, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Content-Type': 'application/x-www-form-urlencoded',
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode('utf-8', errors='ignore')

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        for a in soup.select('a[href]'):
            href = a.get('href', '')
            if href.startswith('http') and 'duckduckgo' not in href and 'google' not in href:
                text = a.get_text(strip=True)
                if text and len(text) > 10 and href not in links:
                    links.append(href)
                    if len(links) >= 3:
                        break
    except Exception:
        pass

    if not links:
        try:
            url = "https://www.google.com/search?q={}&hl=es&num=3".format(urllib.parse.quote(query))
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            })
            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode("utf-8", errors="ignore")

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")
            for g in soup.select("div.g")[:3]:
                link_el = g.select_one("a")
                if link_el:
                    href = link_el.get("href", "")
                    if href.startswith("/url?"):
                        href = urllib.parse.parse_qs(href.split("?")[1]).get("q", [""])[0]
                    if href.startswith("http") and href not in links:
                        links.append(href)
        except Exception:
            pass

    if not links:
        return "No encontre resultados para '{}'".format(query[:50])

    parts = ["═══ BUSQUEDA Y RESUMEN: '{}' ═══\n".format(query[:50])]
    for i, link in enumerate(links[:3], 1):
        part = _summarize_url(link, max_chars // 3)
        parts.append("--- Resultado {} ---\n{}".format(i, part))

    _log_history("search_and_summarize", query[:80])
    return "\n\n".join(parts)


def _extract_video_id(url: str) -> str:
    patterns = [
        r'(?:v=|/v/|youtu\.be/)([a-zA-Z0-9_-]{11})',
        r'(?:embed/)([a-zA-Z0-9_-]{11})',
        r'^([a-zA-Z0-9_-]{11})$',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return ""


def _log_history(action: str, target: str):
    history = _load_history()
    history.append({
        "action": action,
        "target": target[:100],
        "time": datetime.now().isoformat(),
    })
    if len(history) > 100:
        history = history[-100:]
    _save_history(history)


def _load_history() -> list:
    if _HISTORY_FILE.exists():
        try:
            return json.loads(_HISTORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def _save_history(history: list):
    _HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    _HISTORY_FILE.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")


def _get_history() -> str:
    history = _load_history()
    if not history:
        return "Sin historial de resumenes"
    lines = ["═══ HISTORIAL DE RESUMENES ═══", ""]
    for h in history[-10:]:
        lines.append("  [{}] {} -> {}".format(
            h.get("time", "?")[:16],
            h.get("action", "?"),
            h.get("target", "?")[:60]))
    return "\n".join(lines)
