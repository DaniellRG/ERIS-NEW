"""Scheduled task system with cron-like scheduling."""

import json
import os
import threading
import time
import uuid
from datetime import datetime, timedelta
from typing import Any

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
TASKS_FILE = os.path.join(DATA_DIR, "task_scheduler.json")

_timers: dict[str, threading.Timer] = {}
_background_thread: threading.Thread | None = None
_stop_event = threading.Event()


def _load_tasks() -> dict[str, Any]:
    if os.path.exists(TASKS_FILE):
        with open(TASKS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"tasks": {}, "log": []}


def _save_tasks(data: dict[str, Any]) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(TASKS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)


def _parse_schedule(schedule_str: str) -> dict[str, Any]:
    s = schedule_str.strip().lower()
    result: dict[str, Any] = {"type": "unknown", "interval_seconds": 0}

    if s.startswith("every "):
        parts = s[6:].split()
        if len(parts) >= 2:
            try:
                num = int(parts[0])
            except ValueError:
                return result
            unit = parts[1].rstrip("s")
            multipliers = {
                "second": 1, "minute": 60, "hour": 3600, "day": 86400, "week": 604800,
            }
            if unit in multipliers:
                result["type"] = "interval"
                result["interval_seconds"] = num * multipliers[unit]
                result["every_n"] = num
                result["every_unit"] = unit

    elif s.startswith("daily at "):
        time_str = s[9:].strip()
        result["type"] = "daily"
        result["time"] = time_str

    elif s.startswith("weekly on "):
        day_str = s[10:].strip()
        days = {
            "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
            "friday": 4, "saturday": 5, "sunday": 6,
        }
        result["type"] = "weekly"
        result["weekday"] = days.get(day_str, -1)
        result["weekday_name"] = day_str

    elif s.startswith("once in "):
        parts = s[8:].split()
        if len(parts) >= 2:
            try:
                num = int(parts[0])
            except ValueError:
                return result
            unit = parts[1].rstrip("s")
            multipliers = {"minute": 60, "hour": 3600, "day": 86400}
            if unit in multipliers:
                result["type"] = "once"
                result["delay_seconds"] = num * multipliers[unit]

    return result


def _next_run(schedule: dict[str, Any], now: datetime | None = None) -> str:
    if now is None:
        now = datetime.now()
    stype = schedule.get("type", "")

    if stype == "interval":
        nxt = now + timedelta(seconds=schedule.get("interval_seconds", 3600))
        return nxt.isoformat()

    if stype == "daily":
        t = schedule.get("time", "00:00")
        try:
            h, m = map(int, t.split(":"))
        except ValueError:
            h, m = 0, 0
        target = now.replace(hour=h, minute=m, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        return target.isoformat()

    if stype == "weekly":
        wd = schedule.get("weekday", 0)
        days_ahead = (wd - now.weekday()) % 7
        if days_ahead == 0:
            days_ahead = 7
        target = now + timedelta(days=days_ahead)
        t = schedule.get("time", "00:00")
        try:
            h, m = map(int, t.split(":"))
        except ValueError:
            h, m = 0, 0
        target = target.replace(hour=h, minute=m, second=0, microsecond=0)
        return target.isoformat()

    if stype == "once":
        nxt = now + timedelta(seconds=schedule.get("delay_seconds", 3600))
        return nxt.isoformat()

    return (now + timedelta(hours=1)).isoformat()


def _execute_task(task_id: str) -> None:
    data = _load_tasks()
    task = data["tasks"].get(task_id)
    if not task:
        return
    task["status"] = "running"
    _save_tasks(data)

    entry = {
        "task_id": task_id,
        "name": task.get("name", ""),
        "executed_at": datetime.now().isoformat(),
        "result": "executed",
    }
    data["log"].append(entry)
    if len(data["log"]) > 200:
        data["log"] = data["log"][-200:]

    task["status"] = "active" if task.get("schedule", {}).get("type") != "once" else "completed"
    task["last_run"] = datetime.now().isoformat()
    task["run_count"] = task.get("run_count", 0) + 1
    _save_tasks(data)


def _background_checker() -> None:
    while not _stop_event.is_set():
        try:
            data = _load_tasks()
            now = datetime.now()
            changed = False
            for tid, task in data["tasks"].items():
                if task.get("status") not in ("active", "scheduled"):
                    continue
                next_run = task.get("next_run", "")
                if not next_run:
                    continue
                try:
                    nr = datetime.fromisoformat(next_run)
                except (ValueError, TypeError):
                    continue
                if now >= nr:
                    _execute_task(tid)
                    sched = _parse_schedule(task.get("schedule_text", "every 1 hour"))
                    task["next_run"] = _next_run(sched, datetime.now())
                    changed = True
            if changed:
                _save_tasks(data)
        except Exception:
            pass
        _stop_event.wait(30)


def _ensure_background() -> None:
    global _background_thread
    if _background_thread is None or not _background_thread.is_alive():
        _stop_event.clear()
        _background_thread = threading.Thread(target=_background_checker, daemon=True)
        _background_thread.start()


def task_scheduler(parameters: dict, player=None) -> str:
    action = parameters.get("action", "list").lower()
    data = _load_tasks()

    if action == "add":
        name = parameters.get("name", "unnamed_task")
        schedule_text = parameters.get("schedule", "every 1 hour")
        command = parameters.get("command", "")
        if not command:
            return "Error: 'command' parameter is required."
        task_id = str(uuid.uuid4())[:8]
        sched = _parse_schedule(schedule_text)
        data["tasks"][task_id] = {
            "id": task_id,
            "name": name,
            "command": command,
            "schedule_text": schedule_text,
            "schedule": sched,
            "status": "active",
            "next_run": _next_run(sched),
            "created_at": datetime.now().isoformat(),
            "last_run": None,
            "run_count": 0,
        }
        _save_tasks(data)
        _ensure_background()
        return f"Task '{name}' created (id: {task_id}) | Schedule: {schedule_text} | Next run: {data['tasks'][task_id]['next_run']}"

    elif action == "list":
        tasks = data.get("tasks", {})
        if not tasks:
            return "No scheduled tasks."
        lines = []
        for tid, t in tasks.items():
            lines.append(
                f"[{tid}] {t['name']} | cmd: {t.get('command', '')[:40]} | "
                f"status: {t['status']} | runs: {t.get('run_count', 0)} | "
                f"next: {t.get('next_run', 'N/A')}"
            )
        return f"Scheduled tasks ({len(tasks)}):\n" + "\n".join(lines)

    elif action == "delete":
        task_id = parameters.get("task_id", "")
        if task_id not in data["tasks"]:
            return f"Task '{task_id}' not found."
        name = data["tasks"][task_id]["name"]
        del data["tasks"][task_id]
        _save_tasks(data)
        return f"Task '{name}' ({task_id}) deleted."

    elif action == "run_now":
        task_id = parameters.get("task_id", "")
        if task_id not in data["tasks"]:
            return f"Task '{task_id}' not found."
        _execute_task(task_id)
        sched = _parse_schedule(data["tasks"][task_id].get("schedule_text", "every 1 hour"))
        data["tasks"][task_id]["next_run"] = _next_run(sched, datetime.now())
        _save_tasks(data)
        return f"Task '{data['tasks'][task_id]['name']}' executed immediately."

    elif action == "pause":
        task_id = parameters.get("task_id", "")
        if task_id not in data["tasks"]:
            return f"Task '{task_id}' not found."
        data["tasks"][task_id]["status"] = "paused"
        _save_tasks(data)
        return f"Task '{data['tasks'][task_id]['name']}' paused."

    elif action == "resume":
        task_id = parameters.get("task_id", "")
        if task_id not in data["tasks"]:
            return f"Task '{task_id}' not found."
        data["tasks"][task_id]["status"] = "active"
        sched = _parse_schedule(data["tasks"][task_id].get("schedule_text", "every 1 hour"))
        data["tasks"][task_id]["next_run"] = _next_run(sched, datetime.now())
        _save_tasks(data)
        _ensure_background()
        return f"Task '{data['tasks'][task_id]['name']}' resumed."

    elif action == "log":
        logs = data.get("log", [])
        limit = parameters.get("limit", 20)
        recent = logs[-limit:]
        if not recent:
            return "No execution log entries."
        lines = [f"[{e['executed_at']}] {e['name']} (id: {e['task_id']}) - {e['result']}" for e in recent]
        return f"Execution log (last {len(recent)} entries):\n" + "\n".join(lines)

    else:
        return f"Unknown action: '{action}'. Valid: add, list, delete, run_now, pause, resume, log"
