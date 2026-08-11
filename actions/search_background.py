"""Background Search - busca sin interrumpir al usuario."""
import urllib.request, urllib.error, json

def search_background(parameters: dict, player=None) -> str:
    """Busca en internet SIN abrir navegador, sin molestar."""
    query = parameters.get("query", "")
    if not query:
        return "Necesito 'query' para buscar."

    try:
        # Use DuckDuckGo Instant Answer API (free, no key)
        url = f"https://api.duckduckgo.com/?q={urllib.request.quote(query)}&format=json&no_html=1&skip_disambig=1"
        req = urllib.request.Request(url, headers={"User-Agent": "ERIS/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        
        result = []
        
        # Abstract
        abstract = data.get("Abstract", "")
        if abstract:
            result.append(f"Resumen: {abstract[:500]}")
        
        # Related topics
        related = data.get("RelatedTopics", [])
        if related:
            result.append("\nResultados relacionados:")
            for r in related[:5]:
                if isinstance(r, dict):
                    text = r.get("Text", "")
                    if text:
                        result.append(f"  - {text[:200]}")
        
        if result:
            return "\n".join(result)
        
        # Fallback: busqueda real (DuckDuckGo HTML) en vez de un texto vacio
        try:
            from actions.web_search import _search_ddg
            ddg = _search_ddg(query, 3)
            if ddg and not ddg.startswith("No encontr") and not ddg.startswith("Error"):
                return ddg
        except Exception:
            pass
        return f"Busqueda: '{query}'. No se encontro resumen automatico. Sugiero buscar en Google manualmente."
    
    except Exception as e:
        return f"Error en busqueda: {e}"
