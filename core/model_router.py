"""
model_router.py — ERIS AI model routing.

Decides which LLM provider to use for each type of task.
Supports: Gemini, Groq, OpenRouter, Ollama.

Task types:
  conversation  — live voice/text conversation (Gemini Native Audio preferred)
  agent         — multi-step agent tasks (dev_agent, code_helper, agent_task)
  search        — quick text queries (web_search, knowledge_base, etc.)
  vision        — screen_vision, image analysis

Fallback chain on quota/error: Gemini -> Groq -> Cerebras -> OpenRouter -> Ollama.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# ── Config keys ───────────────────────────────────────────────────────────────
_TASK_CFG_KEYS: dict[str, str] = {
    "conversation": "model_for_conversation",
    "agent":        "model_for_agents",
    "search":       "model_for_search",
    "vision":       "model_for_vision",
}

_DEFAULTS: dict[str, str] = {
    "model_for_conversation": "gemini",
    "model_for_agents":       "gemini",
    "model_for_search":       "gemini",
    "model_for_vision":       "gemini",
}

_VALID_PROVIDERS = ("gemini", "groq", "cerebras", "openrouter", "ollama")

# Gemini error strings that indicate quota / billing exhaustion
_QUOTA_ERRORS = (
    "quota",
    "rate limit",
    "resource_exhausted",
    "billing",
    "429",
    "too many requests",
    "you exceeded",
    "free tier",
)

# Auth/blocking errors: provider cannot serve right now -> hard fail & fallback
_HARD_FAIL_ERRORS = (
    "401",
    "402",
    "403",
    "unauthorized",
    "forbidden",
    "invalid api key",
    "authentication",
    "not found",
)

# ── Fallback state ────────────────────────────────────────────────────────────
_gemini_failed = False   # set True on quota error; resets on restart
_groq_failed   = False
_cerebras_failed = False
_openrouter_failed = False


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def _cfg() -> dict:
    try:
        return json.loads(
            (_base_dir() / "config" / "api_keys.json").read_text(encoding="utf-8")
        )
    except Exception:
        return {}


# ── Provider availability ────────────────────────────────────────────────────

def _ollama_reachable(cfg: dict | None = None) -> bool:
    if cfg is None:
        cfg = _cfg()
    if not cfg.get("ollama_enabled", False):
        return False
    try:
        from actions.ollama_provider import is_available
        return is_available()
    except Exception:
        return False


def _groq_available(cfg: dict | None = None) -> bool:
    if cfg is None:
        cfg = _cfg()
    try:
        from actions.groq_provider import is_available as _g_avail
        return _g_avail()
    except Exception:
        return False


def _cerebras_available(cfg: dict | None = None) -> bool:
    if cfg is None:
        cfg = _cfg()
    try:
        from actions.cerebras_provider import is_available as _c_avail
        return _c_avail()
    except Exception:
        return False


def _openrouter_available(cfg: dict | None = None) -> bool:
    if cfg is None:
        cfg = _cfg()
    try:
        from actions.openrouter_provider import is_available as _o_avail
        return _o_avail()
    except Exception:
        return False


# ── Public API ────────────────────────────────────────────────────────────────

def get_model_for(task: str) -> str:
    """
    Return the best available provider for the given task.
    If the configured provider is failing, falls back down the chain:
    gemini -> groq -> openrouter -> ollama.
    """
    global _gemini_failed, _groq_failed, _cerebras_failed, _openrouter_failed
    cfg = _cfg()

    # Check user's configured preference
    key          = _TASK_CFG_KEYS.get(task, "model_for_conversation")
    configured   = cfg.get(key, _DEFAULTS.get(key, "gemini"))

    # Build fallback chain starting from configured provider
    chain = ["gemini", "groq", "cerebras", "openrouter", "ollama"]
    try:
        start_idx = chain.index(configured)
    except ValueError:
        start_idx = 0
    chain = chain[start_idx:]

    for provider in chain:
        if provider == "gemini" and not _gemini_failed and _cfg().get("gemini_api_key", ""):
            return "gemini"
        if provider == "groq" and not _groq_failed and _groq_available(cfg):
            return "groq"
        if provider == "cerebras" and not _cerebras_failed and _cerebras_available(cfg):
            return "cerebras"
        if provider == "openrouter" and not _openrouter_failed and _openrouter_available(cfg):
            return "openrouter"
        if provider == "ollama" and _ollama_reachable(cfg):
            return "ollama"

    # Nothing works — return configured provider so caller gets a clear error
    return configured


def gemini_ok() -> bool:
    """True if Gemini API key is configured and no quota error has been seen."""
    global _gemini_failed
    return bool(_cfg().get("gemini_api_key", "")) and not _gemini_failed


def ollama_ok() -> bool:
    """True if Ollama is enabled and reachable."""
    return _ollama_reachable()


def report_gemini_error(error_text: str) -> bool:
    """
    Call this when a Gemini API call fails.
    Returns True if the error looks like a quota/billing issue.
    """
    global _gemini_failed
    et = str(error_text).lower()
    if any(kw in et for kw in _QUOTA_ERRORS) or any(kw in et for kw in _HARD_FAIL_ERRORS):
        _gemini_failed = True
        print(f"[ModelRouter] Gemini quota/auth error — fallback to next provider")
        return True
    return False


def report_provider_error(provider: str, error_text: str) -> bool:
    """
    Mark a provider as failed (quota/auth) so fallback chain activates.
    Returns True if the error looks like a quota issue.
    """
    global _gemini_failed, _groq_failed, _cerebras_failed, _openrouter_failed
    et = str(error_text).lower()
    is_quota = any(kw in et for kw in _QUOTA_ERRORS)
    is_hard = any(kw in et for kw in _HARD_FAIL_ERRORS)

    if provider == "groq" and (is_quota or is_hard):
        _groq_failed = True
        print(f"[ModelRouter] Groq quota/auth error — fallback to next provider")
        return True
    if provider == "cerebras" and (is_quota or is_hard):
        _cerebras_failed = True
        print(f"[ModelRouter] Cerebras quota/auth error — fallback to next provider")
        return True
    if provider == "openrouter" and (is_quota or is_hard):
        _openrouter_failed = True
        print(f"[ModelRouter] OpenRouter quota/auth error — fallback to next provider")
        return True
    return False


def reset_provider_fallbacks():
    """Clear all fallback flags (e.g. when API key is updated)."""
    global _gemini_failed, _groq_failed, _cerebras_failed, _openrouter_failed
    _gemini_failed = False
    _groq_failed = False
    _cerebras_failed = False
    _openrouter_failed = False


def quick_chat(
    prompt: str,
    *,
    system: str = "",
    task: str = "agent",
) -> str:
    """
    Fire a one-shot text completion using the best available provider.
    Follows the fallback chain on failure.
    Raises on total failure (no provider available).
    """
    provider = get_model_for(task)

    if provider == "gemini":
        return _quick_gemini(prompt, system=system)

    if provider == "groq":
        try:
            from actions.groq_provider import chat as _groq_chat
            return _groq_chat(prompt, system=system)
        except Exception as e:
            if report_provider_error("groq", str(e)):
                print(f"[ModelRouter] Groq quota error, falling back: {e}")
                return quick_chat(prompt, system=system, task=task)
            raise

    if provider == "cerebras":
        try:
            from actions.cerebras_provider import chat as _cerebras_chat
            return _cerebras_chat(prompt, system=system)
        except Exception as e:
            if report_provider_error("cerebras", str(e)):
                print(f"[ModelRouter] Cerebras quota error, falling back: {e}")
                return quick_chat(prompt, system=system, task=task)
            raise

    if provider == "openrouter":
        try:
            from actions.openrouter_provider import chat as _or_chat
            return _or_chat(prompt, system=system)
        except Exception as e:
            if report_provider_error("openrouter", str(e)):
                print(f"[ModelRouter] OpenRouter quota error, falling back: {e}")
                return quick_chat(prompt, system=system, task=task)
            raise

    if provider == "ollama":
        try:
            from actions.ollama_provider import chat as _ollama_chat
            return _ollama_chat(prompt, system=system)
        except Exception as e:
            raise RuntimeError(f"All providers failed. Last error (Ollama): {e}")

    raise RuntimeError(f"No provider available for task '{task}'.")


def _quick_gemini(prompt: str, system: str = "") -> str:
    """One-shot Gemini text completion with fallback to chain on quota error."""
    cfg     = _cfg()
    api_key = cfg.get("gemini_api_key", "")
    if not api_key:
        raise RuntimeError("No Gemini API key configured.")

    try:
        from google import genai as _genai
        client = _genai.Client(api_key=api_key)
        parts  = []
        if system:
            parts.append(system + "\n\n")
        parts.append(prompt)
        from core.model_config import get_model
        resp = client.models.generate_content(
            model=get_model("agent"),
            contents=[{"role": "user", "parts": [{"text": "".join(parts)}]}],
        )
        return resp.text or ""
    except Exception as e:
        if report_gemini_error(str(e)):
            # Recurse — get_model_for will pick next provider
            return quick_chat(prompt, system=system, task="agent")
        raise


def status(parameters: dict = None, player=None) -> dict:
    """Return current routing status for display in UI."""
    cfg = _cfg()
    return {
        "gemini_configured": bool(cfg.get("gemini_api_key", "")),
        "gemini_failed":     _gemini_failed,
        "groq_available":    _groq_available(cfg),
        "groq_failed":       _groq_failed,
        "cerebras_available": _cerebras_available(cfg),
        "cerebras_failed":   _cerebras_failed,
        "openrouter_available": _openrouter_available(cfg),
        "openrouter_failed": _openrouter_failed,
        "ollama_enabled":    cfg.get("ollama_enabled", False),
        "ollama_base_url":   cfg.get("ollama_base_url", "http://localhost:11434"),
        "ollama_reachable":  _ollama_reachable(cfg),
        "model_for_conversation": cfg.get("model_for_conversation", "gemini"),
        "model_for_agents":       cfg.get("model_for_agents",       "gemini"),
        "model_for_search":       cfg.get("model_for_search",       "gemini"),
        "model_for_vision":       cfg.get("model_for_vision",       "gemini"),
        "current_provider":  get_model_for("agent"),
    }
