import httpx
import os
import json

CONTEXT7_API_BASE = "https://context7.com/api"

def _get_api_key():
    key = os.getenv("CONTEXT7_API_KEY", "")
    if not key:
        cfg = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "api_keys.json")
        try:
            with open(cfg, "r") as f:
                key = json.load(f).get("context7_api_key", "")
        except Exception:
            pass
    return key

def _headers():
    h = {}
    key = _get_api_key()
    if key:
        h["Authorization"] = f"Bearer {key}"
    return h

async def context7_search(query: str) -> str:
    """Search for libraries in Context7 by name."""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{CONTEXT7_API_BASE}/v2/search",
            params={"query": query, "limit": 5},
            headers=_headers()
        )
        resp.raise_for_status()
        data = resp.json()
    
    libs = data.get("results", [])
    if not libs:
        return f"No libraries found for '{query}'"
    
    lines = [f"Found {len(libs)} libraries:"]
    for lib in libs[:5]:
        lib_id = lib.get("id", "?")
        title = lib.get("title", "?")
        desc = lib.get("description", "")[:80]
        stars = lib.get("stars", 0)
        lines.append(f"- {lib_id}: {title} ({desc}...) [{stars}★]")
    return "\n".join(lines)

async def context7_docs(library_id: str, query: str) -> str:
    """Get documentation context for a library from Context7."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{CONTEXT7_API_BASE}/v2/context",
            params={
                "libraryId": library_id,
                "query": query,
                "type": "txt"
            },
            headers=_headers()
        )
        resp.raise_for_status()
        return resp.text

async def handle_context7(action: str, **kwargs) -> str:
    """Handle Context7 tool calls."""
    try:
        if action == "search":
            query = kwargs.get("query", "")
            if not query:
                return "Error: query is required"
            return await context7_search(query)
        
        elif action == "docs":
            library_id = kwargs.get("library_id", "")
            query = kwargs.get("query", "")
            if not library_id or not query:
                return "Error: library_id and query are required"
            return await context7_docs(library_id, query)
        
        else:
            return f"Unknown action: {action}. Use 'search' or 'docs'"
    
    except httpx.HTTPStatusError as e:
        return f"Context7 API error: {e.response.status_code} - {e.response.text[:200]}"
    except Exception as e:
        return f"Context7 error: {str(e)}"
