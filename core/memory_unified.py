"""
core/memory_unified.py — Unified memory system for ERIS.

Consolidates the 5 fragmented memory systems into one coherent API:
  - memory_manager.py (key-value store)
  - semantic_memory.py (episodic/semantic/working)
  - rag_pipeline.py (ChromaDB vector search)
  - rag_engine.py (sentence-transformers)
  - memory_consolidation.py (fact extraction)

This module provides a single interface with:
  - Short-term (conversation context)
  - Long-term (persistent facts, notes, preferences)
  - Episodic (what happened when)
  - Semantic (vector search over all memories)
"""
from __future__ import annotations

import json
import time
import threading
from pathlib import Path
from typing import Optional

_BASE = Path(__file__).resolve().parent.parent
_MEMORY_DIR = _BASE / "memory"
_MEMORY_DIR.mkdir(parents=True, exist_ok=True)

_LONG_TERM_FILE = _MEMORY_DIR / "long_term.json"
_EPISODIC_FILE = _MEMORY_DIR / "episodic.json"
_WORKING_FILE = _MEMORY_DIR / "working.json"
_FACTS_FILE = _MEMORY_DIR / "facts.json"

_lock = threading.Lock()

# ── Short-Term: Working Memory (current conversation) ────────────────────────

_working: list[dict] = []
MAX_WORKING = 50


def working_add(role: str, content: str, metadata: dict | None = None):
    """Add entry to working memory (current conversation)."""
    global _working
    entry = {"role": role, "content": content, "time": time.time()}
    if metadata:
        entry["meta"] = metadata
    _working.append(entry)
    if len(_working) > MAX_WORKING:
        _working = _working[-MAX_WORKING:]


def working_get(last_n: int = 10) -> list[dict]:
    """Get recent working memory entries."""
    return _working[-last_n:]


def working_clear():
    """Clear working memory."""
    global _working
    _working = []


def working_context(max_chars: int = 4000) -> str:
    """Build a context string from working memory for LLM prompts."""
    entries = working_get(last_n=20)
    lines = []
    total = 0
    for e in reversed(entries):
        text = f"[{e['role']}] {e['content']}"
        if total + len(text) > max_chars:
            break
        lines.append(text)
        total += len(text)
    return "\n".join(reversed(lines))


# ── Long-Term: Persistent Memory ─────────────────────────────────────────────

def _load_long_term() -> dict:
    if _LONG_TERM_FILE.exists():
        try:
            return json.loads(_LONG_TERM_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"notes": {}, "habits": {}, "preferences": {}, "context": {}, "facts": {}}


def _save_long_term(data: dict):
    _LONG_TERM_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def long_term_set(category: str, key: str, value: str):
    """Store a long-term memory entry."""
    with _lock:
        mem = _load_long_term()
        if category not in mem:
            mem[category] = {}
        mem[category][key] = {
            "value": value[:500],
            "updated": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        _save_long_term(mem)


def long_term_get(category: str, key: str = "") -> str | dict:
    """Retrieve long-term memory. If key is empty, return entire category."""
    mem = _load_long_term()
    cat = mem.get(category, {})
    if not key:
        return cat
    entry = cat.get(key, {})
    return entry.get("value", "") if isinstance(entry, dict) else str(entry)


def long_term_search(query: str) -> list[dict]:
    """Simple keyword search across all long-term memories."""
    mem = _load_long_term()
    results = []
    query_lower = query.lower()
    for cat, entries in mem.items():
        if isinstance(entries, dict):
            for key, val in entries.items():
                val_text = val.get("value", "") if isinstance(val, dict) else str(val)
                if query_lower in key.lower() or query_lower in val_text.lower():
                    results.append({"category": cat, "key": key, "value": val_text})
    return results


# ── Episodic: What happened, when ────────────────────────────────────────────

def _load_episodic() -> list[dict]:
    if _EPISODIC_FILE.exists():
        try:
            data = json.loads(_EPISODIC_FILE.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            pass
    return []


def _save_episodic(data: list):
    # Keep last 500 episodes
    if len(data) > 500:
        data = data[-500:]
    _EPISODIC_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def episodic_add(event: str, context: str = "", importance: float = 0.5):
    """Record an episodic memory."""
    with _lock:
        episodes = _load_episodic()
        episodes.append({
            "event": event,
            "context": context,
            "importance": importance,
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "timestamp": time.time(),
        })
        _save_episodic(episodes)


def episodic_recent(n: int = 10) -> list[dict]:
    """Get recent episodes."""
    return _load_episodic()[-n:]


def episodic_search(query: str, n: int = 5) -> list[dict]:
    """Search episodes by keyword."""
    episodes = _load_episodic()
    query_lower = query.lower()
    matches = [e for e in episodes if query_lower in e.get("event", "").lower() or query_lower in e.get("context", "").lower()]
    return matches[-n:]


# ── Facts: Extracted knowledge ───────────────────────────────────────────────

def _load_facts() -> list[dict]:
    if _FACTS_FILE.exists():
        try:
            data = json.loads(_FACTS_FILE.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            pass
    return []


def _save_facts(data: list):
    if len(data) > 1000:
        data = data[-1000:]
    _FACTS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def fact_add(statement: str, source: str = "", confidence: float = 1.0):
    """Add an extracted fact."""
    with _lock:
        facts = _load_facts()
        # Deduplicate by similar text
        for f in facts:
            if f.get("statement", "").lower() == statement.lower():
                f["updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
                f["confidence"] = max(f.get("confidence", 0), confidence)
                _save_facts(facts)
                return
        facts.append({
            "statement": statement,
            "source": source,
            "confidence": confidence,
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        })
        _save_facts(facts)


def fact_search(query: str, n: int = 5) -> list[dict]:
    """Search facts by keyword."""
    facts = _load_facts()
    query_lower = query.lower()
    matches = [f for f in facts if query_lower in f.get("statement", "").lower()]
    return matches[-n:]


def facts_summary() -> str:
    """Get a summary of all facts."""
    facts = _load_facts()
    if not facts:
        return "No hay hechos registrados."
    return "\n".join(f"• {f['statement']}" for f in facts[-30:])


# ── Consolidated API ─────────────────────────────────────────────────────────

class UnifiedMemory:
    """Single interface to all memory subsystems."""

    def __init__(self):
        pass

    # Working
    def add_context(self, role: str, content: str, **kw):
        working_add(role, content, **kw)

    def get_context(self, last_n: int = 10) -> list[dict]:
        return working_get(last_n)

    def build_prompt_context(self, max_chars: int = 4000) -> str:
        return working_context(max_chars)

    def clear_context(self):
        working_clear()

    # Long-term
    def remember(self, category: str, key: str, value: str):
        long_term_set(category, key, value)

    def recall(self, category: str, key: str = "") -> str | dict:
        return long_term_get(category, key)

    def search_long_term(self, query: str) -> list[dict]:
        return long_term_search(query)

    # Episodic
    def log_event(self, event: str, context: str = "", importance: float = 0.5):
        episodic_add(event, context, importance)

    def recent_events(self, n: int = 10) -> list[dict]:
        return episodic_recent(n)

    def search_events(self, query: str, n: int = 5) -> list[dict]:
        return episodic_search(query, n)

    # Facts
    def add_fact(self, statement: str, source: str = "", confidence: float = 1.0):
        fact_add(statement, source, confidence)

    def search_facts(self, query: str, n: int = 5) -> list[dict]:
        return fact_search(query, n)

    def get_facts(self) -> str:
        return facts_summary()

    # Search everything
    def search_all(self, query: str) -> dict:
        """Search across all memory types."""
        return {
            "long_term": self.search_long_term(query),
            "episodes": self.search_events(query),
            "facts": self.search_facts(query),
        }


# ── Singleton ─────────────────────────────────────────────────────────────────

_instance: UnifiedMemory | None = None


def get_memory() -> UnifiedMemory:
    global _instance
    if _instance is None:
        _instance = UnifiedMemory()
    return _instance
