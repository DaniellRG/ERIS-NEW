import json
import os
import re
import hashlib
import time
from urllib.parse import quote_plus, urljoin, urlparse
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

HISTORY_PATH = Path("D:/Eris_Source/data/browser_history.json")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
}
DOWNLOAD_DIR = Path("D:/Eris_Source/data/downloads")


def _load_history():
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    if HISTORY_PATH.exists():
        with open(HISTORY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _save_history(history):
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def _add_history(url, title=""):
    history = _load_history()
    entry = {
        "url": url,
        "title": title,
        "timestamp": datetime.now().isoformat()
    }
    history.append(entry)
    if len(history) > 500:
        history = history[-500:]
    _save_history(history)
    return entry


def _get_soup(url):
    resp = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser"), resp.text, resp.url


def smart_browser(parameters: dict, player=None) -> str:
    action = parameters.get("action", "open")

    if action == "open":
        url = parameters.get("url", "")
        if not url:
            return "Error: No URL provided."
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        try:
            soup, raw, final_url = _get_soup(url)
            title = soup.title.string.strip() if soup.title and soup.title.string else final_url
            _add_history(final_url, title)
            text = soup.get_text(separator="\n", strip=True)
            lines = [l for l in text.split("\n") if l.strip()]
            preview = "\n".join(lines[:50])
            return f"Opened: {title}\nURL: {final_url}\n\n--- Page Preview (first 50 lines) ---\n{preview}"
        except Exception as e:
            return f"Error opening URL: {e}"

    elif action == "search":
        query = parameters.get("query", "")
        if not query:
            return "Error: No search query provided."
        url = f"https://www.google.com/search?q={quote_plus(query)}"
        try:
            soup, _, final_url = _get_soup(url)
            _add_history(final_url, f"Search: {query}")
            results = []
            for g in soup.select("div.g, div[data-sokoban-container]"):
                title_el = g.select_one("h3")
                link_el = g.select_one("a[href]")
                snippet_el = g.select_one("div[data-sncf], span.aCOpRe, div.VwiC3b")
                if title_el and link_el:
                    t = title_el.get_text(strip=True)
                    h = link_el["href"]
                    s = snippet_el.get_text(strip=True) if snippet_el else ""
                    results.append(f"• {t}\n  {h}\n  {s}")
                if len(results) >= 8:
                    break
            if not results:
                text = soup.get_text(separator="\n", strip=True)
                lines = [l for l in text.split("\n") if l.strip()]
                return f"Search: {query}\n\n" + "\n".join(lines[:30])
            return f"Search results for: {query}\n\n" + "\n\n".join(results)
        except Exception as e:
            return f"Error searching: {e}"

    elif action == "click":
        url = parameters.get("url", "")
        text = parameters.get("text", "")
        if not url:
            return "Error: No URL provided for click."
        try:
            soup, _, final_url = _get_soup(url)
            if text:
                for a in soup.find_all("a", href=True):
                    if text.lower() in a.get_text(strip=True).lower():
                        target = urljoin(final_url, a["href"])
                        _add_history(target, a.get_text(strip=True))
                        return f"Clicked: {a.get_text(strip=True)}\nURL: {target}"
                return f"No link found with text: {text}"
            return "Error: Provide 'text' parameter to click a link."
        except Exception as e:
            return f"Error clicking: {e}"

    elif action == "fill":
        return (
            "Note: Form filling requires browser interaction (Selenium/Playwright). "
            "With requests+bs4, you can submit forms using the 'submit_form' action "
            "by providing form field values."
        )

    elif action == "download":
        url = parameters.get("url", "")
        if not url:
            return "Error: No URL provided for download."
        try:
            DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
            resp = requests.get(url, headers=HEADERS, timeout=30, stream=True)
            resp.raise_for_status()
            cd = resp.headers.get("Content-Disposition", "")
            filename = ""
            if "filename=" in cd:
                filename = cd.split("filename=")[-1].strip('" ')
            if not filename:
                filename = hashlib.md5(url.encode()).hexdigest()[:12]
                ext = urlparse(url).path.split(".")[-1]
                if ext and len(ext) < 8:
                    filename += "." + ext
            filepath = DOWNLOAD_DIR / filename
            with open(filepath, "wb") as f:
                for chunk in resp.iter_content(8192):
                    f.write(chunk)
            size = os.path.getsize(filepath)
            return f"Downloaded: {filename}\nSize: {size:,} bytes\nSaved to: {filepath}"
        except Exception as e:
            return f"Error downloading: {e}"

    elif action == "screenshot":
        return (
            "Screenshot capture requires a browser engine (Selenium/Playwright). "
            "Alternative: use smart_browser(action='open', url=...) to get page text content."
        )

    elif action == "extract_text":
        url = parameters.get("url", "")
        if not url:
            return "Error: No URL provided."
        try:
            soup, _, final_url = _get_soup(url)
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            text = soup.get_text(separator="\n", strip=True)
            lines = [l for l in text.split("\n") if l.strip()]
            return "\n".join(lines[:200])
        except Exception as e:
            return f"Error extracting text: {e}"

    elif action == "extract_links":
        url = parameters.get("url", "")
        if not url:
            return "Error: No URL provided."
        try:
            soup, _, final_url = _get_soup(url)
            links = []
            for a in soup.find_all("a", href=True):
                href = a["href"]
                text = a.get_text(strip=True) or "(no text)"
                if href.startswith(("http://", "https://")):
                    links.append(f"• {text}\n  {href}")
            if not links:
                return "No links found on page."
            return f"Links found: {len(links)}\n\n" + "\n\n".join(links[:60])
        except Exception as e:
            return f"Error extracting links: {e}"

    elif action == "submit_form":
        url = parameters.get("url", "")
        form_data = parameters.get("data", {})
        method = parameters.get("method", "POST").upper()
        if not url:
            return "Error: No URL provided."
        try:
            if method == "GET":
                resp = requests.get(url, params=form_data, headers=HEADERS, timeout=15)
            else:
                resp = requests.post(url, data=form_data, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            _add_history(resp.url, f"Form submit -> {resp.url}")
            text = soup.get_text(separator="\n", strip=True)
            lines = [l for l in text.split("\n") if l.strip()]
            return f"Form submitted to: {resp.url}\nStatus: {resp.status_code}\n\n" + "\n".join(lines[:50])
        except Exception as e:
            return f"Error submitting form: {e}"

    elif action == "history":
        history = _load_history()
        if not history:
            return "No browsing history yet."
        recent = history[-20:]
        lines = []
        for i, h in enumerate(recent, 1):
            lines.append(f"{i}. [{h['timestamp'][:19]}] {h.get('title', '')}\n   {h['url']}")
        return f"Browsing history ({len(history)} total, showing last {len(recent)}):\n\n" + "\n\n".join(lines)

    return f"Unknown action: {action}. Available: open, search, click, fill, download, screenshot, extract_text, extract_links, submit_form, history"
