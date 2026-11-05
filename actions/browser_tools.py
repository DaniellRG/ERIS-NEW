"""Browser automation tools for Eris using browser-use."""

import asyncio
import json
import os
from pathlib import Path
from core.platform import safe_print


def _get_llm():
    """Get LLM for browser-use. Prefers Gemini (already configured in Eris)."""
    try:
        from browser_use.llm import ChatGoogle
        import json
        cfg = json.loads((Path(__file__).parent.parent / "config" / "api_keys.json").read_text())
        api_key = cfg.get("gemini_api_key", "")
        if api_key:
            return ChatGoogle(model="gemini-3.8-flash", api_key=api_key)
    except Exception as e:
        safe_print(f"[BROWSER] ChatGoogle init error: {e}")

    # Fallback to OpenAI if available
    try:
        from browser_use.llm import ChatOpenAI
        import os
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if api_key:
            return ChatOpenAI(model="gpt-4o-mini", api_key=api_key)
    except Exception:
        pass

    return None


async def browse_url(url: str, task: str = "") -> str:
    """Navigate to a URL and extract/summarize content."""
    try:
        from browser_use import Agent

        llm = _get_llm()
        if llm is None:
            return "Error: No LLM configured. Set gemini_api_key in config/api_keys.json"

        agent_task = task or f"Go to {url} and summarize the page content in Spanish"
        agent = Agent(task=agent_task, llm=llm)
        result = await agent.run()
        return str(result)[:3000]
    except Exception as e:
        safe_print(f"[BROWSER] Error: {e}")
        return f"Error browsing {url}: {str(e)[:300]}"


async def search_web(query: str) -> str:
    """Search the web and return results."""
    try:
        from browser_use import Agent

        llm = _get_llm()
        if llm is None:
            return "Error: No LLM configured. Set gemini_api_key in config/api_keys.json"

        agent_task = f"Search the web for: {query}. Return the top 5 results with titles and URLs."
        agent = Agent(task=agent_task, llm=llm)
        result = await agent.run()
        return str(result)[:3000]
    except Exception as e:
        safe_print(f"[BROWSER] Search error: {e}")
        return f"Error searching: {str(e)[:300]}"


def browse_url_sync(url: str, task: str = "") -> str:
    """Synchronous wrapper for browse_url."""
    try:
        return asyncio.run(browse_url(url, task))
    except Exception as e:
        return f"Error: {str(e)[:300]}"


def search_web_sync(query: str) -> str:
    """Synchronous wrapper for search_web."""
    try:
        return asyncio.run(search_web(query))
    except Exception as e:
        return f"Error: {str(e)[:300]}"
