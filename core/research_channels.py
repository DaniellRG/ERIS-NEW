"""
research_channels.py — Canales de investigación externa del motor de barreras.

Reemplaza a los canales `paper_search` / `repo_discovery` que quedaron **sin
módulo** (sus imports caían a `None` en `core/action_imports.py`). Acá SÍ
existen y buscan de verdad, vía DDGS:
  - papers  → arXiv
  - repos   → GitHub
  - web     → general (docs, foros, comandos)

Diseño §5.2b/§8b. Solo **LEEN** la web (investigar es libre); no instalan ni
ejecutan nada — incorporar algo de terceros pasa por validación + prueba
aislada + pre-chequeo de zona.
"""
from __future__ import annotations


def _ddg(query: str, n: int = 5) -> list[dict]:
    """Búsqueda estructurada (best-effort: si no hay red/dep, devuelve [])."""
    if not query:
        return []
    try:
        from ddgs import DDGS
    except ImportError:
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            return []
    try:
        return list(DDGS().text(query, max_results=max(1, min(int(n), 20))))
    except Exception:
        return []


def _normalizar(resultados: list[dict], fuente: str) -> list[dict]:
    out = []
    for r in resultados:
        out.append({
            "titulo": r.get("title") or "",
            "url": r.get("href") or r.get("url") or "",
            "snippet": (r.get("body") or r.get("snippet") or "")[:400],
            "fuente": fuente,
        })
    return out


def buscar_papers(query: str, limite: int = 5) -> list[dict]:
    """Papers de arXiv relacionados con `query`."""
    return _normalizar(_ddg(f"{query} site:arxiv.org", limite), "arxiv.org")


def descubrir_repos(query: str, limite: int = 5) -> list[dict]:
    """Repositorios de GitHub relacionados con `query`."""
    return _normalizar(_ddg(f"{query} site:github.com", limite), "github.com")


def buscar_web(query: str, limite: int = 6) -> list[dict]:
    """Web general (documentación, foros, comandos)."""
    return _normalizar(_ddg(query, limite), "web")


def investigar(query: str, limite: int = 5) -> dict:
    """Reúne papers + repos + web en un solo paquete de fuentes."""
    return {
        "query": query,
        "papers": buscar_papers(query, limite),
        "repos": descubrir_repos(query, limite),
        "web": buscar_web(query, limite),
    }
