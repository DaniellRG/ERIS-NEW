"""
core/compaction.py — Intelligent context compaction for ERIS.

Monitors context size and applies three layers of compaction:
1. Tool result pruning (cheap, no LLM call)
2. LLM summarization of old turns
3. Emergency truncation

Inspired by OpenCode, Omnigent, and Hermes patterns.
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any

# ── Configuration ──
_DEFAULT_CONTEXT_WINDOW = 1_000_000  # Gemini 2.5 Flash native-audio context
_TRIGGER_PERCENT = 0.70  # Start compacting at 70% usage
_RECENT_WINDOW = 10  # Always keep last N turns verbatim
_SUMMARY_TARGET_RATIO = 0.15  # Summary should be ~15% of compressed content
_TOOL_PRUNE_THRESHOLD = 500  # Prune tool results > 500 chars
_MIN_SUMMARY_TOKENS = 200
_MAX_SUMMARY_TOKENS = 4000

# ── State ──
_compaction_stats = {
    "total_compactions": 0,
    "tool_results_pruned": 0,
    "turns_summarized": 0,
    "tokens_saved": 0,
    "last_compaction_time": None,
}
_lock = threading.Lock()


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token for Spanish/English."""
    return max(1, len(text) // 4)


def _estimate_messages_tokens(messages: list[dict]) -> int:
    """Estimate total tokens in a message list."""
    total = 0
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            total += _estimate_tokens(content)
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, dict):
                    total += _estimate_tokens(str(part.get("text", "")))
                else:
                    total += _estimate_tokens(str(part))
        # Tool calls add overhead
        if msg.get("tool_calls"):
            total += 100 * len(msg["tool_calls"])
    return total


# ── Layer 1: Tool result pruning ──

def _prune_tool_results(messages: list[dict], keep_recent: int = _RECENT_WINDOW) -> tuple[list[dict], int]:
    """Replace old tool result contents with placeholders.

    Returns (pruned_messages, pruned_count).
    """
    if not messages:
        return messages, 0

    result = [m.copy() for m in messages]
    pruned = 0
    boundary = len(result) - keep_recent

    for i in range(boundary):
        msg = result[i]
        # Prune tool results
        if msg.get("role") == "tool":
            content = msg.get("content", "")
            if isinstance(content, str) and len(content) > _TOOL_PRUNE_THRESHOLD:
                result[i] = {**msg, "content": "[tool result pruned — too large]"}
                pruned += 1
        # Prune large assistant messages (keep first 500 chars)
        elif msg.get("role") == "assistant":
            content = msg.get("content", "")
            if isinstance(content, str) and len(content) > 1000:
                result[i] = {**msg, "content": content[:500] + "\n...[truncated]..."}
                pruned += 1

    return result, pruned


# ── Layer 2: LLM Summarization ──

def _build_summary_prompt(messages: list[dict], previous_summary: str | None = None) -> str:
    """Build a prompt for the summarizer."""
    parts = []
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        if isinstance(content, str):
            if len(content) > 500:
                content = content[:400] + "...[truncated]"
            parts.append(f"[{role.upper()}]: {content}")

    conversation = "\n".join(parts)

    if previous_summary:
        return (
            "Actualizá el resumen de la conversación. El resumen anterior es:\n"
            f"{previous_summary}\n\n"
            "Nuevos mensajes:\n"
            f"{conversation}\n\n"
            "Generá un resumen actualizado que incluya:\n"
            "- Objetivo principal del usuario\n"
            "- Decisiones tomadas\n"
            "- Archivos modificados\n"
            "- Estado actual del trabajo\n"
            "- Próximos pasos pendientes\n"
            "Mantenelo conciso (máx 300 palabras)."
        )
    return (
        "Resumí esta conversación de forma concisa. Incluí:\n"
        "- Objetivo principal del usuario\n"
        "- Decisiones tomadas\n"
        "- Archivos modificados\n"
        "- Estado actual del trabajo\n"
        "- Próximos pasos pendientes\n\n"
        f"Conversación:\n{conversation}\n\n"
        "Resumen (máx 300 palabras):"
    )


def _summarize_with_gemini(messages: list[dict], previous_summary: str | None = None) -> str | None:
    """Summarize messages using Gemini API directly (cheap model)."""
    try:
        import google.genai as genai
        from core.config_loader import load_config

        config = load_config()
        api_key = config.get("gemini_api_key", "")
        if not api_key:
            return None

        client = genai.Client(api_key=api_key)
        prompt = _build_summary_prompt(messages, previous_summary)

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )
        return response.text
    except Exception:
        return None


def _summarize(messages: list[dict], previous_summary: str | None = None) -> str | None:
    """Try to summarize messages, return summary or None."""
    return _summarize_with_gemini(messages, previous_summary)


# ── Layer 3: Emergency truncation ──

def _truncate_oldest(messages: list[dict], target_tokens: int) -> list[dict]:
    """Emergency: drop oldest messages until under target."""
    result = list(messages)
    while _estimate_messages_tokens(result) > target_tokens and len(result) > _RECENT_WINDOW + 2:
        # Drop the second message (keep system prompt at index 0)
        result.pop(1)
    return result


# ── Public API ──

class ContextCompactor:
    """Manages context compaction for a conversation."""

    def __init__(self, context_window: int = _DEFAULT_CONTEXT_WINDOW,
                 trigger_percent: float = _TRIGGER_PERCENT,
                 recent_window: int = _RECENT_WINDOW):
        self.context_window = context_window
        self.trigger_tokens = int(context_window * trigger_percent)
        self.recent_window = recent_window
        self._previous_summary: str | None = None
        self._compaction_count = 0

    def should_compact(self, messages: list[dict]) -> bool:
        """Check if compaction is needed."""
        tokens = _estimate_messages_tokens(messages)
        return tokens >= self.trigger_tokens

    def compact(self, messages: list[dict], force: bool = False) -> list[dict]:
        """Apply compaction to messages. Returns compacted messages.

        Layers:
        1. Tool result pruning (always, cheap)
        2. LLM summarization (if still over budget)
        3. Emergency truncation (last resort)
        """
        if not force and not self.should_compact(messages):
            return messages

        budget = int(self.context_window * 0.85)  # Target 85% max

        # ── Layer 1: Prune tool results ──
        working, pruned = _prune_tool_results(messages, self.recent_window)
        l1_tokens = _estimate_messages_tokens(working)

        with _lock:
            _compaction_stats["tool_results_pruned"] += pruned

        if not force and l1_tokens <= budget:
            self._log_compaction(1, pruned, 0, l1_tokens)
            return working

        # ── Layer 2: LLM Summarization ──
        # Split: summarize older turns, keep recent verbatim
        if len(working) > self.recent_window + 2:
            to_summarize = working[1:-self.recent_window]  # Skip system prompt
            recent = working[-self.recent_window:]
            system = [working[0]] if working[0].get("role") == "system" else []

            summary = _summarize(to_summarize, self._previous_summary)
            if summary:
                self._previous_summary = summary
                summary_msg = {"role": "assistant", "content": f"[Resumen de conversación previa]\n{summary}"}
                working = system + [summary_msg] + recent
                self._compaction_count += 1

                with _lock:
                    _compaction_stats["total_compactions"] += 1
                    _compaction_stats["turns_summarized"] += len(to_summarize)
                    _compaction_stats["last_compaction_time"] = time.time()

                l2_tokens = _estimate_messages_tokens(working)
                if l2_tokens <= budget:
                    self._log_compaction(2, pruned, len(to_summarize), l2_tokens)
                    return working

        # ── Layer 3: Emergency truncation ──
        working = _truncate_oldest(working, budget)
        self._log_compaction(3, pruned, 0, _estimate_messages_tokens(working))
        return working

    def _log_compaction(self, layer: int, pruned: int, summarized: int, final_tokens: int):
        """Log compaction results."""
        print(f"[COMPACTION] Layer {layer}: pruned={pruned}, summarized={summarized}, tokens={final_tokens}")

    def get_status(self) -> str:
        """Get compaction status."""
        with _lock:
            stats = _compaction_stats.copy()
        return (
            f"Compaction status:\n"
            f"  Total compactions: {stats['total_compactions']}\n"
            f"  Tool results pruned: {stats['tool_results_pruned']}\n"
            f"  Turns summarized: {stats['turns_summarized']}\n"
            f"  Context window: {self.context_window:,} tokens\n"
            f"  Trigger at: {self.trigger_tokens:,} tokens"
        )


# ── Global instance ──
_compactor: ContextCompactor | None = None


def get_compactor() -> ContextCompactor:
    """Get the global compactor instance."""
    global _compactor
    if _compactor is None:
        _compactor = ContextCompactor()
    return _compactor


# ── Tool handler interface ──

def compaction_status() -> str:
    """Get compaction status."""
    return get_compactor().get_status()


def compaction_compact(messages_json: str) -> str:
    """Manually trigger compaction on a JSON message list."""
    try:
        messages = json.loads(messages_json)
        compactor = get_compactor()
        result = compactor.compact(messages, force=True)
        return f"Compacted: {len(messages)} → {len(result)} messages"
    except Exception as e:
        return f"Compaction error: {e}"


# ── Tool handler (called by tool_dispatcher) ──

def compaction_tool(parameters: dict = None, **kwargs) -> str:
    """Unified compaction tool handler."""
    if not parameters:
        return compaction_status()
    action = parameters.get("action", "status")

    if action == "status":
        return compaction_status()
    elif action == "compact":
        messages_json = parameters.get("messages", "[]")
        return compaction_compact(messages_json)
    elif action == "check":
        compactor = get_compactor()
        try:
            messages = json.loads(parameters.get("messages", "[]"))
            needed = compactor.should_compact(messages)
            tokens = _estimate_messages_tokens(messages)
            return f"Tokens: {tokens:,} / {compactor.context_window:,} — {'NEEDS COMPACTION' if needed else 'OK'}"
        except Exception as e:
            return f"Check error: {e}"
    else:
        return f"Unknown compaction action: {action}. Use: status, compact, check"
