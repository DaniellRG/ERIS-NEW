"""
agents/__init__.py — ERIS Specialized Agents Package.
"""
from agents.vision_agent import handle_vision
from agents.search_agent import handle_search
from agents.security_agent import handle_security
from agents.system_agent import handle_system
from agents.media_agent import handle_media
from agents.productivity_agent import handle_productivity
from agents.dev_agent import handle_dev

__all__ = [
    "handle_vision",
    "handle_search",
    "handle_security",
    "handle_system",
    "handle_media",
    "handle_productivity",
    "handle_dev",
]
