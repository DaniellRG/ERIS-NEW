"""
agent_router.py — ERIS Multi-Agent Handoff System.
Routes user intents to specialized agents automatically.
Inspired by OpenAI Agents SDK handoff pattern.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable, Optional

_BASE = Path(__file__).resolve().parent.parent
_REGISTRY_PATH = _BASE / "core" / "agent_registry.json"

# ── Agent definitions ─────────────────────────────────────────────────────────

# Each agent has:
#   name: unique identifier
#   description: what it does (shown to router for classification)
#   keywords: trigger words/phrases for routing
#   tools: list of tool names this agent handles
#   handler: function to call (registered at runtime)

from core.agent_definitions import AGENT_DEFINITIONS


# ── Registry management ───────────────────────────────────────────────────────

def _load_registry() -> dict:
    """Load agent registry from disk."""
    try:
        if _REGISTRY_PATH.exists():
            return json.loads(_REGISTRY_PATH.read_text("utf-8"))
    except Exception:
        pass
    return {"agents": {}, "handoff_count": 0, "last_handoff": None}

def _save_registry(registry: dict):
    """Save agent registry to disk."""
    try:
        _REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
        _REGISTRY_PATH.write_text(json.dumps(registry, indent=2, ensure_ascii=False), "utf-8")
    except Exception as e:
        print(f"[AgentRouter] Registry save error: {e}")

# ── Router ────────────────────────────────────────────────────────────────────

class AgentRouter:
    """Routes user intents to specialized agents."""

    def __init__(self):
        self._handlers: dict[str, Callable] = {}
        self._registry = _load_registry()
        self._register_builtin_agents()

    def _register_builtin_agents(self):
        """Register all builtin agent definitions, REPLACING stale registry
        entries so only declared agents remain (single source of truth)."""
        fresh = {}
        for agent_key, agent_def in AGENT_DEFINITIONS.items():
            fresh[agent_key] = {
                "name": agent_def["name"],
                "description": agent_def["description"],
                "keywords": agent_def["keywords"],
                "tools": agent_def["tools"],
                "enabled": True,
            }
        # keep runtime fields, drop stale/rogue agents not in AGENT_DEFINITIONS
        stale = [k for k in self._registry.get("agents", {}) if k not in fresh]
        if stale:
            print(f"[AgentRouter] Purged {len(stale)} stale agents: {sorted(stale)}")
        self._registry["agents"] = fresh
        _save_registry(self._registry)

    def register_handler(self, agent_key: str, handler: Callable):
        """Register a handler function for an agent."""
        self._handlers[agent_key] = handler
        print(f"[AgentRouter] Registered handler for {agent_key}")

    def classify_intent(self, text: str) -> Optional[str]:
        """
        Classify user text into an agent key using weighted scoring.
        Improvements over pure keyword matching:
        - Multi-word phrases get bonus weight
        - Exact phrase matches scored higher than substring
        - Penalty keywords reduce false positives
        - Recent handoff context prevents agent bouncing
        - Accent normalization (creá → crear)
        Returns None if no agent matches (handled by main ERIS).
        """
        import unicodedata
        def _norm(s):
            nfkd = unicodedata.normalize('NFKD', s)
            return ''.join(c for c in nfkd if not unicodedata.combining(c))

        text_lower = text.lower()
        text_norm = _norm(text_lower)
        scores: dict[str, float] = {}

        for agent_key, agent_info in self._registry.get("agents", {}).items():
            if not agent_info.get("enabled", True):
                continue

            score = 0.0
            for keyword in agent_info.get("keywords", []):
                kw_lower = keyword.lower()
                kw_norm = _norm(kw_lower)
                matched = False
                # Try normalized match first (handles accents: creá → crear)
                if kw_norm in text_norm:
                    matched = True
                elif kw_lower in text_lower:
                    matched = True

                if matched:
                    # Base weight: longer keywords are more specific
                    base = max(len(kw_lower), len(kw_norm))
                    # Bonus for exact word boundary matches (not substring)
                    if f" {kw_norm} " in f" {text_norm} " or text_norm.startswith(kw_norm) or text_norm.endswith(kw_norm):
                        base *= 1.5
                    # Bonus for multi-word phrases (more specific = more reliable)
                    if " " in kw_lower:
                        base *= 2.0
                    score += base

            # Penalty keywords: if present, reduce this agent's score
            for penalty_kw in agent_info.get("penalty_keywords", []):
                pen_norm = _norm(penalty_kw.lower())
                if pen_norm in text_norm or penalty_kw.lower() in text_lower:
                    score *= 0.3

            if score > 0:
                scores[agent_key] = score

        if not scores:
            return None

        # Sort by score descending
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        best_agent, best_score = ranked[0]

        # Minimum threshold
        if best_score < 3:
            return None

        # Disambiguation: if top two are close (within 20%), prefer the one
        # that was NOT used most recently to prevent agent bouncing
        if len(ranked) >= 2:
            second_agent, second_score = ranked[1]
            if second_score >= best_score * 0.8:
                last_agent = self._registry.get("last_handoff", {})
                if isinstance(last_agent, dict) and last_agent.get("agent") == best_agent:
                    # Top agent was used recently, prefer the runner-up
                    return second_agent

        return best_agent

    def route(self, text: str, agent_key: str, **kwargs) -> Any:
        """Route a request to the appropriate agent handler."""
        if agent_key not in self._handlers:
            return f"[AgentRouter] No handler registered for agent: {agent_key}"

        t0 = time.perf_counter()
        try:
            handler = self._handlers[agent_key]
            result = handler(text, **kwargs)

            elapsed = time.perf_counter() - t0

            # Update registry stats
            self._registry["handoff_count"] = self._registry.get("handoff_count", 0) + 1
            self._registry["last_handoff"] = {
                "agent": agent_key,
                "text": text[:100],
                "elapsed": round(elapsed, 2),
                "timestamp": time.time(),
            }
            _save_registry(self._registry)

            print(f"[AgentRouter] Handoff to {agent_key}: {elapsed:.2f}s")
            return result

        except Exception as e:
            print(f"[AgentRouter] Handoff error for {agent_key}: {e}")
            return f"[AgentRouter] Error delegating a {agent_key}: {e}"

    def get_agent_list(self) -> list[dict]:
        """Get list of available agents."""
        agents = []
        for key, info in self._registry.get("agents", {}).items():
            agents.append({
                "key": key,
                "name": info["name"],
                "description": info["description"],
                "enabled": info.get("enabled", True),
                "handler_registered": key in self._handlers,
            })
        return agents

    def get_stats(self) -> dict:
        """Get router statistics."""
        return {
            "handoff_count": self._registry.get("handoff_count", 0),
            "last_handoff": self._registry.get("last_handoff"),
            "agents_available": len(self._registry.get("agents", {})),
            "handlers_registered": len(self._handlers),
        }

    def toggle_agent(self, agent_key: str, enabled: bool) -> str:
        """Enable or disable an agent."""
        if agent_key not in self._registry.get("agents", {}):
            return f"Agente no encontrado: {agent_key}"

        self._registry["agents"][agent_key]["enabled"] = enabled
        _save_registry(self._registry)
        status = "habilitado" if enabled else "deshabilitado"
        return f"Agente {agent_key} {status}."


# ── Singleton ─────────────────────────────────────────────────────────────────

_router: Optional[AgentRouter] = None

def get_router() -> AgentRouter:
    global _router
    if _router is None:
        _router = AgentRouter()
    return _router
