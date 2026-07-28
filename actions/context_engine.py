"""Context awareness engine that tracks user state and suggests actions."""

import json
import os
import time
from datetime import datetime
from typing import Any

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
CONTEXT_FILE = os.path.join(DATA_DIR, "context_engine.json")


def _load_context() -> dict[str, Any]:
    if os.path.exists(CONTEXT_FILE):
        with open(CONTEXT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "profile": {
            "name": "User",
            "language": "es",
            "timezone_offset": 0,
            "preferences": {},
        },
        "current": {
            "time_of_day": "",
            "hour": 0,
            "day_of_week": "",
            "recent_commands": [],
            "active_apps": [],
            "last_updated": "",
        },
        "history": [],
        "preferences": {},
    }


def _save_context(data: dict[str, Any]) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CONTEXT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)


def _detect_time_context(hour: int) -> str:
    if 5 <= hour < 12:
        return "morning"
    elif 12 <= hour < 14:
        return "midday"
    elif 14 <= hour < 18:
        return "afternoon"
    elif 18 <= hour < 21:
        return "evening"
    else:
        return "night"


def _get_time_suggestions(time_ctx: str) -> list[dict[str, str]]:
    suggestions: dict[str, list[dict[str, str]]] = {
        "morning": [
            {"action": "weather", "description": "Check weather forecast for the day", "priority": "medium"},
            {"action": "calendar", "description": "Review today's calendar/schedule", "priority": "high"},
            {"action": "news", "description": "Check morning news briefing", "priority": "low"},
            {"action": "coffee_reminder", "description": "Time for a coffee break reminder", "priority": "low"},
        ],
        "midday": [
            {"action": "lunch", "description": "Lunch time suggestion", "priority": "medium"},
            {"action": "break", "description": "Take a short break", "priority": "medium"},
        ],
        "afternoon": [
            {"action": "tasks", "description": "Review remaining tasks for the day", "priority": "high"},
            {"action": "standup", "description": "Prepare end-of-day summary", "priority": "medium"},
        ],
        "evening": [
            {"action": "summary", "description": "End of day work summary", "priority": "medium"},
            {"action": "backup", "description": "Run daily backup", "priority": "low"},
            {"action": "review", "description": "Review tomorrow's schedule", "priority": "medium"},
        ],
        "night": [
            {"action": "shutdown", "description": "Consider shutting down or sleeping", "priority": "medium"},
            {"action": "backup", "description": "Final backup before sleep", "priority": "high"},
            {"action": "clean", "description": "Clean temp files before bed", "priority": "low"},
        ],
    }
    return suggestions.get(time_ctx, [])


def _get_app_suggestions(apps: list[str]) -> list[dict[str, str]]:
    suggestions: list[dict[str, str]] = []
    apps_lower = [a.lower() for a in apps]
    dev_tools = {"code", "vscode", "visual studio", "pycharm", "intellij", "atom", "sublime",
                 "vim", "nvim", "git", "terminal", "cmd", "powershell", "devenv", "cursor"}
    browser_tools = {"chrome", "firefox", "edge", "opera", "brave", "vivaldi"}
    office_tools = {"word", "excel", "powerpoint", "outlook", "teams", "slack", "discord"}

    if any(d in a for a in apps_lower for d in dev_tools):
        suggestions.append({"action": "compile", "description": "Compile or lint current project", "priority": "medium"})
        suggestions.append({"action": "git_status", "description": "Check git status", "priority": "medium"})
        suggestions.append({"action": "backup_code", "description": "Backup current code", "priority": "low"})

    if any(b in a for a in apps_lower for b in browser_tools):
        suggestions.append({"action": "bookmark_check", "description": "Review open tabs/bookmarks", "priority": "low"})

    if any(o in a for a in apps_lower for o in office_tools):
        suggestions.append({"action": "email_check", "description": "Check for unread emails", "priority": "medium"})
        suggestions.append({"action": "meeting_prep", "description": "Prepare for next meeting", "priority": "medium"})

    return suggestions


def _record_history(data: dict[str, Any], event: str, details: str = "") -> None:
    entry = {
        "timestamp": datetime.now().isoformat(),
        "event": event,
        "details": details,
    }
    data["history"].append(entry)
    if len(data["history"]) > 500:
        data["history"] = data["history"][-500:]


def context_engine(parameters: dict, player=None) -> str:
    action = parameters.get("action", "analyze").lower()
    data = _load_context()

    if action == "analyze":
        now = datetime.now()
        hour = now.hour
        time_ctx = _detect_time_context(hour)
        day = now.strftime("%A")
        data["current"]["time_of_day"] = time_ctx
        data["current"]["hour"] = hour
        data["current"]["day_of_week"] = day
        data["current"]["last_updated"] = now.isoformat()

        recent = parameters.get("recent_commands", [])
        if recent:
            data["current"]["recent_commands"] = recent[-50:]
        apps = parameters.get("active_apps", [])
        if apps:
            data["current"]["active_apps"] = apps

        _save_context(data)
        _record_history(data, "context_analyzed", f"time={time_ctx}, hour={hour}, day={day}")

        lines = [
            f"Time of day: {time_ctx} ({hour}:XX)",
            f"Day: {day}",
            f"Recent commands: {len(data['current']['recent_commands'])} tracked",
            f"Active apps: {len(data['current']['active_apps'])} detected",
            f"User: {data.get('profile', {}).get('name', 'Unknown')}",
            f"Last analysis: {data['current']['last_updated']}",
        ]
        return f"Current context:\n" + "\n".join(lines)

    elif action == "suggest":
        now = datetime.now()
        hour = now.hour
        time_ctx = _detect_time_context(hour)
        apps = data.get("current", {}).get("active_apps", [])
        if not apps:
            apps = parameters.get("active_apps", [])
        prefs = data.get("preferences", {})
        all_suggestions: list[dict[str, str]] = []

        all_suggestions.extend(_get_time_suggestions(time_ctx))
        all_suggestions.extend(_get_app_suggestions(apps))

        if prefs.get("auto_backup", False):
            all_suggestions.append({"action": "backup", "description": "Auto-backup enabled", "priority": "low"})
        if prefs.get("focus_mode", False):
            all_suggestions = [s for s in all_suggestions if s.get("priority") == "high"]

        priority_order = {"high": 0, "medium": 1, "low": 2}
        all_suggestions.sort(key=lambda s: priority_order.get(s.get("priority", "low"), 2))
        all_suggestions = all_suggestions[:8]

        if not all_suggestions:
            return "No suggestions at this time."

        _record_history(data, "suggestions_given", f"{len(all_suggestions)} suggestions for {time_ctx}")
        _save_context(data)

        lines = []
        for i, s in enumerate(all_suggestions, 1):
            lines.append(f"  {i}. [{s['priority'].upper()}] {s['action']}: {s['description']}")
        return f"Suggestions for {time_ctx} ({day}, {hour:02d}h):\n" + "\n".join(lines)

    elif action == "history":
        limit = int(parameters.get("limit", 20))
        history = data.get("history", [])
        recent = history[-limit:]
        if not recent:
            return "No context history."
        lines = [f"[{e['timestamp']}] {e['event']}: {e['details']}" for e in recent]
        return f"Context history ({len(recent)} entries):\n" + "\n".join(lines)

    elif action == "profile":
        sub = parameters.get("sub_action", "get")
        profile = data.get("profile", {})
        if sub == "get":
            lines = [
                f"Name: {profile.get('name', 'Unknown')}",
                f"Language: {profile.get('language', 'en')}",
                f"Timezone offset: {profile.get('timezone_offset', 0)}",
            ]
            prefs = data.get("preferences", {})
            if prefs:
                lines.append("Preferences:")
                for k, v in prefs.items():
                    lines.append(f"  {k}: {v}")
            return "User profile:\n" + "\n".join(lines)
        elif sub == "set":
            name = parameters.get("name")
            if name:
                profile["name"] = name
            lang = parameters.get("language")
            if lang:
                profile["language"] = lang
            tz = parameters.get("timezone_offset")
            if tz is not None:
                profile["timezone_offset"] = float(tz)
            data["profile"] = profile
            _save_context(data)
            _record_history(data, "profile_updated", str(profile))
            return f"Profile updated: {profile}"
        return "Invalid sub_action for profile."

    elif action == "update":
        key = parameters.get("key", "")
        value = parameters.get("value", "")
        if not key:
            return "Error: 'key' parameter is required."
        data.setdefault("preferences", {})[key] = value
        _save_context(data)
        _record_history(data, "preference_updated", f"{key}={value}")
        return f"Preference updated: {key} = {value}"

    else:
        return f"Unknown action: '{action}'. Valid: analyze, suggest, history, profile, update"
