# -*- coding: utf-8 -*-
"""actions/data_connectors.py — Connectors to external knowledge sources.

Provides actions to search and fetch data from:
- HuggingFace (datasets, models)
- Kaggle (datasets)
- Wikidata (structured knowledge)
- data.gov / datos.gov.co (government open data)
- GitHub (repositories, code)
"""
import json
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def data_connectors(parameters: dict, player=None) -> str:
    action = parameters.get("action", "").lower().strip()

    if not action:
        return "Error: Se requiere 'action' (huggingface, wikidata, github, data_gov, kaggle)."

    if action == "huggingface":
        return _search_huggingface(parameters)
    elif action == "wikidata":
        return _search_wikidata(parameters)
    elif action == "github":
        return _search_github(parameters)
    elif action == "data_gov":
        return _search_data_gov(parameters)
    elif action == "kaggle":
        return _search_kaggle(parameters)
    else:
        return f"Acción '{action}' no reconocida."


def _api_get(url: str, headers: dict = None, timeout: int = 15) -> dict:
    hdrs = {"User-Agent": "ERIS/1.0"}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, headers=hdrs)
    resp = urllib.request.urlopen(req, timeout=timeout)
    return json.loads(resp.read())


def _search_huggingface(params: dict) -> str:
    query = params.get("query", "")
    limit = int(params.get("limit", 5))
    if not query:
        return "Error: Se requiere 'query'."

    url = f"https://huggingface.co/api/models?search={urllib.parse.quote(query)}&limit={limit}"
    try:
        data = _api_get(url)
        if not data:
            return f"No se encontraron modelos para '{query}'."
        lines = [f"Modelos HuggingFace para '{query}' ({len(data)}):"]
        for m in data[:limit]:
            name = m.get("id", "?")
            likes = m.get("likes", 0)
            tags = ", ".join(m.get("tags", [])[:3])
            lines.append(f"  {name} | likes: {likes} | tags: {tags}")
        lines.append("\nPara descargar: huggingface-cli download <model_id>")
        return "\n".join(lines)
    except Exception as e:
        return f"Error consultando HuggingFace: {e}"


def _search_wikidata(params: dict) -> str:
    query = params.get("query", "")
    limit = int(params.get("limit", 5))
    if not query:
        return "Error: Se requiere 'query'."

    sparql = f"""
    SELECT ?item ?itemLabel ?description WHERE {{
      ?item rdfs:label "{query}"@es .
      OPTIONAL {{ ?item schema:description ?description . FILTER(LANG(?description) = "es") }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "es,en" . }}
    }} LIMIT {limit}
    """
    url = "https://query.wikidata.org/sparql"
    params_enc = urllib.parse.urlencode({"query": sparql, "format": "json"})
    try:
        data = _api_get(f"{url}?{params_enc}", headers={"Accept": "application/sparql-results+json"})
        bindings = data.get("results", {}).get("bindings", [])
        if not bindings:
            return f"No se encontró '{query}' en Wikidata."
        lines = [f"Resultados Wikidata para '{query}' ({len(bindings)}):"]
        for b in bindings:
            item = b.get("item", {}).get("value", "?")
            label = b.get("itemLabel", {}).get("value", "?")
            desc = b.get("description", {}).get("value", "sin descripcion")
            lines.append(f"  {label} ({item})")
            lines.append(f"    {desc}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error consultando Wikidata: {e}"


def _search_github(params: dict) -> str:
    query = params.get("query", "")
    limit = int(params.get("limit", 5))
    if not query:
        return "Error: Se requiere 'query'."

    url = f"https://api.github.com/search/repositories?q={urllib.parse.quote(query)}&sort=stars&per_page={limit}"
    try:
        data = _api_get(url)
        items = data.get("items", [])
        if not items:
            return f"No se encontraron repos para '{query}'."
        lines = [f"Repos GitHub para '{query}' ({len(items)}):"]
        for r in items:
            name = r.get("full_name", "?")
            stars = r.get("stargazers_count", 0)
            desc = (r.get("description") or "")[:80]
            lang = r.get("language", "?")
            lines.append(f"  {name} | {stars} stars | {lang}")
            if desc:
                lines.append(f"    {desc}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error consultando GitHub: {e}"


def _search_data_gov(params: dict) -> str:
    query = params.get("query", "")
    limit = int(params.get("limit", 5))
    if not query:
        return "Error: Se requiere 'query'."

    url = f"https://api.data.gov/ed/collegescorecard/v1/schools.json?api_key=DEMO_KEY&school.name={urllib.parse.quote(query)}&per_page={limit}"
    try:
        data = _api_get(url)
        results = data.get("results", [])
        if not results:
            return f"No datasets encontrados en data.gov para '{query}'. Intenta: https://data.gov/search?q={urllib.parse.quote(query)}"
        lines = [f"Resultados data.gov para '{query}' ({len(results)}):"]
        for r in results[:limit]:
            name = r.get("school", {}).get("name", "?")
            lines.append(f"  {name}")
        return "\n".join(lines)
    except Exception as e:
        return f"Busca directamente en: https://data.gov/search?q={urllib.parse.quote(query)}\nError: {e}"


def _search_kaggle(params: dict) -> str:
    query = params.get("query", "")
    if not query:
        return "Error: Se requiere 'query'."
    return (
        f"Kaggle no tiene API publica sin autenticacion. "
        f"Busca manualmente: https://www.kaggle.com/datasets?q={urllib.parse.quote(query)}\n"
        f"O usa: kaggle datasets list -s '{query}' (requiere kaggle CLI + API key)"
    )
