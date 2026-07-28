"""
web_search.py — Busqueda web con multiples backends: Google, DuckDuckGo, noticias.
Sin API keys necesarias. Fallback automatico entre motores.
"""
import json
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from datetime import datetime

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_HISTORY_FILE = _DATA_DIR / "search_history.json"


def web_search(parameters: dict, player=None) -> str:
    params = parameters or {}
    query = params.get("query") or params.get("text") or params.get("search") or ""
    num = int(params.get("num_results") or params.get("count") or params.get("items") or 5)
    action = (params.get("action") or "search").lower()
    engine = (params.get("engine") or "auto").lower()

    if player:
        player.write_log("Buscando: {}".format(query[:50]))

    if action == "search" or action == "buscar":
        if engine == "duckduckgo" or engine == "ddg":
            return _search_ddg(query, num)
        elif engine == "google":
            return _search_google(query, num)
        else:
            return _search_auto(query, num)
    elif action == "open" or action == "abrir":
        return _open_url(query)
    elif action == "news" or action == "noticias":
        return _search_news(query, num)
    elif action == "images" or action == "imagenes":
        return _search_images(query, num)
    elif action == "videos":
        return _search_videos_web(query, num)
    elif action == "definition" or action == "definicion":
        return _search_definition(query)
    elif action == "local":
        return _search_local(query)
    elif action == "history":
        return _get_history()
    return (
        "Acciones: search (buscar), news (noticias), images (imagenes), "
        "videos, definition (definicion), local (local), "
        "open (abrir URL), history (historial). "
        "Engines: auto, google, duckduckgo"
    )


def _search_auto(query: str, num: int) -> str:
    result = _search_google(query, num)
    if "Error" in result or "No encontr" in result or "pip install" in result:
        result = _search_ddg(query, num)
    _log_search("auto", query, result)
    return result


def _search_google(query: str, num: int = 5) -> str:
    if not query:
        return "Error: especifica que buscar"
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return "Error: pip install beautifulsoup4"
    url = "https://www.google.com/search?q={}&hl=es&num={}".format(
        urllib.parse.quote(query), num)
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
        results = []
        for g in soup.select("div.g")[:num]:
            title_el = g.select_one("h3")
            link_el = g.select_one("a")
            snippet_el = g.select_one("div.VwiC3b, span.aCOpRe, div[data-sncf]")
            if title_el and link_el:
                title = title_el.get_text(strip=True)
                link = link_el.get("href", "")
                snippet = snippet_el.get_text(strip=True) if snippet_el else ""
                if link.startswith("/url?"):
                    link = urllib.parse.parse_qs(link.split("?")[1]).get("q", [""])[0]
                if link and link.startswith("http"):
                    results.append("**{}**\n{}\n{}".format(title, snippet[:200], link))
        if results:
            return "Resultados para '{}':\n\n{}".format(query, "\n\n".join(results))
        return "No encontre resultados para '{}' (Google)".format(query)
    except Exception as e:
        return "Error en busqueda Google: {}".format(str(e)[:80])


def _search_ddg(query: str, num: int = 5) -> str:
    if not query:
        return "Error: especifica que buscar"
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return "Error: pip install beautifulsoup4"
    url = "https://html.duckduckgo.com/html/?q={}".format(urllib.parse.quote(query))
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        soup = BeautifulSoup(html, "html.parser")
        results = []
        for r in soup.select(".result")[:num]:
            title_el = r.select_one(".result__a")
            snippet_el = r.select_one(".result__snippet")
            if title_el:
                title = title_el.get_text(strip=True)
                link = title_el.get("href", "")
                snippet = snippet_el.get_text(strip=True) if snippet_el else ""
                results.append("**{}**\n{}\n{}".format(title, snippet[:200], link))
        if results:
            return "Resultados para '{}' (DuckDuckGo):\n\n{}".format(query, "\n\n".join(results))
        return "No encontre resultados para '{}' (DuckDuckGo)".format(query)
    except Exception as e:
        return "Error en busqueda DuckDuckGo: {}".format(str(e)[:80])


def _search_news(query: str, num: int = 5) -> str:
    if not query:
        query = "noticias de hoy"
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return "Error: pip install beautifulsoup4"
    url = "https://news.google.com/search?q={}&hl=es".format(urllib.parse.quote(query))
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        soup = BeautifulSoup(html, "html.parser")
        articles = []
        for article in soup.select("article")[:num]:
            title_el = article.select_one("a[href]")
            if title_el:
                title = title_el.get_text(strip=True)
                if title and len(title) > 10:
                    articles.append("  - {}".format(title))
        if articles:
            return "Noticias recientes sobre '{}':\n{}".format(query, "\n".join(articles))
        return "No encontre noticias para '{}'".format(query)
    except Exception as e:
        return "Error buscando noticias: {}".format(str(e)[:60])


def _search_images(query: str, num: int = 5) -> str:
    import webbrowser
    url = "https://www.google.com/search?q={}&tbm=isch&hl=es".format(urllib.parse.quote(query))
    webbrowser.open(url)
    return "Abriendo imagenes de '{}' en el navegador".format(query[:50])


def _search_videos_web(query: str, num: int = 5) -> str:
    import webbrowser
    url = "https://www.google.com/search?q={}&tbm=vid&hl=es".format(urllib.parse.quote(query))
    webbrowser.open(url)
    return "Abriendo videos de '{}' en el navegador".format(query[:50])


def _search_definition(query: str) -> str:
    if not query:
        return "Error: especifica que definir"
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return "Error: pip install beautifulsoup4"
    url = "https://www.google.com/search?q=definicion+de+{}&hl=es".format(urllib.parse.quote(query))
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        soup = BeautifulSoup(html, "html.parser")
        definition_div = soup.select_one("div.kb0PBd, div[data-attrid='wa:/description']")
        if definition_div:
            return "Definicion de '{}':\n{}".format(query, definition_div.get_text(strip=True)[:500])
        for g in soup.select("div.g")[:2]:
            snippet = g.select_one("div.VwiC3b, span.aCOpRe")
            if snippet:
                return "Info sobre '{}':\n{}".format(query, snippet.get_text(strip=True)[:500])
        return "No encontre definicion para '{}'".format(query)
    except Exception as e:
        return "Error: {}".format(str(e)[:60])


def _search_local(query: str) -> str:
    import webbrowser
    url = "https://www.google.com/maps/search/{}/".format(urllib.parse.quote(query))
    webbrowser.open(url)
    return "Buscando '{}' en Google Maps".format(query[:50])


def _open_url(url: str) -> str:
    if not url:
        return "Error: especifica la URL"
    if not url.startswith("http"):
        url = "https://" + url
    try:
        import webbrowser
        webbrowser.open(url)
        return "Abriendo: {}".format(url[:80])
    except Exception as e:
        return "Error abriendo URL: {}".format(str(e)[:50])


def _log_search(engine: str, query: str, result: str):
    history = _load_history()
    history.append({
        "engine": engine,
        "query": query[:80],
        "result_preview": result[:100],
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
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    _HISTORY_FILE.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")


def _get_history() -> str:
    history = _load_history()
    if not history:
        return "Sin historial de busquedas"
    lines = ["═══ HISTORIAL DE BUSQUEDAS ═══", ""]
    for h in history[-10:]:
        lines.append("  [{}] ({}) '{}'".format(
            h.get("time", "?")[:16],
            h.get("engine", "?"),
            h.get("query", "?")[:50]))
    return "\n".join(lines)
