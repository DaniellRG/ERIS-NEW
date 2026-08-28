"""deep_research.py — Busqueda profunda: busca, extrae contenido, analiza calidad y rankea resultados.

ERIS busca en la web, entra a cada pagina, extrae su contenido,
pide a Gemini que evalué la calidad/completitud/pertinencia de la informacion,
y devuelve un ranking con el mejor resultado.
"""
import json
import urllib.request
import urllib.parse
import urllib.error
import re
from pathlib import Path
from datetime import datetime

_BASE = Path(__file__).resolve().parent.parent
_DATA_DIR = _BASE / "data"
_HISTORY_FILE = _DATA_DIR / "deep_research_history.json"

# ── helpers ──

def _fetch_page(url: str, timeout: int = 15) -> str:
    """Fetch a URL and extract clean text content."""
    if not url.startswith("http"):
        url = "https://" + url
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except Exception:
        return ""
    import html as html_mod
    text = html_mod.unescape(raw)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
    text = re.sub(r'<nav[^>]*>.*?</nav>', '', text, flags=re.DOTALL)
    text = re.sub(r'<footer[^>]*>.*?</footer>', '', text, flags=re.DOTALL)
    text = re.sub(r'<header[^>]*>.*?</header>', '', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:6000]


def _search_web(query: str, num: int = 8) -> list:
    """Search via DuckDuckGo HTML scraping. Returns list of {title, snippet, url}."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return []
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
                # Extract actual URL from DuckDuckGo redirect
                if link and "uddg=" in link:
                    from urllib.parse import parse_qs, urlparse
                    parsed = urlparse(link)
                    qs = parse_qs(parsed.query)
                    link = qs.get("uddg", [""])[0]
                if link and link.startswith("http"):
                    results.append({"title": title, "snippet": snippet[:300], "url": link})
        return results
    except Exception:
        return []


def _analyze_with_gemini(content: str, title: str, url: str, query: str) -> dict:
    """Ask Gemini to evaluate page content quality and relevance.
    Falls back to heuristic scoring if Gemini is unavailable."""
    try:
        from google import genai
        from core.audio_config import get_api_key
        api_key = get_api_key()
        client = genai.Client(api_key=api_key)

        prompt = (
            "Eres un investigador experto evaluando la calidad de una pagina web. "
            "Analiza el siguiente contenido y devuelve SOLO un JSON valido con estos campos:\n"
            "- score: numero del 0 al 10 (que tan buena es la informacion)\n"
            "- relevance: numero del 0 al 10 (que tan relevante es para el tema)\n"
            "- completeness: numero del 0 al 10 (que tan completa esta la informacion)\n"
            "- verdict: texto corto explicando por que esta pagina es buena o mala\n"
            "- best_for: para que tipo de consulta es mejor esta pagina\n\n"
            "Tema buscado: {}\n"
            "Titulo de la pagina: {}\n"
            "URL: {}\n\n"
            "Contenido:\n{}"
        ).format(query, title, url, content[:4000])

        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt,
        )
        text = response.text.strip()
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        return json.loads(text)
    except Exception as e:
        err_str = str(e)
        # Fallback heuristic scoring
        word_count = len(content.split())
        query_words = set(query.lower().split())
        content_lower = content.lower()
        matches = sum(1 for w in query_words if w in content_lower)
        relevance = min(10, matches * 3 + 2)
        completeness = min(10, word_count // 200) if word_count > 0 else 1
        score = (relevance + completeness) / 2
        if word_count < 100:
            verdict = "Pagina muy corta, poca informacion sustancial."
        elif completeness >= 7:
            verdict = "Pagina con contenido extenso y detallado."
        elif relevance >= 6:
            verdict = "Informacion relevante pero podria ser mas completa."
        else:
            verdict = "Cobertura basica del tema."
        return {
            "score": round(score, 1),
            "relevance": relevance,
            "completeness": completeness,
            "verdict": "{} (analisis local por limite de API)".format(verdict),
            "best_for": "informacion general" if score >= 5 else "consulta rapida",
        }


def _log_history(query: str, results: list):
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    history = []
    if _HISTORY_FILE.exists():
        try:
            history = json.loads(_HISTORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    history.append({
        "query": query[:80],
        "time": datetime.now().isoformat(),
        "num_results": len(results),
        "best": results[0]["title"] if results else "",
    })
    if len(history) > 50:
        history = history[-50:]
    _HISTORY_FILE.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")


# ── main entry point ──

def deep_research(parameters: dict, player=None) -> str:
    """Deep web research: search, fetch, analyze, rank."""
    params = parameters or {}
    action = params.get("action", "research").lower()
    query = params.get("query") or params.get("text") or params.get("search") or ""
    num_results = int(params.get("num_results") or params.get("count") or 5)

    if not query and action in ("research", "investigar", "search", "buscar"):
        return "Especifica que quieres investigar con 'query'."

    if action in ("history", "historial"):
        if _HISTORY_FILE.exists():
            history = json.loads(_HISTORY_FILE.read_text(encoding="utf-8"))
            lines = ["═══ HISTORIAL DE INVESTIGACIONES ═══", ""]
            for h in history[-10:]:
                lines.append("  [{}] '{}' -> {}".format(
                    h.get("time", "?")[:16],
                    h.get("query", "?")[:50],
                    h.get("best", "?")[:40]))
            return "\n".join(lines) if len(lines) > 2 else "Sin historial."
        return "Sin historial de investigaciones."

    if action in ("analyze", "analizar"):
        url = params.get("url", "")
        if not url:
            return "Especifica la URL con 'url'."
        if player:
            player.write_log("Analizando pagina: {}".format(url[:60]))
        content = _fetch_page(url)
        title = params.get("title") or url
        analysis = _analyze_with_gemini(content, title, url, query or "analisis general")
        lines = [
            "═══ ANALISIS DE PAGINA ═══",
            "URL: {}".format(url),
            "Score: {}/10 | Relevancia: {}/10 | Completitud: {}/10".format(
                analysis.get("score", "?"),
                analysis.get("relevance", "?"),
                analysis.get("completeness", "?")),
            "Veredicto: {}".format(analysis.get("verdict", "?")),
            "Mejor para: {}".format(analysis.get("best_for", "?")),
        ]
        return "\n".join(lines)

    # ── RESEARCH FLOW ──
    if player:
        player.write_log("Iniciando investigacion: '{}'".format(query[:60]))

    # Step 1: Search
    if player:
        player.write_log("Buscando en la web...")
    results = _search_web(query, num_results + 2)
    if not results:
        return "No se encontraron resultados para '{}'.".format(query)
    if player:
        player.write_log("{} resultados encontrados, analizando contenido...".format(len(results)))

    # Step 2: Fetch and analyze each result
    analyzed = []
    for i, r in enumerate(results):
        if player:
            player.write_log("({}/{}) Analizando: {}".format(i+1, len(results), r["title"][:40]))
        content = _fetch_page(r["url"])
        if len(content) < 100:
            analyzed.append({
                "title": r["title"],
                "url": r["url"],
                "snippet": r["snippet"],
                "score": 3,
                "relevance": 3,
                "completeness": 1,
                "verdict": "Pagina sin contenido sustancial o inaccesible.",
                "best_for": "n/a",
            })
            continue
        analysis = _analyze_with_gemini(content, r["title"], r["url"], query)
        analysis["title"] = r["title"]
        analysis["url"] = r["url"]
        analysis["snippet"] = r["snippet"]
        analyzed.append(analysis)

    # Step 3: Rank by score
    analyzed.sort(key=lambda x: (x.get("score", 0) + x.get("completeness", 0)) / 2, reverse=True)

    _log_history(query, analyzed)

    # Step 4: Build report
    lines = [
        "═══ INVESTIGACION: '{}' ═══".format(query.upper()),
        "",
    ]

    for i, a in enumerate(analyzed):
        score = a.get("score", 0)
        completeness = a.get("completeness", 0)
        avg = (score + completeness) / 2
        bar = "[{}{}]".format("#" * int(avg), " " * (10 - int(avg)))
        lines.append("{}. **{}**  [{:.1f}/10]".format(i+1, a["title"], avg))
        lines.append("   {} {}".format(bar, a.get("url", "")))
        lines.append("   Score: {}  Relevancia: {}  Completitud: {}".format(
            score, a.get("relevance", 0), completeness))
        lines.append("   {}".format(a.get("verdict", "")))
        if a.get("best_for"):
            lines.append("   Mejor para: {}".format(a["best_for"]))
        lines.append("")

    # Best result summary
    best = analyzed[0]
    best_avg = (best.get("score", 0) + best.get("completeness", 0)) / 2
    lines.append("═══ RECOMENDACION ═══")
    lines.append("La mejor pagina es: **{}**".format(best["title"]))
    lines.append("Puntuacion: {:.1f}/10".format(best_avg))
    lines.append("URL: {}".format(best["url"]))
    lines.append("Razon: {}".format(best.get("verdict", "")))

    if len(analyzed) > 1:
        lines.append("")
        lines.append("Alternativas:")
        for a in analyzed[1:3]:
            avg = (a.get("score", 0) + a.get("completeness", 0)) / 2
            if avg >= 5:
                lines.append("  - {} ({:.1f}/10): {}".format(a["title"], avg, a.get("verdict", "")[:80]))

    return "\n".join(lines)
