"""
actions/proactive_ia.py — Proactive intelligence for ERIS.
Takes initiative: remembers pending tasks, suggests actions, monitors patterns.
"""
import json
import time
from datetime import datetime, timedelta
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
_STATE_FILE = _BASE / "data" / "proactive_state.json"
_SUGGESTIONS_FILE = _BASE / "data" / "proactive_suggestions.json"

def _load_state():
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "pending_tasks": [],
        "suggestions": [],
        "patterns": {},
        "last_analysis": None,
        "reminders": [],
        "watched_files": [],
        "streaks": {},
    }

def _save_state(state):
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

def _load_suggestions():
    if _SUGGESTIONS_FILE.exists():
        try:
            return json.loads(_SUGGESTIONS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"suggestions": [], "dismissed": []}

def _save_suggestions(data):
    _SUGGESTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _SUGGESTIONS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def proactive_ia(parameters: dict = None, player=None) -> str:
    params = parameters or {}
    action = params.get("action", "status").lower()

    if action == "status":
        state = _load_state()
        pending = state.get("pending_tasks", [])
        reminders = state.get("reminders", [])
        suggestions = _load_suggestions().get("suggestions", [])
        active_reminders = [r for r in reminders if not r.get("triggered")]
        lines = [
            "Proactive IA Status:",
            f"  Pending tasks: {len(pending)}",
            f"  Active reminders: {len(active_reminders)}",
            f"  Pending suggestions: {len(suggestions)}",
            f"  Watched files: {len(state.get('watched_files', []))}",
            f"  Last analysis: {state.get('last_analysis', 'never')}",
        ]
        return "\n".join(lines)

    elif action == "add_task":
        task = params.get("task", "")
        priority = params.get("priority", "normal")
        deadline = params.get("deadline", "")
        if not task:
            return "Requires 'task'."
        state = _load_state()
        state["pending_tasks"].append({
            "task": task,
            "priority": priority,
            "deadline": deadline,
            "created": datetime.now().isoformat(),
            "status": "pending",
        })
        _save_state(state)
        return f"Task added: {task} (priority: {priority})"

    elif action == "complete_task":
        task_ref = params.get("task", "")
        state = _load_state()
        for t in state["pending_tasks"]:
            if task_ref.lower() in t["task"].lower() and t["status"] == "pending":
                t["status"] = "completed"
                t["completed_at"] = datetime.now().isoformat()
                _save_state(state)
                return f"Task completed: {t['task']}"
        return f"No pending task matching '{task_ref}'."

    elif action == "list_tasks":
        state = _load_state()
        pending = [t for t in state.get("pending_tasks", []) if t["status"] == "pending"]
        if not pending:
            return "No pending tasks."
        lines = [f"Pending Tasks ({len(pending)}):"]
        for i, t in enumerate(pending, 1):
            deadline_str = f" | due: {t['deadline']}" if t.get("deadline") else ""
            lines.append(f"  {i}. [{t['priority']}] {t['task']}{deadline_str}")
        return "\n".join(lines)

    elif action == "add_reminder":
        text = params.get("text", "")
        when = params.get("when", "")
        if not text:
            return "Requires 'text'."
        state = _load_state()
        state["reminders"].append({
            "text": text,
            "when": when,
            "created": datetime.now().isoformat(),
            "triggered": False,
        })
        _save_state(state)
        return f"Reminder set: {text} ({when})"

    elif action == "check_reminders":
        state = _load_state()
        now = datetime.now()
        due = []
        for r in state.get("reminders", []):
            if r.get("triggered"):
                continue
            when_str = r.get("when", "")
            if when_str:
                try:
                    when_dt = datetime.fromisoformat(when_str)
                    if when_dt <= now:
                        r["triggered"] = True
                        due.append(r)
                except Exception:
                    pass
        _save_state(state)
        if not due:
            return "No reminders due."
        lines = [f"Due Reminders ({len(due)}):"]
        for r in due:
            lines.append(f"  - {r['text']}")
        return "\n".join(lines)

    elif action == "suggest":
        suggestions_data = _load_suggestions()
        suggestions = suggestions_data.get("suggestions", [])
        if not suggestions:
            suggestions = _generate_suggestions()
            suggestions_data["suggestions"] = suggestions
            _save_suggestions(suggestions_data)
        if not suggestions:
            return "No suggestions right now. Everything looks good!"
        lines = ["Suggestions:"]
        for i, s in enumerate(suggestions[:5], 1):
            lines.append(f"  {i}. [{s['category']}] {s['text']}")
        return "\n".join(lines)

    elif action == "dismiss":
        idx = int(params.get("index", 1)) - 1
        suggestions_data = _load_suggestions()
        suggestions = suggestions_data.get("suggestions", [])
        if 0 <= idx < len(suggestions):
            dismissed = suggestions.pop(idx)
            suggestions_data.setdefault("dismissed", []).append(dismissed)
            _save_suggestions(suggestions_data)
            return f"Dismissed: {dismissed['text']}"
        return "Invalid index."

    elif action == "watch_file":
        path = params.get("path", "")
        if not path:
            return "Requires 'path'."
        state = _load_state()
        watched = state.get("watched_files", [])
        if path not in watched:
            watched.append(path)
            state["watched_files"] = watched
            _save_state(state)
        return f"Now watching: {path}"

    elif action == "unwatch_file":
        path = params.get("path", "")
        state = _load_state()
        watched = state.get("watched_files", [])
        state["watched_files"] = [w for w in watched if w != path]
        _save_state(state)
        return f"Stopped watching: {path}"

    elif action == "check_files":
        state = _load_state()
        watched = state.get("watched_files", [])
        if not watched:
            return "No watched files."
        changes = []
        for path in watched:
            p = Path(path)
            if p.exists():
                mtime = datetime.fromtimestamp(p.stat().st_mtime)
                changes.append(f"  {path}: modified {mtime.strftime('%Y-%m-%d %H:%M')}")
            else:
                changes.append(f"  {path}: MISSING")
        return f"Watched Files ({len(watched)}):\n" + "\n".join(changes)

    elif action == "analyze":
        state = _load_state()
        state["last_analysis"] = datetime.now().isoformat()
        _save_state(state)
        pending = state.get("pending_tasks", [])
        overdue = []
        now = datetime.now()
        for t in pending:
            if t.get("deadline") and t["status"] == "pending":
                try:
                    dl = datetime.fromisoformat(t["deadline"])
                    if dl < now:
                        overdue.append(t)
                except Exception:
                    pass
        lines = ["Analysis:"]
        lines.append(f"  Total pending tasks: {len(pending)}")
        if overdue:
            lines.append(f"  OVERDUE: {len(overdue)}")
            for t in overdue:
                lines.append(f"    - {t['task']} (due: {t['deadline']})")
        else:
            lines.append("  No overdue tasks.")
        lines.append(f"  Reminders: {len(state.get('reminders', []))}")
        lines.append(f"  Watched files: {len(state.get('watched_files', []))}")
        return "\n".join(lines)

    elif action == "clear_completed":
        state = _load_state()
        before = len(state.get("pending_tasks", []))
        state["pending_tasks"] = [t for t in state["pending_tasks"] if t["status"] != "completed"]
        after = len(state["pending_tasks"])
        _save_state(state)
        return f"Cleared {before - after} completed tasks. {after} remaining."

    elif action == "export":
        state = _load_state()
        return json.dumps(state, indent=2, ensure_ascii=False)

    return "Actions: status, add_task, complete_task, list_tasks, add_reminder, check_reminders, suggest, dismiss, watch_file, unwatch_file, check_files, analyze, clear_completed, export"


def _generate_suggestions():
    suggestions = []
    state = _load_state()

    pending = [t for t in state.get("pending_tasks", []) if t["status"] == "pending"]
    if len(pending) > 5:
        suggestions.append({
            "category": "productivity",
            "text": f"You have {len(pending)} pending tasks. Consider prioritizing or delegating.",
        })

    now = datetime.now()
    for t in pending:
        if t.get("deadline"):
            try:
                dl = datetime.fromisoformat(t["deadline"])
                if dl < now:
                    suggestions.append({
                        "category": "urgent",
                        "text": f"OVERDUE: '{t['task']}' was due {t['deadline']}",
                    })
                elif (dl - now).total_seconds() < 3600:
                    suggestions.append({
                        "category": "urgent",
                        "text": f"Due soon: '{t['task']}' due in {int((dl - now).total_seconds() / 60)} min",
                    })
            except Exception:
                pass

    watched = state.get("watched_files", [])
    for path in watched:
        p = Path(path)
        if p.exists():
            mtime = datetime.fromtimestamp(p.stat().st_mtime)
            if (now - mtime).total_seconds() < 300:
                suggestions.append({
                    "category": "file_change",
                    "text": f"File recently modified: {path}",
                })

    if not suggestions:
        suggestions.append({
            "category": "general",
            "text": "All clear! Consider learning something new or organizing your workspace.",
        })

    return suggestions
