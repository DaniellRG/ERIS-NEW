"""core/sub_agents.py — SUB-AGENTES ESPECIALIZADOS DE ERIS.

Arquitectura multi-capa: Orquestación → Especialistas → Calidad/Gobernanza → Meta-mejora.
Cada sub-agente tiene: rol, meta, backstory, tools[], y se comunica via message bus.
Inspirado en CrewAI (role-goal-backstory), LangGraph (state graph), Devika/DeerFlow.
"""

from __future__ import annotations
import json
import time
import threading
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Callable, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum

_BASE = Path(__file__).resolve().parent.parent
_SUB_AGENT_STATE_FILE = _BASE / "memory" / "sub_agent_state.json"
_MESSAGE_BUS_FILE = _BASE / "data" / "agent_bus.jsonl"
_SUB_AGENT_REGISTRY_FILE = _BASE / "core" / "sub_agent_registry.json"


class SubAgentStatus(Enum):
    IDLE = "idle"
    PLANNING = "planning"
    WORKING = "working"
    WAITING = "waiting"
    REVIEWING = "reviewing"
    DONE = "done"
    ERROR = "error"


@dataclass
class SubAgentMessage:
    """Mensaje en el bus de comunicación entre sub-agentes."""
    id: str
    from_agent: str
    to_agent: str
    type: str  # task, result, request, notify, feedback
    payload: dict
    timestamp: float = field(default_factory=time.time)
    correlation_id: Optional[str] = None


@dataclass
class SubAgentTask:
    """Tarea asignada a un sub-agente."""
    id: str
    agent_key: str
    description: str
    params: dict
    priority: int = 1
    status: SubAgentStatus = SubAgentStatus.IDLE
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    depends_on: list[str] = field(default_factory=list)


class SubAgentBase(ABC):
    """Clase base para todos los sub-agentes especializados."""

    def __init__(self, key: str, role: str, goal: str, backstory: str, tools: list[str]):
        self.key = key
        self.role = role
        self.goal = goal
        self.backstory = backstory
        self.tools = tools
        self.status = SubAgentStatus.IDLE
        self.current_task: Optional[SubAgentTask] = None
        self._lock = threading.Lock()

    @abstractmethod
    def execute(self, task: SubAgentTask, context: dict) -> Any:
        """Ejecuta la tarea con el contexto dado. Debe ser implementado por cada sub-agente."""
        pass

    def can_handle(self, task_type: str) -> bool:
        """¿Puede este agente manejar este tipo de tarea?"""
        return task_type in self.tools or task_type == self.key

    def get_state(self) -> dict:
        return {
            "key": self.key,
            "role": self.role,
            "goal": self.goal,
            "status": self.status.value,
            "current_task": self.current_task.id if self.current_task else None,
            "tools": self.tools,
        }


class SubAgentRegistry:
    """Registro central de sub-agentes, persistido en disco."""

    def __init__(self):
        self._agents: dict[str, SubAgentBase] = {}
        self._tasks: dict[str, SubAgentTask] = {}
        self._message_bus: list[SubAgentMessage] = []
        self._lock = threading.Lock()
        self._load_registry()
        self._load_state()

    def _load_registry(self):
        try:
            if _SUB_AGENT_REGISTRY_FILE.exists():
                data = json.loads(_SUB_AGENT_REGISTRY_FILE.read_text("utf-8"))
                for key, info in data.get("agents", {}).items():
                    if key in self._agents:
                        continue
        except Exception:
            pass

    def _save_registry(self):
        try:
            _SUB_AGENT_REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {"agents": {}}
            for key, agent in self._agents.items():
                data["agents"][key] = {
                    "key": agent.key,
                    "role": agent.role,
                    "goal": agent.goal,
                    "backstory": agent.backstory,
                    "tools": agent.tools,
                }
            _SUB_AGENT_REGISTRY_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), "utf-8")
        except Exception as e:
            print(f"[SubAgentRegistry] Save error: {e}")

    def _load_state(self):
        try:
            if _SUB_AGENT_STATE_FILE.exists():
                data = json.loads(_SUB_AGENT_STATE_FILE.read_text("utf-8"))
                for task_data in data.get("tasks", []):
                    task = SubAgentTask(**task_data)
                    task.status = SubAgentStatus(task_data.get("status", "idle"))
                    self._tasks[task.id] = task
        except Exception:
            pass

    def _save_state(self):
        try:
            _SUB_AGENT_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {"tasks": []}
            for task in self._tasks.values():
                td = asdict(task)
                td["status"] = task.status.value
                data["tasks"].append(td)
            _SUB_AGENT_STATE_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), "utf-8")
        except Exception as e:
            print(f"[SubAgentRegistry] State save error: {e}")

    def register(self, agent: SubAgentBase):
        with self._lock:
            self._agents[agent.key] = agent
            self._save_registry()

    def unregister(self, key: str):
        with self._lock:
            self._agents.pop(key, None)
            self._save_registry()

    def get_agent(self, key: str) -> Optional[SubAgentBase]:
        return self._agents.get(key)

    def get_all_agents(self) -> dict[str, SubAgentBase]:
        return dict(self._agents)

    def create_task(self, agent_key: str, description: str, params: dict, priority: int = 1, depends_on: list[str] = None) -> SubAgentTask:
        task_id = f"{agent_key}_{int(time.time()*1000)}"
        task = SubAgentTask(
            id=task_id,
            agent_key=agent_key,
            description=description,
            params=params,
            priority=priority,
            depends_on=depends_on or [],
        )
        with self._lock:
            self._tasks[task_id] = task
            self._save_state()
        return task

    def get_task(self, task_id: str) -> Optional[SubAgentTask]:
        return self._tasks.get(task_id)

    def get_pending_tasks(self, agent_key: str = None) -> list[SubAgentTask]:
        with self._lock:
            tasks = [t for t in self._tasks.values() if t.status == SubAgentStatus.IDLE]
            if agent_key:
                tasks = [t for t in tasks if t.agent_key == agent_key]
            return sorted(tasks, key=lambda t: (-t.priority, t.created_at))

    def update_task_status(self, task_id: str, status: SubAgentStatus, result: Any = None, error: str = None):
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.status = status
                if status == SubAgentStatus.WORKING and not task.started_at:
                    task.started_at = time.time()
                if status in (SubAgentStatus.DONE, SubAgentStatus.ERROR):
                    task.completed_at = time.time()
                    task.result = result
                    task.error = error
                self._save_state()

    def send_message(self, msg: SubAgentMessage):
        with self._lock:
            self._message_bus.append(msg)
            try:
                _MESSAGE_BUS_FILE.parent.mkdir(parents=True, exist_ok=True)
                with _MESSAGE_BUS_FILE.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(asdict(msg), ensure_ascii=False) + "\n")
            except Exception:
                pass

    def get_messages(self, to_agent: str = None, since: float = 0) -> list[SubAgentMessage]:
        with self._lock:
            msgs = [m for m in self._message_bus if m.timestamp >= since]
            if to_agent:
                msgs = [m for m in msgs if m.to_agent == to_agent]
            return msgs

    def get_stats(self) -> dict:
        return {
            "agents_registered": len(self._agents),
            "tasks_total": len(self._tasks),
            "tasks_pending": len([t for t in self._tasks.values() if t.status == SubAgentStatus.IDLE]),
            "tasks_working": len([t for t in self._tasks.values() if t.status == SubAgentStatus.WORKING]),
            "tasks_done": len([t for t in self._tasks.values() if t.status == SubAgentStatus.DONE]),
            "tasks_error": len([t for t in self._tasks.values() if t.status == SubAgentStatus.ERROR]),
            "messages_in_bus": len(self._message_bus),
        }

    def requeue_stuck_tasks(self, stuck_after_secs: float = 120.0) -> int:
        """Re-encola tareas que quedaron en WORKING más de `stuck_after_secs`
        (proceso que murió a mitad de ejecución, daemon sin atenderlas, etc.).
        Devuelve cuántas tareas re-encoló a IDLE con prioridad de vuelta."""
        now = time.time()
        requeued = 0
        with self._lock:
            for t in self._tasks.values():
                if t.status == SubAgentStatus.WORKING and t.started_at is not None:
                    if (now - t.started_at) > stuck_after_secs:
                        t.status = SubAgentStatus.IDLE
                        t.started_at = None
                        t.priority = min(t.priority + 1, 10)
                        requeued += 1
            if requeued:
                self._save_state()
        return requeued


# ── Singleton ──────────────────────────────────────────────────────────────
_sub_agent_registry: Optional[SubAgentRegistry] = None
_sub_agent_registry_lock = threading.Lock()


def get_sub_agent_registry() -> SubAgentRegistry:
    global _sub_agent_registry
    with _sub_agent_registry_lock:
        if _sub_agent_registry is None:
            _sub_agent_registry = SubAgentRegistry()
        return _sub_agent_registry