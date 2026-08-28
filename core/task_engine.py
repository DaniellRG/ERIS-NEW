"""
core/task_engine.py — Task decomposition and execution engine for ERIS.

Enables autonomous multi-step work:
  1. PLAN: Break complex task into ordered steps
  2. EXECUTE: Run each step, capturing results
  3. VERIFY: Check results, retry on failure
  4. REPORT: Summary of what was done
"""
from __future__ import annotations

import json
import time
import traceback
from pathlib import Path
from typing import Callable, Optional
from enum import Enum

_BASE = Path(__file__).resolve().parent.parent
_TASKS_DIR = _BASE / "data" / "tasks"
_TASKS_DIR.mkdir(parents=True, exist_ok=True)


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"


class TaskStatus(str, Enum):
    PLANNING = "planning"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    PAUSED = "paused"


class TaskStep:
    def __init__(self, description: str, tool: str = "", params: dict | None = None, depends_on: list[int] | None = None):
        self.description = description
        self.tool = tool
        self.params = params or {}
        self.depends_on = depends_on or []
        self.status = StepStatus.PENDING
        self.result = ""
        self.error = ""
        self.attempts = 0

    def to_dict(self) -> dict:
        return {
            "description": self.description,
            "tool": self.tool,
            "params": self.params,
            "depends_on": self.depends_on,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "attempts": self.attempts,
        }

    @classmethod
    def from_dict(cls, d: dict) -> TaskStep:
        s = cls(d["description"], d.get("tool", ""), d.get("params", {}), d.get("depends_on", []))
        s.status = StepStatus(d.get("status", "pending"))
        s.result = d.get("result", "")
        s.error = d.get("error", "")
        s.attempts = d.get("attempts", 0)
        return s


class Task:
    def __init__(self, goal: str, steps: list[TaskStep] | None = None):
        self.id = f"task_{int(time.time() * 1000)}"
        self.goal = goal
        self.steps = steps or []
        self.status = TaskStatus.PLANNING
        self.created = time.strftime("%Y-%m-%d %H:%M:%S")
        self.finished = ""
        self.summary = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "goal": self.goal,
            "steps": [s.to_dict() for s in self.steps],
            "status": self.status.value,
            "created": self.created,
            "finished": self.finished,
            "summary": self.summary,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Task:
        t = cls(d["goal"], [TaskStep.from_dict(s) for s in d.get("steps", [])])
        t.id = d.get("id", t.id)
        t.status = TaskStatus(d.get("status", "planning"))
        t.created = d.get("created", t.created)
        t.finished = d.get("finished", "")
        t.summary = d.get("summary", "")
        return t

    def save(self):
        path = _TASKS_DIR / f"{self.id}.json"
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, task_id: str) -> Task | None:
        path = _TASKS_DIR / f"{task_id}.json"
        if path.exists():
            try:
                return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))
            except Exception:
                pass
        return None


class TaskEngine:
    """
    Autonomous task execution engine.
    
    Usage:
        engine = TaskEngine(tool_executor)
        task = engine.create_task("Create a web server", steps=[
            TaskStep("Create main.py", "file_editor", {"action": "write", ...}),
            TaskStep("Create requirements.txt", "file_editor", {"action": "write", ...}),
            TaskStep("Install dependencies", "terminal_agent", {"action": "run", "command": "pip install flask"}),
            TaskStep("Test server", "terminal_agent", {"action": "run", "command": "python main.py"}),
        ])
        result = engine.execute_task(task)
    """

    def __init__(self, tool_executor: Callable[[str, dict], str] | None = None):
        self.tool_executor = tool_executor
        self._log: list[str] = []

    def create_task(self, goal: str, steps: list[TaskStep] | None = None) -> Task:
        task = Task(goal, steps)
        task.save()
        return task

    def plan_task(self, goal: str, available_tools: list[str]) -> Task:
        """
        Create a task with a basic planning template.
        Returns a task with placeholder steps that can be filled in.
        """
        task = Task(goal)
        # Default planning template
        task.steps = [
            TaskStep("Analizar el objetivo y determinar qué archivos/herramientas se necesitan"),
            TaskStep("Crear/modificar los archivos necesarios"),
            TaskStep("Verificar que el resultado sea correcto"),
        ]
        task.save()
        return task

    def execute_step(self, step: TaskStep, context: dict | None = None) -> bool:
        """Execute a single step. Returns True if successful."""
        step.attempts += 1
        step.status = StepStatus.RUNNING
        self._log.append(f"[STEP] {step.description}")

        if not self.tool_executor:
            step.status = StepStatus.FAILED
            step.error = "No hay tool_executor configurado"
            return False

        if not step.tool:
            # Pure informational step — just mark as done
            step.status = StepStatus.DONE
            step.result = "Paso informativo completado"
            return True

        try:
            params = dict(step.params)
            if context:
                params["_context"] = context
            result = self.tool_executor(step.tool, params)
            step.result = str(result)[:2000]
            step.status = StepStatus.DONE
            self._log.append(f"  OK: {step.result[:100]}")
            return True
        except Exception as e:
            step.error = f"{type(e).__name__}: {e}"
            step.status = StepStatus.FAILED
            self._log.append(f"  FAIL: {step.error}")
            return False

    def execute_task(self, task: Task, max_retries: int = 2) -> Task:
        """Execute all steps in a task, respecting dependencies."""
        task.status = TaskStatus.RUNNING
        task.save()

        completed = set()
        total = len(task.steps)

        for i, step in enumerate(task.steps):
            # Check dependencies
            if step.depends_on:
                unmet = [d for d in step.depends_on if d not in completed]
                if unmet:
                    step.status = StepStatus.SKIPPED
                    step.error = f"Dependencias no cumplidas: {unmet}"
                    continue

            # Skip already done steps
            if step.status == StepStatus.DONE:
                completed.add(i)
                continue

            # Execute with retries
            success = False
            for attempt in range(max_retries + 1):
                success = self.execute_step(step)
                if success:
                    break
                if attempt < max_retries:
                    self._log.append(f"  Retry {attempt + 1}/{max_retries}")

            if success:
                completed.add(i)
            else:
                # Continue with other steps that don't depend on this one
                pass

        # Determine final status
        done_count = sum(1 for s in task.steps if s.status == StepStatus.DONE)
        fail_count = sum(1 for s in task.steps if s.status == StepStatus.FAILED)

        if fail_count == 0:
            task.status = TaskStatus.DONE
        elif done_count > 0:
            task.status = TaskStatus.DONE  # Partial success
        else:
            task.status = TaskStatus.FAILED

        task.finished = time.strftime("%Y-%m-%d %H:%M:%S")
        task.summary = self._build_summary(task)
        task.save()
        return task

    def _build_summary(self, task: Task) -> str:
        done = sum(1 for s in task.steps if s.status == StepStatus.DONE)
        failed = sum(1 for s in task.steps if s.status == StepStatus.FAILED)
        skipped = sum(1 for s in task.steps if s.status == StepStatus.SKIPPED)
        total = len(task.steps)

        lines = [f"Tarea: {task.goal}", f"Resultado: {done}/{total} pasos completados"]
        if failed:
            lines.append(f"Fallidos: {failed}")
        if skipped:
            lines.append(f"Saltados: {skipped}")
        for i, s in enumerate(task.steps):
            icon = {"done": "OK", "failed": "FAIL", "skipped": "SKIP", "pending": "?"}.get(s.status.value, "?")
            lines.append(f"  [{icon}] {s.description}")
        return "\n".join(lines)

    def get_log(self) -> list[str]:
        return list(self._log)

    def list_tasks(self) -> list[dict]:
        tasks = []
        for f in _TASKS_DIR.glob("task_*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                tasks.append({"id": data.get("id"), "goal": data.get("goal"), "status": data.get("status")})
            except Exception:
                pass
        return sorted(tasks, key=lambda t: t.get("id", ""), reverse=True)
