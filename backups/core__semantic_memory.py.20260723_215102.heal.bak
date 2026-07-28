"""
semantic_memory.py — ERIS Semantic Memory System.
Simulates AGI-like persistent memory with semantic understanding.

Components:
  - Episodic memory: What happened, when, in what context
  - Semantic memory: Facts, concepts, relationships
  - Working memory: Active context of current conversation
  - Knowledge graph: Relationships between entities

Uses local embeddings (Ollama) for semantic similarity search.
No external dependencies — uses numpy for vector operations.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

try:
    import numpy as np
    _NUMPY = True
except ImportError:
    _NUMPY = False

_BASE = Path(__file__).resolve().parent.parent
_MEMORY_DIR = _BASE / "memory"
_EPISODIC_FILE = _MEMORY_DIR / "episodic.json"
_SEMANTIC_FILE = _MEMORY_DIR / "semantic.json"
_WORKING_FILE = _MEMORY_DIR / "working.json"
_GRAPH_FILE = _MEMORY_DIR / "knowledge_graph.json"

# ── Embedding generation (local, no API) ──────────────────────────────────────

def _get_embedding(text: str, dim: int = 128) -> list[float]:
    """
    Generate text embedding using Ollama (nomic-embed-text) if available,
    falling back to deterministic hash-based pseudo-embedding.
    """
    try:
        from core.llm_bridge import get_embedding
        emb = get_embedding(text)
        if emb and len(emb) >= dim:
            return emb[:dim]
    except Exception:
        pass
    # Fallback: deterministic hash-based pseudo-embedding
    if not _NUMPY:
        h = hashlib.sha256(text.encode()).hexdigest()
        return [int(h[i:i+2], 16) / 255.0 for i in range(0, dim * 2, 2)]
    h = hashlib.sha256(text.encode()).digest()
    np.random.seed(int.from_bytes(h[:4], "big") & 0xFFFFFFFF)
    vec = np.random.randn(dim).astype(np.float32)
    vec = vec / np.linalg.norm(vec)
    return vec.tolist()

def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    if not _NUMPY:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)
    
    a_np = np.array(a, dtype=np.float32)
    b_np = np.array(b, dtype=np.float32)
    dot = np.dot(a_np, b_np)
    norm_a = np.linalg.norm(a_np)
    norm_b = np.linalg.norm(b_np)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot / (norm_a * norm_b))

# ── Memory management ─────────────────────────────────────────────────────────

def _load_json(path: Path, default: Any = None) -> Any:
    """Load JSON file or return default."""
    try:
        if path.exists():
            return json.loads(path.read_text("utf-8"))
    except Exception:
        pass
    return default if default is not None else {}

def _save_json(path: Path, data: Any):
    """Save data to JSON file."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), "utf-8")
    except Exception as e:
        print(f"[SemanticMemory] Save error: {e}")

# ── Episodic Memory ───────────────────────────────────────────────────────────

class EpisodicMemory:
    """Stores events with context: what happened, when, where."""

    def __init__(self):
        self.entries = _load_json(_EPISODIC_FILE, [])

    def add(self, event: str, context: dict = None, importance: float = 0.5):
        """Add an episodic memory."""
        entry = {
            "id": f"ep_{int(time.time() * 1000)}",
            "event": event,
            "context": context or {},
            "importance": importance,
            "timestamp": time.time(),
            "datetime": datetime.now().isoformat(),
        }
        self.entries.append(entry)
        # Keep only last 1000 entries (prevent unbounded growth)
        if len(self.entries) > 1000:
            # Keep most important entries
            self.entries.sort(key=lambda x: x.get("importance", 0), reverse=True)
            self.entries = self.entries[:1000]
        _save_json(_EPISODIC_FILE, self.entries)

    def search(self, query: str, limit: int = 5) -> list[dict]:
        """Search episodic memories by semantic similarity."""
        query_vec = _get_embedding(query)
        scored = []
        for entry in self.entries:
            event_vec = _get_embedding(entry["event"])
            sim = _cosine_similarity(query_vec, event_vec)
            # Boost by importance and recency
            age_days = (time.time() - entry["timestamp"]) / 86400
            recency_boost = max(0, 1 - age_days / 30)  # Decay over 30 days
            score = sim * 0.6 + entry.get("importance", 0.5) * 0.3 + recency_boost * 0.1
            scored.append((score, entry))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        return [entry for score, entry in scored[:limit]]

    def get_recent(self, limit: int = 10) -> list[dict]:
        """Get most recent memories."""
        sorted_entries = sorted(self.entries, key=lambda x: x["timestamp"], reverse=True)
        return sorted_entries[:limit]

# ── Semantic Memory ───────────────────────────────────────────────────────────

class SemanticMemory:
    """Stores facts and concepts with relationships."""

    def __init__(self):
        self.facts = _load_json(_SEMANTIC_FILE, [])

    def add_fact(self, subject: str, predicate: str, obj: str, confidence: float = 0.9):
        """Add a semantic fact: subject-predicate-object triple."""
        fact = {
            "id": f"sem_{hashlib.md5(f'{subject}{predicate}{obj}'.encode()).hexdigest()[:8]}",
            "subject": subject.lower(),
            "predicate": predicate.lower(),
            "object": obj.lower(),
            "confidence": confidence,
            "timestamp": time.time(),
            "sources": [],
        }
        # Check if fact already exists
        for i, existing in enumerate(self.facts):
            if (existing["subject"] == fact["subject"] and
                existing["predicate"] == fact["predicate"] and
                existing["object"] == fact["object"]):
                # Update confidence (average)
                self.facts[i]["confidence"] = (existing["confidence"] + confidence) / 2
                self.facts[i]["timestamp"] = time.time()
                _save_json(_SEMANTIC_FILE, self.facts)
                return
        
        self.facts.append(fact)
        _save_json(_SEMANTIC_FILE, self.facts)

    def query(self, subject: str = None, predicate: str = None, obj: str = None) -> list[dict]:
        """Query semantic facts with optional filters."""
        results = []
        for fact in self.facts:
            if subject and fact["subject"] != subject.lower():
                continue
            if predicate and fact["predicate"] != predicate.lower():
                continue
            if obj and fact["object"] != obj.lower():
                continue
            results.append(fact)
        return results

    def get_facts_about(self, entity: str) -> list[dict]:
        """Get all facts about an entity."""
        return self.query(subject=entity)

    def get_relationships(self, entity: str) -> list[dict]:
        """Get all relationships involving an entity."""
        return [f for f in self.facts if f["subject"] == entity.lower() or f["object"] == entity.lower()]

# ── Working Memory ────────────────────────────────────────────────────────────

class WorkingMemory:
    """Active context of current conversation. Short-term, volatile."""

    def __init__(self):
        self.data = _load_json(_WORKING_FILE, {
            "current_topic": None,
            "recent_entities": [],
            "active_goals": [],
            "conversation_turns": [],
            "user_intent": None,
            "last_updated": time.time(),
        })

    def set_topic(self, topic: str):
        """Set current conversation topic."""
        self.data["current_topic"] = topic
        self.data["last_updated"] = time.time()
        _save_json(_WORKING_FILE, self.data)

    def add_entity(self, entity: str, entity_type: str = "general"):
        """Add entity to active context."""
        if entity.lower() not in [e["name"].lower() for e in self.data.get("recent_entities", [])]:
            self.data.setdefault("recent_entities", []).append({
                "name": entity,
                "type": entity_type,
                "added_at": time.time(),
            })
            # Keep only last 20 entities
            if len(self.data["recent_entities"]) > 20:
                self.data["recent_entities"] = self.data["recent_entities"][-20:]
        _save_json(_WORKING_FILE, self.data)

    def add_goal(self, goal: str):
        """Add active goal."""
        self.data.setdefault("active_goals", []).append({
            "goal": goal,
            "added_at": time.time(),
            "completed": False,
        })
        _save_json(_WORKING_FILE, self.data)

    def complete_goal(self, goal: str):
        """Mark goal as completed."""
        for g in self.data.get("active_goals", []):
            if g["goal"].lower() == goal.lower():
                g["completed"] = True
                g["completed_at"] = time.time()
        _save_json(_WORKING_FILE, self.data)

    def add_turn(self, user_msg: str, assistant_msg: str):
        """Add conversation turn."""
        self.data.setdefault("conversation_turns", []).append({
            "user": user_msg,
            "assistant": assistant_msg,
            "timestamp": time.time(),
        })
        # Keep only last 10 turns
        if len(self.data["conversation_turns"]) > 10:
            self.data["conversation_turns"] = self.data["conversation_turns"][-10:]
        _save_json(_WORKING_FILE, self.data)

    def get_context_summary(self) -> str:
        """Get summary of current working memory."""
        lines = []
        if self.data.get("current_topic"):
            lines.append(f"Tema actual: {self.data['current_topic']}")
        if self.data.get("recent_entities"):
            entities = [e["name"] for e in self.data["recent_entities"][-5:]]
            lines.append(f"Entidades activas: {', '.join(entities)}")
        if self.data.get("active_goals"):
            active = [g["goal"] for g in self.data["active_goals"] if not g.get("completed")]
            if active:
                lines.append(f"Objetivos activos: {', '.join(active)}")
        return "\n".join(lines) if lines else "Sin contexto activo."

    def clear(self):
        """Clear working memory."""
        self.data = {
            "current_topic": None,
            "recent_entities": [],
            "active_goals": [],
            "conversation_turns": [],
            "user_intent": None,
            "last_updated": time.time(),
        }
        _save_json(_WORKING_FILE, self.data)

# ─ Knowledge Graph ───────────────────────────────────────────────────────────

class KnowledgeGraph:
    """Graph of relationships between entities."""

    def __init__(self):
        self.nodes = _load_json(_GRAPH_FILE, {}).get("nodes", {})
        self.edges = _load_json(_GRAPH_FILE, {}).get("edges", [])

    def add_node(self, entity: str, entity_type: str = "concept", properties: dict = None):
        """Add a node to the graph."""
        key = entity.lower()
        self.nodes[key] = {
            "name": entity,
            "type": entity_type,
            "properties": properties or {},
            "created_at": time.time(),
            "connections": 0,
        }
        self._save()

    def add_edge(self, source: str, target: str, relation: str, weight: float = 1.0):
        """Add an edge between two nodes."""
        edge = {
            "source": source.lower(),
            "target": target.lower(),
            "relation": relation.lower(),
            "weight": weight,
            "timestamp": time.time(),
        }
        self.edges.append(edge)
        
        # Update node connection counts
        for node in [source.lower(), target.lower()]:
            if node in self.nodes:
                self.nodes[node]["connections"] = self.nodes[node].get("connections", 0) + 1
        
        self._save()

    def get_neighbors(self, entity: str, relation: str = None) -> list[dict]:
        """Get all neighbors of an entity."""
        neighbors = []
        for edge in self.edges:
            if edge["source"] == entity.lower():
                if relation is None or edge["relation"] == relation.lower():
                    neighbors.append({
                        "entity": edge["target"],
                        "relation": edge["relation"],
                        "weight": edge["weight"],
                    })
            elif edge["target"] == entity.lower():
                if relation is None or edge["relation"] == relation.lower():
                    neighbors.append({
                        "entity": edge["source"],
                        "relation": edge["relation"],
                        "weight": edge["weight"],
                    })
        return neighbors

    def find_path(self, source: str, target: str, max_depth: int = 3) -> list[list[str]]:
        """Find paths between two entities (BFS)."""
        if source.lower() == target.lower():
            return [[source]]
        
        visited = {source.lower()}
        queue = [(source.lower(), [source])]
        paths = []
        
        while queue:
            current, path = queue.pop(0)
            if len(path) > max_depth:
                continue
            
            for neighbor in self.get_neighbors(current):
                neighbor_name = neighbor["entity"]
                if neighbor_name == target.lower():
                    paths.append(path + [target])
                elif neighbor_name not in visited:
                    visited.add(neighbor_name)
                    queue.append((neighbor_name, path + [neighbor_name]))
        
        return paths

    def _save(self):
        """Save graph to disk."""
        _save_json(_GRAPH_FILE, {"nodes": self.nodes, "edges": self.edges})

# ── Unified Interface ─────────────────────────────────────────────────────────

class SemanticMemorySystem:
    """Unified interface for all memory components."""

    def __init__(self):
        self.episodic = EpisodicMemory()
        self.semantic = SemanticMemory()
        self.working = WorkingMemory()
        self.graph = KnowledgeGraph()

    def remember(self, text: str, context: dict = None, importance: float = 0.5):
        """Store information in all memory systems."""
        # Episodic: store the event
        self.episodic.add(text, context, importance)
        
        # Extract entities and add to working memory
        words = text.split()
        for word in words:
            if len(word) > 3 and word[0].isupper():
                self.working.add_entity(word, "entity")
        
        # Add to semantic memory if it contains facts
        # Simple heuristic: look for "X es Y", "X tiene Y", etc.
        text_lower = text.lower()
        if " es " in text_lower or " se llama " in text_lower:
            parts = text_lower.split(" es ")
            if len(parts) == 2:
                subject = parts[0].strip()
                obj = parts[1].strip().rstrip(".")
                self.semantic.add_fact(subject, "es", obj, confidence=0.8)
                self.graph.add_node(subject, "entity")
                self.graph.add_node(obj, "concept")
                self.graph.add_edge(subject, obj, "es")
        
        if " tiene " in text_lower or " su " in text_lower:
            parts = text_lower.split(" tiene ")
            if len(parts) == 2:
                subject = parts[0].strip()
                obj = parts[1].strip().rstrip(".")
                self.semantic.add_fact(subject, "tiene", obj, confidence=0.7)
                self.graph.add_node(subject, "entity")
                self.graph.add_node(obj, "concept")
                self.graph.add_edge(subject, obj, "tiene")

    def recall(self, query: str, limit: int = 5) -> dict:
        """Recall information from all memory systems."""
        return {
            "episodic": self.episodic.search(query, limit),
            "semantic": self.semantic.query(subject=query),
            "working": self.working.get_context_summary(),
            "graph_neighbors": self.graph.get_neighbors(query),
        }

    def get_status(self) -> dict:
        """Get memory system status."""
        return {
            "episodic_entries": len(self.episodic.entries),
            "semantic_facts": len(self.semantic.facts),
            "working_entities": len(self.working.data.get("recent_entities", [])),
            "graph_nodes": len(self.graph.nodes),
            "graph_edges": len(self.graph.edges),
        }

    def consolidate(self):
        """Move important working memories to long-term storage.
        Preserves conversation topics, entities, and goals across sessions."""
        for entity in self.working.data.get("recent_entities", []):
            if entity.get("type") in ("person", "important", "entity"):
                name = entity["name"]
                if not self.semantic.query(subject="usuario", predicate="conoce", obj=name):
                    self.semantic.add_fact("usuario", "conoce", name, confidence=0.6)
                self.graph.add_node("usuario", "person")
                self.graph.add_node(name, entity.get("type", "entity"))
                self.graph.add_edge("usuario", name, "conoce")

        topic = self.working.data.get("current_topic")
        if topic and not self.semantic.query(subject="conversacion", predicate="tema", obj=topic):
            self.semantic.add_fact("conversacion", "tema", topic, confidence=0.7)
            self.graph.add_node("conversacion", "concept")
            self.graph.add_node(topic, "topic")
            self.graph.add_edge("conversacion", topic, "tema")

        for goal in self.working.data.get("active_goals", []):
            goal_text = goal.get("goal", "")
            if goal_text and not goal.get("completed", False):
                existing = self.semantic.query(subject="usuario", predicate="objetivo", obj=goal_text)
                if not existing:
                    self.semantic.add_fact("usuario", "objetivo", goal_text, confidence=0.8)
                    self.graph.add_node("usuario", "person")
                    self.graph.add_node(goal_text, "goal")
                    self.graph.add_edge("usuario", goal_text, "objetivo")

        recent_episodic = self.episodic.get_recent(limit=3)
        for ep in recent_episodic:
            event_text = ep.get("event", "")
            if event_text and len(event_text) > 20 and not self.semantic.query(subject="conversacion", predicate="evento", obj=event_text[:100]):
                self.semantic.add_fact("conversacion", "evento", event_text[:100], confidence=0.5)

# ── Singleton ─────────────────────────────────────────────────────────────────

_memory_system: Optional[SemanticMemorySystem] = None

def get_memory_system() -> SemanticMemorySystem:
    global _memory_system
    if _memory_system is None:
        _memory_system = SemanticMemorySystem()
    return _memory_system
