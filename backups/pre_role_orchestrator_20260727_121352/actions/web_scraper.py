"""
actions/web_scraper.py — Advanced web scraping for ERIS.
Uses requests + BeautifulSoup, with optional Playwright for JS-rendered pages.
"""
import json
import os
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

_BASE = Path(__file__).resolve().parent.parent
_HISTORY_FILE = _BASE / "data" / "scrape_history.json"

def _load_history():
    if _HISTORY_FILE.exists():
        try:
            return json.loads(_HISTORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"scrapes": []}

def _save_history(data):
    _HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    _HISTORY_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def web_scraper(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = params.get("action", "status").lower()

    if action == "status":
        data = _load_history()
        return (
            f"Web Scraper Status:\n"
            f"  Total scrapes: {len(data.get('scrapes', []))}\n"
            f"  Backends: requests+bs4, playwright (optional)"
        )

    elif action == "fetch":
        url = params.get("url", "")
        if not url:
            return "Requires 'url'."
        return _fetch_url(url, params)

    elif action == "extract":
        url = params.get("url", "")
        selector = params.get("selector", "")
        if not url:
            return "Requires 'url'."
        return _extract_content(url, selector, params)

    elif action == "links":
        url = params.get("url", "")
        if not url:
            return "Requires 'url'."
        return _extract_links(url)

    elif action == "images":
        url = params.get("url", "")
        if not url:
            return "Requires 'url'."
        return _extract_images(url)

    elif action == "text":
        url = params.get("url", "")
        if not url:
            return "Requires 'url'."
        return _extract_text(url, params)

    elif action == "metadata":
        url = params.get("url", "")
        if not url:
            return "Requires 'url'."
        return _extract_metadata(url)

    elif action == "search":
        query = params.get("query", "")
        if not query:
            return "Requires 'query'."
        return _search(query, params)

    elif action == "batch":
        urls = params.get("urls", [])
        if not urls:
            return "Requires 'urls' list."
        return _batch_fetch(urls, params)

    elif action == "history":
        data = _load_history()
        scrapes = data.get("scrapes", [])
        if not scrapes:
            return "No scrape history."
        lines = [f"Scrape History ({len(scrapes)}):"]
        for s in scrapes[-10:]:
            lines.append(f"  [{s['timestamp'][:16]}] {s.get('url', '?')[:50]} ({s.get('status', '?')})")
        return "\n".join(lines)

    elif action == "js_render":
        url = params.get("url", "")
        if not url:
            return "Requires 'url'."
        return _js_render(url, params)

    return "Actions: status, fetch, extract, links, images, text, metadata, search, batch, history, js_render"


def _fetch_url(url, params):
    try:
        import requests
        timeout = int(params.get("timeout", 10))
        headers = {"User-Agent": "ERIS-WebScraper/2.0"}
        resp = requests.get(url, timeout=timeout, headers=headers, allow_redirects=True)
        content_type = resp.headers.get("Content-Type", "")

        result = {
            "url": url,
            "status": resp.status_code,
            "content_type": content_type,
            "size": len(resp.content),
            "encoding": resp.encoding,
            "headers": dict(resp.headers),
        }

        _record_scrape(url, resp.status_code)

        if "json" in content_type:
            try:
                result["json"] = resp.json()
            except Exception:
                pass

        if params.get("save"):
            save_path = Path(_BASE) / "data" / "scrapes" / f"{urlparse(url).netloc}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            save_path.parent.mkdir(parents=True, exist_ok=True)
            save_path.write_bytes(resp.content)
            result["saved_to"] = str(save_path)

        return json.dumps(result, indent=2, ensure_ascii=False, default=str)
    except ImportError:
        return "requests not installed. Install with: pip install requests"
    except Exception as e:
        return f"Fetch error: {e}"


def _extract_content(url, selector, params):
    try:
        import requests
        from bs4 import BeautifulSoup

        resp = requests.get(url, timeout=10, headers={"User-Agent": "ERIS-WebScraper/2.0"})
        soup = BeautifulSoup(resp.text, "html.parser")

        if selector:
            elements = soup.select(selector)
            if not elements:
                return f"No elements found for selector: {selector}"
            results = []
            for el in elements[:50]:
                results.append({
                    "tag": el.name,
                    "text": el.get_text(strip=True)[:200],
                    "attrs": dict(el.attrs),
                })
            return json.dumps(results, indent=2, ensure_ascii=False)
        else:
            title = soup.title.string if soup.title else "No title"
            meta = {}
            for m in soup.find_all("meta"):
                name = m.get("name") or m.get("property", "")
                content = m.get("content", "")
                if name and content:
                    meta[name] = content[:100]

            return json.dumps({"title": title, "meta": meta, "text_length": len(soup.get_text())}, indent=2)
    except ImportError:
        return "requests/beautifulsoup4 not installed. pip install requests beautifulsoup4"
    except Exception as e:
        return f"Extract error: {e}"


def _extract_links(url):
    try:
        import requests
        from bs4 import BeautifulSoup

        resp = requests.get(url, timeout=10, headers={"User-Agent": "ERIS-WebScraper/2.0"})
        soup = BeautifulSoup(resp.text, "html.parser")
        base_domain = urlparse(url).netloc

        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            full_url = urljoin(url, href)
            is_internal = urlparse(full_url).netloc == base_domain
            links.append({
                "url": full_url[:200],
                "text": a.get_text(strip=True)[:100],
                "internal": is_internal,
            })

        internal = [l for l in links if l["internal"]]
        external = [l for l in links if not l["internal"]]
        return json.dumps({
            "total": len(links),
            "internal": len(internal),
            "external": len(external),
            "links": links[:50],
        }, indent=2, ensure_ascii=False)
    except ImportError:
        return "requests/beautifulsoup4 not installed."
    except Exception as e:
        return f"Links error: {e}"


def _extract_images(url):
    try:
        import requests
        from bs4 import BeautifulSoup

        resp = requests.get(url, timeout=10, headers={"User-Agent": "ERIS-WebScraper/2.0"})
        soup = BeautifulSoup(resp.text, "html.parser")

        images = []
        for img in soup.find_all("img"):
            src = img.get("src", "")
            if src:
                full_url = urljoin(url, src)
                images.append({
                    "url": full_url[:200],
                    "alt": img.get("alt", "")[:100],
                    "width": img.get("width", ""),
                    "height": img.get("height", ""),
                })

        return json.dumps({"total": len(images), "images": images[:30]}, indent=2, ensure_ascii=False)
    except ImportError:
        return "requests/beautifulsoup4 not installed."
    except Exception as e:
        return f"Images error: {e}"


def _extract_text(url, params):
    try:
        import requests
        from bs4 import BeautifulSoup

        resp = requests.get(url, timeout=10, headers={"User-Agent": "ERIS-WebScraper/2.0"})
        soup = BeautifulSoup(resp.text, "html.parser")

        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        text = soup.get_text(separator="\n", strip=True)
        max_chars = int(params.get("max_chars", 2000))

        if len(text) > max_chars:
            text = text[:max_chars] + "\n... [truncated]"

        return text
    except ImportError:
        return "requests/beautifulsoup4 not installed."
    except Exception as e:
        return f"Text extraction error: {e}"


def _extract_metadata(url):
    try:
        import requests
        from bs4 import BeautifulSoup

        resp = requests.get(url, timeout=10, headers={"User-Agent": "ERIS-WebScraper/2.0"})
        soup = BeautifulSoup(resp.text, "html.parser")

        meta = {
            "url": url,
            "title": soup.title.string.strip() if soup.title and soup.title.string else "",
            "description": "",
            "keywords": "",
            "og_title": "",
            "og_description": "",
            "og_image": "",
            "canonical": "",
            "status_code": resp.status_code,
            "content_length": len(resp.content),
        }

        for m in soup.find_all("meta"):
            name = (m.get("name") or m.get("property", "")).lower()
            content = m.get("content", "")
            if name == "description":
                meta["description"] = content
            elif name == "keywords":
                meta["keywords"] = content
            elif name == "og:title":
                meta["og_title"] = content
            elif name == "og:description":
                meta["og_description"] = content
            elif name == "og:image":
                meta["og_image"] = content

        canonical = soup.find("link", rel="canonical")
        if canonical:
            meta["canonical"] = canonical.get("href", "")

        return json.dumps(meta, indent=2, ensure_ascii=False)
    except ImportError:
        return "requests/beautifulsoup4 not installed."
    except Exception as e:
        return f"Metadata error: {e}"


def _search(query, params):
    try:
        import requests
        from bs4 import BeautifulSoup

        num = int(params.get("num", 5))
        search_url = f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}"
        resp = requests.get(search_url, timeout=10, headers={"User-Agent": "ERIS-WebScraper/2.0"})
        soup = BeautifulSoup(resp.text, "html.parser")

        results = []
        for r in soup.find_all("div", class_="result")[:num]:
            title_el = r.find("a", class_="result__a")
            snippet_el = r.find("a", class_="result__snippet")
            if title_el:
                results.append({
                    "title": title_el.get_text(strip=True)[:100],
                    "url": title_el.get("href", "")[:200],
                    "snippet": snippet_el.get_text(strip=True)[:200] if snippet_el else "",
                })

        return json.dumps({"query": query, "results": results}, indent=2, ensure_ascii=False)
    except ImportError:
        return "requests/beautifulsoup4 not installed."
    except Exception as e:
        return f"Search error: {e}"


def _batch_fetch(urls, params):
    results = []
    for url in urls[:10]:
        try:
            import requests
            resp = requests.get(url, timeout=10, headers={"User-Agent": "ERIS-WebScraper/2.0"})
            results.append({"url": url, "status": resp.status_code, "size": len(resp.content)})
        except Exception as e:
            results.append({"url": url, "error": str(e)[:60]})
    return json.dumps(results, indent=2, ensure_ascii=False)


def _js_render(url, params):
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=int(params.get("timeout", 30)) * 1000)
            page.wait_for_load_state("networkidle")

            content = page.content()
            title = page.title()
            text = page.inner_text("body")
            browser.close()

            max_chars = int(params.get("max_chars", 3000))
            if len(text) > max_chars:
                text = text[:max_chars] + "\n... [truncated]"

            return json.dumps({
                "url": url,
                "title": title,
                "text": text,
                "html_length": len(content),
            }, indent=2, ensure_ascii=False)
    except ImportError:
        return "Playwright not installed. Install with: pip install playwright && playwright install chromium"
    except Exception as e:
        return f"JS render error: {e}"


def _record_scrape(url, status):
    data = _load_history()
    data["scrapes"].append({
        "url": url,
        "status": status,
        "timestamp": datetime.now().isoformat(),
    })
    data["scrapes"] = data["scrapes"][-100:]
    _save_history(data)
