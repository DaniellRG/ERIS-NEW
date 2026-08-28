"""
core/agent_bus.py — Inter-agent communication bus for ERIS.

Provides shared state and messaging between agents:
  - Shared context (all agents see same state)
  - Message queue (agent A can send task to agent B)
  - Event pub/sub (agents subscribe to events)
  - Global scratch pad (key-value for passing data between agents)
"""
from __future__ import annotations

import json
import time
import threading
from pathlib import Path
from typing import Callable, Optional
from collections import defaultdict

_BASE = Path(__file__).resolve().parent.parent
_STATE_DIR = _BASE / "data" / "agent_state"
_STATE_DIR.mkdir(parents=True, exist_ok=True)


class AgentMessage:
    def __init__(self, sender: str, receiver: str, action: str, payload: dict | None = None):
        self.sender = sender
        self.receiver = receiver
        self.action = action
        self.payload = payload or {}
        self.time = time.time()
        self.id = f"msg_{int(self.time * 1000)}"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "sender": self.sender,
            "receiver": self.receiver,
            "action": self.action,
            "payload": self.payload,
            "time": self.time,
        }


class AgentBus:
    """
    Central communication hub for all agents.
    
    Usage:
        bus = get_agent_bus()
        bus.set_shared("current_task", {"goal": "build web server"})
        bus.send("dev_agent", "build_module", {"name": "server"})
        result = bus.request("dev_agent", "run_tool", {"tool": "terminal", "cmd": "python main.py"})
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._shared: dict = {}  # Shared state visible to all agents
        self._queues: dict[str, list[AgentMessage]] = defaultdict(list)  # Per-agent message queues
        self._handlers: dict[str, Callable] = {}  # Agent message handlers
        self._subscribers: dict[str, list[Callable]] = defaultdict(list)  # Event subscriptions
        self._scratch: dict = {}  # Temporary key-value for passing data between agents
        self._state_file = _STATE_DIR / "shared_state.json"
        self._load_state()

    def _load_state(self):
        if self._state_file.exists():
            try:
                data = json.loads(self._state_file.read_text(encoding="utf-8"))
                self._shared = data.get("shared", {})
                self._scratch = data.get("scratch", {})
            except Exception:
                pass

    def _save_state(self):
        try:
            self._state_file.write_text(json.dumps({
                "shared": self._shared,
                "scratch": self._scratch,
            }, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    # ── Shared State ──────────────────────────────────────────────────────

    def set_shared(self, key: str, value):
        """Set a value in shared state (visible to all agents)."""
        with self._lock:
            self._shared[key] = value
            self._save_state()

    def get_shared(self, key: str = "", default=None):
        """Get value from shared state. If key empty, return all."""
        with self._lock:
            if not key:
                return dict(self._shared)
            return self._shared.get(key, default)

    def del_shared(self, key: str):
        with self._lock:
            self._shared.pop(key, None)
            self._save_state()

    # ── Scratch Pad (temporary data passing) ──────────────────────────────

    def set_scratch(self, key: str, value):
        """Set temporary data (for passing results between agents)."""
        with self._lock:
            self._scratch[key] = {"value": value, "time": time.time()}

    def get_scratch(self, key: str, default=None):
        entry = self._scratch.get(key)
        if entry is None:
            return default
        # Auto-expire after 1 hour
        if time.time() - entry.get("time", 0) > 3600:
            with self._lock:
                self._scratch.pop(key, None)
            return default
        return entry.get("value", default)

    def clear_scratch(self):
        with self._lock:
            self._scratch.clear()

    # ── Message Queue ─────────────────────────────────────────────────────

    def send(self, receiver: str, action: str, payload: dict | None = None, sender: str = "system"):
        """Send a message to an agent's queue."""
        msg = AgentMessage(sender, receiver, action, payload)
        with self._lock:
            self._queues[receiver].append(msg)
            # Keep last 100 messages per agent
            if len(self._queues[receiver]) > 100:
                self._queues[receiver] = self._queues[receiver][-100:]

    def receive(self, agent: str) -> AgentMessage | None:
        """Get next message from an agent's queue."""
        with self._lock:
            queue = self._queues.get(agent, [])
            if queue:
                return queue.pop(0)
        return None

    def peek(self, agent: str) -> list[dict]:
        """See pending messages without consuming them."""
        with self._lock:
            return [m.to_dict() for m in self._queues.get(agent, [])]

    def request(self, agent: str, action: str, payload: dict | None = None, timeout: float = 30) -> str:
        """
        Synchronous request to an agent. Sends message, waits for response.
        The target agent must call bus.respond() to complete the request.
        """
        req_id = f"req_{int(time.time() * 1000)}"
        self.set_scratch(f"_resp_{req_id}", None)
        self.send(agent, action, {**(payload or {}), "_req_id": req_id, "_sync": True})

        start = time.time()
        while time.time() - start < timeout:
            resp = self.get_scratch(f"_resp_{req_id}")
            if resp is not None:
                self._scratch.pop(f"_resp_{req_id}", None)
                return str(resp)
            time.sleep(0.1)
        return f"Timeout esperando respuesta de {agent}"

    def respond(self, req_id: str, result: str):
        """Respond to a synchronous request."""
        self.set_scratch(f"_resp_{req_id}", result)

    # ── Event Pub/Sub ─────────────────────────────────────────────────────

    def subscribe(self, event: str, callback: Callable):
        """Subscribe to an event. Callback receives event name and payload."""
        self._subscribers[event].append(callback)

    def publish(self, event: str, payload: dict | None = None):
        """Publish an event to all subscribers."""
        for cb in self._subscribers.get(event, []):
            try:
                cb(event, payload)
            except Exception:
                pass
        # Also publish to wildcard subscribers
        for cb in self._subscribers.get("*", []):
            try:
                cb(event, payload)
            except Exception:
                pass

    # ── Agent Registration ────────────────────────────────────────────────

    def register_handler(self, agent_name: str, handler: Callable):
        """Register a message handler for an agent."""
        self._handlers[agent_name] = handler

    def get_handler(self, agent_name: str) -> Callable | None:
        return self._handlers.get(agent_name)

    # ── Status ────────────────────────────────────────────────────────────

    def status(self) -> dict:
        return {
            "shared_keys": list(self._shared.keys()),
            "scratch_keys": list(self._scratch.keys()),
            "queues": {k: len(v) for k, v in self._queues.items()},
            "handlers": list(self._handlers.keys()),
            "subscribers": list(self._subscribers.keys()),
        }


# ── Singleton ─────────────────────────────────────────────────────────────────

_bus: AgentBus | None = None


def get_agent_bus() -> AgentBus:
    global _bus
    if _bus is None:
        _bus = AgentBus()
    return _bus
