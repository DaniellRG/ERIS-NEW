"""Browser automation tools for Eris using browser-use."""

import asyncio
import json
import os
from core.platform import safe_print


async def browse_url(url: str, task: str = "") -> str:
    """Navigate to a URL and optionally perform a task."""
    try:
        from browser_use import Agent
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        agent = Agent(task=task or f"Go to {url} and summarize the page content", llm=llm)
        result = await agent.run()
        return str(result)[:2000]
    except Exception as e:
        safe_print(f"[BROWSER] Error: {e}")
        return f"Error browsing {url}: {str(e)[:200]}"


async def search_web(query: str) -> str:
    """Search the web and return results."""
    try:
        from browser_use import Agent
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        agent = Agent(task=f"Search the web for: {query}. Return the top 5 results with titles and URLs.", llm=llm)
        result = await agent.run()
        return str(result)[:2000]
    except Exception as e:
        safe_print(f"[BROWSER] Search error: {e}")
        return f"Error searching: {str(e)[:200]}"


def browse_url_sync(url: str, task: str = "") -> str:
    """Synchronous wrapper for browse_url."""
    try:
        return asyncio.run(browse_url(url, task))
    except Exception as e:
        return f"Error: {str(e)[:200]}"


def search_web_sync(query: str) -> str:
    """Synchronous wrapper for search_web."""
    try:
        return asyncio.run(search_web(query))
    except Exception as e:
        return f"Error: {str(e)[:200]}"
